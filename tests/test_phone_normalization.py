from app.services.phone import is_valid_bangladesh_phone, normalize_bangladesh_phone, redact_phone


def test_normalize_bangladesh_phone_formats():
    assert normalize_bangladesh_phone("01712345678") == "+8801712345678"
    assert normalize_bangladesh_phone("+8801712345678") == "+8801712345678"
    assert normalize_bangladesh_phone("8801712345678") == "+8801712345678"


def test_normalize_bangladesh_phone_with_separators():
    assert normalize_bangladesh_phone("+880 1712345678") == "+8801712345678"
    assert normalize_bangladesh_phone("01-7123-45678") == "+8801712345678"


def test_normalize_bangladesh_phone_invalid():
    assert normalize_bangladesh_phone("12345") is None
    assert normalize_bangladesh_phone("+1234567890") is None
    assert normalize_bangladesh_phone("") is None
    assert is_valid_bangladesh_phone("invalid") is False


def test_redact_phone():
    redacted = redact_phone("+8801712345678")
    assert redacted != "+8801712345678"
    assert "880" in redacted
    assert "***" in redacted
