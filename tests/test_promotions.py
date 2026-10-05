from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    Category, CustomerProfile, Order, Product, PromotionCode, PromotionRedemption,
    SellerProfile, User,
)
from app.services.promotions import (
    PromotionError, calculate_discount_for_order, get_active_promotion,
)


def test_promotion_code_applies_percent_discount(app):
    with app.app_context():
        db.session.add(
            PromotionCode(
                code="SAVE10",
                name="Summer sale",
                description="10% off",
                discount_type="percent",
                discount_value=Decimal("10.00"),
                minimum_order_amount=Decimal("50.00"),
                is_active=True,
                starts_at=datetime.now(timezone.utc) - timedelta(days=1),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        db.session.commit()

    assert calculate_discount_for_order(Decimal("120.00"), "SAVE10") == Decimal("12.00")
    assert get_active_promotion("SAVE10").code == "SAVE10"


def test_invalid_promotion_code_is_rejected(app):
    with app.app_context():
        db.session.add(
            PromotionCode(
                code="SAVE20",
                name="Late promo",
                description="20% off",
                discount_type="percent",
                discount_value=Decimal("20.00"),
                minimum_order_amount=Decimal("100.00"),
                is_active=True,
                starts_at=datetime.now(timezone.utc) - timedelta(days=2),
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        db.session.commit()

    with pytest.raises(PromotionError):
        calculate_discount_for_order(Decimal("150.00"), "SAVE20")


def test_seller_deal_is_scoped_and_usage_limited(app):
    with app.app_context():
        seller = User(email="deal-seller@example.com", role="seller")
        seller.set_password("password123")
        db.session.add(seller)
        db.session.flush()
        db.session.add(PromotionCode(
            seller_id=seller.id,
            campaign_type="seller_deal",
            code="LOCAL15",
            name="Local store deal",
            discount_type="fixed",
            discount_value=Decimal("15.00"),
            usage_limit=1,
            starts_at=datetime.now(timezone.utc) - timedelta(days=1),
        ))
        db.session.commit()
        assert calculate_discount_for_order(Decimal("10.00"), "LOCAL15", seller_id=seller.id) == Decimal("10.00")
        with pytest.raises(PromotionError):
            calculate_discount_for_order(Decimal("10.00"), "LOCAL15", seller_id=seller.id + 1)


def test_checkout_applies_discount_and_records_redemption(client, app):
    client.application.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        customer = User(email="promo-customer@example.com", role="customer")
        customer.set_password("password123")
        customer.customer_profile = CustomerProfile(full_name="Promo Customer", phone="01234567890")
        category = Category(name="Promo food", slug="promo-food")
        product = Product(
            category=category, name="Promo meal", slug="promo-meal",
            description="Meal used for promotion checkout", price=Decimal("10.00"),
            stock_quantity=5, is_available=True,
        )
        promotion = PromotionCode(
            code="TAKE10", name="Ten percent", discount_type="percent",
            discount_value=Decimal("10.00"), minimum_order_amount=Decimal("10.00"),
            usage_limit=1, starts_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.session.add_all([customer, product, promotion])
        db.session.commit()
        product_id = product.id
        customer_email = customer.email

    login_response = client.post(
        "/auth/login", data={"email": customer_email, "password": "password123"}
    )
    assert login_response.status_code == 302
    assert client.post(f"/cart/add/{product_id}", data={"quantity": "2"}).status_code == 302
    preview = client.post("/api/v1/checkout/preview", json={"promotion_code": "TAKE10"})
    assert preview.status_code == 200
    preview_data = preview.json["data"]
    assert preview_data["promotion_discount"] == "2.00"
    assert preview_data["total"] == "20.50"
    assert preview_data["orders"][0]["discount_amount"] == "2.00"
    assert preview_data["orders"][0]["total"] == "20.50"
    response = client.post("/checkout", data={
        "customer_name": "Promo Customer",
        "phone": "01234567890",
        "address": "12 Main Street",
        "email": customer_email,
        "payment_method": "cod",
        "promotion_code": "take10",
    })
    assert response.status_code == 302

    with app.app_context():
        order = db.session.scalar(db.select(Order))
        promotion = db.session.scalar(db.select(PromotionCode).where(PromotionCode.code == "TAKE10"))
        assert order.total == Decimal("20.50")
        assert order.discount_amount == Decimal("2.00")
        assert order.promotion_code == "TAKE10"
        assert promotion.used_count == 1
        redemption = db.session.scalar(db.select(PromotionRedemption))
        assert redemption.discount_amount == Decimal("2.00")
        assert redemption.checkout_group == order.checkout_group

    assert client.post(f"/cart/add/{product_id}", data={"quantity": "1"}).status_code == 302
    rejected = client.post("/checkout", data={
        "customer_name": "Promo Customer",
        "phone": "01234567890",
        "address": "12 Main Street",
        "email": customer_email,
        "payment_method": "cod",
        "promotion_code": "TAKE10",
    }, follow_redirects=True)
    assert b"reached its usage limit" in rejected.data.lower()
    with app.app_context():
        assert db.session.query(Order).count() == 1
        assert db.session.get(Product, product_id).stock_quantity == 3


def test_admin_can_create_and_deactivate_campaign(client, app, login_admin):
    client.application.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        admin = User(email="campaign-admin@example.com", role="admin")
        admin.set_password("unused-password")
        db.session.add(admin)
        db.session.commit()

    assert login_admin(client, "campaign-admin@example.com").status_code == 302
    response = client.post("/admin/promotions", data={
        "code": "FALL10", "name": "Fall coupon", "discount_type": "percent",
        "discount_value": "10", "minimum_order_amount": "20",
        "usage_limit": "10",
    })
    assert response.status_code == 302
    with app.app_context():
        campaign = db.session.scalar(
            db.select(PromotionCode).where(PromotionCode.code == "FALL10")
        )
        campaign_id = campaign.id
        assert campaign.campaign_type == "coupon"

    response = client.post(f"/admin/promotions/{campaign_id}/toggle")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(PromotionCode, campaign_id).is_active is False


def test_seller_can_only_manage_own_deals(client, app):
    client.application.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        seller = User(email="seller-deal-owner@example.com", role="seller")
        seller.set_password("password123")
        seller.seller_profile = SellerProfile(
            store_name="Deal Store", contact_name="Owner", phone="01234567890",
            approval_status="approved",
        )
        other = User(email="other-deal-owner@example.com", role="seller")
        other.set_password("password123")
        other.seller_profile = SellerProfile(
            store_name="Other Deal Store", contact_name="Owner", phone="01987654321",
            approval_status="approved",
        )
        db.session.add_all([seller, other])
        db.session.flush()
        foreign_deal = PromotionCode(
            seller_id=other.id, campaign_type="seller_deal", code="OTHER5",
            name="Other store deal", discount_type="fixed", discount_value=Decimal("5"),
            starts_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.session.add(foreign_deal)
        db.session.commit()
        foreign_deal_id = foreign_deal.id

    assert client.post("/auth/login", data={
        "email": "seller-deal-owner@example.com", "password": "password123",
    }).status_code == 302
    response = client.post("/seller/deals", data={
        "code": "MINE5", "name": "My store deal", "discount_type": "fixed",
        "discount_value": "5", "minimum_order_amount": "0",
    })
    assert response.status_code == 302
    assert client.post(f"/seller/deals/{foreign_deal_id}/toggle").status_code == 404
    with app.app_context():
        deal = db.session.scalar(
            db.select(PromotionCode).where(PromotionCode.code == "MINE5")
        )
        assert deal.campaign_type == "seller_deal"
        assert deal.seller_id != db.session.get(PromotionCode, foreign_deal_id).seller_id


def test_migrations_apply_to_isolated_sqlite():
    with TemporaryDirectory(prefix="nexhaat-migrations-") as temporary_directory:
        database_path = Path(temporary_directory) / "migration.sqlite3"
        config_type = type(
            "FullProjectMigrationConfig",
            (TestingConfig,),
            {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
             "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"timeout": 30}}},
        )
        migration_app = create_app(config_type)
        migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
        alembic_config = Config(str(migrations_dir / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(migrations_dir))
        with migration_app.app_context():
            command.upgrade(alembic_config, "head")
            inspector = inspect(db.engine)
            assert {"promotion_codes", "promotion_redemptions"} <= set(inspector.get_table_names())
            assert {"discount_amount", "promotion_code"} <= {
                column["name"] for column in inspector.get_columns("orders")
            }
            assert "brand_name" in {
                column["name"] for column in inspector.get_columns("products")
            }
            assert "recently_viewed_products" in inspector.get_table_names()
            recent_view_indexes = {
                index["name"] for index in inspector.get_indexes("recently_viewed_products")
            }
            assert "ix_recently_viewed_user_viewed_at" in recent_view_indexes
            db.session.remove()
            db.engine.dispose()
            migration_app.extensions["migrate"].db.engine.dispose()
