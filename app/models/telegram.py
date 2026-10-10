from datetime import datetime, timezone

from ..extensions import db


class ProcessedTelegramUpdate(db.Model):
    __tablename__ = "processed_telegram_updates"

    id = db.Column(db.Integer, primary_key=True)
    bot_name = db.Column(db.String(20), nullable=False)
    update_id = db.Column(db.BigInteger, nullable=False)
    state = db.Column(db.String(16), nullable=False, default="processing")
    attempts = db.Column(db.Integer, nullable=False, default=1)
    received_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    __table_args__ = (
        db.UniqueConstraint("bot_name", "update_id", name="uq_telegram_update_bot_id"),
        db.CheckConstraint(
            "state IN ('processing', 'processed', 'failed')", name="ck_telegram_update_state"
        ),
        db.CheckConstraint("attempts > 0", name="ck_telegram_update_attempts_positive"),
    )


class TelegramRateLimit(db.Model):
    __tablename__ = "telegram_rate_limits"

    id = db.Column(db.Integer, primary_key=True)
    bot_name = db.Column(db.String(20), nullable=False)
    telegram_user_hash = db.Column(db.String(64), nullable=False)
    window_started_at = db.Column(db.BigInteger, nullable=False)
    request_count = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (
        db.UniqueConstraint("bot_name", "telegram_user_hash", name="uq_telegram_rate_limit_user"),
        db.CheckConstraint("request_count > 0", name="ck_telegram_rate_limit_count_positive"),
    )


class TelegramIdentity(db.Model):
    __tablename__ = "telegram_identities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    telegram_user_id = db.Column(db.BigInteger, nullable=False, unique=True)
    linked_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", backref=db.backref("telegram_identity", uselist=False))


class TelegramAccountLinkChallenge(db.Model):
    __tablename__ = "telegram_account_link_challenges"

    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, nullable=False, unique=True)
    code_digest = db.Column(db.String(64), nullable=False, unique=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    __table_args__ = (
        db.CheckConstraint("failed_attempts >= 0", name="ck_telegram_link_attempts_nonnegative"),
    )


class CustomerCartItem(db.Model):
    __tablename__ = "customer_cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id = db.Column(
        db.Integer, db.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True
    )
    item_key = db.Column(db.String(40), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    __table_args__ = (
        db.UniqueConstraint("user_id", "item_key", name="uq_customer_cart_user_item"),
        db.CheckConstraint("quantity >= 1 AND quantity <= 20", name="ck_customer_cart_quantity"),
    )
    user = db.relationship("User", backref=db.backref("cart_items", cascade="all, delete-orphan"))
    product = db.relationship("Product")
    variant = db.relationship("ProductVariant")


class TelegramSecurityAlert(db.Model):
    __tablename__ = "telegram_security_alerts"

    id = db.Column(db.Integer, primary_key=True)
    audit_event_id = db.Column(
        db.Integer, db.ForeignKey("audit_events.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    audit_event = db.relationship("AuditEvent")
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')", name="ck_telegram_alert_status"
        ),
        db.CheckConstraint("attempts >= 0", name="ck_telegram_alert_attempts_nonnegative"),
    )
