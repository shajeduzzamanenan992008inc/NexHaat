"""Add review helpful votes and review abuse reports.

Revision ID: 20261011_28
Revises: 20261010_27
Create Date: 2026-10-11
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261011_28"
down_revision = "20261010_27"
branch_labels = None
depends_on = None

def upgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "review_helpful_votes" not in tables:
        op.create_table(
            "review_helpful_votes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "review_id",
                sa.Integer(),
                sa.ForeignKey("reviews.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("review_id", "user_id", name="uq_review_helpful_vote_user"),
        )
        op.create_index("ix_review_helpful_votes_review_id", "review_helpful_votes", ["review_id"])
        op.create_index("ix_review_helpful_votes_user_id", "review_helpful_votes", ["user_id"])

    if "review_reports" not in tables:
        op.create_table(
            "review_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "review_id",
                sa.Integer(),
                sa.ForeignKey("reviews.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "reporter_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "resolved_by_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("review_id", "reporter_user_id", name="uq_review_report_reporter"),
            sa.CheckConstraint(
                "status IN ('open', 'reviewed', 'dismissed')", name="ck_review_report_status_valid"
            ),
            sa.CheckConstraint("length(trim(reason)) > 0", name="ck_review_report_reason_nonempty"),
        )
        op.create_index("ix_review_reports_review_id", "review_reports", ["review_id"])
        op.create_index("ix_review_reports_reporter_user_id", "review_reports", ["reporter_user_id"])
        op.create_index("ix_review_reports_status", "review_reports", ["status"])
        op.create_index(
            "ix_review_reports_status_created", "review_reports", ["status", "created_at"]
        )

def downgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "review_reports" in tables:
        op.drop_table("review_reports")
    if "review_helpful_votes" in tables:
        op.drop_table("review_helpful_votes")
