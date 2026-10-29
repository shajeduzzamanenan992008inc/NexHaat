from datetime import UTC, datetime, timedelta
from decimal import Decimal

from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.models import (
    AdminProfile,
    AppSetting,
    Category,
    CustomerProfile,
    Notification,
    Order,
    OrderItem,
    Payment,
    PaymentAttempt,
    Product,
    SellerLedgerEntry,
    SellerProfile,
    User,
)
from app.services import payments
from app.services.orders import transition_order


def make_checkout(order_count=1, *, expires_in=timedelta(minutes=15)):
    customer = User(email="payer@example.com", role="customer")
    customer.set_password("password123")
    customer.customer_profile = CustomerProfile(full_name="Paying Customer", phone="01234567890")
    sellers = []
    for index in range(order_count):
        seller = User(email=f"seller{index}@example.com", role="seller")
        seller.set_password("password123")
        seller.seller_profile = SellerProfile(
            store_name=f"Seller {index}", contact_name=f"Seller {index}",
            phone="01234567890", approval_status="approved",
        )
        sellers.append(seller)
    db.session.add_all([customer, *sellers])
    db.session.flush()

    amount = Decimal("102.50") * order_count
    payment = Payment(
        checkout_group="FB-PAYMENT-TEST",
        user_id=customer.id,
        amount=amount,
        currency="BDT",
        status="pending",
        expires_at=payments.utc_now() + expires_in,
    )
    db.session.add(payment)
    db.session.flush()
    orders = []
    for index, seller in enumerate(sellers):
        order = Order(
            order_number=f"FB-PAYMENT-TEST-{index + 1}",
            checkout_group=payment.checkout_group,
            user_id=customer.id,
            seller_id=seller.id,
            payment=payment,
            customer_name="Paying Customer",
            phone="01234567890",
            email=customer.email,
            address="12 Test Street",
            city="Dhaka",
            total=Decimal("102.50"),
            delivery_fee=Decimal("2.50"),
            payment_method="sslcommerz",
            commission_rate_percent=Decimal("10.00"),
            commission_amount=Decimal("10.00"),
            return_window_days_snapshot=14,
            status="pending",
        )
        order.items.append(OrderItem(
            product_name="Test product", price=Decimal("100.00"), quantity=1,
            subtotal=Decimal("100.00"),
        ))
        orders.append(order)
    attempt = PaymentAttempt(
        payment=payment,
        transaction_id="NXH-PAYMENT-TEST-0001",
        status="pending",
        expires_at=payment.expires_at,
    )
    db.session.add_all([*orders, attempt])
    db.session.commit()
    return customer, sellers, payment, orders, attempt


def valid_gateway_result(attempt, *, amount="102.50", bank_tran_id="BANK-TEST-1", risk_level=0):
    return {
        "status": "VALID",
        "tran_id": attempt.transaction_id,
        "amount": amount,
        "currency": "BDT",
        "bank_tran_id": bank_tran_id,
        "risk_level": risk_level,
    }


def silence_payment_side_effects(monkeypatch):
    monkeypatch.setattr(payments, "record_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.mail.enqueue_order_emails", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.mail.queue_order_receipt", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.notifications.notify", lambda *args, **kwargs: None)


def post_valid_ipn(monkeypatch, attempt, *, result=None):
    monkeypatch.setattr(
        payments,
        "validate_transaction",
        lambda _validation_id: result or valid_gateway_result(attempt),
    )
    return payments.process_ipn(MultiDict({
        "tran_id": attempt.transaction_id,
        "status": "VALID",
        "val_id": "VALIDATION-TEST-1",
    }))


def test_ipn_confirms_only_server_validated_payment_and_is_idempotent(app, monkeypatch):
    with app.app_context():
        _customer, _sellers, payment, orders, attempt = make_checkout()
        silence_payment_side_effects(monkeypatch)

        assert post_valid_ipn(monkeypatch, attempt)
        db.session.refresh(payment)
        db.session.refresh(orders[0])
        assert payment.status == "paid"
        assert payment.bank_tran_id == "BANK-TEST-1"
        assert orders[0].status == "confirmed"
        assert db.session.query(SellerLedgerEntry).count() == 2

        assert post_valid_ipn(monkeypatch, attempt)
        assert db.session.query(SellerLedgerEntry).count() == 2


def test_forged_or_amount_mismatched_ipn_does_not_confirm_order(app, monkeypatch):
    with app.app_context():
        _customer, _sellers, payment, orders, attempt = make_checkout()
        silence_payment_side_effects(monkeypatch)
        monkeypatch.setattr(payments, "validate_transaction", lambda _validation_id: {})

        assert not payments.process_ipn(MultiDict({
            "tran_id": attempt.transaction_id,
            "status": "VALID",
            "val_id": "FORGED",
        }))
        assert not post_valid_ipn(
            monkeypatch, attempt, result=valid_gateway_result(attempt, amount="1.00")
        )
        db.session.refresh(payment)
        db.session.refresh(orders[0])
        assert payment.status == "pending"
        assert payment.bank_tran_id is None
        assert orders[0].status == "pending"
        assert db.session.query(SellerLedgerEntry).count() == 0


def test_risk_review_stays_held_until_admin_approval(app, monkeypatch):
    with app.app_context():
        _customer, _sellers, payment, orders, attempt = make_checkout()
        silence_payment_side_effects(monkeypatch)
        assert post_valid_ipn(
            monkeypatch, attempt,
            result=valid_gateway_result(attempt, risk_level=1),
        )
        assert post_valid_ipn(
            monkeypatch, attempt,
            result=valid_gateway_result(attempt, risk_level=1),
        )
        db.session.refresh(payment)
        db.session.refresh(orders[0])
        assert payment.status == "review_required"
        assert orders[0].status == "pending"
        assert db.session.query(SellerLedgerEntry).count() == 0

        assert payments.approve_payment_review(payment, actor=None) == "paid"
        db.session.refresh(payment)
        db.session.refresh(orders[0])
        assert payment.status == "paid"
        assert orders[0].status == "confirmed"


def test_second_successful_charge_does_not_replace_original_transaction(app, monkeypatch):
    with app.app_context():
        _customer, _sellers, payment, _orders, first_attempt = make_checkout()
        silence_payment_side_effects(monkeypatch)
        assert post_valid_ipn(monkeypatch, first_attempt)
        original_bank_id = payment.bank_tran_id

        second_attempt = PaymentAttempt(
            payment=payment,
            transaction_id="NXH-PAYMENT-TEST-0002",
            status="pending",
            expires_at=payment.expires_at,
        )
        db.session.add(second_attempt)
        db.session.commit()
        assert post_valid_ipn(
            monkeypatch, second_attempt,
            result=valid_gateway_result(
                second_attempt, bank_tran_id="BANK-TEST-DUPLICATE"
            ),
        )
        db.session.refresh(payment)
        db.session.refresh(second_attempt)
        assert payment.status == "paid"
        assert payment.bank_tran_id == original_bank_id
        assert second_attempt.status == "duplicate_paid"


def test_failed_callback_requires_provider_status_and_allows_a_retry(app, monkeypatch):
    with app.app_context():
        _customer, _sellers, payment, _orders, attempt = make_checkout()
        monkeypatch.setattr(
            payments,
            "provider_query_transaction",
            lambda _transaction_id: {
                "APIConnect": "DONE", "tran_id": attempt.transaction_id, "status": "FAILED",
            },
        )
        assert payments.process_failed_callback(MultiDict({
            "tran_id": attempt.transaction_id,
            "status": "FAILED",
        }))
        db.session.refresh(attempt)
        assert attempt.status == "failed"

        app.config.update(
            SSLCOMMERZ_STORE_ID="sandbox-store",
            SSLCOMMERZ_STORE_PASSWORD="sandbox-password",
            PUBLIC_BASE_URL="https://shop.example.test",
        )
        monkeypatch.setattr(
            payments,
            "create_hosted_session",
            lambda *_args, **_kwargs: (
                "SESSION-RETRY",
                "https://sandbox.sslcommerz.com/gwprocess/v4/retry",
            ),
        )
        retry_url = payments.begin_payment_attempt(payment)
        attempts = db.session.query(PaymentAttempt).order_by(PaymentAttempt.id).all()
        assert retry_url.endswith("/retry")
        assert len(attempts) == 2
        assert attempts[0].status == "failed"
        assert attempts[1].status == "pending"


def test_refunding_one_seller_suborder_leaves_other_seller_active(app, monkeypatch):
    with app.app_context():
        customer, _sellers, payment, orders, attempt = make_checkout(order_count=2)
        silence_payment_side_effects(monkeypatch)
        assert post_valid_ipn(
            monkeypatch, attempt,
            result=valid_gateway_result(attempt, amount="205.00"),
        )
        monkeypatch.setattr(
            payments,
            "provider_initiate_refund",
            lambda *args, **kwargs: {
                "APIConnect": "DONE", "status": "success", "refund_ref_id": "REFUND-1",
            },
        )

        refund = payments.cancel_order_with_refund(
            orders[0], actor=customer, reason="Customer cancelled before shipment"
        )
        db.session.refresh(payment)
        db.session.refresh(orders[0])
        db.session.refresh(orders[1])
        assert refund.status == "processing"
        assert payment.status == "partially_refunded"
        assert orders[0].status == "cancelled"
        assert orders[1].status == "confirmed"
        monkeypatch.setattr(
            payments,
            "provider_query_refund",
            lambda _refund_ref: {"APIConnect": "DONE", "status": "failed"},
        )
        assert payments.refresh_refund_status(refund).status == "failed"
        db.session.refresh(payment)
        assert payment.status == "partially_refunded"
        assert transition_order(orders[1], "preparing")


def test_cancelling_unpaid_multi_seller_checkout_cancels_group_and_releases_stock(app):
    with app.app_context():
        customer, _sellers, payment, orders, attempt = make_checkout(order_count=2)
        attempt.status = "failed"
        products = []
        for index, order in enumerate(orders, start=1):
            category = Category(name=f"Reserved group {index}", slug=f"reserved-group-{index}")
            product = Product(
                category=category, name=f"Reserved group item {index}",
                slug=f"reserved-group-item-{index}", description="",
                price=Decimal("100.00"), stock_quantity=4, is_available=True,
            )
            db.session.add(product)
            db.session.flush()
            order.items[0].product_id = product.id
            products.append(product)
        db.session.commit()

        assert payments.cancel_order_with_refund(
            orders[0], actor=customer, reason="Cancel unpaid checkout"
        ) is None
        db.session.refresh(payment)
        db.session.refresh(orders[0])
        db.session.refresh(orders[1])
        assert payment.status == "cancelled"
        assert [order.status for order in orders] == ["cancelled", "cancelled"]
        assert [db.session.get(Product, product.id).stock_quantity for product in products] == [5, 5]


def test_payment_expiration_releases_reserved_stock(app, monkeypatch):
    with app.app_context():
        _customer, _sellers, payment, orders, attempt = make_checkout(
            expires_in=timedelta(minutes=-1)
        )
        category = Category(name="Payment test category", slug="payment-test-category")
        product = Product(
            category=category, name="Reserved stock", slug="reserved-stock-test",
            description="", price=Decimal("100.00"), stock_quantity=3, is_available=True,
        )
        db.session.add(product)
        db.session.flush()
        item = orders[0].items[0]
        item.product_id = product.id
        item.quantity = 2
        db.session.commit()

        assert payments.expire_pending_payments() == 1
        db.session.refresh(payment)
        db.session.refresh(attempt)
        db.session.refresh(orders[0])
        db.session.refresh(product)
        assert payment.status == "expired"
        assert attempt.status == "expired"
        assert orders[0].status == "cancelled"
        assert product.stock_quantity == 5

        monkeypatch_result = valid_gateway_result(attempt)
        silence_payment_side_effects(monkeypatch)
        monkeypatch.setattr(
            payments, "validate_transaction", lambda _validation_id: monkeypatch_result
        )
        assert payments.process_ipn(MultiDict({
            "tran_id": attempt.transaction_id,
            "status": "VALID",
            "val_id": "LATE-VALIDATION",
        }))
        db.session.refresh(payment)
        db.session.refresh(attempt)
        assert payment.status == "review_required"
        assert attempt.status == "review_required"
        assert orders[0].status == "cancelled"
        assert db.session.query(SellerLedgerEntry).count() == 0


def test_seller_payout_waits_for_delivery_return_window(app, monkeypatch):
    with app.app_context():
        _customer, sellers, payment, orders, attempt = make_checkout()
        silence_payment_side_effects(monkeypatch)
        assert post_valid_ipn(monkeypatch, attempt)
        held = payments.seller_settlement_balance(sellers[0].id)
        assert held["eligible"] == Decimal("0.00")
        assert held["held"] == Decimal("90.00")
        delivered_at = payments.utc_now() - timedelta(days=20)
        payments.make_seller_ledger_eligible(orders[0], delivered_at)
        db.session.commit()
        balance = payments.seller_settlement_balance(sellers[0].id)
        assert balance["eligible"] == Decimal("90.00")
        assert balance["held"] == Decimal("0.00")
        payout = payments.record_seller_payout(
            sellers[0], actor=None, reference="BANK-TRANSFER-001", note="Weekly settlement"
        )
        assert payout.amount == Decimal("90.00")
        balance = payments.seller_settlement_balance(sellers[0].id)
        assert balance["eligible"] == Decimal("0.00")
        assert balance["held"] == Decimal("0.00")


def test_online_checkout_starts_provider_session_and_keeps_cod_available(
    client, app, monkeypatch
):
    customer = User(email="checkout-online@example.com", role="customer")
    customer.set_password("password123")
    customer.customer_profile = CustomerProfile(
        full_name="Online Customer", phone="01234567890"
    )
    sellers = []
    products = []
    for index, price in enumerate((Decimal("25.00"), Decimal("50.00")), start=1):
        seller = User(email=f"online-seller{index}@example.com", role="seller")
        seller.set_password("password123")
        seller.seller_profile = SellerProfile(
            store_name=f"Online Seller {index}", contact_name=f"Seller {index}",
            phone="01234567890", approval_status="approved",
        )
        category = Category(name=f"Online category {index}", slug=f"online-category-{index}")
        products.append(Product(
            category=category, seller=seller, name=f"Online item {index}",
            slug=f"online-item-{index}", description="", price=price,
            stock_quantity=3, is_available=True,
        ))
        sellers.append(seller)
    setting = AppSetting(
        id=1, app_name="NexHaat", commission_rate_percent=Decimal("10.00"),
    )
    db.session.add_all([customer, setting, *sellers, *products])
    db.session.commit()

    client.application.config.update(
        SSLCOMMERZ_STORE_ID="sandbox-store",
        SSLCOMMERZ_STORE_PASSWORD="sandbox-password",
        SSLCOMMERZ_SANDBOX=True,
        PUBLIC_BASE_URL="https://shop.example.test",
        WTF_CSRF_ENABLED=False,
    )
    monkeypatch.setattr(
        payments,
        "create_hosted_session",
        lambda *_args, **_kwargs: (
            "SESSION-KEY",
            "https://sandbox.sslcommerz.com/gwprocess/v4/example",
        ),
    )
    response = client.post(
        "/auth/login",
        data={"email": customer.email, "password": "password123"},
    )
    assert response.status_code == 302
    for product in products:
        client.post(f"/cart/add/{product.id}", data={"quantity": "1"})
    checkout_page = client.get("/checkout").data
    assert b"Pay online with SSLCOMMERZ" in checkout_page
    assert b"Cash on delivery" in checkout_page
    assert b"80.00" in checkout_page

    response = client.post(
        "/checkout",
        data={
            "customer_name": "Online Customer",
            "phone": "01234567890",
            "email": customer.email,
            "city": "Dhaka",
            "address": "12 Test Street, Dhaka",
            "payment_method": "sslcommerz",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://sandbox.sslcommerz.com/")
    orders = db.session.query(Order).order_by(Order.order_number).all()
    payment = db.session.get(Payment, orders[0].payment_id)
    attempt = db.session.query(PaymentAttempt).one()
    assert len(orders) == 2
    assert all(order.payment_method == "sslcommerz" for order in orders)
    assert all(order.status == "pending" for order in orders)
    assert payment.status == "pending"
    assert payment.amount == Decimal("80.00")
    assert attempt.status == "pending"
    assert [order.commission_amount for order in orders] == [
        Decimal("2.50"), Decimal("5.00")
    ]
    assert all(order.return_window_days_snapshot == 14 for order in orders)
    assert [db.session.get(Product, product.id).stock_quantity for product in products] == [2, 2]


def test_cod_checkout_keeps_customer_and_seller_notifications(client, app, monkeypatch):
    import app.services.checkout as checkout_service

    customer = User(email="cod-notification-customer@example.com", role="customer")
    customer.set_password("password123")
    customer.customer_profile = CustomerProfile(
        full_name="COD Customer", phone="01234567890"
    )
    seller = User(email="cod-notification-seller@example.com", role="seller")
    seller.set_password("password123")
    seller.seller_profile = SellerProfile(
        store_name="COD Store", contact_name="COD Seller", phone="01234567890",
        approval_status="approved",
    )
    category = Category(name="COD notifications", slug="cod-notifications")
    product = Product(
        category=category, seller=seller, name="COD item", slug="cod-notification-item",
        description="", price=Decimal("10.00"), stock_quantity=3, is_available=True,
    )
    db.session.add_all([customer, seller, product])
    db.session.commit()
    customer_id, seller_id, product_id = customer.id, seller.id, product.id
    monkeypatch.setattr(checkout_service, "enqueue_order_emails", lambda *_args, **_kwargs: None)
    client.application.config["WTF_CSRF_ENABLED"] = False

    assert client.post(
        "/auth/login", data={"email": customer.email, "password": "password123"}
    ).status_code == 302
    client.post(f"/cart/add/{product_id}", data={"quantity": "1"})
    response = client.post(
        "/checkout",
        data={
            "customer_name": "COD Customer", "phone": "01234567890",
            "email": customer.email, "address": "12 Test Street", "payment_method": "cod",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/orders/")
    assert db.session.query(Notification).filter_by(user_id=customer_id, type="order").count() == 1
    assert db.session.query(Notification).filter_by(user_id=seller_id, type="order").count() == 1


def test_payment_expiry_cli_is_available(app):
    result = app.test_cli_runner().invoke(args=["expire-payments"])
    assert result.exit_code == 0
    assert "0 checkout(s)" in result.output


def test_live_payment_gateway_requires_https_public_url(app):
    from app.services.sslcommerz import gateway_is_configured

    with app.app_context():
        app.config.update(
            ENVIRONMENT="production",
            SSLCOMMERZ_STORE_ID="live-store",
            SSLCOMMERZ_STORE_PASSWORD="live-password",
            SSLCOMMERZ_SANDBOX=False,
            PUBLIC_BASE_URL="http://shop.example.test",
        )
        assert gateway_is_configured() is False
        app.config["PUBLIC_BASE_URL"] = "https://shop.example.test"
        assert gateway_is_configured() is True


def test_admin_reconciliation_page_and_api_show_provider_references(
    client, app, login_admin
):
    admin = User(email="payments-admin@example.com", role="admin")
    admin.set_password("unused-password")
    admin.admin_profile = AdminProfile(full_name="Payments Admin")
    payment = Payment(
        checkout_group="FB-ADMIN-PAYMENT",
        amount=Decimal("102.50"),
        currency="BDT",
        status="paid",
        bank_tran_id="BANK-RECON-001",
        validation_id="VAL-RECON-001",
        paid_at=datetime.now(UTC),
        expires_at=payments.utc_now() + timedelta(minutes=5),
    )
    attempt = PaymentAttempt(
        payment=payment,
        transaction_id="NXH-ADMIN-RECON-001",
        status="paid",
        bank_tran_id="BANK-RECON-001",
        validation_id="VAL-RECON-001",
        expires_at=payment.expires_at,
    )
    db.session.add_all([admin, payment, attempt])
    db.session.commit()

    admin_client = app.test_client()
    assert login_admin(admin_client, admin.email).status_code == 302
    page = admin_client.get("/admin/payments")
    assert page.status_code == 200
    assert b"BANK-RECON-001" in page.data
    assert b"VAL-RECON-001" in page.data

    response = admin_client.get("/api/v1/admin/payments")
    assert response.status_code == 200
    row = response.get_json()["data"][0]
    assert row["bank_tran_id"] == "BANK-RECON-001"
    assert row["validation_id"] == "VAL-RECON-001"
    assert row["attempts"][0]["bank_tran_id"] == "BANK-RECON-001"


def test_paid_online_order_does_not_queue_cash_on_delivery_email(app, monkeypatch):
    from app.services import mail as mail_service

    with app.app_context():
        app.config["ADMIN_EMAIL"] = "ops@example.test"
        queued_templates = []
        monkeypatch.setattr(
            mail_service,
            "_enqueue",
            lambda template, *_args, **_kwargs: queued_templates.append(template) or 1,
        )
        monkeypatch.setattr(mail_service, "_deliver_in_background", lambda *_args: None)
        order = Order(
            order_number="FB-PAID-EMAIL-1",
            customer_name="Paid Customer",
            phone="01234567890",
            email="paid@example.test",
            address="12 Test Street",
            total=Decimal("20.00"),
            payment_method="sslcommerz",
        )

        mail_service.enqueue_order_emails(order)

        assert queued_templates == ["admin_order"]

