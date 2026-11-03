"""Regression tests for provider sign-in and two-factor enrollment hardening.

An earlier ``POST /api/v1/auth/social-login`` started a session from a
client-supplied email address, which allowed account takeover. These tests pin
the fail-closed behaviour and the rule that the TOTP secret must come from the
server, never from the caller.
"""

import base64
import hashlib
import hmac
import struct
import time

from sqlalchemy import select

from app.extensions import db
from app.models import User

ATTACKER_SECRET = "JBSWY3DPEHPK3PXP"


def _create_customer(email="victim@example.com", password="correct-horse"):
    user = User(email=email, role="customer")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _totp(secret, step_offset=0):
    """Compute a valid RFC 6238 code so a client-controlled secret would pass."""
    padding = (8 - len(secret) % 8) % 8
    key = base64.b32decode(secret + "=" * padding)
    step = int(time.time() // 30) + step_offset
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def test_social_login_cannot_take_over_an_existing_account(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    _create_customer()

    response = client.post(
        "/api/v1/auth/social-login",
        json={
            "provider": "google",
            "email": "victim@example.com",
            "display_name": "Attacker",
            "token": "not-a-real-id-token",
        },
    )

    assert response.status_code == 503
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "SOCIAL_LOGIN_UNAVAILABLE"

    # No session may be created from an unverified email claim.
    assert client.get("/api/v1/auth/me").status_code == 401


def test_social_login_does_not_create_accounts_from_unverified_email(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)

    response = client.post(
        "/api/v1/auth/social-login",
        json={"provider": "microsoft", "email": "new.attacker@example.com"},
    )

    assert response.status_code == 503
    assert db.session.scalar(
        select(User).where(User.email == "new.attacker@example.com")
    ) is None
    assert client.get("/api/v1/auth/me").status_code == 401


def test_social_login_rejects_unknown_provider(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)

    response = client.post(
        "/api/v1/auth/social-login",
        json={"provider": "myspace", "email": "someone@example.com"},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_PROVIDER"


def test_two_factor_verify_ignores_caller_supplied_secret(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    _create_customer()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200

    response = client.post(
        "/api/v1/auth/2fa/verify",
        json={"code": _totp(ATTACKER_SECRET), "secret": ATTACKER_SECRET},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "SETUP_EXPIRED"
    with client.session_transaction() as flask_session:
        assert "two_factor_verified" not in flask_session


def test_two_factor_verify_requires_a_server_started_setup(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    _create_customer()

    client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "correct-horse"},
    )

    response = client.post("/api/v1/auth/2fa/verify", json={"code": "123456"})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "SETUP_EXPIRED"
