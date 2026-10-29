import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

from flask import current_app, has_request_context, request
from sqlalchemy import delete, select

from ..extensions import db
from ..models import PhoneOtpChallenge
from ..security import (
    login_is_throttled,
    phone_is_throttled,
    record_login_failure,
    record_phone_failure,
    reset_code_digest,
)
from .phone import is_valid_bangladesh_phone, normalize_bangladesh_phone, redact_phone
from .sms_adapters import SmsErrorClass
from .sms_adapters.alpha_sms import AlphaSmsAdapter

logger = logging.getLogger(__name__)

PHONE_OTP_TTL = timedelta(minutes=10)
PHONE_OTP_RESEND_SECONDS = 60
PHONE_OTP_MAX_ATTEMPTS = 5


def _get_adapter():
    provider = (current_app.config.get("SMS_PROVIDER") or "").strip().lower()
    if provider == "alpha_sms" or provider == "sms_bd":
        return AlphaSmsAdapter()
    # Default to Alpha SMS if not specified but enabled
    return AlphaSmsAdapter()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def send_phone_otp(phone: str, purpose: str = "verify", user_id: int | None = None) -> tuple[bool, str | None]:
    """Send a phone OTP. Returns (success, error_code). Never returns the code."""
    if not current_app.config.get("SMS_ENABLED"):
        return False, "SMS_DISABLED"

    normalized = normalize_bangladesh_phone(phone)
    if not normalized or not is_valid_bangladesh_phone(normalized):
        return False, "INVALID_PHONE"

    # Basic rate limiting
    remote_addr = request.remote_addr if has_request_context() else None
    if remote_addr and login_is_throttled(remote_addr):
        return False, "RATE_LIMITED"
    if phone_is_throttled(normalized):
        return False, "RATE_LIMITED"

    now = datetime.now(UTC)
    # Check for existing active challenge with locking to prevent races
    existing = db.session.scalar(
        select(PhoneOtpChallenge)
        .where(
            PhoneOtpChallenge.phone_canonical == normalized,
            PhoneOtpChallenge.purpose == purpose,
            PhoneOtpChallenge.consumed_at.is_(None),
            PhoneOtpChallenge.expires_at > now,
        )
        .order_by(PhoneOtpChallenge.sent_at.desc())
        .with_for_update()
    )
    if existing:
        sent_at = existing.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=UTC)
        if (now - sent_at).total_seconds() < PHONE_OTP_RESEND_SECONDS:
            db.session.rollback()
            return False, "RESEND_COOLDOWN"
        # If past cooldown, we'll replace by creating new one; mark old as consumed
        existing.consumed_at = now

    # Clean up old challenges
    db.session.execute(
        delete(PhoneOtpChallenge).where(
            (PhoneOtpChallenge.expires_at < now)
            | PhoneOtpChallenge.consumed_at.is_not(None)
        )
    )

    code = _generate_code()
    challenge = PhoneOtpChallenge(
        id=secrets.token_urlsafe(32),
        phone_canonical=normalized,
        purpose=purpose,
        user_id=user_id,
        code_hash=reset_code_digest(code),
        sent_at=now,
        expires_at=now + PHONE_OTP_TTL,
        failed_attempts=0,
        locale=str(current_app.config.get("BABEL_DEFAULT_LOCALE", "en_US")),
    )
    db.session.add(challenge)
    db.session.commit()

    adapter = _get_adapter()
    sender_id = current_app.config.get("SMS_SENDER_ID") or None
    message = f"Your NexHaat verification code is {code}. It expires in 10 minutes."

    try:
        result = adapter.send(normalized, message, sender_id=sender_id)
    except Exception:
        logger.warning("SMS send failed for %s", redact_phone(normalized))
        if remote_addr:
            record_login_failure(remote_addr)
        record_phone_failure(normalized)
        return False, "SEND_FAILED"

    if result.success:
        if result.message_id:
            challenge.provider_message_id = str(result.message_id)[:128]
            db.session.commit()
        return True, None
    logger.warning("SMS send failed for %s (error_class=%s)", redact_phone(normalized), result.error_class.value)
    if remote_addr:
        record_login_failure(remote_addr)
    record_phone_failure(normalized)
    # Classify errors safely - don't leak details
    if result.error_class in (SmsErrorClass.AUTH, SmsErrorClass.CONFIG) or result.error_class == SmsErrorClass.QUOTA:
        return False, "PROVIDER_ERROR"
    if result.error_class == SmsErrorClass.RATE_LIMITED:
        return False, "RATE_LIMITED"
    if result.error_class == SmsErrorClass.INVALID_NUMBER:
        return False, "INVALID_PHONE"
    if result.error_class == SmsErrorClass.TIMEOUT:
        return False, "SEND_FAILED"  # Ambiguous - treat as failed, don't retry blindly
    return False, "SEND_FAILED"


def verify_phone_otp(phone: str, code: str, purpose: str = "verify") -> tuple[bool, str | None]:
    """Verify a phone OTP. Returns (success, error_code)."""
    if not current_app.config.get("SMS_ENABLED"):
        return False, "SMS_DISABLED"

    normalized = normalize_bangladesh_phone(phone)
    if not normalized or not is_valid_bangladesh_phone(normalized):
        return False, "INVALID_PHONE"

    if not code or not isinstance(code, str):
        return False, "INVALID_CODE"

    if phone_is_throttled(normalized):
        return False, "RATE_LIMITED"

    now = datetime.now(UTC)
    challenge = db.session.scalar(
        select(PhoneOtpChallenge)
        .where(
            PhoneOtpChallenge.phone_canonical == normalized,
            PhoneOtpChallenge.purpose == purpose,
            PhoneOtpChallenge.consumed_at.is_(None),
        )
        .order_by(PhoneOtpChallenge.sent_at.desc())
        .with_for_update()
    )

    if not challenge:
        return False, "INVALID_CODE"

    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at < now:
        challenge.consumed_at = now
        db.session.commit()
        record_phone_failure(normalized)
        return False, "CODE_EXPIRED"

    if not hmac.compare_digest(reset_code_digest(code.strip()), challenge.code_hash):
        challenge.failed_attempts += 1
        if challenge.failed_attempts >= PHONE_OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
            db.session.commit()
            record_phone_failure(normalized)
            return False, "CODE_LOCKED"
        db.session.commit()
        record_phone_failure(normalized)
        return False, "INVALID_CODE"

    challenge.consumed_at = now
    db.session.commit()
    return True, None
