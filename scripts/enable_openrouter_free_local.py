#!/usr/bin/env python3
"""Enable a verified OpenRouter free model for local SQLite development only.

Supports standard dotenv and legacy Azure App Service JSON-array .env files. It
never prints API keys and refuses to edit production/PostgreSQL settings. Production
must use delivered Security Bot notices and must not enable local notice mode.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
KEY_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=.*$")


def _load_settings(path: Path):
    """Return (format, mapping, original) without printing any values."""
    raw = path.read_text(encoding="utf-8-sig")
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        entries = None
    if isinstance(entries, list) and all(
        isinstance(item, dict) and isinstance(item.get("name"), str) for item in entries
    ):
        return "json", {item["name"]: str(item.get("value") or "").strip() for item in entries}, (raw, entries)

    try:
        from dotenv import dotenv_values
        parsed = dotenv_values(stream=raw)
    except (ImportError, OSError, ValueError):
        parsed = None
    if parsed is None:
        raise ValueError(".env is neither a valid dotenv file nor an Azure JSON array")
    values = {str(k): str(v or "").strip() for k, v in parsed.items() if k}
    return "dotenv", values, (raw, None)


def _write_settings(format_name, loaded, updates):
    """Update a settings file while preserving unrelated dotenv lines/comments."""
    raw, entries = loaded
    if format_name == "json":
        by_name = {item["name"]: item for item in entries}
        for name, value in updates.items():
            if name in by_name:
                by_name[name]["value"] = value
            else:
                item = {"name": name, "value": value, "slotSetting": False}
                entries.append(item)
                by_name[name] = item
        return json.dumps(entries, indent=2, ensure_ascii=False) + "\n"

    seen = set()
    output = []
    for line in raw.splitlines():
        match = KEY_PATTERN.match(line)
        if match and match.group(1) in updates:
            name = match.group(1)
            output.append(f"{name}={updates[name]}")
            seen.add(name)
        else:
            output.append(line)
    for name, value in updates.items():
        if name not in seen:
            output.append(f"{name}={value}")
    return "\n".join(output).rstrip() + "\n"


def main() -> int:
    if not ENV_FILE.is_file():
        print("ERROR: .env file not found.", file=sys.stderr)
        return 2
    try:
        format_name, values, loaded = _load_settings(ENV_FILE)
    except (OSError, UnicodeError, ValueError):
        print("ERROR: .env must be valid dotenv or a legacy Azure JSON-array settings file; no files were changed.", file=sys.stderr)
        return 2
    model = values.get("AI_MODEL", "").lower()
    parsed = urlsplit(values.get("AI_BASE_URL", ""))
    is_openrouter = parsed.scheme == "https" and (parsed.hostname or "").lower().rstrip(".") in {"openrouter.ai", "www.openrouter.ai"}
    is_free_slug = model == "openrouter/free" or model.endswith(":free")
    provider = values.get("AI_PROVIDER", "").lower()
    if not values.get("AI_API_KEY"):
        print("ERROR: AI_API_KEY is empty; no files were changed.", file=sys.stderr)
        return 2
    if provider not in {"openai_compatible", "openai-compatible", "openai"}:
        print("ERROR: AI_PROVIDER is not an OpenAI-compatible provider; no files were changed.", file=sys.stderr)
        return 2
    if not is_openrouter or not is_free_slug:
        print("ERROR: AI_BASE_URL/AI_MODEL do not match a verified OpenRouter free-model configuration; no files were changed.", file=sys.stderr)
        return 2

    # This is a local-development helper, never a production deployment instruction.
    current_env = (values.get("APP_ENV") or os.environ.get("APP_ENV", "development")).strip().lower()
    current_db = (values.get("DATABASE_URL") or os.environ.get(
        "DATABASE_URL", "sqlite:///instance/food_ordering.sqlite3"
    )).strip().lower()
    if current_env not in {"development", "dev"} or not current_db.startswith("sqlite:"):
        print("ERROR: run this helper only for APP_ENV=development with a SQLite DATABASE_URL.", file=sys.stderr)
        return 2

    try:
        existing_budget = Decimal(values.get("AI_EXTERNAL_MONTHLY_BUDGET_USD") or "0")
    except (InvalidOperation, TypeError, ValueError):
        existing_budget = Decimal("0")
    if not existing_budget.is_finite() or existing_budget <= 0:
        existing_budget = Decimal("1.00")

    updates = {
        "AI_ENABLED": "true",
        "AI_EXTERNAL_ENABLED": "true",
        "AI_EXTERNAL_MONTHLY_BUDGET_USD": format(existing_budget, "f"),
        "AI_API_IS_FREE": "true",
        "AI_EXTERNAL_LOCAL_NOTICE_MODE": "true",
    }
    updated_text = _write_settings(format_name, loaded, updates)
    backup = ENV_FILE.with_name(f".env.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(ENV_FILE, backup)
    ENV_FILE.write_text(updated_text, encoding="utf-8", newline="\n")
    print("Updated local .env settings for the configured OpenRouter free model.")
    print(f"Backup created: {backup.name}")
    print("Restart Flask, apply database migrations if needed, then opt in using the customer AI consent checkbox.")
    print("This helper is for local SQLite development only; do not copy the local-notice flag into production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
