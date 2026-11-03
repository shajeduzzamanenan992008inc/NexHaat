"""Lightweight structural checks for AI-generated feature integration.

This checker intentionally validates only objective repository contracts. It
does not reject legacy naming, infer ownership from filenames, or move/delete
files.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "architecture" / "FEATURE_REGISTRY.json"
REQUIRED_DOCS = (
    ROOT / "AGENTS.md",
    ROOT / "docs" / "PROJECT_STRUCTURE_GUIDE.md",
    ROOT / "docs" / "GOOGLE_AI_STUDIO_INTEGRATION.md",
    ROOT / "docs" / "AI_FEATURE_INTEGRATION_GUIDE.md",
    ROOT / "docs" / "templates" / "AI_FEATURE_SUBMISSION_TEMPLATE.md",
    ROOT / "docs" / "architecture" / "FEATURE_REGISTRY.json",
)
REQUIRED_CONFIG = (
    ROOT / "package.json",
    ROOT / "package-lock.json",
    ROOT / "requirements.txt",
    ROOT / "android" / "gradlew.bat",
    ROOT / "android" / "settings.gradle.kts",
)
NODE_MANIFEST = ROOT / "package.json"
NODE_LOCKFILE = ROOT / "package-lock.json"
NODE_LOCKFILE_MIN_VERSION = 2
COMPETING_NODE_LOCKFILES = (
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lock",
    "bun.lockb",
    "npm-shrinkwrap.json",
)
SOURCE_PREFIXES = ("app/", "src/", "android/app/src/", "tests/", "migrations/", "scripts/")
SOURCE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".kt", ".kts", ".sql")


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def validate_registry(failures: list[str]) -> int:
    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"registry unreadable: {error}", failures)
        return 0

    features = registry.get("features")
    if not isinstance(features, list):
        fail("registry must contain a features array", failures)
        return 0

    ids = [feature.get("id") for feature in features if isinstance(feature, dict)]
    duplicates = sorted({feature_id for feature_id in ids if ids.count(feature_id) > 1})
    for duplicate in duplicates:
        fail(f"duplicate feature id: {duplicate}", failures)

    checked_paths = 0
    for feature in features:
        if not isinstance(feature, dict):
            fail("registry feature entry is not an object", failures)
            continue
        feature_id = feature.get("id", "<unknown>")
        for field in ("frontend_locations", "backend_locations", "test_locations"):
            for raw_path in feature.get(field, []):
                path = ROOT / raw_path
                checked_paths += 1
                if not path.exists():
                    fail(f"{feature_id}: missing {field} path {raw_path}", failures)
    return checked_paths


def validate_frontend_boundaries(failures: list[str]) -> tuple[int, int]:
    source_files = list((ROOT / "src").rglob("*.ts")) + list((ROOT / "src").rglob("*.tsx"))
    marketplace_direct = 0
    express_direct = 0
    for path in source_files:
        if path.parts[-2:] == ("lib", path.name):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"""['"`]/api/v1/""", text):
            marketplace_direct += 1
            fail(f"direct Flask marketplace path outside src/lib: {path.relative_to(ROOT)}", failures)
        if re.search(r"""['"`]/api/(?:gemini|science)/""", text):
            express_direct += 1
    return marketplace_direct, express_direct


def resolve_import_target(source: Path, raw_target: str) -> Path | None:
    target = (source.parent / raw_target).resolve()
    candidates = [target]
    if not target.suffix:
        candidates.extend(target.with_suffix(suffix) for suffix in (".ts", ".tsx", ".js", ".jsx"))
        candidates.append(target / "index.ts")
        candidates.append(target / "index.tsx")
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def validate_relative_imports(failures: list[str]) -> int:
    missing = 0
    import_pattern = re.compile(
        r"""(?:from\s+|import\s+(?!type\b)|import\s*\(\s*)['"](\.[^'"]+)['"]"""
    )
    source_files = list((ROOT / "src").rglob("*.ts")) + list((ROOT / "src").rglob("*.tsx"))
    for source in source_files:
        text = source.read_text(encoding="utf-8", errors="replace")
        for raw_target in import_pattern.findall(text):
            if resolve_import_target(source, raw_target) is None:
                missing += 1
                failures.append(
                    f"missing relative import target: {source.relative_to(ROOT)} -> {raw_target}"
                )
    return missing


def validate_required_config(failures: list[str]) -> int:
    missing = 0
    for path in REQUIRED_CONFIG:
        if not path.exists():
            missing += 1
            failures.append(f"missing required configuration: {path.relative_to(ROOT)}")
    return missing


def read_json_object(path: Path, label: str, failures: list[str]) -> dict | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{label} unreadable: {error}", failures)
        return None
    if not isinstance(document, dict):
        fail(f"{label} must contain a JSON object", failures)
        return None
    return document


def validate_node_dependency_lock(failures: list[str]) -> tuple[int, int, int]:
    """Validate the npm manifest/lockfile pair that CI installs with ``npm ci``.

    Presence alone is not a meaningful contract: a lockfile whose dependency
    graph or integrity hashes cannot reproduce ``package.json`` makes the
    frontend job fail, or installs a different tree than the one reviewed.
    """
    for competing in COMPETING_NODE_LOCKFILES:
        if (ROOT / competing).exists():
            fail(
                f"conflicting Node lockfile {competing}: npm with package-lock.json is the "
                "authoritative package-management contract",
                failures,
            )

    if not NODE_MANIFEST.is_file() or not NODE_LOCKFILE.is_file():
        return 0, 0, 0

    manifest = read_json_object(NODE_MANIFEST, "package.json", failures)
    lockfile = read_json_object(NODE_LOCKFILE, "package-lock.json", failures)
    if manifest is None or lockfile is None:
        return 0, 0, 0

    lock_version = lockfile.get("lockfileVersion")
    if not isinstance(lock_version, int) or lock_version < NODE_LOCKFILE_MIN_VERSION:
        fail(
            f"package-lock.json must declare lockfileVersion >= {NODE_LOCKFILE_MIN_VERSION} "
            f"so npm ci can install the exact dependency graph (found {lock_version!r})",
            failures,
        )

    packages = lockfile.get("packages")
    if not isinstance(packages, dict) or not isinstance(packages.get(""), dict):
        fail("package-lock.json has no root packages entry; npm ci cannot install it", failures)
        return 0, 0, 0
    root = packages[""]

    for field in ("name", "version"):
        if root.get(field) != manifest.get(field):
            fail(
                f"package-lock.json root {field} is out of sync with package.json "
                f"({root.get(field)!r} != {manifest.get(field)!r})",
                failures,
            )

    declared = 0
    for section in ("dependencies", "devDependencies"):
        wanted = manifest.get(section) or {}
        locked = root.get(section) or {}
        if not isinstance(wanted, dict) or not isinstance(locked, dict):
            fail(f"package.json {section} and its lockfile copy must be JSON objects", failures)
            continue
        for name, spec in sorted(wanted.items()):
            declared += 1
            if locked.get(name) != spec:
                fail(
                    f"package-lock.json {section} does not match package.json for {name}",
                    failures,
                )
            if not isinstance(packages.get(f"node_modules/{name}"), dict):
                fail(
                    f"package-lock.json has no locked entry for declared dependency {name}",
                    failures,
                )

    resolvable = [
        key for key, entry in packages.items()
        if key and isinstance(entry, dict) and not entry.get("link")
    ]
    without_resolved = [
        key for key in resolvable
        if not isinstance(packages[key].get("resolved"), str) or not packages[key]["resolved"]
    ]
    without_integrity = [
        key for key in resolvable
        if key not in without_resolved
        and packages[key].get("integrity") is None
        and not str(packages[key].get("resolved", "")).startswith(("git", "file:"))
    ]
    if without_resolved:
        fail(
            f"package-lock.json has {len(without_resolved)} entries without a resolved URL "
            f"(first: {without_resolved[0]})",
            failures,
        )
    if without_integrity:
        fail(
            f"package-lock.json has {len(without_integrity)} entries without an integrity hash "
            f"(first: {without_integrity[0]})",
            failures,
        )
    return declared, len(resolvable), len(without_resolved) + len(without_integrity)


def changed_paths(base: str) -> list[tuple[str, str, str | None]]:
    changes: list[tuple[str, str, str | None]] = []
    for args in (
        ["git", "diff", "--name-status", "--find-renames", base],
        ["git", "diff", "--cached", "--name-status", "--find-renames", base],
    ):
        result = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            fields = line.split("\t")
            if len(fields) >= 2:
                old_path = fields[1] if fields[0].startswith("R") and len(fields) >= 3 else None
                changes.append((fields[0], fields[-1], old_path))
    return changes


def validate_change_review(base: str, failures: list[str], fail_on_review: bool) -> tuple[int, int]:
    changes = changed_paths(base)
    deleted = [
        path for status, path, _ in changes
        if status.startswith("D") and path.startswith(SOURCE_PREFIXES)
    ]
    renamed = [
        f"{old_path} -> {path}" if old_path else path
        for status, path, old_path in changes
        if status.startswith("R")
        and (path.startswith(SOURCE_PREFIXES) or (old_path and old_path.startswith(SOURCE_PREFIXES)))
    ]
    if deleted:
        message = "source deletions require human review: " + ", ".join(sorted(set(deleted)))
        if fail_on_review:
            failures.append(message)
        else:
            print(f"REVIEW_REQUIRED: {message}")
    if renamed:
        message = "source renames/moves require human review: " + ", ".join(sorted(set(renamed)))
        if fail_on_review:
            failures.append(message)
        else:
            print(f"REVIEW_REQUIRED: {message}")
    return len(set(deleted)), len(set(renamed))


def git_review_counts() -> tuple[int, int]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    source_review = sum(
        1
        for line in lines
        if any(line[3:].startswith(prefix) for prefix in ("app/", "src/", "android/", "scripts/"))
    )
    return len(lines), source_review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git revision used to review staged and unstaged changes (default: HEAD).",
    )
    parser.add_argument(
        "--fail-on-review",
        action="store_true",
        help="Return non-zero when source deletions or renames require human review.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    missing_docs = [str(path.relative_to(ROOT)) for path in REQUIRED_DOCS if not path.exists()]
    for path in missing_docs:
        fail(f"missing required documentation: {path}", failures)

    checked_paths = validate_registry(failures) if REGISTRY.exists() else 0
    marketplace_direct, express_direct = validate_frontend_boundaries(failures)
    missing_imports = validate_relative_imports(failures)
    missing_config = validate_required_config(failures)
    node_deps, node_packages, node_unverifiable = validate_node_dependency_lock(failures)
    deleted_sources, renamed_sources = validate_change_review(
        args.base, failures, args.fail_on_review
    )
    status_count, source_review_count = git_review_counts()

    print(f"required_docs={len(REQUIRED_DOCS) - len(missing_docs)}/{len(REQUIRED_DOCS)}")
    print(f"registry_paths_checked={checked_paths}")
    print(f"direct_marketplace_paths_outside_adapters={marketplace_direct}")
    print(f"express_ai_call_sites={express_direct}")
    print(f"missing_relative_import_targets={missing_imports}")
    print(f"missing_required_config={missing_config}")
    print(f"node_manifest_dependencies_declared={node_deps}")
    print(f"node_lockfile_packages={node_packages}")
    print(f"node_lockfile_entries_without_resolved_integrity={node_unverifiable}")
    print(f"source_deletions_for_review={deleted_sources}")
    print(f"source_renames_for_review={renamed_sources}")
    print(f"worktree_entries_for_review={status_count}")
    print(f"source_entries_for_review={source_review_count}")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("repository_structure=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
