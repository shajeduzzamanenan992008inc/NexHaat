"""Application-level bounds and secret redaction for AI output and context."""

from __future__ import annotations

import re

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[\s_-]?key|client[\s_-]?secret|secret[\s_-]?key|private[\s_-]?key|password|authorization|bearer|access[\s_-]?token|refresh[\s_-]?token|bot[\s_-]?token)"
    r"\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+"
)
_SECRET_URL_PARAMETER = re.compile(
    r"(?i)([?&](?:api[\s_-]?key|key|token|access[\s_-]?token|secret)=)[^&\s]+"
)
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
)
_MAX_RESPONSE_CHARS = 6000
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
_INTERNAL_REASONING_MARKERS = (
    re.compile(r"(?i)\bhere(?:'s| is) (?:a )?(?:thinking|reasoning) process\s*:"),
    re.compile(r"(?i)\b(?:chain[- ]of[- ]thought|internal reasoning|internal analysis)\s*:"),
    re.compile(r"(?i)\bdraft response\s*\(\s*internal\s*\)\s*:"),
    re.compile(r"(?is)<\s*think(?:ing)?\b[^>]*>.*?</\s*think(?:ing)?\s*>"),
)
_TOOL_INVOCATION_MARKERS = re.compile(
    r"(?i)<\s*/?\s*(?:tool_use|tool_call|function_call|dots_function_call|invoke|"
    r"server_name|tool_name|parameter|platform_[a-z0-9_]+)\b"
)


def redact_personal_data(value):
    """Remove common contact details before support text is sent to an AI provider."""
    text = str(value or "")
    text = _EMAIL_PATTERN.sub("[email removed]", text)
    return _PHONE_PATTERN.sub("[phone removed]", text)


def redact_external_prompt(value):
    """Remove contact data and recognizable credential formats before API routing."""
    text = redact_personal_data(value)
    text = _SECRET_ASSIGNMENT.sub(r"\1=[secret removed]", text)
    text = _SECRET_URL_PARAMETER.sub(r"\1[secret removed]", text)
    text = _PRIVATE_KEY_BLOCK.sub("[private key removed]", text)
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub("[secret removed]", text)
    return text


def sanitize_ai_response(value, scope=None):
    """Bound model output, redact secrets, and reject internal control markup."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        import json

        value = json.dumps(value, ensure_ascii=False, default=str)
    text = str(value)
    if (any(marker.search(text) for marker in _INTERNAL_REASONING_MARKERS)
            or _TOOL_INVOCATION_MARKERS.search(text)):
        return ""
    text = _SECRET_ASSIGNMENT.sub(r"\1=[redacted]", text)
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


def sanitize_history(value, *, max_messages=8, max_chars=6000):
    """Accept only bounded user/assistant turns; no caller supplied system/tool role."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > max_messages:
        raise ValueError("Conversation context is too long. Start a new conversation.")
    output, size = [], 0
    for item in value:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise ValueError("Conversation context is invalid.")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > 1500:
            raise ValueError("Each conversation turn must be under 1,500 characters.")
        cleaned = redact_personal_data(content.strip())
        size += len(cleaned)
        if size > max_chars:
            raise ValueError("Conversation context is too long. Start a new conversation.")
        output.append({"role": item["role"], "content": cleaned})
    return output
