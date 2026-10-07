"""Add metadata and results for transient Admin project analysis jobs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261007_30"
down_revision = "20261007_29"
branch_labels = None
depends_on = None


def upgrade():
    if not inspect(op.get_bind()).has_table("ai_builder_jobs"):
        op.create_table(
            "ai_builder_jobs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("admin_user_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("task_type", sa.String(length=32), nullable=False,
                      server_default="analyze_project"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
            sa.Column("source_sha256", sa.String(length=64), nullable=False),
            sa.Column("inspected_file_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("external_code_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("result_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "task_type IN ('analyze_project')", name="ck_ai_builder_job_task_type"
            ),
            sa.CheckConstraint(
                "status IN ('running', 'completed', 'failed')", name="ck_ai_builder_job_status"
            ),
            sa.CheckConstraint("inspected_file_count >= 0", name="ck_ai_builder_job_file_count"),
        )
    indexes = {item["name"] for item in inspect(op.get_bind()).get_indexes("ai_builder_jobs")}
    if "ix_ai_builder_jobs_admin_user_id" not in indexes:
        op.create_index("ix_ai_builder_jobs_admin_user_id", "ai_builder_jobs", ["admin_user_id"])
    if "ix_ai_builder_jobs_admin_created" not in indexes:
        op.create_index(
            "ix_ai_builder_jobs_admin_created", "ai_builder_jobs", ["admin_user_id", "created_at"]
        )


def downgrade():
    op.drop_index("ix_ai_builder_jobs_admin_created", table_name="ai_builder_jobs")
    op.drop_index("ix_ai_builder_jobs_admin_user_id", table_name="ai_builder_jobs")
    op.drop_table("ai_builder_jobs")
