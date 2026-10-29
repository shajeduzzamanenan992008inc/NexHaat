"""Add composite indexes for discovery facets and weighted search.

Revision ID: 20261010_27
Revises: 20261006_26
Create Date: 2026-10-10
"""

from alembic import op
from sqlalchemy import inspect

revision = "20261010_27"
down_revision = "20261006_26"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_products_public_category_price", ["category_id", "is_available", "moderation_status", "price"]),
    ("ix_products_public_brand", ["brand_name", "is_available", "moderation_status"]),
    ("ix_products_public_seller", ["seller_id", "is_available", "moderation_status"]),
)

def upgrade():
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes("products")}
    for name, columns in INDEXES:
        if name not in existing:
            op.create_index(name, "products", columns, unique=False)

def downgrade():
    inspector = inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes("products")}
    for name, _columns in INDEXES:
        if name in existing:
            op.drop_index(name, table_name="products")
