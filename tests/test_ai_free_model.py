from app.ai.core.provider import _is_configured_openrouter_free_model


def test_openrouter_free_model_requires_explicit_flag_and_matching_host_slug():
    assert _is_configured_openrouter_free_model(
        "https://openrouter.ai/api/v1", "openrouter/free", True
    )
    assert _is_configured_openrouter_free_model(
        "https://openrouter.ai/api/v1", "provider/model:free", "true"
    )
    assert not _is_configured_openrouter_free_model(
        "https://openrouter.ai/api/v1", "openrouter/free", False
    )
    assert not _is_configured_openrouter_free_model(
        "https://not-openrouter.ai/api/v1", "openrouter/free", True
    )
    assert not _is_configured_openrouter_free_model(
        "http://openrouter.ai/api/v1", "openrouter/free", True
    )
    assert not _is_configured_openrouter_free_model(
        "https://openrouter.ai/api/v1", "openrouter/paid-model", True
    )


def test_openrouter_free_model_rejects_credentials_or_url_query():
    assert not _is_configured_openrouter_free_model(
        "https://user:pass@openrouter.ai/api/v1", "openrouter/free", True
    )
    assert not _is_configured_openrouter_free_model(
        "https://openrouter.ai/api/v1?target=other", "openrouter/free", True
    )


def test_local_sqlite_notice_mode_records_metadata_without_telegram(app, monkeypatch):
    from app.extensions import db
    from app.models import AIExternalCallNotice
    from app.services.ai_external_notices import (
        external_call_notice_delivered,
        external_call_notices_ready,
        record_external_call_notice,
    )

    with app.app_context():
        app.config.update(
            ENVIRONMENT="development",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            AI_EXTERNAL_LOCAL_NOTICE_MODE=True,
            TELEGRAM_SECURITY_BOT_TOKEN="",
            TELEGRAM_SECURITY_ADMIN_IDS="",
        )
        monkeypatch.setattr(
            "app.services.ai_external_notices.send_message",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Telegram must not be called")),
        )
        assert external_call_notices_ready(app.config)
        call_id = record_external_call_notice(
            config=app.config,
            provider="openai_compatible",
            model="openrouter/free",
            purpose="customer-fallback",
            estimated_cost_usd=0,
        )
        assert call_id
        assert db.session.get(AIExternalCallNotice, call_id) is not None
        assert external_call_notice_delivered(call_id)


def test_local_notice_mode_does_not_bypass_production_telegram_gate(app):
    from app.services.ai_external_notices import external_call_notices_ready

    with app.app_context():
        assert not external_call_notices_ready({
            "ENVIRONMENT": "production",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AI_EXTERNAL_LOCAL_NOTICE_MODE": True,
            "TELEGRAM_SECURITY_BOT_TOKEN": "",
            "TELEGRAM_SECURITY_ADMIN_IDS": "",
        })
