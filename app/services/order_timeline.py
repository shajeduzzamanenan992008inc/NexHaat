"""Order tracking timeline: append-only event recording and retrieval.

The timeline is derived exclusively from real state changes. Nothing here
invents a shipment or delivery step, and no financial value is computed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from ..models import ORDER_EVENT_ACTOR_ROLES, ORDER_EVENT_TYPES, OrderEvent

MAX_REFERENCE_LENGTH = 80
MAX_CARRIER_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 255
MAX_DEDUPE_LENGTH = 120


def _actor_role(actor, actor_role):
    if actor_role is not None:
        if actor_role not in ORDER_EVENT_ACTOR_ROLES:
            raise ValueError("Unsupported timeline actor role.")
        return actor_role
    role = getattr(actor, "role", None)
    if role in ORDER_EVENT_ACTOR_ROLES:
        return role
    return "system" if actor is None else None


def _clean(value, limit):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def record_order_event(
    order,
    *,
    event_type,
    previous_status=None,
    new_status=None,
    actor=None,
    actor_role=None,
    description=None,
    tracking_reference=None,
    carrier=None,
    estimated_delivery_at=None,
    dedupe_key=None,
):
    """Append one timeline event to the session without committing.

    The caller keeps order updates and the event write in one transaction, so a
    failed commit leaves neither a status change nor a dangling event behind.
    Returns ``None`` when the same ``dedupe_key`` already exists for the order.
    """
    if event_type not in ORDER_EVENT_TYPES:
        raise ValueError("Unsupported order timeline event type.")
    key = _clean(dedupe_key, MAX_DEDUPE_LENGTH)
    if key is not None and order.id is not None:
        existing = db.session.scalar(
            select(OrderEvent.id).where(
                OrderEvent.order_id == order.id, OrderEvent.dedupe_key == key
            )
        )
        if existing is not None:
            return None
    event = OrderEvent(
        order=order,
        event_type=event_type,
        previous_status=_clean(previous_status, 20),
        new_status=_clean(new_status, 20),
        actor_id=getattr(actor, "id", None),
        actor_role=_actor_role(actor, actor_role),
        description=_clean(description, MAX_DESCRIPTION_LENGTH),
        tracking_reference=_clean(tracking_reference, MAX_REFERENCE_LENGTH),
        carrier=_clean(carrier, MAX_CARRIER_LENGTH),
        estimated_delivery_at=estimated_delivery_at,
        dedupe_key=key,
    )
    db.session.add(event)
    return event


def record_status_transition(order, previous_status, new_status, *, actor=None,
                             actor_role=None, description=None):
    """Record one allowed order-status transition exactly once."""
    return record_order_event(
        order,
        event_type="status",
        previous_status=previous_status,
        new_status=new_status,
        actor=actor,
        actor_role=actor_role,
        description=description,
        dedupe_key=f"status:{previous_status}->{new_status}",
    )


def list_order_events(order_id):
    """Return an order's events in chronological order (oldest first)."""
    return list(
        db.session.scalars(
            select(OrderEvent)
            .where(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.created_at.asc(), OrderEvent.id.asc())
        ).all()
    )


def latest_tracking(order_id):
    """Return the most recent event that actually carries shipment data."""
    return db.session.scalar(
        select(OrderEvent)
        .where(
            OrderEvent.order_id == order_id,
            (OrderEvent.tracking_reference.is_not(None)) | (OrderEvent.carrier.is_not(None)),
        )
        .order_by(OrderEvent.created_at.desc(), OrderEvent.id.desc())
        .limit(1)
    )


def parse_estimated_delivery(raw):
    """Validate an optional ISO-8601 estimated-delivery timestamp."""
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise ValueError("The estimated delivery date must be an ISO-8601 string.")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("The estimated delivery date must be an ISO-8601 string.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if parsed < datetime.now(UTC):
        raise ValueError("The estimated delivery date cannot be in the past.")
    return parsed
