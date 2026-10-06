"""Opt-in, in-app product alerts with a one-per-customer daily cap."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import event, exists, inspect, insert, or_, select, update, union

from ..extensions import db
from ..models import (
    AIPreferences, CustomerCartItem, Notification, Order, OrderItem, Product,
    ProductVariant, RecentViewedProduct, User, WishlistItem,
)


_SMART_ALERT_LINK = "from=ai-alert"
_TRACKED_PRODUCT_FIELDS = {"price", "discount_price", "stock_quantity", "is_available"}
_TRACKED_VARIANT_FIELDS = {"price", "stock_quantity", "is_active"}


def _emit_opted_in_alerts(connection, product_id, slug):
    if not slug:
        return 0
    now = datetime.now(timezone.utc)
    interested = union(
        select(WishlistItem.user_id.label("user_id")).where(WishlistItem.product_id == product_id),
        select(CustomerCartItem.user_id.label("user_id")).where(CustomerCartItem.product_id == product_id),
    ).subquery()
    eligible = connection.execute(
        select(AIPreferences.user_id).join(
            interested, interested.c.user_id == AIPreferences.user_id
        ).where(AIPreferences.smart_notifications_enabled.is_(True)).distinct()
    ).scalars().all()
    created = 0
    notification_table = Notification.__table__
    for user_id in eligible:
        claim = connection.execute(
            update(AIPreferences.__table__).where(
                AIPreferences.user_id == user_id,
                AIPreferences.smart_notifications_enabled.is_(True),
                or_(AIPreferences.last_smart_notification_at.is_(None),
                    AIPreferences.last_smart_notification_at <= now - timedelta(days=1)),
            ).values(last_smart_notification_at=now)
        )
        if claim.rowcount != 1:
            continue
        connection.execute(insert(notification_table).values(
            user_id=user_id, type="system",
            message="A product you saved has a price or availability update. Review the current listing.",
            link=f"/food/{slug}?{_SMART_ALERT_LINK}", is_read=False, created_at=now,
        ))
        created += 1
    return created


@event.listens_for(Product, "after_update")
def _product_updated(mapper, connection, target):
    state = inspect(target)
    if any(state.attrs[name].history.has_changes() for name in _TRACKED_PRODUCT_FIELDS):
        _emit_opted_in_alerts(connection, target.id, target.slug)


def _variant_changed(mapper, connection, target):
    state = inspect(target)
    if not any(state.attrs[name].history.has_changes() for name in _TRACKED_VARIANT_FIELDS):
        return
    product = connection.execute(
        select(Product.id, Product.slug).where(Product.id == target.product_id)
    ).first()
    if product:
        _emit_opted_in_alerts(connection, product.id, product.slug)


event.listen(ProductVariant, "after_update", _variant_changed)


def _variant_created(mapper, connection, target):
    product = connection.execute(
        select(Product.id, Product.slug).where(Product.id == target.product_id)
    ).first()
    if product and target.is_active and target.stock_quantity > 0:
        _emit_opted_in_alerts(connection, product.id, product.slug)


event.listen(ProductVariant, "after_insert", _variant_created)


def send_smart_notification_digest(*, limit=200, now=None):
    """Create opt-in in-app cart reminders or personalized product picks.

    Run from a daily scheduler. This deterministic job never calls an AI provider,
    sends email, or stores shopping conversation data.
    """
    now = now or datetime.now(timezone.utc)
    limit = max(1, min(int(limit), 1000))
    preferences = db.session.scalars(
        select(AIPreferences).join(User, User.id == AIPreferences.user_id)
        .where(AIPreferences.smart_notifications_enabled.is_(True),
               User.role == "customer", User.is_active.is_(True))
        .order_by(AIPreferences.updated_at.asc()).limit(limit)
    ).all()
    totals = {"cart_reminders": 0, "recommendations": 0, "skipped": 0}

    for preference in preferences:
        cart_item = db.session.scalar(
            select(CustomerCartItem).where(CustomerCartItem.user_id == preference.user_id)
            .order_by(CustomerCartItem.updated_at.asc(), CustomerCartItem.id.asc()).limit(1)
        )
        old_cart = False
        if cart_item is not None:
            updated_at = cart_item.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            old_cart = updated_at <= now - timedelta(days=1)

        kind = "cart" if old_cart else "recommendation"
        last_kind_sent = (preference.last_cart_reminder_at if kind == "cart"
                          else preference.last_recommendation_notification_at)
        if last_kind_sent is not None:
            if last_kind_sent.tzinfo is None:
                last_kind_sent = last_kind_sent.replace(tzinfo=timezone.utc)
            if last_kind_sent > now - timedelta(days=7):
                totals["skipped"] += 1
                continue

        if kind == "recommendation":
            has_signal = db.session.query(
                exists().where(RecentViewedProduct.user_id == preference.user_id)
                | exists().where(WishlistItem.user_id == preference.user_id)
                | exists().where(CustomerCartItem.user_id == preference.user_id)
                | exists().where(Order.user_id == preference.user_id)
            ).scalar()
            if not has_signal:
                totals["skipped"] += 1
                continue
            from .personalization import personalized_products_for_user

            customer = db.session.get(User, preference.user_id)
            picks = personalized_products_for_user(customer, limit=1)
            if not picks:
                totals["skipped"] += 1
                continue
            product = picks[0]
            message = f"A product pick based on your NexHaat activity: {product.name[:120]}. Review its current listing and price."
            link = f"/food/{product.slug}?from=ai-recommendation"
        else:
            message = "Some items are still in your cart. Review current availability and prices when you are ready."
            link = "/cart?from=ai-cart-reminder"

        # Claim the daily account-wide cap and the per-kind weekly cap atomically.
        daily_ready = or_(AIPreferences.last_smart_notification_at.is_(None),
                          AIPreferences.last_smart_notification_at <= now - timedelta(days=1))
        weekly_column = (AIPreferences.last_cart_reminder_at if kind == "cart"
                         else AIPreferences.last_recommendation_notification_at)
        weekly_ready = or_(weekly_column.is_(None), weekly_column <= now - timedelta(days=7))
        values = {"last_smart_notification_at": now}
        values["last_cart_reminder_at" if kind == "cart"
               else "last_recommendation_notification_at"] = now
        claimed = db.session.execute(
            update(AIPreferences).where(
                AIPreferences.user_id == preference.user_id,
                AIPreferences.smart_notifications_enabled.is_(True),
                daily_ready, weekly_ready,
            ).values(**values)
        )
        if claimed.rowcount != 1:
            totals["skipped"] += 1
            continue
        db.session.add(Notification(user_id=preference.user_id, type="system",
                                    message=message, link=link, is_read=False,
                                    created_at=now))
        totals["cart_reminders" if kind == "cart" else "recommendations"] += 1

    db.session.commit()
    return totals
