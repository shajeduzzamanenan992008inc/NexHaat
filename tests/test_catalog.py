from decimal import Decimal

from app.extensions import db
from app.models import Category, Product, ProductVariant, SellerProfile, User


def add_catalog():
    category = Category(name="Pizza", slug="pizza", is_active=True)
    inactive = Category(name="Hidden", slug="hidden", is_active=False)
    db.session.add_all([category, inactive])
    db.session.flush()
    db.session.add_all(
        [
            Product(
                category=category,
                name="Garden Pizza",
                slug="garden-pizza",
                description="Fresh basil and tomato",
                price=Decimal("12.50"),
                is_available=True,
            ),
            Product(
                category=category,
                name="Unavailable Pizza",
                slug="unavailable-pizza",
                description="Not currently available",
                price=Decimal("10.00"),
                is_available=False,
            ),
            Product(
                category=inactive,
                name="Hidden Pizza",
                slug="hidden-pizza",
                description="Hidden",
                price=Decimal("10.00"),
                is_available=True,
            ),
        ]
    )
    db.session.commit()


def test_catalog_filters_inactive_and_unavailable(client, app):
    add_catalog()
    response = client.get("/menu")
    assert b"Garden Pizza" in response.data
    assert b"Unavailable Pizza" not in response.data
    assert b"Hidden Pizza" not in response.data


def test_product_detail_category_and_search(client, app):
    add_catalog()
    assert client.get("/food/garden-pizza").status_code == 200
    assert client.get("/category/pizza").status_code == 200
    response = client.get("/search?q=basil")
    assert b"Garden Pizza" in response.data
    assert client.get("/food/unavailable-pizza").status_code == 404


def test_search_is_tolerant_to_common_typo_errors(client, app):
    add_catalog()
    response = client.get("/search?q=garrden")
    assert response.status_code == 200
    assert b"Garden Pizza" in response.data


def test_store_stock_variant_and_deals_discovery(client, app):
    with app.app_context():
        category = Category(name="Discovery", slug="discovery", is_active=True)
        seller = User(email="discovery-store@example.com", role="seller")
        seller.set_password("password123")
        seller.seller_profile = SellerProfile(
            store_name="Discovery Store", contact_name="Owner", phone="01234567890",
            approval_status="approved",
        )
        db.session.add_all([category, seller])
        db.session.flush()
        item = Product(
            seller_id=seller.id, category_id=category.id, brand_name="Cedar House", name="Deal coffee",
            slug="deal-coffee", description="Discounted coffee", price=Decimal("10.00"),
            discount_price=Decimal("8.00"), stock_quantity=0, is_available=True,
        )
        item.variants.append(ProductVariant(
            sku="DEAL-LARGE", option_name="Size", option_value="Large",
            price=Decimal("8.00"), stock_quantity=3,
        ))
        db.session.add(item)
        db.session.commit()
        seller_id = seller.id

    response = client.get(
        f"/menu?seller_id={seller_id}&brand_name=Cedar+House&in_stock=1&variant_value=Large"
    )
    assert response.status_code == 200
    assert b"Deal coffee" in response.data
    assert client.get("/deals").status_code == 200
    assert b"Deal coffee" in client.get("/deals").data
    api_response = client.get(
        f"/api/v1/products?seller_id={seller_id}&brand_name=Cedar+House&in_stock=1&variant_value=Large"
    )
    assert api_response.status_code == 200
    assert b"Deal coffee" in api_response.data


def test_product_seo_metadata_and_structured_data(client, app):
    add_catalog()
    response = client.get("/food/garden-pizza")
    assert response.status_code == 200
    assert b'rel="canonical"' in response.data
    assert b'application/ld+json' in response.data
    assert b'"@type": "Product"' in response.data


def test_marketplace_filters_listing_search_price_category_and_sort(client, app):
    add_catalog()
    response = client.get("/menu?q=garden&min_price=10&max_price=13&sort=price_desc")
    assert response.status_code == 200
    assert b"Garden Pizza" in response.data
    assert b"Unavailable Pizza" not in response.data

    category = db.session.query(Category).filter_by(slug="pizza").one()
    response = client.get(
        f"/menu?category_id={category.id}&min_price=12&sort=price_asc"
    )
    assert response.status_code == 200
    assert b"Garden Pizza" in response.data

    response = client.get("/menu?min_price=25&max_price=5")
    assert response.status_code == 400


def test_recently_viewed_products_are_tracked_and_filtered(client, app):
    with app.app_context():
        category = Category(name="Recent", slug="recent", is_active=True)
        user = User(email="recent-user@example.com", role="customer")
        user.set_password("password123")
        user.customer_profile = User.__dict__.get("customer_profile") if False else None
        product_one = Product(
            category=category,
            name="Recently Seen One",
            slug="recently-seen-one",
            description="One",
            price=Decimal("12.00"),
            is_available=True,
        )
        product_two = Product(
            category=category,
            name="Recently Seen Two",
            slug="recently-seen-two",
            description="Two",
            price=Decimal("15.00"),
            is_available=True,
        )
        unavailable = Product(
            category=category,
            name="Unavailable Recent",
            slug="unavailable-recent",
            description="Hidden",
            price=Decimal("20.00"),
            is_available=False,
        )
        db.session.add_all([category, user, product_one, product_two, unavailable])
        db.session.commit()

    assert client.post("/auth/login", data={"email": "recent-user@example.com", "password": "password123"}).status_code == 302
    assert client.get("/food/recently-seen-one").status_code == 200
    assert client.get("/food/recently-seen-two").status_code == 200

    page = client.get("/").get_data(as_text=True)
    assert "Recently Seen One" in page
    assert "Recently Seen Two" in page
    assert "Unavailable Recent" not in page

    with app.app_context():
        from app.models import CustomerProfile
        user = db.session.scalar(db.select(User).where(User.email == "recent-user@example.com"))
        if not user.customer_profile:
            user.customer_profile = CustomerProfile(full_name="Recent User", phone="01234567890")
            db.session.commit()
        from app.services.recent_views import recent_products_for_user
        recent = recent_products_for_user(user)
        slugs = [product.slug for product in recent]
        assert "recently-seen-one" in slugs
        assert "recently-seen-two" in slugs
        assert "unavailable-recent" not in slugs


def test_missing_catalog_resources_return_404(client):
    assert client.get("/food/nope").status_code == 404
    assert client.get("/category/nope").status_code == 404


def test_slugs_are_unique(app):
    first = Category(name="First", slug="same")
    second = Category(name="Second", slug="same")
    with app.app_context():
        db.session.add_all([first, second])
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        else:
            raise AssertionError("duplicate category slugs must be rejected")


def test_seller_cannot_read_or_change_another_sellers_product(client, app):
    with app.app_context():
        category = Category(name="Seller scoped", slug="seller-scoped", is_active=True)
        seller_a = User(email="seller-a@example.com", role="seller")
        seller_a.set_password("password123")
        seller_a.seller_profile = SellerProfile(
            store_name="Seller A", contact_name="Owner A", phone="01234567890", approval_status="approved"
        )
        seller_b = User(email="seller-b@example.com", role="seller")
        seller_b.set_password("password123")
        seller_b.seller_profile = SellerProfile(
            store_name="Seller B", contact_name="Owner B", phone="01987654321", approval_status="approved"
        )
        db.session.add_all([category, seller_a, seller_b])
        db.session.flush()
        product = Product(
            seller_id=seller_b.id,
            category_id=category.id,
            name="Private seller product",
            slug="private-seller-product",
            description="Belongs to a different seller",
            price=Decimal("9.50"),
            stock_quantity=5,
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id

    assert client.post("/auth/login", data={"email": "seller-a@example.com", "password": "password123"}).status_code == 302
    assert client.get(f"/seller/products/{product_id}/edit").status_code == 404
    assert client.get(f"/seller/products/{product_id}/variants").status_code == 404
    assert client.post(f"/seller/products/{product_id}/archive").status_code == 404
    assert client.post(
        f"/seller/products/{product_id}/variants",
        data={"sku": "TAKEOVER", "option_name": "Size", "option_value": "Large", "stock_quantity": "50"},
    ).status_code == 404

    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.is_available is True
        assert product.stock_quantity == 5
        assert product.moderation_status == "approved"
        assert product.variants == []
