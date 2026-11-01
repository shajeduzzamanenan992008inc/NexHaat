"""Stage 11 discovery checks: weighted search, facets, pagination, fallbacks."""

import html
import re
from decimal import Decimal

from app.extensions import db
from app.models import (
    Category,
    Order,
    OrderItem,
    Product,
    Review,
    SellerProfile,
    User,
)


def make_category(name="Discovery", slug="discovery-hours", active=True):
    category = Category(name=name, slug=slug, is_active=active)
    db.session.add(category)
    db.session.flush()
    return category

def make_seller(email="discovery-seller@example.com", store="Discovery Store"):
    seller = User(email=email, role="seller")
    seller.set_password("password123")
    seller.seller_profile = SellerProfile(
        store_name=store, contact_name="Owner", phone="01234567890", approval_status="approved"
    )
    db.session.add(seller)
    db.session.flush()
    return seller

def make_product(category, name, slug, *, price="10.00", discount=None, stock=5, seller=None, **kwargs):
    product = Product(
        category=category,
        seller_id=seller.id if seller else None,
        name=name,
        slug=slug,
        description=kwargs.pop("description", f"{name} description"),
        price=Decimal(price),
        discount_price=Decimal(discount) if discount else None,
        stock_quantity=stock,
        **kwargs,
    )
    db.session.add(product)
    db.session.flush()
    return product

def make_customer(email):
    user = User(email=email, role="customer")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    return user

def sold_units(product, units, *, order_number, customer_email):
    """Record real delivered order lines, which drive the popularity signal.

    Order lines allow at most 20 units each, so larger totals are split across
    several real orders the same way a repeat customer would place them.
    """
    remaining = int(units)
    index = 0
    while remaining > 0:
        index += 1
        chunk = min(20, remaining)
        remaining -= chunk
        suffix = "" if index == 1 else f"-{index}"
        customer = make_customer(f"{customer_email}{suffix}")
        order = Order(
            order_number=f"{order_number}{suffix}",
            user_id=customer.id,
            customer_name="Discovery Customer",
            phone="01700000000",
            address="1 Test Road",
            total=Decimal("20.00"),
            status="delivered",
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=chunk,
                subtotal=product.price * chunk,
            )
        )
        db.session.flush()

def approve_review(product, rating, *, order_number, customer_email):
    sold_units(product, 1, order_number=order_number, customer_email=customer_email)
    order = db.session.scalar(db.select(Order).where(Order.order_number == order_number))
    customer = make_customer(f"reviewer-{customer_email}")
    db.session.add(
        Review(
            product_id=product.id,
            order_id=order.id,
            user_id=customer.id,
            rating=rating,
            author_name="Reviewer",
            status="approved",
        )
    )
    db.session.flush()

def position_of(page, needle):
    return page.index(needle)

def test_weighted_search_ranks_name_matches_above_description_matches(client, app):
    with app.app_context():
        category = make_category(slug="discovery-weights")
        make_product(category, "Saffron Honey Jar", "honey-jar", description="Nothing else here")
        make_product(category, "Plain Bread", "plain-bread", description="Sweetened with saffron syrup")
        db.session.commit()

    page = client.get("/search", query_string={"q": "saffron"}).get_data(as_text=True)
    assert "Saffron Honey Jar" in page and "Plain Bread" in page
    assert position_of(page, "Saffron Honey Jar") < position_of(page, "Plain Bread")

def test_search_matches_bangla_script_and_banglish_queries(client, app):
    with app.app_context():
        category = make_category(slug="discovery-bangla")
        make_product(category, "\u099a\u09be\u09b2", "chal-rice", description="\u0993\u099c\u09a8\u09bf\u0995 \u099a\u09be\u09b2")
        db.session.commit()

    script_page = client.get("/search", query_string={"q": "\u099a\u09be\u09b2"}).get_data(as_text=True)
    assert "chal-rice" in script_page

    banglish_page = client.get("/search", query_string={"q": "chaal"}).get_data(as_text=True)
    assert "chal-rice" in banglish_page

    typo_page = client.get("/search", query_string={"q": "chall"}).get_data(as_text=True)
    assert "chal-rice" in typo_page

def test_search_popularity_breaks_ties_between_equal_matches(client, app):
    with app.app_context():
        category = make_category(slug="discovery-popularity")
        quiet = make_product(category, "Kacchi Biryani Single", "kacchi-single")
        busy = make_product(category, "Kacchi Biryani Family", "kacchi-family")
        sold_units(busy, 40, order_number="DISC-POP-1", customer_email="popular@example.com")
        db.session.commit()
        assert quiet.id != busy.id

    page = client.get("/search", query_string={"q": "kacchi"}).get_data(as_text=True)
    assert position_of(page, "kacchi-family") < position_of(page, "kacchi-single")

def test_search_facets_filter_by_rating_and_discount(client, app):
    with app.app_context():
        category = make_category(slug="discovery-facets")
        loved = make_product(category, "Five Star Coffee", "five-star-coffee", discount="7.00")
        meh = make_product(category, "Two Star Coffee", "two-star-coffee")
        approve_review(loved, 5, order_number="DISC-RATE-1", customer_email="loved@example.com")
        approve_review(meh, 2, order_number="DISC-RATE-2", customer_email="meh@example.com")
        db.session.commit()

    rating_page = client.get("/menu", query_string={"min_rating": "4"}).get_data(as_text=True)
    assert "Five Star Coffee" in rating_page
    assert "Two Star Coffee" not in rating_page

    discount_page = client.get("/menu", query_string={"discount": "1"}).get_data(as_text=True)
    assert "Five Star Coffee" in discount_page
    assert "Two Star Coffee" not in discount_page

    assert client.get("/menu", query_string={"min_rating": "9"}).status_code == 400
    assert client.get("/menu", query_string={"min_rating": "excellent"}).status_code == 400
    assert client.get("/menu", query_string={"discount": "yes"}).status_code == 400

def link_href(page, rel):
    """Return the unescaped href of a head link such as rel="next", if present."""
    match = re.search(rf'<link rel="{rel}" href="([^"]+)"', page)
    return html.unescape(match.group(1)) if match else None

def test_pagination_links_advance_and_keep_active_filters(client, app):
    app.config["CATALOG_PAGE_SIZE"] = 2
    with app.app_context():
        category = make_category(slug="discovery-paging")
        for index in range(5):
            make_product(
                category,
                f"Paged Widget {index}",
                f"paged-widget-{index}",
                description="Pagination fixture",
                price=f"{10 + index}.00",
            )
        db.session.commit()

    first = client.get("/menu", query_string={"min_price": "10"}).get_data(as_text=True)
    next_href = link_href(first, "next")
    assert next_href and "page=2" in next_href and "min_price=10" in next_href
    assert link_href(first, "prev") is None
    assert "Paged Widget 0" in first

    followed_next = client.get(next_href).get_data(as_text=True)
    assert "Paged Widget 2" in followed_next
    assert link_href(followed_next, "prev") is not None
    assert link_href(followed_next, "next") is not None

    prev_href = link_href(followed_next, "prev")
    assert "min_price=10" in prev_href
    followed_prev = client.get(prev_href).get_data(as_text=True)
    assert "Paged Widget 0" in followed_prev

    last = client.get("/menu", query_string={"min_price": "10", "page": "3"}).get_data(as_text=True)
    assert link_href(last, "next") is None
    assert "Paged Widget 4" in last

def test_empty_search_shows_related_terms_and_popular_products(client, app):
    with app.app_context():
        category = make_category("Pantry Staples", "discovery-pantry")
        seller = make_seller(store="Pantry Store")
        popular = make_product(category, "Everyday Rice Bag", "everyday-rice-bag", seller=seller)
        make_product(category, "Quiet Lentils", "quiet-lentils", seller=seller)
        for index in range(3):
            sold_units(
                popular, 5, order_number=f"DISC-FALLBACK-{index}", customer_email=f"fallback-{index}@example.com"
            )
        db.session.commit()

    page = client.get("/search", query_string={"q": "zzzznothing"}).get_data(as_text=True)
    assert "Related searches" in page
    assert "Popular right now" in page
    assert "everyday-rice-bag" in page
    assert "Pantry Staples" in page

def test_search_suggestions_are_bounded_and_reject_oversized_queries(client, app):
    from app.services.catalog import search_suggestions

    with app.app_context():
        category = make_category("Suggestion Bounds", "suggestion-bounds")
        for index in range(12):
            make_product(category, f"Suggestion Product {index}", f"suggestion-product-{index}")
        db.session.commit()

        assert search_suggestions(["tampered query"]) == []
        assert len(search_suggestions("suggestion", limit=10_000)) == 8
        assert search_suggestions("a " * 100, limit=10_000) == []

    assert client.get("/api/search-suggestions", query_string={"q": "x" * 101}).status_code == 400
    assert client.get("/api/search-suggestions", query_string={"q": "  "}).get_json() == []


def test_search_suggestions_filter_inactive_and_unavailable_products(client, app):
    with app.app_context():
        active = make_category("Suggestion Active", "suggestion-active")
        inactive = make_category("Suggestion Inactive", "suggestion-inactive", active=False)
        make_product(active, "Eligible Suggestion", "eligible-suggestion")
        make_product(active, "Unavailable Suggestion", "unavailable-suggestion", is_available=False)
        make_product(inactive, "Hidden Suggestion", "hidden-suggestion")
        db.session.commit()

    response = client.get("/api/search-suggestions", query_string={"q": "suggestion"})
    assert response.status_code == 200
    assert [item["slug"] for item in response.get_json()] == ["eligible-suggestion"]


def test_search_suggestions_include_store_price_and_image(client, app):
    with app.app_context():
        category = make_category("Suggestion Category", "discovery-suggest")
        seller = make_seller(store="Suggestion Store")
        make_product(
            category,
            "Suggestion Coffee",
            "suggestion-coffee",
            discount="8.50",
            image="https://cdn.example.com/coffee.png",
            seller=seller,
        )
        db.session.commit()

    response = client.get("/api/search-suggestions", query_string={"q": "suggestion"})
    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    suggestion = body[0]
    assert suggestion["slug"] == "suggestion-coffee"
    assert suggestion["price"] == "8.50"
    assert suggestion["was_price"] == "10.00"
    assert suggestion["store"] == "Suggestion Store"
    assert suggestion["category"] == "Suggestion Category"
    assert suggestion["image"] == "https://cdn.example.com/coffee.png"
    assert suggestion["url"].endswith("/food/suggestion-coffee")

def test_api_listing_supports_rating_and_discount_facets(client, app):
    with app.app_context():
        category = make_category(slug="discovery-api-facets")
        loved = make_product(category, "Api Loved Coffee", "api-loved-coffee", discount="6.00")
        make_product(category, "Api Meh Coffee", "api-meh-coffee")
        approve_review(loved, 5, order_number="DISC-API-1", customer_email="api-loved@example.com")
        db.session.commit()

    response = client.get("/api/v1/products", query_string={"min_rating": "4"})
    assert response.status_code == 200
    slugs = [item["slug"] for item in response.get_json()["data"]]
    assert slugs == ["api-loved-coffee"]

    response = client.get("/api/v1/products", query_string={"discount": "1"})
    assert [item["slug"] for item in response.get_json()["data"]] == ["api-loved-coffee"]

    assert client.get("/api/v1/products", query_string={"min_rating": "8"}).status_code == 422
    assert client.get("/api/v1/products", query_string={"discount": "2"}).status_code == 422

def test_search_bounds_are_finite_and_long_queries_stay_safe(client, app):
    from app.services import catalog as catalog_service

    assert catalog_service.SEARCH_TOKEN_LIMIT <= 12
    assert catalog_service.SEARCH_CANDIDATE_DEPTH <= 500
    assert catalog_service.SEARCH_FUZZY_SCAN_DEPTH <= 500

    with app.app_context():
        category = make_category(slug="discovery-bounds")
        for index in range(4):
            make_product(category, f"Bounds Product {index}", f"bounds-product-{index}")
        db.session.commit()

    verbose_query = " ".join(f"word{index}" for index in range(40))
    response = client.get("/search", query_string={"q": verbose_query})
    assert response.status_code == 200
    assert len(catalog_service._normalize_search_tokens(verbose_query)) == catalog_service.SEARCH_TOKEN_LIMIT
