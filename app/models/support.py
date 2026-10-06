"""Explicit customer-initiated support cases, separate from AI chat memory."""

from datetime import datetime, timezone

from ..extensions import db


class SupportConversation(db.Model):
    __tablename__ = "support_conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    subject = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(24), nullable=False, default="other", server_default="other")
    status = db.Column(db.String(16), nullable=False, default="open", server_default="open", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), index=True)
    __table_args__ = (
        db.CheckConstraint("status IN ('open', 'pending', 'closed')", name="ck_support_conversation_status"),
        db.CheckConstraint("category IN ('order', 'delivery', 'returns', 'account', 'product', 'other')", name="ck_support_conversation_category"),
        db.Index("ix_support_conversations_status_updated", "status", "updated_at"),
    )
    messages = db.relationship("SupportMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="SupportMessage.created_at")


class SupportMessage(db.Model):
    __tablename__ = "support_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("support_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_role = db.Column(db.String(12), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    __table_args__ = (
        db.CheckConstraint("sender_role IN ('customer', 'staff')", name="ck_support_message_sender_role"),
        db.CheckConstraint("length(trim(body)) BETWEEN 1 AND 5000", name="ck_support_message_body_length"),
    )
    conversation = db.relationship("SupportConversation", back_populates="messages")
    sender = db.relationship("User")
