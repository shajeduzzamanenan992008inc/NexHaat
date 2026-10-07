"""Durable, metadata-only Security Bot notices for external model requests."""

from datetime import datetime, timezone
from decimal import Decimal
import logging
import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import AIExternalCallNotice, AIExternalCallRecipient
from ..telegram.common import send_message

logger = logging.getLogger(__name__)
MAX_NOTICE_ATTEMPTS = 5


def _admin_ids(config):
    result = set()
    for value in str(config.get("TELEGRAM_SECURITY_ADMIN_IDS") or "").split(","):
        value = value.strip()
        if value.isascii() and value.isdigit() and int(value) > 0:
            result.add(int(value))
    return sorted(result)


def external_call_notices_ready(config):
    if not config.get("TELEGRAM_SECURITY_BOT_TOKEN") or not _admin_ids(config):
        return False
    try:
        db.session.execute(select(AIExternalCallNotice.id).limit(1)).first()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        return False


def _safe_label(value, limit):
    return re.sub(r"[\r\n\t]+", " ", str(value or ""))[:limit].strip()


def _notice_text(notice):
    created_at = notice.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    job = notice.job_id or "not assigned"
    return (
        "NexHaat External AI\n"
        f"Provider: {notice.provider}\nModel: {notice.model}\nPurpose: {notice.purpose}\n"
        f"Job: {job}\nTime: {created_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Estimated reserved cost: USD {notice.estimated_cost_usd:.6f}\n"
        f"Status: {notice.status}\nCall: {notice.id}"
    )


def record_external_call_notice(*, config, provider, model, purpose, estimated_cost_usd, job_id=None):
    recipients = _admin_ids(config)
    if not config.get("TELEGRAM_SECURITY_BOT_TOKEN") or not recipients:
        return None
    call_id = str(uuid4())
    notice = AIExternalCallNotice(
        id=call_id,
        provider=_safe_label(provider, 40),
        model=_safe_label(model, 160),
        purpose=_safe_label(purpose, 32),
        job_id=_safe_label(job_id, 80) or None,
        estimated_cost_usd=max(Decimal("0"), Decimal(str(estimated_cost_usd or 0))),
        status="started",
    )
    db.session.add(notice)
    db.session.add_all([
        AIExternalCallRecipient(call_notice_id=call_id, telegram_user_id=recipient)
        for recipient in recipients
    ])
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        logger.warning("External AI notice persistence failed (%s).", type(error).__name__)
        return None
    deliver_external_call_notice(call_id)
    return call_id


def _deliver_recipient(recipient, notice, *, allowed_ids):
    if recipient.telegram_user_id not in allowed_ids:
        recipient.status = "failed"
    elif recipient.attempts >= MAX_NOTICE_ATTEMPTS:
        recipient.status = "failed"
    else:
        succeeded = send_message("security", recipient.telegram_user_id, _notice_text(notice))
        recipient.attempts += 1
        if succeeded:
            recipient.status = "sent"
            recipient.sent_at = datetime.now(timezone.utc)
        elif recipient.attempts >= MAX_NOTICE_ATTEMPTS:
            recipient.status = "failed"
    db.session.commit()
    return recipient.status == "sent"


def deliver_external_call_notice(call_id):
    from flask import current_app

    allowed_ids = set(_admin_ids(current_app.config))
    if not current_app.config.get("TELEGRAM_SECURITY_BOT_TOKEN") or not allowed_ids:
        return 0
    notice = db.session.get(AIExternalCallNotice, call_id)
    if notice is None:
        return 0
    delivered = 0
    for recipient in notice.recipients:
        if recipient.status == "pending":
            try:
                delivered += int(_deliver_recipient(recipient, notice, allowed_ids=allowed_ids))
            except SQLAlchemyError:
                db.session.rollback()
                logger.warning("External AI notice delivery state could not be saved.")
                break
    return delivered


def external_call_notice_delivered(call_id):
    try:
        notice = db.session.get(AIExternalCallNotice, call_id)
        return bool(notice and notice.recipients and all(
            recipient.status == "sent" for recipient in notice.recipients
        ))
    except SQLAlchemyError:
        db.session.rollback()
        return False


def deliver_pending_external_call_notices(limit=50):
    from flask import current_app

    config = current_app.config
    if not config.get("TELEGRAM_SECURITY_BOT_TOKEN") or not _admin_ids(config):
        return 0
    recipients = db.session.scalars(
        select(AIExternalCallRecipient)
        .where(AIExternalCallRecipient.status == "pending",
               AIExternalCallRecipient.attempts < MAX_NOTICE_ATTEMPTS)
        .order_by(AIExternalCallRecipient.id)
        .limit(max(1, min(int(limit), 200)))
    ).all()
    delivered = 0
    for recipient in recipients:
        notice = db.session.get(AIExternalCallNotice, recipient.call_notice_id)
        if notice is None:
            recipient.status = "failed"
            db.session.commit()
            continue
        try:
            delivered += int(_deliver_recipient(
                recipient, notice, allowed_ids=set(_admin_ids(config))
            ))
        except SQLAlchemyError:
            db.session.rollback()
            logger.warning("External AI notice retry state could not be saved.")
            break
    return delivered
