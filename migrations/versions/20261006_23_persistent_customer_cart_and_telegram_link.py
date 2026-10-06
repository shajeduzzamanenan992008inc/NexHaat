"""Add persistent customer carts and secure Telegram account links.

Revision ID: 20261006_23
Revises: 20261006_22
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261006_23"
down_revision = "20261006_22"
branch_labels = None
depends_on = None


def _create_table_if_missing(name, *columns, **kwargs):
    if not inspect(op.get_bind()).has_table(name):
        op.create_table(name, *columns, **kwargs)


def _create_index_if_missing(name, table, columns):
    existing = {item["name"] for item in inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def upgrade():
    _create_table_if_missing(
        "telegram_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
        sa.UniqueConstraint("user_id"),
    )
    _create_table_if_missing(
        "telegram_account_link_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "failed_attempts >= 0", name="ck_telegram_link_attempts_nonnegative"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_digest"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    _create_index_if_missing(
        "ix_telegram_account_link_challenges_expires_at",
        "telegram_account_link_challenges",
        ["expires_at"],
    )
    _create_table_if_missing(
        "customer_cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("item_key", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity >= 1 AND quantity <= 20", name="ck_customer_cart_quantity"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "item_key", name="uq_customer_cart_user_item"),
    )
    _create_index_if_missing("ix_customer_cart_items_product_id", "customer_cart_items", ["product_id"])
    _create_index_if_missing("ix_customer_cart_items_user_id", "customer_cart_items", ["user_id"])


def downgrade():
    op.drop_table("customer_cart_items")
    op.drop_index(
        "ix_telegram_account_link_challenges_expires_at",
        table_name="telegram_account_link_challenges",
    )
    op.drop_table("telegram_account_link_challenges")
    op.drop_table("telegram_identities")
