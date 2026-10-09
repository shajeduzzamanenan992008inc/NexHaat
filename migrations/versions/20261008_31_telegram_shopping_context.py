"""Add short-lived, privacy-safe Telegram shopping context."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261008_31"
down_revision = "20261007_30"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("telegram_shopping_contexts"):
        op.create_table(
            "telegram_shopping_contexts",
            sa.Column("conversation_hash", sa.String(length=64), primary_key=True),
            sa.Column("context", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
    indexes = {
        item["name"] for item in inspect(bind).get_indexes("telegram_shopping_contexts")
    }
    if "ix_telegram_shopping_contexts_expires_at" not in indexes:
        op.create_index(
            "ix_telegram_shopping_contexts_expires_at",
            "telegram_shopping_contexts",
            ["expires_at"],
        )


def downgrade():
    bind = op.get_bind()
    if inspect(bind).has_table("telegram_shopping_contexts"):
        indexes = {
            item["name"] for item in inspect(bind).get_indexes("telegram_shopping_contexts")
        }
        if "ix_telegram_shopping_contexts_expires_at" in indexes:
            op.drop_index(
                "ix_telegram_shopping_contexts_expires_at",
                table_name="telegram_shopping_contexts",
            )
        op.drop_table("telegram_shopping_contexts")