"""Bounded, non-extracting inspection of uploaded project archives."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
import stat
import zipfile


MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 500
MAX_ARCHIVE_TOTAL_BYTES = 40 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 4 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200

_SOURCE_SUFFIXES = {
    ".cjs", ".cfg", ".css", ".csv", ".html", ".ini", ".js", ".jsx",
    ".json", ".md", ".mjs", ".py", ".pyi", ".sql", ".toml", ".ts",
    ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
_SOURCE_NAMES = {"dockerfile", "makefile", "procfile"}
_IGNORED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".venv", "__pycache__", "build", "dist",
    "node_modules", "venv",
}
_SENSITIVE_NAMES = {
    ".env", "credentials", "id_rsa", "id_ed25519", "secrets.json",
}


class ProjectArchiveError(ValueError):
    """The uploaded project archive is invalid or exceeds inspection limits."""


def inspect_project_archive(data: bytes) -> list[tuple[str, str]]:
    """Return bounded source text from a ZIP without writing or executing files."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_ARCHIVE_BYTES:
        raise ProjectArchiveError("Project archive is empty or exceeds the upload limit.")

    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except (OSError, zipfile.BadZipFile, ValueError) as error:
        raise ProjectArchiveError("Upload a valid ZIP project archive.") from error

    results = []
    try:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_ENTRIES:
            raise ProjectArchiveError("Project archive contains too many entries.")
        declared_total = 0
        for item in entries:
            path = _validate_member_path(item.filename)
            mode = item.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            if file_type == stat.S_IFLNK:
                raise ProjectArchiveError("Project archives cannot contain symbolic links.")
            if item.is_dir():
                if file_type not in {0, stat.S_IFDIR}:
                    raise ProjectArchiveError("Project archive contains an unsupported filesystem entry.")
                continue
            if file_type not in {0, stat.S_IFREG}:
                raise ProjectArchiveError("Project archive contains an unsupported filesystem entry.")
            if item.flag_bits & 0x1:
                raise ProjectArchiveError("Encrypted project files are not supported.")
            if item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise ProjectArchiveError("Project archive uses an unsupported compression method.")
            if item.file_size < 0 or item.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                raise ProjectArchiveError("A project file exceeds the per-file inspection limit.")
            declared_total += item.file_size
            if declared_total > MAX_ARCHIVE_TOTAL_BYTES:
                raise ProjectArchiveError("Project archive expands beyond the inspection limit.")
            if item.file_size and (
                item.compress_size <= 0
                or item.file_size / item.compress_size > MAX_COMPRESSION_RATIO
            ):
                raise ProjectArchiveError("Project archive has an unsafe compression ratio.")
            if not _is_inspectable_source(path):
                continue
            try:
                with archive.open(item, "r") as source:
                    content = source.read(MAX_ARCHIVE_MEMBER_BYTES + 1)
            except (OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
                raise ProjectArchiveError("A project file could not be safely read.") from error
            if len(content) > MAX_ARCHIVE_MEMBER_BYTES or len(content) != item.file_size:
                raise ProjectArchiveError("A project file exceeded its declared inspection size.")
            if b"\x00" in content:
                continue
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            results.append((path.as_posix(), text))
    finally:
        archive.close()
    return results


def _validate_member_path(name: str) -> PurePosixPath:
    if (not isinstance(name, str) or not name or "\x00" in name
            or "\\" in name or name.startswith("/") or name.startswith("~")):
        raise ProjectArchiveError("Project archive contains an unsafe file path.")
    path = PurePosixPath(name)
    if (path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)
            or (path.parts and ":" in path.parts[0])):
        raise ProjectArchiveError("Project archive contains an unsafe file path.")
    return path


def _is_inspectable_source(path: PurePosixPath) -> bool:
    parts = path.parts
    if any(part.lower() in _IGNORED_DIRECTORIES for part in parts[:-1]):
        return False
    name = parts[-1].lower()
    if name in _SENSITIVE_NAMES or name.startswith(".env."):
        return False
    return name in _SOURCE_NAMES or path.suffix.lower() in _SOURCE_SUFFIXES
