from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import AuditEvent, TelegramSecurityAlert
from ..telegram.common import send_message

MAX_ALERT_ATTEMPTS = 5


def _alert_text(event):
    messages = {
        "auth.admin_login_denied": ("Admin sign-in was denied", "ATTENTION"),
        "account.delete_self": ("A customer deleted their account", "NOTICE"),
        "account.remove": ("An account was removed by an administrator", "NOTICE"),
    }
    summary, severity = messages.get(event.action, ("A recorded security event occurred", "NOTICE"))
    created_at = event.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (
        "NexHaat Security Alert\n"
        f"Event: {summary}\nSeverity: {severity}\n"
        f"Time: {created_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
    )


def deliver_telegram_security_alerts(limit=50):
    token = current_token()
    admin_ids = _admin_ids()
    if not token or not admin_ids:
        return 0
    records = db.session.scalars(
        select(TelegramSecurityAlert)
        .where(
            TelegramSecurityAlert.status == "pending",
            TelegramSecurityAlert.attempts < MAX_ALERT_ATTEMPTS,
        )
        .order_by(TelegramSecurityAlert.id)
        .limit(max(1, min(int(limit), 200)))
    ).all()
    delivered = 0
    for record in records:
        event = db.session.get(AuditEvent, record.audit_event_id)
        if event is None:
            record.status = "failed"
            db.session.commit()
            continue
        message = _alert_text(event)
        results = [send_message("security", admin_id, message) for admin_id in admin_ids]
        record.attempts += 1
        if all(results):
            record.status = "sent"
            record.sent_at = datetime.now(UTC)
            delivered += 1
        elif record.attempts >= MAX_ALERT_ATTEMPTS:
            record.status = "failed"
        db.session.commit()
    return delivered


def current_token():
    from flask import current_app

    return current_app.config.get("TELEGRAM_SECURITY_BOT_TOKEN")


def _admin_ids():
    from flask import current_app

    values = current_app.config.get("TELEGRAM_SECURITY_ADMIN_IDS", "")
    result = set()
    for value in values.split(","):
        value = value.strip()
        if value.isascii() and value.isdigit() and int(value) > 0:
            result.add(int(value))
    return sorted(result)
