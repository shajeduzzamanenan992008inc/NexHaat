"""Development-only marketplace fixtures for the customer shopping journey.

This module exists so Phase 2 catalog, cart, checkout, order and review work can
be exercised against real Flask validation rules without inventing catalog data
in the React client or touching a production database.

Safety rules
------------
* Refuses to run in ``production`` and refuses any non-SQLite database.
* Requires an explicit confirmation flag (``python -m app.seed_dev --confirm``).
* Every record is clearly marked: the seller email ends in ``@nexhaat.test``,
  the store name says "Test Listings", and every product slug starts with
  ``dev-fixture-``.
* Products are created through the real ``Product`` model (its validators are the
  same ones used by seller/admin flows) with an already-approved moderation
  state, mirroring an admin-approved listing.
* Repeatable: products are keyed by slug and variants by SKU, so a second run
  updates rather than duplicates.
* No reviews, ratings, sales counts or popularity metrics are invented.
"""

from __future__ import annotations

import os
import secrets
import sys
from decimal import Decimal

from sqlalchemy import select

from .extensions import db
from .models import Category, Product, ProductTranslation, ProductVariant, SellerProfile, User
from .seed import seed_catalog_data

DEV_SELLER_EMAIL = "dev-seller@nexhaat.test"
DEV_SELLER_STORE_NAME = "NexHaat Dev Store (Test Listings)"
DEV_SELLER_CONTACT_NAME = "NexHaat Development Seller"
DEV_SELLER_PHONE = "+8801700000000"
DEV_SELLER_ADDRESS = "Development fixture address, Dhaka, Bangladesh"
DEV_SELLER_PASSWORD_ENV = "DEV_SEED_SELLER_PASSWORD"

DEV_PRODUCT_SLUG_PREFIX = "dev-fixture-"
# A local, obviously artificial image so no fabricated product photography is
# ever presented as a real seller photo.
DEV_PRODUCT_PLACEHOLDER_IMAGE = "/dev-fixture-placeholder.svg"

# (slug, name, category slug, brand, price, discount, stock, description, variants)
# ``variants`` is a tuple of (sku, option_name, option_value, price, stock).
DEV_PRODUCTS = (
    {
        "slug": "dev-fixture-miniket-rice-5kg",
        "name": "Miniket Rice (5 kg bag)",
        "category": "rice-grains-pasta",
        "brand": "NexHaat Test Foods",
        "price": "480.00",
        "discount": None,
        "stock": 40,
        "description": (
            "Development fixture listing. A 5 kg bag of miniket rice used to test "
            "catalog browsing, cart and checkout. Not a real seller offer."
        ),
        "translations": {"bn_BD": ("মিনিকেট চাল (৫ কেজি)", "ডেভেলপমেন্ট ফিক্সচার পণ্য।")},
    },
    {
        "slug": "dev-fixture-basmati-rice",
        "name": "Basmati Rice",
        "category": "rice-grains-pasta",
        "brand": "NexHaat Test Foods",
        "price": "210.00",
        "discount": None,
        "stock": 60,
        "description": (
            "Development fixture listing with two purchasable weight options, used "
            "to test variant selection and stock validation."
        ),
        "variants": (
            ("DEV-BASMATI-1KG", "Weight", "1 kg", "210.00", 30),
            ("DEV-BASMATI-5KG", "Weight", "5 kg", "990.00", 12),
        ),
    },
    {
        "slug": "dev-fixture-whole-wheat-atta-2kg",
        "name": "Whole Wheat Atta (2 kg)",
        "category": "rice-grains-pasta",
        "brand": "NexHaat Test Foods",
        "price": "145.00",
        "discount": None,
        "stock": 55,
        "description": "Development fixture listing for a 2 kg pack of whole wheat atta.",
    },
    {
        "slug": "dev-fixture-red-lentil-1kg",
        "name": "Red Lentil / Masoor Dal (1 kg)",
        "category": "beans-peas-lentils",
        "brand": "NexHaat Test Foods",
        "price": "165.00",
        "discount": "149.00",
        "stock": 35,
        "description": (
            "Development fixture listing with a real discounted price so the "
            "discount filter and discount display can be verified."
        ),
    },
    {
        "slug": "dev-fixture-soybean-oil-2l",
        "name": "Soybean Cooking Oil (2 L bottle)",
        "category": "cooking-oils-sauces",
        "brand": "NexHaat Test Foods",
        "price": "395.00",
        "discount": None,
        "stock": 25,
        "description": "Development fixture listing for a 2 litre bottle of soybean cooking oil.",
    },
    {
        "slug": "dev-fixture-black-tea-400g",
        "name": "Black Tea (400 g pack)",
        "category": "beverages",
        "brand": "NexHaat Test Foods",
        "price": "285.00",
        "discount": None,
        "stock": 45,
        "description": "Development fixture listing for a 400 gram pack of black tea.",
    },
    {
        "slug": "dev-fixture-instant-coffee-100g",
        "name": "Instant Coffee (100 g jar)",
        "category": "beverages",
        "brand": "NexHaat Test Foods",
        "price": "520.00",
        "discount": None,
        "stock": 0,
        "description": (
            "Development fixture listing deliberately at zero stock so the "
            "out-of-stock state and stock filter can be verified."
        ),
    },
    {
        "slug": "dev-fixture-farm-eggs-12",
        "name": "Farm Eggs (12 pcs)",
        "category": "dairy-eggs",
        "brand": "NexHaat Test Foods",
        "price": "150.00",
        "discount": None,
        "stock": 40,
        "description": "Development fixture listing for a tray of twelve farm eggs.",
    },
    {
        "slug": "dev-fixture-himsagar-mango-1kg",
        "name": "Himsagar Mango (1 kg)",
        "category": "fruits-vegetables",
        "brand": "NexHaat Test Foods",
        "price": "180.00",
        "discount": None,
        "stock": 20,
        "description": "Development fixture listing for one kilogram of Himsagar mango.",
    },
    {
        "slug": "dev-fixture-cotton-crew-neck-tshirt",
        "name": "Cotton Crew-Neck T-Shirt",
        "category": "mens-clothing",
        "brand": "NexHaat Test Apparel",
        "price": "690.00",
        "discount": "590.00",
        "stock": 24,
        "description": (
            "Development fixture apparel listing with size variants and a "
            "discounted price."
        ),
        "variants": (
            ("DEV-TSHIRT-S", "Size", "S", "690.00", 8),
            ("DEV-TSHIRT-M", "Size", "M", "690.00", 10),
            ("DEV-TSHIRT-L", "Size", "L", "690.00", 6),
        ),
    },
    {
        "slug": "dev-fixture-usb-c-cable-1m",
        "name": "USB-C Charging Cable (1 m)",
        "category": "electronics",
        "brand": "NexHaat Test Electronics",
        "price": "249.00",
        "discount": None,
        "stock": 80,
        "description": "Development fixture listing for a one metre USB-C charging cable.",
    },
    {
        "slug": "dev-fixture-power-bank-10000mah",
        "name": "10,000 mAh Power Bank",
        "category": "electronics",
        "brand": "NexHaat Test Electronics",
        "price": "1890.00",
        "discount": "1650.00",
        "stock": 12,
        "description": "Development fixture listing for a 10,000 mAh power bank.",
    },
    {
        "slug": "dev-fixture-stainless-frying-pan-24cm",
        "name": "Stainless Steel Frying Pan (24 cm)",
        "category": "home-kitchen",
        "brand": "NexHaat Test Home",
        "price": "1290.00",
        "discount": None,
        "stock": 18,
        "description": "Development fixture listing for a 24 cm stainless steel frying pan.",
    },
    {
        "slug": "dev-fixture-cotton-bath-towel",
        "name": "Cotton Bath Towel",
        "category": "home-kitchen",
        "brand": "NexHaat Test Home",
        "price": "450.00",
        "discount": None,
        "stock": 30,
        "description": "Development fixture listing for one cotton bath towel.",
    },
    {
        "slug": "dev-fixture-a5-notebook-200-pages",
        "name": "A5 Ruled Notebook (200 pages)",
        "category": "books-stationery",
        "brand": "NexHaat Test Stationery",
        "price": "180.00",
        "discount": None,
        "stock": 45,
        "description": "Development fixture listing for an A5 ruled notebook.",
    },
    {
        "slug": "dev-fixture-toothbrush-pack-of-4",
        "name": "Soft Bristle Toothbrush (pack of 4)",
        "category": "personal-care",
        "brand": "NexHaat Test Care",
        "price": "220.00",
        "discount": None,
        "stock": 55,
        "description": "Development fixture listing for a pack of four soft bristle toothbrushes.",
    },
)


class DevSeedRefused(RuntimeError):
    """Raised when development fixtures are requested in an unsafe environment."""


def _assert_safe_target(application):
    environment = str(application.config.get("ENVIRONMENT") or "").lower()
    if environment == "production":
        raise DevSeedRefused(
            "Refusing to seed development fixtures: APP_ENV is production."
        )
    if environment not in {"development", "testing"}:
        raise DevSeedRefused(
            f"Refusing to seed development fixtures in the {environment!r} environment."
        )
    database_uri = str(application.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if not database_uri.startswith("sqlite:"):
        raise DevSeedRefused(
            "Refusing to seed development fixtures: only a disposable SQLite database is allowed."
        )


def _dev_seller(password):
    """Return the approved development seller, creating it on first run."""
    user = db.session.scalar(select(User).where(User.email == DEV_SELLER_EMAIL))
    if user is not None and user.role != "seller":
        raise DevSeedRefused(
            f"{DEV_SELLER_EMAIL} already exists with role {user.role!r}; refusing to convert it."
        )
    if user is None:
        user = User(email=DEV_SELLER_EMAIL, role="seller", is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
    if user.seller_profile is None:
        db.session.add(
            SellerProfile(
                user_id=user.id,
                store_name=DEV_SELLER_STORE_NAME,
                contact_name=DEV_SELLER_CONTACT_NAME,
                phone=DEV_SELLER_PHONE,
                business_address=DEV_SELLER_ADDRESS,
                approval_status="approved",
            )
        )
        db.session.flush()
    else:
        profile = user.seller_profile
        profile.store_name = DEV_SELLER_STORE_NAME
        profile.contact_name = DEV_SELLER_CONTACT_NAME
        profile.phone = DEV_SELLER_PHONE
        profile.business_address = DEV_SELLER_ADDRESS
        profile.approval_status = "approved"
    return user


def _upsert_product(seller, category, spec, counters):
    product = db.session.scalar(select(Product).where(Product.slug == spec["slug"]))
    if product is None:
        product = Product(slug=spec["slug"], category_id=category.id, seller_id=seller.id, name=spec["name"], description=spec["description"])
        db.session.add(product)
        counters["products_created"] += 1
    else:
        counters["products_updated"] += 1

    # Assign in validator-safe order: ``price`` before ``discount_price``.
    product.name = spec["name"]
    product.description = spec["description"]
    product.category_id = category.id
    product.seller_id = seller.id
    product.brand_name = spec.get("brand")
    product.image = DEV_PRODUCT_PLACEHOLDER_IMAGE
    product.stock_quantity = spec["stock"]
    product.price = Decimal(spec["price"])
    product.discount_price = Decimal(spec["discount"]) if spec.get("discount") else None
    product.moderation_status = "approved"
    product.is_available = True
    product.is_featured = False
    product.original_locale = "en_US"

    for locale, (translated_name, translated_description) in (spec.get("translations") or {}).items():
        existing = next((item for item in product.translations if item.locale == locale), None)
        if existing is None:
            product.translations.append(
                ProductTranslation(
                    locale=locale,
                    name=translated_name,
                    description=translated_description,
                )
            )
        else:
            existing.name = translated_name
            existing.description = translated_description

    db.session.flush()

    for sku, option_name, option_value, variant_price, variant_stock in spec.get("variants") or ():
        variant = next((item for item in product.variants if item.sku == sku), None)
        if variant is None:
            variant = ProductVariant(product_id=product.id, sku=sku)
            db.session.add(variant)
            counters["variants_created"] += 1
        variant.option_name = option_name
        variant.option_value = option_value
        variant.price = Decimal(variant_price)
        variant.stock_quantity = variant_stock
        variant.is_active = True
    return product


def seed_dev_catalog(*, confirm=False, password=None):
    """Create or update the marked development fixtures. Returns a summary dict.

    Raises :class:`DevSeedRefused` unless explicitly confirmed and running
    against a disposable, non-production SQLite database.
    """
    from flask import current_app

    if not confirm:
        raise DevSeedRefused(
            "Development fixtures were not created. Re-run with --confirm to acknowledge "
            "that only a disposable development database is targeted."
        )
    _assert_safe_target(current_app)

    seller_password = password or os.getenv(DEV_SELLER_PASSWORD_ENV)
    generated_password = False
    if not seller_password:
        seller_password = secrets.token_urlsafe(18)
        generated_password = True

    counters = {
        "products_created": 0,
        "products_updated": 0,
        "variants_created": 0,
        "categories_created": seed_catalog_data(),
    }

    seller = _dev_seller(seller_password)
    for spec in DEV_PRODUCTS:
        category = db.session.scalar(select(Category).where(Category.slug == spec["category"]))
        if category is None:
            raise DevSeedRefused(
                f"Category {spec['category']!r} is missing; the curated taxonomy seed did not run."
            )
        _upsert_product(seller, category, spec, counters)

    db.session.commit()

    return {
        "seller_email": DEV_SELLER_EMAIL,
        "seller_store": DEV_SELLER_STORE_NAME,
        "seller_password_generated": generated_password,
        "seller_password": seller_password if generated_password else None,
        **counters,
        "products_total": len(DEV_PRODUCTS),
    }


def main(argv=None):
    from app import create_app

    argv = list(sys.argv[1:] if argv is None else argv)
    app = create_app()
    with app.app_context():
        summary = seed_dev_catalog(confirm="--confirm" in argv)
        print(
            "Development fixtures ready: "
            f"{summary['products_total']} test products for {summary['seller_email']}."
        )
        if summary["seller_password_generated"]:
            print(
                "A one-time seller password was generated for this run. Set "
                f"{DEV_SELLER_PASSWORD_ENV} to control it:"
            )
            print(summary["seller_password"])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
