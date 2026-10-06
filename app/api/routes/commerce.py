"""Session-cart, checkout, customer-order, and seller-order API routes."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, current_app, request, session, url_for
from flask_babel import gettext
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from ...extensions import db
from ...models import Category, Order, Payment, Product, ProductTranslation, ProductVariant
from ...i18n import SUPPORTED_LOCALES
from ...routes.orders import _cart_key, cart_rows, parse_quantity
from ...security import current_session_user
from ...services.audit import record_audit
from ...services.cart import (
    CartError, add_customer_cart_item, clear_customer_cart,
    remove_customer_cart_item, update_customer_cart_item,
)
from ...services.checkout import CheckoutError, create_checkout_orders
from ...services.payments import (
    PaymentError, begin_payment_attempt, cancel_order_with_refund,
    expire_pending_payments, normalize_utc, request_order_return,
)
from ...services.sslcommerz import gateway_is_configured
from ...services.mail import queue_order_status
from ...services.notifications import notify
from ...services.orders import transition_order
from ...services.promotions import (
    PromotionError, allocate_discount_shares, calculate_discount_for_order,
    get_active_promotion,
)
from ..errors import ApiError
from ..responses import created_response, success_response
from ..serializers import order_to_dict, product_to_dict


commerce_api = Blueprint("api_commerce", __name__)


def _customer():
    user = current_session_user()
    if user is None:
        raise ApiError("Sign in as a customer to continue.", "UNAUTHENTICATED", 401)
    if user.role != "customer":
        raise ApiError("This action is only available to customers.", "FORBIDDEN", 403)
    return user


def _seller():
    user = current_session_user()
    if user is None:
        raise ApiError("Sign in as an approved seller to continue.", "UNAUTHENTICATED", 401)
    if (
        user.role != "seller" or not user.seller_profile
        or user.seller_profile.approval_status != "approved"
    ):
        raise ApiError("An approved seller account is required.", "FORBIDDEN", 403)
    return user


def _cart_data():
    rows, subtotal = cart_rows()
    return {
        "items": [
            {
                "key": row["cart_key"],
                "product_id": row["product"].id,
                "variant_id": row["variant_id"],
                "variant_label": row["variant_label"],
                "sku": row["variant"].sku if row["variant"] else None,
                "name": row["product"].name,
                "price": f"{row['price']:.2f}",
                "quantity": row["quantity"],
                "available_stock": row["available_stock"],
                "subtotal": f"{row['subtotal']:.2f}",
            }
            for row in rows
        ],
        "subtotal": f"{subtotal:.2f}",
        "delivery_fee": f"{Decimal('2.50'):.2f}" if rows else "0.00",
        "total": f"{(subtotal + Decimal('2.50')):.2f}" if rows else "0.00",
    }


@commerce_api.get("/cart")
def get_cart():
    _customer()
    return success_response(_cart_data())


@commerce_api.post("/cart/items")
def add_cart_item():
    user = _customer()
    payload = request.get_json(silent=True) or {}
    product_id = payload.get("product_id")
    if isinstance(product_id, bool) or not isinstance(product_id, int):
        raise ApiError("product_id must be an integer.", "VALIDATION_ERROR", 422)
    product = db.session.get(Product, product_id)
    if not product or not product.is_available or not product.category.is_active:
        raise ApiError("Product is unavailable.", "NOT_FOUND", 404)
    variant_id = payload.get("variant_id")
    active_variants = [variant for variant in product.variants if variant.is_active]
    variant = next((item for item in active_variants if item.id == variant_id), None)
    if active_variants and variant is None:
        raise ApiError("Choose an active product variant.", "VALIDATION_ERROR", 422)
    if variant_id is not None and variant is None:
        raise ApiError("Product variant not found.", "NOT_FOUND", 404)
    stock = variant.stock_quantity if variant else product.stock_quantity
    if stock <= 0:
        raise ApiError("Product is out of stock.", "OUT_OF_STOCK", 409)
    quantity = payload.get("quantity", 1)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 20:
        raise ApiError("quantity must be between 1 and 20.", "VALIDATION_ERROR", 422)
    try:
        add_customer_cart_item(
            user.id, product.id, variant.id if variant else None, quantity
        )
    except CartError as error:
        raise ApiError(str(error), "OUT_OF_STOCK", 409) from error
    return created_response(_cart_data(), "Cart item added.")


@commerce_api.patch("/cart/items/<path:cart_key>")
def update_cart_item(cart_key):
    user = _customer()
    payload = request.get_json(silent=True) or {}
    quantity = payload.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 0 <= quantity <= 20:
        raise ApiError("quantity must be between 0 and 20.", "VALIDATION_ERROR", 422)
    try:
        update_customer_cart_item(user.id, cart_key, quantity)
    except CartError as error:
        status = 404 if str(error) == "Cart item not found." else 409
        raise ApiError(str(error), "NOT_FOUND" if status == 404 else "OUT_OF_STOCK", status) from error
    return success_response(_cart_data())


@commerce_api.delete("/cart/items/<path:cart_key>")
def remove_cart_item(cart_key):
    user = _customer()
    if not remove_customer_cart_item(user.id, cart_key):
        raise ApiError("Cart item not found.", "NOT_FOUND", 404)
    return success_response(_cart_data(), "Cart item removed.")


@commerce_api.delete("/cart")
def clear_cart():
    user = _customer()
    clear_customer_cart(user.id)
    session["cart"] = {}
    return success_response(_cart_data(), "Cart cleared.")


@commerce_api.post("/checkout/preview")
def checkout_preview():
    _customer()
    rows, _subtotal = cart_rows()
    if not rows:
        raise ApiError("Your cart is empty.", "EMPTY_CART", 409)
    payload = request.get_json(silent=True) or {}
    groups = {}
    for row in rows:
        group = groups.setdefault(row["seller_id"], {"items": [], "subtotal": Decimal("0.00")})
        group["items"].append({
            "product_id": row["product"].id,
            "variant_id": row["variant_id"],
            "name": row["product"].name,
            "variant_label": row["variant_label"],
            "quantity": row["quantity"],
            "unit_price": f"{row['price']:.2f}",
            "subtotal": f"{row['subtotal']:.2f}",
        })
        group["subtotal"] += row["subtotal"]
    promotion_code = str(payload.get("promotion_code", "")).strip().upper()
    promotion_discount = Decimal("0.00")
    eligible_subtotals = {seller_id: group["subtotal"] for seller_id, group in groups.items()}
    if promotion_code:
        try:
            promotion = get_active_promotion(promotion_code)
            if promotion.seller_id is not None:
                eligible_subtotals = {
                    seller_id: subtotal for seller_id, subtotal in eligible_subtotals.items()
                    if seller_id == promotion.seller_id
                }
            eligible_subtotal = sum(eligible_subtotals.values(), Decimal("0.00"))
            promotion_discount = calculate_discount_for_order(
                eligible_subtotal, promotion_code,
                seller_id=promotion.seller_id, promotion=promotion,
            )
        except PromotionError as error:
            raise ApiError(str(error), "PROMOTION_REJECTED", 422) from error
    discount_shares = allocate_discount_shares(promotion_discount, eligible_subtotals)
    return success_response({
        "orders": [
            {
                "seller_id": seller_id,
                "items": group["items"],
                "subtotal": f"{group['subtotal']:.2f}",
                "delivery_fee": "2.50",
                "promotion_code": promotion_code or None,
                "discount_amount": f"{discount_shares.get(seller_id, Decimal('0.00')):.2f}",
                "total": f"{group['subtotal'] + Decimal('2.50') - discount_shares.get(seller_id, Decimal('0.00')):.2f}",
            }
            for seller_id, group in groups.items()
        ],
        "promotion_code": promotion_code or None,
        "promotion_discount": f"{promotion_discount:.2f}",
        "total": f"{sum((group['subtotal'] for group in groups.values()), Decimal('0.00')) + Decimal('2.50') * len(groups) - promotion_discount:.2f}",
    })


@commerce_api.post("/checkout")
def checkout():
    user = _customer()
    rows, _subtotal = cart_rows()
    payload = request.get_json(silent=True) or {}
    payment_method = str(payload.get("payment_method", "")).strip().lower()
    if payment_method == "sslcommerz":
        from ...models import AppSetting

        setting = db.session.get(AppSetting, 1)
        if not gateway_is_configured():
            raise ApiError("Online payment is not configured.", "PAYMENT_UNAVAILABLE", 503)
        if (
            current_app.config.get("ENVIRONMENT") == "production"
            and (not setting or setting.commission_rate_percent is None)
        ):
            raise ApiError(
                "Online payment is unavailable until marketplace commission is configured.",
                "PAYMENT_UNAVAILABLE",
                503,
            )
    try:
        orders = create_checkout_orders(
            user,
            rows,
            name=str(payload.get("customer_name", "")).strip(),
            phone=str(payload.get("phone", "")).strip(),
            address=str(payload.get("address", "")).strip(),
            city=str(payload.get("city", "")).strip(),
            email=user.email,
            payment_method=payment_method,
            promotion_code=str(payload.get("promotion_code", "")).strip().upper() or None,
        )
    except CheckoutError as error:
        db.session.rollback()
        status = 409 if "stock" in str(error).lower() or "cart" in str(error).lower() else 422
        raise ApiError(str(error), "CHECKOUT_REJECTED", status) from error
    session["cart"] = {}
    if payment_method == "sslcommerz":
        payment = db.session.get(Payment, orders[0].payment_id)
        try:
            gateway_url = begin_payment_attempt(payment)
        except PaymentError:
            gateway_url = None
        return created_response(
            {
                "orders": [order_to_dict(order) for order in orders],
                "checkout_group": payment.checkout_group,
                "payment_status": payment.status,
                "checkout_url": gateway_url,
                "payment_status_url": f"/api/v1/payments/{payment.checkout_group}",
            },
            "Order created. Complete online payment to confirm it.",
        )
    return created_response(
        {"orders": [order_to_dict(order) for order in orders]},
        "Order placed.",
    )


@commerce_api.get("/payments/<checkout_group>")
def customer_payment_status(checkout_group):
    user = _customer()
    expire_pending_payments()
    payment = db.session.scalar(
        select(Payment)
        .options(selectinload(Payment.attempts))
        .where(Payment.checkout_group == checkout_group, Payment.user_id == user.id)
    )
    if payment is None:
        raise ApiError("Payment not found.", "NOT_FOUND", 404)
    latest = payment.attempts[-1] if payment.attempts else None
    can_retry = bool(
        payment.status == "pending"
        and (latest is None or latest.status in {"failed", "cancelled", "expired"})
        and normalize_utc(payment.expires_at) > datetime.now(timezone.utc)
        and gateway_is_configured()
    )
    return success_response({
        "checkout_group": payment.checkout_group,
        "amount": f"{payment.amount:.2f}",
        "currency": payment.currency,
        "status": payment.status,
        "expires_at": payment.expires_at.isoformat(),
        "can_retry": can_retry,
    })


@commerce_api.post("/payments/<checkout_group>/retry")
def retry_customer_payment(checkout_group):
    user = _customer()
    payment = db.session.scalar(
        select(Payment).where(Payment.checkout_group == checkout_group, Payment.user_id == user.id)
    )
    if payment is None:
        raise ApiError("Payment not found.", "NOT_FOUND", 404)
    try:
        gateway_url = begin_payment_attempt(payment)
    except PaymentError as error:
        raise ApiError(str(error), "PAYMENT_RETRY_REJECTED", 409) from error
    return success_response({"checkout_url": gateway_url}, "Continue to the payment provider.")


@commerce_api.get("/orders")
def customer_orders():
    user = _customer()
    orders = db.session.scalars(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.return_request),
            selectinload(Order.payment).selectinload(Payment.refunds),
        )
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(100)
    ).all()
    return success_response([order_to_dict(order) for order in orders])


@commerce_api.get("/orders/<order_number>")
def customer_order_detail(order_number):
    user = _customer()
    order = db.session.scalar(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.return_request),
            selectinload(Order.payment).selectinload(Payment.refunds),
        )
        .where(Order.order_number == order_number, Order.user_id == user.id)
    )
    if order is None:
        raise ApiError("Order not found.", "NOT_FOUND", 404)
    return success_response(order_to_dict(order))


@commerce_api.post("/orders/<order_number>/return")
def customer_order_return(order_number):
    user = _customer()
    order = db.session.scalar(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.return_request),
            selectinload(Order.payment).selectinload(Payment.refunds),
        )
        .where(Order.order_number == order_number, Order.user_id == user.id)
        .with_for_update()
    )
    if order is None:
        raise ApiError("Order not found.", "NOT_FOUND", 404)
    payload = request.get_json(silent=True) or {}
    reason = payload.get("reason", "") if isinstance(payload, dict) else None
    if not isinstance(reason, str) or len(reason) > 255:
        raise ApiError(
            "Return request must include a text reason no longer than 255 characters.",
            "INVALID_INPUT",
            422,
        )
    try:
        request_order_return(order, actor=user, reason=reason)
    except PaymentError as error:
        raise ApiError(str(error), "RETURN_REQUEST_INVALID", 409) from error
    return success_response(order_to_dict(order), "Return request submitted.")


@commerce_api.post("/orders/<order_number>/cancel")
def cancel_customer_order(order_number):
    user = _customer()
    order = db.session.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number, Order.user_id == user.id)
        .with_for_update()
    )
    if order is None:
        raise ApiError("Order not found.", "NOT_FOUND", 404)
    if order.status not in {"pending", "confirmed"}:
        raise ApiError("This order can no longer be cancelled.", "INVALID_TRANSITION", 409)
    try:
        cancel_order_with_refund(order, actor=user, reason="Customer cancelled before shipment")
    except PaymentError as error:
        db.session.rollback()
        raise ApiError(str(error), "CANCELLATION_REJECTED", 409) from error
    db.session.commit()
    record_audit("order.cancel", actor=user, target_type="order", target_id=order.id)
    queue_order_status(order)
    return success_response(order_to_dict(order), "Order cancelled.")


@commerce_api.get("/seller/orders")
def seller_orders():
    user = _seller()
    orders = db.session.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.seller_id == user.id,
            or_(
                Order.payment_method == "cod",
                Order.payment.has(Payment.status.in_({"paid", "partially_refunded"})),
            ),
        )
        .order_by(Order.created_at.desc())
        .limit(100)
    ).all()
    return success_response([order_to_dict(order) for order in orders])


@commerce_api.get("/seller/dashboard")
def seller_dashboard():
    user = _seller()
    return success_response({
        "products": db.session.scalar(
            select(func.count(Product.id)).where(Product.seller_id == user.id)
        ) or 0,
        "active_products": db.session.scalar(
            select(func.count(Product.id)).where(
                Product.seller_id == user.id, Product.is_available.is_(True)
            )
        ) or 0,
        "pending_orders": db.session.scalar(
            select(func.count(Order.id)).where(
                Order.seller_id == user.id,
                Order.status == "pending",
                or_(
                    Order.payment_method == "cod",
                    Order.payment.has(Payment.status.in_({"paid", "partially_refunded"})),
                ),
            )
        ) or 0,
        "completed_orders": db.session.scalar(
            select(func.count(Order.id)).where(
                Order.seller_id == user.id, Order.status == "delivered"
            )
        ) or 0,
        "sales": f"{db.session.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.seller_id == user.id, Order.status == "delivered"
            )
        ) or Decimal('0.00'):.2f}",
    })


@commerce_api.get("/seller/products")
def seller_products():
    user = _seller()
    products = db.session.scalars(
        select(Product)
        .options(selectinload(Product.variants), selectinload(Product.translations))
        .where(Product.seller_id == user.id)
        .order_by(Product.updated_at.desc(), Product.id.desc())
        .limit(100)
    ).all()
    return success_response([product_to_dict(product) for product in products])


def _seller_product_payload(payload, product=None):
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    slug = str(payload.get("slug", "")).strip() or re.sub(
        r"[^a-z0-9-]+", "-", name.lower()
    ).strip("-")
    category_id = payload.get("category_id")
    locale = payload.get("original_locale", "en_US")
    if not 2 <= len(name) <= 160 or not description or len(description) > 10000:
        raise ApiError("Enter a product name and description within the allowed length.", "VALIDATION_ERROR", 422)
    if locale not in SUPPORTED_LOCALES:
        raise ApiError("Choose a supported source language.", "VALIDATION_ERROR", 422)
    if isinstance(category_id, bool) or not isinstance(category_id, int):
        raise ApiError("category_id must be an integer.", "VALIDATION_ERROR", 422)
    category = db.session.get(Category, category_id)
    if not category or not category.is_active:
        raise ApiError("Choose an active category.", "VALIDATION_ERROR", 422)
    try:
        price = Decimal(str(payload.get("price", "")))
        discount = (
            Decimal(str(payload["discount_price"]))
            if payload.get("discount_price") not in (None, "") else None
        )
        stock = int(payload.get("stock_quantity", 0))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ApiError("Enter valid price and stock values.", "VALIDATION_ERROR", 422) from error
    if (
        not price.is_finite() or price < 0 or price > Decimal("99999999.99")
        or price != price.quantize(Decimal("0.01"))
        or (discount is not None and (
            not discount.is_finite() or discount < 0 or discount >= price
            or discount != discount.quantize(Decimal("0.01"))
        ))
    ):
        raise ApiError("Enter a valid price and lower optional discount price.", "VALIDATION_ERROR", 422)
    if not 0 <= stock <= 2_147_483_647:
        raise ApiError("Stock must be a non-negative whole number.", "VALIDATION_ERROR", 422)
    duplicate = db.session.scalar(
        select(Product.id).where(Product.slug == slug, Product.id != (product.id if product else -1))
    )
    if not slug or len(slug) > 180 or duplicate:
        raise ApiError("That product URL is invalid or already in use.", "CONFLICT", 409)
    return {
        "name": name,
        "description": description,
        "slug": slug,
        "category_id": category.id,
        "original_locale": locale,
        "price": price,
        "discount_price": discount,
        "stock_quantity": stock,
    }


def _apply_translations(product, payload):
    translations = payload.get("translations", {})
    if not isinstance(translations, dict):
        raise ApiError("translations must be an object keyed by locale.", "VALIDATION_ERROR", 422)
    existing = {translation.locale: translation for translation in product.translations}
    for locale, values in translations.items():
        if locale not in SUPPORTED_LOCALES or locale == product.original_locale or not isinstance(values, dict):
            raise ApiError("A translation has an unsupported locale or shape.", "VALIDATION_ERROR", 422)
        translated_name = str(values.get("name", "")).strip()
        translated_description = str(values.get("description", "")).strip()
        if not translated_name or len(translated_name) > 160 or len(translated_description) > 10000:
            raise ApiError("Translated name and description are invalid.", "VALIDATION_ERROR", 422)
        translation = existing.pop(locale, None)
        if translation:
            translation.name = translated_name
            translation.description = translated_description
        else:
            product.translations.append(ProductTranslation(
                locale=locale, name=translated_name, description=translated_description
            ))
    for stale in existing.values():
        product.translations.remove(stale)


@commerce_api.post("/seller/products")
def create_seller_product():
    user = _seller()
    payload = request.get_json(silent=True) or {}
    fields = _seller_product_payload(payload)
    product = Product(
        seller_id=user.id,
        **fields,
        moderation_status="pending",
        is_available=False,
        is_featured=False,
    )
    _apply_translations(product, payload)
    db.session.add(product)
    db.session.commit()
    return created_response(product_to_dict(product), "Product submitted for Admin review.")


@commerce_api.patch("/seller/products/<int:product_id>")
def update_seller_product(product_id):
    user = _seller()
    product = db.session.scalar(
        select(Product)
        .options(selectinload(Product.translations), selectinload(Product.variants))
        .where(Product.id == product_id, Product.seller_id == user.id)
    )
    if product is None:
        raise ApiError("Product not found.", "NOT_FOUND", 404)
    payload = request.get_json(silent=True) or {}
    fields = _seller_product_payload(payload, product)
    for key, value in fields.items():
        setattr(product, key, value)
    product.moderation_status = "pending"
    product.moderation_note = None
    product.reviewed_at = None
    product.reviewed_by_id = None
    product.is_available = False
    _apply_translations(product, payload)
    db.session.commit()
    return success_response(product_to_dict(product), "Updated product submitted for Admin review.")


@commerce_api.delete("/seller/products/<int:product_id>")
def deactivate_seller_product(product_id):
    user = _seller()
    product = db.session.scalar(
        select(Product).where(Product.id == product_id, Product.seller_id == user.id)
    )
    if product is None:
        raise ApiError("Product not found.", "NOT_FOUND", 404)
    product.is_available = False
    product.moderation_status = "suspended"
    db.session.commit()
    return success_response({"id": product.id, "is_available": False}, "Product deactivated.")


@commerce_api.patch("/seller/orders/<int:order_id>")
def update_seller_order(order_id):
    user = _seller()
    order = db.session.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.seller_id == user.id)
    )
    if order is None:
        raise ApiError("Order not found.", "NOT_FOUND", 404)
    payload = request.get_json(silent=True) or {}
    target = payload.get("status")
    if target not in {"confirmed", "preparing", "declined"}:
        raise ApiError("That order status transition is not allowed.", "INVALID_TRANSITION", 409)
    if target == "declined":
        try:
            cancel_order_with_refund(
                order, actor=user, reason="Seller declined the unshipped order",
                final_order_status="declined",
            )
        except PaymentError as error:
            db.session.rollback()
            raise ApiError(str(error), "ORDER_DECLINE_REJECTED", 409) from error
    elif not transition_order(order, target):
        raise ApiError("That order status transition is not allowed.", "INVALID_TRANSITION", 409)
    db.session.commit()
    record_audit("order.status", actor=user, target_type="order", target_id=order.id, detail=target)
    queue_order_status(order)
    if order.user_id:
        notify(
            order.user_id,
            gettext("Order %(number)s is now %(status)s.", number=order.order_number, status=target),
            type="order",
            link=url_for("orders.confirmation", order_number=order.order_number),
        )
    return success_response(order_to_dict(order), "Order status updated.")
