"""Read-only catalog query building blocks shared by services and the API.

The helpers here only build bounded, server-authoritative ``select`` statements.
Relevance scoring, validation, and pagination live in ``app.services.catalog``.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import contains_eager, selectinload

from ..extensions import db
from ..models import Category, Order, OrderItem, Product, ProductTranslation, Review, User

# Statuses that represent a real purchase signal rather than an abandoned or
# reversed checkout. Shared by discovery ranking and recommendations.
PURCHASE_STATUSES = ("confirmed", "preparing", "delivered")

def active_product_conditions():
    """Conditions every publicly visible product must satisfy."""
    return (
        Product.is_available.is_(True),
        Product.moderation_status == "approved",
        Category.is_active.is_(True),
    )

def active_categories():
    return select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())

def active_products():
    return (
        select(Product)
        .join(Product.category)
        .options(contains_eager(Product.category))
        .where(*active_product_conditions())
        .order_by(Product.is_featured.desc(), Product.name.asc())
    )

def products_for_category(category):
    return active_products().where(Product.category_id == category.id)

def _listing_loaders():
    """Eager-load exactly what listing cards read, so listings never N+1."""
    return (
        selectinload(Product.translations),
        selectinload(Product.seller).selectinload(User.seller_profile),
    )

def search_candidate_products(tokens, limit=300):
    """Bounded candidate pool for weighted relevance scoring.

    Every token may match the product name, brand, description, its category, or
    a translation. The pool is capped so a broad query can never scan the whole
    catalog, and the caller ranks the pool afterwards.
    """
    filters = []
    for token in tokens:
        pattern = f"%{token}%"
        filters.extend(
            (
                Product.name.ilike(pattern),
                Product.brand_name.ilike(pattern),
                Product.description.ilike(pattern),
                Product.category.has(Category.name.ilike(pattern)),
                Product.translations.any(ProductTranslation.name.ilike(pattern)),
                Product.translations.any(ProductTranslation.description.ilike(pattern)),
            )
        )
    if not filters:
        return active_products().where(Product.id.in_([]))
    return (
        active_products()
        .options(*_listing_loaders())
        .where(or_(*filters))
        .limit(limit)
    )

def bounded_active_products(limit=200):
    """Bounded public product pool used by the fuzzy scan and empty-result fallback."""
    return active_products().options(*_listing_loaders()).limit(limit)

def product_sales_totals(statuses=PURCHASE_STATUSES, limit=500):
    """Total units sold per product across real orders, highest first."""
    return dict(
        db.session.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                OrderItem.product_id.is_not(None),
                Order.status.in_(statuses),
            )
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        ).all()
    )

def approval_rating_product_ids(min_rating):
    """Product ids whose approved reviews average at least ``min_rating``.

    Returned as a subquery so the filter stays server-side and paginates with the
    rest of the listing query instead of being applied in Python.
    """
    return (
        select(Review.product_id)
        .where(Review.status == "approved")
        .group_by(Review.product_id)
        .having(func.avg(Review.rating) >= float(min_rating))
    )

def active_brand_counts(limit=100):
    """Public brands with their listing counts, most stocked first."""
    return db.session.execute(
        select(Product.brand_name, func.count(Product.id))
        .join(Category, Category.id == Product.category_id)
        .where(
            *active_product_conditions(),
            Product.brand_name.is_not(None),
            Product.brand_name != "",
        )
        .group_by(Product.brand_name)
        .order_by(func.count(Product.id).desc(), Product.brand_name.asc())
        .limit(limit)
    ).all()

def active_category_counts(limit=100):
    """Active categories with their public listing counts, largest first."""
    return db.session.execute(
        select(Category.name, Category.slug, func.count(Product.id))
        .join(Product, Product.category_id == Category.id)
        .where(*active_product_conditions())
        .group_by(Category.id, Category.name, Category.slug)
        .order_by(func.count(Product.id).desc(), Category.name.asc())
        .limit(limit)
    ).all()
