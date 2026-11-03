"""Session-authenticated REST endpoints for account access."""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, jsonify, request, session
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
    UserBackupCode,
    UserTwoFactor,
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

    if user.is_totp_enabled:
        challenge_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        session.clear()
        session["pending_2fa_user_id"] = user.id
        session["pending_2fa_challenge_id"] = challenge_id
        session["pending_2fa_expires_at"] = expires_at.isoformat()
        session["pending_2fa_attempts"] = 0
        record_audit("auth.login_2fa_challenge_issued", actor=user)
        response = jsonify({
            "success": True,
            "two_factor_required": True,
            "data": {
                "challenge_id": challenge_id,
                "expires_at": expires_at.isoformat(),
                "two_factor_required": True,
            },
            "message": "Two-factor authentication required. Enter your authenticator or backup code.",
        })
        response.status_code = 202
        return response

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


SOCIAL_PROVIDERS = frozenset({"google", "microsoft", "github"})
TWO_FACTOR_MAX_ATTEMPTS = 5


@auth_api.post("/social-login")
def social_login():
    """Refuse provider sign-in until a verified token flow exists.

    An earlier implementation started a session from a client-supplied email
    address, which let any caller sign in as any account. Identity must come from
    a provider token whose issuer, audience, expiry, and signature are verified on
    the server. Until that verification is configured this route fails closed and
    never falls back to email-only authentication.
    """
    payload = request.get_json(silent=True) or {}
    provider = str(payload.get("provider", "")).strip().lower()
    remote_addr = request.remote_addr

    if login_is_throttled(remote_addr):
        raise ApiError("Too many attempts. Try again later.", "RATE_LIMITED", 429)
    if provider not in SOCIAL_PROVIDERS:
        record_login_failure(remote_addr)
        raise ApiError("Choose a supported sign-in provider.", "UNSUPPORTED_PROVIDER", 422)

    record_audit("auth.social_login_blocked", detail=f"provider:{provider}")
    raise ApiError(
        "Social sign-in is not available yet. Use email and password.",
        "SOCIAL_LOGIN_UNAVAILABLE",
        503,
    )


@auth_api.get("/2fa/status")
def two_factor_status():
    """Return the current user's 2FA status and remaining backup codes."""
    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)

    from ...services.two_factor import get_backup_codes_remaining_count

    remaining = get_backup_codes_remaining_count(user.id) if user.is_totp_enabled else 0
    return success_response({
        "enabled": user.is_totp_enabled,
        "confirmed_at": user.two_factor.confirmed_at.isoformat() if (user.two_factor and user.two_factor.confirmed_at) else None,
        "backup_codes_remaining": remaining,
    })


@auth_api.post("/2fa/setup")
def setup_2fa():
    """Start 2FA setup.

    Generates a secure secret, encrypts it with AES-256-GCM, stores unconfirmed record,
    and returns the provisioning URI and backup codes. Never sends data to external QR APIs.
    """
    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)

    from ...services.two_factor import (
        generate_backup_codes,
        generate_totp_secret,
        get_provisioning_uri,
        save_backup_codes,
    )
    from ...services.two_factor_crypto import encrypt_totp_secret

    secret = generate_totp_secret()
    encrypted_secret, version = encrypt_totp_secret(secret)

    if user.two_factor:
        user.two_factor.encrypted_secret = encrypted_secret
        user.two_factor.encryption_key_version = version
        user.two_factor.enabled = False
        user.two_factor.confirmed_at = None
        user.two_factor.updated_at = datetime.now(UTC)
    else:
        tf = UserTwoFactor(
            user_id=user.id,
            encrypted_secret=encrypted_secret,
            encryption_key_version=version,
            enabled=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.session.add(tf)

    backup_codes = generate_backup_codes(8)
    save_backup_codes(user.id, backup_codes)
    db.session.commit()

    provisioning_uri = get_provisioning_uri(user.email, secret)
    record_audit("auth.2fa_setup_initiated", actor=user)

    return success_response({
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "backup_codes": backup_codes,
    }, "Two-factor authentication setup initiated.")


@auth_api.post("/2fa/confirm")
@auth_api.post("/2fa/verify")
def confirm_2fa():
    """Verify code and activate 2FA for the authenticated user."""
    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)

    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip().replace(" ", "")
    if not code:
        raise ApiError("Verification code is required.", "VALIDATION_ERROR", 422)

    tf = user.two_factor
    if not tf or not tf.encrypted_secret:
        raise ApiError(
            "Two-factor setup expired or was not initiated. Start setup again.",
            "SETUP_EXPIRED",
            400,
        )

    from ...services.two_factor import verify_totp_code
    from ...services.two_factor_crypto import decrypt_totp_secret

    secret = decrypt_totp_secret(tf.encrypted_secret, version=tf.encryption_key_version)
    valid, step = verify_totp_code(secret, code, last_used_step=tf.last_used_step)

    if not valid:
        record_audit("auth.2fa_confirm_failed", actor=user)
        raise ApiError("The 6-digit authenticator code is incorrect or expired.", "INVALID_CODE", 400)

    tf.enabled = True
    tf.confirmed_at = datetime.now(UTC)
    tf.last_used_step = step
    tf.updated_at = datetime.now(UTC)
    user.auth_version += 1
    session["auth_version"] = user.auth_version
    db.session.commit()

    record_audit("auth.2fa_enabled", actor=user)
    return success_response({"two_factor_enabled": True}, "Two-factor authentication verified and enabled.")


@auth_api.post("/2fa/challenge")
def challenge_2fa():
    """Verify second-factor code (TOTP or backup code) during login."""
    remote_addr = request.remote_addr
    if login_is_throttled(remote_addr):
        raise ApiError("Too many attempts. Try again later.", "RATE_LIMITED", 429)

    pending_user_id = session.get("pending_2fa_user_id")
    pending_challenge_id = session.get("pending_2fa_challenge_id")
    expires_at_str = session.get("pending_2fa_expires_at")

    if not pending_user_id or not pending_challenge_id or not expires_at_str:
        raise ApiError("No pending two-factor challenge. Please sign in again.", "CHALLENGE_EXPIRED", 401)

    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(UTC) > expires_at:
            session.clear()
            raise ApiError("Two-factor challenge expired. Please sign in again.", "CHALLENGE_EXPIRED", 401)
    except (ValueError, TypeError):
        session.clear()
        raise ApiError("Two-factor challenge is invalid. Please sign in again.", "CHALLENGE_EXPIRED", 401)

    attempts = int(session.get("pending_2fa_attempts", 0) or 0)
    if attempts >= TWO_FACTOR_MAX_ATTEMPTS:
        session.clear()
        record_login_failure(remote_addr)
        raise ApiError("Too many incorrect codes. Please sign in again.", "CODE_LOCKED", 429)

    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip().replace(" ", "")
    if not code:
        raise ApiError("Verification code is required.", "VALIDATION_ERROR", 422)

    user = db.session.get(User, pending_user_id)
    if not user or not user.is_active or not user.is_totp_enabled:
        session.clear()
        raise ApiError("Invalid authentication state. Please sign in again.", "INVALID_SESSION", 401)

    from ...services.two_factor import verify_and_consume_backup_code, verify_totp_code
    from ...services.two_factor_crypto import decrypt_totp_secret

    authenticated = False
    if len(code) == 6 and code.isdigit():
        tf = user.two_factor
        secret = decrypt_totp_secret(tf.encrypted_secret, version=tf.encryption_key_version)
        valid, step = verify_totp_code(secret, code, last_used_step=tf.last_used_step)
        if valid:
            tf.last_used_step = step
            db.session.commit()
            authenticated = True
            record_audit("auth.login_2fa", actor=user)
    elif len(code) == 8 and code.isdigit():
        if verify_and_consume_backup_code(user.id, code):
            authenticated = True
            record_audit("auth.login_backup_code", actor=user)

    if not authenticated:
        session["pending_2fa_attempts"] = attempts + 1
        record_login_failure(remote_addr)
        raise ApiError("The verification code is incorrect or expired.", "INVALID_CODE", 400)

    session.clear()
    clear_login_failures(remote_addr)
    from ...routes.auth import _start_authenticated_session
    _start_authenticated_session(user)
    return success_response(user_to_dict(user), "Signed in successfully.")


@auth_api.post("/2fa/regenerate-backup-codes")
def regenerate_backup_codes():
    """Generate fresh backup codes, invalidating previous unused codes."""
    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)
    if not user.is_totp_enabled:
        raise ApiError("Two-factor authentication is not enabled.", "PRECONDITION_REQUIRED", 400)

    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", "")).strip()
    code = str(payload.get("code", "")).strip().replace(" ", "")

    reauth_ok = False
    if password and user.check_password(password):
        reauth_ok = True
    elif code and len(code) == 6 and code.isdigit():
        from ...services.two_factor import verify_totp_code
        from ...services.two_factor_crypto import decrypt_totp_secret
        secret = decrypt_totp_secret(user.two_factor.encrypted_secret, version=user.two_factor.encryption_key_version)
        valid, step = verify_totp_code(secret, code, last_used_step=user.two_factor.last_used_step)
        if valid:
            user.two_factor.last_used_step = step
            reauth_ok = True

    if not reauth_ok:
        raise ApiError("Your password or current authenticator code is required to regenerate backup codes.", "REAUTH_REQUIRED", 403)

    from ...services.two_factor import generate_backup_codes, save_backup_codes
    new_codes = generate_backup_codes(8)
    save_backup_codes(user.id, new_codes)
    record_audit("auth.2fa_backup_codes_regenerated", actor=user)

    return success_response({
        "backup_codes": new_codes,
    }, "New backup codes generated.")


@auth_api.post("/2fa/disable")
def disable_2fa():
    """Disable 2FA after password or TOTP reauthentication."""
    user = current_session_user()
    if not user:
        raise ApiError("Sign in is required.", "UNAUTHENTICATED", 401)
    if not user.is_totp_enabled:
        raise ApiError("Two-factor authentication is not enabled.", "PRECONDITION_REQUIRED", 400)

    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", "")).strip()
    code = str(payload.get("code", "")).strip().replace(" ", "")

    reauth_ok = False
    if password and user.check_password(password):
        reauth_ok = True
    elif code and len(code) == 6 and code.isdigit():
        from ...services.two_factor import verify_totp_code
        from ...services.two_factor_crypto import decrypt_totp_secret
        secret = decrypt_totp_secret(user.two_factor.encrypted_secret, version=user.two_factor.encryption_key_version)
        valid, step = verify_totp_code(secret, code, last_used_step=user.two_factor.last_used_step)
        if valid:
            reauth_ok = True

    if not reauth_ok:
        raise ApiError("Your password or current authenticator code is required to disable 2FA.", "REAUTH_REQUIRED", 403)

    from ...services.two_factor import revoke_all_backup_codes

    revoke_all_backup_codes(user.id)
    if user.two_factor:
        db.session.delete(user.two_factor)
    user.auth_version += 1
    session["auth_version"] = user.auth_version
    db.session.commit()

    record_audit("auth.2fa_disabled", actor=user)
    return success_response({"two_factor_enabled": False}, "Two-factor authentication has been disabled.")


