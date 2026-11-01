"""Privacy-preserving AI event logging."""

import logging
import re

logger = logging.getLogger("nexhaat.ai")
_SAFE_FIELDS = {
    "scope", "tool", "status", "provider", "model", "latency_ms",
    "input_tokens", "output_tokens", "request_id", "reason",
}
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|authorization|bearer|token)\s*[:=]\s*[^\s,;]+"
)


def log_ai_event(event_type, **details):
    """Log only a small metadata allowlist; prompts and user data are never logged."""
    safe_details = {}
    for key, value in details.items():
        if key not in _SAFE_FIELDS:
            continue
        if isinstance(value, str):
            value = _SECRET_PATTERN.sub(r"\1=[redacted]", value[:120])
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            value = max(0, min(value, 2_147_483_647))
        else:
            continue
        safe_details[key] = value
    logger.info("AI_EVENT %s %s", str(event_type)[:50], safe_details)
    return safe_details
