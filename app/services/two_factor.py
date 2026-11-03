"""Server-side Two-Factor Authentication (TOTP) and Backup Code service.

Implements RFC 6238 Time-Based One-Time Passwords with replay protection, clock skew
tolerance, encrypted secret storage via two_factor_crypto, and single-use hashed backup codes.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse
from datetime import UTC, datetime
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models.security import UserBackupCode, UserTwoFactor
from .two_factor_crypto import decrypt_totp_secret, encrypt_totp_secret

DEFAULT_ISSUER = "NexHaat"
TOTP_TIME_STEP_SECONDS = 30
TOTP_DIGITS = 6
BACKUP_CODE_COUNT = 8


def generate_totp_secret() -> str:
    """Generate a high-entropy 160-bit (20 bytes) Base32-encoded TOTP secret."""
    raw = secrets.token_bytes(20)
    return base64.b32encode(raw).decode("ascii").rstrip("=").upper()


def get_provisioning_uri(
    user_email: str,
    secret: str,
    issuer: str = DEFAULT_ISSUER
) -> str:
    """Generate the standard otpauth URI compatible with Google/Microsoft Authenticator.

    No external QR API is used; clients render the URI safely or use manual setup.
    """
    clean_secret = secret.replace(" ", "").upper()
    label = f"{issuer}:{user_email.strip().lower()}"
    params = urllib.parse.urlencode({
        "secret": clean_secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": str(TOTP_DIGITS),
        "period": str(TOTP_TIME_STEP_SECONDS),
    })
    return f"otpauth://totp/{urllib.parse.quote(label)}?{params}"


def verify_totp_code(
    secret: str,
    code: str,
    last_used_step: Optional[int] = None,
    allowed_skew: int = 1
) -> Tuple[bool, Optional[int]]:
    """Verify an RFC 6238 TOTP code against the shared secret.

    Enforces replay protection: a code from an earlier or identical time step
    to last_used_step is rejected.

    Returns:
        (valid, matching_step)
    """
    if not secret or not code:
        return False, None

    clean_code = str(code).strip().replace(" ", "")
    if len(clean_code) != TOTP_DIGITS or not clean_code.isdigit():
        return False, None

    clean_secret = secret.replace(" ", "").upper()
    pad = (8 - len(clean_secret) % 8) % 8
    try:
        key = base64.b32decode(clean_secret + "=" * pad)
    except Exception:
        return False, None

    target_code = int(clean_code)
    current_step = int(time.time() // TOTP_TIME_STEP_SECONDS)

    for step in range(current_step - allowed_skew, current_step + allowed_skew + 1):
        if last_used_step is not None and step <= last_used_step:
            continue

        msg = struct.pack(">Q", step)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** TOTP_DIGITS)

        if code_int == target_code:
            return True, step

    return False, None


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> List[str]:
    """Generate secure 8-digit decimal backup codes."""
    return [f"{secrets.randbelow(100_000_000):08d}" for _ in range(count)]


def save_backup_codes(user_id: int, codes: List[str]) -> None:
    """Store password-hashed backup codes for a user.

    Plaintext codes are never stored. Existing unused codes are removed first.
    """
    db.session.execute(
        delete(UserBackupCode).where(
            UserBackupCode.user_id == user_id,
            UserBackupCode.used_at.is_(None)
        )
    )
    for code in codes:
        code_hash = generate_password_hash(code)
        db.session.add(UserBackupCode(
            user_id=user_id,
            code_hash=code_hash,
            created_at=datetime.now(UTC),
            used_at=None
        ))
    db.session.commit()


def verify_and_consume_backup_code(user_id: int, code: str) -> bool:
    """Verify an 8-digit backup code and atomically mark it as used.

    Single-use only. Used codes cannot be reused.
    """
    clean_code = str(code).strip().replace(" ", "")
    if len(clean_code) != 8 or not clean_code.isdigit():
        return False

    unused_codes = db.session.scalars(
        select(UserBackupCode).where(
            UserBackupCode.user_id == user_id,
            UserBackupCode.used_at.is_(None)
        )
    ).all()

    for item in unused_codes:
        if check_password_hash(item.code_hash, clean_code):
            item.used_at = datetime.now(UTC)
            db.session.commit()
            return True

    return False


def get_backup_codes_remaining_count(user_id: int) -> int:
    """Return the number of unconsumed backup codes for a user."""
    count = db.session.scalar(
        select(func.count(UserBackupCode.id)).where(
            UserBackupCode.user_id == user_id,
            UserBackupCode.used_at.is_(None)
        )
    )
    return int(count or 0)


def revoke_all_backup_codes(user_id: int) -> None:
    """Delete all backup codes (used and unused) for a user."""
    db.session.execute(delete(UserBackupCode).where(UserBackupCode.user_id == user_id))
    db.session.commit()
