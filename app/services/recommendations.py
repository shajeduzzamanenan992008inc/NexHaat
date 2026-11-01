"""Deterministic cross-sell and repeat-purchase helpers for the storefront.

Every helper here is server-authoritative. They read the live catalog plus real
order rows, only return products a customer can add to a cart right now
(available, approved, active category, stock on hand), and never trust or
recalculate a client-supplied price. No AI provider call is involved, so the
sections still render when the AI assistants are disabled.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Category, Order, OrderItem, Product

# Statuses that represent a real purchase signal rather than an abandoned or
# reversed checkout.
PURCHASE_STATUSES = ("confirmed", "preparing", "delivered")

_POPULARITY_DEPTH = 500
_CANDIDATE_DEPTH = 200


def _sales_popularity(limit=_POPULARITY_DEPTH):
    """Units sold per product across real orders, highest first."""
    return dict(
        db.session.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                OrderItem.product_id.is_not(None),
                Order.status.in_(PURCHASE_STATUSES),
            )
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        ).all()
    )


def _purchasable(products):
    """Keep only products that can actually be bought right now."""
    return [
        item
        for item in products
        if item.is_available
        and item.moderation_status == "approved"
        and item.category is not None
        and item.category.is_active
        and item.available_stock > 0
    ]


def _candidate_query(*conditions):
    return (
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.variants))
        .join(Category, Category.id == Product.category_id)
        .where(
            Product.is_available.is_(True),
            Product.moderation_status == "approved",
            Category.is_active.is_(True),
            *conditions,
        )
        .order_by(Product.is_featured.desc(), Product.updated_at.desc())
        .limit(_CANDIDATE_DEPTH)
    )


def _frequently_bought_together(product, popularity, limit):
    """Products that orders containing this product also contained."""
    anchor_orders = select(OrderItem.order_id).where(OrderItem.product_id == product.id)
    counts = dict(
        db.session.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                OrderItem.order_id.in_(anchor_orders),
                OrderItem.product_id.is_not(None),
                OrderItem.product_id != product.id,
                Order.status.in_(PURCHASE_STATUSES),
            )
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(50)
        ).all()
    )
    if not counts:
        return []
    products = _purchasable(db.session.scalars(_candidate_query(Product.id.in_(counts))).all())
    products.sort(
        key=lambda item: (
            -int(counts.get(item.id, 0)),
            -int(popularity.get(item.id, 0)),
            item.name.lower(),
        )
    )
    return products[:limit]


def _related_products(product, popularity, limit):
    """Similar products from the same category, store, or brand."""
    matches = [Product.category_id == product.category_id]
    if product.seller_id:
        matches.append(Product.seller_id == product.seller_id)
    if product.brand_name:
        matches.append(Product.brand_name == product.brand_name)
    products = _purchasable(
        db.session.scalars(_candidate_query(Product.id != product.id, or_(*matches))).all()
    )
    products.sort(
        key=lambda item: (
            item.category_id != product.category_id,
            bool(product.seller_id) and item.seller_id != product.seller_id,
            -int(popularity.get(item.id, 0)),
            not item.is_featured,
            item.name.lower(),
        )
    )
    return products[:limit]


def product_recommendations(product, *, together_limit=6, related_limit=8):
    """Return both product-page shelves from one popularity lookup."""
    if product is None or getattr(product, "id", None) is None:
        return {"frequently_bought_together": [], "related": []}
    together_limit = max(1, min(int(together_limit), 12))
    related_limit = max(1, min(int(related_limit), 12))
    popularity = _sales_popularity()
    return {
        "frequently_bought_together": _frequently_bought_together(product, popularity, together_limit),
        "related": _related_products(product, popularity, related_limit),
    }


def cart_cross_sell(rows, *, limit=4):
    """Suggest in-category products that are not already in the cart."""
    if not rows:
        return []
    limit = max(1, min(int(limit), 8))
    category_ids = {row["product"].category_id for row in rows}
    cart_ids = {row["product"].id for row in rows}
    if not category_ids:
        return []
    products = _purchasable(
        db.session.scalars(
            _candidate_query(
                Product.category_id.in_(category_ids),
                Product.id.notin_(cart_ids),
            )
        ).all()
    )
    if not products:
        return []
    popularity = _sales_popularity()
    products.sort(
        key=lambda item: (
            -int(popularity.get(item.id, 0)),
            not item.is_featured,
            item.name.lower(),
        )
    )
    return products[:limit]
