"""Privacy choices for sending bounded prompts to external model providers."""

from __future__ import annotations

import hashlib
import hmac

from flask import current_app, has_app_context, has_request_context, session
from sqlalchemy import select

from ...extensions import db
from ...models import AIExternalConsent


def principal_name(user=None, principal=None):
    if principal:
        return str(principal)[:240]
    if user is not None and getattr(user, "id", None) is not None:
        return f"account:{getattr(user, 'role', 'user')}:{user.id}"
    return None


def _digest(value):
    secret = current_app.secret_key
    secret = secret.encode("utf-8") if isinstance(secret, str) else secret
    return hmac.new(secret, str(value).encode("utf-8"), hashlib.sha256).hexdigest()


def external_consent_enabled(*, user=None, principal=None):
    if not has_app_context():
        return False
    names = []
    if principal:
        names.append(str(principal)[:240])
    if user is not None and getattr(user, "id", None) is not None:
        names.append(f"account:{getattr(user, 'role', 'user')}:{user.id}")
    if names:
        return any(bool((record := db.session.get(AIExternalConsent, _digest(name))) and record.enabled)
                   for name in dict.fromkeys(names))
    return bool(has_request_context() and session.get("ai_external_consent") is True)


def set_external_consent(enabled, *, user=None, principal=None):
    """Persist account or hashed Telegram consent; keep guest consent in session only."""
    if not has_app_context():
        return False
    name = principal_name(user, principal)
    if name:
        key = _digest(name)
        record = db.session.get(AIExternalConsent, key)
        if record is None:
            record = AIExternalConsent(principal_hash=key, enabled=bool(enabled))
            db.session.add(record)
        else:
            record.enabled = bool(enabled)
        db.session.commit()
        return True
    if has_request_context():
        session["ai_external_consent"] = bool(enabled)
        return True
    return False
