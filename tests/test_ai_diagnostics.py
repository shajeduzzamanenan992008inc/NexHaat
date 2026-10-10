"""Configuration diagnostics must be useful without exposing credentials or probing automatically."""

import json

from scripts import diagnose_ai


def test_read_settings_supports_app_service_json_and_dotenv(tmp_path):
    path = tmp_path / ".env"
    path.write_text(json.dumps([
        {"name": "APP_ENV", "value": "development"},
        {"name": "AI_MODEL", "value": "test-model"},
    ]), encoding="utf-8")
    assert diagnose_ai._read_settings(path) == {
        "APP_ENV": "development", "AI_MODEL": "test-model",
    }

    path.write_text('AI_MODEL="test-model"\n# ignored\nAI_ENABLED=true\n', encoding="utf-8")
    assert diagnose_ai._read_settings(path) == {
        "AI_MODEL": "test-model", "AI_ENABLED": "true",
    }


def test_configuration_report_never_prints_api_secret(capsys):
    secret = "do-not-print-this-test-key"
    result = diagnose_ai._report({
        "APP_ENV": "development",
        "AI_ENABLED": "true",
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": secret,
        "AI_MODEL": "configured-test-model",
        "AI_BASE_URL": "https://provider.example/v1",
        "AI_LOCAL_ENABLED": "false",
        "AI_EXTERNAL_ENABLED": "false",
    })
    output = capsys.readouterr().out
    assert result["direct_ready"] is True
    assert secret not in output
    assert "provider.example" not in output


def test_external_fallback_remains_blocked_without_positive_budget(capsys):
    result = diagnose_ai._report({
        "APP_ENV": "development",
        "AI_LOCAL_ENABLED": "false",
        "AI_ENABLED": "true",
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": "synthetic-secret",
        "AI_MODEL": "configured-test-model",
        "AI_BASE_URL": "https://provider.example/v1",
        "AI_EXTERNAL_ENABLED": "true",
        "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0",
    })
    output = capsys.readouterr().out
    assert result["direct_ready"] is True
    assert result["external_ready"] is False
    assert "positive budget=False" in output
