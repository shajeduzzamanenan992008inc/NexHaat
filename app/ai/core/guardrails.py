"""Application-level bounds and secret redaction for AI output and context."""

from __future__ import annotations

import re

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|client[_-]?secret|password|authorization|bearer|access[_-]?token)"
    r"\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+"
)
_MAX_RESPONSE_CHARS = 6000
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")


def redact_personal_data(value):
    """Remove common contact details before support text is sent to an AI provider."""
    text = str(value or "")
    text = _EMAIL_PATTERN.sub("[email removed]", text)
    return _PHONE_PATTERN.sub("[phone removed]", text)


def sanitize_ai_response(value, scope=None):
    """Bound model output and redact secret-shaped values without hiding ordinary words."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        import json

        value = json.dumps(value, ensure_ascii=False, default=str)
    text = _SECRET_ASSIGNMENT.sub(r"\1=[redacted]", str(value))
    text = "".join(character for character in text if character in "\n\t" or ord(character) >= 32)
    return text.strip()[:_MAX_RESPONSE_CHARS] or "I can’t verify that from the marketplace data right now."


def sanitize_prompt(value, *, max_chars=2000):
    """Validate and bound user-supplied prompt text before provider use."""
    if not isinstance(value, str):
        raise ValueError("Send a text question.")
    text = value.strip()
    if not text:
        raise ValueError("Send a question to continue.")
    if len(text) > max_chars:
        raise ValueError(f"Keep the question under {max_chars} characters.")
    return text
