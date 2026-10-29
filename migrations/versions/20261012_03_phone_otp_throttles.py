"""Add phone OTP throttles table.

Revision ID: 20261012_03
Revises: 20261012_02
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261012_03"
down_revision = "20261012_02"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "phone_otp_throttles" not in tables:
        op.create_table(
            "phone_otp_throttles",
            sa.Column("key_hash", sa.String(length=64), nullable=False),
            sa.Column("failures", sa.Integer(), nullable=False, default=0),
            sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "failures >= 0", name="ck_phone_otp_throttle_failures_nonnegative"
            ),
            sa.PrimaryKeyConstraint("key_hash"),
        )
        op.create_index(
            "ix_phone_otp_throttles_last_attempt", "phone_otp_throttles", ["last_attempt_at"]
        )


def downgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "phone_otp_throttles" in tables:
        op.drop_table("phone_otp_throttles")
