"""Add durable per-request external AI notice metadata."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261007_28"
down_revision = "20261007_27"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("ai_external_call_notices"):
        op.create_table(
            "ai_external_call_notices",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("model", sa.String(length=160), nullable=False),
            sa.Column("purpose", sa.String(length=32), nullable=False),
            sa.Column("job_id", sa.String(length=80), nullable=True),
            sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="started"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("status = 'started'", name="ck_ai_external_call_notice_status"),
            sa.CheckConstraint("estimated_cost_usd >= 0", name="ck_ai_external_call_notice_cost"),
        )
    if not inspect(bind).has_table("ai_external_call_recipients"):
        op.create_table(
            "ai_external_call_recipients",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("call_notice_id", sa.String(length=36),
                      sa.ForeignKey("ai_external_call_notices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("call_notice_id", "telegram_user_id", name="uq_ai_call_recipient"),
            sa.CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_ai_call_recipient_status"),
            sa.CheckConstraint("attempts >= 0", name="ck_ai_call_recipient_attempts"),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("ai_external_call_recipients")}
    if "ix_ai_external_call_recipients_status" not in indexes:
        op.create_index("ix_ai_external_call_recipients_status",
                        "ai_external_call_recipients", ["status"])
    if "ix_ai_call_recipient_pending" not in indexes:
        op.create_index("ix_ai_call_recipient_pending", "ai_external_call_recipients",
                        ["status", "id"])


def downgrade():
    op.drop_index("ix_ai_call_recipient_pending", table_name="ai_external_call_recipients")
    op.drop_index("ix_ai_external_call_recipients_status", table_name="ai_external_call_recipients")
    op.drop_table("ai_external_call_recipients")
    op.drop_table("ai_external_call_notices")
