"""Deterministic task-aware specialist routing tests."""

from app.ai.core.specialist_router import classify_specialist_task, select_specialists


def _ready():
    return [
        ("openai", {"agent_name": "Astra", "model": "a"}),
        ("anthropic", {"agent_name": "Luna", "model": "b"}),
        ("gemini", {"agent_name": "Sol", "model": "c"}),
        ("deepseek", {"agent_name": "Forge", "model": "d"}),
    ]


def test_task_classifier_routes_common_marketplace_questions():
    assert classify_specialist_task("Recommend a product under 5000 taka") == "shopping"
    assert classify_specialist_task("Debug this Python API exception and add tests") == "engineering"
    assert classify_specialist_task("Audit privacy risks and verify this security change") == "review"
    assert classify_specialist_task("Create a roadmap and plan project phases") == "planning"
    assert classify_specialist_task("Hello, how are you?") == "general"


def test_shopping_prefers_sol_and_luna():
    selected = select_specialists("Compare products and find the best price for my budget", _ready())
    assert [spec["agent_name"].lower() for _name, spec in selected] == ["sol", "luna"]


def test_engineering_prefers_forge_and_luna():
    selected = select_specialists("Debug the API bug and write regression tests", _ready())
    assert [spec["agent_name"].lower() for _name, spec in selected] == ["forge", "luna"]


def test_review_prefers_luna_and_forge():
    selected = select_specialists("Audit the security risks and verify correctness", _ready())
    assert [spec["agent_name"].lower() for _name, spec in selected] == ["luna", "forge"]


def test_selector_never_chooses_unconfigured_providers_and_prefers_unique_personas():
    only_two = [
        ("openai", {"agent_name": "Astra", "model": "a"}),
        ("custom", {"agent_name": "Astra", "model": "b"}),
        ("deepseek", {"agent_name": "Forge", "model": "d"}),
    ]
    selected = select_specialists("review this code", only_two, limit=2)
    assert len(selected) == 2
    assert {name for name, _spec in selected} == {"openai", "deepseek"}


def test_selector_handles_empty_config_and_invalid_limit():
    assert select_specialists("shopping", []) == []
    assert len(select_specialists("shopping", _ready(), limit="invalid")) == 2
