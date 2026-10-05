from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import (
    CustomerProfile, Order, OrderItem, OrderReturn, Payment, PaymentRefund,
    SellerLedgerEntry, SellerProfile, User,
)
from app.services import payments as payment_service
from app.services.payments import (
    PaymentError, issue_order_return_refund, mark_order_return_received,
    record_manual_return_refund, request_order_return, review_order_return,
    seller_settlement_balance,
)
from app.services.sslcommerz import SSLCOMMERZError


def _sign_in_client(client, user):
    with client.session_transaction() as session:
        session["user_id"] = user.id
        session["role"] = user.role
        session["auth_version"] = user.auth_version


def _account(email, role, *, approved_seller=False):
    user = User(email=email, role=role)
    user.set_password("password123")
    if role == "customer":
        user.customer_profile = CustomerProfile(full_name=email.split("@")[0], phone="01234567890")
    if role == "seller":
        user.seller_profile = SellerProfile(
            store_name=email.split("@")[0],
            contact_name=email.split("@")[0],
            phone="01234567890",
            approval_status="approved" if approved_seller else "pending",
        )
    db.session.add(user)
    db.session.commit()
    return user


def _delivered_order(customer, *, seller=None, payment_method="cod", total="80.00", payment=None):
    order = Order(
        order_number=f"RET-{User.query.count():04d}",
        customer_name=customer.customer_profile.full_name,
        phone="01234567890",
        email=customer.email,
        address="12 Test Street",
        total=Decimal(total),
        payment_method=payment_method,
        payment=payment,
        seller_id=seller.id if seller else None,
        status="delivered",
        delivery_status="delivered",
        user_id=customer.id,
        delivered_at=datetime.now(timezone.utc) - timedelta(days=1),
        return_window_days_snapshot=14,
        commission_amount=Decimal("8.00") if payment_method == "sslcommerz" else None,
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name="Test item",
        price=Decimal(total),
        quantity=1,
        subtotal=Decimal(total),
    ))
    db.session.commit()
    return order


def test_return_request_uses_delivery_window(app):
    customer = User(email="return-customer@example.com", role="customer")
    customer.set_password("password123")
    customer.customer_profile = CustomerProfile(full_name="Return Customer", phone="01234567890")
    db.session.add(customer)
    db.session.commit()

    order = Order(
        order_number="RET-1001",
        customer_name="Return Customer",
        phone="01234567890",
        email="return-customer@example.com",
        address="12 Test Street",
        total=Decimal("80.00"),
        payment_method="cod",
        status="delivered",
        delivery_status="delivered",
        user_id=customer.id,
        delivered_at=datetime.now(timezone.utc) - timedelta(days=3),
        return_window_days_snapshot=7,
    )
    db.session.add(order)
    db.session.commit()

    request = request_order_return(order, actor=customer, reason="Damaged item")

    assert request.status == "requested"
    assert request.refund_amount == Decimal("80.00")
    assert order.is_return_eligible is True
    assert order.return_deadline is not None


def test_return_request_can_be_approved(app):
    customer = User(email="return-approve@example.com", role="customer")
    customer.set_password("password123")
    customer.customer_profile = CustomerProfile(full_name="Return Approver", phone="01234567891")
    db.session.add(customer)
    db.session.commit()

    order = Order(
        order_number="RET-2001",
        customer_name="Return Approver",
        phone="01234567891",
        email="return-approve@example.com",
        address="10 Example Road",
        total=Decimal("55.00"),
        payment_method="cod",
        status="delivered",
        delivery_status="delivered",
        user_id=customer.id,
        delivered_at=datetime.now(timezone.utc) - timedelta(days=1),
        return_window_days_snapshot=14,
    )
    db.session.add(order)
    db.session.commit()

    request = request_order_return(order, actor=customer, reason="Wrong size")
    admin = User(email="return-admin@example.com", role="admin")
    admin.set_password("password123")
    db.session.add(admin)
    db.session.commit()
    approved = review_order_return(request, decision="approved", actor=admin, note="Accepted")

    assert approved.status == "approved"
    assert approved.review_note == "Accepted"
    assert db.session.get(OrderReturn, request.id).status == "approved"


def test_return_review_is_scoped_to_admin_or_the_order_seller(app):
    customer = _account("return-scope-customer@example.com", "customer")
    seller = _account("return-scope-seller@example.com", "seller", approved_seller=True)
    other_seller = _account("return-other-seller@example.com", "seller", approved_seller=True)
    order = _delivered_order(customer, seller=seller)
    request = request_order_return(order, actor=customer, reason="Wrong item")

    with pytest.raises(PaymentError):
        review_order_return(request, decision="approved", actor=customer)
    with pytest.raises(PaymentError):
        review_order_return(request, decision="approved", actor=other_seller)

    approved = review_order_return(request, decision="approved", actor=seller, note="Return accepted")
    assert approved.reviewed_at is not None
    with pytest.raises(PaymentError):
        review_order_return(approved, decision="rejected", actor=seller, note="Late change")
    received = mark_order_return_received(approved, actor=seller)
    assert received.status == "received"


def test_online_return_waits_for_provider_confirmation_and_posts_ledger_once(app, client, monkeypatch):
    customer = _account("online-return-customer@example.com", "customer")
    seller = _account("online-return-seller@example.com", "seller", approved_seller=True)
    admin = _account("online-return-admin@example.com", "admin")
    payment = Payment(
        checkout_group="RET-GROUP-ONLINE",
        user_id=customer.id,
        amount=Decimal("80.00"),
        status="paid",
        bank_tran_id="BANK-RETURN-1",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.session.add(payment)
    db.session.commit()
    order = _delivered_order(customer, seller=seller, payment_method="sslcommerz", payment=payment)
    db.session.add_all([
        SellerLedgerEntry(
            seller_id=seller.id, order_id=order.id, payment_id=payment.id,
            entry_type="sale", amount=Decimal("80.00"),
            idempotency_key=f"test:{order.id}:sale", eligible_at=datetime.now(timezone.utc) - timedelta(days=1),
        ),
        SellerLedgerEntry(
            seller_id=seller.id, order_id=order.id, payment_id=payment.id,
            entry_type="commission", amount=Decimal("-8.00"),
            idempotency_key=f"test:{order.id}:commission", eligible_at=datetime.now(timezone.utc) - timedelta(days=1),
        ),
    ])
    db.session.commit()
    request = request_order_return(order, actor=customer, reason="Damaged")
    review_order_return(request, decision="approved", actor=seller)
    mark_order_return_received(request, actor=seller)
    monkeypatch.setattr(payment_service, "provider_initiate_refund", lambda *args: {
        "APIConnect": "DONE", "status": "success", "refund_ref_id": "PROVIDER-REF-1",
    })

    processing = issue_order_return_refund(request, actor=admin)
    refund = db.session.scalar(db.select(PaymentRefund).where(PaymentRefund.order_id == order.id))
    assert processing.status == "received"
    assert refund.status == "processing"
    assert order.status == "delivered"
    assert seller_settlement_balance(seller.id)["eligible"] == Decimal("0.00")
    _sign_in_client(client, customer)
    api_response = client.get(f"/api/v1/orders/{order.order_number}")
    assert api_response.json["data"]["return_request"]["refund_status"] == "processing"
    assert b"Refund status" in client.get("/my-orders").data

    monkeypatch.setattr(payment_service, "provider_query_refund", lambda reference: {
        "APIConnect": "DONE", "status": "refunded",
    })
    payment_service.refresh_refund_status(refund)
    payment_service.refresh_refund_status(refund)

    assert request.status == "refunded"
    assert order.status == "returned"
    assert refund.status == "refunded"
    api_response = client.get(f"/api/v1/orders/{order.order_number}")
    assert api_response.json["data"]["return_request"]["refund_status"] == "refunded"
    assert b"Refunded" in client.get("/my-orders").data
    entries = db.session.scalars(
        db.select(SellerLedgerEntry).where(SellerLedgerEntry.order_id == order.id)
    ).all()
    assert len(entries) == 4
    assert seller_settlement_balance(seller.id)["eligible"] == Decimal("0.00")


def test_ambiguous_provider_timeout_cannot_be_retried_as_a_new_refund(app, monkeypatch):
    customer = _account("timeout-return-customer@example.com", "customer")
    seller = _account("timeout-return-seller@example.com", "seller", approved_seller=True)
    admin = _account("timeout-return-admin@example.com", "admin")
    payment = Payment(
        checkout_group="RET-GROUP-TIMEOUT",
        user_id=customer.id,
        amount=Decimal("80.00"),
        status="paid",
        bank_tran_id="BANK-RETURN-TIMEOUT",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.session.add(payment)
    db.session.commit()
    order = _delivered_order(customer, seller=seller, payment_method="sslcommerz", payment=payment)
    request = request_order_return(order, actor=customer, reason="Damaged")
    review_order_return(request, decision="approved", actor=seller)
    mark_order_return_received(request, actor=seller)
    attempts = []

    def provider_timeout(*args):
        attempts.append(args)
        raise SSLCOMMERZError("Provider response timed out.")

    monkeypatch.setattr(payment_service, "provider_initiate_refund", provider_timeout)
    with pytest.raises(PaymentError):
        issue_order_return_refund(request, actor=admin)

    refund = db.session.scalar(db.select(PaymentRefund).where(PaymentRefund.order_id == order.id))
    assert refund.status == "initiating"
    assert request.status == "received"
    with pytest.raises(PaymentError, match="reconciliation"):
        issue_order_return_refund(request, actor=admin)
    assert len(attempts) == 1


def test_pending_return_holds_payout_and_rejection_releases_it(app):
    customer = _account("return-hold-customer@example.com", "customer")
    seller = _account("return-hold-seller@example.com", "seller", approved_seller=True)
    admin = _account("return-hold-admin@example.com", "admin")
    payment = Payment(
        checkout_group="RET-GROUP-HOLD", user_id=customer.id, amount=Decimal("80.00"),
        status="paid", bank_tran_id="BANK-HOLD",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.session.add(payment)
    db.session.commit()
    order = _delivered_order(customer, seller=seller, payment_method="sslcommerz", payment=payment)
    db.session.add(SellerLedgerEntry(
        seller_id=seller.id, order_id=order.id, payment_id=payment.id,
        entry_type="sale", amount=Decimal("80.00"), idempotency_key=f"hold:{order.id}",
        eligible_at=datetime.now(timezone.utc) - timedelta(days=1),
    ))
    db.session.commit()
    request = request_order_return(order, actor=customer, reason="Does not fit")

    balance = seller_settlement_balance(seller.id)
    assert balance["eligible"] == Decimal("0.00")
    assert balance["held"] == Decimal("80.00")
    review_order_return(request, decision="rejected", actor=admin, note="Outside return policy")
    assert seller_settlement_balance(seller.id)["eligible"] == Decimal("80.00")


def test_cod_return_requires_review_receipt_and_records_manual_refund(app):
    customer = _account("cod-return-customer@example.com", "customer")
    seller = _account("cod-return-seller@example.com", "seller", approved_seller=True)
    admin = _account("cod-return-admin@example.com", "admin")
    order = _delivered_order(customer, seller=seller, payment_method="cod")
    request = request_order_return(order, actor=customer, reason="Damaged")
    review_order_return(request, decision="approved", actor=seller)
    mark_order_return_received(request, actor=seller)

    completed = record_manual_return_refund(request, actor=admin, reference="BANK-TRANSFER-123")
    repeated = record_manual_return_refund(completed, actor=admin, reference="BANK-TRANSFER-123")
    assert repeated.status == "refunded"
    assert repeated.manual_refund_reference == "BANK-TRANSFER-123"
    assert order.status == "returned"
    with pytest.raises(PaymentError):
        record_manual_return_refund(completed, actor=admin, reference="OTHER-REF-123")


def test_customer_seller_and_admin_return_pages_share_status(client, app):
    customer = _account("return-pages-customer@example.com", "customer")
    seller = _account("return-pages-seller@example.com", "seller", approved_seller=True)
    admin = _account("return-pages-admin@example.com", "admin")
    order = _delivered_order(customer, seller=seller)

    _sign_in_client(client, customer)
    response = client.get("/my-orders")
    assert b"Request return" in response.data
    response = client.post(f"/orders/{order.order_number}/return", data={"reason": "Arrived damaged"})
    assert response.status_code == 302
    return_request = db.session.scalar(db.select(OrderReturn).where(OrderReturn.order_id == order.id))
    assert return_request.status == "requested"

    _sign_in_client(client, seller)
    response = client.get("/seller/orders")
    assert b"Arrived damaged" in response.data
    response = client.post(
        f"/seller/orders/{order.id}/returns/{return_request.id}",
        data={"action": "approved", "note": "Return accepted"},
    )
    assert response.status_code == 302
    assert return_request.status == "approved"

    _sign_in_client(client, admin)
    response = client.get("/admin/payments")
    assert b"Customer return requests" in response.data
    response = client.post(f"/admin/orders/{return_request.id}/return-received")
    assert response.status_code == 302
    assert return_request.status == "received"


def test_customer_api_returns_status_and_rejects_unowned_order(client, app):
    customer = _account("return-api-customer@example.com", "customer")
    stranger = _account("return-api-stranger@example.com", "customer")
    order = _delivered_order(customer)

    _sign_in_client(client, stranger)
    response = client.post(f"/api/v1/orders/{order.order_number}/return", json={"reason": "Not mine"})
    assert response.status_code == 404

    _sign_in_client(client, customer)
    response = client.post(
        f"/api/v1/orders/{order.order_number}/return", json={"reason": "x" * 256}
    )
    assert response.status_code == 422
    response = client.post(f"/api/v1/orders/{order.order_number}/return", json={"reason": "Wrong item"})
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["return_request"]["status"] == "requested"
    assert response.json["data"]["return_request"]["reason"] == "Wrong item"
    assert response.json["data"]["return_request"]["refund_status"] is None
