"""Add SSLCOMMERZ payment and seller settlement records.

Revision ID: 20261009_16
Revises: 20261008_15
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261009_16"
down_revision = "20261008_15"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "app_settings" in existing_tables:
        columns = {column["name"] for column in inspector.get_columns("app_settings")}
        with op.batch_alter_table("app_settings") as batch:
            if "commission_rate_percent" not in columns:
                batch.add_column(sa.Column("commission_rate_percent", sa.Numeric(5, 2), nullable=True))
            if "seller_return_window_days" not in columns:
                batch.add_column(
                    sa.Column(
                        "seller_return_window_days", sa.Integer(), nullable=False, server_default="14"
                    )
                )

    if "payments" not in existing_tables:
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("checkout_group", sa.String(length=40), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="BDT"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
            sa.Column("bank_tran_id", sa.String(length=80), nullable=True),
            sa.Column("validation_id", sa.String(length=50), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
            sa.CheckConstraint(
                "status IN ('pending', 'paid', 'review_required', 'partially_refunded', 'refunded', 'expired', 'cancelled')",
                name="ck_payments_status_valid",
            ),
            sa.CheckConstraint("currency = 'BDT'", name="ck_payments_currency_valid"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("checkout_group", name="uq_payments_checkout_group"),
        )
    existing_tables.add("payments")
    for name, table, columns in (
        ("ix_payments_expires_at", "payments", ["expires_at"]),
        ("ix_payments_bank_tran_id", "payments", ["bank_tran_id"]),
    ):
        known = {idx["name"] for idx in inspect(bind).get_indexes(table)}
        if name not in known:
            op.create_index(name, table, columns)

    if "payment_attempts" not in existing_tables:
        op.create_table(
            "payment_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("payment_id", sa.Integer(), nullable=False),
            sa.Column("transaction_id", sa.String(length=30), nullable=False),
            sa.Column("session_key", sa.String(length=80), nullable=True),
            sa.Column("gateway_url", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="initiating"),
            sa.Column("validation_id", sa.String(length=50), nullable=True),
            sa.Column("bank_tran_id", sa.String(length=80), nullable=True),
            sa.Column("validated_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("validated_currency", sa.String(length=3), nullable=True),
            sa.Column("risk_level", sa.Integer(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "status IN ('initiating', 'pending', 'paid', 'review_required', 'failed', 'cancelled', 'expired', 'superseded', 'duplicate_paid')",
                name="ck_payment_attempts_status_valid",
            ),
            sa.CheckConstraint(
                "risk_level IS NULL OR risk_level IN (0, 1)", name="ck_payment_attempts_risk_level"
            ),
            sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("transaction_id", name="uq_payment_attempts_transaction_id"),
        )
    for name, table, columns in (
        ("ix_payment_attempts_payment_id", "payment_attempts", ["payment_id"]),
        ("ix_payment_attempts_bank_tran_id", "payment_attempts", ["bank_tran_id"]),
        ("ix_payment_attempts_expires_at", "payment_attempts", ["expires_at"]),
    ):
        known = {idx["name"] for idx in inspect(bind).get_indexes(table)}
        if name not in known:
            op.create_index(name, table, columns)

    if "seller_payouts" not in existing_tables:
        op.create_table(
            "seller_payouts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("seller_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("reference", sa.String(length=120), nullable=False),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("recorded_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("amount > 0", name="ck_seller_payouts_amount_positive"),
            sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_seller_payouts_seller_id", "seller_payouts", ["seller_id"])

    if "orders" in existing_tables:
        columns = {column["name"] for column in inspect(bind).get_columns("orders")}
        with op.batch_alter_table("orders") as batch:
            if "ck_order_payment_method_valid" in {
                constraint.get("name") for constraint in inspect(bind).get_check_constraints("orders")
            }:
                batch.drop_constraint("ck_order_payment_method_valid", type_="check")
            if "payment_id" not in columns:
                batch.add_column(sa.Column("payment_id", sa.Integer(), nullable=True))
                batch.create_foreign_key(
                    "fk_orders_payment_id_payments", "payments", ["payment_id"], ["id"], ondelete="SET NULL"
                )
            if "city" not in columns:
                batch.add_column(sa.Column("city", sa.String(length=100), nullable=True))
            if "commission_rate_percent" not in columns:
                batch.add_column(sa.Column("commission_rate_percent", sa.Numeric(5, 2), nullable=True))
            if "commission_amount" not in columns:
                batch.add_column(sa.Column("commission_amount", sa.Numeric(10, 2), nullable=True))
            if "return_window_days_snapshot" not in columns:
                batch.add_column(sa.Column("return_window_days_snapshot", sa.Integer(), nullable=True))
            batch.create_check_constraint(
                "ck_order_payment_method_valid", "payment_method IN ('cod', 'sslcommerz')"
            )
        if "ix_orders_payment_id" not in {idx["name"] for idx in inspect(bind).get_indexes("orders")}:
            op.create_index("ix_orders_payment_id", "orders", ["payment_id"])

    if "payment_refunds" not in existing_tables:
        op.create_table(
            "payment_refunds",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("payment_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("refund_trans_id", sa.String(length=30), nullable=False),
            sa.Column("provider_refund_id", sa.String(length=80), nullable=True),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="initiating"),
            sa.Column("reason", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("amount > 0", name="ck_payment_refunds_amount_positive"),
            sa.CheckConstraint(
                "status IN ('initiating', 'processing', 'refunded', 'failed')",
                name="ck_payment_refunds_status_valid",
            ),
            sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("order_id", name="uq_payment_refunds_order_id"),
            sa.UniqueConstraint("refund_trans_id", name="uq_payment_refunds_refund_trans_id"),
        )
        op.create_index("ix_payment_refunds_payment_id", "payment_refunds", ["payment_id"])
        op.create_index("ix_payment_refunds_provider_refund_id", "payment_refunds", ["provider_refund_id"])

    if "seller_ledger_entries" not in existing_tables:
        op.create_table(
            "seller_ledger_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("seller_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("payment_id", sa.Integer(), nullable=False),
            sa.Column("payout_id", sa.Integer(), nullable=True),
            sa.Column("entry_type", sa.String(length=24), nullable=False),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("idempotency_key", sa.String(length=100), nullable=False),
            sa.Column("eligible_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "entry_type IN ('sale', 'commission', 'refund', 'commission_refund', 'payout')",
                name="ck_seller_ledger_entry_type",
            ),
            sa.CheckConstraint("amount <> 0", name="ck_seller_ledger_amount_nonzero"),
            sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["payout_id"], ["seller_payouts.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key", name="uq_seller_ledger_idempotency_key"),
        )
        op.create_index("ix_seller_ledger_entries_seller_id", "seller_ledger_entries", ["seller_id"])
        op.create_index("ix_seller_ledger_entries_order_id", "seller_ledger_entries", ["order_id"])
        op.create_index("ix_seller_ledger_entries_payment_id", "seller_ledger_entries", ["payment_id"])
        op.create_index("ix_seller_ledger_entries_payout_id", "seller_ledger_entries", ["payout_id"])
        op.create_index("ix_seller_ledger_entries_eligible_at", "seller_ledger_entries", ["eligible_at"])
        op.create_index(
            "ix_seller_ledger_seller_eligible", "seller_ledger_entries", ["seller_id", "eligible_at"]
        )


def downgrade():
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "seller_ledger_entries" in tables:
        op.drop_table("seller_ledger_entries")
    if "payment_refunds" in tables:
        op.drop_table("payment_refunds")
    if "orders" in tables:
        indexes = {idx["name"] for idx in inspect(bind).get_indexes("orders")}
        if "ix_orders_payment_id" in indexes:
            op.drop_index("ix_orders_payment_id", table_name="orders")
        columns = {column["name"] for column in inspect(bind).get_columns("orders")}
        with op.batch_alter_table("orders") as batch:
            checks = {
                constraint.get("name") for constraint in inspect(bind).get_check_constraints("orders")
            }
            if "ck_order_payment_method_valid" in checks:
                batch.drop_constraint("ck_order_payment_method_valid", type_="check")
            if "payment_id" in columns:
                batch.drop_constraint("fk_orders_payment_id_payments", type_="foreignkey")
                batch.drop_column("payment_id")
            for column in ("return_window_days_snapshot", "commission_amount", "commission_rate_percent"):
                if column in columns:
                    batch.drop_column(column)
            batch.create_check_constraint(
                "ck_order_payment_method_valid", "payment_method = 'cod'"
            )
    if "seller_payouts" in tables:
        op.drop_table("seller_payouts")
    if "payment_attempts" in tables:
        op.drop_table("payment_attempts")
    if "payments" in tables:
        op.drop_table("payments")
    if "app_settings" in tables:
        columns = {column["name"] for column in inspect(bind).get_columns("app_settings")}
        with op.batch_alter_table("app_settings") as batch:
            for column in ("seller_return_window_days", "commission_rate_percent"):
                if column in columns:
                    batch.drop_column(column)
