#!/usr/bin/env python3
"""Safely diagnose NexHaat AI configuration without printing credentials.

This command never makes a network request unless --probe-local or --probe-direct
is explicitly selected. Provider responses and URLs are not printed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TRUE_VALUES = {"1", "true", "yes", "on"}
SUPPORTED_DIRECT = {"openai_compatible", "openai-compatible", "openai"}


def _truthy(value, default=False):
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return default


def _decimal(value):
    try:
        number = Decimal(str(value or "0").strip())
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    return number if number.is_finite() else Decimal("0")


def _read_settings(path: Path) -> dict[str, str]:
    """Read only .env, supporting ordinary KEY=VALUE or App Service JSON-array format."""
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        values: dict[str, str] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[name] = value
        return values
    if isinstance(document, list):
        return {
            item["name"]: str(item.get("value") or "")
            for item in document
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item["name"])
        }
    return {}


def _effective_settings() -> dict[str, str]:
    file_values = _read_settings(ENV_FILE)
    # The application intentionally accepts an App Service JSON export locally only
    # when it declares development + SQLite, except for its tightly allowlisted
    # direct-provider settings path. Mirror that behavior to avoid false positives.
    use_file_values = True
    try:
        raw = ENV_FILE.read_text(encoding="utf-8-sig") if ENV_FILE.is_file() else ""
        document = json.loads(raw) if raw else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        document = None
    if isinstance(document, list):
        file_environment = str(file_values.get("APP_ENV") or "").strip().lower()
        file_db = str(file_values.get("DATABASE_URL") or "").strip()
        file_db_backend = urlsplit(file_db).scheme.split("+", 1)[0].lower()
        runtime_environment = str(os.environ.get("APP_ENV") or "development").strip().lower()
        runtime_db = str(os.environ.get("DATABASE_URL") or f"sqlite:///{ROOT / 'instance' / 'food_ordering.sqlite3'}")
        runtime_db_backend = urlsplit(runtime_db).scheme.split("+", 1)[0].lower()
        active_environment = str(os.environ.get("APP_ENV") or file_environment).strip().lower()
        active_db = str(os.environ.get("DATABASE_URL") or file_db)
        active_db_backend = urlsplit(active_db).scheme.split("+", 1)[0].lower()
        accepted_development_json = (
            file_environment == "development" and file_db_backend == "sqlite"
            and active_environment == "development" and active_db_backend == "sqlite"
        )
        direct_is_configured = (
            _truthy(file_values.get("AI_ENABLED"), False)
            and str(file_values.get("AI_PROVIDER") or "").strip().lower() in SUPPORTED_DIRECT
            and all(str(file_values.get(key) or "").strip() for key in ("AI_API_KEY", "AI_MODEL", "AI_BASE_URL"))
        )
        allowlisted_production_direct = (
            file_environment == "production" and runtime_environment == "development"
            and runtime_db_backend == "sqlite" and direct_is_configured
        )
        if accepted_development_json:
            use_file_values = True
        elif allowlisted_production_direct:
            allowed = {
                "AI_ENABLED", "AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL",
                "AI_TIMEOUT", "AI_MAX_TOKENS", "AI_EXTERNAL_ENABLED",
                "AI_EXTERNAL_MONTHLY_BUDGET_USD", "AI_API_INPUT_USD_PER_MILLION",
                "AI_API_OUTPUT_USD_PER_MILLION", "AI_API_IS_FREE", "AI_EXTERNAL_LOCAL_NOTICE_MODE",
            }
            file_values = {key: value for key, value in file_values.items() if key in allowed}
            file_values["AI_LOCAL_ENABLED"] = "false"
            use_file_values = True
        else:
            use_file_values = False
    if not use_file_values:
        file_values = {}
    keys = set(file_values) | set(os.environ)
    # Process environment overrides accepted .env values, matching dotenv's normal behavior.
    return {key: os.environ.get(key, file_values.get(key, "")) for key in keys}


def _valid_http_base(value, *, production=False):
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in ({"https"} if production else {"http", "https"}):
        return False
    if not parsed.hostname or parsed.username or parsed.password:
        return False
    return True


def _specialist_ready(settings, prefix):
    return bool(
        settings.get(f"{prefix}_API_KEY", "").strip()
        and settings.get(f"{prefix}_MODEL", "").strip()
        and _valid_http_base(settings.get(f"{prefix}_BASE_URL"), production=False)
        and _decimal(settings.get(f"{prefix}_INPUT_USD_PER_MILLION")) > 0
        and _decimal(settings.get(f"{prefix}_OUTPUT_USD_PER_MILLION")) > 0
    )


def _report(settings):
    environment = (settings.get("APP_ENV") or "development").strip().lower()
    production = environment == "production"
    local_enabled = _truthy(settings.get("AI_LOCAL_ENABLED"), True)
    local_url = settings.get("AI_LOCAL_BASE_URL", "").strip()
    local_model = settings.get("AI_LOCAL_MODEL", "").strip()
    local_ready = local_enabled and bool(local_url and local_model and _valid_http_base(local_url, production=production))

    ai_enabled = _truthy(settings.get("AI_ENABLED"), False)
    direct_provider = (settings.get("AI_PROVIDER") or "disabled").strip().lower()
    direct_key = bool(settings.get("AI_API_KEY", "").strip())
    direct_model = bool(settings.get("AI_MODEL", "").strip())
    direct_url = settings.get("AI_BASE_URL", "").strip()
    direct_ready = (
        ai_enabled and direct_provider in SUPPORTED_DIRECT and direct_key and direct_model
        and _valid_http_base(direct_url, production=production)
    )
    is_openrouter_free = (
        (urlsplit(direct_url).hostname or "").lower().rstrip(".") in {"openrouter.ai", "www.openrouter.ai"}
        and (settings.get("AI_MODEL", "").strip().lower() == "openrouter/free"
             or settings.get("AI_MODEL", "").strip().lower().endswith(":free"))
        and _truthy(settings.get("AI_API_IS_FREE"), False)
    )

    external_enabled = _truthy(settings.get("AI_EXTERNAL_ENABLED"), False)
    budget_ok = _decimal(settings.get("AI_EXTERNAL_MONTHLY_BUDGET_USD")) > 0
    specialist_prefixes = ("AI_OPENAI", "AI_ANTHROPIC", "AI_GEMINI", "AI_DEEPSEEK")
    ready_specialists = [p.removeprefix("AI_").lower() for p in specialist_prefixes if _specialist_ready(settings, p)]
    direct_external_ready = direct_ready and budget_ok and (is_openrouter_free or (
        _decimal(settings.get("AI_API_INPUT_USD_PER_MILLION")) > 0
        and _decimal(settings.get("AI_API_OUTPUT_USD_PER_MILLION")) > 0
    ))
    external_ready = external_enabled and budget_ok and bool(ready_specialists or direct_external_ready)

    if production:
        notice_ready = bool(
            settings.get("TELEGRAM_SECURITY_BOT_TOKEN", "").strip()
            and settings.get("TELEGRAM_SECURITY_ADMIN_IDS", "").strip()
        )
    else:
        # Local notice persistence is deliberately limited to opted-in SQLite development.
        database = (settings.get("DATABASE_URL") or f"sqlite:///{ROOT / 'instance' / 'food_ordering.sqlite3'}").lower()
        notice_ready = _truthy(settings.get("AI_EXTERNAL_LOCAL_NOTICE_MODE"), False) and database.startswith("sqlite:")

    print("NexHaat AI configuration check (secrets are never displayed)")
    print(f"Config source: {'.env found' if ENV_FILE.is_file() else 'no .env file; process environment only'}")
    if not ENV_FILE.is_file() and (ROOT / ".env.example").is_file():
        print("NOTE: .env.example is a template, not an active configuration file.")
    print(f"Runtime environment: {environment}")
    print(f"Local AI: {'READY' if local_ready else 'not ready'} (enabled={local_enabled}, URL={'set' if local_url else 'missing'}, model={'set' if local_model else 'missing'})")
    print(f"Direct API: {'READY' if direct_ready else 'not ready'} (enabled={ai_enabled}, provider={direct_provider if direct_provider in SUPPORTED_DIRECT else 'unsupported/disabled'}, key={'set' if direct_key else 'missing'}, model={'set' if direct_model else 'missing'}, URL={'valid' if _valid_http_base(direct_url, production=production) else 'missing/invalid'})")
    print(f"External fallback: {'READY to evaluate consent/budget/notice gates' if external_ready else 'BLOCKED or incomplete'} (enabled={external_enabled}, positive budget={budget_ok}, ready specialists={len(ready_specialists)})")
    print(f"External-call notice path: {'configured' if notice_ready else 'not configured'}")

    blockers = []
    if not local_ready:
        blockers.append("Set AI_LOCAL_BASE_URL and AI_LOCAL_MODEL for local-first inference, or explicitly configure a supported direct provider.")
    if not direct_ready and not ready_specialists:
        blockers.append("No complete direct/specialist API provider is configured; an API key alone is not enough.")
    if not external_enabled:
        blockers.append("AI_EXTERNAL_ENABLED is false, so external fallback calls are intentionally disabled.")
    if external_enabled and not budget_ok:
        blockers.append("AI_EXTERNAL_MONTHLY_BUDGET_USD must be positive for paid external fallback.")
    if external_ready and not notice_ready:
        blockers.append("External calls are still blocked until the required metadata-only notice path is configured.")
    if blockers:
        print("\nLikely blockers:")
        for item in dict.fromkeys(blockers):
            print(f"- {item}")
    else:
        print("\nStatic configuration looks complete; this does not prove the model endpoint or key works.")
    print("Note: customer external-AI consent and request-specific safety/data gates still apply at runtime.")
    return {"local_ready": local_ready, "direct_ready": direct_ready,
            "external_ready": external_ready, "notice_ready": notice_ready}


def _probe(settings, *, local=False):
    try:
        import requests
    except ImportError:
        print("Probe unavailable: install the project's requirements first.")
        return 2

    if local:
        base_url = settings.get("AI_LOCAL_BASE_URL", "").strip()
        model = settings.get("AI_LOCAL_MODEL", "").strip()
        key = settings.get("AI_LOCAL_API_KEY", "").strip()
        label = "Local AI"
    else:
        base_url = settings.get("AI_BASE_URL", "").strip()
        model = settings.get("AI_MODEL", "").strip()
        key = settings.get("AI_API_KEY", "").strip()
        label = "Direct API"
    production = (settings.get("APP_ENV") or "development").strip().lower() == "production"
    if not model or not _valid_http_base(base_url, production=production):
        print(f"{label} probe not sent: model or valid provider URL is missing.")
        return 2
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only the word READY."},
            {"role": "user", "content": "Connection test."},
        ],
        "max_tokens": 12,
        "stream": False,
    }
    print(f"Sending one minimal test request to the configured {label}; the provider may charge for it.")
    try:
        response = requests.post(
            base_url.rstrip("/") + "/chat/completions",
            headers=headers, json=payload, timeout=8,
        )
        if response.ok:
            try:
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                if isinstance(content, str) and content.strip():
                    print(f"{label} probe: HTTP {response.status_code}, non-empty model response.")
                    return 0
            except (ValueError, KeyError, IndexError, TypeError):
                pass
            print(f"{label} probe: HTTP {response.status_code}, but response shape was unexpected.")
            return 1
        print(f"{label} probe failed: HTTP {response.status_code}. Response body was not printed.")
        return 1
    except requests.RequestException as error:
        print(f"{label} probe failed: {type(error).__name__}. Endpoint details were not printed.")
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    probes = parser.add_mutually_exclusive_group()
    probes.add_argument("--probe-local", action="store_true", help="send one minimal request to the configured local endpoint")
    probes.add_argument("--probe-direct", action="store_true", help="send one minimal request to the configured direct API (may incur charges)")
    args = parser.parse_args(argv)

    settings = _effective_settings()
    _report(settings)
    if args.probe_local:
        return _probe(settings, local=True)
    if args.probe_direct:
        return _probe(settings, local=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
