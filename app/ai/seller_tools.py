"""Seller-scope tools for reviewed suggestions and seller-owned analytics."""

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from decimal import Decimal

from sqlalchemy import func, select

from ..extensions import db
from ..models import Order, OrderItem, Product, ProductVariant, User
from ..services.catalog import get_active_categories, get_catalog_products
from .core.permissions import AI_SCOPE_SELLER
from .core.tools import ToolRegistry


def _seller(user):
    if user is None or getattr(user, "role", None) != "seller" or not user.seller_profile:
        raise ValueError("An authenticated seller account is required.")
    if user.seller_profile.approval_status != "approved":
        raise ValueError("Seller approval is required for seller insights.")
    return user


def _product_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": (product.description or "")[:1000],
        "category": product.category.name if product.category else None,
        "brand": product.brand_name,
        "price": str(product.discount_price or product.price),
        "stock": product.available_stock,
        "image_present": bool(product.image),
        "variants": [
            {"option": item.option_name, "value": item.option_value,
             "price": str(item.price if item.price is not None else product.discount_price or product.price),
             "stock": item.stock_quantity}
            for item in product.variants if item.is_active
        ][:20],
    }


def get_seller_listing_context_tool(user=None, product_id=None, title="", description="", **_kwargs):
    seller = _seller(user)
    product = None
    if product_id is not None:
        if isinstance(product_id, bool) or not isinstance(product_id, int):
            raise ValueError("Product identifier is invalid.")
        product = db.session.scalar(select(Product).where(
            Product.id == product_id, Product.seller_id == seller.id
        ))
        if product is None:
            raise ValueError("Product not found in this seller's catalog.")
    categories = [item.name for item in get_active_categories()[:100]]
    payload = {
        "existing_product": _product_dict(product) if product else None,
        "draft_title": str(title or "")[:160],
        "draft_description": str(description or "")[:3000],
        "valid_categories": categories,
        "instructions": "Return suggestions only. The seller must review and save them through the normal product form.",
    }
    return payload


def get_seller_insights_tool(user=None, **_kwargs):
    seller = _seller(user)
    products = db.session.scalars(select(Product).where(Product.seller_id == seller.id)).all()
    product_ids = [item.id for item in products]
    active_count = sum(1 for item in products if item.is_available and item.moderation_status == "approved")
    low_stock = [
        {"name": item.name, "stock": item.available_stock}
        for item in products if item.is_available and item.available_stock <= 5
    ][:20]
    sold = db.session.execute(
        select(OrderItem.product_name, func.sum(OrderItem.quantity), func.sum(OrderItem.subtotal))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.seller_id == seller.id, Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(20)
    ).all()
    revenue = db.session.scalar(
        select(func.coalesce(func.sum(OrderItem.subtotal), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.seller_id == seller.id, Order.status.notin_(("cancelled", "refunded")))
    ) or Decimal("0.00")
    return {
        "product_count": len(product_ids),
        "active_product_count": active_count,
        "low_stock_products": low_stock,
        "sales": [{"product": name, "units": int(quantity or 0), "gross_bdt": str(amount or 0)}
                  for name, quantity, amount in sold],
        "gross_bdt": str(revenue),
    }


def get_seller_listing_quality_tool(user=None, product_id=None, title="", description="", **_kwargs):
    seller = _seller(user)
    product = None
    if product_id is not None:
        product = db.session.scalar(select(Product).where(
            Product.id == product_id, Product.seller_id == seller.id
        ))
        if product is None:
            raise ValueError("Product not found in this seller's catalog.")
    title = str(title or (product.name if product else "")).strip()
    description = str(description or (product.description if product else "")).strip()
    image_present = bool(product and product.image)
    score = 100
    issues = []
    if len(title) < 12:
        score -= 15
        issues.append("Use a clear, specific title with product type and key attribute.")
    if len(description) < 120:
        score -= 25
        issues.append("Add a fuller description with material, dimensions, compatibility, or use details where applicable.")
    if len(description) > 2500:
        score -= 10
        issues.append("Keep the description focused and easy to scan.")
    if product and not image_present:
        score -= 20
        issues.append("Add a product image.")
    if product and not product.brand_name:
        score -= 5
        issues.append("Add the brand when it is known.")
    return {"score": max(0, score), "issues": issues,
            "title_characters": len(title), "description_characters": len(description),
            "image_present": image_present,
            "note": "Heuristic listing completeness score, not a sales or quality guarantee."}


def find_seller_duplicates_tool(user=None, product_id=None, title="", description="", limit=5, **_kwargs):
    seller = _seller(user)
    source = None
    if product_id is not None:
        source = db.session.scalar(select(Product).where(
            Product.id == product_id, Product.seller_id == seller.id
        ))
        if source is None:
            raise ValueError("Product not found in this seller's catalog.")
    candidate_title = str(title or (source.name if source else "")).strip().lower()
    if len(candidate_title) < 2:
        raise ValueError("Provide a listing title to compare.")
    category_id = source.category_id if source else None
    statement = select(Product).where(
        Product.id != (source.id if source else -1),
        Product.is_available.is_(True), Product.moderation_status == "approved",
    ).order_by(Product.updated_at.desc()).limit(200)
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    candidates = db.session.scalars(statement).all()
    results = []
    for item in candidates:
        similarity = SequenceMatcher(None, candidate_title, item.name.lower()).ratio()
        if similarity >= 0.48:
            results.append({"name": item.name, "slug": item.slug,
                            "category": item.category.name if item.category else None,
                            "similarity_percent": round(similarity * 100)})
    results.sort(key=lambda item: (-item["similarity_percent"], item["name"].lower()))
    return results[: max(1, min(int(limit), 10))]


def get_seller_inventory_forecast_tool(user=None, days=30, **_kwargs):
    seller = _seller(user)
    days = max(7, min(int(days), 90))
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=days)
    prior_start = current_start - timedelta(days=days)
    products = db.session.scalars(select(Product).where(Product.seller_id == seller.id)).all()
    sold_rows = db.session.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.seller_id == seller.id, OrderItem.product_id.is_not(None),
               Order.created_at >= current_start,
               Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_id)
    ).all()
    prior_rows = db.session.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.seller_id == seller.id, OrderItem.product_id.is_not(None),
               Order.created_at >= prior_start, Order.created_at < current_start,
               Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_id)
    ).all()
    current = {product_id: int(quantity or 0) for product_id, quantity in sold_rows}
    previous = {product_id: int(quantity or 0) for product_id, quantity in prior_rows}
    insight = []
    for product in products:
        units = current.get(product.id, 0)
        prior_units = previous.get(product.id, 0)
        average_per_day = Decimal(units) / Decimal(days)
        stock = max(0, int(product.available_stock))
        days_until_stockout = int(Decimal(stock) / average_per_day) if average_per_day > 0 else None
        if units >= max(5, prior_units * 1.5):
            pace = "fast_moving"
        elif units == 0:
            pace = "no_recent_sales"
        elif units <= 2:
            pace = "slow_moving"
        else:
            pace = "steady"
        enough_history = units + prior_units >= 10
        insight.append({"product": product.name, "recent_units_sold": units,
                        "previous_period_units_sold": prior_units, "current_stock": stock,
                        "pace": pace, "low_stock": stock <= 5,
                        "estimated_days_until_stockout": days_until_stockout if enough_history else None,
                        "confidence": "moderate" if enough_history and units >= 5 else "low",
                        "estimate_note": ("Simple recent sales pace; not a guaranteed forecast."
                                          if enough_history else
                                          "Not enough recent sales history for a stock-out estimate.")})
    insight.sort(key=lambda item: (item["estimated_days_until_stockout"] is None,
                                  item["estimated_days_until_stockout"] or 0,
                                  item["product"].lower()))
    return {"window_days": days, "products": insight[:50],
            "forecast_note": "Directional estimate from two recent order windows. Small samples are uncertain."}


def get_seller_price_context_tool(user=None, product_id=None, competitor_price=None, **_kwargs):
    seller = _seller(user)
    if isinstance(product_id, bool) or not isinstance(product_id, int):
        raise ValueError("Choose one of your products.")
    product = db.session.scalar(select(Product).where(
        Product.id == product_id, Product.seller_id == seller.id
    ))
    if product is None:
        raise ValueError("Product not found in this seller's catalog.")
    statement = select(Product.price).where(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_available.is_(True),
        Product.moderation_status == "approved",
    )
    prices = [Decimal(str(value)) for value in db.session.scalars(statement).all()]
    competitor = None
    if competitor_price is not None:
        try:
            competitor = Decimal(str(competitor_price))
        except Exception as error:
            raise ValueError("Competitor price must be a number you provide.") from error
        if not competitor.is_finite() or competitor < 0 or competitor > Decimal("100000000"):
            raise ValueError("Competitor price is outside the supported range.")
    prices.sort()
    return {
        "product": product.name,
        "current_price_bdt": str(product.discount_price or product.price),
        "marketplace_category_sample_count": len(prices),
        "marketplace_category_median_bdt": str(prices[len(prices) // 2]) if prices else None,
        "seller_supplied_competitor_price_bdt": str(competitor) if competitor is not None else None,
        "warning": "Any suggested price is informational; the seller must choose and save it.",
    }


def get_similar_products_tool(user=None, product_id=None, limit=5, **_kwargs):
    seller = _seller(user)
    product = db.session.scalar(select(Product).where(
        Product.id == product_id, Product.seller_id == seller.id
    ))
    if product is None:
        raise ValueError("Product not found in this seller's catalog.")
    rows, _page = get_catalog_products(
        page=1, per_page=max(1, min(int(limit) + 1, 20)), category_id=product.category_id,
        in_stock=True,
    )
    return [
        {"name": row.name, "category": row.category.name, "price_bdt": str(row.price)}
        for row in rows if row.id != product.id
    ][:max(1, min(int(limit), 10))]


def build_seller_tool_registry(max_tool_calls=5):
    registry = ToolRegistry(max_calls=max_tool_calls)
    registry.register(
        "get_seller_listing_context", get_seller_listing_context_tool,
        scope=AI_SCOPE_SELLER,
        description="Read the current seller's own listing and valid categories for suggestions.",
        parameters={"type": "object", "properties": {
            "product_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string", "maxLength": 160},
            "description": {"type": "string", "maxLength": 3000},
        }, "additionalProperties": False},
    )
    registry.register(
        "get_seller_insights", get_seller_insights_tool, scope=AI_SCOPE_SELLER,
        description="Return only the authenticated seller's sales and inventory aggregates.",
    )
    registry.register(
        "get_seller_price_context", get_seller_price_context_tool, scope=AI_SCOPE_SELLER,
        description="Compare a seller's own product with public category prices and optional seller-supplied competitor price.",
        parameters={"type": "object", "properties": {
            "product_id": {"type": "integer", "minimum": 1},
            "competitor_price": {"type": "number", "minimum": 0, "maximum": 100000000},
        }, "required": ["product_id"], "additionalProperties": False},
    )
    registry.register(
        "get_similar_products", get_similar_products_tool, scope=AI_SCOPE_SELLER,
        description="Find public catalog products in the same category for listing comparison.",
        parameters={"type": "object", "properties": {
            "product_id": {"type": "integer", "minimum": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        }, "required": ["product_id"], "additionalProperties": False},
    )
    registry.register(
        "get_seller_listing_quality", get_seller_listing_quality_tool,
        scope=AI_SCOPE_SELLER,
        description="Score listing completeness and identify missing information; does not change the listing.",
        parameters={"type": "object", "properties": {
            "product_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string", "maxLength": 160},
            "description": {"type": "string", "maxLength": 3000},
        }, "additionalProperties": False},
    )
    registry.register(
        "find_seller_duplicates", find_seller_duplicates_tool,
        scope=AI_SCOPE_SELLER,
        description="Find similar public listings as review suggestions only.",
        parameters={"type": "object", "properties": {
            "product_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string", "maxLength": 160},
            "description": {"type": "string", "maxLength": 3000},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        }, "additionalProperties": False},
    )
    registry.register(
        "get_seller_inventory_forecast", get_seller_inventory_forecast_tool,
        scope=AI_SCOPE_SELLER,
        description="Estimate seller-owned stock pace and possible stockout risk with uncertainty labels.",
        parameters={"type": "object", "properties": {
            "days": {"type": "integer", "minimum": 7, "maximum": 90},
        }, "additionalProperties": False},
    )
    return registry
