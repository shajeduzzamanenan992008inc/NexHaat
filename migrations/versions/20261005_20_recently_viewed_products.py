"""Track customer recently viewed products for the Stage 11 slice.

Revision ID: 20261005_20
Revises: 20261011_18
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20261005_20"
down_revision = "20261011_18"
branch_labels = None
depends_on = None


def upgrade():
    if not op.get_bind().dialect.has_table(op.get_bind(), "recently_viewed_products"):
        op.create_table(
            "recently_viewed_products",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "product_id", name="uq_recently_viewed_user_product"),
        )
        op.create_index("ix_recently_viewed_products_user_id", "recently_viewed_products", ["user_id"])
        op.create_index("ix_recently_viewed_products_product_id", "recently_viewed_products", ["product_id"])
        op.create_index("ix_recently_viewed_products_viewed_at", "recently_viewed_products", ["viewed_at"])
        op.create_index(
            "ix_recently_viewed_user_viewed_at",
            "recently_viewed_products",
            ["user_id", "viewed_at"],
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.has_table(bind, "recently_viewed_products"):
        op.drop_table("recently_viewed_products")
