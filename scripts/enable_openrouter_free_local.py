#!/usr/bin/env python3
"""Enable a verified OpenRouter free model for this project's local SQLite development run.

The script edits the Azure App Service JSON-array format in .env. It will not edit a
plain dotenv file, and it never prints API keys or other credential values. Production
must use Telegram Security Bot notices and must not enable the local notice mode.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main() -> int:
    if not ENV_FILE.is_file():
        print("ERROR: .env file not found.", file=sys.stderr)
        return 2
    try:
        entries = json.loads(ENV_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("ERROR: .env must use the Azure App Service JSON-array format; no files were changed.", file=sys.stderr)
        return 2
    if not isinstance(entries, list) or not all(isinstance(item, dict) and isinstance(item.get("name"), str) for item in entries):
        print("ERROR: .env is not a valid JSON array of {name, value} settings; no files were changed.", file=sys.stderr)
        return 2

    values = {item["name"]: str(item.get("value") or "").strip() for item in entries}
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
    current_env = os.environ.get("APP_ENV", "development").strip().lower()
    current_db = os.environ.get("DATABASE_URL", "sqlite:///instance/food_ordering.sqlite3").strip().lower()
    if current_env not in {"development", "dev"} or not current_db.startswith("sqlite:"):
        print("ERROR: run this helper only for APP_ENV=development with a SQLite DATABASE_URL.", file=sys.stderr)
        return 2

    by_name = {item["name"]: item for item in entries}
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
    for name, value in updates.items():
        if name in by_name:
            by_name[name]["value"] = value
        else:
            item = {"name": name, "value": value, "slotSetting": False}
            entries.append(item)
            by_name[name] = item

    backup = ENV_FILE.with_name(f".env.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(ENV_FILE, backup)
    ENV_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("Updated local .env settings for the configured OpenRouter free model.")
    print(f"Backup created: {backup.name}")
    print("Restart Flask, apply database migrations if needed, then opt in using the customer AI consent checkbox.")
    print("This helper is for local SQLite development only; do not copy the local-notice flag into production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
