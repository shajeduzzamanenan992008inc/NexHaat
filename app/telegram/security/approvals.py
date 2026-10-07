"""Identity-bound Admin approval actions for the Security Bot."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...extensions import db
from ...models import Order, OrderReturn, Payment, Product, Review, SellerProfile, User
from ...services.ai_action_notices import notify_admin_ai_action
from ...services.mail import queue_order_receipt, queue_order_status
from ...services.notifications import notify
from ...services.orders import transition_order
from ...services.payments import PaymentError, approve_payment_review


def mapped_admin(telegram_user_id):
    from flask import current_app

    if telegram_user_id not in _allowed_admin_ids_from_config():
        return None
    raw_map = current_app.config.get("TELEGRAM_SECURITY_ADMIN_USER_MAP", "")
    user_id = None
    for pair in str(raw_map).split(","):
        telegram_id, separator, mapped_user_id = pair.strip().partition(":")
        if not separator or not telegram_id.isascii() or not telegram_id.isdigit():
            continue
        if int(telegram_id) == telegram_user_id and mapped_user_id.isascii() and mapped_user_id.isdigit():
            user_id = int(mapped_user_id)
            break
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None or not user.is_active or user.role not in {"admin", "super_admin"}:
        return None
    return user


def _allowed_admin_ids_from_config():
    from flask import current_app

    return {
        int(value.strip()) for value in
        str(current_app.config.get("TELEGRAM_SECURITY_ADMIN_IDS") or "").split(",")
        if value.strip().isascii() and value.strip().isdigit() and int(value.strip()) > 0
    }


def _buttons(kind, item_id, actions):
    return [
        {"text": label, "callback_data": f"approval|{kind}|{item_id}|{action}"}
        for action, label in actions
    ]


def pending_approvals_markup(telegram_user_id):
    from flask import current_app

    allowed_ids = _allowed_admin_ids_from_config()
    if telegram_user_id not in allowed_ids:
        return "Access denied.", None
    if mapped_admin(telegram_user_id) is None:
        return (
            "Link this allowlisted Telegram ID to an active Admin account in "
            "TELEGRAM_SECURITY_ADMIN_USER_MAP before using approval actions.",
            None,
        )

    rows = []
    for profile in db.session.scalars(
        select(SellerProfile).where(SellerProfile.approval_status == "pending")
        .order_by(SellerProfile.created_at, SellerProfile.id).limit(10)
    ).all():
        rows.append((
            f"Seller application · {profile.store_name}",
            _buttons("seller", profile.id, (("approved", "Approve"), ("rejected", "Reject"))),
        ))
    for product in db.session.scalars(
        select(Product).where(
            Product.moderation_status == "pending", Product.seller_id.is_not(None)
        ).order_by(Product.created_at, Product.id).limit(10)
    ).all():
        rows.append((
            f"Product listing · {product.name}",
            _buttons("product", product.id, (("approved", "Approve"), ("rejected", "Reject"))),
        ))
    for review in db.session.scalars(
        select(Review).options(selectinload(Review.product))
        .where(Review.status == "pending")
        .order_by(Review.created_at, Review.id).limit(10)
    ).all():
        rows.append((
            f"Product review · {review.product.name} · {review.rating}/5",
            _buttons("review", review.id, (("approved", "Approve"), ("rejected", "Reject"))),
        ))
    for payment in db.session.scalars(
        select(Payment).where(Payment.status == "review_required")
        .order_by(Payment.created_at, Payment.id).limit(10)
    ).all():
        rows.append((
            f"Validated payment risk review · {payment.checkout_group}",
            _buttons("payment", payment.id, (("approved", "Approve payment"),)),
        ))
    for return_request in db.session.scalars(
        select(OrderReturn).options(selectinload(OrderReturn.order))
        .where(OrderReturn.status == "requested")
        .order_by(OrderReturn.created_at, OrderReturn.id).limit(10)
    ).all():
        rows.append((
            f"Return request · {return_request.order.order_number}",
            _buttons("return", return_request.id, (("approved", "Approve return"),)),
        ))
    for order in db.session.scalars(
        select(Order).where(Order.status == "pending")
        .order_by(Order.created_at, Order.id).limit(10)
    ).all():
        if order.payment_method == "cod":
            actions = (("confirmed", "Confirm"), ("declined", "Decline"))
        elif order.payment and order.payment.status in {"paid", "partially_refunded"}:
            actions = (("confirmed", "Confirm"),)
        else:
            continue
        rows.append((
            f"Order · {order.order_number} · BDT {order.total:.2f}",
            _buttons("order", order.id, actions),
        ))

    rows = rows[:10]
    if not rows:
        return "No pending approvals or order confirmations.", None
    message_lines = ["Pending Admin decisions (all actions are audited):"]
    keyboard = []
    for label, buttons in rows:
        message_lines.append(f"• {label}")
        keyboard.append(buttons)
    return "\n".join(message_lines), {"inline_keyboard": keyboard}


def decide_approval(telegram_user_id, callback_data):
    admin = mapped_admin(telegram_user_id)
    if admin is None:
        return "Access denied. Link an allowlisted Telegram ID to an active Admin account."
    parts = callback_data.split("|")
    if len(parts) != 4 or parts[0] != "approval":
        return "That approval action is invalid."
    _, kind, raw_id, decision = parts
    if not raw_id.isascii() or not raw_id.isdigit():
        return "That approval action is invalid."
    item_id = int(raw_id)
    now = datetime.now(timezone.utc)

    try:
        if kind == "seller":
            item = db.session.get(SellerProfile, item_id)
            if item is None or item.approval_status != "pending" or decision not in {"approved", "rejected"}:
                return "This seller application is no longer pending."
            item.approval_status = decision
            item.reviewed_at = now
            item.reviewed_by_id = admin.id
            db.session.commit()
            if decision == "approved":
                notify(item.user_id, "Your store was approved. You can now publish products.", type="account")
            action, target_type = "seller.review", "seller_profile"
        elif kind == "product":
            item = db.session.get(Product, item_id)
            if (item is None or item.seller_id is None or item.moderation_status != "pending"
                    or decision not in {"approved", "rejected"}):
                return "This product listing is no longer pending."
            item.moderation_status = decision
            item.is_available = decision == "approved"
            item.reviewed_at = now
            item.reviewed_by_id = admin.id
            db.session.commit()
            action, target_type = "catalog.product_review", "product"
        elif kind == "review":
            item = db.session.get(Review, item_id)
            if item is None or item.status != "pending" or decision not in {"approved", "rejected"}:
                return "This product review is no longer pending."
            item.status = decision
            item.moderated_at = now
            item.moderated_by_id = admin.id
            db.session.commit()
            action, target_type = "review.moderate", "review"
        elif kind == "payment":
            item = db.session.get(Payment, item_id)
            if item is None or item.status != "review_required" or decision != "approved":
                return "This payment is no longer awaiting risk review."
            approve_payment_review(item, actor=admin)
            return "Validated payment approved. Its orders are now confirmed; the website reflects the update."
        elif kind == "return":
            item = db.session.get(OrderReturn, item_id)
            if item is None or item.status != "requested" or decision != "approved":
                return "This return request is no longer awaiting review."
            from ...services.payments import review_order_return

            review_order_return(item, decision="approved", actor=admin)
            return "Return request approved. The website reflects the updated status."
        elif kind == "order":
            item = db.session.scalar(
                select(Order).options(selectinload(Order.items))
                .where(Order.id == item_id)
            )
            if item is None or item.status != "pending":
                return "This order is no longer awaiting confirmation."
            if decision == "confirmed":
                if not transition_order(item, "confirmed"):
                    return "This order cannot be confirmed in its current payment state."
                db.session.commit()
                queue_order_status(item)
                queue_order_receipt(item)
            elif decision == "declined" and item.payment_method == "cod":
                if not transition_order(item, "declined"):
                    return "This order cannot be declined in its current state."
                db.session.commit()
                queue_order_status(item)
            else:
                return "That order decision is not allowed."
            action, target_type = "order.status", "order"
        else:
            return "That approval type is not supported."
    except PaymentError as error:
        db.session.rollback()
        return str(error)

    notify_admin_ai_action(
        action, actor=admin, target_type=target_type,
        target_id=item_id, detail=decision,
    )
    return "Decision saved. The website now shows the updated status."
