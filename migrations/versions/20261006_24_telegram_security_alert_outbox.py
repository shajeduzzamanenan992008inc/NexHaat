"""Add durable Telegram security-alert delivery state.

Revision ID: 20261006_24
Revises: 20261006_23
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261006_24"
down_revision = "20261006_23"
branch_labels = None
depends_on = None


def _create_index_if_missing(name, table, columns):
    existing = {item["name"] for item in inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def upgrade():
    if not inspect(op.get_bind()).has_table("telegram_security_alerts"):
        op.create_table(
        "telegram_security_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("audit_event_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')", name="ck_telegram_alert_status"
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_telegram_alert_attempts_nonnegative"),
        sa.ForeignKeyConstraint(["audit_event_id"], ["audit_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_event_id"),
    )
    _create_index_if_missing(
        "ix_telegram_security_alerts_status",
        "telegram_security_alerts",
        ["status"],
    )


def downgrade():
    op.drop_index("ix_telegram_security_alerts_status", table_name="telegram_security_alerts")
    op.drop_table("telegram_security_alerts")
