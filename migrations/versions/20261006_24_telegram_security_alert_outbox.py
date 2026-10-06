"""Add durable Telegram security-alert delivery state.

Revision ID: 20261006_24
Revises: 20261006_23
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20261006_24"
down_revision = "20261006_23"
branch_labels = None
depends_on = None


def upgrade():
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
    op.create_index(
        "ix_telegram_security_alerts_status",
        "telegram_security_alerts",
        ["status"],
    )


def downgrade():
    op.drop_index("ix_telegram_security_alerts_status", table_name="telegram_security_alerts")
    op.drop_table("telegram_security_alerts")
