"""Queue and promptly deliver metadata-only notices for Admin actions."""

import logging

from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from .audit import record_audit
from .telegram_alerts import deliver_telegram_security_alerts

logger = logging.getLogger(__name__)
AI_ACTIONS = frozenset({
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
})


def notify_admin_ai_action(action, *, actor, target_id=None, target_type="ai_action", detail=None):
    if action not in AI_ACTIONS:
        raise ValueError("Unsupported Admin action event.")
    event_id = record_audit(
        action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        actor=actor,
    )
    if event_id is None:
        return False
    try:
        deliver_telegram_security_alerts(alert_id=event_id)
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.warning("Admin AI Telegram notice remains queued (%s).", type(error).__name__)
    return True
