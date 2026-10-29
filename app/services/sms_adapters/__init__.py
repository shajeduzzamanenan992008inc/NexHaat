"""SMS provider adapters with provider-independent interface."""

from dataclasses import dataclass
from enum import Enum


class SmsErrorClass(Enum):
    SUCCESS = "success"
    AUTH = "auth"
    QUOTA = "quota"
    INVALID_NUMBER = "invalid_number"
    RATE_LIMITED = "rate_limited"
    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    CONFIG = "config"


@dataclass
class SmsResult:
    success: bool
    message_id: str | None = None
    error_class: SmsErrorClass = SmsErrorClass.UNKNOWN
    error_message: str | None = None  # Internal only, never expose to end users


class SmsAdapter:
    """Base class for SMS provider adapters."""

    def send(self, phone: str, message: str, sender_id: str | None = None) -> SmsResult:
        raise NotImplementedError
