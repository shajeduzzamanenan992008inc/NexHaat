"""Add opt-in personalization and observed price history/alerts.

Revision ID: 20261007_29
Revises: 20261007_28
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261007_29"
down_revision = "20261007_28"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    preference_columns = {item["name"] for item in inspector.get_columns("ai_preferences")}
    if "personalized_recommendations_enabled" not in preference_columns:
        op.add_column("ai_preferences", sa.Column(
            "personalized_recommendations_enabled", sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ))

    if not inspector.has_table("ai_product_price_history"):
        op.create_table(
            "ai_product_price_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(),
                      sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("regular_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("discount_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("effective_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("regular_price >= 0", name="ck_ai_price_history_regular_nonnegative"),
            sa.CheckConstraint("discount_price IS NULL OR discount_price >= 0",
                               name="ck_ai_price_history_discount_nonnegative"),
            sa.CheckConstraint("effective_price >= 0", name="ck_ai_price_history_effective_nonnegative"),
        )
    history_indexes = {item["name"] for item in inspect(bind).get_indexes("ai_product_price_history")}
    if "ix_ai_product_price_history_product_id" not in history_indexes:
        op.create_index("ix_ai_product_price_history_product_id", "ai_product_price_history", ["product_id"])
    if "ix_ai_price_history_product_recorded" not in history_indexes:
        op.create_index("ix_ai_price_history_product_recorded", "ai_product_price_history",
                        ["product_id", "recorded_at"])

    if not inspect(bind).has_table("ai_product_price_alerts"):
        op.create_table(
            "ai_product_price_alerts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id", "product_id", name="uq_ai_price_alert_user_product"),
            sa.CheckConstraint("target_price >= 0", name="ck_ai_price_alert_target_nonnegative"),
        )
    alert_indexes = {item["name"] for item in inspect(bind).get_indexes("ai_product_price_alerts")}
    if "ix_ai_product_price_alerts_user_id" not in alert_indexes:
        op.create_index("ix_ai_product_price_alerts_user_id", "ai_product_price_alerts", ["user_id"])
    if "ix_ai_product_price_alerts_product_id" not in alert_indexes:
        op.create_index("ix_ai_product_price_alerts_product_id", "ai_product_price_alerts", ["product_id"])
    if "ix_ai_price_alert_product_active" not in alert_indexes:
        op.create_index("ix_ai_price_alert_product_active", "ai_product_price_alerts", ["product_id", "active"])


def downgrade():
    op.drop_index("ix_ai_price_alert_product_active", table_name="ai_product_price_alerts")
    op.drop_index("ix_ai_product_price_alerts_product_id", table_name="ai_product_price_alerts")
    op.drop_index("ix_ai_product_price_alerts_user_id", table_name="ai_product_price_alerts")
    op.drop_table("ai_product_price_alerts")
    op.drop_index("ix_ai_price_history_product_recorded", table_name="ai_product_price_history")
    op.drop_index("ix_ai_product_price_history_product_id", table_name="ai_product_price_history")
    op.drop_table("ai_product_price_history")
    op.drop_column("ai_preferences", "personalized_recommendations_enabled")
