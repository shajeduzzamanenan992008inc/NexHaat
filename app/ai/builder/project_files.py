"""Validation and deterministic source handling for saved Builder projects."""

from __future__ import annotations

from hashlib import sha256
from html import escape
import json
from pathlib import PurePosixPath
import re

from .archives import ProjectArchiveError, inspect_project_archive


MAX_PROJECT_FILES = 100
MAX_PROJECT_BYTES = 512 * 1024
MAX_PROJECT_FILE_BYTES = 64 * 1024
_ALLOWED_SUFFIXES = {
    ".cjs", ".cfg", ".css", ".html", ".ini", ".js", ".jsx", ".json",
    ".md", ".mjs", ".py", ".pyi", ".sql", ".toml", ".ts", ".tsx",
    ".txt", ".xml", ".yaml", ".yml",
}
_ALLOWED_NAMES = {"dockerfile", "makefile", "procfile"}
_BLOCKED_PARTS = {".git", ".hg", ".svn", ".venv", "__pycache__", "build", "dist", "node_modules", "venv"}
_BLOCKED_NAMES = {
    ".env", "credentials", "id_rsa", "id_ed25519", "private.key",
    "secrets.json", "service-account.json",
}
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|password|passwd|secret|token)"
        r"\s*[:=]\s*['\"][A-Za-z0-9_./+=:-]{16,}['\"]"
    ),
)


class ProjectFilesError(ValueError):
    """A project file set failed the bounded source policy."""


def validate_project_path(value: str) -> str:
    if (
        not isinstance(value, str) or not value or len(value) > 240
        or "\x00" in value or "\\" in value or value.startswith(("/", "~"))
    ):
        raise ProjectFilesError("Project contains an unsafe file path.")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or (path.parts and ":" in path.parts[0])
    ):
        raise ProjectFilesError("Project contains an unsafe file path.")
    if not path.parts or any(part.lower() in _BLOCKED_PARTS for part in path.parts[:-1]):
        raise ProjectFilesError("Project contains a generated or private directory.")
    name = path.name.lower()
    if name in _BLOCKED_NAMES or name.startswith(".env."):
        raise ProjectFilesError("Project contains a private settings file.")
    if name not in _ALLOWED_NAMES and path.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise ProjectFilesError("Project contains an unsupported file type.")
    return path.as_posix()


def normalize_project_files(files) -> list[dict[str, str]]:
    if not isinstance(files, (list, tuple)) or not files or len(files) > MAX_PROJECT_FILES:
        raise ProjectFilesError("A project must contain between one and 100 source files.")
    normalized = {}
    byte_count = 0
    for entry in files:
        if isinstance(entry, dict):
            path, content = entry.get("path"), entry.get("content")
        elif isinstance(entry, (tuple, list)) and len(entry) == 2:
            path, content = entry
        else:
            raise ProjectFilesError("Project files must contain a path and text content.")
        path = validate_project_path(path)
        if not isinstance(content, str) or "\x00" in content:
            raise ProjectFilesError("Project source must be valid UTF-8 text.")
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        encoded_size = len(content.encode("utf-8"))
        if encoded_size > MAX_PROJECT_FILE_BYTES:
            raise ProjectFilesError("A project file exceeds the 64 KB limit.")
        byte_count += encoded_size
        if byte_count > MAX_PROJECT_BYTES:
            raise ProjectFilesError("Project source exceeds the 512 KB limit.")
        if path in normalized:
            raise ProjectFilesError("Project contains duplicate file paths.")
        normalized[path] = content
    return [{"path": path, "content": normalized[path]} for path in sorted(normalized)]


def project_files_from_json(raw: str) -> list[dict[str, str]]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as error:
        raise ProjectFilesError("Saved project source is unavailable.") from error
    return normalize_project_files(value)


def encode_project_files(files) -> str:
    normalized = normalize_project_files(files)
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def project_digest(files) -> str:
    canonical = encode_project_files(files)
    return sha256(canonical.encode("utf-8")).hexdigest()


def has_secret_literal(files) -> bool:
    for item in normalize_project_files(files):
        if any(pattern.search(item["content"]) for pattern in _SECRET_PATTERNS):
            return True
    return False


def inspect_uploaded_project(data: bytes, filename: str) -> list[dict[str, str]]:
    """Read source from a ZIP or bounded single text file without extraction."""
    safe_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    suffix = PurePosixPath(safe_name).suffix.lower()
    if suffix == ".zip":
        try:
            return normalize_project_files(inspect_project_archive(data))
        except ProjectArchiveError as error:
            raise ProjectFilesError(str(error)) from error
    if len(data) > MAX_PROJECT_FILE_BYTES:
        raise ProjectFilesError("A project file exceeds the 64 KB limit.")
    if suffix not in _ALLOWED_SUFFIXES and safe_name.lower() not in _ALLOWED_NAMES:
        raise ProjectFilesError("Upload a ZIP, source text, PDF, image, or audio file.")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ProjectFilesError("Text source must use UTF-8 encoding.") from error
    return normalize_project_files([{"path": safe_name, "content": content}])


def diff_project_files(before, after) -> str:
    """Create a bounded unified diff from two already validated file sets."""
    from difflib import unified_diff

    old = {item["path"]: item["content"] for item in normalize_project_files(before)}
    new = {item["path"]: item["content"] for item in normalize_project_files(after)}
    chunks = []
    for path in sorted(set(old) | set(new)):
        if old.get(path) == new.get(path):
            continue
        chunks.extend(unified_diff(
            old.get(path, "").splitlines(keepends=True),
            new.get(path, "").splitlines(keepends=True),
            fromfile=f"a/{path}" if path in old else "/dev/null",
            tofile=f"b/{path}" if path in new else "/dev/null",
            n=3,
        ))
        if not chunks or not chunks[-1].endswith("\n"):
            chunks.append("\n")
    result = "".join(chunks)
    if len(result) > MAX_PROJECT_BYTES:
        raise ProjectFilesError("The generated change exceeds the review limit.")
    return result


def apply_file_changes(files, changes) -> list[dict[str, str]]:
    if not isinstance(changes, list) or not changes or len(changes) > MAX_PROJECT_FILES:
        raise ProjectFilesError("Provide between one and 100 file changes.")
    result = {item["path"]: item["content"] for item in normalize_project_files(files)}
    for change in changes:
        if not isinstance(change, dict):
            raise ProjectFilesError("Each change must specify a path and content.")
        path = validate_project_path(change.get("path"))
        if change.get("delete") is True:
            if path not in result:
                raise ProjectFilesError("A deleted file must exist in the project.")
            del result[path]
        else:
            result[path] = change.get("content")
    if not result:
        raise ProjectFilesError("A patch cannot remove every project file.")
    return normalize_project_files([{"path": path, "content": content} for path, content in result.items()])


def starter_project_files(project_type: str, name: str) -> list[dict[str, str]]:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "nexhaat-project"
    if project_type == "flask":
        files = [
            {
                "path": "app.py",
                "content": (
                    '"""Small Flask starter application."""\n\n'
                    "from flask import Flask, jsonify\n\n"
                    "app = Flask(__name__)\n\n"
                    "@app.get(\"/health\")\n"
                    "def health():\n"
                    "    return jsonify(status=\"ok\")\n"
                ),
            },
            {
                "path": "tests/test_app.py",
                "content": (
                    "from app import app\n\n\n"
                    "def test_health_endpoint():\n"
                    "    response = app.test_client().get(\"/health\")\n"
                    "    assert response.status_code == 200\n"
                    "    assert response.get_json() == {\"status\": \"ok\"}\n"
                ),
            },
        ]
    elif project_type == "python":
        files = [
            {"path": "main.py", "content": '"""Python starter module."""\n\n\ndef main():\n    return "Hello from NexHaat"\n\n\nif __name__ == "__main__":\n    print(main())\n'},
            {"path": "tests/test_main.py", "content": "from main import main\n\n\ndef test_main_returns_greeting():\n    assert main() == \"Hello from NexHaat\"\n"},
        ]
    else:
        safe_name = escape(name[:100], quote=True)
        files = [
            {"path": "index.html", "content": "<!doctype html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>" + safe_name + "</title>\n  <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n  <main><h1>" + safe_name + "</h1><p>Your project starter is ready.</p></main>\n  <script src=\"app.js\" defer></script>\n</body>\n</html>\n"},
            {"path": "styles.css", "content": "body { font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }\nmain { max-width: 48rem; margin: 0 auto; }\n"},
            {"path": "app.js", "content": "'use strict';\n\n// Add your browser-side behavior here.\n"},
            {"path": "tests/test_static_project.py", "content": "from pathlib import Path\n\n\ndef test_static_starter_has_semantic_entrypoint():\n    page = Path(\"index.html\").read_text(encoding=\"utf-8\")\n    assert \"<main>\" in page\n    assert \"styles.css\" in page\n    assert \"app.js\" in page\n"},
        ]
    files.append({"path": "README.md", "content": f"# {name}\n\nGenerated starter project ({project_type}).\n\nProject ID: {slug}\n"})
    return normalize_project_files(files)
