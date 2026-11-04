"""End-to-end customer journey over the real Flask API and development fixtures.

Covers catalog discovery, server cart mutation, disposable COD checkout, order
history/detail, review eligibility, moderation-gated publication and honestly
derived rating metrics. It never contacts a payment provider.
"""

from sqlalchemy import select

from app.extensions import db
from app.models import CustomerProfile, Order, Review, User
from app.seed_dev import DEV_SELLER_STORE_NAME, seed_dev_catalog

CUSTOMER_EMAIL = "phase2-customer@example.com"
CUSTOMER_PASSWORD = "customerpass1"


def _login_customer(client):
    client.post(
        "/auth/login",
        data={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
    )


def _create_customer():
    customer = User(email=CUSTOMER_EMAIL, role="customer", is_active=True)
    customer.set_password(CUSTOMER_PASSWORD)
    customer.customer_profile = CustomerProfile(
        full_name="Phase Two Customer", phone="01712345678"
    )
    db.session.add(customer)
    db.session.commit()
    return customer


def _catalog_item(client, slug):
    response = client.get("/api/v1/products?limit=100")
    assert response.status_code == 200
    return next(item for item in response.get_json()["data"] if item["slug"] == slug)


def test_customer_catalog_cart_cod_order_and_review_journey(app, client):
    client.application.config["WTF_CSRF_ENABLED"] = False
    seed_dev_catalog(confirm=True)
    _create_customer()
    _login_customer(client)

    # --- Catalog discovery is backend-driven ---------------------------------
    listing = client.get("/api/v1/products?limit=24&sort=price_asc&in_stock=1")
    assert listing.status_code == 200
    body = listing.get_json()
    # 15 of the 16 fixtures are in stock; the sold-out fixture is filtered out.
    assert body["pagination"]["total"] == 15
    prices = [float(item["display_price"]) for item in body["data"]]
    assert prices == sorted(prices)
    assert all(item["stock"] > 0 for item in body["data"])
    # Seller identity is the real store name, never a client placeholder.
    assert all(item["seller_name"] == DEV_SELLER_STORE_NAME for item in body["data"])
    unavailable = client.get("/api/v1/products?limit=24")
    assert unavailable.get_json()["pagination"]["total"] == 16

    search = client.get("/api/v1/products?q=Miniket")
    assert search.status_code == 200
    assert [item["slug"] for item in search.get_json()["data"]] == [
        "dev-fixture-miniket-rice-5kg"
    ]

    discounted = client.get("/api/v1/products?discount=1")
    assert discounted.status_code == 200
    discounted_slugs = {item["slug"] for item in discounted.get_json()["data"]}
    assert "dev-fixture-red-lentil-1kg" in discounted_slugs
    assert "dev-fixture-miniket-rice-5kg" not in discounted_slugs

    rice = _catalog_item(client, "dev-fixture-miniket-rice-5kg")
    detail = client.get(f"/api/v1/products/{rice['id']}")
    assert detail.status_code == 200
    assert detail.get_json()["data"]["name"] == rice["name"]
    assert detail.get_json()["data"]["seller_name"] == DEV_SELLER_STORE_NAME

    # --- Server cart: add, update, remove ------------------------------------
    added = client.post(
        "/api/v1/cart/items", json={"product_id": rice["id"], "quantity": 2}
    )
    assert added.status_code == 201
    cart = added.get_json()["data"]
    assert cart["items"][0]["quantity"] == 2
    assert cart["items"][0]["price"] == "480.00"
    assert cart["subtotal"] == "960.00"

    updated = client.patch(f"/api/v1/cart/items/{rice['id']}", json={"quantity": 3})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["items"][0]["quantity"] == 3

    # The API rejects out-of-range quantities before touching stock.
    over_limit = client.patch(f"/api/v1/cart/items/{rice['id']}", json={"quantity": 21})
    assert over_limit.status_code == 422

    sold_out = _catalog_item(client, "dev-fixture-instant-coffee-100g")
    rejected = client.post(
        "/api/v1/cart/items", json={"product_id": sold_out["id"], "quantity": 1}
    )
    assert rejected.status_code == 409
    assert rejected.get_json()["error"]["code"] == "OUT_OF_STOCK"

    # --- COD checkout --------------------------------------------------------
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "customer_name": "Phase Two Customer",
            "phone": "01712345678",
            "address": "House 12, Road 5, Dhanmondi, Dhaka",
            "city": "Dhaka",
            "payment_method": "cod",
        },
    )
    assert checkout.status_code == 201
    checkout_body = checkout.get_json()
    order_payload = checkout_body["data"]["orders"][0]
    order_number = order_payload["order_number"]
    assert order_payload["status"] == "pending"
    assert order_payload["payment_method"] == "cod"
    assert order_payload["payment_status"] is None
    assert order_payload["total"] == "1442.50"  # 3 x 480.00 + 2.50 delivery

    cart_after = client.get("/api/v1/cart")
    assert cart_after.status_code == 200
    assert cart_after.get_json()["data"]["items"] == []

    # --- Order history and detail -------------------------------------------
    history = client.get("/api/v1/orders")
    assert history.status_code == 200
    numbers = [item["order_number"] for item in history.get_json()["data"]]
    assert order_number in numbers

    order_detail = client.get(f"/api/v1/orders/{order_number}")
    assert order_detail.status_code == 200
    detail_body = order_detail.get_json()["data"]
    assert detail_body["items"][0]["quantity"] == 3
    assert detail_body["items"][0]["name"] == "Miniket Rice (5 kg bag)"

    timeline = client.get(f"/api/v1/orders/{order_number}/timeline")
    assert timeline.status_code == 200
    assert timeline.get_json()["data"]["status"] == "pending"

    # Stock was reserved by the authoritative checkout.
    restocked = client.get(f"/api/v1/products/{rice['id']}").get_json()["data"]
    assert restocked["stock"] == 37

    # --- Reviews need a delivered purchase ----------------------------------
    ineligible = client.post(
        f"/api/v1/products/{rice['id']}/reviews",
        json={"rating": 5, "comment": "Not delivered yet."},
    )
    assert ineligible.status_code == 422
    assert ineligible.get_json()["error"]["code"] == "REVIEW_NOT_ALLOWED"

    with app.app_context():
        order = db.session.scalar(select(Order).where(Order.order_number == order_number))
        order.status = "delivered"
        db.session.commit()
        product_id = rice["id"]

    created = client.post(
        f"/api/v1/products/{product_id}/reviews",
        json={"rating": 4, "comment": "Fixture rice arrived as described."},
    )
    assert created.status_code == 201
    assert created.get_json()["data"]["status"] == "pending"

    # Pending reviews are not public and must not create a rating metric.
    public_reviews = client.get(f"/api/v1/products/{product_id}/reviews")
    assert public_reviews.status_code == 200
    assert public_reviews.get_json()["data"]["reviews"] == []
    assert public_reviews.get_json()["data"]["summary"] == {"count": 0, "average": None}
    assert "rating" not in client.get("/api/v1/products?q=Miniket").get_json()["data"][0]

    # --- Approval publishes the review and the real rating ------------------
    with app.app_context():
        review = db.session.scalar(select(Review).where(Review.product_id == product_id))
        review.status = "approved"
        db.session.commit()

    published = client.get(f"/api/v1/products/{product_id}/reviews").get_json()["data"]
    assert published["summary"] == {"count": 1, "average": 4.0}
    assert len(published["reviews"]) == 1
    assert published["reviews"][0]["verified_purchase"] is True

    rated = client.get(f"/api/v1/products/{product_id}").get_json()["data"]
    assert rated["rating"] == 4.0
    assert rated["review_count"] == 1

    # A product with no approved reviews still reports no rating metric.
    unrated = client.get(
        f"/api/v1/products/{_catalog_item(client, 'dev-fixture-farm-eggs-12')['id']}"
    ).get_json()["data"]
    assert "rating" not in unrated
    assert "review_count" not in unrated
