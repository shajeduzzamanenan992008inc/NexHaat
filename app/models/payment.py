"""Payment, refund, and seller-settlement records."""

from datetime import UTC, datetime

from ..extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    checkout_group = db.Column(db.String(40), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="BDT", server_default="BDT")
    status = db.Column(db.String(24), nullable=False, default="pending", server_default="pending")
    bank_tran_id = db.Column(db.String(80), nullable=True, index=True)
    validation_id = db.Column(db.String(50), nullable=True)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        db.CheckConstraint(
            "status IN ('pending', 'paid', 'review_required', 'partially_refunded', 'refunded', 'expired', 'cancelled')",
            name="ck_payments_status_valid",
        ),
        db.CheckConstraint("currency = 'BDT'", name="ck_payments_currency_valid"),
    )

    orders = db.relationship("Order", back_populates="payment")
    attempts = db.relationship(
        "PaymentAttempt", back_populates="payment", cascade="all, delete-orphan",
        order_by="PaymentAttempt.created_at",
    )
    refunds = db.relationship(
        "PaymentRefund", back_populates="payment", cascade="all, delete-orphan",
        order_by="PaymentRefund.created_at.desc()",
    )


class PaymentAttempt(db.Model):
    __tablename__ = "payment_attempts"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id = db.Column(db.String(30), nullable=False, unique=True)
    session_key = db.Column(db.String(80), nullable=True)
    gateway_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(24), nullable=False, default="initiating", server_default="initiating")
    validation_id = db.Column(db.String(50), nullable=True)
    bank_tran_id = db.Column(db.String(80), nullable=True, index=True)
    validated_amount = db.Column(db.Numeric(10, 2), nullable=True)
    validated_currency = db.Column(db.String(3), nullable=True)
    risk_level = db.Column(db.Integer, nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('initiating', 'pending', 'paid', 'review_required', 'failed', 'cancelled', 'expired', 'superseded', 'duplicate_paid')",
            name="ck_payment_attempts_status_valid",
        ),
        db.CheckConstraint("risk_level IS NULL OR risk_level IN (0, 1)", name="ck_payment_attempts_risk_level"),
    )

    payment = db.relationship("Payment", back_populates="attempts")


class PaymentRefund(db.Model):
    __tablename__ = "payment_refunds"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    refund_trans_id = db.Column(db.String(30), nullable=False, unique=True)
    provider_refund_id = db.Column(db.String(80), nullable=True, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="initiating", server_default="initiating")
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_payment_refunds_amount_positive"),
        db.CheckConstraint(
            "status IN ('initiating', 'processing', 'refunded', 'failed')",
            name="ck_payment_refunds_status_valid",
        ),
    )

    payment = db.relationship("Payment", back_populates="refunds")
    order = db.relationship("Order")
    created_by = db.relationship("User")


class SellerPayout(db.Model):
    __tablename__ = "seller_payouts"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference = db.Column(db.String(120), nullable=False)
    note = db.Column(db.String(500), nullable=True)
    recorded_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (db.CheckConstraint("amount > 0", name="ck_seller_payouts_amount_positive"),)

    seller = db.relationship("User", foreign_keys=[seller_id])
    recorded_by = db.relationship("User", foreign_keys=[recorded_by_id])
    entries = db.relationship("SellerLedgerEntry", back_populates="payout")


class SellerLedgerEntry(db.Model):
    __tablename__ = "seller_ledger_entries"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payout_id = db.Column(
        db.Integer, db.ForeignKey("seller_payouts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    entry_type = db.Column(db.String(24), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    idempotency_key = db.Column(db.String(100), nullable=False, unique=True)
    eligible_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        db.CheckConstraint(
            "entry_type IN ('sale', 'commission', 'refund', 'commission_refund', 'payout')",
            name="ck_seller_ledger_entry_type",
        ),
        db.CheckConstraint("amount <> 0", name="ck_seller_ledger_amount_nonzero"),
        db.Index("ix_seller_ledger_seller_eligible", "seller_id", "eligible_at"),
    )

    seller = db.relationship("User", foreign_keys=[seller_id])
    order = db.relationship("Order")
    payment = db.relationship("Payment")
    payout = db.relationship("SellerPayout", back_populates="entries")
