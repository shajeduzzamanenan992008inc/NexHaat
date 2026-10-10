"""Regression tests for dependency-free deployment validation scripts."""
import json
from pathlib import Path
import sys

import pytest

from scripts import smoke_test

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, status, headers=None):
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeOpener:
    def __init__(self, statuses=None, homepage_headers=None):
        self.statuses = statuses or {}
        self.homepage_headers = homepage_headers or {}

    def open(self, request, timeout):
        path = request.full_url.split("example.com", 1)[-1]
        headers = self.homepage_headers if path == "/" else {}
        return FakeResponse(self.statuses.get(path, 200), headers)


def test_env_template_validator_passes():
    import subprocess

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_env_example.py")],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "105 unique keys" in result.stdout


def test_azure_settings_example_is_unique_and_contains_only_secret_placeholders():
    settings = json.loads((ROOT / ".azure-app-settings.example.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in settings]
    assert len(names) == len(set(names))
    values = {item["name"]: item["value"] for item in settings}
    assert values["APP_ENV"] == "production"
    assert values["SESSION_COOKIE_SECURE"] == "1"
    assert values["TELEGRAM_CUSTOMER_BOT_TOKEN"] == ""
    assert values["AI_OPENAI_API_KEY"] == ""
    assert values["SSLCOMMERZ_STORE_PASSWORD"] == ""


def test_smoke_test_rejects_public_http(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["smoke_test.py", "--base-url", "http://example.com"])
    assert smoke_test.main() == 2


def test_smoke_test_passes_successful_https_readiness_and_headers(monkeypatch, capsys):
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }
    monkeypatch.setattr(sys, "argv", ["smoke_test.py", "--base-url", "https://example.com"])
    monkeypatch.setattr(smoke_test, "build_opener", lambda *_args: FakeOpener(homepage_headers=headers))
    assert smoke_test.main() == 0
    assert "Smoke test PASSED" in capsys.readouterr().out


def test_smoke_test_fails_if_database_readiness_is_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["smoke_test.py", "--base-url", "https://example.com"])
    monkeypatch.setattr(
        smoke_test, "build_opener",
        lambda *_args: FakeOpener(statuses={"/health/ready": 503}, homepage_headers={
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
        }),
    )
    assert smoke_test.main() == 1
    assert "FAIL /health/ready: HTTP 503" in capsys.readouterr().out
