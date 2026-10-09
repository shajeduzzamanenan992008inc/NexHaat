"""Add saved Admin Builder projects, patch approvals, Guardian scans and lessons."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261009_33"
down_revision = "20261008_32"
branch_labels = None
depends_on = None


def _create_table_if_missing(table_name, *args, **kwargs):
    if not inspect(op.get_bind()).has_table(table_name):
        op.create_table(table_name, *args, **kwargs)


def _create_index_if_missing(index_name, table_name, columns):
    if index_name not in {
        item["name"] for item in inspect(op.get_bind()).get_indexes(table_name)
    }:
        op.create_index(index_name, table_name, columns)


def upgrade():
    _create_table_if_missing(
        "ai_builder_projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("project_type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=1500), nullable=False, server_default=""),
        sa.Column("files_json", sa.Text(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("external_code_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "project_type IN ('flask', 'python', 'static')",
            name="ck_ai_builder_project_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_ai_builder_project_status",
        ),
    )
    _create_index_if_missing("ix_ai_builder_projects_admin_user_id", "ai_builder_projects", ["admin_user_id"])
    _create_index_if_missing(
        "ix_ai_builder_projects_admin_updated",
        "ai_builder_projects",
        ["admin_user_id", "updated_at"],
    )

    _create_table_if_missing(
        "ai_builder_patches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("ai_builder_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_sha256", sa.String(length=64), nullable=False),
        sa.Column("candidate_sha256", sa.String(length=64), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=False),
        sa.Column("candidate_files_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("test_status", sa.String(length=16), nullable=False, server_default="not_run"),
        sa.Column("test_output", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'tested', 'approved', 'rejected')",
            name="ck_ai_builder_patch_status",
        ),
        sa.CheckConstraint(
            "test_status IN ('not_run', 'passed', 'failed', 'unavailable', 'no_tests')",
            name="ck_ai_builder_patch_test_status",
        ),
    )
    _create_index_if_missing("ix_ai_builder_patches_project_id", "ai_builder_patches", ["project_id"])
    _create_index_if_missing(
        "ix_ai_builder_patches_project_created",
        "ai_builder_patches",
        ["project_id", "created_at"],
    )

    _create_table_if_missing(
        "ai_guardian_scans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("ai_builder_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("queue_signature", sa.String(length=64), nullable=False),
        sa.Column("result_summary", sa.String(length=1000), nullable=True),
        sa.Column("scanner_version", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "trigger IN ('manual', 'deployment', 'nightly')",
            name="ck_ai_guardian_scan_trigger",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'warning', 'failed')",
            name="ck_ai_guardian_scan_status",
        ),
    )
    _create_index_if_missing("ix_ai_guardian_scans_project_id", "ai_guardian_scans", ["project_id"])
    _create_index_if_missing(
        "ix_ai_guardian_scans_project_created",
        "ai_guardian_scans",
        ["project_id", "created_at"],
    )
    _create_index_if_missing(
        "ix_ai_guardian_scans_queue",
        "ai_guardian_scans",
        ["status", "created_at"],
    )

    _create_table_if_missing(
        "ai_guardian_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("ai_builder_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "first_scan_id",
            sa.String(length=36),
            sa.ForeignKey("ai_guardian_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "latest_scan_id",
            sa.String(length=36),
            sa.ForeignKey("ai_guardian_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=12), nullable=False),
        sa.Column("rule_id", sa.String(length=48), nullable=False),
        sa.Column("file_path", sa.String(length=240), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confirmed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_note", sa.String(length=500), nullable=True),
        sa.Column("first_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "project_id", "fingerprint", name="uq_ai_guardian_finding_project_fingerprint"
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_ai_guardian_finding_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'fixed', 'false_positive')",
            name="ck_ai_guardian_finding_status",
        ),
        sa.CheckConstraint("line_number >= 1", name="ck_ai_guardian_finding_line"),
    )
    _create_index_if_missing("ix_ai_guardian_findings_project_id", "ai_guardian_findings", ["project_id"])
    _create_index_if_missing(
        "ix_ai_guardian_findings_project_status",
        "ai_guardian_findings",
        ["project_id", "status"],
    )
    _create_index_if_missing("ix_ai_guardian_findings_fingerprint", "ai_guardian_findings", ["fingerprint"])

    _create_table_if_missing(
        "ai_guardian_lessons",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "patch_id",
            sa.String(length=36),
            sa.ForeignKey("ai_builder_patches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("content", sa.String(length=2000), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name="ck_ai_guardian_lesson_status",
        ),
    )
    _create_index_if_missing("ix_ai_guardian_lessons_admin_user_id", "ai_guardian_lessons", ["admin_user_id"])
    _create_index_if_missing(
        "ix_ai_guardian_lessons_admin_created",
        "ai_guardian_lessons",
        ["admin_user_id", "created_at"],
    )
    _create_index_if_missing("ix_ai_guardian_lessons_patch_id", "ai_guardian_lessons", ["patch_id"])


def downgrade():
    for table_name in (
        "ai_guardian_lessons", "ai_guardian_findings", "ai_guardian_scans",
        "ai_builder_patches", "ai_builder_projects",
    ):
        if inspect(op.get_bind()).has_table(table_name):
            op.drop_table(table_name)
