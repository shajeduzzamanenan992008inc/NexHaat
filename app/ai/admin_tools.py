"""Admin-scope read-only tools backed by server-side marketplace aggregates."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re

from sqlalchemy import and_, case, func, select

from ..extensions import db
from ..models import Category, Order, OrderItem, Product, Review, User
from ..models.catalog import RecentViewedProduct
from ..models.telegram import CustomerCartItem
from .core.permissions import AI_SCOPE_ADMIN
from .core.tools import ToolRegistry
from .core.guardrails import redact_personal_data


def _admin(user):
    if user is None or getattr(user, "role", None) not in {"admin", "super_admin"}:
        raise ValueError("An authorized administrator is required.")
    return user


def get_sales_summary_tool(user=None, days=7, **_kwargs):
    _admin(user)
    days = max(1, min(int(days), 90))
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    previous = start - timedelta(days=days)
    base = Order.status.notin_(("cancelled", "refunded"))
    current_count, current_total = db.session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(base, Order.created_at >= start)
    ).one()
    previous_count, previous_total = db.session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(base, Order.created_at >= previous, Order.created_at < start)
    ).one()
    return {
        "window_days": days,
        "orders": int(current_count or 0),
        "gross_bdt": str(Decimal(str(current_total or 0))),
        "previous_orders": int(previous_count or 0),
        "previous_gross_bdt": str(Decimal(str(previous_total or 0))),
        "as_of": now.isoformat(),
        "note": "Gross order totals exclude cancelled and refunded orders; not a settlement report.",
    }


def get_order_trends_tool(user=None, days=7, **_kwargs):
    _admin(user)
    days = max(1, min(int(days), 90))
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.session.execute(
        select(func.date(Order.created_at), func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(Order.created_at >= start, Order.status.notin_(("cancelled", "refunded")))
        .group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at))
    ).all()
    return [{"date": str(day), "orders": int(count), "gross_bdt": str(Decimal(str(total)))}
            for day, count, total in rows]


def get_product_performance_tool(user=None, limit=10, **_kwargs):
    _admin(user)
    limit = max(1, min(int(limit), 20))
    best = db.session.execute(
        select(OrderItem.product_name, func.sum(OrderItem.quantity), func.sum(OrderItem.subtotal))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc()).limit(limit)
    ).all()
    low = db.session.execute(
        select(Product.name,
               func.coalesce(func.sum(case((Order.id.is_not(None), OrderItem.quantity), else_=0)), 0),
               func.coalesce(func.sum(case((Order.id.is_not(None), OrderItem.subtotal), else_=0)), 0))
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .outerjoin(Order, and_(Order.id == OrderItem.order_id,
                               Order.status.notin_(("cancelled", "refunded"))))
        .where(Product.is_available.is_(True), Product.moderation_status == "approved")
        .group_by(Product.id, Product.name)
        .order_by(func.coalesce(func.sum(case((Order.id.is_not(None), OrderItem.quantity), else_=0)), 0).asc(), Product.name.asc())
        .limit(limit)
    ).all()
    catalog = db.session.scalars(
        select(Product).where(
            Product.is_available.is_(True), Product.moderation_status == "approved",
        ).order_by(Product.name.asc()).limit(1000)
    ).all()
    low_stock = sorted((item for item in catalog if item.available_stock <= 5),
                       key=lambda item: (item.available_stock, item.name.lower()))[:limit]
    low_rating = db.session.execute(
        select(Product.name, func.avg(Review.rating), func.count(Review.id))
        .join(Review, Review.product_id == Product.id)
        .where(Review.status == "approved")
        .group_by(Product.id, Product.name)
        .having(func.count(Review.id) >= 3)
        .order_by(func.avg(Review.rating).asc()).limit(limit)
    ).all()
    return {
        "best_sellers": [{"product": name, "units": int(qty or 0), "gross_bdt": str(total or 0)}
                         for name, qty, total in best],
        "low_performing_products": [{"product": name, "units": int(qty or 0),
                                     "gross_bdt": str(total or 0)} for name, qty, total in low],
        "low_stock": [{"product": item.name, "stock": item.available_stock}
                      for item in low_stock],
        "low_review_rating": [{"product": name, "average_rating": round(float(avg), 2), "reviews": count}
                              for name, avg, count in low_rating],
    }


def get_category_performance_tool(user=None, days=30, **_kwargs):
    _admin(user)
    days = max(1, min(int(days), 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.session.execute(
        select(Category.name, func.sum(OrderItem.quantity), func.sum(OrderItem.subtotal))
        .join(Product, Product.category_id == Category.id)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.created_at >= since, Order.status.notin_(("cancelled", "refunded")))
        .group_by(Category.id, Category.name)
        .order_by(func.sum(OrderItem.subtotal).desc()).limit(20)
    ).all()
    return [{"category": name, "units": int(quantity or 0), "gross_bdt": str(total or 0)}
            for name, quantity, total in rows]


def get_customer_behavior_summary_tool(user=None, **_kwargs):
    _admin(user)
    recent_since = datetime.now(timezone.utc) - timedelta(days=30)
    customer_count = db.session.scalar(select(func.count(User.id)).where(User.role == "customer")) or 0
    active_customers = db.session.scalar(
        select(func.count(func.distinct(RecentViewedProduct.user_id))).where(
            RecentViewedProduct.viewed_at >= recent_since
        )
    ) or 0
    popular_views = db.session.execute(
        select(Product.name, func.count(RecentViewedProduct.id))
        .join(RecentViewedProduct, RecentViewedProduct.product_id == Product.id)
        .where(RecentViewedProduct.viewed_at >= recent_since,
               Product.is_available.is_(True), Product.moderation_status == "approved")
        .group_by(Product.id, Product.name)
        .order_by(func.count(RecentViewedProduct.id).desc()).limit(10)
    ).all()
    cart_items = db.session.scalar(select(func.count(CustomerCartItem.id))) or 0
    return {
        "registered_customers": int(customer_count),
        "customers_with_recent_views_30d": int(active_customers),
        "active_cart_line_count": int(cart_items),
        "popular_viewed_products": [{"product": name, "views": int(count)} for name, count in popular_views],
        "window_days": 30,
    }


def get_catalog_quality_tool(user=None, limit=20, **_kwargs):
    _admin(user)
    limit = max(1, min(int(limit), 50))
    pending = db.session.scalar(select(func.count(Product.id)).where(Product.moderation_status == "pending")) or 0
    sparse = db.session.scalars(
        select(Product).where(
            Product.is_available.is_(True), Product.moderation_status == "approved",
            (func.length(func.trim(Product.description)) < 80) | Product.image.is_(None),
        ).order_by(Product.updated_at.desc()).limit(limit)
    ).all()
    pending_reviews = db.session.scalar(select(func.count(Review.id)).where(Review.status == "pending")) or 0
    return {
        "pending_products": int(pending),
        "pending_reviews": int(pending_reviews),
        "sparse_public_listings": [{"product": item.name,
                                    "missing_image": not bool(item.image),
                                    "short_description": len((item.description or "").strip()) < 80}
                                   for item in sparse],
    }


def get_support_conversation_summaries_tool(user=None, limit=10, **_kwargs):
    _admin(user)
    from ..models.support import SupportConversation, SupportMessage

    conversations = db.session.scalars(
        select(SupportConversation).where(SupportConversation.status.in_(("open", "pending")))
        .order_by(SupportConversation.updated_at.desc()).limit(max(1, min(int(limit), 20)))
    ).all()
    result = []
    for conversation in conversations:
        messages = db.session.scalars(
            select(SupportMessage).where(SupportMessage.conversation_id == conversation.id)
            .order_by(SupportMessage.created_at.asc()).limit(20)
        ).all()
        result.append({
            "conversation_id": conversation.id,
            "subject": redact_personal_data(conversation.subject or "")[:160],
            "category": conversation.category,
            "status": conversation.status,
            "messages": [{"from": item.sender_role,
                          "text": redact_personal_data(item.body)[:1200]} for item in messages],
        })
    return result


def get_review_spam_risk_tool(user=None, limit=30, **_kwargs):
    """Flag possible spam patterns for human review; never changes moderation state."""
    _admin(user)
    reviews = db.session.scalars(
        select(Review).where(Review.status == "pending")
        .order_by(Review.created_at.desc()).limit(max(1, min(int(limit), 50)))
    ).all()
    normalized_counts = {}
    for item in reviews:
        normalized = re.sub(r"\W+", " ", (item.comment or "").lower()).strip()
        if normalized:
            normalized_counts[normalized] = normalized_counts.get(normalized, 0) + 1
    output = []
    for item in reviews:
        comment = item.comment or ""
        normalized = re.sub(r"\W+", " ", comment.lower()).strip()
        reasons = []
        if re.search(r"https?://|www\.", comment, re.I):
            reasons.append("contains a link")
        if re.search(r"\b(buy now|discount code|promo code|whatsapp|telegram)\b", comment, re.I):
            reasons.append("contains promotional wording")
        if normalized and normalized_counts.get(normalized, 0) > 1:
            reasons.append("repeated text among pending reviews")
        if len(normalized) < 8:
            reasons.append("very short text")
        if reasons:
            output.append({"review_id": item.id,
                           "product": item.product.name if item.product else "Removed product",
                           "rating": item.rating, "risk": "high" if len(reasons) >= 2 else "review",
                           "reasons": reasons,
                           "action": "Human moderation required; this tool never approves or rejects reviews."})
    return output


def build_admin_tool_registry(max_tool_calls=5):
    registry = ToolRegistry(max_calls=max_tool_calls)
    registry.register("get_sales_summary", get_sales_summary_tool, scope=AI_SCOPE_ADMIN,
                      description="Read aggregate sales and order totals for a bounded date range.",
                      parameters={"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90}}, "additionalProperties": False})
    registry.register("get_order_trends", get_order_trends_tool, scope=AI_SCOPE_ADMIN,
                      description="Read daily order and gross-total trends.",
                      parameters={"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90}}, "additionalProperties": False})
    registry.register("get_product_performance", get_product_performance_tool, scope=AI_SCOPE_ADMIN,
                      description="Read best-selling, low-stock, and low-review-rating products.",
                      parameters={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "additionalProperties": False})
    registry.register("get_category_performance", get_category_performance_tool, scope=AI_SCOPE_ADMIN,
                      description="Read category sales from real orders.",
                      parameters={"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90}}, "additionalProperties": False})
    registry.register("get_customer_behavior_summary", get_customer_behavior_summary_tool,
                      scope=AI_SCOPE_ADMIN, description="Read anonymized customer activity aggregates.")
    registry.register("get_catalog_quality", get_catalog_quality_tool, scope=AI_SCOPE_ADMIN,
                      description="Read product/review moderation and listing quality counts.",
                      parameters={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "additionalProperties": False})
    registry.register("get_support_conversation_summaries", get_support_conversation_summaries_tool,
                      scope=AI_SCOPE_ADMIN, description="Read open support case text with personal data redacted.",
                      parameters={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "additionalProperties": False})
    registry.register("get_review_spam_risk", get_review_spam_risk_tool,
                      scope=AI_SCOPE_ADMIN,
                      description="Flag possible spam patterns in pending reviews for human moderation; read-only.",
                      parameters={"type": "object", "properties": {
                          "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                      }, "additionalProperties": False})
    return registry


def handle_admin_ai_query(prompt, *, user):
    """Run a read-only admin query or deterministic aggregate fallback."""
    from flask import current_app
    from ..services.ai_rate_limit import consume_ai_request
    from .core.provider import AIService

    if user is None or getattr(user, "role", None) not in {"admin", "super_admin"}:
        return {"ok": False, "scope": AI_SCOPE_ADMIN, "answer": "Access denied.", "tools_used": []}
    try:
        if not consume_ai_request(AI_SCOPE_ADMIN, user=user):
            return {"ok": False, "scope": AI_SCOPE_ADMIN,
                    "answer": "Admin assistant request limit reached. Try again shortly.", "tools_used": []}
    except Exception:
        db.session.rollback()
        return {"ok": False, "scope": AI_SCOPE_ADMIN,
                "answer": "Admin analytics are temporarily unavailable.", "tools_used": []}
    registry = build_admin_tool_registry()
    service = AIService(current_app.config)
    result = service.respond(str(prompt or "")[:2000], scope=AI_SCOPE_ADMIN,
                             user=user, tools=registry,
                             context={"query_type": "read-only marketplace analytics"})
    if result.get("ok") and any(isinstance(item, dict) and item.get("ok") is True
                                  for item in result.get("tool_results", [])):
        return {**result, "data": result.get("tool_results", [])}
    lowered = str(prompt or "").lower()
    if any(item in lowered for item in ("review", "spam", "ফেক", "স্প্যাম")):
        tool = "get_review_spam_risk"
    elif any(item in lowered for item in ("stock", "inventory", "স্টক", "মজুদ")):
        tool = "get_product_performance"
    elif any(item in lowered for item in ("category", "ক্যাটাগরি", "श्रेणी")):
        tool = "get_category_performance"
    elif any(item in lowered for item in ("customer", "behavior", "customer activity", "গ্রাহক")):
        tool = "get_customer_behavior_summary"
    elif any(item in lowered for item in ("support", "ticket", "conversation", "সাপোর্ট")):
        tool = "get_support_conversation_summaries"
    elif any(item in lowered for item in ("product", "best", "worst", "low performing", "বিক্রি")):
        tool = "get_product_performance"
    elif any(item in lowered for item in ("trend", "daily", "প্রবণতা")):
        tool = "get_order_trends"
    else:
        tool = "get_sales_summary"
    arguments = {"days": 7} if tool in {"get_sales_summary", "get_order_trends", "get_category_performance"} else {}
    data = registry.call(tool, scope=AI_SCOPE_ADMIN, user=user, arguments=arguments)
    return {"ok": bool(data.get("ok")), "scope": AI_SCOPE_ADMIN,
            "answer": "Read-only marketplace data from the current database:",
            "data": data.get("result", {}), "tools_used": [tool]}
