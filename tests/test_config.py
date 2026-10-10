import json
import os
from unittest.mock import patch

import pytest

from app.ai.core.provider import AIService, OpenAICompatibleProvider
from app.config import _env_bool, _env_int, _load_local_environment


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_env_bool_accepts_true_values(monkeypatch, value):
    monkeypatch.setenv("TEST_BOOLEAN", value)

    assert _env_bool("TEST_BOOLEAN") is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
def test_env_bool_accepts_false_values(monkeypatch, value):
    monkeypatch.setenv("TEST_BOOLEAN", value)

    assert _env_bool("TEST_BOOLEAN") is False


def test_env_bool_falls_back_and_warns_for_unknown_values(monkeypatch):
    monkeypatch.setenv("TEST_BOOLEAN", "maybe")

    with patch("app.config.logger.warning") as warning:
        assert _env_bool("TEST_BOOLEAN", default=True) is True
    warning.assert_called_once()
    assert "Invalid boolean value for %s" in warning.call_args.args[0]
    assert warning.call_args.args[1] == "TEST_BOOLEAN"




@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [("15", 15), (" 20 ", 20), ("not-a-number", 12), ("0", 12), ("999", 12)],
)
def test_env_int_uses_default_for_invalid_or_out_of_range_values(monkeypatch, raw_value, expected):
    monkeypatch.setenv("TEST_INTEGER", raw_value)
    assert _env_int("TEST_INTEGER", 12, minimum=1, maximum=100) == expected


def test_env_int_uses_default_when_missing_or_empty(monkeypatch):
    monkeypatch.delenv("TEST_INTEGER", raising=False)
    assert _env_int("TEST_INTEGER", 12, minimum=1, maximum=100) == 12
    monkeypatch.setenv("TEST_INTEGER", " ")
    assert _env_int("TEST_INTEGER", 12, minimum=1, maximum=100) == 12


def test_production_json_imports_only_direct_ai_settings_for_sqlite_development(
    tmp_path, monkeypatch,
):
    settings = [
        {"name": "APP_ENV", "value": "production"},
        {"name": "DATABASE_URL", "value": "postgresql://production/db"},
        {"name": "SECRET_KEY", "value": "production-secret"},
        {"name": "BREVO_API_KEY", "value": "production-mail-key"},
        {"name": "AI_ENABLED", "value": "true"},
        {"name": "AI_PROVIDER", "value": "openai_compatible"},
        {"name": "AI_API_KEY", "value": "direct-provider-test-key"},
        {"name": "AI_MODEL", "value": "direct-model"},
        {"name": "AI_BASE_URL", "value": "https://provider.example/v1"},
        {"name": "AI_LOCAL_ENABLED", "value": "true"},
        {"name": "AI_LOCAL_BASE_URL", "value": "https://private.example/v1"},
        {"name": "AI_EXTERNAL_ENABLED", "value": "false"},
        {"name": "AI_EXTERNAL_MONTHLY_BUDGET_USD", "value": "0"},
        {"name": "AI_API_INPUT_USD_PER_MILLION", "value": "0"},
        {"name": "AI_API_OUTPUT_USD_PER_MILLION", "value": "0"},
        {"name": "AI_API_IS_FREE", "value": "true"},
        {"name": "AI_EXTERNAL_LOCAL_NOTICE_MODE", "value": "true"},
    ]
    settings_path = tmp_path / ".env"
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AI_LOCAL_ENABLED", "true")
    for name in (
        "AI_ENABLED", "AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL",
        "AI_EXTERNAL_ENABLED", "AI_EXTERNAL_MONTHLY_BUDGET_USD",
        "AI_API_INPUT_USD_PER_MILLION", "AI_API_OUTPUT_USD_PER_MILLION",
        "AI_API_IS_FREE", "AI_EXTERNAL_LOCAL_NOTICE_MODE",
        "SECRET_KEY", "BREVO_API_KEY", "AI_LOCAL_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_LOCAL_ENABLED", "true")

    _load_local_environment(settings_path)

    assert os.environ["AI_ENABLED"] == "true"
    assert os.environ["AI_PROVIDER"] == "openai_compatible"
    assert os.environ["AI_API_KEY"] == "direct-provider-test-key"
    assert os.environ["AI_MODEL"] == "direct-model"
    assert os.environ["AI_BASE_URL"] == "https://provider.example/v1"
    assert os.environ["AI_LOCAL_ENABLED"] == "false"
    assert os.environ["AI_EXTERNAL_ENABLED"] == "false"
    assert os.environ["AI_EXTERNAL_MONTHLY_BUDGET_USD"] == "0"
    assert os.environ["AI_API_IS_FREE"] == "true"
    assert os.environ["AI_EXTERNAL_LOCAL_NOTICE_MODE"] == "true"
    service = AIService({
        "ENVIRONMENT": "development",
        "AI_ENABLED": os.environ["AI_ENABLED"].lower() == "true",
        "AI_PROVIDER": os.environ["AI_PROVIDER"],
        "AI_API_KEY": os.environ["AI_API_KEY"],
        "AI_MODEL": os.environ["AI_MODEL"],
        "AI_BASE_URL": os.environ["AI_BASE_URL"],
        "AI_LOCAL_ENABLED": os.environ["AI_LOCAL_ENABLED"].lower() == "true",
        "AI_EXTERNAL_ENABLED": os.environ["AI_EXTERNAL_ENABLED"].lower() == "true",
        "AI_EXTERNAL_MONTHLY_BUDGET_USD": os.environ["AI_EXTERNAL_MONTHLY_BUDGET_USD"],
    })
    assert service.local_enabled is False
    assert service.direct_provider is not None
    assert isinstance(service.provider, OpenAICompatibleProvider)
    assert "DATABASE_URL" not in os.environ
    assert "SECRET_KEY" not in os.environ
    assert "BREVO_API_KEY" not in os.environ
    assert "AI_LOCAL_BASE_URL" not in os.environ


@pytest.mark.parametrize(
    ("runtime_environment", "runtime_database_url"),
    [
        ("production", "postgresql://production/db"),
        ("development", "postgresql://production/db"),
    ],
)
def test_production_json_does_not_import_ai_settings_outside_local_sqlite(
    tmp_path, monkeypatch, runtime_environment, runtime_database_url,
):
    settings_path = tmp_path / ".env"
    settings_path.write_text(json.dumps([
        {"name": "APP_ENV", "value": "production"},
        {"name": "DATABASE_URL", "value": "postgresql://production/db"},
        {"name": "AI_ENABLED", "value": "true"},
        {"name": "AI_PROVIDER", "value": "openai_compatible"},
        {"name": "AI_API_KEY", "value": "direct-provider-test-key"},
        {"name": "AI_MODEL", "value": "direct-model"},
        {"name": "AI_BASE_URL", "value": "https://provider.example/v1"},
    ]), encoding="utf-8")
    monkeypatch.setenv("APP_ENV", runtime_environment)
    monkeypatch.setenv("DATABASE_URL", runtime_database_url)
    for name in ("AI_ENABLED", "AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    _load_local_environment(settings_path)

    assert all(name not in os.environ for name in (
        "AI_ENABLED", "AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL",
    ))
