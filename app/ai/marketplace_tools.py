"""Customer assistant tools backed by the existing marketplace services."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import re
import time

from flask import current_app, has_app_context
from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    AppSetting, Order, OrderItem, Product, ProductVariant, Review, User,
)
from ..services.cart import CartError, customer_cart_rows
from ..services.catalog import get_active_categories, get_catalog_products, get_product_by_slug
from .core.permissions import AI_SCOPE_CUSTOMER
from .core.provider import AIService
from .core.tools import ToolRegistry
from .core.guardrails import redact_personal_data
from ..services.ai_rate_limit import consume_ai_request


_DECIMAL_LIMIT = Decimal("100000000")
_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "maxLength": 100},
        "max_price": {"type": "number", "minimum": 0, "maximum": 100000000},
        "min_price": {"type": "number", "minimum": 0, "maximum": 100000000},
        "category": {"type": "string", "maxLength": 100},
        "brand": {"type": "string", "maxLength": 120},
        "size": {"type": "string", "maxLength": 80},
        "attribute": {"type": "string", "maxLength": 80},
        "limit": {"type": "integer", "minimum": 1, "maximum": 8},
    },
    "additionalProperties": False,
}


def _money(value):
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _display_price(product, variant=None):
    if variant is not None and variant.price is not None:
        return variant.price
    return product.discount_price if product.discount_price is not None else product.price


def _product_summary(product: Product):
    price = _display_price(product)
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category": getattr(product.category, "name", None),
        "brand": product.brand_name,
        "price": _money(price),
        "stock": product.available_stock,
        "available": bool(product.is_available and product.moderation_status == "approved"
                           and product.available_stock > 0
                           and getattr(product.category, "is_active", True)),
        "description": (product.description or "")[:220],
        "variants": [
            {
                "id": item.id,
                "label": f"{item.option_name}: {item.option_value}",
                "price": _money(_display_price(product, item)),
                "stock": item.stock_quantity,
                "available": bool(item.is_active and item.stock_quantity > 0),
            }
            for item in product.variants if item.is_active
        ][:12],
    }


def _valid_money(value, field):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a valid amount.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a valid amount.") from None
    if not amount.is_finite() or amount < 0 or amount > _DECIMAL_LIMIT:
        raise ValueError(f"{field} is outside the supported range.")
    return amount


def search_products_tool(query="", max_price=None, min_price=None, category="", brand="", size="", attribute="", limit=5, **_kwargs):
    query = str(query or "").strip()[:100]
    upper = _valid_money(max_price, "Maximum price")
    lower = _valid_money(min_price, "Minimum price")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Minimum price cannot exceed maximum price.")
    variant_value = str(size or attribute or "").strip()[:80] or None
    category_id = None
    if category:
        from ..models import Category

        category_row = db.session.scalar(select(Category).where(
            Category.is_active.is_(True), Category.name.ilike(str(category).strip()[:100])
        ))
        category_id = category_row.id if category_row else -1
    products, _page = get_catalog_products(
        page=1, per_page=max(1, min(int(limit), 8)), query=query,
        category_id=category_id,
        min_price=lower, max_price=upper,
        brand_name=str(brand or "").strip()[:120],
        in_stock=True,
        variant_value=variant_value,
    )
    return [_product_summary(product) for product in products]


def get_product_tool(slug="", **_kwargs):
    if not isinstance(slug, str) or not slug or len(slug) > 180:
        raise ValueError("A valid product slug is required.")
    product = get_product_by_slug(slug)
    if (product is None or product.moderation_status != "approved" or not product.is_available
            or product.available_stock < 1 or not getattr(product.category, "is_active", True)):
        return {"error": "Product not found."}
    return _product_summary(product)


def compare_products_tool(slugs=None, **_kwargs):
    if not isinstance(slugs, list) or not 2 <= len(slugs) <= 3:
        raise ValueError("Choose two or three product slugs to compare.")
    products = []
    for slug in slugs:
        if not isinstance(slug, str) or len(slug) > 180:
            raise ValueError("Product identifiers are invalid.")
        product = get_product_by_slug(slug.strip())
        if (product is not None and product.moderation_status == "approved"
                and product.is_available and product.available_stock > 0
                and getattr(product.category, "is_active", True)):
            products.append(_product_summary(product))
    return products


def get_categories_tool(limit=10, **_kwargs):
    cache_key = "ai_public_active_categories"
    cache = current_app.extensions.setdefault("ai_public_cache", {}) if has_app_context() else {}
    cached = cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        rows = [dict(item) for item in cached[1]]
    else:
        categories = get_active_categories()
        rows = [{"name": item.name, "slug": item.slug,
                 "description": (item.description or "")[:180]} for item in categories[:100]]
        if has_app_context():
            cache[cache_key] = (time.monotonic() + 60, rows)
    return rows[: max(1, min(int(limit), 20))]


def get_recommendations_tool(user=None, category="", query="", max_price=None, limit=5, **_kwargs):
    upper = _valid_money(max_price, "Maximum price")
    category_id = None
    if category:
        from ..models import Category

        row = db.session.scalar(select(Category).where(
            Category.is_active.is_(True), Category.name.ilike(str(category).strip()[:100])
        ))
        category_id = row.id if row else -1

    signals = set()
    purchased_product_ids = set()
    if user is not None and getattr(user, "role", None) == "customer":
        from ..models import RecentViewedProduct, WishlistItem

        for model in (RecentViewedProduct, WishlistItem):
            product_id = db.session.scalar(
                select(model.product_id).where(model.user_id == user.id)
                .order_by(model.id.desc()).limit(1)
            )
            if product_id:
                product = db.session.get(Product, product_id)
                if product:
                    signals.add(product.category_id)
        for row in customer_cart_rows(user.id):
            signals.add(row["product"].category_id)
        recent_orders = db.session.scalars(
            select(Order).where(Order.user_id == user.id)
            .order_by(Order.created_at.desc()).limit(10)
        ).all()
        for order in recent_orders:
            for line in order.items:
                if line.product_id:
                    purchased_product_ids.add(line.product_id)
                    product = db.session.get(Product, line.product_id)
                    if product:
                        signals.add(product.category_id)
    if category_id is None and signals:
        category_id = next(iter(signals))

    popularity = dict(db.session.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .where(OrderItem.product_id.is_not(None))
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(100)
    ).all())
    products, _page = get_catalog_products(
        page=1, per_page=max(10, min(int(limit) * 4, 40)),
        query=str(query or "")[:100], category_id=category_id,
        max_price=upper, in_stock=True,
    )
    category_counts = Counter(signals)
    cart_ids = {row["product"].id for row in customer_cart_rows(user.id)} if user is not None and getattr(user, "role", None) == "customer" else set()
    products.sort(key=lambda item: (
        -(int(item.id in purchased_product_ids or item.id in cart_ids)),
        -int(popularity.get(item.id, 0)),
        -int(category_counts.get(item.category_id, 0)),
        not item.is_featured, item.id,
    ))
    return [_product_summary(item) for item in products[: max(1, min(int(limit), 8))]]


def get_frequently_bought_together_tool(user=None, product_slug="", limit=5, **_kwargs):
    """Use real co-purchases from completed/non-cancelled orders, never model guesses."""
    product = get_product_by_slug(str(product_slug).strip())
    if (not product or product.moderation_status != "approved" or not product.is_available
            or not getattr(product.category, "is_active", True)):
        return []
    matching_orders = select(OrderItem.order_id).where(OrderItem.product_id == product.id).subquery()
    counts = dict(db.session.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.order_id.in_(select(matching_orders.c.order_id)),
               OrderItem.product_id.is_not(None), OrderItem.product_id != product.id,
               Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc()).limit(20)
    ).all())
    if not counts:
        return []
    rows = db.session.scalars(select(Product).where(
        Product.id.in_(counts), Product.is_available.is_(True), Product.moderation_status == "approved",
    )).all()
    rows.sort(key=lambda item: (-counts.get(item.id, 0), item.id))
    return [{**_product_summary(item), "co_purchase_units": int(counts[item.id])}
            for item in rows[: max(1, min(int(limit), 8))] if item.available_stock > 0]


def get_customer_cart_tool(user=None, **_kwargs):
    if user is None or getattr(user, "role", None) != "customer":
        raise ValueError("Sign in as a customer to view the cart.")
    rows = customer_cart_rows(user.id)
    cart = []
    subtotal = Decimal("0.00")
    for row in rows:
        product, variant = row["product"], row["variant"]
        line_total = Decimal(str(row["subtotal"]))
        subtotal += line_total
        cart.append({
            "item_key": row["item"].item_key,
            "product_id": product.id,
            "product": product.name,
            "slug": product.slug,
            "variant_id": variant.id if variant else None,
            "variant": f"{variant.option_name}: {variant.option_value}" if variant else None,
            "quantity": int(row["quantity"]),
            "price": _money(row["price"]),
            "subtotal": _money(line_total),
            "available_stock": int(row["stock"]),
        })
    return {"items": cart, "subtotal": _money(subtotal), "count": len(cart)}


def propose_cart_change_tool(user=None, action="", product_slug="", quantity=1, variant_id=None, item_key="", **_kwargs):
    if user is None or getattr(user, "role", None) != "customer":
        raise ValueError("Sign in as a customer before changing the cart.")
    if action not in {"add", "set_quantity", "remove"}:
        raise ValueError("Choose a supported cart action.")
    if action == "add":
        product = get_product_by_slug(str(product_slug).strip())
        if not product or product.moderation_status != "approved":
            raise ValueError("That product is unavailable.")
        variants = [item for item in product.variants if item.is_active]
        variant = next((item for item in variants if item.id == variant_id), None) if variant_id else None
        if variants and variant is None:
            if len(variants) == 1:
                variant = variants[0]
            else:
                return {"needs_variant": True, "product": _product_summary(product)}
        if not variants and variant_id is not None:
            raise ValueError("That product option is unavailable.")
        stock = variant.stock_quantity if variant else product.stock_quantity
        if stock < 1 or not 1 <= int(quantity) <= min(stock, 20):
            raise ValueError("That quantity is not available.")
        return {
            "requires_confirmation": True, "action": action,
            "product_id": product.id, "variant_id": variant.id if variant else None,
            "product_slug": product.slug,
            "quantity": int(quantity), "product": product.name,
            "price": _money(_display_price(product, variant)),
        }
    rows = customer_cart_rows(user.id)
    row = next((item for item in rows if item["item"].item_key == item_key), None)
    if row is None:
        raise ValueError("That item is not in your cart.")
    target_quantity = 0 if action == "remove" else int(quantity)
    if target_quantity < 0 or target_quantity > 20 or target_quantity > row["stock"]:
        raise ValueError("That quantity is not available.")
    return {
        "requires_confirmation": True, "action": action,
        "item_key": row["item"].item_key, "quantity": target_quantity,
        "product_id": row["product"].id, "product": row["product"].name,
        "price": _money(row["price"]),
    }


def get_customer_orders_tool(user=None, limit=5, **_kwargs):
    if user is None or getattr(user, "role", None) != "customer":
        raise ValueError("Sign in as a customer to view orders.")
    orders = db.session.scalars(
        select(Order).where(Order.user_id == user.id)
        .order_by(Order.created_at.desc()).limit(max(1, min(int(limit), 10)))
    ).all()
    return [{
        "order_number": order.order_number,
        "status": order.status,
        "delivery_status": order.delivery_status,
        "total": _money(order.total),
        "created_at": order.created_at.isoformat() if order.created_at else None,
    } for order in orders]


def get_customer_order_tool(user=None, order_number="", **_kwargs):
    if user is None or getattr(user, "role", None) != "customer":
        raise ValueError("Sign in as a customer to view an order.")
    if not isinstance(order_number, str) or not 1 <= len(order_number) <= 50:
        raise ValueError("Provide a valid order number.")
    order = db.session.scalar(select(Order).where(
        Order.order_number == order_number.strip(), Order.user_id == user.id
    ))
    if order is None:
        return {"error": "Order not found."}
    return {
        "order_number": order.order_number, "status": order.status,
        "delivery_status": order.delivery_status, "total": _money(order.total),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [{"product": item.product_name, "quantity": item.quantity,
                   "subtotal": _money(item.subtotal)} for item in order.items],
        "return_status": order.return_request.status if order.return_request else None,
    }


def get_store_policy_tool(**_kwargs):
    setting = db.session.get(AppSetting, 1)
    return {
        "return_window_days": setting.seller_return_window_days if setting else None,
        "return_instruction": "Check the order page for this order's eligibility and submit a return request there.",
        "delivery_instruction": "Delivery status and timing for a placed order are shown in the customer's order page.",
        "verified_policy": bool(setting and setting.seller_return_window_days),
    }


def get_support_info_tool(user=None, **_kwargs):
    try:
        sender = (current_app.config.get("SUPPORT_EMAIL") or "").strip()
        url = (current_app.config.get("TELEGRAM_SUPPORT_URL") or "").strip()
        from flask import url_for
        support_page = url_for("support.customer_cases") if user is not None and getattr(user, "role", None) == "customer" else None
    except RuntimeError:
        sender = url = support_page = ""
    return {"email": sender or None, "support_url": url or None,
            "support_page": support_page or None,
            "message": "If the assistant cannot verify an answer, contact marketplace support."}


def get_review_summary_source(product_slug="", **_kwargs):
    product = get_product_by_slug(str(product_slug).strip())
    if not product or product.moderation_status != "approved":
        return {"error": "Product not found."}
    reviews = db.session.scalars(
        select(Review).where(Review.product_id == product.id, Review.status == "approved")
        .order_by(Review.created_at.desc()).limit(40)
    ).all()
    return {
        "product": product.name,
        "count": len(reviews),
        "average_rating": (
            round(sum(review.rating for review in reviews) / len(reviews), 1) if reviews else None
        ),
        "reviews": [redact_personal_data(review.comment[:500]) for review in reviews if review.comment][:20],
    }


def build_customer_tool_registry(max_tool_calls=5):
    registry = ToolRegistry(max_calls=max_tool_calls)
    registry.register("search_products", search_products_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Search actual approved, available catalog items using text and filters.",
                      parameters=_SEARCH_SCHEMA)
    registry.register("get_product", get_product_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Read one approved product by its catalog slug.",
                      parameters={"type": "object", "properties": {"slug": {"type": "string", "maxLength": 180}}, "required": ["slug"], "additionalProperties": False})
    registry.register("compare_products", compare_products_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Compare two or three approved catalog products by slug.",
                      parameters={"type": "object", "properties": {"slugs": {"type": "array", "minItems": 2, "maxItems": 3, "items": {"type": "string", "maxLength": 180}}}, "required": ["slugs"], "additionalProperties": False})
    registry.register("get_categories", get_categories_tool, scope=AI_SCOPE_CUSTOMER,
                      description="List active marketplace categories.",
                      parameters={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "additionalProperties": False})
    registry.register("get_recommendations", get_recommendations_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Rank available products using actual catalog and customer context.",
                      parameters={"type": "object", "properties": {"category": {"type": "string", "maxLength": 100}, "query": {"type": "string", "maxLength": 100}, "max_price": {"type": "number", "minimum": 0, "maximum": 100000000}, "limit": {"type": "integer", "minimum": 1, "maximum": 8}}, "additionalProperties": False})
    registry.register("get_frequently_bought_together", get_frequently_bought_together_tool,
                      scope=AI_SCOPE_CUSTOMER,
                      description="Read real products purchased in the same completed customer orders.",
                      parameters={"type": "object", "properties": {
                          "product_slug": {"type": "string", "maxLength": 180},
                          "limit": {"type": "integer", "minimum": 1, "maximum": 8},
                      }, "required": ["product_slug"], "additionalProperties": False})
    registry.register("get_customer_cart", get_customer_cart_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Read the authenticated customer's current cart.")
    registry.register("propose_cart_change", propose_cart_change_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Propose a cart change for the customer to confirm; never checks out.",
                      parameters={"type": "object", "properties": {"action": {"type": "string", "enum": ["add", "set_quantity", "remove"]}, "product_slug": {"type": "string", "maxLength": 180}, "quantity": {"type": "integer", "minimum": 0, "maximum": 20}, "variant_id": {"type": "integer", "minimum": 1}, "item_key": {"type": "string", "maxLength": 80}}, "required": ["action"], "additionalProperties": False})
    registry.register("get_customer_orders", get_customer_orders_tool, scope=AI_SCOPE_CUSTOMER,
                      description="List only the authenticated customer's own recent orders.",
                      parameters={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "additionalProperties": False})
    registry.register("get_customer_order", get_customer_order_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Read one order belonging to the authenticated customer.",
                      parameters={"type": "object", "properties": {"order_number": {"type": "string", "maxLength": 50}}, "required": ["order_number"], "additionalProperties": False})
    registry.register("get_store_policy", get_store_policy_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Return verifiable store policy and support instructions.")
    registry.register("get_support_info", get_support_info_tool, scope=AI_SCOPE_CUSTOMER,
                      description="Return configured human support contacts.")
    registry.register("get_review_summary_source", get_review_summary_source, scope=AI_SCOPE_CUSTOMER,
                      description="Return approved public reviews and ratings for a product.",
                      parameters={"type": "object", "properties": {"product_slug": {"type": "string", "maxLength": 180}}, "required": ["product_slug"], "additionalProperties": False})
    return registry


def handle_marketplace_ai_query(prompt: str, *, user=None, channel="web", context=None,
                               rate_limited=False):
    """Run Customer AI through the provider tools, with a real-catalog fallback."""
    text = (prompt or "").strip()
    if not text:
        return {"ok": False, "answer": "Please ask about a product, cart, order, or store policy.", "scope": AI_SCOPE_CUSTOMER, "data": "", "products": []}
    safe_context = dict(context) if isinstance(context, dict) else {}
    principal = safe_context.pop("principal", None)
    if has_app_context() and not rate_limited:
        try:
            if not consume_ai_request(AI_SCOPE_CUSTOMER, user=user, principal=principal):
                message = "You have reached the assistant request limit. Please try again shortly."
                return {"ok": False, "scope": AI_SCOPE_CUSTOMER, "answer": message,
                        "data": "", "products": [], "fallback": message, "tools_used": []}
        except Exception:
            db.session.rollback()
            message = "The assistant is temporarily unavailable. Please use regular catalog search."
            return {"ok": False, "scope": AI_SCOPE_CUSTOMER, "answer": message,
                    "data": "", "products": [], "fallback": message, "tools_used": []}
    try:
        service = AIService(current_app.config)
        registry = build_customer_tool_registry(service.max_tool_calls)
        result = service.respond(
            text, scope=AI_SCOPE_CUSTOMER, user=user,
            context={"channel": channel, "locale": current_app.config.get("BABEL_DEFAULT_LOCALE", "en_US"), **safe_context},
            tools=registry,
        )
        if result.get("ok"):
            grounded = any(isinstance(item, dict) and item.get("ok") is True
                           for item in result.get("tool_results", []))
            if _requires_marketplace_data(text) and not grounded:
                return _deterministic_fallback(text, user=user)
            response = {**result, "data": result.get("answer", ""),
                        "products": _products_from_result(result)}
            support_tool = next((item for item in result.get("tool_results", [])
                                 if isinstance(item, dict) and item.get("ok")
                                 and isinstance(item.get("result"), dict)
                                 and "support_page" in item["result"]), None)
            if support_tool:
                support = support_tool["result"]
                response["support_contact"] = {
                    "support_page": support.get("support_page"),
                    "email": support.get("email"),
                    "support_url": support.get("support_url"),
                }
            return response
    except RuntimeError:
        pass
    return _deterministic_fallback(text, user=user)


def _products_from_result(result):
    for item in result.get("tool_results", []):
        value = item.get("result")
        if isinstance(value, list) and value and isinstance(value[0], dict) and "slug" in value[0]:
            return value
        if isinstance(value, dict) and "slug" in value:
            return [value]
    return []


def _requires_marketplace_data(prompt):
    lowered = str(prompt or "").lower()
    return any(word in lowered for word in (
        "product", "price", "stock", "available", "search", "find", "show", "compare",
        "recommend", "cart", "basket", "order", "delivery", "return", "refund", "policy", "support",
        "category", "headphone", "phone", "laptop", "shirt", "shoe", "food", "gift",
        "দাম", "স্টক", "পণ্য", "প্রোডাক্ট", "খুঁজ", "দেখাও", "কার্ট", "অর্ডার", "ডেলিভারি",
        "ফেরত", "রিফান্ড", "ক্যাটাগরি", "উপহার", "মূল্য", "सामान", "कीमत", "स्टॉक",
        "खोज", "दिखाओ", "कार्ट", "ऑर्डर", "डिलीवरी", "वापसी", "उपहार",
    )) or bool(re.search(r"\d", str(prompt or "")))


def _deterministic_fallback(prompt, *, user=None):
    """Do common shopping lookups directly from services when no model is available."""
    if not has_app_context():
        answer = "AI is currently unavailable. Please use the standard catalog search or contact support."
        return {"ok": False, "scope": AI_SCOPE_CUSTOMER, "answer": answer, "data": "", "products": [], "fallback": answer, "tools_used": []}
    text = prompt.strip()[:200]
    normalized = text.translate(str.maketrans("০১২৩৪৫৬৭৮৯०१२३४५६७८९", "01234567890123456789"))
    normalized = _normalize_budget_words(normalized)
    lowered = normalized.lower()
    registry = build_customer_tool_registry()

    def invoke(name, **arguments):
        arguments = {key: value for key, value in arguments.items() if value is not None}
        result = registry.call(name, scope=AI_SCOPE_CUSTOMER, user=user, **arguments)
        return result.get("result") if result.get("ok") else {"error": result.get("error")}

    if any(word in lowered for word in ("cart", "basket", "কার্ট", "ঝুড়ি", "ঝুড়ি")):
        data = invoke("get_customer_cart")
        if isinstance(data, dict) and "error" in data:
            answer = "Sign in as a customer to see your personal cart."
        elif not data.get("items"):
            answer = "Your cart is empty."
        else:
            answer = "Your current cart and item totals are shown from your saved cart."
        return _tool_result(answer, data, "get_customer_cart")
    if any(word in lowered for word in ("order", "অর্ডার", "ऑर्डर")):
        data = invoke("get_customer_orders")
        answer = "Your recent order status is shown from your account." if isinstance(data, list) else "Sign in as a customer to see your own orders."
        return _tool_result(answer, data, "get_customer_orders")
    if any(word in lowered for word in ("category", "categories", "ক্যাটাগরি", "श्रेणी")):
        data = invoke("get_categories", limit=12)
        answer = "Active marketplace categories:" if data else "There are no active categories right now."
        return _tool_result(answer, data, "get_categories")
    if any(word in lowered for word in ("return", "refund", "delivery policy", "policy", "ফেরত", "রিফান্ড", "নীতি", "वापसी", "रिफंड")):
        data = invoke("get_store_policy")
        return _tool_result("Verified return and delivery guidance from the store policy is shown below.", data, "get_store_policy")
    if any(word in lowered for word in ("human support", "support agent", "contact support", "speak to support", "সাপোর্ট", "মানুষের সাথে কথা", "सहायता")):
        data = invoke("get_support_info")
        return _tool_result("Use this human support contact or open a support request from your NexHaat account.", data, "get_support_info")

    price_match = re.search(
        r"(?:under|below|less than|within|up to|max(?:imum)?|under tk|under bdt|এর নিচে|নিচে|বাজেট|এর মধ্যে|মধ্যে|से कम|के अंदर|ke moddhe|er moddhe|er niche)\s*(?:tk|৳|bdt|টাকা|रु)?\s*([\d,.]+)\s*(k|thousand|hazar|hajar|হাজার|हज़ार|हजार)?",
        lowered, re.I,
    )
    if price_match is None:
        price_match = re.search(
            r"([\d,.]+)\s*(k|thousand|hazar|hajar|হাজার|हज़ार|हजार)?\s*(?:tk|৳|bdt|টাকা|টাকার|rupees?)?\s*(?:এর মধ্যে|টাকার মধ্যে|এর নিচে|মধ্যে|के अंदर|से कम|er moddhe|er niche|ke andar|ke andar)",
            lowered, re.I,
        )
    maximum = None
    query = normalized
    if price_match:
        value = price_match.group(1).replace(",", "").replace(" ", "")
        try:
            suffix = (price_match.group(2) or "").lower()
            multiplier = Decimal("1000") if suffix in {"k", "thousand", "hazar", "hajar", "হাজার", "हज़ार", "हजार"} else Decimal("1")
            maximum = Decimal(value) * multiplier
            query = (query[:price_match.start()] + " " + query[price_match.end():]).strip()
        except InvalidOperation:
            maximum = None
    strip_patterns = (
        r"(?i)\b(?:show me|find|search|look for|recommend|suggest|please|i need|i want|for me|gift for|compare)\b",
        r"(?:দেখাও|দেখান|খুঁজে দাও|খুঁজুন|আমার দরকার|আমার জন্য|ভালো|একটা|একটি|উপহার|জন্মদিনের জন্য)",
        r"(?i)\b(?:amar|amr|lagbe|dorkar|valo|bhalo|dekhaw|khuje dao|gift|er jonno|er moddhe|ekta)\b",
        r"(?:मुझे|चाहिए|दिखाओ|अच्छा|एक|उपहार)",
    )
    for pattern in strip_patterns:
        query = re.sub(pattern, " ", query, flags=re.I).strip()
    query = re.sub(r"(?i)\b(?:under|below|less than|within|up to|budget|tk|bdt|hazar|hajar|thousand)\b|৳|টাকা|হাজার|এর নিচে|এর মধ্যে|এর|নিচে|মধ্যে|টাকার|के अंदर|से कम|हजार|हज़ार|rupees?|taka\b", " ", query)
    query = re.sub(r"\s+", " ", query).strip(" ,.-")[:100]
    is_gift_or_recommendation = any(token in lowered for token in ("recommend", "suggest", "gift", "উপহার", "জন্মদিন", "উপহার", "सलाह", "उपहार"))
    size_match = re.search(r"(?i)\b(?:size\s*)?(\d{1,3})\b", query)
    size = size_match.group(1) if size_match and any(token in lowered for token in ("size", "সাইজ", "साइज़", "42", "40")) else ""
    if size_match and size:
        query = (query[:size_match.start()] + " " + query[size_match.end():]).strip()
    color = next((item for item in ("black", "white", "red", "blue", "green", "কালো", "সাদা", "লাল", "নীল", "काला", "सफेद", "लाल", "नीला") if item in query.lower()), "")
    if color:
        query = re.sub(re.escape(color), " ", query, flags=re.I).strip()
    if is_gift_or_recommendation:
        if any(token in lowered for token in ("gift", "উপহার", "জন্মদিন", "उपहार")):
            query = re.sub(r"(?i)\b(?:birthday|brother|sister|friend|mother|father|gift|present|for)\b|ভাইয়ের|ভাইয়ের|বোনের|জন্মদিনের|জন্য|উপহার|के लिए|जन्मदिन|भाई|बहन", " ", query)
            query = re.sub(r"\s+", " ", query).strip()
        data = invoke("get_recommendations", query=query[:100], max_price=maximum, limit=5)
        return _tool_result("Recommendations are ranked from currently available marketplace products and your permitted shopping signals.", data, "get_recommendations", products=data if isinstance(data, list) else [])
    is_compare = any(token in lowered for token in ("compare", "which is better", "vs", "তুলনা", "কোনটা ভালো", "कौन बेहतर"))
    data = invoke("search_products", query=query or text[:100], max_price=maximum,
                  size=size, attribute=color, limit=5)
    if is_compare and isinstance(data, list) and len(data) >= 2:
        compared = invoke("compare_products", slugs=[item["slug"] for item in data[:3]])
        return _tool_result("Compare the verified specifications, options, prices, and current stock shown below.", compared, "compare_products", products=compared if isinstance(compared, list) else [])
    if any(token in lowered for token in ("compatible", "goes with", "bought with", "accessory", "সাথে মানাবে", "একসাথে", "साथ में")) and isinstance(data, list) and data:
        related = invoke("get_frequently_bought_together", product_slug=data[0]["slug"], limit=5)
        if isinstance(related, list) and related:
            return _tool_result("These items have appeared with this product in real marketplace orders.", related, "get_frequently_bought_together", products=related)
        return _tool_result("There is not enough order history to verify compatible or frequently bought items.", [], "get_frequently_bought_together")
    products = data if isinstance(data, list) else []
    if products:
        answer = "Matching available products: " + ", ".join(
            f"{row['name']} (BDT {row['price']})" for row in products[:3]
        )
        return _tool_result(answer, products, "search_products", products=products)
    answer = "No available catalog products matched. Try changing the keywords or filters."
    return _tool_result(answer, [], "search_products", products=[])


def _tool_result(answer, data, tool, *, products=None):
    result = {"ok": True, "scope": AI_SCOPE_CUSTOMER, "answer": answer, "data": data,
              "products": products if products is not None else [], "tools_used": [tool]}
    if tool == "get_support_info" and isinstance(data, dict):
        result["support_contact"] = {
            "support_page": data.get("support_page"),
            "email": data.get("email"),
            "support_url": data.get("support_url"),
        }
    return result


def _normalize_budget_words(value):
    text = value.lower()
    words = {
        "দেড় হাজার": "1500", "দেড় হাজার": "1500", "পনেরো হাজার": "15000",
        "দুই হাজার": "2000", "তিন হাজার": "3000", "পাঁচ হাজার": "5000",
        "dui hajar": "2000", "tin hajar": "3000", "pach hajar": "5000",
        "der hajar": "1500", "ponero hajar": "15000",
        "दो हजार": "2000", "तीन हजार": "3000", "पांच हजार": "5000",
        "डेढ़ हजार": "1500", "पंद्रह हजार": "15000",
        "two thousand": "2000", "three thousand": "3000", "five thousand": "5000",
        "fifteen thousand": "15000", "one thousand": "1000",
    }
    for phrase, number in words.items():
        text = text.replace(phrase, number)
    return text
