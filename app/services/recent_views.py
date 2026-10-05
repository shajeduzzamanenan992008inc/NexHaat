"""Bounded customer tracking for recently viewed products."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from ..extensions import db
from ..models import Product, RecentViewedProduct

MAX_RECENT_PRODUCTS = 8
RECENT_VIEW_RETENTION_DAYS = 30


def _trim_recent_views_for_user(user_id, *, limit=MAX_RECENT_PRODUCTS):
    rows = db.session.scalars(
        select(RecentViewedProduct)
        .where(RecentViewedProduct.user_id == user_id)
        .order_by(RecentViewedProduct.viewed_at.desc(), RecentViewedProduct.id.desc())
    ).all()
    if len(rows) > limit:
        for row in rows[limit:]:
            db.session.delete(row)

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_VIEW_RETENTION_DAYS)
    expired = db.session.scalars(
        select(RecentViewedProduct).where(
            RecentViewedProduct.user_id == user_id,
            RecentViewedProduct.viewed_at < cutoff,
        )
    ).all()
    for row in expired:
        db.session.delete(row)


def record_recent_view(user, product):
    """Persist a customer product view while keeping the history bounded and private."""
    if user is None or product is None or getattr(user, "role", None) != "customer":
        return None
    if getattr(product, "is_available", None) is False:
        return None

    now = datetime.now(timezone.utc)
    row = db.session.scalar(
        select(RecentViewedProduct).where(
            RecentViewedProduct.user_id == user.id,
            RecentViewedProduct.product_id == product.id,
        )
    )
    if row is None:
        row = RecentViewedProduct(user_id=user.id, product_id=product.id, viewed_at=now)
        db.session.add(row)
    else:
        row.viewed_at = now

    _trim_recent_views_for_user(user.id)
    db.session.commit()
    return row


def recent_products_for_user(user, *, limit=MAX_RECENT_PRODUCTS):
    """Return the distinct available product set most recently viewed by the user."""
    if user is None or getattr(user, "role", None) != "customer":
        return []

    _trim_recent_views_for_user(user.id, limit=limit)
    return db.session.scalars(
        select(Product)
        .join(RecentViewedProduct, RecentViewedProduct.product_id == Product.id)
        .where(
            RecentViewedProduct.user_id == user.id,
            Product.is_available.is_(True),
            Product.moderation_status == "approved",
        )
        .order_by(RecentViewedProduct.viewed_at.desc(), RecentViewedProduct.id.desc())
        .limit(limit)
    ).all()
