"""Read-only Rider AI tools limited to the authenticated rider's assignments."""

from sqlalchemy import select

from ..extensions import db
from ..models import Order
from .core.permissions import AI_SCOPE_RIDER
from .core.tools import ToolRegistry


def get_my_deliveries_tool(*, user=None, limit=8, **_kwargs):
    if user is None or getattr(user, "role", None) != "rider":
        return {"ok": False, "error": "A rider account is required."}
    orders = db.session.scalars(
        select(Order).where(Order.rider_id == user.id,
                            Order.delivery_status.in_(["assigned", "picked_up", "out_for_delivery"]))
        .order_by(Order.created_at.asc()).limit(max(1, min(int(limit), 8)))
    ).all()
    return {"ok": True, "deliveries": [
        {
            "order_number": order.order_number,
            "delivery_status": order.delivery_status,
            "customer_name": order.customer_name,
            "phone": order.phone,
            "address": order.address,
            "city": order.city,
            "delivery_instruction": order.delivery_note,
            "items": [{"name": item.product_name, "quantity": item.quantity,
                       "variant": item.variant_label} for item in order.items[:12]],
        } for order in orders
    ]}


def build_rider_tool_registry():
    registry = ToolRegistry(max_calls=2)
    registry.register(
        "get_my_deliveries", get_my_deliveries_tool, scope=AI_SCOPE_RIDER,
        description="Read only the authenticated rider's active assigned deliveries and handoff instructions.",
        parameters={"type": "object", "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 8},
        }, "additionalProperties": False},
    )
    return registry


def run_rider_query(user, prompt):
    from flask import current_app
    from .core.provider import AIService

    registry = build_rider_tool_registry()
    lowered = str(prompt or "").lower()
    private_delivery_request = any(term in lowered for term in (
        "my delivery", "my deliveries", "assigned delivery", "my route", "my order",
        "delivery address", "delivery instruction", "delivery status", "order status",
        "order number", "where do i deliver", "address", "instructions", "assigned order",
        "ডেলিভারি ঠিকানা", "আমার ডেলিভারি", "আমার অর্ডার", "ঠিকানা", "নির্দেশনা", "অবস্থা",
        "डिलीवरी पता", "मेरी डिलीवरी", "मेरा ऑर्डर", "पता", "निर्देश", "स्थिति",
    ))
    result = AIService(current_app.config).respond(
        str(prompt or "")[:2000], scope=AI_SCOPE_RIDER, user=user,
        tools=registry, context={"request_kind": "read-only assigned delivery help"},
        allow_external=False if private_delivery_request else None,
    )
    if result.get("ok"):
        return result
    if any(term in lowered for term in ("delivery", "deliveries", "order", "address", "instruction",
                                         "ডেলিভারি", "অর্ডার", "ঠিকানা", "নির্দেশ")):
        data = registry.call("get_my_deliveries", scope=AI_SCOPE_RIDER, user=user)
        return {"ok": bool(data.get("ok")), "scope": AI_SCOPE_RIDER,
                "answer": "Your active assigned deliveries and instructions are shown from your rider account.",
                "data": data.get("deliveries", []), "tools_used": ["get_my_deliveries"]}
    return result
