"""Task-aware routing for configured external specialist personas.

This module deliberately uses transparent, deterministic routing. It does not call an
LLM, inspect private user data, or imply that persona names are separate model products.
"""

from __future__ import annotations

import re
from typing import Iterable


_DEFAULT_PERSONAS = {
    "openai": "astra",
    "anthropic": "luna",
    "gemini": "sol",
    "deepseek": "forge",
}

_TASK_KEYWORDS = {
    "shopping": (
        "product", "shopping", "shop", "buy", "purchase", "cart", "wishlist",
        "price", "budget", "recommend", "compare products", "catalog", "seller",
        "stock", "inventory", "delivery", "order", "refund", "review", "deal",
    ),
    "engineering": (
        "code", "coding", "bug", "debug", "stack trace", "exception", "python",
        "javascript", "typescript", "api", "endpoint", "database", "sql", "test",
        "tests", "refactor", "deploy", "deployment", "build", "compile", "security patch",
    ),
    "review": (
        "audit", "verify", "verification", "validate", "review", "risk", "secure",
        "security", "privacy", "check this", "correctness", "fact check", "failure",
        "regression", "threat model",
    ),
    "planning": (
        "plan", "roadmap", "strategy", "architecture", "design", "phases", "prioritize",
        "milestone", "workflow", "approach", "proposal", "steps", "project plan",
    ),
}

# Best-fit roles first; the selector falls back to other configured personas if needed.
_TASK_PERSONAS = {
    "shopping": ("sol", "luna", "astra", "forge"),
    "engineering": ("forge", "luna", "astra", "sol"),
    "review": ("luna", "forge", "astra", "sol"),
    "planning": ("astra", "luna", "forge", "sol"),
    "general": ("astra", "luna", "sol", "forge"),
}


def classify_specialist_task(prompt: str) -> str:
    """Return a coarse task category from user-visible text only."""
    text = str(prompt or "").lower()
    scores = {}
    for task, phrases in _TASK_KEYWORDS.items():
        score = 0
        for phrase in phrases:
            # Count whole words for single tokens, literal phrases for multiword terms.
            if " " in phrase:
                score += 2 if phrase in text else 0
            else:
                score += len(re.findall(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))
        scores[task] = score
    if not any(scores.values()):
        return "general"
    # Stable tie-break prioritizes risk/review, then engineering, shopping, planning.
    tie_order = {"review": 0, "engineering": 1, "shopping": 2, "planning": 3}
    return min(scores, key=lambda key: (-scores[key], tie_order[key]))


def _persona_for(name: str, spec: dict) -> str:
    raw = spec.get("agent_name") or _DEFAULT_PERSONAS.get(str(name).lower(), "analyst")
    persona = str(raw).strip().lower()
    return persona if persona in {"astra", "luna", "sol", "forge"} else "analyst"


def select_specialists(prompt: str, ready: Iterable[tuple[str, dict]], *, limit: int = 2):
    """Choose configured specialists that best fit the task, preserving safe fallback order.

    ``ready`` contains only already-validated provider configurations. The function never
    changes budget, consent, or notice gates; callers must still enforce those gates.
    Unique personas are preferred so a multi-agent answer gets genuinely different roles.
    """
    candidates = list(ready or [])
    try:
        limit = max(1, min(int(limit), 4))
    except (TypeError, ValueError):
        limit = 2
    if not candidates:
        return []

    task = classify_specialist_task(prompt)
    preference = _TASK_PERSONAS[task]
    original_order = {name: index for index, (name, _spec) in enumerate(candidates)}
    ranked = sorted(
        candidates,
        key=lambda item: (
            preference.index(_persona_for(item[0], item[1]))
            if _persona_for(item[0], item[1]) in preference else len(preference),
            original_order[item[0]],
        ),
    )

    selected = []
    seen_personas = set()
    for item in ranked:
        persona = _persona_for(item[0], item[1])
        if persona in seen_personas:
            continue
        selected.append(item)
        seen_personas.add(persona)
        if len(selected) >= limit:
            return selected
    # If there are fewer unique personas than requested, retain configured availability.
    for item in ranked:
        if item not in selected:
            selected.append(item)
            if len(selected) >= limit:
                break
    return selected
