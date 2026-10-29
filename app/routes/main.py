from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import gettext
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..i18n import SUPPORTED_LOCALES
from ..models import Review
from ..services.catalog import (
    discovery_fallback,
    get_active_brands,
    get_active_categories,
    get_active_sellers,
    get_catalog_products,
    get_category_by_slug,
    get_home_products,
    get_new_arrivals,
    get_product_by_slug,
    get_reference_food_categories,
    get_reference_foods,
    search_suggestions,
    store_name_for_product,
)
from ..services.checkout import DELIVERY_FEE
from ..services.personalization import (
    frequently_bought_with_for_user,
    personalized_products_for_user,
)
from ..services.recent_views import recent_products_for_user, record_recent_view
from ..services.recommendations import product_recommendations
from ..services.reviews import (
    ReviewError,
    create_review,
    eligible_order_id,
    helpful_counts,
    rating_histogram,
    rating_summary,
    report_review,
    reviews_for_product,
    toggle_helpful_vote,
    viewer_helpful_review_ids,
)
from ..services.stores import get_public_store, store_slug, store_summary
from ..services.wishlist import has as wishlist_has
from ..services.wishlist import saved_product_ids

main_bp = Blueprint("main", __name__)


def _price_filter(name):
    raw_value = request.args.get(name, "").strip()
    if not raw_value:
        return None
    try:
        price = Decimal(raw_value)
    except InvalidOperation:
        abort(400)
    if not price.is_finite() or price < 0 or price > Decimal("99999999.99"):
        abort(400)
    return price

def _rating_filter():
    """Read the optional minimum-rating facet, rejecting anything outside 1-5."""
    raw_value = request.args.get("min_rating", "").strip()
    if not raw_value:
        return None
    try:
        rating = int(raw_value)
    except ValueError:
        abort(400)
    if rating < 1 or rating > 5:
        abort(400)
    return rating

def _flag(name):
    """Read a 0/1 query flag, rejecting any other value instead of guessing."""
    raw_value = request.args.get(name, "").strip()
    if not raw_value:
        return False
    if raw_value not in {"0", "1"}:
        abort(400)
    return raw_value == "1"

def _paged_url(page, param="page", **overrides):
    """Rebuild the current URL for another page while keeping every active filter."""
    args = {
        key: value
        for key, value in request.args.items()
        if key != param and value not in {"", None}
    }
    args.update({key: value for key, value in overrides.items() if value not in {"", None}})
    if page and page > 1:
        args[param] = page
    return url_for(request.endpoint, **(request.view_args or {}), **args)


@main_bp.post("/language")
def set_language():
    locale = request.form.get("locale", "")
    if locale not in SUPPORTED_LOCALES:
        abort(400)

    destination = request.form.get("next", "/")
    parsed = urlsplit(destination)
    if (
        not destination.startswith("/")
        or destination.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or "\\" in destination
        or any(ord(character) < 32 for character in destination)
    ):
        destination = url_for("main.index")

    user = getattr(g, "current_user", None)
    if user:
        user.preferred_locale = locale
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash(gettext("We could not save your language preference. Please try again."), "error")
            return redirect(destination)

    session["locale"] = locale
    flash(gettext("Language preference updated."), "success")
    return redirect(destination)


@main_bp.get("/health/live")
def health_live():
    """Liveness probe that does not depend on database availability."""
    return {"status": "ok"}, 200


@main_bp.get("/health")
@main_bp.get("/health/db")
@main_bp.get("/health/ready")
def health():
    """Readiness probe for traffic that requires a working database."""
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Readiness check could not reach the database.")
        return {"status": "unavailable"}, 503
    return {"status": "ok"}, 200


@main_bp.get("/")
def index():
    user = getattr(g, "current_user", None)
    from ..services.catalog import popular_products
    return render_template(
        "home_upgraded.html",
        categories=get_active_categories(),
        products=get_home_products(),
        popular_products_func=popular_products,
        new_arrivals_func=get_new_arrivals,
        get_active_sellers_func=get_active_sellers,
        current_user_id=session.get("user_id"),
        recent_products=recent_products_for_user(user) if user and user.role == "customer" else [],
        personalized_products=personalized_products_for_user(user) if user and user.role == "customer" else [],
        frequently_bought_products_func=frequently_bought_with_for_user,
    )


@main_bp.get("/menu")
def menu():
    page = max(1, request.args.get("page", 1, type=int))
    reference_page = max(1, request.args.get("ref_page", 1, type=int))
    category_id = request.args.get("category_id", type=int)
    reference_category_id = request.args.get("ref_category_id", type=int)
    query = request.args.get("q", "").strip()[:current_app.config["MAX_SEARCH_LENGTH"]]
    min_price = _price_filter("min_price")
    max_price = _price_filter("max_price")
    seller_id = request.args.get("seller_id", type=int)
    brand_name = request.args.get("brand_name", "").strip()[:120]
    in_stock = request.args.get("in_stock") == "1"
    variant_value = request.args.get("variant_value", "").strip()[:80]
    if min_price is not None and max_price is not None and min_price > max_price:
        abort(400)
    min_rating = _rating_filter()
    discount_only = _flag("discount")
    sort = request.args.get("sort", "featured")
    if sort not in {"featured", "relevance", "newest", "price_asc", "price_desc"}:
        abort(400)
    products, pagination = get_catalog_products(
        page,
        current_app.config["CATALOG_PAGE_SIZE"],
        query=query,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        seller_id=seller_id,
        brand_name=brand_name,
        in_stock=in_stock,
        variant_value=variant_value,
        min_rating=min_rating,
        discount_only=discount_only,
    )
    fallback = (
        discovery_fallback(query) if query and not products else {"terms": [], "products": []}
    )
    reference_categories = []
    reference_foods = []
    reference_pagination = None
    if query or category_id is not None:
        if reference_category_id is not None:
            reference_categories = get_reference_food_categories()
            if reference_category_id not in {category.id for category, _ in reference_categories}:
                reference_category_id = None
        reference_foods, reference_pagination = get_reference_foods(
            reference_page,
            min(current_app.config["CATALOG_PAGE_SIZE"], 20),
            category_id=reference_category_id,
            query=query,
        )
    return render_template(
        "catalog/menu.html",
        categories=get_active_categories(),
        products=products,
        pagination=pagination,
        query=query,
        sort=sort,
        min_price=min_price,
        max_price=max_price,
        selected_category_id=category_id,
        selected_seller_id=seller_id,
        selected_brand_name=brand_name,
        brands=get_active_brands(),
        in_stock=in_stock,
        variant_value=variant_value,
        sellers=get_active_sellers(),
        selected_reference_category_id=reference_category_id,
        reference_categories=reference_categories,
        reference_foods=reference_foods,
        reference_pagination=reference_pagination,
        min_rating=min_rating,
        discount_only=discount_only,
        fallback_terms=fallback["terms"],
        fallback_products=fallback["products"],
        page_url=_paged_url,
    )


@main_bp.get("/category/<slug>")
def category(slug):
    selected = get_category_by_slug(slug)
    if selected is None:
        abort(404)
    min_price = _price_filter("min_price")
    max_price = _price_filter("max_price")
    seller_id = request.args.get("seller_id", type=int)
    brand_name = request.args.get("brand_name", "").strip()[:120]
    in_stock = request.args.get("in_stock") == "1"
    variant_value = request.args.get("variant_value", "").strip()[:80]
    if min_price is not None and max_price is not None and min_price > max_price:
        abort(400)
    min_rating = _rating_filter()
    discount_only = _flag("discount")
    sort = request.args.get("sort", "featured")
    if sort not in {"featured", "relevance", "newest", "price_asc", "price_desc"}:
        abort(400)
    products, pagination = get_catalog_products(
        max(1, request.args.get("page", 1, type=int)),
        current_app.config["CATALOG_PAGE_SIZE"],
        category_id=selected.id,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        seller_id=seller_id,
        brand_name=brand_name,
        in_stock=in_stock,
        variant_value=variant_value,
        min_rating=min_rating,
        discount_only=discount_only,
    )
    return render_template(
        "catalog/category.html",
        category=selected,
        products=products,
        pagination=pagination,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        sellers=get_active_sellers(),
        selected_seller_id=seller_id,
        selected_brand_name=brand_name,
        brands=get_active_brands(),
        in_stock=in_stock,
        variant_value=variant_value,
        min_rating=min_rating,
        discount_only=discount_only,
        page_url=_paged_url,
    )


@main_bp.get("/food/<slug>")
def food(slug):
    product = get_product_by_slug(slug)
    if product is None:
        abort(404)
    user = getattr(g, "current_user", None)
    customer = user if user is not None and user.role == "customer" else None
    if customer is not None and product.is_available:
        record_recent_view(customer, product)
    recommendations = product_recommendations(product)
    reviews = reviews_for_product(product.id)
    review_ids = [review.id for review in reviews]
    store_profile = product.seller.seller_profile if product.seller is not None else None
    return render_template(
        "catalog/food.html",
        product=product,
        reviews=reviews,
        rating=rating_summary(product.id),
        histogram=rating_histogram(product.id),
        helpful_counts=helpful_counts(review_ids),
        viewer_helpful_ids=viewer_helpful_review_ids(user, review_ids),
        store_profile=store_profile,
        store_url=(
            url_for("main.store", slug=store_slug(store_profile.store_name))
            if store_profile is not None
            else None
        ),
        delivery_fee=DELIVERY_FEE,
        is_saved=bool(customer and wishlist_has(customer, product.id)),
        saved_ids=saved_product_ids(customer) if customer else set(),
        bought_together=recommendations["frequently_bought_together"],
        related_products=recommendations["related"],
        can_review=(
            customer is not None and eligible_order_id(customer, product.id) is not None
        ),
    )


@main_bp.post("/food/<slug>/reviews")
def submit_review(slug):
    """Accept a purchase-verified product review for moderation."""
    product = get_product_by_slug(slug)
    if product is None:
        abort(404)
    user = getattr(g, "current_user", None)
    if user is None or user.role != "customer":
        flash(gettext("Sign in to review this product."), "error")
        return redirect(url_for("auth.login"))
    try:
        create_review(user, product, request.form.get("rating"), request.form.get("comment", ""))
    except ReviewError as error:
        db.session.rollback()
        flash(str(error), "error")
    else:
        flash(gettext("Thanks! Your review is waiting for moderation."), "success")
    return redirect(url_for("main.food", slug=slug))


@main_bp.post("/food/<slug>/reviews/<int:review_id>/helpful")
def toggle_review_helpful(slug, review_id):
    """Toggle the signed-in viewer's helpful vote on an approved review."""
    product = get_product_by_slug(slug)
    if product is None:
        abort(404)
    review = db.session.get(Review, review_id)
    if review is None or review.product_id != product.id:
        abort(404)
    user = getattr(g, "current_user", None)
    if user is None:
        flash(gettext("Sign in to mark a review helpful."), "error")
        return redirect(url_for("auth.login", next=url_for("main.food", slug=slug)))
    try:
        voted = toggle_helpful_vote(user, review)
    except ReviewError as error:
        db.session.rollback()
        flash(str(error), "error")
    else:
        flash(
            gettext("Thanks, that vote is recorded.") if voted else gettext("Your vote was removed."),
            "success",
        )
    return redirect(url_for("main.food", slug=slug))

@main_bp.post("/food/<slug>/reviews/<int:review_id>/report")
def report_review_route(slug, review_id):
    """Record an abuse report about one review for Admin triage."""
    product = get_product_by_slug(slug)
    if product is None:
        abort(404)
    review = db.session.get(Review, review_id)
    if review is None or review.product_id != product.id:
        abort(404)
    user = getattr(g, "current_user", None)
    if user is None:
        flash(gettext("Sign in to report a review."), "error")
        return redirect(url_for("auth.login", next=url_for("main.food", slug=slug)))
    try:
        report_review(user, review, request.form.get("reason", ""))
    except ReviewError as error:
        db.session.rollback()
        flash(str(error), "error")
    else:
        flash(gettext("Thanks. Our team will review that review."), "success")
    return redirect(url_for("main.food", slug=slug))

@main_bp.get("/store/<slug>")
def store(slug):
    """Public storefront for one approved seller, built from live listings."""
    profile = get_public_store(slug)
    if profile is None:
        abort(404)
    canonical_slug = store_slug(profile.store_name)
    if canonical_slug != slug:
        return redirect(url_for("main.store", slug=canonical_slug), code=301)
    return render_template("store.html", **store_summary(profile))

@main_bp.get("/search")
def search():
    query = request.args.get("q", "").strip()[:current_app.config["MAX_SEARCH_LENGTH"]]
    if not query:
        return redirect(url_for("main.menu"))
    page = max(1, request.args.get("page", 1, type=int))
    category_id = request.args.get("category_id", type=int)
    min_price = _price_filter("min_price")
    max_price = _price_filter("max_price")
    seller_id = request.args.get("seller_id", type=int)
    brand_name = request.args.get("brand_name", "").strip()[:120]
    in_stock = request.args.get("in_stock") == "1"
    variant_value = request.args.get("variant_value", "").strip()[:80]
    if min_price is not None and max_price is not None and min_price > max_price:
        abort(400)
    min_rating = _rating_filter()
    discount_only = _flag("discount")
    sort = request.args.get("sort", "relevance")
    if sort not in {"featured", "relevance", "newest", "price_asc", "price_desc"}:
        abort(400)
    products, pagination = get_catalog_products(
        page,
        current_app.config["CATALOG_PAGE_SIZE"],
        query=query,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        seller_id=seller_id,
        brand_name=brand_name,
        in_stock=in_stock,
        variant_value=variant_value,
        min_rating=min_rating,
        discount_only=discount_only,
    )
    fallback = (
        discovery_fallback(query) if not products else {"terms": [], "products": []}
    )
    reference_foods, reference_pagination = get_reference_foods(
        page, min(current_app.config["CATALOG_PAGE_SIZE"], 20), query=query
    )
    return render_template(
        "catalog/menu.html",
        categories=get_active_categories(),
        products=products,
        pagination=pagination,
        query=query,
        sort=sort,
        min_price=min_price,
        max_price=max_price,
        selected_category_id=category_id,
        selected_seller_id=seller_id,
        selected_brand_name=brand_name,
        brands=get_active_brands(),
        in_stock=in_stock,
        variant_value=variant_value,
        sellers=get_active_sellers(),
        selected_reference_category_id=None,
        reference_categories=[],
        reference_foods=reference_foods,
        reference_pagination=reference_pagination,
        min_rating=min_rating,
        discount_only=discount_only,
        fallback_terms=fallback["terms"],
        fallback_products=fallback["products"],
        page_url=_paged_url,
    )


@main_bp.get("/deals")
def deals():
    page = max(1, request.args.get("page", 1, type=int))
    min_price = _price_filter("min_price")
    max_price = _price_filter("max_price")
    if min_price is not None and max_price is not None and min_price > max_price:
        abort(400)
    seller_id = request.args.get("seller_id", type=int)
    brand_name = request.args.get("brand_name", "").strip()[:120]
    in_stock = request.args.get("in_stock") == "1"
    variant_value = request.args.get("variant_value", "").strip()[:80]
    sort = request.args.get("sort", "newest")
    if sort not in {"featured", "newest", "price_asc", "price_desc"}:
        abort(400)
    min_rating = _rating_filter()
    products, pagination = get_catalog_products(
        page, current_app.config["CATALOG_PAGE_SIZE"], min_price=min_price,
        max_price=max_price, sort=sort, seller_id=seller_id, in_stock=in_stock,
        brand_name=brand_name, variant_value=variant_value, deals_only=True,
        min_rating=min_rating,
    )
    return render_template(
        "catalog/deals.html", products=products, pagination=pagination,
        min_price=min_price, max_price=max_price, sort=sort,
        sellers=get_active_sellers(), selected_seller_id=seller_id,
        brands=get_active_brands(), selected_brand_name=brand_name,
        in_stock=in_stock, variant_value=variant_value,
        min_rating=min_rating, page_url=_paged_url,
    )


@main_bp.get("/api/search-suggestions")
def search_suggestions_api():
    query = request.args.get("q", "").strip()
    if len(query) > current_app.config["MAX_SEARCH_LENGTH"]:
        abort(400)
    products = search_suggestions(query)
    return jsonify([
        {
            "name": product.name,
            "slug": product.slug,
            "price": f"{product.display_price:.2f}",
            "was_price": f"{product.price:.2f}" if product.discount_price is not None else None,
            "image": product.display_image,
            "store": store_name_for_product(product),
            "category": product.category.name if product.category else None,
            "url": url_for("main.food", slug=product.slug),
        }
        for product in products
    ])
