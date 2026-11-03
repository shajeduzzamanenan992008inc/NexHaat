"""Session-authenticated REST endpoints for account access."""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, request, session
from werkzeug.security import generate_password_hash
from flask_login import logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import select

from ...extensions import db
from ...i18n import SUPPORTED_LOCALES
from ...models import (
    AdminLoginChallenge,
    CustomerProfile,
    RegistrationChallenge,
    SellerProfile,
    User,
)
from ...security import (
    clear_login_failures,
    current_session_user,
    login_is_throttled,
    record_login_failure,
)
from ...services.audit import record_audit
from ..errors import ApiError
from ..responses import created_response, success_response
from ..serializers import user_to_dict

auth_api = Blueprint("api_auth", __name__, url_prefix="/auth")


@auth_api.get("/csrf")
def csrf_token():
    """Return a CSRF token for state-changing API requests.

    API clients authenticate with the session cookie and echo this token back in
    the ``X-CSRFToken`` header on POST/PATCH/DELETE requests.
    """
    return success_response({"csrf_token": generate_csrf()})


@auth_api.post("/register")
def register():
    from ...routes.auth import (
        EMAIL_PATTERN,
        _create_registration_challenge,
        _password_length_error,
        _staff_email_ready,
    )

    payload = request.get_json(silent=True) or {}
    role = str(payload.get("role", "customer")).strip().lower()
    email = str(payload.get("email", "")).strip().lower()
    full_name = str(payload.get("full_name", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    password = payload.get("password", "")
    if role not in {"customer", "seller"}:
        raise ApiError("Choose customer or seller registration.", "VALIDATION_ERROR", 422)
    if not EMAIL_PATTERN.fullmatch(email) or len(email) > 255:
        raise ApiError("Enter a valid email address.", "VALIDATION_ERROR", 422)
    if not 2 <= len(full_name) <= 120 or not 7 <= len(phone) <= 30:
        raise ApiError("Enter a valid name and phone number.", "VALIDATION_ERROR", 422)
    password_error = _password_length_error(password)
    if password_error:
        raise ApiError(str(password_error), "VALIDATION_ERROR", 422)
    if db.session.scalar(select(User.id).where(User.email == email)):
        raise ApiError("An account with this email already exists.", "CONFLICT", 409)
    if not _staff_email_ready():
        raise ApiError("Email verification is unavailable.", "EMAIL_UNAVAILABLE", 503)

    if role == "customer":
        profile_data = {"full_name": full_name, "phone": phone}
    else:
        store_name = str(payload.get("store_name", "")).strip()
        business_address = str(payload.get("business_address", "")).strip()
        if not 2 <= len(store_name) <= 120 or len(business_address) > 500:
            raise ApiError("Enter valid seller store details.", "VALIDATION_ERROR", 422)
        profile_data = {
            "store_name": store_name,
            "contact_name": full_name,
            "phone": phone,
            "business_address": business_address or None,
        }
    challenge = _create_registration_challenge(
        email=email, role=role, password=password, profile_data=profile_data
    )
    return success_response(
        {"email": challenge.email, "expires_at": challenge.expires_at.isoformat()},
        message="Verification code sent.",
        status=202,
    )


@auth_api.post("/register/verify")
def verify_registration():
    from ...routes.auth import (
        REGISTRATION_CODE_MAX_ATTEMPTS,
        _as_utc,
        _reset_code_digest,
    )

    challenge_id = session.get("registration_challenge_id")
    challenge = db.session.get(RegistrationChallenge, challenge_id) if challenge_id else None
    now = datetime.now(UTC)
    expires = _as_utc(challenge.expires_at) if challenge else None
    if not challenge or challenge.consumed_at or not expires or expires < now:
        if challenge:
            db.session.delete(challenge)
            db.session.commit()
        session.pop("registration_challenge_id", None)
        raise ApiError("Registration code is invalid or expired.", "CODE_EXPIRED", 400)

    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip()
    if not re.fullmatch(r"[0-9]{6}", code) or not hmac.compare_digest(
        _reset_code_digest(code), challenge.code_hash
    ):
        challenge.failed_attempts += 1
        locked = challenge.failed_attempts >= REGISTRATION_CODE_MAX_ATTEMPTS
        if locked:
            db.session.delete(challenge)
            session.pop("registration_challenge_id", None)
        db.session.commit()
        raise ApiError(
            "Too many incorrect codes." if locked else "The verification code is incorrect.",
            "CODE_LOCKED" if locked else "INVALID_CODE",
            429 if locked else 400,
        )

    if db.session.scalar(select(User.id).where(User.email == challenge.email)):
        db.session.delete(challenge)
        db.session.commit()
        session.pop("registration_challenge_id", None)
        raise ApiError("An account with this email already exists.", "CONFLICT", 409)

    user = User(
        email=challenge.email,
        role=challenge.role,
        password_hash=challenge.password_hash,
        preferred_locale=(
            challenge.locale if challenge.locale in SUPPORTED_LOCALES else None
        ),
    )
    if challenge.role == "customer":
        user.customer_profile = CustomerProfile(**challenge.profile_data)
    else:
        user.seller_profile = SellerProfile(
            **challenge.profile_data,
            approval_status="pending",
        )
    db.session.delete(challenge)
    db.session.add(user)
    db.session.commit()
    session.pop("registration_challenge_id", None)
    record_audit("auth.register", actor=user)
    return created_response(user_to_dict(user), "Account verified and created.")


@auth_api.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = payload.get("password", "")
    if not isinstance(password, str) or len(password) > current_app.config["MAX_PASSWORD_LENGTH"]:
        password = ""
    remote_addr = request.remote_addr
    if login_is_throttled(remote_addr):
        raise ApiError("Too many attempts. Try again later.", "RATE_LIMITED", 429)
    user = db.session.scalar(select(User).where(User.email == email)) if email else None
    valid = bool(
        user and user.is_active and user.role in {"customer", "seller", "rider"}
        and user.check_password(password)
    )
    if not valid:
        record_login_failure(remote_addr)
        raise ApiError("Invalid email or password.", "INVALID_CREDENTIALS", 401)
    clear_login_failures(remote_addr)
    from ...routes.auth import _start_authenticated_session
    _start_authenticated_session(user)
    record_audit("auth.login", actor=user)
    return success_response(user_to_dict(user), "Signed in.")


@auth_api.post("/logout")
def logout():
    user = current_session_user()
    if user:
        record_audit("auth.logout", actor=user)
    logout_user()
    session.clear()
    return success_response(message="Signed out.")


@auth_api.get("/me")
def me():
    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)
    return success_response(user_to_dict(user))


@auth_api.post("/admin/code")
def request_admin_code():
    from ...routes.auth import (
        ADMIN_LOGIN_CODE_RESEND_SECONDS,
        ADMIN_LOGIN_CODE_TTL,
        _as_utc,
        _queue_admin_code,
        _reset_code_digest,
        _staff_email_ready,
    )

    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    remote_addr = request.remote_addr
    if login_is_throttled(remote_addr):
        raise ApiError("Too many attempts. Try again later.", "RATE_LIMITED", 429)
    user = db.session.scalar(select(User).where(User.email == email)) if email else None
    now = datetime.now(UTC)
    if user and user.role == "admin" and user.is_active and _staff_email_ready():
        latest = db.session.scalar(
            select(AdminLoginChallenge)
            .where(AdminLoginChallenge.user_id == user.id)
            .order_by(AdminLoginChallenge.sent_at.desc())
            .limit(1)
        )
        last_sent = _as_utc(latest.sent_at) if latest else None
        if last_sent is None or (now - last_sent).total_seconds() >= ADMIN_LOGIN_CODE_RESEND_SECONDS:
            for previous in db.session.scalars(
                select(AdminLoginChallenge).where(
                    AdminLoginChallenge.user_id == user.id,
                    AdminLoginChallenge.consumed_at.is_(None),
                )
            ):
                previous.consumed_at = now
            code = f"{secrets.randbelow(1_000_000):06d}"
            challenge = AdminLoginChallenge(
                id=secrets.token_urlsafe(32),
                user_id=user.id,
                code_hash=_reset_code_digest(code),
                sent_at=now,
                expires_at=now + ADMIN_LOGIN_CODE_TTL,
                failed_attempts=0,
            )
            db.session.add(challenge)
            db.session.commit()
            session["admin_login_challenge_id"] = challenge.id
            _queue_admin_code(user, code)
        elif latest:
            session["admin_login_challenge_id"] = latest.id
    elif user and user.role != "admin":
        record_login_failure(remote_addr)
        record_audit("auth.admin_login_denied", target_id=email, detail="not an admin account")
        raise ApiError("That email is not an Admin account.", "NOT_ADMIN", 403)
    else:
        record_login_failure(remote_addr)
    return success_response(
        {"code_requested": True},
        message="If an active Admin account matches that email, a sign-in code will be sent.",
        status=202,
    )


@auth_api.post("/admin/verify")
def verify_admin_code():
    from ...routes.auth import (
        ADMIN_LOGIN_CODE_MAX_ATTEMPTS,
        _as_utc,
        _reset_code_digest,
        _start_authenticated_session,
    )

    remote_addr = request.remote_addr
    if login_is_throttled(remote_addr):
        raise ApiError("Too many attempts. Request a new sign-in code.", "RATE_LIMITED", 429)
    challenge_id = session.get("admin_login_challenge_id")
    challenge = db.session.get(AdminLoginChallenge, challenge_id) if challenge_id else None
    user = db.session.get(User, challenge.user_id) if challenge else None
    now = datetime.now(UTC)
    expires = _as_utc(challenge.expires_at) if challenge else None
    valid_challenge = bool(
        challenge and challenge.consumed_at is None and expires and expires >= now
        and user and user.role == "admin" and user.is_active
    )
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip()
    valid_code = bool(
        valid_challenge and re.fullmatch(r"[0-9]{6}", code)
        and hmac.compare_digest(_reset_code_digest(code), challenge.code_hash)
    )
    if not valid_code:
        if challenge and challenge.consumed_at is None:
            if valid_challenge:
                challenge.failed_attempts += 1
                locked = challenge.failed_attempts >= ADMIN_LOGIN_CODE_MAX_ATTEMPTS
            else:
                locked = True
            if locked:
                db.session.delete(challenge)
                session.pop("admin_login_challenge_id", None)
            db.session.commit()
        record_login_failure(remote_addr)
        raise ApiError(
            "The code is incorrect or expired.", "INVALID_CODE", 400
        )

    challenge.consumed_at = now
    db.session.commit()
    clear_login_failures(remote_addr)
    session.pop("admin_login_challenge_id", None)
    _start_authenticated_session(user, permanent=True)
    record_audit("auth.admin_login", actor=user)
    return success_response(user_to_dict(user), "Admin signed in.")


@auth_api.post("/forgot-password")
def forgot_password():
    from ...routes.auth import (
        EMAIL_PATTERN,
        _as_utc,
        _reset_code_digest,
    )
    from ...services.mail import queue_password_reset_code

    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    if not EMAIL_PATTERN.fullmatch(email) or len(email) > 255:
        raise ApiError("Enter a valid email address.", "VALIDATION_ERROR", 422)

    user = db.session.scalar(select(User).where(User.email == email))
    if user and user.is_active and user.role != "admin":
        now = datetime.now(UTC)
        sent_at = _as_utc(user.password_reset_sent_at)
        previous_expiry = _as_utc(user.password_reset_expires_at)
        token_still_valid = bool(user.password_reset_hash and previous_expiry and previous_expiry > now)
        cooldown_elapsed = sent_at is None or (now - sent_at).total_seconds() >= 60
        if cooldown_elapsed or not token_still_valid:
            code = f"{secrets.randbelow(1_000_000):06d}"
            user.password_reset_hash = _reset_code_digest(code)
            user.password_reset_expires_at = now + timedelta(minutes=10)
            user.password_reset_sent_at = now
            user.password_reset_attempts = 0
            db.session.commit()
            reset_locale = (
                user.preferred_locale
                if user.preferred_locale in SUPPORTED_LOCALES
                else "en"
            )
            queue_password_reset_code(user.email, code, locale=reset_locale)
    return success_response(
        {"email": email},
        message="If an active account exists for that email, a verification code has been sent.",
    )


@auth_api.post("/reset-password")
def reset_password():
    from ...routes.auth import (
        _as_utc,
        _password_length_error,
        _reset_code_digest,
    )

    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    new_password = payload.get("new_password", "")

    if not email or not code or not new_password:
        raise ApiError("Email, verification code, and new password are required.", "VALIDATION_ERROR", 422)

    user = db.session.scalar(select(User).where(User.email == email))
    expires = _as_utc(user.password_reset_expires_at) if user else None
    valid_token = bool(
        user and user.is_active and user.role != "admin"
        and user.password_reset_hash and expires and expires >= datetime.now(UTC)
    )

    digest = _reset_code_digest(code)
    if not valid_token or not hmac.compare_digest(digest, user.password_reset_hash):
        if valid_token:
            user.password_reset_attempts += 1
            if user.password_reset_attempts >= 5:
                user.password_reset_hash = None
                user.password_reset_expires_at = None
                db.session.commit()
                raise ApiError("Too many incorrect codes. Request a new verification code.", "CODE_LOCKED", 429)
            db.session.commit()
        raise ApiError("The verification code is incorrect or has expired.", "INVALID_CODE", 400)

    password_error = _password_length_error(new_password)
    if password_error:
        raise ApiError(str(password_error), "VALIDATION_ERROR", 422)

    user.set_password(new_password)
    user.auth_version += 1
    user.password_reset_hash = None
    user.password_reset_expires_at = None
    user.password_reset_attempts = 0
    db.session.commit()
    record_audit("auth.reset_password", actor=user)
    return success_response(None, "Password updated successfully. You can now sign in.")


@auth_api.post("/social-login")
def social_login():
    from ...routes.auth import _start_authenticated_session

    payload = request.get_json(silent=True) or {}
    provider = str(payload.get("provider", "google")).strip().lower()
    email = str(payload.get("email", "")).strip().lower()
    display_name = str(payload.get("display_name", "")).strip()

    if not email or "@" not in email:
        raise ApiError("Valid email is required for social sign-in.", "VALIDATION_ERROR", 422)

    user = db.session.scalar(select(User).where(User.email == email))
    if user:
        if not user.is_active:
            raise ApiError("This account is suspended.", "ACCOUNT_SUSPENDED", 403)
        _start_authenticated_session(user)
        record_audit("auth.social_login", actor=user, detail=f"provider:{provider}")
        return success_response(user_to_dict(user), f"Signed in with {provider.capitalize()}.")

    # Auto-create customer account
    user = User(
        email=email,
        role="customer",
        password_hash=generate_password_hash(secrets.token_urlsafe(32)),
        preferred_locale=session.get("locale", "en"),
    )
    user.customer_profile = CustomerProfile(
        full_name=display_name or email.split("@")[0],
        phone="+8801700000000",
    )
    db.session.add(user)
    db.session.commit()
    _start_authenticated_session(user)
    record_audit("auth.social_register", actor=user, detail=f"provider:{provider}")
    return created_response(user_to_dict(user), f"Account created and signed in with {provider.capitalize()}.")


@auth_api.post("/2fa/setup")
def setup_2fa():
    import base64
    import urllib.parse

    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)

    raw_bytes = secrets.token_bytes(20)
    secret = base64.b32encode(raw_bytes).decode("ascii").rstrip("=")
    session["totp_pending_secret"] = secret
    backup_codes = [f"{secrets.randbelow(100_000_000):08d}" for _ in range(8)]
    session["totp_backup_codes"] = backup_codes
    otpauth_url = f"otpauth://totp/NexHaat:{user.email}?secret={secret}&issuer=NexHaat"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={urllib.parse.quote(otpauth_url)}"

    return success_response({
        "secret": secret,
        "qr_code_url": qr_code_url,
        "backup_codes": backup_codes,
    }, "Two-factor authentication setup initiated.")


@auth_api.post("/2fa/verify")
def verify_2fa():
    import base64
    import struct
    import time

    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)

    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip().replace(" ", "")
    secret = str(payload.get("secret", "")).strip() or session.get("totp_pending_secret", "")

    if not code:
        raise ApiError("Verification code is required.", "VALIDATION_ERROR", 422)

    # Check if matches any backup code
    backup_codes = session.get("totp_backup_codes", [])
    if code in backup_codes:
        backup_codes.remove(code)
        session["totp_backup_codes"] = backup_codes
        session["two_factor_verified"] = True
        record_audit("auth.2fa_backup_code_used", actor=user)
        return success_response({"two_factor_enabled": True}, "Verified with backup code.")

    # Verify RFC 6238 TOTP
    clean_secret = secret.replace(" ", "").upper()
    pad = (8 - len(clean_secret) % 8) % 8
    try:
        key = base64.b32decode(clean_secret + "=" * pad)
        current_step = int(time.time() // 30)
        target_code = int(code)
        valid = False
        for step in (current_step - 1, current_step, current_step + 1):
            msg = struct.pack(">Q", step)
            h = hmac.new(key, msg, hashlib.sha1).digest()
            offset = h[-1] & 0x0F
            token = (struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
            if token == target_code:
                valid = True
                break
    except Exception:
        valid = False

    if not valid:
        raise ApiError("The 6-digit authenticator code is incorrect.", "INVALID_CODE", 400)

    session["two_factor_verified"] = True
    session["totp_secret"] = clean_secret
    session.pop("totp_pending_secret", None)
    record_audit("auth.2fa_enabled", actor=user)
    return success_response({"two_factor_enabled": True}, "Two-factor authentication verified and enabled.")

