from app.services import sms


class DummyAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def send(self, phone, message, sender_id=None):
        self.calls.append((phone, message, sender_id))
        return self.result


def test_send_phone_otp_disabled_by_default(app):
    with app.app_context():
        success, error = sms.send_phone_otp("+8801712345678")
        assert success is False
        assert error == "SMS_DISABLED"


def test_send_phone_otp_invalid_phone(app):
    app.config["SMS_ENABLED"] = True
    with app.app_context():
        success, error = sms.send_phone_otp("12345")
        assert success is False
        assert error == "INVALID_PHONE"


def test_verify_phone_otp_expired(app):
    app.config["SMS_ENABLED"] = True
    with app.app_context():
        # Create an expired challenge directly
        import secrets
        from datetime import UTC, datetime, timedelta

        from app.extensions import db
        from app.models import PhoneOtpChallenge
        from app.routes.auth import _reset_code_digest

        challenge = PhoneOtpChallenge(
            id=secrets.token_urlsafe(32),
            phone_canonical="+8801712345678",
            purpose="verify",
            code_hash=_reset_code_digest("123456"),
            sent_at=datetime.now(UTC) - timedelta(minutes=20),
            expires_at=datetime.now(UTC) - timedelta(minutes=10),
            failed_attempts=0,
        )
        db.session.add(challenge)
        db.session.commit()

        success, error = sms.verify_phone_otp("+8801712345678", "123456")
        assert success is False
        assert error == "CODE_EXPIRED"


def test_verify_phone_otp_wrong_code(app):
    app.config["SMS_ENABLED"] = True
    with app.app_context():
        import secrets
        from datetime import UTC, datetime, timedelta

        from app.extensions import db
        from app.models import PhoneOtpChallenge
        from app.routes.auth import _reset_code_digest

        challenge = PhoneOtpChallenge(
            id=secrets.token_urlsafe(32),
            phone_canonical="+8801712345678",
            purpose="verify",
            code_hash=_reset_code_digest("123456"),
            sent_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            failed_attempts=0,
        )
        db.session.add(challenge)
        db.session.commit()

        success, error = sms.verify_phone_otp("+8801712345678", "000000")
        assert success is False
        assert error == "INVALID_CODE"
