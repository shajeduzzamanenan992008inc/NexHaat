"""Add customer return requests and return status tracking.

Revision ID: 20261010_17
Revises: 20261009_16
Create Date: 2026-10-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261010_17"
down_revision = "20261009_16"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "orders" in existing_tables:
        with op.batch_alter_table("orders") as batch:
            check_names = {constraint.get("name") for constraint in inspector.get_check_constraints("orders")}
            if "ck_order_status_valid" in check_names:
                batch.drop_constraint("ck_order_status_valid", type_="check")
            batch.create_check_constraint(
                "ck_order_status_valid",
                "status IN ('pending', 'confirmed', 'preparing', 'delivered', 'returned', 'cancelled', 'declined')",
            )

    if "order_returns" not in existing_tables:
        op.create_table(
            "order_returns",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("customer_id", sa.Integer(), nullable=True),
            sa.Column("requested_by_id", sa.Integer(), nullable=True),
            sa.Column("reason", sa.String(length=255), nullable=False),
            sa.Column("refund_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="requested"),
            sa.Column("review_note", sa.String(length=500), nullable=True),
            sa.Column("provider_refund_id", sa.String(length=80), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("refund_amount >= 0", name="ck_order_return_refund_amount_nonnegative"),
            sa.CheckConstraint(
                "status IN ('requested', 'approved', 'rejected', 'received', 'refunded', 'failed')",
                name="ck_order_return_status_valid",
            ),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("order_id", name="uq_order_returns_order_id"),
        )
        op.create_index("ix_order_returns_customer_id", "order_returns", ["customer_id"])
        op.create_index("ix_order_returns_provider_refund_id", "order_returns", ["provider_refund_id"])


def downgrade():
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "order_returns" in tables:
        op.drop_table("order_returns")
    if "orders" in tables:
        with op.batch_alter_table("orders") as batch:
            check_names = {constraint.get("name") for constraint in inspect(bind).get_check_constraints("orders")}
            if "ck_order_status_valid" in check_names:
                batch.drop_constraint("ck_order_status_valid", type_="check")
            batch.create_check_constraint(
                "ck_order_status_valid",
                "status IN ('pending', 'confirmed', 'preparing', 'delivered', 'cancelled', 'declined')",
            )
