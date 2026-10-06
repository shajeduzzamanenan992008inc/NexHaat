"""Add durable Telegram update and rate-limit state.

Revision ID: 20261006_22
Revises: 20261005_21
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261006_22"
down_revision = "20261005_21"
branch_labels = None
depends_on = None


def upgrade():
    if not inspect(op.get_bind()).has_table("processed_telegram_updates"):
        op.create_table(
        "processed_telegram_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_name", sa.String(length=20), nullable=False),
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('processing', 'processed', 'failed')", name="ck_telegram_update_state"
        ),
        sa.CheckConstraint("attempts > 0", name="ck_telegram_update_attempts_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_name", "update_id", name="uq_telegram_update_bot_id"),
    )
    if not inspect(op.get_bind()).has_table("telegram_rate_limits"):
        op.create_table(
        "telegram_rate_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_name", sa.String(length=20), nullable=False),
        sa.Column("telegram_user_hash", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.BigInteger(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("request_count > 0", name="ck_telegram_rate_limit_count_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_name", "telegram_user_hash", name="uq_telegram_rate_limit_user"),
    )


def downgrade():
    op.drop_table("telegram_rate_limits")
    op.drop_table("processed_telegram_updates")
