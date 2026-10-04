import pytest

from app.config import _env_bool


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_env_bool_accepts_true_values(monkeypatch, value):
    monkeypatch.setenv("TEST_BOOLEAN", value)

    assert _env_bool("TEST_BOOLEAN") is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "off"])
def test_env_bool_accepts_false_values(monkeypatch, value):
    monkeypatch.setenv("TEST_BOOLEAN", value)

    assert _env_bool("TEST_BOOLEAN") is False


def test_env_bool_rejects_unknown_values(monkeypatch):
    monkeypatch.setenv("TEST_BOOLEAN", "maybe")

    with pytest.raises(ValueError):
        _env_bool("TEST_BOOLEAN")
