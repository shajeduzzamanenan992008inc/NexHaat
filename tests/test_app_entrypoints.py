from datetime import UTC


def test_app_module_exposes_wsgi_entry():
    from app import app

    assert app is not None
    assert hasattr(app, "url_map")


def test_homepage_fresh_arrivals_are_newest_listings_not_bestsellers(client, app):
    from datetime import datetime
    from decimal import Decimal

    from app.extensions import db
    from app.models import Category, Order, OrderItem, Product, User

    with app.app_context():
        category = Category(name="Arrival Shelf", slug="arrival-shelf", is_active=True)
        customer = User(email="arrival-buyer@example.test", role="customer")
        customer.set_password("test-password")
        db.session.add_all([category, customer])
        db.session.flush()
        older = Product(
            category_id=category.id, name="Older bestseller", slug="older-bestseller",
            description="A popular older listing", price=Decimal("10.00"), stock_quantity=5,
            is_available=True, moderation_status="approved",
            created_at=datetime(2026, 1, 1),
        )
        newer = Product(
            category_id=category.id, name="Newest listing", slug="newest-listing",
            description="A recently added listing", price=Decimal("12.00"), stock_quantity=5,
            is_available=True, moderation_status="approved",
            created_at=datetime(2026, 2, 1),
        )
        db.session.add_all([older, newer])
        db.session.flush()
        order = Order(
            order_number="ARRIVAL-BESTSELLER", user_id=customer.id,
            customer_name="Arrival Buyer", phone="01700000000", address="1 Test Road",
            total=Decimal("50.00"), status="delivered",
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(
            order_id=order.id, product_id=older.id, product_name=older.name,
            price=older.price, quantity=5, subtotal=older.price * 5,
        ))
        db.session.commit()

    response = client.get("/")
    page = response.get_data(as_text=True)
    fresh_arrivals = page.split('aria-labelledby="new-arrivals-heading"', 1)[1].split(
        "<!-- CART USER GUIDE -->", 1
    )[0]
    trending = page.split('aria-labelledby="trending-heading"', 1)[1].split("</section>", 1)[0]
    assert response.status_code == 200
    assert fresh_arrivals.index("Newest listing") < fresh_arrivals.index("Older bestseller")
    assert trending.index("Older bestseller") < trending.index("Newest listing")
    assert 'aria-labelledby="picked-for-you-heading"' not in page


def test_homepage_renders_personalized_sections_for_a_signed_in_customer(client, app):
    from datetime import datetime

    from app.extensions import db
    from app.models import Category, Product, RecentViewedProduct, User

    with app.app_context():
        user = User(email="homepage-smoke@example.test", role="customer")
        user.set_password("test-password")
        category = Category(name="Homepage", slug="homepage-smoke", is_active=True)
        db.session.add_all([user, category])
        db.session.flush()
        viewed = Product(
            category_id=category.id, name="Recently viewed item", slug="homepage-viewed-item",
            description="Homepage smoke item", price=10, stock_quantity=5,
            is_available=True, moderation_status="approved",
        )
        recommended = Product(
            category_id=category.id, name="Personalized item", slug="homepage-recommended-item",
            description="Homepage smoke item", price=12, stock_quantity=5,
            is_available=True, moderation_status="approved",
        )
        db.session.add_all([viewed, recommended])
        db.session.flush()
        db.session.add(RecentViewedProduct(
            user_id=user.id, product_id=viewed.id, viewed_at=datetime.now(UTC),
        ))
        db.session.commit()
        user_id, auth_version = user.id, user.auth_version

    with client.session_transaction() as browser_session:
        browser_session["user_id"] = user_id
        browser_session["auth_version"] = auth_version

    response = client.get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Recently viewed" in html
    assert "Recently viewed item" in html
    personalized = html.split('aria-labelledby="picked-for-you-heading"', 1)[1].split(
        "</section>", 1
    )[0]
    assert "Picked for you" in html
    assert "Personalized item" in personalized
    assert "Recently viewed item" not in personalized


def test_personalized_recommendations_are_user_scoped_and_publicly_eligible(app):
    from datetime import datetime, timedelta
    from decimal import Decimal

    from app.extensions import db
    from app.models import Category, Product, RecentViewedProduct, User
    from app.services.personalization import personalized_products_for_user

    with app.app_context():
        category_a = Category(name="Interest A", slug="interest-a", is_active=True)
        category_b = Category(name="Interest B", slug="interest-b", is_active=True)
        hidden_category = Category(name="Hidden Interest", slug="hidden-interest", is_active=False)
        user_a = User(email="personalization-a@example.test", role="customer")
        user_a.set_password("test-password")
        user_b = User(email="personalization-b@example.test", role="customer")
        user_b.set_password("test-password")
        db.session.add_all([category_a, category_b, hidden_category, user_a, user_b])
        db.session.flush()

        def product(category, name, slug, **overrides):
            values = {
                "category_id": category.id,
                "name": name,
                "slug": slug,
                "description": name,
                "price": Decimal("10.00"),
                "stock_quantity": 5,
                "is_available": True,
                "moderation_status": "approved",
            }
            values.update(overrides)
            return Product(**values)

        viewed_a = product(category_a, "Viewed A", "viewed-a")
        viewed_b = product(category_b, "Viewed B", "viewed-b")
        recommend_a = product(category_a, "Recommendation A", "recommend-a")
        recommend_b = product(category_b, "Recommendation B", "recommend-b")
        hidden = product(hidden_category, "Hidden Category Product", "hidden-category-product")
        sold_out = product(category_a, "Sold Out Product", "sold-out-product", stock_quantity=0)
        pending = product(category_a, "Pending Product", "pending-product", moderation_status="pending")
        db.session.add_all([viewed_a, viewed_b, recommend_a, recommend_b, hidden, sold_out, pending])
        db.session.flush()
        now = datetime.now(UTC)
        db.session.add_all([
            RecentViewedProduct(user_id=user_a.id, product_id=viewed_a.id, viewed_at=now),
            RecentViewedProduct(
                user_id=user_b.id,
                product_id=viewed_b.id,
                viewed_at=now - timedelta(seconds=1),
            ),
        ])
        db.session.commit()

        results_a = personalized_products_for_user(user_a, limit=12)
        results_b = personalized_products_for_user(user_b, limit=12)

    assert results_a[0].slug == "recommend-a"
    assert results_b[0].slug == "recommend-b"
    result_slugs = {item.slug for item in results_a + results_b}
    assert "hidden-category-product" not in result_slugs
    assert "sold-out-product" not in result_slugs
    assert "pending-product" not in result_slugs


def test_homepage_recently_viewed_hides_products_in_inactive_categories(client, app):
    from datetime import UTC, datetime
    from decimal import Decimal

    from app.extensions import db
    from app.models import Category, Product, RecentViewedProduct, User

    with app.app_context():
        category = Category(name="Deactivated category", slug="deactivated-category", is_active=False)
        user = User(email="recent-inactive@example.test", role="customer")
        user.set_password("test-password")
        db.session.add_all([category, user])
        db.session.flush()
        product = Product(
            category_id=category.id,
            name="No longer public",
            slug="no-longer-public",
            description="Hidden after category deactivation",
            price=Decimal("10.00"),
            stock_quantity=2,
            is_available=True,
            moderation_status="approved",
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(RecentViewedProduct(
            user_id=user.id, product_id=product.id, viewed_at=datetime.now(UTC),
        ))
        db.session.commit()
        identity = user.id, user.auth_version

    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = identity

    response = client.get("/")
    assert response.status_code == 200
    assert 'aria-labelledby="recently-viewed-home-heading"' not in response.get_data(as_text=True)


def test_personalized_homepage_hides_empty_recommendation_section(client, app):
    from decimal import Decimal

    from app.extensions import db
    from app.models import Category, Product, User

    with app.app_context():
        user = User(email="personalization-empty@example.test", role="customer")
        user.set_password("test-password")
        category = Category(name="Empty Picks", slug="empty-picks", is_active=True)
        product = Product(
            category=category,
            name="Unavailable pick",
            slug="unavailable-pick",
            description="Not for sale",
            price=Decimal("10.00"),
            stock_quantity=0,
            is_available=True,
            moderation_status="approved",
        )
        db.session.add_all([user, category, product])
        db.session.commit()
        identity = user.id, user.auth_version

    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = identity

    page = client.get("/").get_data(as_text=True)
    assert 'aria-labelledby="picked-for-you-heading"' not in page
