"""Shared server-authoritative COD checkout for HTML and API clients."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from flask import current_app, url_for
from flask_babel import gettext
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    AppSetting,
    CustomerCartItem,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    PromotionCode,
    PromotionRedemption,
)
from .mail import enqueue_order_emails
from .notifications import notify
from .order_timeline import record_order_event

DELIVERY_FEE = Decimal("2.50")


class CheckoutError(ValueError):
    """A safe checkout validation or inventory error suitable for clients."""


def create_checkout_orders(
    user, rows, *, name, phone, address, email, payment_method, city="", promotion_code=None
):
    """Validate current inventory, reserve it, split seller orders, and commit."""
    if not rows:
        raise CheckoutError(gettext("Your cart is empty."))
    if (
        not email or len(email) > 255 or "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        raise CheckoutError(gettext("Please provide a valid email address for order updates."))
    if payment_method not in {"cod", "sslcommerz"}:
        raise CheckoutError(gettext("Please choose a supported payment method."))
    if not 2 <= len(name) <= 120 or not 7 <= len(phone) <= 30 or not 8 <= len(address) <= 2000:
        raise CheckoutError(gettext("Please provide a valid name, phone, and delivery address."))
    city = (city or "").strip()
    if payment_method == "sslcommerz" and not 2 <= len(city) <= 100:
        raise CheckoutError(gettext("Please provide your city for online payment."))

    for row in rows:
        product = db.session.scalar(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == row["product"].id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not product or not product.is_available or not product.category.is_active:
            raise CheckoutError(gettext("A cart item is no longer available. Please review your cart."))

        variant = None
        if row.get("variant_id"):
            variant = db.session.scalar(
                select(ProductVariant)
                .where(
                    ProductVariant.id == row["variant_id"],
                    ProductVariant.product_id == product.id,
                    ProductVariant.is_active.is_(True),
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if variant is None:
                raise CheckoutError(gettext("A cart option is no longer available. Please review your cart."))
        elif db.session.scalar(
            select(ProductVariant.id).where(
                ProductVariant.product_id == product.id,
                ProductVariant.is_active.is_(True),
            ).limit(1)
        ):
            raise CheckoutError(gettext("Choose a product option before checkout."))

        stock = variant.stock_quantity if variant else product.stock_quantity
        if stock < row["quantity"]:
            raise CheckoutError(
                gettext("Not enough stock is available for one or more items. Please update your cart.")
            )
        if variant:
            variant.stock_quantity -= row["quantity"]
            row["variant_label"] = f"{variant.option_name}: {variant.option_value}"
            row["sku_snapshot"] = variant.sku
            row["price"] = variant.price if variant.price is not None else product.display_price
        else:
            product.stock_quantity -= row["quantity"]
            row["variant_label"] = None
            row["sku_snapshot"] = None
            row["price"] = product.display_price
        row["product"] = product
        row["variant_id"] = variant.id if variant else None
        row["subtotal"] = row["price"] * row["quantity"]
        row["seller_id"] = product.seller_id

    checkout_group = f"FB-{uuid4().hex.upper()}"
    seller_groups = {}
    for row in rows:
        seller_groups.setdefault(row["seller_id"], []).append(row)
    seller_subtotals = {
        seller_id: sum((row["subtotal"] for row in group_rows), Decimal("0.00"))
        for seller_id, group_rows in seller_groups.items()
    }
    subtotal_before_discount = sum(seller_subtotals.values(), Decimal("0.00"))
    delivery_total = DELIVERY_FEE * len(seller_groups)
    promotion_discount = Decimal("0.00")
    promotion = None
    eligible_subtotals = seller_subtotals
    if promotion_code:
        from .promotions import (
            PromotionError,
            calculate_discount_for_order,
            get_active_promotion,
        )

        try:
            promotion = get_active_promotion(promotion_code, lock=True)
            if promotion.seller_id is not None:
                eligible_subtotals = {
                    seller_id: subtotal
                    for seller_id, subtotal in seller_subtotals.items()
                    if seller_id == promotion.seller_id
                }
            eligible_total = sum(eligible_subtotals.values(), Decimal("0.00"))
            promotion_discount = calculate_discount_for_order(
                eligible_total,
                promotion_code,
                seller_id=promotion.seller_id,
                promotion=promotion,
            )
        except PromotionError as error:
            raise CheckoutError(gettext(str(error))) from error

    from .promotions import allocate_discount_shares

    eligible_shares = allocate_discount_shares(promotion_discount, eligible_subtotals)
    discount_shares = {seller_id: eligible_shares.get(seller_id, Decimal("0.00")) for seller_id in seller_groups}

    setting = db.session.get(AppSetting, 1)
    commission_rate = (
        Decimal(setting.commission_rate_percent)
        if setting and setting.commission_rate_percent is not None
        else None
    )
    if payment_method == "sslcommerz":
        if commission_rate is None:
            if current_app.config.get("ENVIRONMENT") == "production":
                raise CheckoutError(
                    gettext("Online payments are temporarily unavailable. Please try cash on delivery.")
                )
            commission_rate = Decimal("0.00")
        return_window_days = (
            setting.seller_return_window_days if setting else 14
        )
        total = subtotal_before_discount + delivery_total - promotion_discount
        payment = Payment(
            checkout_group=checkout_group,
            user_id=user.id if user else None,
            amount=total,
            currency="BDT",
            status="pending",
            expires_at=datetime.now(UTC)
            + timedelta(minutes=max(1, int(current_app.config.get("PAYMENT_SESSION_MINUTES", 15)))),
        )
        db.session.add(payment)
        db.session.flush()
    else:
        payment = None
        commission_rate = None
        return_window_days = None

    orders = []
    for index, (seller_id, group_rows) in enumerate(seller_groups.items(), start=1):
        subtotal = sum((row["subtotal"] for row in group_rows), Decimal("0.00"))
        seller_discount = discount_shares[seller_id]
        net_subtotal = subtotal - seller_discount
        commission = (
            (net_subtotal * commission_rate / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if commission_rate is not None
            else None
        )
        order = Order(
            order_number=f"{checkout_group}-{index}",
            checkout_group=checkout_group,
            user_id=user.id if user else None,
            seller_id=seller_id,
            payment_id=payment.id if payment else None,
            customer_name=name,
            phone=phone,
            email=email,
            address=address,
            city=city or None,
            delivery_fee=DELIVERY_FEE,
            discount_amount=seller_discount,
            promotion_code=promotion.code if promotion else None,
            total=subtotal + DELIVERY_FEE - seller_discount,
            payment_method=payment_method,
            commission_rate_percent=commission_rate,
            commission_amount=commission,
            return_window_days_snapshot=return_window_days,
            status="pending",
        )
        for row in group_rows:
            order.items.append(OrderItem(
                product_id=row["product"].id,
                variant_id=row.get("variant_id"),
                variant_label=row.get("variant_label"),
                sku_snapshot=row.get("sku_snapshot"),
                product_name=row["product"].name,
                price=row["price"],
                quantity=row["quantity"],
                subtotal=row["subtotal"],
            ))
        db.session.add(order)
        record_order_event(
            order,
            event_type="created",
            new_status="pending",
            actor=user,
            actor_role="customer" if user is not None else "system",
            description=gettext("Order placed."),
            dedupe_key="created",
        )
        orders.append(order)
    if promotion is not None:
        reserved_usage = db.session.execute(
            update(PromotionCode)
            .where(
                PromotionCode.id == promotion.id,
                PromotionCode.is_active.is_(True),
                or_(
                    PromotionCode.usage_limit.is_(None),
                    PromotionCode.used_count < PromotionCode.usage_limit,
                ),
            )
            .values(used_count=PromotionCode.used_count + 1)
            .execution_options(synchronize_session=False)
        )
        if reserved_usage.rowcount != 1:
            raise CheckoutError(gettext("This promotion has reached its usage limit."))
        db.session.add(PromotionRedemption(
            promotion=promotion,
            user_id=user.id if user else None,
            checkout_group=checkout_group,
            discount_amount=promotion_discount,
        ))
    if user is not None:
        db.session.execute(
            delete(CustomerCartItem).where(CustomerCartItem.user_id == user.id)
        )
    db.session.commit()

    if payment_method == "cod":
        for order in orders:
            enqueue_order_emails(order)
            confirmation_link = url_for("orders.confirmation", order_number=order.order_number)
            if order.user_id:
                notify(
                    order.user_id,
                    gettext("Order %(number)s was received.", number=order.order_number),
                    type="order",
                    link=confirmation_link,
                )
            if order.seller_id:
                notify(
                    order.seller_id,
                    gettext("New order %(number)s for your store.", number=order.order_number),
                    type="order",
                    link=url_for("seller.dashboard"),
                )
    return orders
