"""NextHaat AI Core package."""

from .core.provider import AIService
from .core.tools import ToolRegistry
from .marketplace_tools import build_customer_tool_registry, handle_marketplace_ai_query

__all__ = [
    "AIService",
    "ToolRegistry",
    "build_customer_tool_registry",
    "handle_marketplace_ai_query",
]


def get_ai_service(config=None, *, provider=None):
    """Return a configured AI service using the app config when available."""
    return AIService(config or {}, provider=provider)
