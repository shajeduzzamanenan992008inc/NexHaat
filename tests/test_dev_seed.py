"""Development fixture safety and honesty checks."""

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Category, Product, Review, SellerProfile, User
from app.seed_dev import (
    DEV_PRODUCT_SLUG_PREFIX,
    DEV_PRODUCTS,
    DEV_SELLER_EMAIL,
    DEV_SELLER_STORE_NAME,
    DevSeedRefused,
    seed_dev_catalog,
)


def test_dev_seed_requires_explicit_confirmation(app):
    with pytest.raises(DevSeedRefused):
        seed_dev_catalog(confirm=False)
    assert db.session.scalar(select(Product)) is None


def test_dev_seed_refuses_production(app):
    app.config["ENVIRONMENT"] = "production"
    try:
        with pytest.raises(DevSeedRefused):
            seed_dev_catalog(confirm=True)
    finally:
        app.config["ENVIRONMENT"] = "testing"
    assert db.session.scalar(select(Product)) is None


def test_dev_seed_refuses_non_sqlite_database(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://example/db"
    try:
        with pytest.raises(DevSeedRefused):
            seed_dev_catalog(confirm=True)
    finally:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    assert db.session.scalar(select(Product)) is None


def test_dev_seed_is_repeatable_without_duplicates(app):
    first = seed_dev_catalog(confirm=True)
    assert first["products_created"] == len(DEV_PRODUCTS)
    assert first["products_updated"] == 0

    second = seed_dev_catalog(confirm=True)
    assert second["products_created"] == 0
    assert second["products_updated"] == len(DEV_PRODUCTS)

    products = db.session.scalars(select(Product)).all()
    assert len(products) == len(DEV_PRODUCTS)
    assert all(product.slug.startswith(DEV_PRODUCT_SLUG_PREFIX) for product in products)
    assert all(product.moderation_status == "approved" for product in products)
    assert all(product.is_available for product in products)

    seller = db.session.scalar(select(User).where(User.email == DEV_SELLER_EMAIL))
    assert seller is not None and seller.role == "seller"
    profile = db.session.scalar(
        select(SellerProfile).where(SellerProfile.user_id == seller.id)
    )
    assert profile is not None and profile.approval_status == "approved"
    assert profile.store_name == DEV_SELLER_STORE_NAME
    assert all(product.seller_id == seller.id for product in products)


def test_dev_seed_invents_no_reviews_or_ratings(app):
    seed_dev_catalog(confirm=True)
    assert db.session.scalar(select(Review)) is None


def test_dev_seed_products_are_public_and_honest(app, client):
    seed_dev_catalog(confirm=True)

    response = client.get("/api/v1/products?limit=100")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    items = payload["data"]
    assert len(items) == len(DEV_PRODUCTS)
    assert payload["pagination"]["total"] == len(DEV_PRODUCTS)

    for item in items:
        # No approved reviews exist, so no rating metric may be invented.
        assert "rating" not in item
        assert "review_count" not in item
        assert item["display_image"] == "/dev-fixture-placeholder.svg"

    slugs = {item["slug"] for item in items}
    assert "dev-fixture-red-lentil-1kg" in slugs
    discounted = next(item for item in items if item["slug"] == "dev-fixture-red-lentil-1kg")
    assert discounted["discount_price"] == "149.00"

    out_of_stock = next(
        item for item in items if item["slug"] == "dev-fixture-instant-coffee-100g"
    )
    assert out_of_stock["stock"] == 0

    variant_product = next(item for item in items if item["slug"] == "dev-fixture-basmati-rice")
    assert len(variant_product["variants"]) == 2
    assert all(variant["stock"] > 0 for variant in variant_product["variants"])


def test_dev_seed_categories_are_curated_not_fabricated(app):
    seed_dev_catalog(confirm=True)
    categories = db.session.scalars(select(Category)).all()
    assert categories
    assert all(category.slug for category in categories)
