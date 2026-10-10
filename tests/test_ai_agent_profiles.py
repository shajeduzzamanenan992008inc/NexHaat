"""Tests for the optional Astra/Luna/Sol/Forge specialist personas."""

from app.ai.core.provider import _specialist_agent_guidance


def test_default_provider_personas_are_explicit_and_not_model_claims():
    assert "Astra" in _specialist_agent_guidance("openai", {})
    assert "Luna" in _specialist_agent_guidance("anthropic", {})
    assert "Sol" in _specialist_agent_guidance("gemini", {})
    assert "Forge" in _specialist_agent_guidance("deepseek", {})


def test_persona_can_be_overridden_and_unknown_name_is_safe():
    assert "planning and synthesis" in _specialist_agent_guidance(
        "openai", {"agent_name": "Astra"}
    )
    assert "independent specialist" in _specialist_agent_guidance(
        "custom-provider", {"agent_name": "unlisted-persona"}
    )


def test_verifier_role_is_added_without_asking_for_hidden_reasoning():
    prompt = _specialist_agent_guidance("gemini", {"agent_name": "Sol"}, verifier=True)
    assert "independent verifier" in prompt
    assert "hidden reasoning" not in prompt.lower()
