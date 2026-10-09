"""Minimal persisted AI request limits and customer alert preferences."""

from datetime import datetime, timezone
import json

from sqlalchemy.types import TypeDecorator, Text

from ..extensions import db

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # Development can still use the SQLite JSON-vector path.
    Vector = None


class EmbeddingVector(TypeDecorator):
    """Use pgvector in PostgreSQL and an ephemeral JSON representation in SQLite."""

    impl = Text
    cache_ok = True

    class Comparator(TypeDecorator.Comparator):
        def cosine_distance(self, other):
            return self.expr.op("<=>", return_type=db.Float)(other)

    comparator_factory = Comparator

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and Vector is not None:
            return dialect.type_descriptor(Vector(1024))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, separators=(",", ":"))

    def process_result_value(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None


class AIRequestWindow(db.Model):
    __tablename__ = "ai_request_windows"

    principal_hash = db.Column(db.String(64), primary_key=True)
    window_started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    request_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    updated_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
    __table_args__ = (
        db.CheckConstraint("request_count >= 0", name="ck_ai_request_window_count_nonnegative"),
        db.Index("ix_ai_request_windows_updated_at", "updated_at"),
    )


class AIPreferences(db.Model):
    __tablename__ = "ai_preferences"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    smart_notifications_enabled = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    personalized_recommendations_enabled = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    long_term_memory_enabled = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )
    last_smart_notification_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_cart_reminder_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_recommendation_notification_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
    user = db.relationship("User", backref=db.backref("ai_preferences", uselist=False, cascade="all, delete-orphan"))


class AIExternalConsent(db.Model):
    __tablename__ = "ai_external_consents"

    principal_hash = db.Column(db.String(64), primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    updated_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )


class AIExternalSpend(db.Model):
    __tablename__ = "ai_external_spend"

    month_key = db.Column(db.String(7), primary_key=True)
    reserved_usd = db.Column(db.Numeric(12, 6), nullable=False, default=0, server_default="0")
    updated_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )


class AIExternalCallNotice(db.Model):
    __tablename__ = "ai_external_call_notices"

    id = db.Column(db.String(36), primary_key=True)
    provider = db.Column(db.String(40), nullable=False)
    model = db.Column(db.String(160), nullable=False)
    purpose = db.Column(db.String(32), nullable=False)
    job_id = db.Column(db.String(80), nullable=True)
    estimated_cost_usd = db.Column(db.Numeric(12, 6), nullable=False, server_default="0")
    status = db.Column(db.String(16), nullable=False, server_default="started")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    recipients = db.relationship(
        "AIExternalCallRecipient", backref="call_notice", cascade="all, delete-orphan",
        order_by="AIExternalCallRecipient.telegram_user_id",
    )
    __table_args__ = (
        db.CheckConstraint("status = 'started'", name="ck_ai_external_call_notice_status"),
        db.CheckConstraint("estimated_cost_usd >= 0", name="ck_ai_external_call_notice_cost"),
    )


class AIExternalCallRecipient(db.Model):
    __tablename__ = "ai_external_call_recipients"

    id = db.Column(db.Integer, primary_key=True)
    call_notice_id = db.Column(
        db.String(36), db.ForeignKey("ai_external_call_notices.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_user_id = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.String(16), nullable=False, server_default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, server_default="0")
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    __table_args__ = (
        db.UniqueConstraint("call_notice_id", "telegram_user_id", name="uq_ai_call_recipient"),
        db.CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_ai_call_recipient_status"),
        db.CheckConstraint("attempts >= 0", name="ck_ai_call_recipient_attempts"),
        db.Index("ix_ai_call_recipient_pending", "status", "id"),
    )


class AIBuilderJob(db.Model):
    __tablename__ = "ai_builder_jobs"

    id = db.Column(db.String(36), primary_key=True)
    admin_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_type = db.Column(db.String(32), nullable=False, server_default="analyze_project")
    status = db.Column(db.String(16), nullable=False, server_default="running")
    source_sha256 = db.Column(db.String(64), nullable=False)
    inspected_file_count = db.Column(db.Integer, nullable=False, server_default="0")
    external_code_allowed = db.Column(db.Boolean, nullable=False, server_default=db.false())
    result_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    admin_user = db.relationship("User", backref=db.backref("ai_builder_jobs", cascade="all, delete-orphan"))

    __table_args__ = (
        db.CheckConstraint(
            "task_type IN ('analyze_project')", name="ck_ai_builder_job_task_type"
        ),
        db.CheckConstraint(
            "status IN ('running', 'completed', 'failed')", name="ck_ai_builder_job_status"
        ),
        db.CheckConstraint("inspected_file_count >= 0", name="ck_ai_builder_job_file_count"),
        db.Index("ix_ai_builder_jobs_admin_created", "admin_user_id", "created_at"),
    )


class AIBuilderProject(db.Model):
    __tablename__ = "ai_builder_projects"

    id = db.Column(db.String(36), primary_key=True)
    admin_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    project_type = db.Column(db.String(16), nullable=False)
    description = db.Column(db.String(1500), nullable=False, default="", server_default="")
    files_json = db.Column(db.Text, nullable=False)
    source_sha256 = db.Column(db.String(64), nullable=False)
    external_code_consent = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    status = db.Column(db.String(16), nullable=False, default="active", server_default="active")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    admin_user = db.relationship("User", backref=db.backref("ai_builder_projects", cascade="all, delete-orphan"))

    __table_args__ = (
        db.CheckConstraint(
            "project_type IN ('flask', 'python', 'static')",
            name="ck_ai_builder_project_type",
        ),
        db.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_ai_builder_project_status",
        ),
        db.Index("ix_ai_builder_projects_admin_updated", "admin_user_id", "updated_at"),
    )


class AIBuilderPatch(db.Model):
    __tablename__ = "ai_builder_patches"

    id = db.Column(db.String(36), primary_key=True)
    project_id = db.Column(
        db.String(36), db.ForeignKey("ai_builder_projects.id", ondelete="CASCADE"), nullable=False
    )
    admin_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    base_sha256 = db.Column(db.String(64), nullable=False)
    candidate_sha256 = db.Column(db.String(64), nullable=False)
    diff_text = db.Column(db.Text, nullable=False)
    candidate_files_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="draft", server_default="draft")
    test_status = db.Column(db.String(16), nullable=False, default="not_run", server_default="not_run")
    test_output = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    tested_at = db.Column(db.DateTime(timezone=True), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    project = db.relationship("AIBuilderProject", backref=db.backref("patches", cascade="all, delete-orphan"))
    admin_user = db.relationship("User", foreign_keys=[admin_user_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft', 'tested', 'approved', 'rejected')",
            name="ck_ai_builder_patch_status",
        ),
        db.CheckConstraint(
            "test_status IN ('not_run', 'passed', 'failed', 'unavailable', 'no_tests')",
            name="ck_ai_builder_patch_test_status",
        ),
        db.Index("ix_ai_builder_patches_project_created", "project_id", "created_at"),
    )


class AIGuardianScan(db.Model):
    __tablename__ = "ai_guardian_scans"

    id = db.Column(db.String(36), primary_key=True)
    project_id = db.Column(
        db.String(36), db.ForeignKey("ai_builder_projects.id", ondelete="CASCADE"), nullable=False
    )
    admin_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    trigger = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="queued", server_default="queued")
    source_sha256 = db.Column(db.String(64), nullable=False)
    queue_signature = db.Column(db.String(64), nullable=False)
    result_summary = db.Column(db.String(1000), nullable=True)
    scanner_version = db.Column(db.String(32), nullable=False, default="1", server_default="1")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    project = db.relationship("AIBuilderProject", backref=db.backref("guardian_scans", cascade="all, delete-orphan"))

    __table_args__ = (
        db.CheckConstraint(
            "trigger IN ('manual', 'deployment', 'nightly')",
            name="ck_ai_guardian_scan_trigger",
        ),
        db.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'warning', 'failed')",
            name="ck_ai_guardian_scan_status",
        ),
        db.Index("ix_ai_guardian_scans_project_created", "project_id", "created_at"),
        db.Index("ix_ai_guardian_scans_queue", "status", "created_at"),
    )


class AIGuardianFinding(db.Model):
    __tablename__ = "ai_guardian_findings"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.String(36), db.ForeignKey("ai_builder_projects.id", ondelete="CASCADE"), nullable=False
    )
    first_scan_id = db.Column(
        db.String(36), db.ForeignKey("ai_guardian_scans.id", ondelete="CASCADE"), nullable=False
    )
    latest_scan_id = db.Column(
        db.String(36), db.ForeignKey("ai_guardian_scans.id", ondelete="CASCADE"), nullable=False
    )
    fingerprint = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(12), nullable=False)
    rule_id = db.Column(db.String(48), nullable=False)
    file_path = db.Column(db.String(240), nullable=False)
    line_number = db.Column(db.Integer, nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="open", server_default="open")
    confirmed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    confirmation_note = db.Column(db.String(500), nullable=True)
    first_notified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("project_id", "fingerprint", name="uq_ai_guardian_finding_project_fingerprint"),
        db.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_ai_guardian_finding_severity",
        ),
        db.CheckConstraint(
            "status IN ('open', 'acknowledged', 'fixed', 'false_positive')",
            name="ck_ai_guardian_finding_status",
        ),
        db.CheckConstraint("line_number >= 1", name="ck_ai_guardian_finding_line"),
        db.Index("ix_ai_guardian_findings_project_status", "project_id", "status"),
    )


class AIGuardianLesson(db.Model):
    __tablename__ = "ai_guardian_lessons"

    id = db.Column(db.String(36), primary_key=True)
    admin_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    patch_id = db.Column(
        db.String(36), db.ForeignKey("ai_builder_patches.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.String(140), nullable=False)
    content = db.Column(db.String(2000), nullable=False)
    content_sha256 = db.Column(db.String(64), nullable=False, unique=True)
    status = db.Column(db.String(16), nullable=False, default="proposed", server_default="proposed")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    admin_user = db.relationship("User", foreign_keys=[admin_user_id])
    patch = db.relationship("AIBuilderPatch", backref=db.backref("lessons", cascade="all, delete-orphan"))
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name="ck_ai_guardian_lesson_status",
        ),
        db.Index("ix_ai_guardian_lessons_admin_created", "admin_user_id", "created_at"),
    )


class AIProductPriceHistory(db.Model):
    __tablename__ = "ai_product_price_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    regular_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_price = db.Column(db.Numeric(10, 2), nullable=True)
    effective_price = db.Column(db.Numeric(10, 2), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        db.CheckConstraint("regular_price >= 0", name="ck_ai_price_history_regular_nonnegative"),
        db.CheckConstraint("discount_price IS NULL OR discount_price >= 0",
                           name="ck_ai_price_history_discount_nonnegative"),
        db.CheckConstraint("effective_price >= 0", name="ck_ai_price_history_effective_nonnegative"),
        db.Index("ix_ai_price_history_product_recorded", "product_id", "recorded_at"),
    )


class AIProductPriceAlert(db.Model):
    __tablename__ = "ai_product_price_alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    target_price = db.Column(db.Numeric(10, 2), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    notified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_ai_price_alert_user_product"),
        db.CheckConstraint("target_price >= 0", name="ck_ai_price_alert_target_nonnegative"),
        db.Index("ix_ai_price_alert_product_active", "product_id", "active"),
    )


class AIUserMemory(db.Model):
    __tablename__ = "ai_user_memories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", backref=db.backref("ai_memories", cascade="all, delete-orphan"))


class AIKnowledgeChunk(db.Model):
    __tablename__ = "ai_knowledge_chunks"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(240), nullable=False, index=True)
    scope = db.Column(db.String(24), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(EmbeddingVector, nullable=True)
    content_hash = db.Column(db.String(64), nullable=False, unique=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        db.CheckConstraint("scope IN ('public', 'customer', 'seller', 'admin', 'rider', 'security')",
                           name="ck_ai_knowledge_scope"),
    )
