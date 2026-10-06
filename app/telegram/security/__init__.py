import hmac
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from ...extensions import csrf, db
from ...models import AuditEvent, AuthThrottle
from ...services.audit import record_audit
from ..common import (
    answer_callback, credentials_ready, receive_update, send_message,
    valid_webhook_secret,
)

telegram_security_bp = Blueprint(
    "telegram_security", __name__, url_prefix="/telegram/security"
)
ADMIN_ROLES = {"admin", "super_admin", "support"}
LOGIN_ACTIONS = {"auth.login", "auth.admin_login", "auth.admin_login_denied"}
ALERT_ACTIONS = {"auth.admin_login_denied", "account.delete_self", "account.remove"}


def _allowed_admin_ids():
    values = current_app.config.get("TELEGRAM_SECURITY_ADMIN_IDS", "")
    allowed = set()
    for value in values.split(","):
        value = value.strip()
        if value.isascii() and value.isdigit() and int(value) > 0:
            allowed.add(int(value))
    return allowed


def _format_time(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _event_lines(events):
    if not events:
        return "No matching recorded events."
    return "\n".join(
        f"{_format_time(event.created_at)} | {event.action} | {event.actor_role or 'unknown role'}"
        for event in events
    )


def _health_text():
    database = "healthy"
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        database = "unavailable"
    telegram = "configured" if credentials_ready("security") else "not configured"
    overall = "healthy" if database == "healthy" else "degraded"
    return (
        f"Application: {overall}\nWebsite: online\nDatabase: {database}\n"
        f"Security bot: {telegram}"
    )


def _security_summary():
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    denied_count = db.session.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.action == "auth.admin_login_denied",
            AuditEvent.created_at >= since,
        )
    ) or 0
    blocked_count = db.session.scalar(
        select(func.count(AuthThrottle.key_hash)).where(AuthThrottle.blocked_until > datetime.now(timezone.utc))
    ) or 0
    severity = "high" if denied_count >= 10 else "attention" if denied_count else "not elevated"
    return (
        f"Risk level: {severity}\nDenied admin sign-ins in last hour: {denied_count}\n"
        f"Currently blocked login sources: {blocked_count}"
    )


def _recent_events(actions=None, role=None, limit=10):
    statement = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if actions:
        statement = statement.where(AuditEvent.action.in_(actions))
    if role:
        statement = statement.where(AuditEvent.actor_role == role)
    return db.session.scalars(statement).all()


def _dashboard_markup():
    return {
        "inline_keyboard": [
            [
                {"text": "System Health", "callback_data": "/status"},
                {"text": "Security", "callback_data": "/security"},
            ],
            [
                {"text": "Alerts", "callback_data": "/alerts"},
                {"text": "Login Activity", "callback_data": "/logins"},
            ],
            [
                {"text": "Audit Logs", "callback_data": "/audit"},
                {"text": "Admin Activity", "callback_data": "/admins"},
            ],
        ]
    }


def handle_security_update(payload, telegram_user_id, chat_id):
    callback = payload.get("callback_query")
    if isinstance(callback, dict):
        text_value = callback.get("data", "")
        command = text_value.strip().lower() if isinstance(text_value, str) else ""
    else:
        message = payload.get("message") or payload.get("edited_message") or {}
        text_value = message.get("text", "")
        command = text_value.strip().split(maxsplit=1)[0].split("@", 1)[0].lower() if isinstance(text_value, str) and text_value.strip() else "/start"
    if telegram_user_id not in _allowed_admin_ids():
        record_audit(
            "telegram.security_access_denied",
            target_type="telegram_user",
            target_id=hmac.digest(
                str(current_app.secret_key).encode(),
                str(telegram_user_id).encode(),
                "sha256",
            ).hex()[:40],
            detail="allowlist check failed",
        )
        return send_message("security", chat_id, "Access denied.")
    if chat_id != telegram_user_id:
        if isinstance(callback, dict):
            answer_callback("security", callback.get("id"), "Use security commands in a private chat.")
        return send_message("security", chat_id, "Security commands are available only in a private chat.")

    if command in {"/start", "/help"}:
        text = (
            "NexHaat Security Management\nCommands: /status, /health, /security, "
            "/alerts, /logins, /audit, /admins, /help"
        )
    elif command in {"/status", "/health"}:
        text = _health_text()
    elif command == "/security":
        text = _security_summary()
    elif command == "/alerts":
        text = _event_lines(_recent_events(actions=ALERT_ACTIONS))
    elif command == "/logins":
        text = _event_lines(_recent_events(actions=LOGIN_ACTIONS))
    elif command == "/audit":
        text = _event_lines(_recent_events())
    elif command == "/admins":
        admin_events = db.session.scalars(
            select(AuditEvent)
            .where(AuditEvent.actor_role.in_(ADMIN_ROLES))
            .order_by(AuditEvent.created_at.desc())
            .limit(10)
        ).all()
        text = _event_lines(admin_events)
    else:
        text = "Unknown command. Use /help."

    if isinstance(callback, dict):
        answer_callback("security", callback.get("id"))

    record_audit(
        "telegram.security_command",
        target_type="telegram_user",
        target_id=hmac.digest(
            str(current_app.secret_key).encode(),
            str(telegram_user_id).encode(),
            "sha256",
        ).hex()[:40],
        detail=command[:200],
    )
    return send_message(
        "security", chat_id, text,
        _dashboard_markup() if command in {"/start", "/help"} else None,
    )


@telegram_security_bp.post("/webhook")
@csrf.exempt
def webhook():
    if not credentials_ready("security"):
        return jsonify(ok=False), 503
    if not valid_webhook_secret(
        "security", request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    ):
        return jsonify(ok=False), 403
    return receive_update("security", handle_security_update)
