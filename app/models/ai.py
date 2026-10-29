"""Minimal persisted AI request limits and customer alert preferences."""

from datetime import UTC, datetime

from ..extensions import db


class AIRequestWindow(db.Model):
    __tablename__ = "ai_request_windows"

    principal_hash = db.Column(db.String(64), primary_key=True)
    window_started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    request_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    updated_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
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
    last_smart_notification_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_cart_reminder_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_recommendation_notification_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )
    user = db.relationship("User", backref=db.backref("ai_preferences", uselist=False, cascade="all, delete-orphan"))
