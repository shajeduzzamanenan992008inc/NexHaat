"""Public storefront pages and seller trust summaries.

Store pages are built from the same server-authoritative queries as the catalog:
only approved, active sellers and publicly visible products are ever returned.
Store slugs are derived from the published store name; there is no separate slug
column yet, so two stores with an identical name resolve to the oldest account.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import contains_eager, selectinload

from ..extensions import db
from ..models import AppSetting, Category, Order, OrderItem, Product, Review, SellerProfile
from ..repositories.catalog import PURCHASE_STATUSES, active_product_conditions
from .checkout import DELIVERY_FEE

STORE_LOOKUP_LIMIT = 500
DEFAULT_RETURN_WINDOW_DAYS = 14

def store_slug(store_name):
    """Deterministic public slug for a store name."""
    return re.sub(r"[^a-z0-9]+", "-", (store_name or "").strip().lower()).strip("-")[:140]

def get_public_store(slug):
    """Resolve ``/store/<slug>`` to an approved, active seller profile."""
    wanted = store_slug(slug)
    if not wanted:
        return None
    profiles = db.session.scalars(
        select(SellerProfile)
        .options(selectinload(SellerProfile.user))
        .where(SellerProfile.approval_status == "approved")
        .order_by(SellerProfile.id.asc())
        .limit(STORE_LOOKUP_LIMIT)
    ).all()
    for profile in profiles:
        user = profile.user
        if user is None or not user.is_active:
            continue
        if store_slug(profile.store_name) == wanted:
            return profile
    return None

def store_names_for_sellers(seller_ids):
    """Map seller user IDs to their published store names in one query.

    Catalog serializers use this to expose real seller information without an
    N+1 lookup per product. A seller without a profile simply has no entry.
    """
    ids = {int(seller_id) for seller_id in seller_ids if seller_id}
    if not ids:
        return {}
    rows = db.session.execute(
        select(SellerProfile.user_id, SellerProfile.store_name).where(
            SellerProfile.user_id.in_(ids)
        )
    ).all()
    return dict(rows)

def store_listing(seller_id, limit=12):
    """Public listings for one store, featured and recently updated first."""
    return db.session.scalars(
        select(Product)
        .join(Product.category)
        .options(contains_eager(Product.category))
        .where(Product.seller_id == seller_id, *active_product_conditions())
        .order_by(Product.is_featured.desc(), Product.updated_at.desc(), Product.name.asc())
        .limit(limit)
    ).all()

def store_product_count(seller_id):
    return db.session.scalar(
        select(func.count(Product.id))
        .join(Category, Category.id == Product.category_id)
        .where(Product.seller_id == seller_id, *active_product_conditions())
    ) or 0

def store_rating(seller_id):
    """Average approved review rating across the store's products."""
    count, average = db.session.execute(
        select(func.count(Review.id), func.avg(Review.rating))
        .join(Product, Product.id == Review.product_id)
        .where(Product.seller_id == seller_id, Review.status == "approved")
    ).one()
    count = int(count or 0)
    return {
        "count": count,
        "average": round(float(average), 1) if count and average is not None else None,
    }

def store_sold_units(seller_id):
    """Real purchased units for the store, excluding cancelled and declined orders."""
    return db.session.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Product.seller_id == seller_id, Order.status.in_(PURCHASE_STATUSES))
    ) or 0

def store_policy_summary():
    """Marketplace-wide delivery and returns policies shown on a store page."""
    setting = db.session.scalar(select(AppSetting).order_by(AppSetting.id.desc()))
    window = getattr(setting, "seller_return_window_days", None) if setting else None
    return {
        "delivery_fee": DELIVERY_FEE,
        "return_window_days": int(window) if window else DEFAULT_RETURN_WINDOW_DAYS,
    }

def store_summary(profile):
    """Everything a store page renders, gathered without per-row queries."""
    seller_id = profile.user_id
    return {
        "store": profile,
        "profile": profile,
        "slug": store_slug(profile.store_name),
        "product_count": store_product_count(seller_id),
        "rating": store_rating(seller_id),
        "sold_units": store_sold_units(seller_id),
        "products": store_listing(seller_id),
        "policies": store_policy_summary(),
    }
