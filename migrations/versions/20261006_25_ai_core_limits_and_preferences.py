"""Add AI request limits and opt-in smart notification preferences."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261006_25"
down_revision = "20261006_24"
branch_labels = None
depends_on = None


def _create_table_if_missing(name, *columns, **kwargs):
    if not inspect(op.get_bind()).has_table(name):
        op.create_table(name, *columns, **kwargs)


def _create_index_if_missing(name, table, columns):
    existing = {item["name"] for item in inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def upgrade():
    _create_table_if_missing(
        "ai_request_windows",
        sa.Column("principal_hash", sa.String(length=64), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("request_count >= 0", name="ck_ai_request_window_count_nonnegative"),
    )
    _create_index_if_missing(
        "ix_ai_request_windows_updated_at", "ai_request_windows", ["updated_at"]
    )
    _create_table_if_missing(
        "ai_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("smart_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_smart_notification_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    _create_table_if_missing(
        "support_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False, server_default="other"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open', 'pending', 'closed')", name="ck_support_conversation_status"),
        sa.CheckConstraint("category IN ('order', 'delivery', 'returns', 'account', 'product', 'other')", name="ck_support_conversation_category"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    _create_index_if_missing("ix_support_conversations_user_id", "support_conversations", ["user_id"])
    _create_index_if_missing("ix_support_conversations_status", "support_conversations", ["status"])
    _create_index_if_missing("ix_support_conversations_updated_at", "support_conversations", ["updated_at"])
    _create_index_if_missing("ix_support_conversations_status_updated", "support_conversations", ["status", "updated_at"])
    _create_table_if_missing(
        "support_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column("sender_role", sa.String(length=12), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sender_role IN ('customer', 'staff')", name="ck_support_message_sender_role"),
        sa.CheckConstraint("length(trim(body)) BETWEEN 1 AND 5000", name="ck_support_message_body_length"),
        sa.ForeignKeyConstraint(["conversation_id"], ["support_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    _create_index_if_missing("ix_support_messages_conversation_id", "support_messages", ["conversation_id"])
    _create_index_if_missing("ix_support_messages_sender_user_id", "support_messages", ["sender_user_id"])
    _create_index_if_missing("ix_support_messages_created_at", "support_messages", ["created_at"])


def downgrade():
    op.drop_table("support_messages")
    op.drop_table("support_conversations")
    op.drop_table("ai_preferences")
    op.drop_index("ix_ai_request_windows_updated_at", table_name="ai_request_windows")
    op.drop_table("ai_request_windows")
