"""Store manual refund references for COD returns.

Revision ID: 20261005_19
Revises: 20261011_18
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261005_19"
down_revision = "20261011_18"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "order_returns" not in tables:
        raise RuntimeError("Expected the order_returns table from the Stage 8 migration.")
    columns = {column["name"] for column in inspect(bind).get_columns("order_returns")}
    if "manual_refund_reference" not in columns:
        op.add_column(
            "order_returns",
            sa.Column("manual_refund_reference", sa.String(length=120), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    if "order_returns" not in set(inspect(bind).get_table_names()):
        return
    columns = {column["name"] for column in inspect(bind).get_columns("order_returns")}
    if "manual_refund_reference" in columns:
        op.drop_column("order_returns", "manual_refund_reference")
