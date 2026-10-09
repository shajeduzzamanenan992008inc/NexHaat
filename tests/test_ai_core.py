from app.ai.core.permissions import AI_SCOPE_CUSTOMER, AI_SCOPE_SECURITY
from unittest.mock import Mock

import pytest
import requests

from app.ai.core.provider import AIProviderError, AIService, OpenAICompatibleProvider
from app.ai.core.tools import ToolRegistry
from app.ai.marketplace_tools import build_customer_tool_registry, handle_marketplace_ai_query
from app.extensions import db
from app.models import SupportMessage, User


def test_ai_service_returns_safe_fallback_when_disabled():
    service = AIService({"AI_ENABLED": False, "AI_PROVIDER": "disabled"})
    result = service.respond("hello", scope=AI_SCOPE_CUSTOMER)
    assert result["ok"] is False
    assert "AI is not configured" in result["fallback"]


def test_local_ai_health_is_not_configured_without_endpoint_or_model():
    result = AIService({
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "",
        "AI_LOCAL_MODEL": "",
    }).health_check()

    assert result["ok"] is False
    assert result["status"] == "not_configured"
    assert "AI_LOCAL_BASE_URL" in result["message"]
    assert "AI_LOCAL_MODEL" in result["message"]
    assert "http" not in str(result).lower()


def test_missing_local_model_explains_external_consent_gate_without_calling_provider(
    app, monkeypatch,
):
    external_calls = []
    monkeypatch.setattr(
        "app.ai.core.provider._specialist_provider",
        lambda *_args, **_kwargs: external_calls.append(True),
    )
    service = AIService({
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "",
        "AI_LOCAL_MODEL": "",
        "AI_EXTERNAL_ENABLED": True,
        "AI_EXTERNAL_MONTHLY_BUDGET_USD": "2",
        "AI_SPECIALISTS": {
            "openai": {
                "api_key": "test-only",
                "model": "test-model",
                "base_url": "https://provider.example/v1",
                "input_rate": "1",
                "output_rate": "1",
            },
        },
    })

    with app.app_context():
        user = User(email="external-consent-required@example.test", role="customer")
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
        result = service.respond(
            "Explain recursion", scope=AI_SCOPE_CUSTOMER, user=user,
        )

    assert result["ok"] is False
    assert "External fallback is configured" in result["fallback"]
    assert "not authorized" in result["fallback"]
    assert external_calls == []


def test_local_and_external_unavailable_returns_clear_non_sensitive_error():
    result = AIService({
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "",
        "AI_LOCAL_MODEL": "",
        "AI_EXTERNAL_ENABLED": False,
    }).respond("Explain recursion", scope=AI_SCOPE_CUSTOMER)

    assert result["ok"] is False
    assert "Private Local AI is not configured" in result["fallback"]
    assert "No complete external fallback is enabled" in result["fallback"]
    assert "api_key" not in result["fallback"].lower()


def test_openai_compatible_health_check_uses_models_endpoint():
    response = Mock()
    response.json.return_value = {"data": [{"id": "configured-model"}]}
    session = Mock()
    session.get.return_value = response
    provider = OpenAICompatibleProvider(
        api_key="", model="configured-model", base_url="http://127.0.0.1:1234/v1",
        allow_missing_key=True, session=session,
    )

    assert provider.health_check(timeout=3) is True
    session.get.assert_called_once_with(
        "http://127.0.0.1:1234/v1/models", headers={"Content-Type": "application/json"},
        timeout=3, allow_redirects=False,
    )


def test_openai_compatible_health_check_reports_unreachable_service():
    session = Mock()
    session.get.side_effect = requests.exceptions.ConnectTimeout()
    provider = OpenAICompatibleProvider(
        api_key="", model="configured-model", base_url="https://private.example/v1",
        allow_missing_key=True, session=session,
    )

    with pytest.raises(AIProviderError):
        provider.health_check(timeout=3)


def test_local_ai_health_rejects_malformed_endpoint_without_internal_error():
    result = AIService({
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "http://[::1",
        "AI_LOCAL_MODEL": "configured-model",
    }).health_check()

    assert result["ok"] is False
    assert result["status"] == "unreachable"
    assert "http://[::1" not in str(result)


@pytest.mark.parametrize(
    ("environment", "base_url"),
    [
        ("development", "http://192.0.2.10/v1"),
        ("production", "http://localhost:1234/v1"),
    ],
)
def test_local_ai_health_rejects_non_loopback_or_production_http(environment, base_url, monkeypatch):
    def unexpected_request(*_args, **_kwargs):
        pytest.fail("An insecure AI endpoint must not be contacted.")

    monkeypatch.setattr("app.ai.core.provider.requests.get", unexpected_request)
    result = AIService({
        "ENVIRONMENT": environment,
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": base_url,
        "AI_LOCAL_MODEL": "configured-model",
    }).health_check()

    assert result["ok"] is False
    assert result["status"] == "unreachable"


def test_customer_ai_health_route_distinguishes_unconfigured_and_reachable(client, app, monkeypatch):
    missing = client.get("/ai/health")

    assert missing.status_code == 503
    assert missing.get_json()["status"] == "not_configured"
    assert missing.headers["Cache-Control"] == "no-store"

    app.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="http://127.0.0.1:1234/v1",
        AI_LOCAL_MODEL="configured-model",
    )
    response = Mock()
    response.json.return_value = {"data": [{"id": "configured-model"}]}
    monkeypatch.setattr("app.ai.core.provider.requests.get", lambda *_args, **_kwargs: response)

    connected = client.get("/ai/health")

    assert connected.status_code == 200
    assert connected.get_json()["status"] == "available"
    assert "127.0.0.1" not in connected.get_data(as_text=True)
    assert "configured-model" not in connected.get_data(as_text=True)


def test_customer_ai_health_route_reports_unreachable_without_endpoint_details(client, app, monkeypatch):
    app.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="https://private.example/v1",
        AI_LOCAL_MODEL="configured-model",
    )

    def fail_request(*_args, **_kwargs):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr("app.ai.core.provider.requests.get", fail_request)
    response = client.get("/ai/health")

    assert response.status_code == 503
    assert response.get_json()["status"] == "unreachable"
    assert "private.example" not in response.get_data(as_text=True)
    assert "configured-model" not in response.get_data(as_text=True)


def test_openai_compatible_ai_request_succeeds_with_configured_endpoint(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "choices": [{"message": {"content": "Verified provider answer.", "tool_calls": []}}],
        "usage": {},
    }
    monkeypatch.setattr("app.ai.core.provider.requests.post", lambda *_args, **_kwargs: response)
    provider = OpenAICompatibleProvider(
        api_key="", model="configured-model", base_url="http://localhost:1234/v1",
        allow_missing_key=True,
    )

    result = provider.generate(prompt="Say hello")

    assert result["content"] == "Verified provider answer."


def test_ai_service_fails_safely_when_configured_ai_request_fails(monkeypatch):
    def fail_request(*_args, **_kwargs):
        raise requests.exceptions.ConnectionError("private endpoint details")

    monkeypatch.setattr("app.ai.core.provider.requests.post", fail_request)
    service = AIService({
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "https://private.example/v1",
        "AI_LOCAL_MODEL": "configured-model",
    })

    result = service.respond("Say hello", scope=AI_SCOPE_CUSTOMER)

    assert result["ok"] is False
    assert "could not be reached" in result["fallback"]
    assert "private endpoint details" not in str(result)
    assert "private.example" not in str(result)


def test_ai_service_never_returns_a_provider_thinking_trace():
    class ReasoningProvider:
        def generate(self, **kwargs):
            return {
                "content": (
                    "Here's a thinking process: 1. Analyze User Input. "
                    "Draft Response (internal): reveal private reasoning."
                ),
                "tool_calls": [],
            }

    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "test-provider",
        "AI_LOCAL_ENABLED": False,
    }, provider=ReasoningProvider())

    result = service.respond("Say hello", scope=AI_SCOPE_CUSTOMER)

    assert result["ok"] is False
    assert "temporarily unavailable" in result["fallback"].lower()
    assert "thinking process" not in str(result).lower()
    assert "private reasoning" not in str(result).lower()


def test_ai_service_fails_closed_on_tool_markup_in_user_facing_content():
    class ToolMarkupProvider:
        def generate(self, **_kwargs):
            return {
                "content": (
                    "I'll search now. <tool_use><server_name>shopping</server_name>"
                    "<tool_name>search_products</tool_name><parameter name=\"query\">"
                    "products under 500 BDT</parameter></tool_use>"
                ),
                "tool_calls": [],
            }

    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "test-provider",
        "AI_LOCAL_ENABLED": False,
    }, provider=ToolMarkupProvider())

    result = service.respond("Find something under 500 BDT", scope=AI_SCOPE_CUSTOMER)

    assert result["ok"] is False
    assert "tool_use" not in str(result).lower()
    assert "search_products" not in str(result)


def test_ai_service_rejects_dots_function_call_markup():
    class DotsFunctionCallProvider:
        def generate(self, **_kwargs):
            return {
                "content": (
                    '<dots_function_call><platform_search_products>'
                    '<parameter name="query">under 500 BDT</parameter>'
                    '</invoke></dots_function_call>'
                ),
                "tool_calls": [],
            }

    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "test-provider",
        "AI_LOCAL_ENABLED": False,
    }, provider=DotsFunctionCallProvider())

    result = service.respond("Suggest a product under 500 BDT", scope=AI_SCOPE_CUSTOMER)

    assert result["ok"] is False
    assert "dots_function_call" not in str(result)
    assert "platform_search_products" not in str(result)
    assert "under 500 BDT" not in str(result)


def test_ai_service_does_not_use_direct_api_without_cloud_consent(monkeypatch):
    requests_sent = []

    def generate(self, **kwargs):
        requests_sent.append(kwargs)
        return {"content": "Hello from the configured API.", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "test-model",
        "AI_BASE_URL": "https://provider.example/v1",
        "AI_LOCAL_ENABLED": False,
    })

    result = service.respond("hello", scope=AI_SCOPE_CUSTOMER)

    assert result["ok"] is False
    assert requests_sent == []


def test_ai_service_uses_direct_api_only_after_consent_budget_and_notice(
    app, monkeypatch,
):
    def generate(self, **kwargs):
        return {"content": "Hello from the configured API.", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    monkeypatch.setattr(
        "app.ai.core.external_budget.reserve_external_budget",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.external_call_notices_ready",
        lambda _config: True,
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.record_external_call_notice",
        lambda **_kwargs: "notice-id",
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.external_call_notice_delivered",
        lambda _call_id: True,
    )
    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "test-model",
        "AI_BASE_URL": "https://provider.example/v1",
        "AI_API_INPUT_USD_PER_MILLION": "1",
        "AI_API_OUTPUT_USD_PER_MILLION": "1",
        "AI_EXTERNAL_ENABLED": True,
        "AI_EXTERNAL_MONTHLY_BUDGET_USD": "5",
        "AI_LOCAL_ENABLED": False,
    })

    result = service.respond(
        "hello", scope=AI_SCOPE_CUSTOMER, allow_external=True,
    )

    assert result["ok"] is True
    assert result["answer"] == "Hello from the configured API."
    assert result["provider"] == "openai_compatible-fallback"


def test_ai_service_falls_back_to_configured_api_when_local_server_is_unreachable(monkeypatch):
    requested_urls = []

    def generate(self, **kwargs):
        requested_urls.append(kwargs["base_url"])
        if kwargs["base_url"] == "http://127.0.0.1:1234/v1":
            raise requests.exceptions.ConnectionError()
        return {"content": "Try this helpful option 🌱", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    monkeypatch.setattr(
        "app.ai.core.external_budget.reserve_external_budget",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.external_call_notices_ready",
        lambda _config: True,
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.record_external_call_notice",
        lambda **_kwargs: "notice-id",
    )
    monkeypatch.setattr(
        "app.services.ai_external_notices.external_call_notice_delivered",
        lambda _call_id: True,
    )
    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "test-model",
        "AI_BASE_URL": "https://provider.example/v1",
        "AI_API_INPUT_USD_PER_MILLION": "1",
        "AI_API_OUTPUT_USD_PER_MILLION": "1",
        "AI_EXTERNAL_ENABLED": True,
        "AI_EXTERNAL_MONTHLY_BUDGET_USD": "5",
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "http://127.0.0.1:1234/v1",
        "AI_LOCAL_MODEL": "local-model",
    })

    result = service.respond(
        "Suggest a helpful study tip",
        scope=AI_SCOPE_CUSTOMER,
        tools=ToolRegistry(),
        allow_external=True,
    )

    assert result["ok"] is True
    assert result["provider"] == "openai_compatible-fallback"
    assert result["answer"] == "Try this helpful option 🌱"
    assert requested_urls == [
        "http://127.0.0.1:1234/v1",
        "https://provider.example/v1",
    ]


def test_customer_chat_uses_configured_local_api_end_to_end(client, monkeypatch):
    def generate(self, **kwargs):
        return {"content": "API response reached the customer chat.", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    client.application.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="http://127.0.0.1:1234/v1",
        AI_LOCAL_MODEL="test-model",
    )

    page = client.get("/ai/")
    response = client.post("/ai/chat", json={"prompt": "Explain photosynthesis"})

    assert page.status_code == 200
    assert b'id="ai-service-status"' in page.data
    assert b'id="ai-health-endpoint"' in page.data
    assert response.status_code == 200
    assert response.get_json()["answer"] == "API response reached the customer chat."
    assert response.get_json()["warnings"] == []
    assert "provider" not in response.get_json()
    assert "model" not in response.get_json()


def test_customer_chat_returns_only_a_fixed_notice_for_external_assistance(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.ai.handle_marketplace_ai_query",
        lambda *_args, **_kwargs: {
            "ok": True,
            "answer": "A safe answer",
            "products": [],
            "external_assistance": True,
            "warnings": ["provider-supplied secret"],
            "provider": "private-provider-id",
            "model": "private-model-id",
            "usage": {"prompt_tokens": 9},
            "latency_ms": 125,
        },
    )

    response = client.post("/ai/chat", json={"prompt": "Explain this topic."})
    result = response.get_json()

    assert response.status_code == 200
    assert result["warnings"] == [
        "External specialist assistance was used for this response."
    ]
    assert "provider" not in result
    assert "model" not in result
    assert "usage" not in result
    assert "latency_ms" not in result
    assert "provider-supplied secret" not in response.get_data(as_text=True)
    assert "private-provider-id" not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "prompt",
    [
        "show me a phone",
        "find me a smartphone",
        "amar jonno phone dekhao",
        "phone gula dekhaw",
        "ভালো ফোন দেখাও",
        "i need a mobile",
        "can you find me a phone?",
        "show phne",
        "amar 30k er moddhe Samsung er ekta camera valo phone chai",
        "amar bot bujtese na",
    ],
)
def test_natural_prompts_reach_ai_with_tools_before_keyword_fallback(
    app, monkeypatch, prompt
):
    captured = {}

    def generate(self, **kwargs):
        captured.update(kwargs)
        return {"content": "I understood your request.", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    app.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="http://127.0.0.1:1234/v1",
        AI_LOCAL_MODEL="test-model",
    )

    with app.app_context():
        result = handle_marketplace_ai_query(prompt)

    assert result["ok"] is True
    assert captured["prompt"] == prompt
    assert "search_products" in {
        tool["function"]["name"] for tool in captured["tools"]
    }
    assert "meaning, not by exact words" in captured["messages"][0]["content"]


def test_natural_follow_up_history_reaches_provider_for_reference_resolution(
    app, monkeypatch
):
    captured = {}

    def generate(self, **kwargs):
        captured.update(kwargs)
        return {"content": "I will filter those Samsung phones by your budget.", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    app.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="http://127.0.0.1:1234/v1",
        AI_LOCAL_MODEL="test-model",
    )

    with app.app_context():
        result = handle_marketplace_ai_query(
            "under 30000",
            context={"history": [
                {"role": "user", "content": "Samsung phones দেখাও"},
                {"role": "assistant", "content": "Here are Samsung phones."},
            ]},
        )

    assert result["ok"] is True
    assert captured["prompt"] == "under 30000"
    assert any(
        item["role"] == "user" and item["content"] == "Samsung phones দেখাও"
        for item in captured["messages"]
    )
    assert any(
        item["role"] == "assistant" and item["content"] == "Here are Samsung phones."
        for item in captured["messages"]
    )
    assert "Use recent conversation to resolve follow-ups" in captured["messages"][0]["content"]


def test_customer_chat_preserves_emojis_and_instructs_model_to_use_them_naturally(client, monkeypatch):
    expected = "Here is a helpful tip 🌱✨"

    def generate(self, **kwargs):
        assert "relevant Unicode emoji naturally" in kwargs["messages"][0]["content"]
        return {"content": expected, "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    client.application.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="http://127.0.0.1:1234/v1",
        AI_LOCAL_MODEL="test-model",
    )

    response = client.post("/ai/chat", json={"prompt": "Explain photosynthesis"})

    assert response.status_code == 200
    assert response.get_json()["answer"] == expected


def test_customer_chat_rejects_function_markup_at_response_boundary(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.ai.handle_marketplace_ai_query",
        lambda *_args, **_kwargs: {
            "ok": True,
            "answer": (
                '<dots_function_call><platform_search_products>'
                '<parameter name="query">under 500 BDT</parameter>'
                '</invoke></dots_function_call>'
            ),
            "data": "same markup",
            "products": [],
        },
    )

    response = client.post("/ai/chat", json={"prompt": "Suggest something under 500 BDT"})
    result = response.get_json()

    assert response.status_code == 503
    assert result["ok"] is False
    assert "could not verify" in result["answer"].lower()
    assert "dots_function_call" not in str(result)
    assert "platform_search_products" not in str(result)


def test_ai_service_does_not_send_customer_image_to_direct_external_api(monkeypatch):
    describe_image = Mock()
    monkeypatch.setattr(OpenAICompatibleProvider, "describe_image", describe_image)
    service = AIService({
        "AI_ENABLED": True,
        "AI_PROVIDER": "openai_compatible",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "vision-test",
        "AI_BASE_URL": "https://provider.example/v1",
        "AI_LOCAL_ENABLED": False,
    })

    with pytest.raises(AIProviderError, match="Private local visual search"):
        service.describe_image(b"test-image")
    describe_image.assert_not_called()


def test_ai_service_describes_customer_image_using_local_provider(monkeypatch):
    describe_image = Mock(return_value="orange geometric product")
    monkeypatch.setattr(OpenAICompatibleProvider, "describe_image", describe_image)
    service = AIService({
        "AI_LOCAL_ENABLED": True,
        "AI_LOCAL_BASE_URL": "http://127.0.0.1:1234/v1",
        "AI_LOCAL_MODEL": "local-vision",
    })

    assert service.describe_image(b"test-image") == "orange geometric product"
    describe_image.assert_called_once()
    assert describe_image.call_args.kwargs["model"] == "local-vision"
    assert describe_image.call_args.kwargs["max_tokens"] == 160


def test_customer_ai_hides_voice_actions_when_local_media_services_are_missing(client):
    response = client.get("/ai/")

    assert response.status_code == 200
    assert b"Ask NexHaat Shopping assistant" in response.data
    assert b'id="ai-voice-unavailable"' in response.data
    assert b'id="ai-voice-toggle"' not in response.data
    assert b'id="ai-voice-form"' not in response.data
    assert b'id="ai-voice-transcription-configured" type="hidden" value="false"' in response.data
    assert b'id="ai-speech-output-configured" type="hidden" value="false"' in response.data
    assert b'id="ai-external-consent" type="hidden" value="false"' in response.data


def test_guest_external_provider_consent_is_explicit_and_session_scoped(client, app):
    app.config["AI_EXTERNAL_ENABLED"] = True

    initial_page = client.get("/ai/")
    initial_html = initial_page.get_data(as_text=True)
    assert initial_page.status_code == 200
    assert 'id="ai-external-consent" type="checkbox"' in initial_html
    assert 'id="ai-external-consent" type="checkbox" checked' not in initial_html

    consent = client.post("/ai/external-consent", json={"enabled": True})
    opted_in_page = client.get("/ai/").get_data(as_text=True)

    assert consent.status_code == 200
    assert 'id="ai-external-consent" type="checkbox" checked' in opted_in_page


def test_customer_can_opt_in_to_external_fallback_from_chat_page(client, app):
    from app.ai.core.consent import external_consent_enabled

    app.config["AI_EXTERNAL_ENABLED"] = True
    with app.app_context():
        customer = User(
            email="inline-external-consent@example.test",
            role="customer",
        )
        customer.set_password("test-password")
        db.session.add(customer)
        db.session.commit()
        identity = (customer.id, customer.auth_version)

    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = identity

    page = client.get("/ai/")
    assert page.status_code == 200
    assert b'id="ai-external-consent" type="checkbox"' in page.data
    assert b'id="ai-external-consent" type="checkbox" checked' not in page.data

    response = client.post("/ai/external-consent", json={"enabled": True})
    assert response.status_code == 200
    assert response.get_json()["enabled"] is True

    with app.app_context():
        customer = db.session.get(User, identity[0])
        assert external_consent_enabled(user=customer)

    opted_in_page = client.get("/ai/")
    assert b'id="ai-external-consent" type="checkbox" checked' in opted_in_page.data


def test_customer_ai_enables_voice_controls_only_with_local_asr(client, app):
    app.config.update(AI_ASR_BASE_URL="https://asr.example.test/v1", AI_ASR_MODEL="whisper-local")

    response = client.get("/ai/")

    assert response.status_code == 200
    assert b'id="ai-voice-toggle"' in response.data
    assert b'id="ai-voice-form"' in response.data
    assert b'id="ai-voice-transcription-configured" type="hidden" value="true"' in response.data


def test_voice_unavailable_notice_uses_bengali_for_bangla_locale(client):
    assert client.post("/language", data={"locale": "bn_BD", "next": "/ai/"}).status_code == 302

    response = client.get("/ai/")

    assert response.status_code == 200
    assert "ব্যক্তিগত ভয়েস ট্রান্সক্রিপশন সংযুক্ত নেই".encode() in response.data


def test_tool_registry_restricts_security_scope_to_security_users():
    registry = ToolRegistry()
    registry.register("get_security_summary", lambda **kwargs: {"ok": True}, scope=AI_SCOPE_SECURITY)
    allowed = registry.call("get_security_summary", scope=AI_SCOPE_SECURITY)
    blocked = registry.call("get_security_summary", scope=AI_SCOPE_CUSTOMER)
    assert allowed["ok"] is True
    assert blocked["ok"] is False
    assert blocked["error"] == "Tool is not available in this assistant scope."


def test_ai_service_uses_safe_fallback_when_provider_errors():
    class BrokenProvider:
        def generate(self, **kwargs):
            raise RuntimeError("provider body must not escape")

    service = AIService({"AI_ENABLED": True, "AI_PROVIDER": "mock", "AI_MODEL": "test-model"},
                        provider=BrokenProvider())
    result = service.respond("tell me about my cart", scope=AI_SCOPE_CUSTOMER)
    assert result["ok"] is False
    assert "temporarily unavailable" in result["fallback"].lower()
    assert "provider body" not in str(result)


def test_customer_tool_registry_can_answer_catalog_search_and_policy(app):
    with app.app_context():
        registry = build_customer_tool_registry()
        search_result = registry.call("search_products", scope=AI_SCOPE_CUSTOMER, query="burger", limit=3)
        policy_result = registry.call("get_store_policy", scope=AI_SCOPE_CUSTOMER)
    assert search_result["ok"] is True
    assert isinstance(search_result["result"], list)
    assert policy_result["ok"] is True
    assert "delivery" in str(policy_result["result"]).lower()


def test_marketplace_ai_query_uses_customer_tools_with_no_provider(app):
    with app.app_context():
        result = handle_marketplace_ai_query("show me burgers in the catalog", user=None)
    assert result["ok"] is True
    assert result["tools_used"] == ["search_products"]
    assert result["products"] == []
    assert "no available" in result["answer"].lower()


def test_marketplace_queries_stay_deterministic_when_local_ai_is_disabled(app, monkeypatch):
    app.config.update(
        AI_ENABLED=True,
        AI_PROVIDER="openai_compatible",
        AI_API_KEY="test-key",
        AI_MODEL="test-model",
        AI_BASE_URL="https://provider.example/v1",
        AI_LOCAL_ENABLED=False,
        AI_EXTERNAL_ENABLED=True,
        AI_EXTERNAL_MONTHLY_BUDGET_USD="5",
        AI_API_INPUT_USD_PER_MILLION="1",
        AI_API_OUTPUT_USD_PER_MILLION="1",
    )

    def reject_external_request(*_args, **_kwargs):
        pytest.fail("Marketplace prompts must not be sent to the direct external provider.")

    monkeypatch.setattr("app.ai.core.provider.requests.post", reject_external_request)
    with app.app_context():
        result = handle_marketplace_ai_query("show me burgers in the catalog", user=None)

    assert result["ok"] is True
    assert result["tools_used"] == ["search_products"]
    assert "no available" in result["answer"].lower()


def test_customer_ai_is_post_only_and_does_not_persist_chat(client, app):
    assert client.get("/ai/chat").status_code == 405
    response = client.post("/ai/chat", json={"prompt": "Find headphones under 2k"})
    assert response.status_code == 200
    assert "products" in response.get_json()
    with app.app_context():
        assert SupportMessage.query.count() == 0


def test_disabled_provider_handles_banglish_budget(app):
    with app.app_context():
        result = handle_marketplace_ai_query("amar 2k er moddhe headphone lagbe")
    assert result["ok"] is True
    assert result["tools_used"] == ["search_products"]


def test_tool_registry_rejects_nested_malformed_arguments_and_nan():
    registry = ToolRegistry()
    registry.register("compare_items", lambda **kwargs: kwargs, scope=AI_SCOPE_CUSTOMER,
                      parameters={"type": "object", "properties": {
                          "slugs": {"type": "array", "minItems": 2, "maxItems": 3,
                                    "items": {"type": "string", "maxLength": 8}},
                          "price": {"type": "number", "minimum": 0, "maximum": 1000},
                      }, "additionalProperties": False})
    assert not registry.call("compare_items", scope=AI_SCOPE_CUSTOMER, slugs=["one"])["ok"]
    assert not registry.call("compare_items", scope=AI_SCOPE_CUSTOMER, slugs=["one", "two"], price=float("nan"))["ok"]


def test_tool_registry_rejects_unknown_scope_fields():
    registry = ToolRegistry()
    registry.register("catalog_search", lambda **kwargs: {"ok": True}, scope=AI_SCOPE_CUSTOMER,
                      parameters={"type": "object", "properties": {
                          "query": {"type": "string", "maxLength": 20},
                      }, "additionalProperties": False})
    result = registry.call("catalog_search", scope=AI_SCOPE_CUSTOMER, arguments={"query": "item", "user_id": 7})
    assert result["ok"] is False
