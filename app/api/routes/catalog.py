"""Paginated marketplace catalog and product-review API routes."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from sqlalchemy import select

from ...extensions import db
from ...models import Category, Product, Review
from ...security import current_session_user
from ...services.catalog import get_active_categories, get_catalog_products
from ...services.recommendations import product_recommendations
from ...services.reviews import (
    ReviewError,
    create_review,
    helpful_counts,
    open_report_counts,
    rating_summary,
    report_review,
    reviews_for_product,
    toggle_helpful_vote,
)
from ...services.stores import get_public_store, store_slug, store_summary
from ..errors import ApiError
from ..responses import created_response, paginated_response, success_response
from ..serializers import category_to_dict, product_to_dict, review_to_dict

catalog_api = Blueprint("api_catalog", __name__)


def _page_args():
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=20, type=int)
    if page is None or limit is None or page < 1 or limit < 1 or limit > 100:
        raise ApiError("Page must be positive and limit must be between 1 and 100.", "VALIDATION_ERROR", 422)
    return page, limit


def _price_arg(name):
    value = request.args.get(name, "").strip()
    if not value:
        return None
    try:
        price = Decimal(value)
    except InvalidOperation as error:
        raise ApiError(f"{name} must be a valid decimal amount.", "VALIDATION_ERROR", 422) from error
    if not price.is_finite() or price < 0 or price > Decimal("99999999.99"):
        raise ApiError(f"{name} is outside the supported range.", "VALIDATION_ERROR", 422)
    return price


def _rating_arg():
    raw_value = request.args.get("min_rating", "").strip()
    if not raw_value:
        return None
    try:
        rating = int(raw_value)
    except ValueError as error:
        raise ApiError("min_rating must be a whole number from 1 to 5.", "VALIDATION_ERROR", 422) from error
    if not 1 <= rating <= 5:
        raise ApiError("min_rating must be a whole number from 1 to 5.", "VALIDATION_ERROR", 422)
    return rating

def _flag_arg(name):
    raw_value = request.args.get(name, "0").strip()
    if raw_value not in {"0", "1"}:
        raise ApiError(f"{name} must be 0 or 1.", "VALIDATION_ERROR", 422)
    return raw_value == "1"

def _listing(category_id_override=None, *, deals_only=False):
    page, limit = _page_args()
    query = request.args.get("q", "").strip()[:100]
    category_id = (
        category_id_override
        if category_id_override is not None
        else request.args.get("category_id", type=int)
    )
    minimum = _price_arg("min_price")
    maximum = _price_arg("max_price")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ApiError("min_price cannot exceed max_price.", "VALIDATION_ERROR", 422)
    sort = request.args.get("sort", "relevance" if query else "featured")
    if sort not in {"featured", "relevance", "newest", "price_asc", "price_desc"}:
        raise ApiError("Unsupported product sort order.", "VALIDATION_ERROR", 422)
    seller_id = request.args.get("seller_id", type=int)
    raw_stock = request.args.get("in_stock", "0")
    if raw_stock not in {"0", "1"}:
        raise ApiError("in_stock must be 0 or 1.", "VALIDATION_ERROR", 422)
    variant_value = request.args.get("variant_value", "").strip()
    if len(variant_value) > 80:
        raise ApiError("variant_value is too long.", "VALIDATION_ERROR", 422)
    brand_name = request.args.get("brand_name", "").strip()
    if len(brand_name) > 120:
        raise ApiError("brand_name is too long.", "VALIDATION_ERROR", 422)
    min_rating = _rating_arg()
    discount_only = _flag_arg("discount")
    products, pagination = get_catalog_products(
        page, limit, query, category_id, minimum, maximum, sort,
        seller_id=seller_id, brand_name=brand_name, in_stock=raw_stock == "1",
        variant_value=variant_value, deals_only=deals_only,
        min_rating=min_rating, discount_only=discount_only,
    )
    return paginated_response(
        [product_to_dict(product) for product in products],
        page=pagination["page"],
        limit=limit,
        total=pagination["total"],
    )


@catalog_api.get("/products")
def list_products():
    return _listing()


@catalog_api.get("/deals")
def list_deals():
    return _listing(deals_only=True)


@catalog_api.get("/products/<int:product_id>")
def product_detail(product_id):
    product = db.session.scalar(
        select(Product)
        .join(Product.category)
        .where(
            Product.id == product_id,
            Product.is_available.is_(True),
            Product.moderation_status == "approved",
            Category.is_active.is_(True),
        )
    )
    if product is None:
        raise ApiError("Product not found.", "NOT_FOUND", 404)
    return success_response(product_to_dict(product))


@catalog_api.get("/products/<int:product_id>/recommendations")
def product_recommendation_shelf(product_id):
    """Related and frequently-bought-together products for one listing."""
    product = db.session.scalar(
        select(Product)
        .join(Product.category)
        .where(
            Product.id == product_id,
            Product.is_available.is_(True),
            Product.moderation_status == "approved",
            Category.is_active.is_(True),
        )
    )
    if product is None:
        raise ApiError("Product not found.", "NOT_FOUND", 404)
    shelves = product_recommendations(product)
    return success_response(
        {
            "frequently_bought_together": [
                product_to_dict(item) for item in shelves["frequently_bought_together"]
            ],
            "related": [product_to_dict(item) for item in shelves["related"]],
        }
    )


@catalog_api.post("/products/<int:product_id>/reviews/<int:review_id>/helpful")
def vote_review_helpful(product_id, review_id):
    """Toggle the caller's helpful vote on one approved review of this product."""
    user = current_session_user()
    if user is None:
        raise ApiError("Sign in to mark a review helpful.", "UNAUTHENTICATED", 401)
    review = db.session.scalar(
        select(Review).where(Review.id == review_id, Review.product_id == product_id)
    )
    if review is None:
        raise ApiError("Review not found.", "NOT_FOUND", 404)
    try:
        voted = toggle_helpful_vote(user, review)
    except ReviewError as error:
        raise ApiError(str(error), "REVIEW_NOT_ALLOWED", 422) from error
    return success_response({"review_id": review_id, "helpful": voted, "count": helpful_counts([review_id]).get(review_id, 0)})

@catalog_api.post("/products/<int:product_id>/reviews/<int:review_id>/report")
def report_product_review(product_id, review_id):
    """Record an abuse report about one review for Admin triage."""
    user = current_session_user()
    if user is None:
        raise ApiError("Sign in to report a review.", "UNAUTHENTICATED", 401)
    review = db.session.scalar(
        select(Review).where(Review.id == review_id, Review.product_id == product_id)
    )
    if review is None:
        raise ApiError("Review not found.", "NOT_FOUND", 404)
    payload = request.get_json(silent=True) or request.form
    try:
        report_review(user, review, payload.get("reason", ""))
    except ReviewError as error:
        raise ApiError(str(error), "REVIEW_NOT_ALLOWED", 422) from error
    return created_response({"review_id": review_id, "status": "open"}, "Report submitted.")

@catalog_api.get("/stores/<slug>")
def store_detail(slug):
    """Public storefront summary for one approved seller."""
    profile = get_public_store(slug)
    if profile is None:
        raise ApiError("Store not found.", "NOT_FOUND", 404)
    summary = store_summary(profile)
    return success_response(
        {
            "store_name": profile.store_name,
            "slug": store_slug(profile.store_name),
            "phone": profile.phone,
            "business_address": profile.business_address,
            "product_count": summary["product_count"],
            "sold_units": int(summary["sold_units"]),
            "rating": summary["rating"],
            "policies": {
                "delivery_fee": f"{summary['policies']['delivery_fee']:.2f}",
                "return_window_days": summary["policies"]["return_window_days"],
            },
            "products": [product_to_dict(product) for product in summary["products"]],
        }
    )

@catalog_api.get("/categories")
def list_categories():
    return success_response([category_to_dict(category) for category in get_active_categories()])


@catalog_api.get("/categories/<slug>")
def category_products(slug):
    category = db.session.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )
    if category is None:
        raise ApiError("Category not found.", "NOT_FOUND", 404)
    return _listing(category_id_override=category.id)


@catalog_api.get("/search")
def search_products():
    if not request.args.get("q", "").strip():
        raise ApiError("A search query is required.", "VALIDATION_ERROR", 422)
    return _listing()


@catalog_api.get("/products/<int:product_id>/reviews")
def list_product_reviews(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError("Product not found.", "NOT_FOUND", 404)
    reviews = reviews_for_product(product_id)
    review_ids = [review.id for review in reviews]
    helpful = helpful_counts(review_ids)
    reports = open_report_counts(review_ids)
    return success_response(
        {
            "product_id": product_id,
            "summary": rating_summary(product_id),
            "reviews": [
                {
                    **review_to_dict(review),
                    "helpful_count": helpful.get(review.id, 0),
                    "open_reports": reports.get(review.id, 0),
                }
                for review in reviews
            ],
        }
    )


@catalog_api.post("/products/<int:product_id>/reviews")
def submit_product_review(product_id):
    user = current_session_user()
    if user is None or user.role != "customer":
        raise ApiError("Sign in as a customer to write a review.", "UNAUTHENTICATED", 401)
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError("Product not found.", "NOT_FOUND", 404)
    payload = request.get_json(silent=True) or request.form
    try:
        review = create_review(
            user, product, payload.get("rating"), payload.get("comment", "")
        )
    except ReviewError as error:
        raise ApiError(str(error), "REVIEW_NOT_ALLOWED", 422) from error
    return created_response(review_to_dict(review), "Review submitted for moderation.")
