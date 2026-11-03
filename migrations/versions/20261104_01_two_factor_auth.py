"""Create user_two_factor and user_backup_codes tables for server-side 2FA.

Revision ID: 20261104_01
Revises: 20261103_01
Create Date: 2026-11-04

This migration is purely additive: it creates the ``user_two_factor`` and
``user_backup_codes`` tables and indexes. It never alters existing columns in
``users`` or any other table, so existing accounts and data remain intact.

Manual rollback sequence (documented, not executed by this migration):
1. Back up data if any users have enrolled:
   psql -c "COPY user_two_factor TO STDOUT" > user_two_factor_backup.sql
   psql -c "COPY user_backup_codes TO STDOUT" > user_backup_codes_backup.sql
2. Drop indexes and tables in reverse dependency order:
   - DROP INDEX IF EXISTS ix_user_backup_codes_user_used;
   - DROP INDEX IF EXISTS ix_user_backup_codes_user_id;
   - DROP TABLE IF EXISTS user_backup_codes;
   - DROP INDEX IF EXISTS ix_user_two_factor_enabled;
   - DROP INDEX IF EXISTS ix_user_two_factor_user_id;
   - DROP TABLE IF EXISTS user_two_factor;
3. Re-run `alembic upgrade 20261103_01`.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261104_01"
down_revision = "20261103_01"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    table_names = inspector.get_table_names()

    if "user_two_factor" not in table_names:
        op.create_table(
            "user_two_factor",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("encrypted_secret", sa.LargeBinary(), nullable=False),
            sa.Column("encryption_key_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_step", sa.BigInteger(), nullable=True),
            sa.CheckConstraint(
                "encryption_key_version >= 1",
                name="ck_user_two_factor_key_version_positive",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_user_two_factor_user_id",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_user_two_factor"),
        )
        op.create_index(
            "ix_user_two_factor_user_id",
            "user_two_factor",
            ["user_id"],
            unique=True,
        )
        op.create_index(
            "ix_user_two_factor_enabled",
            "user_two_factor",
            ["enabled"],
        )

    if "user_backup_codes" not in table_names:
        op.create_table(
            "user_backup_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("code_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_user_backup_codes_user_id",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_user_backup_codes"),
        )
        op.create_index(
            "ix_user_backup_codes_user_id",
            "user_backup_codes",
            ["user_id"],
        )
        op.create_index(
            "ix_user_backup_codes_user_used",
            "user_backup_codes",
            ["user_id", "used_at"],
        )


def downgrade():
    raise RuntimeError(
        "Automatic downgrade of revision 20261104_01 is intentionally disabled "
        "so user two-factor secrets and backup codes are never dropped silently.\n\n"
        "To roll back safely, back up the user_two_factor and user_backup_codes tables first:\n"
        "  - psql -c \"COPY user_two_factor TO STDOUT\" > user_two_factor_backup.sql\n"
        "  - psql -c \"COPY user_backup_codes TO STDOUT\" > user_backup_codes_backup.sql\n"
        "Verify the backup contains the rows you expect, then drop the indexes and tables manually in reverse dependency order:\n"
        "  - DROP INDEX IF EXISTS ix_user_backup_codes_user_used;\n"
        "  - DROP INDEX IF EXISTS ix_user_backup_codes_user_id;\n"
        "  - DROP TABLE IF EXISTS user_backup_codes;\n"
        "  - DROP INDEX IF EXISTS ix_user_two_factor_enabled;\n"
        "  - DROP INDEX IF EXISTS ix_user_two_factor_user_id;\n"
        "  - DROP TABLE IF EXISTS user_two_factor;\n"
        "After completing those manual steps, re-run the earlier revision with `alembic upgrade 20261103_01`."
    )
