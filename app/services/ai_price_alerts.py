"""Record observed catalog prices and trigger explicit customer target alerts."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import event, insert, inspect, select, update

from ..extensions import db
from ..models import AIProductPriceAlert, AIProductPriceHistory, Notification, Product


def _effective_price(regular_price, discount_price):
    return Decimal(str(discount_price if discount_price is not None else regular_price))


def _record_observation(connection, product, *, regular_price=None, discount_price=None):
    regular_price = regular_price if regular_price is not None else product.price
    discount_price = discount_price if discount_price is not None else product.discount_price
    effective_price = _effective_price(regular_price, discount_price)
    connection.execute(insert(AIProductPriceHistory.__table__).values(
        product_id=product.id, regular_price=regular_price, discount_price=discount_price,
        effective_price=effective_price, recorded_at=datetime.now(timezone.utc),
    ))
    return effective_price


def _notify_target_alerts(connection, product, *, old_price, new_price):
    if old_price is None or new_price >= old_price:
        return 0
    alerts = connection.execute(
        select(AIProductPriceAlert.id, AIProductPriceAlert.user_id,
               AIProductPriceAlert.target_price).where(
            AIProductPriceAlert.product_id == product.id,
            AIProductPriceAlert.active.is_(True),
            AIProductPriceAlert.target_price >= new_price,
            AIProductPriceAlert.target_price < old_price,
        )
    ).all()
    now = datetime.now(timezone.utc)
    created = 0
    for alert_id, user_id, target_price in alerts:
        claimed = connection.execute(
            update(AIProductPriceAlert.__table__).where(
                AIProductPriceAlert.id == alert_id,
                AIProductPriceAlert.active.is_(True),
            ).values(active=False, notified_at=now)
        )
        if claimed.rowcount != 1:
            continue
        connection.execute(insert(Notification.__table__).values(
            user_id=user_id, type="system",
            message=(f"{product.name[:100]} is now BDT {new_price:.2f}, at or below your "
                     f"BDT {Decimal(str(target_price)):.2f} target."),
            link=f"/food/{product.slug}?from=ai-price-alert",
            is_read=False, created_at=now,
        ))
        created += 1
    return created


@event.listens_for(Product, "after_insert")
def _product_created(mapper, connection, target):
    if target.moderation_status == "approved" and target.is_available:
        _record_observation(connection, target)


@event.listens_for(Product, "after_update")
def _product_price_changed(mapper, connection, target):
    state = inspect(target)
    old_regular = state.attrs.price.history.deleted
    old_discount = state.attrs.discount_price.history.deleted
    price_changed = (state.attrs.price.history.has_changes()
                     or state.attrs.discount_price.history.has_changes())
    became_public = bool(
        state.attrs.moderation_status.history.has_changes()
        and target.moderation_status == "approved"
    )
    if not target.is_available or target.moderation_status != "approved":
        return
    if not price_changed and not became_public:
        return

    old_price = connection.scalar(
        select(AIProductPriceHistory.effective_price).where(
            AIProductPriceHistory.product_id == target.id
        ).order_by(AIProductPriceHistory.recorded_at.desc(), AIProductPriceHistory.id.desc()).limit(1)
    )
    if old_price is None and price_changed:
        regular = old_regular[0] if old_regular else target.price
        discount = old_discount[0] if old_discount else target.discount_price
        old_price = _effective_price(regular, discount)
    elif old_price is not None:
        old_price = Decimal(str(old_price))
    new_price = _record_observation(connection, target)
    if price_changed:
        _notify_target_alerts(connection, target, old_price=old_price, new_price=new_price)


def save_price_alert(user, product, target_price):
    has_observation = db.session.scalar(select(AIProductPriceHistory.id).where(
        AIProductPriceHistory.product_id == product.id
    ).limit(1))
    if not has_observation:
        db.session.add(AIProductPriceHistory(
            product_id=product.id, regular_price=product.price,
            discount_price=product.discount_price,
            effective_price=_effective_price(product.price, product.discount_price),
        ))
    alert = db.session.scalar(select(AIProductPriceAlert).where(
        AIProductPriceAlert.user_id == user.id,
        AIProductPriceAlert.product_id == product.id,
    ).with_for_update())
    now = datetime.now(timezone.utc)
    if alert is None:
        alert = AIProductPriceAlert(user_id=user.id, product_id=product.id,
                                    target_price=target_price)
        db.session.add(alert)
    else:
        alert.target_price = target_price
        alert.active = True
        alert.notified_at = None
    current_price = _effective_price(product.price, product.discount_price)
    if current_price <= target_price:
        alert.active = False
        alert.notified_at = now
        db.session.add(Notification(
            user_id=user.id, type="system",
            message=f"{product.name[:100]} is currently BDT {current_price:.2f}, at or below your BDT {target_price:.2f} target.",
            link=f"/food/{product.slug}?from=ai-price-alert", is_read=False,
            created_at=now,
        ))
    db.session.commit()
    return alert


def cancel_price_alert(user, product):
    alert = db.session.scalar(select(AIProductPriceAlert).where(
        AIProductPriceAlert.user_id == user.id,
        AIProductPriceAlert.product_id == product.id,
        AIProductPriceAlert.active.is_(True),
    ))
    if alert is not None:
        alert.active = False
        db.session.commit()
    return alert is not None


def observed_price_history(product_id, limit=12):
    rows = db.session.scalars(
        select(AIProductPriceHistory).where(AIProductPriceHistory.product_id == product_id)
        .order_by(AIProductPriceHistory.recorded_at.desc(), AIProductPriceHistory.id.desc())
        .limit(max(1, min(int(limit), 24)))
    ).all()
    return [{
        "regular_price": str(row.regular_price),
        "discount_price": str(row.discount_price) if row.discount_price is not None else None,
        "effective_price": str(row.effective_price),
        "recorded_at": row.recorded_at.isoformat(),
    } for row in rows]
