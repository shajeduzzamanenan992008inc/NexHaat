"""Add phone verification timestamp to customers.

Revision ID: 20261012_02
Revises: 20261012_01
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261012_02"
down_revision = "20261012_01"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("customers")}
    if "phone_verified_at" not in columns:
        op.add_column(
            "customers",
            sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade():
    inspector = inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("customers")}
    if "phone_verified_at" in columns:
        op.drop_column("customers", "phone_verified_at")
