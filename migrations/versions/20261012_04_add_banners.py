"""Add banners table for home carousel.

Revision ID: 20261012_04
Revises: 20261012_03
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261012_04"
down_revision = "20261012_03"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "banners" not in tables:
        op.create_table(
            "banners",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=False),
            sa.Column("subtitle", sa.String(length=255), nullable=True),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column("link_url", sa.String(length=500), nullable=True),
            sa.Column("link_type", sa.String(length=32), nullable=False, server_default="products"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("length(trim(title)) > 0", name="ck_banner_title_nonempty"),
            sa.CheckConstraint(
                "link_type IN ('products', 'category', 'search', 'external')",
                name="ck_banner_link_type",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_banners_is_active", "banners", ["is_active"])
        op.create_index("ix_banners_active_order", "banners", ["is_active", "display_order"])


def downgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "banners" in tables:
        op.drop_index("ix_banners_active_order", table_name="banners")
        op.drop_index("ix_banners_is_active", table_name="banners")
        op.drop_table("banners")
