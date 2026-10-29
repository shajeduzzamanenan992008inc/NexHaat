"""Stage 11 discovery checks: cross-sell shelves and repeat purchase."""

from decimal import Decimal

from app.extensions import db
from app.models import (
    Category,
    CustomerCartItem,
    Order,
    OrderItem,
    Product,
    SellerProfile,
    User,
)


def csrf_off(client):
    client.application.config["WTF_CSRF_ENABLED"] = False


def make_category(name="Recommendations", slug="recommendations", active=True):
    category = Category(name=name, slug=slug, is_active=active)
    db.session.add(category)
    db.session.flush()
    return category


def make_seller(email="rec-seller@example.com"):
    seller = User(email=email, role="seller")
    seller.set_password("password123")
    seller.seller_profile = SellerProfile(
        store_name="Rec Store", contact_name="Owner", phone="01234567890",
        approval_status="approved",
    )
    db.session.add(seller)
    db.session.flush()
    return seller


def make_product(category, name, slug, *, price="10.00", stock=5, seller=None, **kwargs):
    product = Product(
        category=category,
        seller_id=seller.id if seller else None,
        name=name,
        slug=slug,
        description=f"{name} description",
        price=Decimal(price),
        stock_quantity=stock,
        **kwargs,
    )
    db.session.add(product)
    db.session.flush()
    return product


def make_customer(email="rec-customer@example.com"):
    user = User(email=email, role="customer")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    return user


def make_order(customer, order_number, *, status="delivered"):
    order = Order(
        order_number=order_number,
        user_id=customer.id,
        customer_name="Rec Customer",
        phone="01700000000",
        address="1 Test Road",
        total=Decimal("20.00"),
        status=status,
    )
    db.session.add(order)
    db.session.flush()
    return order


def add_item(order, product, quantity=1):
    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        price=product.price,
        quantity=quantity,
        subtotal=product.price * quantity,
    )
    db.session.add(item)
    db.session.flush()
    return item


def test_frequently_bought_together_uses_real_order_combinations(app):
    from app.services.recommendations import product_recommendations

    with app.app_context():
        category = make_category(slug="rec-together")
        anchor = make_product(category, "Anchor Item", "anchor-item")
        often = make_product(category, "Often Together", "often-together")
        sometimes = make_product(category, "Sometimes Together", "sometimes-together")
        cancelled_only = make_product(category, "Cancelled Only", "cancelled-only")

        for index in range(3):
            order = make_order(make_customer(f"together-{index}@example.com"), f"REC-T{index}")
            add_item(order, anchor)
            add_item(order, often, 2)
        second = make_order(make_customer("together-second@example.com"), "REC-T-SECOND")
        add_item(second, anchor)
        add_item(second, sometimes)
        cancelled = make_order(
            make_customer("together-cancelled@example.com"), "REC-T-CANCELLED", status="cancelled"
        )
        add_item(cancelled, anchor)
        add_item(cancelled, cancelled_only)
        db.session.commit()

        shelves = product_recommendations(anchor)

    together = [item.slug for item in shelves["frequently_bought_together"]]
    assert together[:2] == ["often-together", "sometimes-together"]
    assert "cancelled-only" not in together
    assert "anchor-item" not in together


def test_related_products_skip_the_anchor_and_unbuyable_items(app):
    from app.services.recommendations import product_recommendations

    with app.app_context():
        category = make_category(slug="rec-related")
        hidden_category = make_category("Hidden Related", "rec-related-hidden", active=False)
        seller = make_seller()
        anchor = make_product(category, "Anchor Related", "related-anchor", seller=seller)
        make_product(category, "Same Store", "related-same-store", seller=seller)
        make_product(category, "Sold Out", "related-sold-out", stock=0)
        make_product(category, "Pending Review", "related-pending", moderation_status="pending")
        make_product(hidden_category, "Hidden Category", "related-hidden")
        db.session.commit()

        shelves = product_recommendations(anchor)

    related = [item.slug for item in shelves["related"]]
    assert "related-same-store" in related
    assert "related-anchor" not in related
    assert "related-sold-out" not in related
    assert "related-pending" not in related
    assert "related-hidden" not in related


def test_buy_again_adds_available_items_and_clamps_to_stock(client, app):
    csrf_off(client)
    with app.app_context():
        category = make_category(slug="rec-buy-again")
        customer = make_customer("again-customer@example.com")
        keep = make_product(category, "Keep Me", "keep-me", stock=2)
        gone = make_product(category, "Gone Away", "gone-away", is_available=False)
        order = make_order(customer, "AGAIN-1")
        add_item(order, keep, 5)
        add_item(order, gone)
        db.session.commit()

    client.post("/auth/login", data={"email": "again-customer@example.com", "password": "password123"})
    response = client.post("/orders/AGAIN-1/buy-again")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")

    with app.app_context():
        rows = db.session.query(CustomerCartItem).all()
        assert len(rows) == 1
        assert rows[0].quantity == 2

    page = client.get("/cart").get_data(as_text=True)
    assert "Keep Me" in page


def test_buy_again_is_owner_scoped_and_rejects_staff(client, app):
    csrf_off(client)
    with app.app_context():
        category = make_category(slug="rec-scoped")
        owner = make_customer("again-owner@example.com")
        make_customer("again-other@example.com")
        make_seller("again-seller@example.com")
        product = make_product(category, "Scoped Item", "scoped-item")
        order = make_order(owner, "AGAIN-2")
        add_item(order, product)
        db.session.commit()

    response = client.post("/orders/AGAIN-2/buy-again")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

    client.post("/auth/login", data={"email": "again-other@example.com", "password": "password123"})
    assert client.post("/orders/AGAIN-2/buy-again").status_code == 404

    client.post("/auth/logout")
    client.post("/auth/login", data={"email": "again-seller@example.com", "password": "password123"})
    assert client.post("/orders/AGAIN-2/buy-again").status_code == 403


def test_product_recommendations_api_returns_shelves(client, app):
    with app.app_context():
        category = make_category(slug="rec-api")
        anchor = make_product(category, "Api Anchor", "api-anchor")
        make_product(category, "Api Related", "api-related")
        db.session.commit()
        anchor_id = anchor.id

    response = client.get(f"/api/v1/products/{anchor_id}/recommendations")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    slugs = [item["slug"] for item in body["data"]["related"]]
    assert slugs == ["api-related"]
    assert body["data"]["frequently_bought_together"] == []


def test_product_recommendations_api_hides_unknown_products(client, app):
    response = client.get("/api/v1/products/999999/recommendations")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"
