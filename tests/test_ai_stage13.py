from decimal import Decimal

from flask import current_app

from app.ai.core.consent import external_consent_enabled, set_external_consent
from app.ai.core.permissions import (
    AI_SCOPE_ADMIN, AI_SCOPE_CUSTOMER, AI_SCOPE_RIDER, AI_SCOPE_SECURITY, AI_SCOPE_SELLER,
)
from app.ai.core.provider import AIService
from app.ai.core.external_budget import reserve_external_budget
from app.ai.core.guardrails import redact_external_prompt
from app.ai.core.knowledge import retrieve_knowledge
from app.ai.core.tools import ToolRegistry
from app.ai.marketplace_tools import handle_marketplace_ai_query
from app.ai.rider_tools import build_rider_tool_registry
from app.extensions import db
from app.models import (
    AIExternalCallNotice, AIExternalCallRecipient, AIExternalConsent,
    AIExternalSpend, AIKnowledgeChunk, AIPreferences, AIUserMemory, Order,
    RiderProfile, User,
)


def _user(role, suffix):
    user = User(email=f"{role}-{suffix}@example.test", role=role)
    user.set_password("test-password")
    db.session.add(user)
    db.session.flush()
    return user


def _provider_spec(rate="1"):
    return {"api_key": "fake-key", "model": "configured-model",
            "base_url": "https://provider.example.test/v1",
            "input_rate": rate, "output_rate": rate}


def test_local_core_answers_when_external_ai_is_disabled(app):
    class LocalModel:
        def generate(self, **kwargs):
            return {"content": "বাংলায় উত্তর এবং Python উদাহরণ।", "tool_calls": []}

    with app.app_context():
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "Qwen/Qwen3.5-9B", "AI_EXTERNAL_ENABLED": False,
                  "AI_ENABLED": False, "AI_MAX_TOOL_CALLS": 0}
        result = AIService(config, provider=LocalModel()).respond(
            "Explain recursion and show Python code", scope=AI_SCOPE_CUSTOMER,
        )
    assert result["ok"] is True
    assert result["answer"].startswith("বাংলায়")
    assert result["external_assistance"] is False


def test_external_specialists_require_consent_and_monthly_budget(app, monkeypatch):
    calls = []
    requested_limits = []

    class LocalModel:
        def __init__(self):
            self.calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"content": "Local draft answer", "tool_calls": []}
            return {"content": "One fused and cautious answer", "tool_calls": []}

    class Expert:
        def __init__(self, name):
            self.name = name

        def generate(self, **kwargs):
            requested_limits.append(kwargs["max_tokens"])
            notice = AIExternalCallNotice.query.filter_by(provider=self.name).one()
            assert notice.status == "started"
            assert notice.recipients[0].status == "sent"
            return {"content": f"Candidate answer from {self.name}", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider._specialist_provider",
                        lambda name, spec, timeout: (calls.append(name) or Expert(name)))
    with app.app_context():
        user = _user("customer", "stage13-consent")
        specs = {name: _provider_spec() for name in ("openai", "anthropic", "gemini")}
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "Qwen/Qwen3.5-9B", "AI_EXTERNAL_ENABLED": True,
                  "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05", "AI_EXTERNAL_MAX_TOKENS": 8192,
                  "AI_SPECIALISTS": specs, "AI_MAX_TOOL_CALLS": 0,
                  "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
                  "TELEGRAM_SECURITY_ADMIN_IDS": "9001"}
        app.config.update({key: config[key] for key in (
            "TELEGRAM_SECURITY_BOT_TOKEN", "TELEGRAM_SECURITY_ADMIN_IDS",
        )})
        monkeypatch.setattr("app.services.ai_external_notices.send_message",
                            lambda *_args: True)
        model = LocalModel()
        prompt = "Please debug and implement a careful Python code example for a complex data pipeline."
        denied = AIService(config, provider=model).respond(prompt, scope=AI_SCOPE_CUSTOMER,
                                                           user=user, allow_external=False)
        assert denied["ok"] and not denied["external_assistance"]
        assert calls == []

        set_external_consent(True, user=user)
        assert external_consent_enabled(user=user)
        allowed = AIService(config, provider=model).respond(prompt, scope=AI_SCOPE_CUSTOMER,
                                                            user=user, allow_external=True)
        assert allowed["ok"] and allowed["external_assistance"]
        assert allowed["answer"] == "One fused and cautious answer"
        assert len(calls) == 2
        assert requested_limits == [1024, 1024]
        assert AIExternalCallNotice.query.count() == 2
        assert AIExternalCallRecipient.query.filter_by(status="sent").count() == 2
        assert AIExternalSpend.query.one().reserved_usd > 0
        consent = AIExternalConsent.query.one()
        assert len(consent.principal_hash) == 64
        assert consent.principal_hash != user.email


def test_configured_api_is_local_failure_fallback_only_after_consent_and_budget(app, monkeypatch):
    direct_calls = []

    class FailedLocalModel:
        def generate(self, **kwargs):
            raise RuntimeError("private local endpoint is unavailable")

    class DirectAPI:
        def generate(self, **kwargs):
            direct_calls.append(kwargs)
            return {"content": "A safe general answer from the API.", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider.AIService._build_direct_provider",
                        lambda _service: DirectAPI())
    monkeypatch.setattr("app.services.ai_external_notices.send_message",
                        lambda *_args: True)
    with app.app_context():
        user = _user("customer", "local-api-fallback")
        config = {
            "AI_LOCAL_ENABLED": True,
            "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
            "AI_LOCAL_MODEL": "local-model",
            "AI_ENABLED": True,
            "AI_PROVIDER": "openai_compatible",
            "AI_API_KEY": "api-test-key",
            "AI_MODEL": "api-model",
            "AI_BASE_URL": "https://api.example.test/v1",
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05",
            "AI_API_INPUT_USD_PER_MILLION": "1",
            "AI_API_OUTPUT_USD_PER_MILLION": "1",
            "AI_SPECIALISTS": {},
            "AI_MAX_TOOL_CALLS": 0,
            "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
            "TELEGRAM_SECURITY_ADMIN_IDS": "9001",
        }
        app.config.update({
            "TELEGRAM_SECURITY_BOT_TOKEN": config["TELEGRAM_SECURITY_BOT_TOKEN"],
            "TELEGRAM_SECURITY_ADMIN_IDS": config["TELEGRAM_SECURITY_ADMIN_IDS"],
        })

        denied = AIService(config, provider=FailedLocalModel()).respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )
        assert denied["ok"] is False
        assert direct_calls == []

        set_external_consent(True, user=user)
        no_budget_config = {**config, "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0"}
        no_budget = AIService(no_budget_config, provider=FailedLocalModel()).respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )
        assert no_budget["ok"] is False
        assert direct_calls == []

        allowed = AIService(config, provider=FailedLocalModel()).respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )
        assert allowed["ok"] is True
        assert allowed["provider"] == "openai_compatible-fallback"
        assert allowed["external_assistance"] is True
        assert allowed["answer"] == "A safe general answer from the API."

        class EmptyLocalModel:
            def generate(self, **kwargs):
                return {"content": "", "tool_calls": []}

        empty_local = AIService(config, provider=EmptyLocalModel()).respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )
        assert empty_local["ok"] is True
        assert empty_local["provider"] == "openai_compatible-fallback"
        assert empty_local["fallback_used"] is True
        assert empty_local["external_assistance"] is True
        assert empty_local["answer"] == "A safe general answer from the API."
        assert len(direct_calls) == 2
        assert direct_calls[0]["model"] == "api-model"
        assert direct_calls[0]["messages"][-1]["content"] == "Explain recursion"
        assert len(direct_calls[0]["messages"]) == 2
        assert AIExternalCallNotice.query.count() == 2
        assert AIExternalCallRecipient.query.filter_by(status="sent").count() == 2
        assert AIExternalSpend.query.one().reserved_usd > 0


def test_single_configured_specialist_answers_when_local_endpoint_is_missing(app, monkeypatch):
    specialist_calls = []

    class Specialist:
        def generate(self, **kwargs):
            specialist_calls.append(kwargs)
            notice = AIExternalCallNotice.query.filter_by(provider="openai").one()
            assert notice.status == "started"
            assert notice.recipients[0].status == "sent"
            return {"content": "A cautious answer from the configured specialist.", "tool_calls": []}

    monkeypatch.setattr(
        "app.ai.core.provider._specialist_provider",
        lambda name, _spec, _timeout: Specialist(),
    )
    monkeypatch.setattr("app.services.ai_external_notices.send_message",
                        lambda *_args: True)
    with app.app_context():
        user = _user("customer", "single-specialist-fallback")
        set_external_consent(True, user=user)
        config = {
            "AI_LOCAL_ENABLED": True,
            "AI_LOCAL_BASE_URL": "",
            "AI_LOCAL_MODEL": "",
            "AI_ENABLED": False,
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05",
            "AI_EXTERNAL_MAX_TOKENS": 256,
            "AI_SPECIALISTS": {"openai": _provider_spec()},
            "AI_MAX_TOOL_CALLS": 0,
            "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
            "TELEGRAM_SECURITY_ADMIN_IDS": "9001",
        }
        app.config.update({
            "TELEGRAM_SECURITY_BOT_TOKEN": config["TELEGRAM_SECURITY_BOT_TOKEN"],
            "TELEGRAM_SECURITY_ADMIN_IDS": config["TELEGRAM_SECURITY_ADMIN_IDS"],
        })

        result = AIService(config).respond(
            "Explain recursion in simple terms",
            scope=AI_SCOPE_CUSTOMER,
            user=user,
        )

        assert result["ok"] is True
        assert result["provider"] == "openai-fallback"
        assert result["answer"] == "A cautious answer from the configured specialist."
        assert result["external_assistance"] is True
        assert len(specialist_calls) == 1
        assert len(specialist_calls[0]["messages"]) == 2
        assert AIExternalCallNotice.query.count() == 1
        assert AIExternalSpend.query.one().reserved_usd > 0


def test_external_fallback_never_handles_customer_marketplace_facts(app, monkeypatch):
    external_calls = []

    class ExternalProvider:
        def generate(self, **kwargs):
            external_calls.append(kwargs)
            return {"content": "Unverified product answer.", "tool_calls": []}

    monkeypatch.setattr(
        "app.ai.core.provider._specialist_provider",
        lambda *_args: ExternalProvider(),
    )
    monkeypatch.setattr("app.services.ai_external_notices.send_message",
                        lambda *_args: True)
    monkeypatch.setattr(
        "app.ai.core.provider.AIService._build_direct_provider",
        lambda _service: ExternalProvider(),
    )
    with app.app_context():
        user = _user("customer", "marketplace-fallback-boundary")
        set_external_consent(True, user=user)
        config = {
            "AI_LOCAL_ENABLED": True,
            "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
            "AI_LOCAL_MODEL": "local-model",
            "AI_ENABLED": True,
            "AI_PROVIDER": "openai_compatible",
            "AI_API_KEY": "api-test-key",
            "AI_MODEL": "api-model",
            "AI_BASE_URL": "https://api.example.test/v1",
            "AI_API_INPUT_USD_PER_MILLION": "1",
            "AI_API_OUTPUT_USD_PER_MILLION": "1",
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05",
            "AI_SPECIALISTS": {"openai": _provider_spec()},
            "AI_MAX_TOOL_CALLS": 0,
            "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
            "TELEGRAM_SECURITY_ADMIN_IDS": "9001",
        }
        app.config.update({
            "TELEGRAM_SECURITY_BOT_TOKEN": config["TELEGRAM_SECURITY_BOT_TOKEN"],
            "TELEGRAM_SECURITY_ADMIN_IDS": config["TELEGRAM_SECURITY_ADMIN_IDS"],
        })
        class FailedLocalModel:
            def generate(self, **kwargs):
                raise RuntimeError("local unavailable")

        result = AIService(config, provider=FailedLocalModel()).respond(
            "Show Samsung phones under BDT 30000",
            scope=AI_SCOPE_CUSTOMER,
            user=user,
            context={"allow_external_fallback": False},
            allow_external=True,
        )

        assert result["ok"] is False
        assert external_calls == []
        assert AIExternalCallNotice.query.count() == 0


def test_local_response_remains_primary_when_direct_api_is_configured(monkeypatch):
    direct_calls = []

    class LocalModel:
        def generate(self, **kwargs):
            return {"content": "The private local answer.", "tool_calls": []}

    class DirectAPI:
        def generate(self, **kwargs):
            direct_calls.append(kwargs)
            return {"content": "This should not be used.", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider.AIService._build_direct_provider",
                        lambda _service: DirectAPI())
    config = {
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
        "AI_LOCAL_MODEL": "local-model",
        "AI_ENABLED": True,
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": "api-test-key",
        "AI_MODEL": "api-model",
        "AI_BASE_URL": "https://api.example.test/v1",
        "AI_EXTERNAL_ENABLED": True,
    }

    result = AIService(config, provider=LocalModel()).respond(
        "Explain recursion", scope=AI_SCOPE_CUSTOMER, allow_external=True,
    )

    assert result["ok"] is True
    assert result["answer"] == "The private local answer."
    assert result["external_assistance"] is False
    assert direct_calls == []


def test_missing_local_endpoint_does_not_make_api_an_ungated_primary(app, monkeypatch):
    direct_calls = []

    class DirectAPI:
        def generate(self, **kwargs):
            direct_calls.append(kwargs)
            return {"content": "Paid fallback answer.", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider.AIService._build_direct_provider",
                        lambda _service: DirectAPI())
    monkeypatch.setattr("app.services.ai_external_notices.send_message",
                        lambda *_args: True)
    with app.app_context():
        user = _user("customer", "missing-local-endpoint")
        config = {
            "AI_LOCAL_ENABLED": True,
            "AI_LOCAL_BASE_URL": "",
            "AI_LOCAL_MODEL": "",
            "AI_ENABLED": True,
            "AI_PROVIDER": "openai_compatible",
            "AI_API_KEY": "api-test-key",
            "AI_MODEL": "api-model",
            "AI_BASE_URL": "https://api.example.test/v1",
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05",
            "AI_API_INPUT_USD_PER_MILLION": "1",
            "AI_API_OUTPUT_USD_PER_MILLION": "1",
            "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
            "TELEGRAM_SECURITY_ADMIN_IDS": "9001",
        }
        app.config.update({
            "TELEGRAM_SECURITY_BOT_TOKEN": config["TELEGRAM_SECURITY_BOT_TOKEN"],
            "TELEGRAM_SECURITY_ADMIN_IDS": config["TELEGRAM_SECURITY_ADMIN_IDS"],
        })

        blocked = AIService(config).respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )
        assert blocked["ok"] is False
        assert direct_calls == []

        set_external_consent(True, user=user)
        allowed = AIService(config).respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )
        assert allowed["ok"] is True
        assert allowed["provider"] == "openai_compatible-fallback"
        assert len(direct_calls) == 1


def test_configured_external_failure_returns_clear_error_without_provider_details(
    app, monkeypatch,
):
    class FailedSpecialist:
        def generate(self, **kwargs):
            raise RuntimeError("provider body and private endpoint must not escape")

    monkeypatch.setattr(
        "app.ai.core.provider._specialist_provider",
        lambda *_args, **_kwargs: FailedSpecialist(),
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.send_message",
        lambda *_args: True,
    )
    with app.app_context():
        user = _user("customer", "external-fallback-failure")
        set_external_consent(True, user=user)
        config = {
            "AI_LOCAL_ENABLED": True,
            "AI_LOCAL_BASE_URL": "",
            "AI_LOCAL_MODEL": "",
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05",
            "AI_EXTERNAL_MAX_TOKENS": 128,
            "AI_SPECIALISTS": {"openai": _provider_spec()},
            "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
            "TELEGRAM_SECURITY_ADMIN_IDS": "9001",
        }
        app.config.update({
            "TELEGRAM_SECURITY_BOT_TOKEN": config["TELEGRAM_SECURITY_BOT_TOKEN"],
            "TELEGRAM_SECURITY_ADMIN_IDS": config["TELEGRAM_SECURITY_ADMIN_IDS"],
        })

        result = AIService(config).respond(
            "Explain recursion in simple terms",
            scope=AI_SCOPE_CUSTOMER,
            user=user,
        )

    assert result["ok"] is False
    assert "AI Core is temporarily unavailable" in result["fallback"]
    assert "external fallback could not complete" in result["fallback"]
    assert "provider body" not in result["fallback"]
    assert "provider.example.test" not in result["fallback"]


def test_budget_exhaustion_prevents_external_requests(app):
    with app.app_context():
        specs = [_provider_spec(rate="1000"), _provider_spec(rate="1000")]
        config = {"AI_EXTERNAL_ENABLED": True, "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.01",
                  "AI_SPECIALISTS": {"openai": specs[0], "anthropic": specs[1]}}
        assert reserve_external_budget(config, specs) is False
        assert AIExternalSpend.query.count() == 0


def test_external_prompt_redacts_credentials_and_search_rejects_plain_http():
    text = redact_external_prompt(
        "Please debug using api_key=sk-abcdefghijklmnopqrstuvwxyz012345 "
        "and Telegram token 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmno"
    )
    assert "sk-abcdefghijklmnopqrstuvwxyz012345" not in text
    assert "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmno" not in text

    from app.ai.core.search import _public_http_url
    from app.ai.core.search import needs_live_sources
    from app.ai.core.provider import _needs_fresh_answer
    assert _public_http_url("https://public.example.test/reference")
    assert not _public_http_url("http://public.example.test/reference")
    assert not _public_http_url("https://127.0.0.1/private")
    for prompt in ("Give me the latest link", "আজকের সূত্র দাও", "link dao latest", "आज का स्रोत लिंक"):
        assert needs_live_sources(prompt)
        assert _needs_fresh_answer(prompt)


def test_local_tts_stream_is_bounded_and_not_cached(client, app, monkeypatch):
    class SpeechResponse:
        def __init__(self, chunks, content_type="audio/wav"):
            self.chunks = chunks
            self.closed = False
            self.headers = {"Content-Type": content_type}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size == 64 * 1024
            yield from self.chunks

        def close(self):
            self.closed = True

    response = SpeechResponse([b"RIFF", b"wav bytes"])
    calls = {}

    def post(url, **kwargs):
        calls.update(url=url, kwargs=kwargs)
        return response

    monkeypatch.setattr("requests.post", post)
    app.config.update(AI_TTS_BASE_URL="https://voice.internal/v1", AI_TTS_MODEL="cosyvoice")
    result = client.post("/ai/speak", json={"text": "বাংলায় উত্তর"})
    assert result.status_code == 200
    assert result.data == b"RIFFwav bytes"
    assert result.headers["Cache-Control"] == "no-store"
    assert calls["kwargs"]["stream"] is True
    assert "Authorization" not in calls["kwargs"]["headers"]
    assert response.closed

    oversized = SpeechResponse([b"x" * (10 * 1024 * 1024 + 1)])
    monkeypatch.setattr("requests.post", lambda _url, **_kwargs: oversized)
    rejected = client.post("/ai/speak", json={"text": "Short answer"})
    assert rejected.status_code == 503
    assert oversized.closed

    invalid_type = SpeechResponse([b"<html>Not audio</html>"], "audio/html")
    monkeypatch.setattr("requests.post", lambda _url, **_kwargs: invalid_type)
    invalid = client.post("/ai/speak", json={"text": "Short answer"})
    assert invalid.status_code == 503
    assert invalid_type.closed


def test_security_scope_never_uses_specialist_provider(app, monkeypatch):
    calls = []

    class LocalModel:
        def generate(self, **kwargs):
            return {"content": "Read-only security explanation.", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider._specialist_provider",
                        lambda *args: calls.append(args))
    with app.app_context():
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "local", "AI_EXTERNAL_ENABLED": True,
                  "AI_EXTERNAL_MONTHLY_BUDGET_USD": "2",
                  "AI_SPECIALISTS": {name: _provider_spec() for name in ("openai", "anthropic", "gemini")},
                  "AI_MAX_TOOL_CALLS": 0}
        result = AIService(config, provider=LocalModel()).respond(
            "Explain how to detect suspicious login attempts", scope=AI_SCOPE_SECURITY,
            allow_external=True,
        )
    assert result["ok"] is True
    assert calls == []


def test_rider_complex_general_question_requires_consent_for_specialists(app, monkeypatch):
    calls = []

    class LocalModel:
        def __init__(self):
            self.calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"content": "Local coding explanation", "tool_calls": []}
            return {"content": "Fused local and specialist coding explanation", "tool_calls": []}

    class Expert:
        def generate(self, **kwargs):
            return {"content": "An independent coding explanation", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider._specialist_provider",
                        lambda name, spec, timeout: (calls.append(name) or Expert()))
    with app.app_context():
        rider = _user("rider", "stage13-external")
        specs = {name: _provider_spec() for name in ("openai", "anthropic", "gemini")}
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "local", "AI_EXTERNAL_ENABLED": True,
                  "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05", "AI_EXTERNAL_MAX_TOKENS": 128,
                  "AI_SPECIALISTS": specs, "AI_MAX_TOOL_CALLS": 0,
                  "TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
                  "TELEGRAM_SECURITY_ADMIN_IDS": "9001"}
        app.config.update({key: config[key] for key in (
            "TELEGRAM_SECURITY_BOT_TOKEN", "TELEGRAM_SECURITY_ADMIN_IDS",
        )})
        monkeypatch.setattr("app.services.ai_external_notices.send_message",
                            lambda *_args: True)
        prompt = "Please debug and implement a careful Python code example for a complex data pipeline."
        denied = AIService(config, provider=LocalModel()).respond(
            prompt, scope=AI_SCOPE_RIDER, user=rider,
        )
        assert denied["ok"] and not denied["external_assistance"]
        assert calls == []

        set_external_consent(True, user=rider)
        allowed = AIService(config, provider=LocalModel()).respond(
            prompt, scope=AI_SCOPE_RIDER, user=rider,
        )
    assert allowed["ok"] and allowed["external_assistance"]
    assert len(calls) == 2


def test_external_provider_is_blocked_without_security_notice_recipient(app, monkeypatch):
    calls = []

    class LocalModel:
        def generate(self, **kwargs):
            return {"content": "Local-only answer", "tool_calls": []}

    class Expert:
        def generate(self, **kwargs):
            calls.append(kwargs)
            return {"content": "External answer", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider._specialist_provider",
                        lambda *_args: Expert())
    with app.app_context():
        specs = {name: _provider_spec() for name in ("openai", "anthropic", "gemini")}
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "local", "AI_EXTERNAL_ENABLED": True,
                  "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05", "AI_SPECIALISTS": specs,
                  "AI_MAX_TOOL_CALLS": 0}
        result = AIService(config, provider=LocalModel()).respond(
            "Please debug and implement a complex Python data pipeline with careful examples.",
            scope=AI_SCOPE_CUSTOMER, allow_external=True,
        )
        assert result["ok"] and not result["external_assistance"]
        assert AIExternalCallNotice.query.count() == 0
    assert calls == []


def test_external_provider_is_blocked_when_security_notice_delivery_fails(app, monkeypatch):
    calls = []
    project_code = "def approved_source(): return 'private'"

    class LocalModel:
        def generate(self, **kwargs):
            return {"content": "Local-only answer", "tool_calls": []}

    class Expert:
        def generate(self, **kwargs):
            calls.append(kwargs)
            return {"content": "External answer", "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider._specialist_provider",
                        lambda *_args: Expert())
    monkeypatch.setattr("app.services.ai_external_notices.send_message",
                        lambda *_args: False)
    with app.app_context():
        settings = {"TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
                    "TELEGRAM_SECURITY_ADMIN_IDS": "9001"}
        app.config.update(settings)
        specialists = {name: _provider_spec() for name in ("openai", "anthropic", "gemini")}
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "local", "AI_EXTERNAL_ENABLED": True,
                  "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05", "AI_SPECIALISTS": specialists,
                  "AI_MAX_TOOL_CALLS": 0, **settings}
        result = AIService(config, provider=LocalModel()).respond(
            "Please debug and implement a complex Python data pipeline with careful examples.",
            scope=AI_SCOPE_CUSTOMER, allow_external=True,
            context={"job_id": "builder-job-2"},
            external_payload=project_code,
        )
        assert result["ok"] and not result["external_assistance"]
        notices = AIExternalCallNotice.query.all()
        assert len(notices) == 2
        assert all(notice.job_id == "builder-job-2" for notice in notices)
        assert AIExternalCallRecipient.query.filter_by(status="pending").count() == 2
    assert calls == []


def test_verifier_request_gets_its_own_notice_before_dispatch(app, monkeypatch):
    calls = []
    provider_inputs = []
    notices_sent = []
    project_code = "def approved_source(): return 'private'"

    class Expert:
        def __init__(self, name):
            self.name = name

        def generate(self, **kwargs):
            provider_inputs.append((self.name, kwargs))
            notice = AIExternalCallNotice.query.filter_by(provider=self.name).one()
            assert notice.status == "started"
            assert notice.job_id == "builder-job-1"
            assert notice.recipients[0].status == "sent"
            calls.append((self.name, kwargs["model"]))
            answer = {
                "openai": "Crimson penguin",
                "anthropic": "Quantum asteroid",
                "gemini": "The cautious answer is uncertain",
            }[self.name]
            return {"content": answer, "tool_calls": []}

    monkeypatch.setattr("app.ai.core.provider._specialist_provider",
                        lambda name, _spec, _timeout: Expert(name))
    monkeypatch.setattr(
        "app.services.ai_external_notices.send_message",
        lambda _bot, _recipient, text: notices_sent.append(text) or True,
    )
    with app.app_context():
        settings = {"TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
                    "TELEGRAM_SECURITY_ADMIN_IDS": "9001"}
        app.config.update(settings)
        specialists = {name: _provider_spec() for name in ("openai", "anthropic", "gemini")}
        config = {"AI_LOCAL_ENABLED": False, "AI_EXTERNAL_ENABLED": True,
                  "AI_EXTERNAL_MONTHLY_BUDGET_USD": "0.05", "AI_SPECIALISTS": specialists,
                  "AI_MAX_TOKENS": 1024, **settings}
        result = AIService(config).respond(
            "Please debug this complex Python implementation carefully.",
            scope=AI_SCOPE_CUSTOMER, allow_external=True,
            context={"job_id": "builder-job-1"},
            external_payload=project_code,
        )
        assert result["ok"] and result["external_assistance"]
        assert AIExternalCallNotice.query.count() == 3
        assert AIExternalCallNotice.query.filter_by(purpose="specialist").count() == 2
        assert AIExternalCallNotice.query.filter_by(purpose="verifier").count() == 1
        assert AIExternalCallRecipient.query.filter_by(status="sent").count() == 3
        notices = AIExternalCallNotice.query.all()
        assert len({notice.id for notice in notices}) == 3
        assert all(not hasattr(notice, "prompt") and not hasattr(notice, "content")
                   for notice in notices)
    assert calls == [("openai", "configured-model"), ("anthropic", "configured-model"),
                     ("gemini", "configured-model")]
    assert all(
        project_code in " ".join(str(message.get("content", "")) for message in kwargs["messages"])
        for _, kwargs in provider_inputs
    )
    assert len(notices_sent) == 3
    assert all("builder-job-1" in text and project_code not in text for text in notices_sent)


def test_external_call_notice_retries_without_storing_prompt_or_code(app, monkeypatch):
    from app.services.ai_external_notices import (
        deliver_pending_external_call_notices, record_external_call_notice,
    )

    attempts = []
    responses = iter((False, True))

    def send(bot, telegram_user_id, text):
        attempts.append((bot, telegram_user_id, text))
        return next(responses)

    monkeypatch.setattr("app.services.ai_external_notices.send_message", send)
    with app.app_context():
        config = {"TELEGRAM_SECURITY_BOT_TOKEN": "security-test-token",
                  "TELEGRAM_SECURITY_ADMIN_IDS": "9001"}
        app.config.update(config)
        call_id = record_external_call_notice(
            config=config, provider="openai", model="configured-model",
            purpose="specialist", estimated_cost_usd="0.012345", job_id="job-7",
        )
        recipient = AIExternalCallRecipient.query.one()
        assert call_id and recipient.status == "pending" and recipient.attempts == 1
        assert deliver_pending_external_call_notices() == 1
        assert recipient.status == "sent" and recipient.attempts == 2
        notice = AIExternalCallNotice.query.one()
        assert notice.status == "started"
        assert notice.model == "configured-model" and notice.job_id == "job-7"
        assert not hasattr(notice, "prompt") and not hasattr(notice, "content")
    assert len(attempts) == 2
    assert all("External AI" in call[2] and "job-7" in call[2] for call in attempts)


def test_security_telegram_general_question_uses_local_core(app, monkeypatch):
    from app.extensions import db
    from app.models import User
    from app.telegram.security import handle_security_update

    delivered = {}
    app.config["TELEGRAM_SECURITY_ADMIN_IDS"] = "9001"
    app.config["AI_LOCAL_BASE_URL"] = "https://gpu.internal/v1"
    admin = User(email="stage13-security-admin@example.test", role="admin")
    admin.set_password("password123")
    db.session.add(admin)
    db.session.flush()
    app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = f"9001:{admin.id}"

    def local_answer(self, prompt, **kwargs):
        assert prompt == "Explain recursion in simple terms"
        assert kwargs["scope"] == AI_SCOPE_SECURITY
        assert kwargs["user"].telegram_id == 9001
        return {"ok": True, "answer": "Recursion is a function calling itself.",
                "tool_results": [], "tools_used": []}

    monkeypatch.setattr("app.ai.security_tools.AIService.respond", local_answer)
    monkeypatch.setattr("app.telegram.security.send_message",
                        lambda bot, chat, text, *args, **kwargs:
                        delivered.update(bot=bot, chat=chat, text=text) or True)
    with app.app_context():
        assert handle_security_update(
            {"message": {"text": "Explain recursion in simple terms"}}, 9001, 9001
        )

    assert delivered == {"bot": "security", "chat": 9001,
                         "text": "Recursion is a function calling itself."}


def test_customer_general_and_coding_prompt_uses_core_instead_of_catalog(app, monkeypatch):
    class LocalCore:
        def __init__(self, _config):
            pass

        def respond(self, prompt, **kwargs):
            assert "recursion" in prompt
            return {"ok": True, "answer": "A Python recursion explanation.", "tools_used": [],
                    "tool_results": [], "sources": []}

    monkeypatch.setattr("app.ai.marketplace_tools.AIService", LocalCore)
    with app.app_context():
        result = handle_marketplace_ai_query("Explain recursion and show Python code")
    assert result["answer"] == "A Python recursion explanation."
    assert result["products"] == []


def test_customer_telegram_free_text_uses_shared_general_core(app, monkeypatch):
    captured = {}

    def shared_core(prompt, **kwargs):
        captured["prompt"] = prompt
        return {"ok": True, "answer": "Telegram coding answer", "products": []}

    monkeypatch.setattr("app.ai.marketplace_tools.handle_marketplace_ai_query", shared_core)
    monkeypatch.setattr("app.telegram.customer.send_message", lambda bot, chat, text, *args, **kwargs:
                        captured.update(bot=bot, chat=chat, text=text) or True)
    from app.telegram.customer import handle_customer_update
    with app.test_request_context("/"):
        assert handle_customer_update({"message": {"text": "Explain recursion and show Python code"}},
                                      555001, 555001)
    assert captured["prompt"].startswith("Explain recursion")
    assert captured["text"] == "Telegram coding answer"


def test_security_telegram_free_text_routes_to_security_local_core(app, monkeypatch):
    from app.extensions import db
    from app.models import User
    from app.telegram.security import handle_security_update

    app.config["TELEGRAM_SECURITY_ADMIN_IDS"] = "9001"
    app.config["AI_LOCAL_BASE_URL"] = "https://gpu.internal/v1"
    admin = User(email="stage13-security-query-admin@example.test", role="admin")
    admin.set_password("password123")
    db.session.add(admin)
    db.session.flush()
    app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = f"9001:{admin.id}"
    captured = {}

    def local_answer(self, prompt, **kwargs):
        captured.update(prompt=prompt, scope=kwargs["scope"],
                        principal=kwargs["user"].telegram_id)
        return {"ok": True, "answer": "A generator yields values lazily.",
                "tool_results": [], "tools_used": []}

    monkeypatch.setattr("app.ai.security_tools.AIService.respond", local_answer)
    monkeypatch.setattr("app.telegram.security.send_message",
                        lambda bot, chat, text, *args, **kwargs: True)
    with app.app_context():
        assert handle_security_update(
            {"message": {"text": "What is a Python generator?"}}, 9001, 9001
        )

    assert captured["prompt"] == "What is a Python generator?"
    assert captured["scope"] == AI_SCOPE_SECURITY
    assert captured["principal"] == 9001


def test_curated_retrieval_excludes_other_role_scopes(app, monkeypatch):
    vector = [1.0] + [0.0] * 1023
    monkeypatch.setattr("app.ai.core.knowledge.embed_text", lambda _text: vector)
    scope_rows = {
        "public": "public fact",
        "customer": "customer fact",
        "seller": "seller fact",
        "admin": "admin fact",
        "rider": "rider fact",
        "security": "security fact",
    }
    with app.app_context():
        db.session.add_all([
            AIKnowledgeChunk(
                source=f"{scope}.md", scope=scope, content=content,
                content_hash=f"{index + 1:064x}", embedding=vector,
            )
            for index, (scope, content) in enumerate(scope_rows.items())
        ])
        db.session.commit()
        visible_by_role = {
            scope: retrieve_knowledge("question", scope=scope, limit=10)
            for scope in (
                AI_SCOPE_CUSTOMER, AI_SCOPE_SELLER, AI_SCOPE_ADMIN,
                AI_SCOPE_RIDER, AI_SCOPE_SECURITY,
            )
        }
    for scope, visible in visible_by_role.items():
        expected_scope = scope.removesuffix("_ai")
        assert scope_rows["public"] in visible
        assert scope_rows[expected_scope] in visible
        assert all(
            content not in visible
            for other_scope, content in scope_rows.items()
            if other_scope not in {"public", expected_scope}
        )


def test_customer_ai_context_uses_curated_guidance_without_static_product_facts(app, monkeypatch):
    vector = [1.0] + [0.0] * 1023
    captured = {}

    class LocalModel:
        def generate(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return {"content": "I cannot verify current price or stock without a live catalog result.",
                    "tool_calls": []}

    monkeypatch.setattr("app.ai.core.knowledge.embed_text", lambda _text: vector)
    with app.app_context():
        db.session.add(AIKnowledgeChunk(
            source="public.md",
            scope="public",
            content="Prices and stock change; verify both with current approved catalog results.",
            content_hash="f" * 64,
            embedding=vector,
        ))
        db.session.commit()
        config = {
            "AI_LOCAL_ENABLED": True,
            "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
            "AI_LOCAL_MODEL": "local",
            "AI_MAX_TOOL_CALLS": 0,
            "AI_EXTERNAL_ENABLED": False,
        }
        result = AIService(config, provider=LocalModel()).respond(
            "What is the exact current price and stock of the Mango Blender?",
            scope=AI_SCOPE_CUSTOMER,
            allow_external=False,
        )

    messages = captured["messages"]
    assert result["ok"] is True
    assert "cannot verify" in result["answer"].lower()
    assert "current approved catalog results" in messages[1]["content"]
    assert "Use only results returned by the approved marketplace tools" in messages[0]["content"]
    assert "Mango Blender" not in messages[1]["content"]


def test_long_term_memory_is_opt_in_and_account_scoped(app):
    observed = []

    class LocalModel:
        def generate(self, **kwargs):
            observed.append(kwargs["context"].get("opt_in_memories", []))
            return {"content": "Answer from the current request.", "tool_calls": []}

    with app.app_context():
        user = _user("customer", "stage13-memory")
        preferences = AIPreferences(user_id=user.id, long_term_memory_enabled=True)
        db.session.add_all([preferences, AIUserMemory(user_id=user.id, content="I prefer short answers.")])
        db.session.commit()
        config = {"AI_LOCAL_ENABLED": True, "AI_LOCAL_BASE_URL": "https://gpu.internal/v1",
                  "AI_LOCAL_MODEL": "local", "AI_MAX_TOOL_CALLS": 0}
        AIService(config, provider=LocalModel()).respond("How do you explain things?",
                                                        scope=AI_SCOPE_CUSTOMER, user=user)
        preferences.long_term_memory_enabled = False
        db.session.commit()
        AIService(config, provider=LocalModel()).respond("What should you remember?",
                                                        scope=AI_SCOPE_CUSTOMER, user=user)
    assert observed[0] == ["I prefer short answers."]
    assert observed[1] == []


def test_rider_delivery_tool_is_limited_to_own_assigned_orders(app):
    with app.app_context():
        rider = _user("rider", "stage13-own")
        rider.rider_profile = RiderProfile(full_name="Own rider", phone="01700000000")
        other = _user("rider", "stage13-other")
        other.rider_profile = RiderProfile(full_name="Other rider", phone="01800000000")
        own_order = Order(order_number="NX-RIDER-OWN", customer_name="Own customer", phone="01711111111",
                          address="Own assigned address", total=Decimal("10.00"), status="confirmed",
                          delivery_status="assigned", rider_id=rider.id)
        other_order = Order(order_number="NX-RIDER-OTHER", customer_name="Other customer", phone="01811111111",
                            address="Other address", total=Decimal("10.00"), status="confirmed",
                            delivery_status="assigned", rider_id=other.id)
        db.session.add_all([own_order, other_order])
        db.session.commit()
        registry = build_rider_tool_registry()
        result = registry.call("get_my_deliveries", scope=AI_SCOPE_RIDER, user=rider)
    assert result["ok"]
    assert [row["order_number"] for row in result["result"]["deliveries"]] == ["NX-RIDER-OWN"]


def test_rider_private_delivery_question_never_uses_specialists(app, monkeypatch):
    from app.ai.rider_tools import run_rider_query

    captured = {}

    class LocalOnlyService:
        def __init__(self, _config):
            pass

        def respond(self, prompt, **kwargs):
            captured.update(prompt=prompt, allow_external=kwargs.get("allow_external"))
            return {"ok": False, "fallback": "Private local model unavailable.", "tools_used": []}

    monkeypatch.setattr("app.ai.core.provider.AIService", LocalOnlyService)
    with app.app_context():
        rider = _user("rider", "stage13-private-request")
        result = run_rider_query(rider, "What address is on my assigned delivery?")
    assert captured["allow_external"] is False
    assert result["ok"] is True


def test_external_consent_can_be_revoked(app):
    with app.app_context():
        set_external_consent(True, principal="telegram:customer:8408532941")
        assert external_consent_enabled(principal="telegram:customer:8408532941")
        set_external_consent(False, principal="telegram:customer:8408532941")
        assert not external_consent_enabled(principal="telegram:customer:8408532941")


def test_seller_and_admin_can_revoke_account_external_consent(client, app):
    with app.app_context():
        seller = _user("seller", "stage13-consent-seller")
        admin = _user("admin", "stage13-consent-admin")
        db.session.commit()
        seller_identity = (seller.id, seller.auth_version)
        admin_identity = (admin.id, admin.auth_version)
        set_external_consent(True, user=seller)
        set_external_consent(True, user=admin)

    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = seller_identity
    response = client.post("/ai/role-external-consent", data={})
    assert response.status_code == 302
    with app.app_context():
        seller = db.session.get(User, seller_identity[0])
        assert not external_consent_enabled(user=seller)

    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = admin_identity
    response = client.post("/ai/role-external-consent", json={"enabled": True})
    assert response.status_code == 200
    with app.app_context():
        admin = db.session.get(User, admin_identity[0])
        assert external_consent_enabled(user=admin)


def test_guest_can_toggle_session_consent_and_rider_has_a_protected_workspace(client, app):
    consent = client.post("/ai/external-consent", json={"enabled": True})
    assert consent.status_code == 200
    with client.session_transaction() as browser_session:
        assert browser_session["ai_external_consent"] is True

    with app.app_context():
        rider = _user("rider", "stage13-route")
        rider.rider_profile = RiderProfile(full_name="Rider Route", phone="01700000000")
        customer = _user("customer", "stage13-not-rider")
        db.session.commit()
        rider_id, rider_version = rider.id, rider.auth_version
        customer_id, customer_version = customer.id, customer.auth_version
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = rider_id
        browser_session["auth_version"] = rider_version
    assert client.get("/rider/ai").status_code == 200
    response = client.post("/rider/ai/query", json={"prompt": "What are my delivery instructions?"})
    assert response.status_code == 200
    assert response.get_json()["scope"] == AI_SCOPE_RIDER

    with client.session_transaction() as browser_session:
        browser_session["user_id"] = customer_id
        browser_session["auth_version"] = customer_version
    assert client.get("/rider/ai").status_code == 403
    assert client.post("/rider/ai/query", json={"prompt": "Explain coding"}).status_code == 403


def test_zero_price_openrouter_free_model_can_reserve_budget_gate(app):
    with app.app_context():
        config = {
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "1.00",
            "AI_SPECIALISTS": {},
        }
        spec = {
            "model": "openrouter/free",
            "api_key": "test-key",
            "base_url": "https://openrouter.ai/api/v1",
            "input_rate": "0",
            "output_rate": "0",
            "free": True,
        }
        assert reserve_external_budget(
            config, [spec], minimum_provider_count=1, include_verifier=False,
        ) is True


def test_unverified_zero_price_model_still_cannot_reserve_budget(app):
    with app.app_context():
        config = {
            "AI_EXTERNAL_ENABLED": True,
            "AI_EXTERNAL_MONTHLY_BUDGET_USD": "1.00",
            "AI_SPECIALISTS": {},
        }
        spec = {
            "model": "some-model",
            "api_key": "test-key",
            "base_url": "https://provider.example/v1",
            "input_rate": "0",
            "output_rate": "0",
        }
        assert reserve_external_budget(
            config, [spec], minimum_provider_count=1, include_verifier=False,
        ) is False
