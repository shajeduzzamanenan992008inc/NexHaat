"""Add per-kind throttles for opt-in smart notification digests."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261006_26"
down_revision = "20261006_25"
branch_labels = None
depends_on = None


def upgrade():
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("ai_preferences")}
    if "last_cart_reminder_at" not in columns:
        op.add_column("ai_preferences", sa.Column("last_cart_reminder_at", sa.DateTime(timezone=True), nullable=True))
    if "last_recommendation_notification_at" not in columns:
        op.add_column("ai_preferences", sa.Column("last_recommendation_notification_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("ai_preferences")}
    with op.batch_alter_table("ai_preferences") as batch:
        if "last_recommendation_notification_at" in columns:
            batch.drop_column("last_recommendation_notification_at")
        if "last_cart_reminder_at" in columns:
            batch.drop_column("last_cart_reminder_at")
