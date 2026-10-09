from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import re
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_babel import gettext
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..i18n import SUPPORTED_LOCALES
from ..models import Product

from ..services.catalog import (
    get_active_categories,
    get_active_brands,
    get_active_sellers,
    get_category_by_slug,
    get_catalog_products,
    get_home_products,
    get_product_by_slug,
    get_reference_food_categories,
    get_reference_foods,
    search_suggestions,
)
from ..services.recent_views import recent_products_for_user, record_recent_view
from ..services.personalization import personalized_products_for_user, frequently_bought_with_for_user
from ..services.reviews import (
    ReviewError,
    create_review,
    eligible_order_id,
    rating_summary,
    reviews_for_product,
)
from ..services.wishlist import has as wishlist_has


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
    return render_template(
        "home.html",
        categories=get_active_categories(),
        products=get_home_products(),
        current_user_id=session.get("user_id"),
        recent_products=recent_products_for_user(user) if user and user.role == "customer" else [],
        personalized_products=personalized_products_for_user(user) if user and user.role == "customer" else [],
        frequently_bought_products=frequently_bought_with_for_user(user) if user and user.role == "customer" else [],
    )


def _menu_response(*, page, reference_page, category_id, reference_category_id, query, min_price, max_price, seller_id, brand_name, in_stock, variant_value, deals_only, sort):
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
        deals_only=deals_only,
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
        deals_only=deals_only,
    )


def _search_routes_to_ai(query):
    term = (query or "").strip()
    if not term:
        return False
    if any(ord(character) > 127 for character in term):
        return False
    if " " in term or "-" in term:
        return True
    product_names = [
        name for name in db.session.scalars(
            select(Product.name).where(
                Product.is_available.is_(True),
                Product.moderation_status == "approved",
            )
        ).all() if name
    ]
    if product_names:
        lowered = term.lower()
        catalog_terms = {
            token
            for name in product_names
            for token in re.findall(r"[a-z0-9]+", name.lower())
        }
        if any(SequenceMatcher(None, lowered, token).ratio() >= 0.78 for token in catalog_terms):
            return False
    return True


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
    deals_only = request.args.get("deals_only") == "1"
    if min_price is not None and max_price is not None and min_price > max_price:
        abort(400)
    sort = request.args.get("sort", "newest" if deals_only else "featured")
    allowed_sorts = {"featured", "relevance", "newest", "price_asc", "price_desc"}
    if deals_only:
        allowed_sorts = {"featured", "newest", "price_asc", "price_desc"}
    if sort not in allowed_sorts:
        abort(400)
    return _menu_response(
        page=page,
        reference_page=reference_page,
        category_id=category_id,
        reference_category_id=reference_category_id,
        query=query,
        min_price=min_price,
        max_price=max_price,
        seller_id=seller_id,
        brand_name=brand_name,
        in_stock=in_stock,
        variant_value=variant_value,
        deals_only=deals_only,
        sort=sort,
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
    )


@main_bp.get("/food/<slug>")
def food(slug):
    product = get_product_by_slug(slug)
    if product is None:
        abort(404)
    user = getattr(g, "current_user", None)
    if user is not None and user.role == "customer" and product.is_available:
        record_recent_view(user, product)
    from ..models import AIProductPriceAlert
    from ..services.ai_price_alerts import observed_price_history
    price_history = (observed_price_history(product.id)
                     if product.moderation_status == "approved" and product.is_available else [])
    active_price_alert = (db.session.scalar(select(AIProductPriceAlert).where(
        AIProductPriceAlert.user_id == user.id,
        AIProductPriceAlert.product_id == product.id,
        AIProductPriceAlert.active.is_(True),
    )) if user is not None and user.role == "customer" else None)
    return render_template(
        "catalog/food.html",
        product=product,
        price_history=price_history,
        active_price_alert=active_price_alert,
        reviews=reviews_for_product(product.id),
        rating=rating_summary(product.id),
        is_saved=bool(user and user.role == "customer" and wishlist_has(user, product.id)),
        can_review=(
            user is not None
            and user.role == "customer"
            and eligible_order_id(user, product.id) is not None
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


@main_bp.get("/search")
def search():
    query = request.args.get("q", "").strip()[:current_app.config["MAX_SEARCH_LENGTH"]]
    if not query:
        return redirect(url_for("main.menu"))
    if _search_routes_to_ai(query):
        return redirect(url_for("ai.index", q=query))
    return _menu_response(
        page=max(1, request.args.get("page", 1, type=int)),
        reference_page=max(1, request.args.get("ref_page", 1, type=int)),
        category_id=request.args.get("category_id", type=int),
        reference_category_id=request.args.get("ref_category_id", type=int),
        query=query,
        min_price=_price_filter("min_price"),
        max_price=_price_filter("max_price"),
        seller_id=request.args.get("seller_id", type=int),
        brand_name=request.args.get("brand_name", "").strip()[:120],
        in_stock=request.args.get("in_stock") == "1",
        variant_value=request.args.get("variant_value", "").strip()[:80],
        deals_only=request.args.get("deals_only") == "1",
        sort=request.args.get("sort", "featured"),
    )


@main_bp.get("/deals")
def deals():
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
    sort = request.args.get("sort", "newest")
    if min_price is not None and max_price is not None and min_price > max_price:
        abort(400)
    allowed_sorts = {"featured", "newest", "price_asc", "price_desc"}
    if sort not in allowed_sorts:
        abort(400)
    return _menu_response(
        page=page,
        reference_page=reference_page,
        category_id=category_id,
        reference_category_id=reference_category_id,
        query=query,
        min_price=min_price,
        max_price=max_price,
        seller_id=seller_id,
        brand_name=brand_name,
        in_stock=in_stock,
        variant_value=variant_value,
        deals_only=True,
        sort=sort,
    )


@main_bp.get("/api/search-suggestions")
def search_suggestions_api():
    query = (request.args.get("q", "") or "").strip()
    products = search_suggestions(query)
    if products:
        return jsonify([
            {"name": product.name, "slug": product.slug, "price": f"{product.display_price:.2f}"}
            for product in products
        ])
    if len(query) >= 2:
        return jsonify([
            {"name": f"Search for \"{query}\"", "slug": "", "price": "AI search", "is_ai_fallback": True}
        ])
    return jsonify([])
