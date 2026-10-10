"""Validate that the dotenv template documents every statically referenced env key.

This script intentionally uses only the Python standard library so CI can run it
before runtime dependencies are installed and without contacting external services.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".env.example"
ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")
ENV_ACCESS = re.compile(
    r"(?:os\.getenv|os\.environ\.get|_env_bool|_env_int)\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]"
)
SECRET_NAME = re.compile(r"(?:SECRET_KEY|API_KEY|(?:^|_)TOKEN$|_PASSWORD$|_BOT_TOKEN$|_WEBHOOK_SECRET$)", re.IGNORECASE)
SAFE_EXAMPLE_SECRETS = {"", "dev-only-change-me"}


def main() -> int:
    if not TEMPLATE.is_file():
        print("ERROR: .env.example is missing.", file=sys.stderr)
        return 1

    declared: dict[str, str] = {}
    duplicates: list[str] = []
    invalid_lines: list[int] = []
    for line_number, raw_line in enumerate(TEMPLATE.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ENV_LINE.fullmatch(stripped)
        if not match:
            invalid_lines.append(line_number)
            continue
        name, value = match.groups()
        if name in declared:
            duplicates.append(name)
        declared[name] = value.strip().strip("\"'")

    referenced: set[str] = set()
    for path in (ROOT / "app").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        referenced.update(ENV_ACCESS.findall(source))

    missing = sorted(referenced - declared.keys())
    unsafe_secrets = sorted(
        name for name, value in declared.items()
        if SECRET_NAME.search(name) and value not in SAFE_EXAMPLE_SECRETS
    )

    errors = False
    if invalid_lines:
        print(f"ERROR: invalid dotenv line(s): {', '.join(map(str, invalid_lines))}")
        errors = True
    if duplicates:
        print(f"ERROR: duplicate key(s): {', '.join(sorted(set(duplicates)))}")
        errors = True
    if missing:
        print(f"ERROR: environment key(s) referenced in app code but missing in .env.example: {', '.join(missing)}")
        errors = True
    if unsafe_secrets:
        print(f"ERROR: non-empty secret-like value(s) must be blank/demo-only: {', '.join(unsafe_secrets)}")
        errors = True

    if errors:
        return 1
    print(f"Environment template OK: {len(declared)} unique keys; {len(referenced)} statically referenced keys covered; no non-demo secrets detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
