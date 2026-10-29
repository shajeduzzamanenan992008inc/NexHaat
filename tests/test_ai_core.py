from app.ai.core.permissions import AI_SCOPE_CUSTOMER, AI_SCOPE_SECURITY
from app.ai.core.provider import AIService
from app.ai.core.tools import ToolRegistry
from app.ai.marketplace_tools import (
    build_customer_tool_registry,
    handle_marketplace_ai_query,
)
from app.models import SupportMessage


def test_ai_service_returns_safe_fallback_when_disabled():
    service = AIService({"AI_ENABLED": False, "AI_PROVIDER": "disabled"})
    result = service.respond("hello", scope=AI_SCOPE_CUSTOMER)
    assert result["ok"] is False
    assert "AI is currently unavailable" in result["fallback"]


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
