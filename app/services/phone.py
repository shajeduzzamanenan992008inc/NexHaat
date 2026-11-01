"""Phone number normalization and validation for Bangladesh SMS OTP."""

import re

_E164_BD_RE = re.compile(r"^\+8801[3-9]\d{8}$")


def normalize_bangladesh_phone(phone: str) -> str | None:
    """Normalize a Bangladesh mobile number to E.164 format (+8801XXXXXXXXX).

    Returns None if the number cannot be normalized safely.
    """
    if not phone or not isinstance(phone, str):
        return None

    # Strip whitespace and common delimiters
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", phone.strip())

    if not cleaned:
        return None

    # Try to match various formats
    # Format: +8801XXXXXXXXX
    if cleaned.startswith("+880"):
        if _E164_BD_RE.match(cleaned):
            return cleaned
        return None
    # Format: 8801XXXXXXXXX
    if cleaned.startswith("880"):
        if cleaned.startswith("8801") and len(cleaned) == 13 and re.match(r"^8801[3-9]\d{8}$", cleaned):
            return f"+{cleaned}"
        return None
    # Format: 01XXXXXXXXX
    if cleaned.startswith("01"):
        if len(cleaned) == 11 and re.match(r"^01[3-9]\d{8}$", cleaned):
            return f"+880{cleaned[1:]}"
        return None
    return None


def is_valid_bangladesh_phone(phone: str) -> bool:
    """Check if a phone number is a valid Bangladesh mobile number."""
    return normalize_bangladesh_phone(phone) is not None


def redact_phone(phone: str) -> str:
    """Redact a phone number for safe logging."""
    normalized = normalize_bangladesh_phone(phone)
    if not normalized:
        # Try to redact as much as possible without guessing
        if not phone:
            return "[redacted]"
        cleaned = re.sub(r"[\s\-\(\)\.]+", "", phone.strip())
        if len(cleaned) > 4:
            return f"{cleaned[:3]}***{cleaned[-2:]}"
        return "[redacted]"

    # For +8801XXXXXXXXX, show +8801***XXXX
    if len(normalized) == 14:  # +880 + 1 + 8 digits = 4+1+8 = 13 chars total? +880 is 4 chars, 1XXXXXXXXX is 9 chars total = 13
        return f"+8801***{normalized[-4:]}"
    return "[redacted]"
