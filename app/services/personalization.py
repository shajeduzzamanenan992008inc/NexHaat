"""Deterministic, private customer product ranking without an AI call per page."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from ..extensions import db
from ..models import Order, OrderItem, Product, RecentViewedProduct, WishlistItem
from .cart import customer_cart_rows


def personalized_products_for_user(user, limit=8):
    if user is None or getattr(user, "role", None) != "customer":
        return []
    limit = max(1, min(int(limit), 12))
    since = datetime.now(timezone.utc) - timedelta(days=30)
    category_score = {}
    excluded = set()
    recent = db.session.execute(
        select(RecentViewedProduct.product_id, Product.category_id)
        .join(Product, Product.id == RecentViewedProduct.product_id)
        .where(RecentViewedProduct.user_id == user.id, RecentViewedProduct.viewed_at >= since)
        .order_by(RecentViewedProduct.viewed_at.desc()).limit(30)
    ).all()
    for product_id, category_id in recent:
        category_score[category_id] = category_score.get(category_id, 0) + 3
        excluded.add(product_id)
    wishlist = db.session.execute(
        select(WishlistItem.product_id, Product.category_id)
        .join(Product, Product.id == WishlistItem.product_id)
        .where(WishlistItem.user_id == user.id)
    ).all()
    for product_id, category_id in wishlist:
        category_score[category_id] = category_score.get(category_id, 0) + 4
        excluded.add(product_id)
    for row in customer_cart_rows(user.id):
        category_id = row["product"].category_id
        category_score[category_id] = category_score.get(category_id, 0) + 5
        excluded.add(row["product"].id)
    order_categories = db.session.execute(
        select(OrderItem.product_id, Product.category_id)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Order.user_id == user.id, Order.status.notin_(("cancelled", "refunded")),
               OrderItem.product_id.is_not(None))
        .order_by(Order.created_at.desc()).limit(50)
    ).all()
    for product_id, category_id in order_categories:
        category_score[category_id] = category_score.get(category_id, 0) + 2
        excluded.add(product_id)
    popularity = dict(db.session.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.product_id.is_not(None), Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_id).order_by(func.sum(OrderItem.quantity).desc()).limit(500)
    ).all())
    rows = db.session.scalars(select(Product).where(
        Product.is_available.is_(True), Product.moderation_status == "approved",
    ).order_by(Product.is_featured.desc(), Product.updated_at.desc()).limit(500)).all()
    rows = [item for item in rows if item.available_stock > 0 and item.id not in excluded]
    rows.sort(key=lambda item: (
        -category_score.get(item.category_id, 0),
        -int(popularity.get(item.id, 0)), not item.is_featured, item.name.lower(),
    ))
    return rows[:limit]


def frequently_bought_with_for_user(user, limit=6):
    if user is None or getattr(user, "role", None) != "customer":
        return []
    limit = max(1, min(int(limit), 10))
    anchor_ids = {row["product"].id for row in customer_cart_rows(user.id)}
    if not anchor_ids:
        anchor_ids = set(db.session.scalars(
            select(OrderItem.product_id).join(Order, Order.id == OrderItem.order_id)
            .where(Order.user_id == user.id, OrderItem.product_id.is_not(None),
                   Order.status.notin_(("cancelled", "refunded")))
            .order_by(Order.created_at.desc()).limit(10)
        ).all())
    if not anchor_ids:
        return []
    anchor_order_ids = select(OrderItem.order_id).where(OrderItem.product_id.in_(anchor_ids)).subquery()
    counts = dict(db.session.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.order_id.in_(select(anchor_order_ids.c.order_id)),
               OrderItem.product_id.is_not(None), ~OrderItem.product_id.in_(anchor_ids),
               Order.status.notin_(("cancelled", "refunded")))
        .group_by(OrderItem.product_id).order_by(func.sum(OrderItem.quantity).desc()).limit(50)
    ).all())
    if not counts:
        return []
    products = db.session.scalars(select(Product).where(
        Product.id.in_(counts), Product.is_available.is_(True),
        Product.moderation_status == "approved",
    )).all()
    products = [item for item in products if item.available_stock > 0]
    products.sort(key=lambda item: (-counts.get(item.id, 0), item.name.lower()))
    return products[:limit]
