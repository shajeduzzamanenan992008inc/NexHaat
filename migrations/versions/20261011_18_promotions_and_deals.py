"""Add promotion campaigns, seller deals, and redemption snapshots.

Revision ID: 20261011_18
Revises: 20261010_17
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261011_18"
down_revision = "20261010_17"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        with op.batch_alter_table("orders") as batch:
            if "discount_amount" not in columns:
                batch.add_column(
                    sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False, server_default="0")
                )
            if "promotion_code" not in columns:
                batch.add_column(sa.Column("promotion_code", sa.String(length=40), nullable=True))
            check_names = {constraint.get("name") for constraint in inspector.get_check_constraints("orders")}
            if "ck_order_discount_nonnegative" not in check_names:
                batch.create_check_constraint("ck_order_discount_nonnegative", "discount_amount >= 0")

    if "products" in tables:
        columns = {column["name"] for column in inspector.get_columns("products")}
        if "brand_name" not in columns:
            op.add_column("products", sa.Column("brand_name", sa.String(length=120), nullable=True))
        indexes = {index["name"] for index in inspect(bind).get_indexes("products")}
        if "ix_products_brand_name" not in indexes:
            op.create_index("ix_products_brand_name", "products", ["brand_name"])

    if "promotion_codes" not in tables:
        op.create_table(
            "promotion_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("seller_id", sa.Integer(), nullable=True),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("campaign_type", sa.String(length=20), nullable=False, server_default="coupon"),
            sa.Column("discount_type", sa.String(length=20), nullable=False, server_default="percent"),
            sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
            sa.Column("minimum_order_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("max_discount_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("usage_limit", sa.Integer(), nullable=True),
            sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("length(trim(code)) > 0", name="ck_promotion_code_nonempty"),
            sa.CheckConstraint("length(trim(name)) > 0", name="ck_promotion_name_nonempty"),
            sa.CheckConstraint("campaign_type IN ('coupon', 'seller_deal')", name="ck_promotion_campaign_type_valid"),
            sa.CheckConstraint("discount_type IN ('percent', 'fixed')", name="ck_promotion_discount_type_valid"),
            sa.CheckConstraint("discount_value >= 0", name="ck_promotion_discount_value_nonnegative"),
            sa.CheckConstraint("minimum_order_amount >= 0", name="ck_promotion_min_order_nonnegative"),
            sa.CheckConstraint("used_count >= 0", name="ck_promotion_used_count_nonnegative"),
            sa.CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="ck_promotion_usage_limit_positive"),
            sa.CheckConstraint("max_discount_amount IS NULL OR max_discount_amount >= 0", name="ck_promotion_max_discount_nonnegative"),
            sa.CheckConstraint("discount_type != 'percent' OR discount_value <= 100", name="ck_promotion_percent_max_100"),
            sa.CheckConstraint("expires_at IS NULL OR expires_at > starts_at", name="ck_promotion_dates_ordered"),
            sa.CheckConstraint("campaign_type != 'seller_deal' OR seller_id IS NOT NULL", name="ck_seller_deal_has_owner"),
            sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uq_promotion_codes_code"),
        )
        op.create_index("ix_promotion_codes_seller_id", "promotion_codes", ["seller_id"])
        op.create_index("ix_promotion_codes_is_active", "promotion_codes", ["is_active"])

    if "promotion_redemptions" not in tables:
        op.create_table(
            "promotion_redemptions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("promotion_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("checkout_group", sa.String(length=40), nullable=False),
            sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("discount_amount >= 0", name="ck_promotion_redemption_amount_nonnegative"),
            sa.ForeignKeyConstraint(["promotion_id"], ["promotion_codes.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("promotion_id", "checkout_group", name="uq_promotion_redemption_checkout"),
        )
        op.create_index("ix_promotion_redemptions_promotion_id", "promotion_redemptions", ["promotion_id"])
        op.create_index("ix_promotion_redemptions_user_id", "promotion_redemptions", ["user_id"])


def downgrade():
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "promotion_redemptions" in tables:
        op.drop_table("promotion_redemptions")
    if "promotion_codes" in tables:
        op.drop_table("promotion_codes")
    if "orders" in tables:
        columns = {column["name"] for column in inspect(bind).get_columns("orders")}
        with op.batch_alter_table("orders") as batch:
            checks = {constraint.get("name") for constraint in inspect(bind).get_check_constraints("orders")}
            if "ck_order_discount_nonnegative" in checks:
                batch.drop_constraint("ck_order_discount_nonnegative", type_="check")
            if "discount_amount" in columns:
                batch.drop_column("discount_amount")
            if "promotion_code" in columns:
                batch.drop_column("promotion_code")
    if "products" in tables:
        indexes = {index["name"] for index in inspect(bind).get_indexes("products")}
        if "ix_products_brand_name" in indexes:
            op.drop_index("ix_products_brand_name", table_name="products")
        columns = {column["name"] for column in inspect(bind).get_columns("products")}
        if "brand_name" in columns:
            op.drop_column("products", "brand_name")
