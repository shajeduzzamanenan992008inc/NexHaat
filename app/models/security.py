from datetime import UTC, datetime

from ..extensions import db


class AuthThrottle(db.Model):
    __tablename__ = "auth_throttles"

    key_hash = db.Column(db.String(64), primary_key=True)
    failures = db.Column(db.Integer, nullable=False, default=0)
    window_started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    blocked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_attempt_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    __table_args__ = (
        db.CheckConstraint("failures >= 0", name="ck_auth_throttle_failures_nonnegative"),
        db.Index("ix_auth_throttles_last_attempt", "last_attempt_at"),
    )


class AdminLoginChallenge(db.Model):
    __tablename__ = "admin_login_challenges"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash = db.Column(db.String(64), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "failed_attempts >= 0", name="ck_admin_login_challenges_failed_attempts_nonnegative"
        ),
        db.Index("ix_admin_login_challenges_user_sent", "user_id", "sent_at"),
    )


class RegistrationChallenge(db.Model):
    __tablename__ = "registration_challenges"

    id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_data = db.Column(db.JSON, nullable=False)
    locale = db.Column(db.String(12), nullable=True)
    code_hash = db.Column(db.String(64), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint("role IN ('customer', 'seller')", name="ck_registration_challenge_role_valid"),
        db.CheckConstraint(
            "failed_attempts >= 0", name="ck_registration_challenges_failed_attempts_nonnegative"
        ),
        db.Index("ix_registration_challenges_email_sent", "email", "sent_at"),
    )


class PhoneOtpChallenge(db.Model):
    __tablename__ = "phone_otp_challenges"

    id = db.Column(db.String(64), primary_key=True)
    phone_canonical = db.Column(db.String(20), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    purpose = db.Column(db.String(32), nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    provider_message_id = db.Column(db.String(128), nullable=True)
    locale = db.Column(db.String(12), nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "failed_attempts >= 0", name="ck_phone_otp_challenges_failed_attempts_nonnegative"
        ),
        db.Index("ix_phone_otp_challenges_phone_sent", "phone_canonical", "sent_at"),
    )


class PhoneOtpThrottle(db.Model):
    __tablename__ = "phone_otp_throttles"

    key_hash = db.Column(db.String(64), primary_key=True)
    failures = db.Column(db.Integer, nullable=False, default=0)
    window_started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    blocked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_attempt_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    __table_args__ = (
        db.CheckConstraint("failures >= 0", name="ck_phone_otp_throttle_failures_nonnegative"),
        db.Index("ix_phone_otp_throttles_last_attempt", "last_attempt_at"),
    )


class UserTwoFactor(db.Model):
    __tablename__ = "user_two_factor"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    encrypted_secret = db.Column(db.LargeBinary, nullable=False)
    encryption_key_version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="0", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_used_step = db.Column(db.BigInteger, nullable=True)

    __table_args__ = (
        db.CheckConstraint("encryption_key_version >= 1", name="ck_user_two_factor_key_version_positive"),
    )

    user = db.relationship("User", backref=db.backref("two_factor", uselist=False, cascade="all, delete-orphan"))


class UserBackupCode(db.Model):
    __tablename__ = "user_backup_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.Index("ix_user_backup_codes_user_used", "user_id", "used_at"),
    )

    user = db.relationship("User", backref=db.backref("backup_codes", cascade="all, delete-orphan"))

