"""Create the order_events table for order tracking timelines.

Revision ID: 20261103_01
Revises: 20261031_01
Create Date: 2026-11-03

This migration is additive: it creates a new table and indexes and never
alters the existing ``orders`` or ``order_items`` tables, so pre-existing
order data is untouched.

Manual rollback sequence (documented, not executed by this migration):
1. Back up the table, for example:
   psql -c "COPY order_events TO STDOUT" > order_events_backup.sql
   (or sqlite3 .dump / pg_dump / mysqldump equivalent).
2. Verify the backup contains the rows you expect.
3. Only after that verification, drop the indexes and table manually:
   - DROP INDEX IF EXISTS ix_order_events_order_created;
   - DROP INDEX IF EXISTS ix_order_events_created_at;
   - DROP TABLE IF EXISTS order_events;
4. Re-run `alembic upgrade <earlier-revision>`.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261103_01"
down_revision = "20261031_01"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    if "order_events" in inspector.get_table_names():
        return

    op.create_table(
        "order_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type", sa.String(length=20), nullable=False, server_default="status"
        ),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_role", sa.String(length=16), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("tracking_reference", sa.String(length=80), nullable=True),
        sa.Column("carrier", sa.String(length=80), nullable=True),
        sa.Column("estimated_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('created', 'status', 'delivery', 'payment', 'return', 'tracking')",
            name="ck_order_event_type_valid",
        ),
        sa.CheckConstraint(
            "actor_role IS NULL OR actor_role IN "
            "('customer', 'seller', 'admin', 'rider', 'system')",
            name="ck_order_event_actor_role_valid",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_order_events_order", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_order_events_actor", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "dedupe_key", name="uq_order_event_dedupe"),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])
    op.create_index("ix_order_events_created_at", "order_events", ["created_at"])
    op.create_index(
        "ix_order_events_order_created", "order_events", ["order_id", "created_at"]
    )


def downgrade():
    raise RuntimeError(
        "Automatic downgrade of revision 20261103_01 is intentionally disabled "
        "so order timeline history is never dropped silently.\n\n"
        "To roll back safely, back up the order_events table first, verify the "
        "backup, then drop the indexes and table manually:\n"
        "  - DROP INDEX IF EXISTS ix_order_events_order_created;\n"
        "  - DROP INDEX IF EXISTS ix_order_events_created_at;\n"
        "  - DROP INDEX IF EXISTS ix_order_events_order_id;\n"
        "  - DROP TABLE IF EXISTS order_events;\n"
        "After completing those manual steps, re-run the earlier revision with "
        "`alembic upgrade 20261031_01`."
    )
