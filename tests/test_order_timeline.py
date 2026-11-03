"""Order tracking timeline: recording, idempotency, and authorization."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.api.serializers import order_event_to_dict
from app.extensions import db
from app.models import (
    Category,
    CustomerProfile,
    Order,
    OrderEvent,
    OrderItem,
    Product,
    User,
)
from app.services.order_timeline import (
    list_order_events,
    parse_estimated_delivery,
    record_status_transition,
)
from app.services.orders import transition_order


@pytest.fixture()
def seller(app):
    with app.app_context():
        user = User(email=f"seller-{uuid4().hex[:8]}@example.com", role="seller")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def customer(app):
    with app.app_context():
        user = User(email=f"customer-{uuid4().hex[:8]}@example.com", role="customer")
        user.set_password("password123")
        user.customer_profile = CustomerProfile(full_name="Timeline Customer", phone="01234567890")
        db.session.add(user)
        db.session.commit()
        return user.id


def make_order(*, seller_id=None, user_id=None, status="pending", payment_method="cod",
               stock=10, quantity=2):
    category = Category(name="Timeline", slug=f"timeline-{uuid4().hex[:8]}")
    product = Product(
        category=category,
        name="Timeline Item",
        slug=f"timeline-item-{uuid4().hex[:8]}",
        description="Timeline test item",
        price=Decimal("10.00"),
        stock_quantity=stock,
        is_available=True,
        seller_id=seller_id,
    )
    order = Order(
        order_number=f"TL-{uuid4().hex[:10]}",
        user_id=user_id,
        seller_id=seller_id,
        customer_name="Timeline Customer",
        phone="01234567890",
        email="timeline@example.com",
        address="12 Main Street",
        total=Decimal("22.50"),
        payment_method=payment_method,
        status=status,
    )
    order.items.append(
        OrderItem(
            product_id=None,
            product_name="Timeline Item",
            price=Decimal("10.00"),
            quantity=quantity,
            subtotal=Decimal("20.00"),
        )
    )
    db.session.add(product)
    db.session.add(order)
    db.session.commit()
    return order.id, product.id


def test_transition_records_timeline_event(app, seller):
    with app.app_context():
        order_id, _ = make_order(seller_id=seller)
        order = db.session.get(Order, order_id)
        actor = db.session.get(User, seller)

        assert transition_order(order, "confirmed", actor=actor)
        db.session.commit()

        events = list_order_events(order_id)
        assert len(events) == 1
        assert events[0].event_type == "status"
        assert events[0].previous_status == "pending"
        assert events[0].new_status == "confirmed"
        assert events[0].actor_role == "seller"
        assert events[0].actor_id == seller


def test_invalid_transition_records_nothing(app, seller):
    with app.app_context():
        order_id, _ = make_order(seller_id=seller)
        order = db.session.get(Order, order_id)

        assert not transition_order(order, "delivered")
        db.session.commit()
        assert list_order_events(order_id) == []


def test_repeated_transition_is_not_duplicated(app, seller):
    with app.app_context():
        order_id, _ = make_order(seller_id=seller)
        order = db.session.get(Order, order_id)

        assert transition_order(order, "confirmed")
        assert not transition_order(order, "confirmed")
        db.session.commit()
        assert len(list_order_events(order_id)) == 1

        # The dedupe key also protects a retried service-level write.
        assert record_status_transition(order, "confirmed", "preparing") is not None
        assert record_status_transition(order, "confirmed", "preparing") is None
        db.session.commit()
        assert len(list_order_events(order_id)) == 2


def test_cancellation_releases_stock_and_records_event(app, seller):
    with app.app_context():
        order_id, product_id = make_order(seller_id=seller, stock=10, quantity=2)
        order = db.session.get(Order, order_id)
        order.items[0].product_id = product_id
        db.session.commit()

        assert transition_order(order, "cancelled", actor_role="system")
        db.session.commit()
        assert db.session.get(Product, product_id).stock_quantity == 12
        events = list_order_events(order_id)
        assert events[-1].new_status == "cancelled"
        assert events[-1].actor_role == "system"


def test_timeline_is_chronological_and_keeps_tracking_data(app, seller):
    with app.app_context():
        order_id, _ = make_order(seller_id=seller)
        order = db.session.get(Order, order_id)
        actor = db.session.get(User, seller)

        assert transition_order(order, "confirmed", actor=actor)
        db.session.commit()
        estimate = datetime.now(UTC) + timedelta(days=3)
        order.events.append(
            OrderEvent(
                event_type="tracking",
                tracking_reference="NEX-123456",
                carrier="Sundarban",
                estimated_delivery_at=estimate,
                actor_role="seller",
            )
        )
        db.session.commit()

        events = list_order_events(order_id)
        assert [event.event_type for event in events] == ["status", "tracking"]
        assert events[1].tracking_reference == "NEX-123456"
        assert events[1].carrier == "Sundarban"
        assert events[1].estimated_delivery_at is not None


def test_online_order_cannot_confirm_without_payment(app, seller):
    with app.app_context():
        order_id, _ = make_order(seller_id=seller, payment_method="sslcommerz")
        order = db.session.get(Order, order_id)

        assert not transition_order(order, "confirmed")
        db.session.commit()
        assert list_order_events(order_id) == []


def test_estimated_delivery_validation():
    assert parse_estimated_delivery(None) is None
    assert parse_estimated_delivery("") is None
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    assert parse_estimated_delivery(future) is not None
    with pytest.raises(ValueError):
        parse_estimated_delivery("not-a-date")
    with pytest.raises(ValueError):
        parse_estimated_delivery((datetime.now(UTC) - timedelta(days=1)).isoformat())


def test_event_serializer_does_not_expose_actor_id(app, seller):
    with app.app_context():
        order_id, _ = make_order(seller_id=seller)
        order = db.session.get(Order, order_id)
        assert transition_order(order, "confirmed", actor=db.session.get(User, seller))
        db.session.commit()

        payload = order_event_to_dict(list_order_events(order_id)[0])
        assert "actor_id" not in payload
        assert payload["actor_role"] == "seller"
        assert payload["new_status"] == "confirmed"


def login(client, email, password="password123"):
    client.application.config["WTF_CSRF_ENABLED"] = False
    response = client.post("/auth/login", data={"email": email, "password": password})
    assert response.status_code == 302


def test_customer_timeline_api_is_owner_scoped(app, client, customer):
    with app.app_context():
        order_id, _ = make_order(user_id=customer)
        order = db.session.get(Order, order_id)
        assert transition_order(order, "confirmed", actor_role="system")
        db.session.commit()
        order_number = order.order_number
        email = db.session.get(User, customer).email

        stranger = User(email=f"stranger-{uuid4().hex[:8]}@example.com", role="customer")
        stranger.set_password("password123")
        stranger.customer_profile = CustomerProfile(full_name="Other", phone="01234567890")
        db.session.add(stranger)
        db.session.commit()
        stranger_email = stranger.email

    login(client, email)
    response = client.get(f"/api/v1/orders/{order_number}/timeline")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["order_number"] == order_number
    assert [event["new_status"] for event in data["events"]] == ["confirmed"]
    assert data["events"][0]["actor_role"] == "system"
    client.get("/auth/logout")

    login(client, stranger_email)
    assert client.get(f"/api/v1/orders/{order_number}/timeline").status_code == 404
    assert client.get("/api/v1/orders/DOES-NOT-EXIST/timeline").status_code == 404


def test_checkout_records_created_event(app, client):
    with app.app_context():
        category = Category(name="Pizza", slug=f"pizza-{uuid4().hex[:6]}")
        item = Product(
            category=category,
            name="Test Pizza",
            slug=f"test-pizza-{uuid4().hex[:6]}",
            description="A test item",
            price=Decimal("10.00"),
            stock_quantity=20,
            is_available=True,
        )
        customer = User(email=f"buyer-{uuid4().hex[:8]}@example.com", role="customer")
        customer.set_password("password123")
        customer.customer_profile = CustomerProfile(full_name="Buyer", phone="01234567890")
        db.session.add_all([item, customer])
        db.session.commit()
        item_id = item.id
        email = customer.email

    login(client, email)
    client.post(f"/cart/add/{item_id}", data={"quantity": "2"})
    response = client.post(
        "/checkout",
        data={
            "customer_name": "Cart User",
            "phone": "01234567890",
            "address": "12 Main Street",
            "email": "cart@example.com",
            "payment_method": "cod",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        order = db.session.query(Order).one()
        events = list_order_events(order.id)
        assert [event.event_type for event in events] == ["created"]
        assert events[0].new_status == "pending"
        assert events[0].actor_role == "customer"
