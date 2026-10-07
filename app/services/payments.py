"""Checkout payment, refund, expiration, and seller-settlement workflows."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from .ai_action_notices import notify_admin_ai_action
from ..models import (
    Order, OrderReturn, Payment, PaymentAttempt, PaymentRefund, SellerLedgerEntry, SellerPayout, User,
)
from .audit import record_audit
from .sslcommerz import (
    SSLCOMMERZError,
    create_hosted_session,
    gateway_is_configured,
    initiate_refund as provider_initiate_refund,
    normalized_decimal,
    query_refund as provider_query_refund,
    query_transaction as provider_query_transaction,
    validate_transaction,
)


class PaymentError(ValueError):
    """A safe checkout or settlement validation error."""


def utc_now():
    return datetime.now(timezone.utc)


def normalize_utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def order_return_deadline(order, *, now=None):
    if order is None or order.delivered_at is None:
        return None
    base = normalize_utc(order.delivered_at)
    if base is None:
        return None
    days = max(0, int(order.return_window_days_snapshot or 0))
    return base + timedelta(days=days)


def is_order_return_eligible(order, *, now=None):
    if order is None or order.status != "delivered" or order.delivered_at is None:
        return False
    deadline = order_return_deadline(order, now=now)
    if deadline is None:
        return False
    current = normalize_utc(now) if now is not None else utc_now()
    return current <= deadline


def request_order_return(order, *, actor, reason=""):
    """Create one return request for a delivered order within the configured window."""
    if order is None:
        raise PaymentError("The order could not be found.")
    if getattr(actor, "role", None) != "customer" or getattr(actor, "id", None) != order.user_id:
        raise PaymentError("Only the customer who placed this order can request its return.")
    if order.status != "delivered" or order.delivery_status != "delivered":
        raise PaymentError("Only delivered orders can be returned.")
    if not is_order_return_eligible(order):
        raise PaymentError("This return window has expired.")
    existing = db.session.scalar(select(OrderReturn).where(OrderReturn.order_id == order.id).with_for_update())
    if existing is not None:
        return existing
    return_request = OrderReturn(
        order=order,
        order_id=order.id,
        customer_id=order.user_id,
        requested_by_id=getattr(actor, "id", None),
        reason=(reason or "Customer return request")[:255],
        refund_amount=Decimal(order.total or 0).quantize(Decimal("0.01")),
        status="requested",
    )
    db.session.add(return_request)
    db.session.commit()
    record_audit(
        "order.return_requested",
        actor=actor,
        target_type="order_return",
        target_id=return_request.id,
        detail=f"order={order.order_number}; amount={return_request.refund_amount}",
    )
    from .notifications import notify

    if order.seller_id:
        notify(
            order.seller_id,
            f"A return was requested for order {order.order_number}.",
            type="order",
            link="/seller/orders",
        )
    admin_ids = db.session.scalars(
        select(User.id).where(User.is_active.is_(True), User.role.in_({"admin", "super_admin", "support"}))
    ).all()
    for admin_id in admin_ids:
        notify(
            admin_id,
            f"A return was requested for order {order.order_number}.",
            type="order",
            link="/admin/payments",
        )
    return return_request


def request_return_for_order(order, *, actor, reason=""):
    return request_order_return(order, actor=actor, reason=reason)


def review_order_return(return_request, *, decision, actor=None, note=""):
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    return_request = db.session.scalar(
        select(OrderReturn).where(OrderReturn.id == return_request.id).with_for_update()
    )
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    if not _may_review_return(return_request, actor):
        raise PaymentError("Only the order's seller or an Admin can review this return.")
    if return_request.status != "requested":
        raise PaymentError("This return request has already been reviewed.")
    decision = str(decision or "").strip().lower()
    if decision not in {"approved", "rejected"}:
        raise PaymentError("Choose an approved or rejected decision.")
    note = (note or "").strip()
    if decision == "rejected" and not note:
        raise PaymentError("Add a short reason when rejecting a return request.")
    return_request.status = decision
    return_request.review_note = note[:500] or None
    return_request.reviewed_at = utc_now()
    if decision == "rejected":
        return_request.resolved_at = utc_now()
    db.session.commit()
    notify_admin_ai_action(
        "order.return_reviewed", actor=actor, target_type="order_return",
        target_id=return_request.id, detail=decision,
    )
    _notify_return_customer(
        return_request,
        f"Your return request for order {return_request.order.order_number} was {decision}.",
    )
    return return_request


def review_return_request(return_request, *, decision, actor=None, note=""):
    return review_order_return(return_request, decision=decision, actor=actor, note=note)


def _may_review_return(return_request, actor):
    if actor is None or not getattr(actor, "is_active", False):
        return False
    role = getattr(actor, "role", None)
    if role in {"admin", "super_admin", "support"}:
        return True
    seller_profile = getattr(actor, "seller_profile", None)
    return (
        role == "seller"
        and seller_profile is not None
        and seller_profile.approval_status == "approved"
        and return_request.order is not None
        and return_request.order.seller_id == actor.id
    )


def _notify_return_customer(return_request, message):
    user_id = return_request.customer_id or (return_request.order.user_id if return_request.order else None)
    if not user_id:
        return
    from .notifications import notify

    order_number = return_request.order.order_number if return_request.order else ""
    notify(
        user_id,
        message,
        type="order",
        link=f"/orders/{order_number}" if order_number else "/my-orders",
    )


def mark_order_return_received(return_request, *, actor):
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    return_request = db.session.scalar(
        select(OrderReturn).where(OrderReturn.id == return_request.id).with_for_update()
    )
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    if not _may_review_return(return_request, actor):
        raise PaymentError("Only the order's seller or an Admin can update this return.")
    if return_request.status != "approved":
        raise PaymentError("Only an approved return can be marked received.")
    return_request.status = "received"
    db.session.commit()
    record_audit(
        "order.return_received",
        actor=actor,
        target_type="order_return",
        target_id=return_request.id,
        detail=f"order={return_request.order_id}",
    )
    _notify_return_customer(
        return_request,
        f"The returned items for order {return_request.order.order_number} were received.",
    )
    return return_request


def _complete_return_refund(return_request, refund, *, actor=None):
    if return_request is None or refund is None or refund.status != "refunded":
        return return_request
    if return_request.status == "refunded":
        return return_request
    order = return_request.order
    payment = refund.payment
    return_request.status = "refunded"
    return_request.provider_refund_id = refund.provider_refund_id or return_request.provider_refund_id
    return_request.resolved_at = return_request.resolved_at or utc_now()
    order.status = "returned"
    _new_ledger_entry(payment, order, "refund", -order.items_subtotal, f"return:{return_request.id}:sale")
    _new_ledger_entry(
        payment,
        order,
        "commission_refund",
        Decimal(order.commission_amount or 0),
        f"return:{return_request.id}:commission",
    )
    db.session.commit()
    record_audit(
        "order.return_refunded",
        actor=actor,
        target_type="order_return",
        target_id=return_request.id,
        detail=f"order={order.order_number}; amount={refund.amount}",
    )
    _notify_return_customer(return_request, f"The refund for order {order.order_number} is complete.")
    return return_request


def issue_order_return_refund(return_request, *, actor=None):
    """Start an approved online return refund after the seller receives the items."""
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    return_request = db.session.scalar(
        select(OrderReturn).where(OrderReturn.id == return_request.id).with_for_update()
    )
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    if (
        actor is None
        or not getattr(actor, "is_active", False)
        or getattr(actor, "role", None) not in {"admin", "super_admin", "support"}
    ):
        raise PaymentError("Only an Admin can issue a gateway refund.")
    if return_request.status == "refunded":
        return return_request
    if return_request.status not in {"received", "failed"}:
        raise PaymentError("Approve the return and mark the items received before refunding.")
    order = return_request.order
    if order is None or order.payment_method != "sslcommerz" or order.payment is None:
        raise PaymentError("Use the manual refund action for a cash-on-delivery return.")
    payment = db.session.scalar(select(Payment).where(Payment.id == order.payment_id).with_for_update())
    if payment is None or not payment.bank_tran_id:
        raise PaymentError("A validated payment transaction is not available for this return.")
    existing = db.session.scalar(select(PaymentRefund).where(PaymentRefund.order_id == order.id).with_for_update())
    if existing is not None and existing.status == "refunded":
        return _complete_return_refund(return_request, existing, actor=actor)
    if existing is not None and existing.status == "processing":
        return_request.status = "received"
        db.session.commit()
        return return_request
    if existing is not None and existing.status == "initiating":
        raise PaymentError("A refund attempt needs provider reconciliation before it can be retried.")
    if existing is None:
        refund = PaymentRefund(
            payment_id=payment.id,
            order_id=order.id,
            created_by_id=getattr(actor, "id", None),
            refund_trans_id=f"NXHR{uuid4().hex[:24].upper()}",
            amount=Decimal(return_request.refund_amount or order.total or 0).quantize(Decimal("0.01")),
            status="initiating",
            reason=(f"Return approved for {order.order_number}")[:255],
        )
        db.session.add(refund)
        db.session.commit()
    else:
        refund = existing
        refund.status = "initiating"
        db.session.commit()
    try:
        result = provider_initiate_refund(
            payment.bank_tran_id,
            refund.refund_trans_id,
            Decimal(refund.amount),
            refund.reason,
            order.order_number,
        )
    except SSLCOMMERZError as error:
        # A timeout can happen after the provider accepted the request. Keep
        # the attempt in an unretryable state until an Admin reconciles it.
        db.session.rollback()
        refund = db.session.get(PaymentRefund, refund.id)
        if refund:
            refund.status = "initiating"
            return_request.status = "received"
            db.session.commit()
        raise PaymentError(str(error)) from error
    provider_status = str(result.get("status", "")).strip().lower()
    if result.get("APIConnect") != "DONE" or provider_status not in {"success", "processing"}:
        refund.status = "failed"
        return_request.status = "failed"
        db.session.commit()
        _notify_return_customer(return_request, f"The refund for order {order.order_number} failed and needs review.")
        raise PaymentError("The gateway did not accept this refund request.")
    refund.status = "processing"
    refund.provider_refund_id = str(result.get("refund_ref_id", "")).strip()[:80] or None
    return_request.provider_refund_id = refund.provider_refund_id
    return_request.status = "received"
    db.session.commit()
    record_audit(
        "order.return_refund_initiated",
        actor=actor,
        target_type="order_return",
        target_id=return_request.id,
        detail=f"order={order.order_number}; amount={refund.amount}",
    )
    _notify_return_customer(return_request, f"A refund for order {order.order_number} is being processed.")
    return return_request


def finalize_order_return(return_request, *, actor=None):
    return issue_order_return_refund(return_request, actor=actor)


def record_manual_return_refund(return_request, *, actor, reference):
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    return_request = db.session.scalar(
        select(OrderReturn).where(OrderReturn.id == return_request.id).with_for_update()
    )
    if return_request is None:
        raise PaymentError("The return request could not be found.")
    if (
        actor is None
        or not getattr(actor, "is_active", False)
        or getattr(actor, "role", None) not in {"admin", "super_admin", "support"}
    ):
        raise PaymentError("Only an Admin can record a manual refund.")
    if return_request.order is None or return_request.order.payment_method != "cod":
        raise PaymentError("Manual refund references are only for cash-on-delivery orders.")
    reference = (reference or "").strip()
    if return_request.status == "refunded":
        if return_request.manual_refund_reference == reference:
            return return_request
        raise PaymentError("This return has already been refunded.")
    if return_request.status not in {"received", "failed"}:
        raise PaymentError("Approve the return and mark the items received before recording a refund.")
    if not 3 <= len(reference) <= 120:
        raise PaymentError("Enter a manual refund reference between 3 and 120 characters.")
    order = return_request.order
    return_request.manual_refund_reference = reference
    return_request.status = "refunded"
    return_request.resolved_at = utc_now()
    order.status = "returned"
    db.session.commit()
    record_audit(
        "order.return_manual_refunded",
        actor=actor,
        target_type="order_return",
        target_id=return_request.id,
        detail=f"order={order.order_number}; amount={return_request.refund_amount}; reference={reference}",
    )
    _notify_return_customer(return_request, f"The manual refund for order {order.order_number} is complete.")
    return return_request


def begin_payment_attempt(payment):
    """Create a persisted, idempotently addressable gateway session attempt."""
    payment = db.session.scalar(
        select(Payment)
        .where(Payment.id == payment.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if payment is None:
        raise PaymentError("This payment could not be found.")
    now = utc_now()
    if payment.status != "pending":
        raise PaymentError("This payment can no longer be retried.")
    if normalize_utc(payment.expires_at) <= now:
        expire_pending_payments(now=now, payment_id=payment.id)
        raise PaymentError("This payment session expired. Please place the order again.")
    if not gateway_is_configured():
        raise PaymentError("Online payment is not configured. Please choose cash on delivery.")

    latest = db.session.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.payment_id == payment.id)
        .order_by(PaymentAttempt.created_at.desc(), PaymentAttempt.id.desc())
        .limit(1)
    )
    if latest and latest.status == "pending" and latest.gateway_url:
        return latest.gateway_url
    if latest and latest.status in {"initiating", "pending"}:
        raise PaymentError("A payment attempt is already being processed.")

    attempt = PaymentAttempt(
        payment_id=payment.id,
        transaction_id=f"NXH{uuid4().hex[:24].upper()}",
        status="initiating",
        expires_at=payment.expires_at,
    )
    db.session.add(attempt)
    db.session.commit()
    orders = db.session.scalars(
        select(Order).where(Order.payment_id == payment.id).order_by(Order.order_number)
    ).all()
    if not orders:
        attempt.status = "failed"
        db.session.commit()
        raise PaymentError("No orders are attached to this payment.")
    try:
        session_key, gateway_url = create_hosted_session(payment, attempt, orders[0])
    except SSLCOMMERZError as error:
        attempt.status = "failed"
        db.session.commit()
        raise PaymentError(str(error)) from error
    attempt.session_key = session_key
    attempt.gateway_url = gateway_url
    attempt.status = "pending"
    db.session.commit()
    return gateway_url


def _order_list(payment):
    return db.session.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.payment_id == payment.id)
        .order_by(Order.order_number)
    ).all()


def _new_ledger_entry(payment, order, entry_type, amount, suffix):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    if amount == 0 or not order.seller_id:
        return None
    key = f"payment:{payment.id}:order:{order.id}:{suffix}"
    existing = db.session.scalar(
        select(SellerLedgerEntry).where(SellerLedgerEntry.idempotency_key == key)
    )
    if existing:
        if entry_type in {"refund", "commission_refund"} and existing.eligible_at is None:
            existing.eligible_at = utc_now()
        return existing
    entry = SellerLedgerEntry(
        seller_id=order.seller_id,
        order_id=order.id,
        payment_id=payment.id,
        entry_type=entry_type,
        amount=amount,
        idempotency_key=key,
        eligible_at=utc_now() if entry_type in {"refund", "commission_refund"} else None,
    )
    db.session.add(entry)
    return entry


def _confirm_paid_payment(payment, attempt, *, risk_level=0):
    orders = _order_list(payment)

    # Repeated IPNs must remain idempotent, and a second successful attempt
    # must never replace the transaction already linked to this checkout.
    if payment.status in {"paid", "partially_refunded", "refunded"}:
        if payment.bank_tran_id == attempt.bank_tran_id:
            attempt.status = "paid"
            db.session.commit()
            return "paid"
        attempt.status = "duplicate_paid"
        db.session.commit()
        record_audit(
            "payment.duplicate_success",
            target_type="payment",
            target_id=payment.id,
            detail="A second valid provider transaction needs reconciliation",
        )
        return "duplicate_paid"

    # Do not let a duplicate notification automatically release a payment
    # that was held for risk or late-payment review.
    if payment.status == "review_required":
        return "review_required"

    if risk_level == 1:
        payment.status = "review_required"
        payment.bank_tran_id = attempt.bank_tran_id
        payment.validation_id = attempt.validation_id
        attempt.status = "review_required"
        db.session.commit()
        record_audit(
            "payment.risk_review",
            target_type="payment",
            target_id=payment.id,
            detail="SSLCOMMERZ risk level requires Admin review",
        )
        return "review_required"

    if payment.status in {"expired", "cancelled"} or any(
        order.status in {"cancelled", "declined"} for order in orders
    ):
        payment.status = "review_required"
        payment.bank_tran_id = attempt.bank_tran_id
        payment.validation_id = attempt.validation_id
        attempt.status = "review_required"
        db.session.commit()
        record_audit(
            "payment.late_success",
            target_type="payment",
            target_id=payment.id,
            detail="Validated payment arrived after order expiry/cancellation",
        )
        return "review_required"

    payment.status = "paid"
    payment.bank_tran_id = attempt.bank_tran_id
    payment.validation_id = attempt.validation_id
    payment.paid_at = utc_now()
    for order in orders:
        if order.status == "pending":
            order.status = "confirmed"
        _new_ledger_entry(payment, order, "sale", order.items_subtotal, "sale")
        commission = Decimal(order.commission_amount or 0)
        _new_ledger_entry(payment, order, "commission", -commission, "commission")
    attempt.status = "paid"
    db.session.commit()

    from .mail import enqueue_order_emails, queue_order_receipt
    from .notifications import notify
    for order in orders:
        enqueue_order_emails(order)
        queue_order_receipt(order)
        if order.user_id:
            notify(
                order.user_id,
                f"Payment confirmed for order {order.order_number}.",
                type="order",
                link=f"/orders/{order.order_number}",
            )
        if order.seller_id:
            notify(
                order.seller_id,
                f"Paid order {order.order_number} is ready for review.",
                type="order",
                link="/seller/orders",
            )
    record_audit("payment.confirmed", target_type="payment", target_id=payment.id)
    return "paid"


def process_ipn(form):
    """Validate a provider callback against SSLCOMMERZ and local money data."""
    transaction_id = str(form.get("tran_id", "")).strip()
    attempt = db.session.scalar(
        select(PaymentAttempt)
        .options(selectinload(PaymentAttempt.payment))
        .where(PaymentAttempt.transaction_id == transaction_id)
        .with_for_update()
    )
    if attempt is None:
        return False
    payment = db.session.scalar(
        select(Payment)
        .where(Payment.id == attempt.payment_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if payment is None:
        db.session.rollback()
        return False
    supplied_status = str(form.get("status", "")).strip().upper()
    if supplied_status not in {"VALID", "VALIDATED"}:
        return False
    validation_id = str(form.get("val_id", "")).strip()
    try:
        validated = validate_transaction(validation_id)
    except SSLCOMMERZError:
        db.session.rollback()
        return False
    provider_status = str(validated.get("status", "")).strip().upper()
    validated_amount = normalized_decimal(validated.get("amount"))
    validated_transaction = str(validated.get("tran_id", "")).strip()
    currency = str(validated.get("currency", "")).strip().upper()
    if (
        provider_status not in {"VALID", "VALIDATED"}
        or validated_transaction != attempt.transaction_id
        or validated_amount != Decimal(payment.amount).quantize(Decimal("0.01"))
        or currency != payment.currency
        or not str(validated.get("bank_tran_id", "")).strip()
    ):
        db.session.rollback()
        return False

    attempt.validation_id = validation_id
    attempt.bank_tran_id = str(validated.get("bank_tran_id", "")).strip()[:80] or None
    attempt.validated_amount = validated_amount
    attempt.validated_currency = currency
    try:
        risk_level = int(validated.get("risk_level", 0) or 0)
    except (TypeError, ValueError):
        risk_level = 1
    attempt.risk_level = risk_level if risk_level in {0, 1} else 1
    result = _confirm_paid_payment(payment, attempt, risk_level=attempt.risk_level)
    return result in {"paid", "review_required", "duplicate_paid"}


def process_failed_callback(form):
    """Only mark a failed attempt after checking its state with the provider."""
    transaction_id = str(form.get("tran_id", "")).strip()
    attempt = db.session.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.transaction_id == transaction_id)
        .with_for_update()
    )
    if attempt is None or attempt.status != "pending":
        return False
    try:
        result = provider_query_transaction(transaction_id)
    except SSLCOMMERZError:
        db.session.rollback()
        return False
    provider_transaction = str(result.get("tran_id", "")).strip()
    provider_status = str(result.get("status", "")).strip().upper()
    mapping = {
        "FAILED": "failed",
        "CANCELLED": "cancelled",
        "EXPIRED": "expired",
        "UNATTEMPTED": "failed",
    }
    if result.get("APIConnect") != "DONE" or provider_transaction != transaction_id:
        db.session.rollback()
        return False
    terminal = mapping.get(provider_status)
    if not terminal:
        db.session.rollback()
        return False
    attempt.status = terminal
    db.session.commit()
    return True


def cancel_order_with_refund(order, *, actor=None, reason=None, final_order_status="cancelled"):
    """Cancel an order safely, refunding a paid online sub-order first."""
    if order.payment_method != "sslcommerz" or order.payment is None:
        from .orders import transition_order

        if not transition_order(order, final_order_status):
            raise PaymentError("That order status transition is not allowed.")
        db.session.commit()
        return None

    payment = db.session.scalar(
        select(Payment).where(Payment.id == order.payment_id).with_for_update()
    )
    if payment is None:
        raise PaymentError("The payment record could not be found.")
    if payment.status in {"paid", "review_required", "partially_refunded"}:
        return initiate_order_refund(
            order,
            actor=actor,
            reason=reason or "Unshipped order cancelled",
            final_order_status=final_order_status,
        )
    if payment.status == "pending":
        latest = db.session.scalar(
            select(PaymentAttempt)
            .where(PaymentAttempt.payment_id == payment.id)
            .order_by(PaymentAttempt.created_at.desc(), PaymentAttempt.id.desc())
            .limit(1)
            .with_for_update()
        )
        if latest and latest.status in {"initiating", "pending"}:
            if normalize_utc(latest.expires_at) > utc_now():
                raise PaymentError("Wait for the active payment attempt to finish before cancelling.")
            latest.status = "expired"
        payment.status = "cancelled"
        from .orders import transition_order

        # One provider session covers the whole checkout group. If it has not
        # been paid, cancelling just one sub-order would leave a stale gateway
        # amount and other orders that can never be paid, so cancel the group.
        for group_order in _order_list(payment):
            if group_order.status not in {"pending", "confirmed"}:
                continue
            target = final_order_status if group_order.id == order.id else "cancelled"
            if not transition_order(group_order, target):
                raise PaymentError("The unpaid checkout could not be cancelled safely.")
        db.session.commit()
        return None

    from .orders import transition_order

    if not transition_order(order, final_order_status):
        raise PaymentError("That order status transition is not allowed.")
    db.session.commit()
    return None


def make_seller_ledger_eligible(order, delivered_at):
    """Start the snapshotted return window when proof-of-delivery is recorded."""
    if order.payment_method != "sslcommerz" or not order.payment_id or not delivered_at:
        return
    days = max(0, int(order.return_window_days_snapshot or 0))
    eligible_at = normalize_utc(delivered_at) + timedelta(days=days)
    entries = db.session.scalars(
        select(SellerLedgerEntry).where(
            SellerLedgerEntry.order_id == order.id,
            SellerLedgerEntry.payout_id.is_(None),
        )
    ).all()
    for entry in entries:
        if entry.eligible_at is None:
            entry.eligible_at = eligible_at


def approve_payment_review(payment, actor):
    payment = db.session.scalar(
        select(Payment).where(Payment.id == payment.id).with_for_update()
    )
    if payment is None or payment.status != "review_required":
        raise PaymentError("This payment is not awaiting review.")
    orders = _order_list(payment)
    if not orders or any(order.status in {"cancelled", "declined"} for order in orders):
        raise PaymentError("This order group was already cancelled; issue a refund instead.")
    attempt = db.session.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.payment_id == payment.id, PaymentAttempt.status == "review_required")
        .order_by(PaymentAttempt.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if attempt is None:
        raise PaymentError("No validated payment is awaiting review.")
    attempt.status = "pending"
    payment.status = "pending"
    result = _confirm_paid_payment(payment, attempt, risk_level=0)
    notify_admin_ai_action(
        "payment.risk_approved", actor=actor,
        target_type="payment", target_id=payment.id,
    )
    return result


def expire_pending_payments(*, now=None, payment_id=None, limit=200):
    now = now or utc_now()
    statement = select(Payment).where(Payment.status == "pending", Payment.expires_at <= now)
    if payment_id is not None:
        statement = statement.where(Payment.id == payment_id)
    payments = db.session.scalars(
        statement.order_by(Payment.expires_at).limit(limit).with_for_update()
    ).all()
    from .orders import transition_order

    expired = 0
    for payment in payments:
        payment.status = "expired"
        orders = _order_list(payment)
        for order in orders:
            if order.status in {"pending", "confirmed"}:
                transition_order(order, "cancelled")
        for attempt in payment.attempts:
            if attempt.status in {"initiating", "pending"}:
                attempt.status = "expired"
        expired += 1
    if expired:
        db.session.commit()
    return expired


def initiate_order_refund(order, *, actor, reason, final_order_status="cancelled"):
    """Issue a full refund for one unshipped seller sub-order, idempotently."""
    if order.payment_method != "sslcommerz" or order.payment is None:
        raise PaymentError("This order does not have an online payment to refund.")
    payment = db.session.scalar(
        select(Payment).where(Payment.id == order.payment_id).with_for_update()
    )
    if payment is None or payment.status not in {
        "paid", "review_required", "partially_refunded",
    } or not payment.bank_tran_id:
        raise PaymentError("A validated payment transaction is not available for refund.")
    if final_order_status not in {"cancelled", "declined"}:
        raise PaymentError("Invalid cancellation status.")
    if order.status not in {"pending", "confirmed", "cancelled"}:
        raise PaymentError("Only an unshipped order can be refunded here.")
    refund = db.session.scalar(
        select(PaymentRefund).where(PaymentRefund.order_id == order.id).with_for_update()
    )
    if refund and refund.status in {"processing", "refunded"}:
        return refund
    if refund is None:
        refund = PaymentRefund(
            payment_id=payment.id,
            order_id=order.id,
            created_by_id=getattr(actor, "id", None),
            refund_trans_id=f"NXHR{uuid4().hex[:24].upper()}",
            amount=order.total,
            status="initiating",
            reason=(reason or "Order cancelled before shipment")[:255],
        )
        db.session.add(refund)
        db.session.commit()
    else:
        refund.status = "initiating"
        db.session.commit()
    try:
        result = provider_initiate_refund(
            payment.bank_tran_id,
            refund.refund_trans_id,
            Decimal(refund.amount),
            refund.reason,
            order.order_number,
        )
    except SSLCOMMERZError as error:
        db.session.rollback()
        refund = db.session.get(PaymentRefund, refund.id)
        if refund:
            refund.status = "initiating"
            db.session.commit()
        raise PaymentError(str(error)) from error
    provider_status = str(result.get("status", "")).strip().lower()
    if result.get("APIConnect") != "DONE" or provider_status not in {"success", "processing"}:
        refund.status = "failed"
        db.session.commit()
        raise PaymentError("The gateway did not accept the refund. The order was not cancelled.")

    refund.status = "processing"
    refund.provider_refund_id = str(result.get("refund_ref_id", "")).strip()[:80] or None
    if not refund.provider_refund_id:
        refund.status = "initiating"
        db.session.commit()
        raise PaymentError("The gateway did not return a refund reference. Refresh and reconcile this payment.")
    from .orders import transition_order

    if order.status != final_order_status and not transition_order(
        order, final_order_status, allow_paid_cancel=True
    ):
        db.session.rollback()
        raise PaymentError("The order changed before the refund could be recorded.")
    subtotal = order.items_subtotal
    _new_ledger_entry(payment, order, "refund", -subtotal, f"refund:{refund.id}:sale")
    _new_ledger_entry(
        payment, order, "commission_refund",
        Decimal(order.commission_amount or 0),
        f"refund:{refund.id}:commission",
    )
    payment.status = "partially_refunded"
    db.session.commit()
    record_audit(
        "payment.refund_initiated",
        actor=actor,
        target_type="payment_refund",
        target_id=refund.id,
        detail=f"order={order.order_number}; amount={refund.amount}",
    )
    return refund


def refresh_refund_status(refund):
    if refund is None:
        raise PaymentError("The refund could not be found.")
    refund = db.session.scalar(
        select(PaymentRefund).where(PaymentRefund.id == refund.id).with_for_update()
    )
    if refund is None:
        raise PaymentError("The refund could not be found.")
    if not refund.provider_refund_id:
        raise PaymentError("The provider has not supplied a refund reference yet.")
    try:
        result = provider_query_refund(refund.provider_refund_id)
    except SSLCOMMERZError as error:
        raise PaymentError(str(error)) from error
    if result.get("APIConnect") != "DONE":
        raise PaymentError("The gateway could not confirm the refund status.")
    status = str(result.get("status", "")).strip().lower()
    if status == "refunded":
        refund.status = "refunded"
    elif status == "processing":
        refund.status = "processing"
    elif status in {"failed", "cancelled"}:
        refund.status = "failed"
    db.session.commit()
    _refresh_payment_refund_status(refund.payment)
    return_request = db.session.scalar(
        select(OrderReturn).where(OrderReturn.order_id == refund.order_id).with_for_update()
    )
    if return_request is not None:
        if refund.status == "refunded":
            _complete_return_refund(return_request, refund)
        elif refund.status == "failed":
            newly_failed = return_request.status != "failed"
            return_request.status = "failed"
            db.session.commit()
            if newly_failed:
                record_audit(
                    "order.return_refund_failed",
                    target_type="order_return",
                    target_id=return_request.id,
                    detail=f"order={return_request.order.order_number}",
                )
                _notify_return_customer(
                    return_request,
                    f"The refund for order {return_request.order.order_number} failed and needs review.",
                )
        else:
            return_request.status = "received"
            db.session.commit()
    return refund


def _refresh_payment_refund_status(payment):
    refunds = list(payment.refunds)
    refunded = sum(
        (Decimal(item.amount) for item in refunds if item.status == "refunded"),
        Decimal("0.00"),
    )
    in_flight = any(item.status in {"initiating", "processing"} for item in refunds)
    if refunded >= Decimal(payment.amount):
        payment.status = "refunded"
    elif refunded or in_flight or any(item.status == "failed" for item in refunds):
        payment.status = "partially_refunded"
    elif payment.status not in {"review_required", "expired"}:
        payment.status = "paid"
    db.session.commit()


def seller_settlement_balance(seller_id):
    now = utc_now()
    open_return_order_ids = set(db.session.scalars(
        select(OrderReturn.order_id)
        .join(Order, OrderReturn.order_id == Order.id)
        .where(
            Order.seller_id == seller_id,
            OrderReturn.status.in_({"requested", "approved", "received", "failed"}),
        )
    ).all())
    entries = db.session.scalars(
        select(SellerLedgerEntry)
        .where(
            SellerLedgerEntry.seller_id == seller_id,
            SellerLedgerEntry.payout_id.is_(None),
        )
        .order_by(SellerLedgerEntry.id)
    ).all()
    eligible = Decimal("0.00")
    held = Decimal("0.00")
    for entry in entries:
        amount = Decimal(entry.amount)
        if (
            entry.order_id not in open_return_order_ids
            and normalize_utc(entry.eligible_at)
            and normalize_utc(entry.eligible_at) <= now
        ):
            eligible += amount
        else:
            held += amount
    return {
        "eligible": eligible.quantize(Decimal("0.01")),
        "held": held.quantize(Decimal("0.01")),
    }


def record_seller_payout(seller, actor, *, reference, note=""):
    reference = (reference or "").strip()
    note = (note or "").strip()
    if seller.role != "seller" or not seller.seller_profile:
        raise PaymentError("Choose a valid seller account.")
    if not 3 <= len(reference) <= 120 or len(note) > 500:
        raise PaymentError("Enter a payout reference and a note of at most 500 characters.")
    now = utc_now()
    open_return_order_ids = select(OrderReturn.order_id).where(
        OrderReturn.status.in_({"requested", "approved", "received", "failed"})
    )
    entries = db.session.scalars(
        select(SellerLedgerEntry)
        .where(
            SellerLedgerEntry.seller_id == seller.id,
            SellerLedgerEntry.payout_id.is_(None),
            SellerLedgerEntry.eligible_at.is_not(None),
            SellerLedgerEntry.eligible_at <= now,
            ~SellerLedgerEntry.order_id.in_(open_return_order_ids),
        )
        .order_by(SellerLedgerEntry.id)
        .with_for_update()
    ).all()
    amount = sum((Decimal(entry.amount) for entry in entries), Decimal("0.00")).quantize(
        Decimal("0.01")
    )
    if amount <= 0:
        raise PaymentError("This seller has no positive eligible payout balance.")
    payout = SellerPayout(
        seller_id=seller.id,
        amount=amount,
        reference=reference,
        note=note or None,
        recorded_by_id=getattr(actor, "id", None),
    )
    db.session.add(payout)
    db.session.flush()
    for entry in entries:
        entry.payout_id = payout.id
    payout_entry = SellerLedgerEntry(
        seller_id=seller.id,
        order_id=entries[-1].order_id,
        payment_id=entries[-1].payment_id,
        payout_id=payout.id,
        entry_type="payout",
        amount=-amount,
        idempotency_key=f"payout:{payout.id}",
        eligible_at=now,
    )
    db.session.add(payout_entry)
    db.session.commit()
    record_audit(
        "seller.payout.recorded",
        actor=actor,
        target_type="seller_payout",
        target_id=payout.id,
        detail=f"seller={seller.id}; amount={amount}; reference={reference}",
    )
    return payout
