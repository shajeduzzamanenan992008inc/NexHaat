from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_babel import gettext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..extensions import csrf, db
from ..models import (
    AppSetting, Category, CustomerAddress, CustomerProfile, Order, OrderReturn, Payment,
    PaymentAttempt, PaymentRefund, Product, PromotionCode, Review, SellerProfile, SellerPayout, User,
)
from ..security import (
    admin_required, customer_or_guest_required, current_session_user,
    is_primary_admin, primary_admin_required, save_raster_upload,
)
from ..services.audit import record_audit
from ..services.mail import (
    enqueue_order_emails,
    queue_order_receipt,
    queue_order_status,
)
from ..services.notifications import notify
from ..services.orders import release_reserved_stock, transition_order
from ..services.checkout import CheckoutError, DELIVERY_FEE, create_checkout_orders
from ..services.promotions import (
    PromotionError, calculate_discount_for_order, get_active_promotion,
    promotion_values_from_form,
)
from ..services.payments import (
    PaymentError, approve_payment_review, begin_payment_attempt, cancel_order_with_refund,
    expire_pending_payments, initiate_order_refund, process_failed_callback, process_ipn,
    mark_order_return_received, record_manual_return_refund, record_seller_payout,
    refresh_refund_status, request_order_return, review_order_return,
    issue_order_return_refund, seller_settlement_balance, normalize_utc,
)
from ..services.sslcommerz import gateway_is_configured


orders_bp = Blueprint("orders", __name__)
STATUSES = ("pending", "confirmed", "preparing", "delivered", "cancelled", "declined")


def parse_quantity(value, default=1):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(quantity, 20))


def _cart_key(product_id, variant_id=None):
    return f"{product_id}:{variant_id}" if variant_id else str(product_id)


def _parse_cart_key(value):
    try:
        product_part, separator, variant_part = str(value).partition(":")
        product_id = int(product_part)
        variant_id = int(variant_part) if separator else None
    except (TypeError, ValueError):
        return None, None
    return product_id, variant_id


def cart_rows():
    raw_cart = session.get("cart", {})
    parsed_rows = [(_parse_cart_key(key), key, quantity) for key, quantity in raw_cart.items()]
    product_ids = {parsed[0] for parsed, _key, _quantity in parsed_rows if parsed[0] is not None}
    products = db.session.scalars(
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.variants))
        .where(Product.id.in_(product_ids))
    ).all() if product_ids else []
    product_by_id = {product.id: product for product in products}
    rows, total = [], Decimal("0.00")
    valid_cart = {}
    for (product_id, variant_id), _old_key, raw_quantity in parsed_rows:
        product = product_by_id.get(product_id)
        if product is None:
            continue
        if not product.is_available or not product.category.is_active:
            continue
        active_variants = [variant for variant in product.variants if variant.is_active]
        variant = next(
            (item for item in active_variants if item.id == variant_id), None
        ) if variant_id else None
        if variant_id and variant is None:
            continue
        if not variant and active_variants:
            if len(active_variants) != 1:
                continue
            variant = active_variants[0]
        available_stock = variant.stock_quantity if variant else product.stock_quantity
        if available_stock <= 0:
            continue
        quantity = parse_quantity(raw_quantity)
        price = variant.price if variant and variant.price is not None else product.display_price
        subtotal = price * quantity
        key = _cart_key(product.id, variant.id if variant else None)
        rows.append({
            "product": product,
            "variant": variant,
            "variant_id": variant.id if variant else None,
            "variant_label": f"{variant.option_name}: {variant.option_value}" if variant else None,
            "cart_key": key,
            "price": price,
            "available_stock": available_stock,
            "quantity": quantity,
            "subtotal": subtotal,
            "seller_id": product.seller_id,
        })
        total += subtotal
        valid_cart[key] = quantity
    session["cart"] = valid_cart
    return rows, total


@orders_bp.get("/cart")
@customer_or_guest_required
def cart():
    rows, subtotal = cart_rows()
    return render_template("orders/cart.html", rows=rows, subtotal=subtotal, delivery=DELIVERY_FEE, total=subtotal + DELIVERY_FEE if rows else Decimal("0.00"))


@orders_bp.post("/cart/add/<int:product_id>")
@customer_or_guest_required
def add_to_cart(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.is_available or not product.category.is_active:
        abort(404)
    active_variants = [variant for variant in product.variants if variant.is_active]
    variant_id = request.form.get("variant_id", type=int)
    variant = next((item for item in active_variants if item.id == variant_id), None)
    if active_variants and variant is None:
        flash(gettext("Choose a product option before adding it to your cart."), "error")
        return redirect(url_for("main.food", slug=product.slug))
    stock = variant.stock_quantity if variant else product.stock_quantity
    if stock <= 0:
        flash(gettext("This item is out of stock."), "error")
        return redirect(url_for("main.food", slug=product.slug))
    cart = session.get("cart", {})
    key = _cart_key(product_id, variant.id if variant else None)
    cart[key] = min(
        parse_quantity(cart.get(key), default=0) + parse_quantity(request.form.get("quantity")),
        stock,
        20,
    )
    session["cart"] = cart
    flash(f"{product.name} added to your cart.", "success")
    next_url = request.form.get("next", "")
    parsed_next = urlsplit(next_url)
    safe_next = bool(
        next_url.startswith("/")
        and not next_url.startswith("//")
        and not parsed_next.scheme
        and not parsed_next.netloc
        and "\\" not in next_url
    )
    return redirect(next_url if safe_next else url_for("orders.cart"))


@orders_bp.post("/cart/update")
@customer_or_guest_required
def update_cart():
    cart = session.get("cart", {})
    for key, value in request.form.items():
        if key.startswith("quantity_"):
            cart_key = key.removeprefix("quantity_")
            try:
                quantity = int(value)
            except (TypeError, ValueError):
                quantity = 0
            if quantity > 0:
                cart[cart_key] = min(quantity, 20)
            else:
                cart.pop(cart_key, None)
    session["cart"] = cart
    cart_rows()
    return redirect(url_for("orders.cart"))


@orders_bp.post("/cart/remove/<int:product_id>")
@customer_or_guest_required
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    variant_id = request.form.get("variant_id", type=int)
    cart.pop(_cart_key(product_id, variant_id), None)
    session["cart"] = cart
    return redirect(url_for("orders.cart"))


@orders_bp.route("/checkout", methods=["GET", "POST"])
@customer_or_guest_required
def checkout():
    rows, subtotal = cart_rows()
    if not rows:
        flash("Your cart is empty.", "error")
        return redirect(url_for("orders.cart"))
    promotion_code = (request.form.get("promotion_code", request.args.get("promotion_code", "")) or "").strip().upper()
    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        user = current_session_user("customer")
        email = user.email if user else request.form.get("email", "").strip() or None
        payment_method = request.form.get("payment_method", "").strip().lower()
        city = request.form.get("city", "").strip()
        promotion_code = (request.form.get("promotion_code", "") or "").strip().upper()
        if payment_method == "sslcommerz":
            setting = db.session.get(AppSetting, 1)
            if not gateway_is_configured():
                flash(gettext("Online payment is not configured yet. Please choose cash on delivery."), "error")
                return redirect(url_for("orders.checkout"))
            if (
                current_app.config.get("ENVIRONMENT") == "production"
                and (not setting or setting.commission_rate_percent is None)
            ):
                flash(gettext("Online payments are unavailable until the marketplace commission is configured."), "error")
                return redirect(url_for("orders.checkout"))
        try:
            orders = create_checkout_orders(
                user,
                rows,
                name=name,
                phone=phone,
                address=address,
                email=email,
                payment_method=payment_method,
                city=city,
                promotion_code=promotion_code,
            )
        except CheckoutError as error:
            db.session.rollback()
            flash(gettext(str(error)), "error")
        else:
            session["cart"] = {}
            if user is None:
                session["guest_checkout_group"] = orders[0].checkout_group
            if payment_method == "sslcommerz":
                payment = db.session.get(Payment, orders[0].payment_id)
                try:
                    gateway_url = begin_payment_attempt(payment)
                except PaymentError as error:
                    flash(gettext(str(error)), "error")
                    return redirect(
                        url_for("orders.payment_status", checkout_group=payment.checkout_group)
                    )
                return redirect(gateway_url)
            return redirect(url_for("orders.confirmation", order_number=orders[0].order_number))
    customer = None
    user_email = None
    if session.get("user_id"):
        signed_in_user = db.session.get(User, session["user_id"])
        customer = signed_in_user.customer_profile
        user_email = signed_in_user.email
    setting = db.session.get(AppSetting, 1)
    online_payment_available = gateway_is_configured() and (
        current_app.config.get("ENVIRONMENT") != "production"
        or (setting is not None and setting.commission_rate_percent is not None)
    )
    delivery_total = DELIVERY_FEE * len({row["seller_id"] for row in rows})
    promotion_discount = Decimal("0.00")
    if promotion_code:
        try:
            promotion = get_active_promotion(promotion_code)
            eligible_total = sum(
                (row["subtotal"] for row in rows if promotion.seller_id is None or row["seller_id"] == promotion.seller_id),
                Decimal("0.00"),
            )
            promotion_discount = calculate_discount_for_order(
                eligible_total, promotion_code, seller_id=promotion.seller_id, promotion=promotion
            )
        except PromotionError as error:
            flash(gettext(str(error)), "error")
    return render_template(
        "orders/checkout.html", rows=rows, subtotal=subtotal, delivery=delivery_total,
        total=subtotal + delivery_total - promotion_discount, promotion_discount=promotion_discount,
        customer=customer, user_email=user_email,
        online_payment_available=online_payment_available,
        promotion_code=promotion_code,
    )


def _payment_for_current_customer(checkout_group):
    payment = db.session.scalar(
        select(Payment)
        .options(selectinload(Payment.attempts), selectinload(Payment.refunds))
        .where(Payment.checkout_group == checkout_group)
    )
    if payment is None:
        abort(404)
    user = current_session_user("customer")
    if payment.user_id is not None:
        if user is None or user.id != payment.user_id:
            abort(404)
    elif session.get("guest_checkout_group") != payment.checkout_group:
        abort(404)
    return payment


@orders_bp.get("/payments/<checkout_group>")
def payment_status(checkout_group):
    expire_pending_payments()
    payment = _payment_for_current_customer(checkout_group)
    orders = db.session.scalars(
        select(Order).options(selectinload(Order.items), selectinload(Order.return_request))
        .where(Order.payment_id == payment.id).order_by(Order.order_number)
    ).all()
    latest_attempt = payment.attempts[-1] if payment.attempts else None
    can_retry = bool(
        payment.status == "pending"
        and (latest_attempt is None or latest_attempt.status in {"failed", "cancelled", "expired"})
        and normalize_utc(payment.expires_at) > datetime.now(timezone.utc)
        and gateway_is_configured()
    )
    return render_template(
        "orders/payment_status.html", payment=payment, orders=orders,
        latest_attempt=latest_attempt, can_retry=can_retry,
    )


@orders_bp.post("/payments/<checkout_group>/retry")
def payment_retry(checkout_group):
    payment = _payment_for_current_customer(checkout_group)
    try:
        gateway_url = begin_payment_attempt(payment)
    except PaymentError as error:
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.payment_status", checkout_group=checkout_group))
    return redirect(gateway_url)


@orders_bp.route("/payments/sslcommerz/success", methods=["GET", "POST"])
@csrf.exempt
def sslcommerz_success():
    process_ipn(request.form if request.method == "POST" else request.args)
    transaction_id = str(request.values.get("tran_id", "")).strip()
    attempt = db.session.scalar(
        select(PaymentAttempt).where(PaymentAttempt.transaction_id == transaction_id)
    )
    if not attempt:
        abort(404)
    return redirect(url_for("orders.payment_status", checkout_group=attempt.payment.checkout_group))


@orders_bp.route("/payments/sslcommerz/return", methods=["GET", "POST"])
@csrf.exempt
def sslcommerz_return():
    process_failed_callback(request.form if request.method == "POST" else request.args)
    transaction_id = str(request.values.get("tran_id", "")).strip()
    attempt = db.session.scalar(
        select(PaymentAttempt).where(PaymentAttempt.transaction_id == transaction_id)
    )
    if not attempt:
        abort(404)
    return redirect(url_for("orders.payment_status", checkout_group=attempt.payment.checkout_group))


@orders_bp.post("/payments/sslcommerz/ipn")
@csrf.exempt
def sslcommerz_ipn():
    if process_ipn(request.form):
        return "OK", 200
    if process_failed_callback(request.form):
        return "OK", 200
    return "Notification not validated.", 400


@orders_bp.get("/orders/<order_number>")
def confirmation(order_number):
    order = db.session.scalar(select(Order).where(Order.order_number == order_number))
    if not order:
        abort(404)
    if order.user_id is not None:
        if order.user_id != session.get("user_id"):
            abort(404)
    elif (
        session.get("user_id") is not None
        or session.get("guest_checkout_group") != order.checkout_group
    ):
        abort(404)
    sub_orders = [order]
    if order.checkout_group:
        sub_orders = db.session.scalars(
            select(Order).options(selectinload(Order.items))
            .where(Order.checkout_group == order.checkout_group)
            .order_by(Order.order_number)
        ).all()
    grand_total = sum((item.total for item in sub_orders), Decimal("0.00"))
    return render_template(
        "orders/confirmation.html",
        order=order, sub_orders=sub_orders, grand_total=grand_total,
    )


@orders_bp.get("/my-orders")
def my_orders():
    user = current_session_user("customer")
    if not user:
        if session.get("user_id") is not None:
            abort(403)
        return redirect(url_for("auth.login", next=url_for("orders.my_orders")))
    orders = db.session.scalars(
        select(Order).options(
            selectinload(Order.items),
            selectinload(Order.return_request),
            selectinload(Order.payment).selectinload(Payment.refunds),
        )
        .where(Order.user_id == user.id).order_by(Order.created_at.desc())
    ).all()
    return render_template("orders/my_orders.html", orders=orders)


@orders_bp.post("/orders/<order_number>/cancel")
def customer_order_cancel(order_number):
    user = current_session_user("customer")
    if not user:
        if session.get("user_id") is not None:
            abort(403)
        return redirect(url_for("auth.login", next=url_for("orders.my_orders")))
    order = db.session.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number, Order.user_id == user.id)
        .with_for_update()
    )
    if not order:
        abort(404)
    if order.status not in {"pending", "confirmed"}:
        flash(gettext("This order can no longer be cancelled."), "error")
        return redirect(url_for("orders.my_orders"))
    try:
        cancel_order_with_refund(order, actor=user, reason="Customer cancelled before shipment")
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.my_orders"))
    db.session.commit()
    record_audit("order.cancel", actor=user, target_type="order", target_id=order.id)
    queue_order_status(order)
    if order.seller_id:
        notify(
            order.seller_id,
            gettext("Order %(number)s was cancelled by the customer.", number=order.order_number),
            type="order",
            link=url_for("seller.orders"),
        )
    flash(gettext("Your order was cancelled."), "success")
    return redirect(url_for("orders.my_orders"))


@orders_bp.post("/orders/<order_number>/return")
def customer_order_return(order_number):
    user = current_session_user("customer")
    if not user:
        if session.get("user_id") is not None:
            abort(403)
        return redirect(url_for("auth.login", next=url_for("orders.my_orders")))
    order = db.session.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number, Order.user_id == user.id)
        .with_for_update()
    )
    if not order:
        abort(404)
    if order.status != "delivered":
        flash(gettext("Only delivered orders can be returned."), "error")
        return redirect(url_for("orders.my_orders"))
    try:
        request_order_return(
            order,
            actor=user,
            reason=request.form.get("reason", "").strip() or "Customer return request",
        )
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.my_orders"))
    flash(gettext("Your return request was submitted for review."), "success")
    return redirect(url_for("orders.my_orders"))


@orders_bp.post("/admin/orders/<int:return_id>/return-review")
@admin_required
def admin_review_order_return(return_id):
    return_request = db.session.get(OrderReturn, return_id)
    if return_request is None:
        abort(404)
    decision = request.form.get("decision", "").strip().lower()
    if decision not in {"approved", "rejected"}:
        abort(400)
    try:
        review_order_return(
            return_request,
            decision=decision,
            actor=current_session_user(),
            note=request.form.get("note", "").strip(),
        )
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash(
        gettext("Return request approved.") if decision == "approved" else gettext("Return request rejected."),
        "success",
    )
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/orders/<int:return_id>/return-received")
@admin_required
def admin_return_received(return_id):
    return_request = db.session.get(OrderReturn, return_id)
    if return_request is None:
        abort(404)
    try:
        mark_order_return_received(return_request, actor=current_session_user())
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash(gettext("Returned items marked as received."), "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/orders/<int:return_id>/return-refund")
@admin_required
def admin_return_refund(return_id):
    return_request = db.session.get(OrderReturn, return_id)
    if return_request is None:
        abort(404)
    try:
        issue_order_return_refund(return_request, actor=current_session_user())
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash(gettext("Return refund request sent to the payment provider."), "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/orders/<int:return_id>/manual-return-refund")
@admin_required
def admin_manual_return_refund(return_id):
    return_request = db.session.get(OrderReturn, return_id)
    if return_request is None:
        abort(404)
    try:
        record_manual_return_refund(
            return_request,
            actor=current_session_user(),
            reference=request.form.get("reference", ""),
        )
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash(gettext("Manual return refund recorded."), "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/sellers/<int:profile_id>/review")
@admin_required
def admin_review_seller(profile_id):
    profile = db.session.get(SellerProfile, profile_id)
    if not profile:
        abort(404)
    if profile.approval_status != "pending":
        flash(gettext("This seller application has already been reviewed."), "error")
        return redirect(url_for("admin.dashboard"))
    decision = request.form.get("decision", "")
    if decision not in {"approved", "rejected"}:
        abort(400)
    note = request.form.get("review_note", "").strip()
    if len(note) > 500:
        flash(gettext("The review note must be 500 characters or fewer."), "error")
        return redirect(url_for("admin.dashboard"))
    profile.approval_status = decision
    profile.reviewed_at = datetime.now(timezone.utc)
    profile.reviewed_by_id = session["user_id"]
    profile.review_note = note or None
    db.session.commit()
    record_audit("seller.review", target_type="seller_profile", target_id=profile_id, detail=decision)
    if decision == "approved":
        notify(
            profile.user_id,
            gettext("Your store was approved. You can now publish products."),
            type="account",
            link=url_for("seller.dashboard"),
        )
    flash(
        gettext("Seller application approved.") if decision == "approved"
        else gettext("Seller application rejected."),
        "success",
    )
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/products/<int:product_id>/review")
@admin_required
def admin_review_product(product_id):
    product = db.session.get(Product, product_id)
    if not product or product.seller_id is None or product.moderation_status != "pending":
        abort(404)
    decision = request.form.get("decision", "")
    if decision not in {"approved", "rejected"}:
        abort(400)
    note = request.form.get("review_note", "").strip()
    if len(note) > 500:
        flash(gettext("The review note must be 500 characters or fewer."), "error")
        return redirect(url_for("admin.dashboard"))
    product.moderation_status = decision
    product.is_available = decision == "approved"
    product.moderation_note = note or None
    product.reviewed_at = datetime.now(timezone.utc)
    product.reviewed_by_id = session["user_id"]
    db.session.commit()
    record_audit("catalog.product_review", target_type="product", target_id=product_id, detail=decision)
    flash(
        gettext("Product listing approved.") if decision == "approved"
        else gettext("Product listing rejected."),
        "success",
    )
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/reviews/<int:review_id>/moderate")
@admin_required
def admin_moderate_review(review_id):
    review = db.session.get(Review, review_id)
    if not review or review.status != "pending":
        abort(404)
    decision = request.form.get("decision", "")
    if decision not in {"approved", "rejected"}:
        abort(400)
    note = request.form.get("review_note", "").strip()
    if len(note) > 500:
        flash(gettext("The review note must be 500 characters or fewer."), "error")
        return redirect(url_for("admin.dashboard"))
    review.status = decision
    review.moderation_note = note or None
    review.moderated_at = datetime.now(timezone.utc)
    review.moderated_by_id = session["user_id"]
    db.session.commit()
    record_audit("review.moderate", target_type="review", target_id=review_id, detail=decision)
    flash(
        gettext("Review approved.") if decision == "approved" else gettext("Review rejected."),
        "success",
    )
    return redirect(url_for("admin.dashboard"))


@orders_bp.route("/admin/promotions", methods=["GET", "POST"])
@admin_required
def admin_promotions():
    if request.method == "POST":
        seller_id = request.form.get("seller_id", type=int)
        if seller_id is not None:
            eligible_seller = db.session.scalar(
                select(SellerProfile).where(
                    SellerProfile.user_id == seller_id,
                    SellerProfile.approval_status == "approved",
                )
            )
            if eligible_seller is None:
                flash(gettext("Choose an approved seller for a seller deal."), "error")
                return redirect(url_for("orders.admin_promotions"))
        try:
            campaign = PromotionCode(**promotion_values_from_form(request.form, seller_id=seller_id))
            db.session.add(campaign)
            db.session.commit()
        except (PromotionError, ValueError, IntegrityError) as error:
            db.session.rollback()
            flash(gettext(str(error)) if not isinstance(error, IntegrityError) else gettext("That promotion code is already in use."), "error")
            return redirect(url_for("orders.admin_promotions"))
        record_audit(
            "promotion.create", target_type="promotion", target_id=campaign.id,
            detail=campaign.code,
        )
        flash(gettext("Promotion campaign created."), "success")
        return redirect(url_for("orders.admin_promotions"))

    campaigns = db.session.scalars(
        select(PromotionCode).options(selectinload(PromotionCode.seller))
        .order_by(PromotionCode.created_at.desc(), PromotionCode.id.desc())
    ).all()
    sellers = db.session.scalars(
        select(SellerProfile).options(selectinload(SellerProfile.user))
        .where(SellerProfile.approval_status == "approved")
        .order_by(SellerProfile.store_name.asc())
    ).all()
    return render_template("admin/promotions.html", campaigns=campaigns, sellers=sellers)


@orders_bp.post("/admin/promotions/<int:promotion_id>/toggle")
@admin_required
def admin_promotion_toggle(promotion_id):
    campaign = db.session.get(PromotionCode, promotion_id)
    if campaign is None:
        abort(404)
    campaign.is_active = not campaign.is_active
    db.session.commit()
    record_audit(
        "promotion.activate" if campaign.is_active else "promotion.deactivate",
        target_type="promotion", target_id=campaign.id, detail=campaign.code,
    )
    flash(gettext("Promotion status updated."), "success")
    return redirect(url_for("orders.admin_promotions"))


@orders_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    setting = db.session.get(AppSetting, 1)
    if not setting:
        setting = AppSetting(id=1, app_name="NexHaat")
        db.session.add(setting)
    if request.method == "POST":
        name = request.form.get("app_name", "").strip()
        rate_value = request.form.get("commission_rate_percent", "").strip()
        return_window_value = request.form.get("seller_return_window_days", "").strip()
        if len(name) < 2:
            flash("App name must contain at least 2 characters.", "error")
            return render_template("admin/settings.html", setting=setting), 400
        try:
            commission_rate = Decimal(rate_value) if rate_value else None
            return_window_days = int(return_window_value)
            if commission_rate is not None and not Decimal("0") <= commission_rate <= Decimal("100"):
                raise ValueError
            if not 0 <= return_window_days <= 90:
                raise ValueError
        except (InvalidOperation, TypeError, ValueError):
            flash("Enter a commission from 0 to 100 percent and a return window from 0 to 90 days.", "error")
            return render_template("admin/settings.html", setting=setting), 400
        setting.app_name = name[:120]
        setting.commission_rate_percent = (
            commission_rate.quantize(Decimal("0.01")) if commission_rate is not None else None
        )
        setting.seller_return_window_days = return_window_days
        logo = request.files.get("logo")
        if logo and logo.filename:
            filename, upload_error = save_raster_upload(
                logo, current_app.config["BRANDING_UPLOAD_FOLDER"], "app-logo"
            )
            if upload_error:
                flash(upload_error, "error")
                return render_template("admin/settings.html", setting=setting), 400
            setting.logo_path = f"uploads/branding/{filename}"
        db.session.commit()
        record_audit("settings.update", target_type="app_setting", detail=setting.app_name)
        flash("App branding updated.", "success")
        return redirect(url_for("admin.dashboard"))
    db.session.commit()
    return render_template("admin/settings.html", setting=setting)


@orders_bp.get("/admin/payments")
@admin_required
def admin_payments():
    expire_pending_payments()
    payments = db.session.scalars(
        select(Payment)
        .options(
            selectinload(Payment.attempts),
            selectinload(Payment.refunds),
            selectinload(Payment.orders),
        )
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .limit(100)
    ).all()
    return_requests = db.session.scalars(
        select(OrderReturn)
        .options(
            joinedload(OrderReturn.order).selectinload(Order.items),
            joinedload(OrderReturn.customer),
        )
        .order_by(OrderReturn.created_at.desc(), OrderReturn.id.desc())
        .limit(100)
    ).all()
    return_order_ids = [item.order_id for item in return_requests]
    return_refunds = {}
    if return_order_ids:
        return_refunds = {
            refund.order_id: refund
            for refund in db.session.scalars(
                select(PaymentRefund).where(PaymentRefund.order_id.in_(return_order_ids))
            ).all()
        }
    sellers = db.session.scalars(
        select(User)
        .where(User.role == "seller")
        .order_by(User.email)
        .limit(500)
    ).all()
    seller_balances = {
        seller.id: seller_settlement_balance(seller.id) for seller in sellers
    }
    payouts = db.session.scalars(
        select(SellerPayout)
        .options(selectinload(SellerPayout.seller))
        .order_by(SellerPayout.created_at.desc(), SellerPayout.id.desc())
        .limit(100)
    ).all()
    return render_template(
        "admin/payments.html",
        payments=payments,
        return_requests=return_requests,
        return_refunds=return_refunds,
        sellers=sellers,
        seller_balances=seller_balances,
        payouts=payouts,
    )


@orders_bp.post("/admin/payments/<int:payment_id>/approve-review")
@admin_required
def admin_payment_approve_review(payment_id):
    payment = db.session.get(Payment, payment_id)
    if payment is None:
        abort(404)
    try:
        approve_payment_review(payment, actor=current_session_user())
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash("Payment review approved; the paid orders are now available to sellers.", "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/payments/<int:payment_id>/orders/<int:order_id>/refund")
@admin_required
def admin_payment_refund_order(payment_id, order_id):
    order = db.session.scalar(
        select(Order).where(Order.id == order_id, Order.payment_id == payment_id)
    )
    if order is None:
        abort(404)
    try:
        initiate_order_refund(
            order,
            actor=current_session_user(),
            reason=request.form.get("reason", "").strip() or "Administrator refund",
        )
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash("Refund request sent to SSLCOMMERZ; its final status is still being processed.", "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/refunds/<int:refund_id>/refresh")
@admin_required
def admin_refund_refresh(refund_id):
    refund = db.session.get(PaymentRefund, refund_id)
    if refund is None:
        abort(404)
    try:
        refresh_refund_status(refund)
    except PaymentError as error:
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash(f"Refund status: {refund.status}.", "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.post("/admin/sellers/<int:seller_id>/payouts")
@admin_required
def admin_seller_payout(seller_id):
    seller = db.session.get(User, seller_id)
    if seller is None:
        abort(404)
    try:
        payout = record_seller_payout(
            seller,
            current_session_user(),
            reference=request.form.get("reference", ""),
            note=request.form.get("note", ""),
        )
    except PaymentError as error:
        db.session.rollback()
        flash(gettext(str(error)), "error")
        return redirect(url_for("orders.admin_payments"))
    flash(f"Manual payout of ৳{payout.amount:.2f} recorded for {seller.email}.", "success")
    return redirect(url_for("orders.admin_payments"))


@orders_bp.route("/admin/customers/new", methods=["GET", "POST"])
@admin_required
def admin_customer_new():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        min_password_length = current_app.config["MIN_PASSWORD_LENGTH"]
        max_password_length = current_app.config["MAX_PASSWORD_LENGTH"]
        if (
            "@" not in email
            or len(email) > 255
            or not min_password_length <= len(password) <= max_password_length
            or not 2 <= len(name) <= 120
            or not 7 <= len(phone) <= 30
        ):
            flash(
                f"Enter valid customer details and a password ({min_password_length}–{max_password_length} characters).",
                "error",
            )
        elif db.session.scalar(select(User).where(User.email == email)):
            flash("That email is already registered.", "error")
        else:
            user = User(email=email, role="customer")
            user.set_password(password)
            user.customer_profile = CustomerProfile(full_name=name, phone=phone)
            db.session.add(user)
            db.session.commit()
            flash("Customer added.", "success")
            return redirect(url_for("admin.dashboard"))
    return render_template("admin/customer_form.html")


@orders_bp.post("/admin/customers/<int:user_id>/remove")
@admin_required
def admin_customer_remove(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "customer":
        abort(404)
    email = user.email
    db.session.delete(user)
    db.session.commit()
    record_audit("customer.remove", target_type="user", target_id=user_id, detail=f"customer:{email}")
    flash(gettext("Customer removed."), "success")
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/customers/<int:user_id>/toggle-active")
@admin_required
def admin_customer_toggle_active(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "customer":
        abort(404)
    action = request.form.get("action")
    if action == "activate":
        user.is_active = True
    elif action == "deactivate":
        user.is_active = False
    else:
        user.is_active = not user.is_active
    user.auth_version += 1
    db.session.commit()
    status_key = "activated" if user.is_active else "deactivated"
    record_audit(f"customer.{status_key}", target_type="user", target_id=user.id, detail=f"customer:{user.email}")
    if user.is_active:
        flash(gettext("Customer account activated."), "success")
    else:
        flash(gettext("Customer account deactivated."), "success")
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/customers/<int:user_id>/activate")
@admin_required
def admin_customer_activate(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "customer":
        abort(404)
    user.is_active = True
    user.auth_version += 1
    db.session.commit()
    record_audit("customer.activated", target_type="user", target_id=user.id, detail=f"customer:{user.email}")
    flash(gettext("Customer account activated."), "success")
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/customers/<int:user_id>/deactivate")
@admin_required
def admin_customer_deactivate(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "customer":
        abort(404)
    user.is_active = False
    user.auth_version += 1
    db.session.commit()
    record_audit("customer.deactivated", target_type="user", target_id=user.id, detail=f"customer:{user.email}")
    flash(gettext("Customer account deactivated."), "success")
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/accounts/<int:user_id>/remove")
@primary_admin_required
def admin_account_remove(user_id):
    """Delete a Seller, Rider, or sub-Admin. The primary Admin is protected."""
    user = db.session.get(User, user_id)
    if not user or user.role not in {"seller", "rider", "admin"}:
        abort(404)
    if is_primary_admin(user):
        flash(gettext("The primary Admin account cannot be deleted."), "error")
        return redirect(url_for("admin.dashboard"))
    if user.id == session.get("user_id"):
        flash(gettext("You cannot delete your own account here."), "error")
        return redirect(url_for("admin.dashboard"))
    detail = f"{user.role}:{user.email}"
    db.session.delete(user)
    db.session.commit()
    record_audit("account.remove", target_type="user", target_id=user_id, detail=detail)
    flash(gettext("Account removed."), "success")
    return redirect(url_for("admin.dashboard"))


@orders_bp.get("/admin/orders/<int:order_id>")
@admin_required
def admin_order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    return render_template("admin/order_detail.html", order=order)


def _set_admin_order_status(order_id, status):
    order = db.session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        abort(404)
    if status in {"cancelled", "declined"}:
        try:
            cancel_order_with_refund(
                order,
                actor=current_session_user(),
                reason="Administrator cancelled the unshipped order",
                final_order_status=status,
            )
        except PaymentError as error:
            db.session.rollback()
            flash(gettext(str(error)), "error")
            return redirect(url_for("admin.dashboard"))
    else:
        if not transition_order(order, status):
            flash(gettext("That order status transition is not allowed."), "error")
            return redirect(url_for("admin.dashboard"))
        db.session.commit()
    record_audit("order.status", target_type="order", target_id=order.id, detail=status)
    queue_order_status(order)
    if status == "confirmed":
        queue_order_receipt(order)
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/orders/<int:order_id>/confirm")
@admin_required
def admin_order_confirm(order_id):
    return _set_admin_order_status(order_id, "confirmed")


@orders_bp.post("/admin/orders/<int:order_id>/decline")
@admin_required
def admin_order_decline(order_id):
    return _set_admin_order_status(order_id, "declined")


@orders_bp.post("/admin/orders/<int:order_id>/remove")
@admin_required
def admin_order_remove(order_id):
    order = db.session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        abort(404)
    if order.payment_method == "sslcommerz":
        flash("Online payment orders are retained for financial audit.", "error")
        return redirect(url_for("admin.dashboard"))
    if order.status in {"pending", "confirmed", "preparing"}:
        release_reserved_stock(order)
    db.session.delete(order)
    db.session.commit()
    flash("Order removed permanently.", "success")
    return redirect(url_for("admin.dashboard"))


def _set_all_pending_order_status(status):
    pending_orders = db.session.scalars(
        select(Order).options(selectinload(Order.items))
        .where(Order.status == "pending").order_by(Order.created_at)
    ).all()
    updated = []
    rejected = 0
    for order in pending_orders:
        try:
            if status in {"cancelled", "declined"}:
                cancel_order_with_refund(
                    order,
                    actor=current_session_user(),
                    reason="Administrator bulk-cancelled the unshipped order",
                    final_order_status=status,
                )
                updated.append(order)
            elif transition_order(order, status):
                updated.append(order)
            else:
                rejected += 1
        except PaymentError:
            db.session.rollback()
            rejected += 1
    db.session.commit()
    for order in updated:
        queue_order_status(order)
        if status == "confirmed":
            queue_order_receipt(order)
    flash(
        f"{len(updated)} pending order(s) marked {status}; {rejected} require payment review.",
        "success" if not rejected else "error",
    )
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/orders/confirm-all")
@admin_required
def admin_order_confirm_all():
    return _set_all_pending_order_status("confirmed")


@orders_bp.post("/admin/orders/decline-all")
@admin_required
def admin_order_decline_all():
    return _set_all_pending_order_status("declined")


@orders_bp.route("/admin/products/new", methods=["GET", "POST"])
@admin_required
def admin_product_new():
    categories = db.session.scalars(select(Category).order_by(Category.name)).all()
    if request.method == "POST":
        try:
            price = Decimal(request.form["price"])
            discount_price = Decimal(request.form["discount_price"]) if request.form.get("discount_price") else None
            category_id = int(request.form["category_id"])
            name = request.form["name"].strip()
            brand_name = request.form.get("brand_name", "").strip() or None
            slug = request.form["slug"].strip()
            description = request.form["description"].strip()
            if (
                not db.session.get(Category, category_id)
                or not 2 <= len(name) <= 160
                or len(description) > 10000
            ):
                raise ValueError("Invalid product fields")
            product = Product(
                category_id=category_id, brand_name=brand_name, name=name, slug=slug, description=description,
                price=price, discount_price=discount_price, is_available="is_available" in request.form,
            )
            if len(product.slug) > 180 or db.session.scalar(
                select(Product.id).where(Product.slug == product.slug)
            ):
                raise ValueError("Duplicate or invalid product slug")
        except (KeyError, TypeError, ValueError, ArithmeticError):
            flash("Please enter valid product details.", "error")
            return render_template("admin/product_form.html", product=None, categories=categories), 400
        db.session.add(product)
        db.session.commit()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/product_form.html", product=None, categories=categories)


@orders_bp.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_edit(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    categories = db.session.scalars(select(Category).order_by(Category.name)).all()
    if request.method == "POST":
        try:
            category_id = int(request.form["category_id"])
            name = request.form["name"].strip()
            description = request.form["description"].strip()
            if (
                not db.session.get(Category, category_id)
                or not 2 <= len(name) <= 160
                or len(description) > 10000
            ):
                raise ValueError("Invalid product fields")
            candidate = Product(
                category_id=category_id,
                brand_name=request.form.get("brand_name", "").strip() or None,
                name=name,
                slug=request.form["slug"].strip(),
                description=description,
                price=Decimal(request.form["price"]),
                discount_price=Decimal(request.form["discount_price"]) if request.form.get("discount_price") else None,
                is_available="is_available" in request.form,
            )
            if len(candidate.slug) > 180 or db.session.scalar(
                select(Product.id).where(Product.slug == candidate.slug, Product.id != product.id)
            ):
                raise ValueError("Duplicate or invalid product slug")
        except (KeyError, TypeError, ValueError, ArithmeticError):
            flash("Please enter valid product details.", "error")
            return render_template("admin/product_form.html", product=product, categories=categories), 400
        product.name = candidate.name
        product.slug = candidate.slug
        product.category_id = candidate.category_id
        product.brand_name = candidate.brand_name
        product.description = candidate.description
        product.price = candidate.price
        product.discount_price = candidate.discount_price
        product.is_available = "is_available" in request.form
        db.session.commit()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/product_form.html", product=product, categories=categories)


@orders_bp.post("/admin/products/<int:product_id>/delete")
@admin_required
def admin_product_delete(product_id):
    product = db.session.get(Product, product_id)
    if product:
        product.is_available = False
        db.session.commit()
    return redirect(url_for("admin.dashboard"))


@orders_bp.route("/admin/categories/new", methods=["GET", "POST"])
@admin_required
def admin_category_new():
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            description = request.form.get("description", "").strip()
            if not 2 <= len(name) <= 100 or len(description) > 5000:
                raise ValueError("Invalid category fields")
            category = Category(name=name, slug=request.form["slug"].strip(), description=description)
            if len(category.slug) > 120 or db.session.scalar(
                select(Category.id).where(Category.slug == category.slug)
            ):
                raise ValueError("Duplicate or invalid category slug")
        except (KeyError, TypeError, ValueError):
            flash("Please enter valid category details.", "error")
            return render_template("admin/category_form.html", category=None), 400
        db.session.add(category)
        db.session.commit()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/category_form.html", category=None)


@orders_bp.route("/admin/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_category_edit(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        abort(404)
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            description = request.form.get("description", "").strip()
            if not 2 <= len(name) <= 100 or len(description) > 5000:
                raise ValueError("Invalid category fields")
            candidate = Category(name=name, slug=request.form["slug"].strip(), description=description)
            if len(candidate.slug) > 120 or db.session.scalar(
                select(Category.id).where(Category.slug == candidate.slug, Category.id != category.id)
            ):
                raise ValueError("Duplicate or invalid category slug")
        except (KeyError, TypeError, ValueError):
            flash("Please enter valid category details.", "error")
            return render_template("admin/category_form.html", category=category), 400
        category.name = candidate.name
        category.slug = candidate.slug
        category.description = candidate.description
        db.session.commit()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/category_form.html", category=category)


@orders_bp.post("/admin/categories/<int:category_id>/delete")
@admin_required
def admin_category_delete(category_id):
    category = db.session.get(Category, category_id)
    if category:
        category.is_active = False
        for product in category.products:
            product.is_available = False
        db.session.commit()
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/orders/<int:order_id>/status")
@admin_required
def admin_order_status(order_id):
    order = db.session.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    status = request.form.get("status")
    if not order or status not in STATUSES:
        abort(404)
    if status in {"cancelled", "declined"}:
        try:
            cancel_order_with_refund(
                order,
                actor=current_session_user(),
                reason="Administrator cancelled the unshipped order",
                final_order_status=status,
            )
        except PaymentError as error:
            db.session.rollback()
            flash(gettext(str(error)), "error")
            return redirect(url_for("admin.dashboard"))
    else:
        if not transition_order(order, status):
            flash(gettext("That order status transition is not allowed."), "error")
            return redirect(url_for("admin.dashboard"))
        db.session.commit()
    queue_order_status(order)
    if status == "confirmed":
        queue_order_receipt(order)
    if order.user_id:
        notify(
            order.user_id,
            gettext(
                "Order %(number)s is now %(status)s.",
                number=order.order_number,
                status=status,
            ),
            type="order",
            link=url_for("orders.confirmation", order_number=order.order_number),
        )
    return redirect(url_for("admin.dashboard"))


@orders_bp.post("/admin/orders/<int:order_id>/assign")
@admin_required
def admin_assign_rider(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    rider_id = request.form.get("rider_id", type=int)
    if rider_id:
        rider = db.session.get(User, rider_id)
        if not rider or rider.role != "rider" or rider.rider_profile is None:
            flash(gettext("Choose an active delivery rider."), "error")
            return redirect(url_for("admin.dashboard"))
        order.rider_id = rider.id
        order.delivery_status = "assigned"
        order.assigned_at = datetime.now(timezone.utc)
        order.delivery_note = None
        flash(gettext("Rider assigned to this delivery."), "success")
    else:
        order.rider_id = None
        order.delivery_status = "unassigned"
        order.assigned_at = None
        order.picked_up_at = None
        order.out_for_delivery_at = None
        order.delivered_at = None
        flash(gettext("Delivery unassigned."), "success")
    db.session.commit()
    record_audit(
        "delivery.assign",
        target_type="order",
        target_id=order.id,
        detail=f"rider={order.rider_id}" if order.rider_id else "cleared",
    )
    if order.rider_id:
        notify(
            order.rider_id,
            gettext("A new delivery was assigned to you: %(number)s.", number=order.order_number),
            type="delivery",
            link=url_for("rider.dashboard"),
        )
    return redirect(url_for("admin.dashboard"))
