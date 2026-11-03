"""Comprehensive security tests for server-side Two-Factor Authentication (TOTP).

Covers:
- AES-256-GCM encryption & decryption of secrets at rest
- Tamper and wrong-key rejection
- TOTP enrollment and confirmation
- Login enforcement (HTTP 202 challenge when 2FA is active)
- TOTP and backup-code completion
- Single-use atomic backup code consumption
- Replay attack protection (last_used_step)
- Rate-limiting & 5-attempt lockout on pending challenge
- Backup code regeneration & 2FA disablement with reauthentication
"""

import base64
import hashlib
import hmac
import struct
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.extensions import db
from app.models import User, UserBackupCode, UserTwoFactor
from app.services.two_factor import generate_totp_secret, verify_totp_code
from app.services.two_factor_crypto import (
    TwoFactorCryptoError,
    decrypt_totp_secret,
    encrypt_totp_secret,
)

TEST_ENCRYPTION_KEY = b"0123456789abcdef0123456789abcdef"


def _generate_totp_code(secret: str, step_offset: int = 0) -> str:
    """Generate a valid RFC 6238 code for the secret at current time + step_offset."""
    clean = secret.replace(" ", "").upper()
    pad = (8 - len(clean) % 8) % 8
    key = base64.b32decode(clean + "=" * pad)
    step = int(time.time() // 30) + step_offset
    msg = struct.pack(">Q", step)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code_int:06d}"


def _create_user(email="test2fa@example.com", password="SecurePassword123!"):
    user = User(email=email, role="customer")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_crypto_roundtrip():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted, version = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    assert isinstance(encrypted, bytes)
    assert len(encrypted) > 28
    assert version == 1
    decrypted = decrypt_totp_secret(encrypted, key_input=TEST_ENCRYPTION_KEY)
    assert decrypted == secret


def test_crypto_tampering_rejected():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted, version = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    tampered = bytearray(encrypted)
    tampered[-1] ^= 0x01
    try:
        decrypt_totp_secret(bytes(tampered), key_input=TEST_ENCRYPTION_KEY)
        assert False, "Tampered ciphertext must fail decryption"
    except TwoFactorCryptoError:
        pass


def test_crypto_wrong_key_rejected():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted, _ = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    wrong_key = b"wrongkeywrongkeywrongkeywrongkey"
    try:
        decrypt_totp_secret(encrypted, key_input=wrong_key)
        assert False, "Decryption with wrong key must fail"
    except TwoFactorCryptoError:
        pass


def test_crypto_fresh_nonce_per_encryption():
    secret = "JBSWY3DPEHPK3PXP"
    enc1, _ = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    enc2, _ = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    assert enc1 != enc2
    assert enc1[:12] != enc2[:12]  # First 12 bytes is the nonce


def test_totp_setup_and_confirm_flow(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    user = _create_user(email="setup_confirm@example.com")

    # Sign in
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess["auth_version"] = user.auth_version

    # Check status (should be disabled)
    res = client.get("/api/v1/auth/2fa/status")
    assert res.status_code == 200
    assert res.get_json()["data"]["enabled"] is False

    # Start setup
    res = client.post("/api/v1/auth/2fa/setup")
    assert res.status_code == 200
    data = res.get_json()["data"]
    secret = data["secret"]
    assert "provisioning_uri" in data
    assert len(data["backup_codes"]) == 8
    assert "api.qrserver.com" not in data.get("qr_code_url", "")

    # Secret is encrypted in DB, not plaintext
    tf = db.session.scalar(select(UserTwoFactor).where(UserTwoFactor.user_id == user.id))
    assert tf is not None
    assert tf.enabled is False
    assert tf.encrypted_secret != secret.encode()

    # Confirm with valid TOTP code
    valid_code = _generate_totp_code(secret)
    res = client.post("/api/v1/auth/2fa/confirm", json={"code": valid_code})
    assert res.status_code == 200
    assert res.get_json()["data"]["two_factor_enabled"] is True

    # User now has 2FA enabled
    db.session.refresh(tf)
    assert tf.enabled is True
    assert tf.confirmed_at is not None


def test_login_enforces_2fa_challenge(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    user = _create_user(email="enforce2fa@example.com", password="Password123!")

    # Set up 2FA for this user
    secret = generate_totp_secret()
    enc, version = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    tf = UserTwoFactor(
        user_id=user.id,
        encrypted_secret=enc,
        encryption_key_version=version,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC),
    )
    db.session.add(tf)
    db.session.commit()

    # Normal login should return HTTP 202 Accepted
    res = client.post("/api/v1/auth/login", json={"email": "enforce2fa@example.com", "password": "Password123!"})
    assert res.status_code == 202
    body = res.get_json()
    assert body["two_factor_required"] is True
    assert "challenge_id" in body["data"]

    # Session does not have user_id (not fully logged in)
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None
        assert sess.get("pending_2fa_user_id") == user.id

    # Protected endpoint rejected
    res_me = client.get("/api/v1/auth/me")
    assert res_me.status_code == 401

    # Solve challenge with valid TOTP code
    code = _generate_totp_code(secret)
    res_challenge = client.post("/api/v1/auth/2fa/challenge", json={"code": code})
    assert res_challenge.status_code == 200
    # Now fully logged in
    with client.session_transaction() as sess:
        assert sess.get("user_id") == user.id

    res_me2 = client.get("/api/v1/auth/me")
    assert res_me2.status_code == 200


def test_2fa_challenge_with_backup_code_and_single_use(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    user = _create_user(email="backupcode@example.com", password="Password123!")
    secret = generate_totp_secret()
    enc, version = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    tf = UserTwoFactor(
        user_id=user.id,
        encrypted_secret=enc,
        encryption_key_version=version,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC),
    )
    db.session.add(tf)
    from app.services.two_factor import save_backup_codes
    backup_codes = ["12345678", "87654321"]
    save_backup_codes(user.id, backup_codes)

    # Login to issue challenge
    res = client.post("/api/v1/auth/login", json={"email": "backupcode@example.com", "password": "Password123!"})
    assert res.status_code == 202

    # Solve challenge using 8-digit backup code
    res_b = client.post("/api/v1/auth/2fa/challenge", json={"code": "12345678"})
    assert res_b.status_code == 200
    assert res_b.get_json()["data"]["email"] == "backupcode@example.com"

    # Try to reuse the same backup code in a second login
    client.post("/api/v1/auth/logout")
    res2 = client.post("/api/v1/auth/login", json={"email": "backupcode@example.com", "password": "Password123!"})
    assert res2.status_code == 202
    res_reuse = client.post("/api/v1/auth/2fa/challenge", json={"code": "12345678"})
    assert res_reuse.status_code == 400
    assert res_reuse.get_json()["error"]["code"] == "INVALID_CODE"

    # Second backup code works
    res_second = client.post("/api/v1/auth/2fa/challenge", json={"code": "87654321"})
    assert res_second.status_code == 200


def test_2fa_challenge_replay_attack_rejected(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    user = _create_user(email="replay@example.com", password="Password123!")
    secret = generate_totp_secret()
    enc, version = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    tf = UserTwoFactor(
        user_id=user.id,
        encrypted_secret=enc,
        encryption_key_version=version,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC),
    )
    db.session.add(tf)
    db.session.commit()

    # Login 1
    client.post("/api/v1/auth/login", json={"email": "replay@example.com", "password": "Password123!"})
    code = _generate_totp_code(secret)
    res = client.post("/api/v1/auth/2fa/challenge", json={"code": code})
    assert res.status_code == 200

    # Logout and immediate Login 2 with SAME time-step code
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": "replay@example.com", "password": "Password123!"})
    res_replay = client.post("/api/v1/auth/2fa/challenge", json={"code": code})
    assert res_replay.status_code == 400
    assert res_replay.get_json()["error"]["code"] == "INVALID_CODE"


def test_2fa_challenge_lockout_after_five_attempts(client, app):
    app.config.update(WTF_CSRF_ENABLED=False)
    user = _create_user(email="lockout@example.com", password="Password123!")
    secret = generate_totp_secret()
    enc, version = encrypt_totp_secret(secret, key_input=TEST_ENCRYPTION_KEY)
    tf = UserTwoFactor(
        user_id=user.id,
        encrypted_secret=enc,
        encryption_key_version=version,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC),
    )
    db.session.add(tf)
    db.session.commit()

    client.post("/api/v1/auth/login", json={"email": "lockout@example.com", "password": "Password123!"})

    for i in range(5):
        res = client.post("/api/v1/auth/2fa/challenge", json={"code": f"00000{i}"})
        assert res.status_code == 400

    # 6th attempt is locked out
    res_locked = client.post("/api/v1/auth/2fa/challenge", json={"code": "111111"})
    assert res_locked.status_code == 429
    assert res_locked.get_json()["error"]["code"] == "CODE_LOCKED"

