"""Database-backed shared AI request limiter with hashed principals."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import time

from flask import current_app, has_request_context, request
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..extensions import db
from ..models import AIRequestWindow


def consume_ai_request(scope, user=None, principal=None):
    now = datetime.now(timezone.utc)
    window_seconds = max(10, min(int(current_app.config.get("AI_RATE_LIMIT_WINDOW_SECONDS", 60)), 3600))
    limit = max(1, min(int(current_app.config.get("AI_RATE_LIMIT", 60)), 10000))
    bucket_start = datetime.fromtimestamp(int(now.timestamp() // window_seconds) * window_seconds, timezone.utc)
    key_hash = _principal_hash(scope, user=user, principal=principal)

    table = AIRequestWindow.__table__
    dialect = db.session.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else postgres_insert if dialect == "postgresql" else None
    if insert is None:
        raise RuntimeError("AI rate limiting requires SQLite or PostgreSQL.")
    statement = insert(table).values(
        principal_hash=key_hash,
        window_started_at=bucket_start,
        request_count=1,
        updated_at=now,
    )
    stale_window = table.c.window_started_at < bucket_start
    statement = statement.on_conflict_do_update(
        index_elements=[table.c.principal_hash],
        set_={
            "window_started_at": case((stale_window, bucket_start), else_=table.c.window_started_at),
            "request_count": case(
                (stale_window, 1),
                (table.c.request_count < limit + 1, table.c.request_count + 1),
                else_=table.c.request_count,
            ),
            "updated_at": now,
        },
    )
    db.session.execute(statement)
    db.session.commit()
    record = db.session.get(AIRequestWindow, key_hash)
    allowed = bool(record and record.request_count <= limit)
    _cleanup_stale_windows(now)
    return allowed


def get_ai_request_usage(scope, user=None, principal=None):
    """Return the current hashed rate-limit window without consuming a request."""
    now = datetime.now(timezone.utc)
    window_seconds = max(10, min(int(current_app.config.get("AI_RATE_LIMIT_WINDOW_SECONDS", 60)), 3600))
    limit = max(1, min(int(current_app.config.get("AI_RATE_LIMIT", 60)), 10000))
    bucket_start = datetime.fromtimestamp(int(now.timestamp() // window_seconds) * window_seconds, timezone.utc)
    key_hash = _principal_hash(scope, user=user, principal=principal)
    record = db.session.get(AIRequestWindow, key_hash)
    recorded_bucket = record.window_started_at if record is not None else None
    if recorded_bucket is not None and recorded_bucket.tzinfo is None:
        recorded_bucket = recorded_bucket.replace(tzinfo=timezone.utc)
    used = (
        min(record.request_count, limit)
        if record is not None and recorded_bucket == bucket_start
        else 0
    )
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "window_seconds": window_seconds,
        "resets_at": (bucket_start + timedelta(seconds=window_seconds)).isoformat(),
    }


def _principal_hash(scope, *, user=None, principal=None):
    if principal is not None:
        principal = f"channel:{str(principal)[:120]}"
    else:
        principal = (f"user:{user.id}" if user is not None else
                     f"ip:{request.remote_addr or 'unknown'}" if has_request_context() else "ip:internal")
    key_material = f"ai-rate:{scope}:{principal}".encode("utf-8")
    secret = current_app.secret_key
    secret = secret.encode("utf-8") if isinstance(secret, str) else secret
    return hmac.new(secret or b"nexhaat-ai-rate-limit", key_material, hashlib.sha256).hexdigest()


def _cleanup_stale_windows(now):
    """Bound principal-hash retention without putting cleanup on every request."""
    try:
        last = current_app.extensions.get("ai_rate_cleanup_at", 0)
        if time.monotonic() - last < 3600:
            return
        current_app.extensions["ai_rate_cleanup_at"] = time.monotonic()
        db.session.execute(delete(AIRequestWindow).where(
            AIRequestWindow.updated_at < now - timedelta(days=1)
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
