from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

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
        "customer.ai.cart_change.confirmed": (
            "A customer confirmed an AI-assisted cart change", "NOTICE"
        ),
        "seller.review": ("An Admin reviewed a seller application", "NOTICE"),
        "catalog.product_review": ("An Admin moderated a product listing", "NOTICE"),
        "review.moderate": ("An Admin moderated a customer review", "NOTICE"),
        "order.status": ("An Admin updated an order status", "NOTICE"),
        "order.return_reviewed": ("An order return request was reviewed", "NOTICE"),
        "payment.risk_approved": ("An Admin approved a validated payment review", "NOTICE"),
        "admin.ai.query.started": ("Admin AI read-only query started", "NOTICE"),
        "admin.ai.query.completed": ("Admin AI read-only query completed", "NOTICE"),
        "admin.ai.query.failed": ("Admin AI read-only query failed", "ATTENTION"),
        "admin.ai_builder.job.started": ("Admin AI project analysis started", "NOTICE"),
        "admin.ai_builder.job.completed": ("Admin AI project analysis completed", "NOTICE"),
        "admin.ai_builder.job.failed": ("Admin AI project analysis failed", "ATTENTION"),
        "admin.ai_builder.job.deleted": ("Admin deleted an AI analysis record", "NOTICE"),
    }
    summary, severity = messages.get(event.action, ("A recorded security event occurred", "NOTICE"))
    created_at = event.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (
        "NexHaat Security Alert\n"
        f"Event: {summary}\nSeverity: {severity}\n"
        f"Time: {created_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )


def _alert_markup(event):
    if not event.action.startswith(("admin.ai.query.", "admin.ai_builder.job.")):
        return None
    from flask import current_app

    base_url = str(current_app.config.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or current_app.config.get("ENVIRONMENT") == "production" and parsed.scheme != "https"
    ):
        return None
    path = f"{parsed.path.rstrip('/')}/admin/ai"
    return {"inline_keyboard": [[{
        "text": "Open Admin AI workspace",
        "url": urlunsplit((parsed.scheme, parsed.netloc, path, "", "")),
    }]]}


def deliver_telegram_security_alerts(limit=50, *, alert_id=None):
    token = current_token()
    admin_ids = _admin_ids()
    if not token or not admin_ids:
        return 0
    statement = select(TelegramSecurityAlert).where(
        TelegramSecurityAlert.status == "pending",
        TelegramSecurityAlert.attempts < MAX_ALERT_ATTEMPTS,
    )
    if alert_id is not None:
        statement = statement.where(TelegramSecurityAlert.audit_event_id == alert_id)
    records = db.session.scalars(
        statement
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
        markup = _alert_markup(event)
        results = [
            send_message("security", admin_id, message, markup)
            for admin_id in admin_ids
        ]
        record.attempts += 1
        if all(results):
            record.status = "sent"
            record.sent_at = datetime.now(timezone.utc)
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
