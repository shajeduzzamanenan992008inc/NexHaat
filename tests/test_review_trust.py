"""Stage 11 trust checks: review helpful votes, abuse reports, and store pages."""

from decimal import Decimal

from app.extensions import db
from app.models import (
    AuditEvent,
    Category,
    Product,
    Review,
    ReviewHelpfulVote,
    ReviewReport,
    SellerProfile,
    User,
)


def make_category(name="Trust", slug="trust-category", active=True):
    category = Category(name=name, slug=slug, is_active=active)
    db.session.add(category)
    db.session.flush()
    return category

def make_seller(email="trust-seller@example.com", store="Trusted Store", approved=True):
    seller = User(email=email, role="seller")
    seller.set_password("password123")
    seller.seller_profile = SellerProfile(
        store_name=store,
        contact_name="Owner",
        phone="01234567890",
        business_address="12 Market Road, Dhaka",
        approval_status="approved" if approved else "pending",
    )
    db.session.add(seller)
    db.session.flush()
    return seller

def make_product(category, name, slug, *, seller=None, stock=5, available=True, price="10.00"):
    product = Product(
        category=category,
        seller_id=seller.id if seller else None,
        name=name,
        slug=slug,
        description=f"{name} description",
        price=Decimal(price),
        stock_quantity=stock,
        is_available=available,
    )
    db.session.add(product)
    db.session.flush()
    return product

def make_customer(email, password="password123"):
    user = User(email=email, role="customer")
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user

def add_review(product, *, rating=5, author=None, comment="Solid product", status="approved"):
    review = Review(
        product_id=product.id,
        user_id=author.id if author else None,
        rating=rating,
        comment=comment,
        author_name=(author.email if author else "Trusted Reviewer"),
        status=status,
    )
    db.session.add(review)
    db.session.flush()
    return review

def sign_in(client, email, password="password123"):
    return client.post("/auth/login", data={"email": email, "password": password})

def test_helpful_vote_toggles_once_per_account(client, app):
    with app.app_context():
        category = make_category(slug="trust-helpful")
        product = make_product(category, "Helpful Product", "helpful-product")
        review = add_review(product)
        make_customer("helpful-voter@example.com")
        db.session.commit()
        review_id = review.id

    sign_in(client, "helpful-voter@example.com")
    first = client.post(f"/food/helpful-product/reviews/{review_id}/helpful")
    assert first.status_code == 302
    with app.app_context():
        assert db.session.query(ReviewHelpfulVote).count() == 1

    page = client.get("/food/helpful-product").get_data(as_text=True)
    assert "Helpful (1)" in page

    client.post(f"/food/helpful-product/reviews/{review_id}/helpful")
    with app.app_context():
        assert db.session.query(ReviewHelpfulVote).count() == 0

def test_review_author_cannot_vote_on_their_own_review(client, app):
    with app.app_context():
        category = make_category(slug="trust-author")
        product = make_product(category, "Author Product", "author-product")
        author = make_customer("author@example.com")
        review = add_review(product, author=author)
        db.session.commit()
        review_id = review.id

    sign_in(client, "author@example.com")
    response = client.post(f"/food/author-product/reviews/{review_id}/helpful")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.query(ReviewHelpfulVote).count() == 0

def test_report_review_fills_the_admin_queue_and_can_be_resolved(client, app, login_admin):
    with app.app_context():
        category = make_category(slug="trust-report")
        product = make_product(category, "Reported Product", "reported-product")
        review = add_review(product, comment="Spam link please delete")
        make_customer("reporter@example.com")
        admin = User(email="trust-admin@example.com", role="admin")
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()
        review_id = review.id

    sign_in(client, "reporter@example.com")
    response = client.post(
        f"/food/reported-product/reviews/{review_id}/report",
        data={"reason": "This review is advertising a scam website."},
    )
    assert response.status_code == 302
    with app.app_context():
        report = db.session.query(ReviewReport).one()
        assert report.status == "open"
        report_id = report.id

    login_admin(client, "trust-admin@example.com")
    dashboard = client.get("/admin").get_data(as_text=True)
    assert "Review reports awaiting triage" in dashboard
    assert "advertising a scam website" in dashboard

    resolved = client.post(
        f"/admin/review-reports/{report_id}/resolve", data={"decision": "reviewed"}
    )
    assert resolved.status_code == 302
    with app.app_context():
        report = db.session.get(ReviewReport, report_id)
        assert report.status == "reviewed"
        assert report.resolved_at is not None
        assert db.session.query(AuditEvent).filter_by(action="review_report.resolve").count() == 1

def test_reports_require_a_reason_and_stay_unique_per_reporter(client, app):
    with app.app_context():
        category = make_category(slug="trust-report-reason")
        product = make_product(category, "Reason Product", "reason-product")
        review = add_review(product)
        make_customer("reason-reporter@example.com")
        db.session.commit()
        review_id = review.id

    sign_in(client, "reason-reporter@example.com")
    client.post(f"/food/reason-product/reviews/{review_id}/report", data={"reason": "bad"})
    with app.app_context():
        assert db.session.query(ReviewReport).count() == 0

    client.post(
        f"/food/reason-product/reviews/{review_id}/report",
        data={"reason": "The review contains abusive language."},
    )
    client.post(
        f"/food/reason-product/reviews/{review_id}/report",
        data={"reason": "The review contains abusive language."},
    )
    with app.app_context():
        assert db.session.query(ReviewReport).count() == 1

def test_product_page_renders_rating_histogram(client, app):
    with app.app_context():
        category = make_category(slug="trust-histogram")
        product = make_product(category, "Histogram Product", "histogram-product")
        add_review(product, rating=5, comment="Excellent")
        add_review(product, rating=5, comment="Also excellent")
        add_review(product, rating=3, comment="Average")
        db.session.commit()

    page = client.get("/food/histogram-product").get_data(as_text=True)
    assert "Rating breakdown" in page
    assert "2 review" in page

def test_store_page_lists_public_listings_only(client, app):
    with app.app_context():
        category = make_category(slug="trust-store")
        seller = make_seller(store="Neighbourhood Grocer")
        make_product(category, "Store Rice", "store-rice", seller=seller)
        make_product(category, "Store Oil", "store-oil", seller=seller)
        make_product(category, "Hidden Store Item", "hidden-store-item", seller=seller, available=False)
        db.session.commit()
        slug = "neighbourhood-grocer"

    page = client.get(f"/store/{slug}")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Neighbourhood Grocer" in body
    assert "store-rice" in body and "store-oil" in body
    assert "hidden-store-item" not in body
    assert "application/ld+json" in body
    assert 'rel="canonical"' in body
    assert "2.50" in body

    assert client.get("/store/nope-not-a-store").status_code == 404
    redirect_response = client.get("/store/Neighbourhood%20Grocer")
    assert redirect_response.status_code == 301
    assert redirect_response.headers["Location"].endswith(f"/store/{slug}")

def test_store_page_hides_unapproved_sellers(client, app):
    with app.app_context():
        category = make_category(slug="trust-store-pending")
        pending = make_seller(email="pending-store@example.com", store="Pending Store", approved=False)
        make_product(category, "Pending Item", "pending-item", seller=pending)
        db.session.commit()

    assert client.get("/store/pending-store").status_code == 404

def test_store_api_returns_summary_and_policies(client, app):
    with app.app_context():
        category = make_category(slug="trust-store-api")
        seller = make_seller(email="api-store@example.com", store="API Store")
        make_product(category, "Api Store Item", "api-store-item", seller=seller)
        db.session.commit()

    response = client.get("/api/v1/stores/api-store")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["store_name"] == "API Store"
    assert data["product_count"] == 1
    assert data["policies"]["delivery_fee"] == "2.50"
    assert data["products"][0]["slug"] == "api-store-item"

def test_helpful_vote_api_requires_login_and_toggles(client, app):
    with app.app_context():
        category = make_category(slug="trust-helpful-api")
        product = make_product(category, "Helpful Api Product", "helpful-api-product")
        review = add_review(product)
        make_customer("helpful-api-voter@example.com")
        db.session.commit()
        review_id = review.id

    anonymous = client.post(f"/api/v1/products/1/reviews/{review_id}/helpful")
    assert anonymous.status_code == 401

    with app.app_context():
        product_id = db.session.scalar(db.select(Product.id).where(Product.slug == "helpful-api-product"))

    sign_in(client, "helpful-api-voter@example.com")
    voted = client.post(f"/api/v1/products/{product_id}/reviews/{review_id}/helpful")
    assert voted.status_code == 200
    assert voted.get_json()["data"] == {"review_id": review_id, "helpful": True, "count": 1}
    listed = client.get(f"/api/v1/products/{product_id}/reviews").get_json()["data"]["reviews"]
    assert next(item for item in listed if item["id"] == review_id)["viewer_helpful"] is True

    removed = client.post(f"/api/v1/products/{product_id}/reviews/{review_id}/helpful")
    assert removed.get_json()["data"]["helpful"] is False
    listed = client.get(f"/api/v1/products/{product_id}/reviews").get_json()["data"]["reviews"]
    assert next(item for item in listed if item["id"] == review_id)["viewer_helpful"] is False
