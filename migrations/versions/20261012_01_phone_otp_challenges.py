"""Add phone OTP challenges for SMS verification.

Revision ID: 20261012_01
Revises: 20261011_28
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261012_01"
down_revision = "20261011_28"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "phone_otp_challenges" not in tables:
        op.create_table(
            "phone_otp_challenges",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("phone_canonical", sa.String(length=20), nullable=False),
            sa.Column("code_hash", sa.String(length=64), nullable=False),
            sa.Column("purpose", sa.String(length=32), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provider_message_id", sa.String(length=128), nullable=True),
            sa.Column("locale", sa.String(length=12), nullable=True),
            sa.CheckConstraint(
                "failed_attempts >= 0",
                name="ck_phone_otp_challenges_failed_attempts_nonnegative",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_phone_otp_challenges_phone_canonical",
            "phone_otp_challenges",
            ["phone_canonical"],
        )
        op.create_index(
            "ix_phone_otp_challenges_expires_at",
            "phone_otp_challenges",
            ["expires_at"],
        )
        op.create_index(
            "ix_phone_otp_challenges_user_id",
            "phone_otp_challenges",
            ["user_id"],
        )
        op.create_index(
            "ix_phone_otp_challenges_phone_sent",
            "phone_otp_challenges",
            ["phone_canonical", "sent_at"],
        )


def downgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "phone_otp_challenges" in tables:
        op.drop_table("phone_otp_challenges")
