from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select

from ..extensions import db
from ..models import (
    AuditEvent, TelegramSecurityAlert, TelegramSecurityAlertRecipient,
)
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
        "admin.ai_builder.project.created": ("Admin created a Builder project", "NOTICE"),
        "admin.ai_builder.project.updated": ("Admin updated a Builder project", "NOTICE"),
        "admin.ai_builder.project.deleted": ("Admin deleted a Builder project", "NOTICE"),
        "admin.ai_builder.project.exported": ("Admin exported a Builder project", "NOTICE"),
        "admin.ai_builder.patch.created": ("Admin created a patch candidate", "NOTICE"),
        "admin.ai_builder.patch.tested": ("Admin tested a patch candidate", "NOTICE"),
        "admin.ai_builder.patch.approved": ("Admin approved a test-backed patch", "NOTICE"),
        "admin.ai_builder.patch.rejected": ("Admin rejected a patch candidate", "NOTICE"),
        "admin.ai_builder.patch.applied": ("Admin applied an approved project patch", "NOTICE"),
        "admin.ai_builder.patch.exported": ("Admin exported an approved patch", "NOTICE"),
        "admin.ai_guardian.finding": ("Guardian found a high-risk issue", "ATTENTION"),
        "admin.ai_guardian.finding.confirmed": ("Admin confirmed a Guardian risk", "ATTENTION"),
        "admin.ai_guardian.finding.reviewed": ("Admin reviewed a Guardian finding", "NOTICE"),
        "admin.ai_guardian.lesson.proposed": ("Admin proposed a tested Guardian lesson", "NOTICE"),
        "admin.ai_guardian.lesson.approved": ("Admin approved a Guardian lesson for private retrieval", "NOTICE"),
        "admin.ai_guardian.lesson.rejected": ("Admin rejected a Guardian lesson", "NOTICE"),
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
    if not event.action.startswith((
        "admin.ai.query.", "admin.ai_builder.", "admin.ai_guardian.",
    )):
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
    destination = (
        "/admin/ai-builder"
        if event.action.startswith(("admin.ai_guardian.", "admin.ai_builder.project.", "admin.ai_builder.patch."))
        else "/admin/ai"
    )
    path = f"{parsed.path.rstrip('/')}{destination}"
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
        delivered_to = set(db.session.scalars(
            select(TelegramSecurityAlertRecipient.telegram_user_id).where(
                TelegramSecurityAlertRecipient.alert_id == record.id
            )
        ).all())
        for admin_id in admin_ids:
            if admin_id in delivered_to:
                continue
            if send_message("security", admin_id, message, markup):
                db.session.add(TelegramSecurityAlertRecipient(
                    alert_id=record.id,
                    telegram_user_id=admin_id,
                    sent_at=datetime.now(timezone.utc),
                ))
                db.session.commit()
                delivered_to.add(admin_id)
        record.attempts += 1
        if all(admin_id in delivered_to for admin_id in admin_ids):
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
