def test_app_module_exposes_wsgi_entry():
    from app import app

    assert app is not None
    assert hasattr(app, "url_map")


def test_homepage_renders_personalized_sections_for_a_signed_in_customer(client, app):
    from datetime import datetime, timezone

    from app.extensions import db
    from app.models import AIPreferences, Category, Product, RecentViewedProduct, User

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
            user_id=user.id, product_id=viewed.id, viewed_at=datetime.now(timezone.utc),
        ))
        db.session.add(AIPreferences(
            user_id=user.id, personalized_recommendations_enabled=True,
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
    assert "Picked for you" in html
    assert "Personalized item" in html
