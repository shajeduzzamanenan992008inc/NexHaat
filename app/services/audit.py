"""Append security-relevant audit events without ever breaking a request."""

import logging

from flask import g

from ..extensions import db
from ..models import AuditEvent, TelegramSecurityAlert
from ..security import client_address_hash

logger = logging.getLogger(__name__)
TELEGRAM_ALERT_ACTIONS = frozenset({
    "auth.admin_login_denied",
    "account.delete_self",
    "account.remove",
    "customer.ai.cart_change.confirmed",
    "seller.review",
    "catalog.product_review",
    "review.moderate",
    "order.status",
    "order.return_reviewed",
    "payment.risk_approved",
    "admin.ai.query.started",
    "admin.ai.query.completed",
    "admin.ai.query.failed",
    "admin.ai_builder.job.started",
    "admin.ai_builder.job.completed",
    "admin.ai_builder.job.failed",
    "admin.ai_builder.job.deleted",
    "admin.ai_builder.project.created",
    "admin.ai_builder.project.updated",
    "admin.ai_builder.project.deleted",
    "admin.ai_builder.project.exported",
    "admin.ai_builder.patch.created",
    "admin.ai_builder.patch.tested",
    "admin.ai_builder.patch.approved",
    "admin.ai_builder.patch.rejected",
    "admin.ai_builder.patch.applied",
    "admin.ai_builder.patch.exported",
    "admin.ai_guardian.finding",
    "admin.ai_guardian.finding.confirmed",
    "admin.ai_guardian.finding.reviewed",
    "admin.ai_guardian.lesson.proposed",
    "admin.ai_guardian.lesson.approved",
    "admin.ai_guardian.lesson.rejected",
})


def record_audit(action, target_type=None, target_id=None, detail=None, actor=None):
    """Persist one audit event. Failures are logged and swallowed."""
    try:
        if actor is None:
            actor = getattr(g, "current_user", None)
        event = AuditEvent(
            action=str(action)[:60],
            actor_id=getattr(actor, "id", None),
            actor_email=getattr(actor, "email", None),
            actor_role=getattr(actor, "role", None),
            target_type=str(target_type)[:40] if target_type else None,
            target_id=str(target_id)[:40] if target_id is not None else None,
            detail=str(detail)[:255] if detail else None,
            ip_hash=client_address_hash(),
        )
        db.session.add(event)
        db.session.flush()
        if event.action in TELEGRAM_ALERT_ACTIONS:
            try:
                with db.session.begin_nested():
                    db.session.add(TelegramSecurityAlert(audit_event_id=event.id))
                    db.session.flush()
            except Exception as error:  # noqa: BLE001 - alert enqueue must not block the audit record
                logger.warning("Telegram security alert could not be queued (%s).", type(error).__name__)
        db.session.commit()
        return event.id
    except Exception:  # noqa: BLE001 - auditing must never break a request
        db.session.rollback()
        logger.exception("Audit event %s could not be recorded.", action)
        return None
