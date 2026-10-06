from unittest.mock import patch

from app.extensions import db
from app.models import (
    AuditEvent, CustomerProfile, Order, ProcessedTelegramUpdate,
    TelegramAccountLinkChallenge, TelegramIdentity, TelegramRateLimit,
    TelegramSecurityAlert, User,
)
from app.services.audit import record_audit
from app.services.telegram_alerts import deliver_telegram_security_alerts


def telegram_payload(update_id, telegram_user_id, text):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from": {"id": telegram_user_id, "username": "admin"},
            "chat": {"id": telegram_user_id, "type": "private"},
            "text": text,
        },
    }


def configure_bots(app):
    app.config.update(
        TELEGRAM_CUSTOMER_BOT_TOKEN="customer-test-token",
        TELEGRAM_CUSTOMER_WEBHOOK_SECRET="customer-test-secret",
        TELEGRAM_SECURITY_BOT_TOKEN="security-test-token",
        TELEGRAM_SECURITY_WEBHOOK_SECRET="security-test-secret",
        TELEGRAM_SECURITY_ADMIN_IDS="9001",
        TELEGRAM_RATE_LIMIT_PER_MINUTE=30,
        PUBLIC_BASE_URL="https://shop.example.test",
    )


def test_customer_webhook_requires_secret_and_deduplicates_updates(client, app):
    configure_bots(app)
    endpoint = "/telegram/customer/webhook"
    payload = telegram_payload(101, 7001, "/start")
    denied = client.post(endpoint, json=payload)
    assert denied.status_code == 403

    with patch("app.telegram.customer.send_message", return_value=True) as send:
        first = client.post(
            endpoint,
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
        )
        duplicate = client.post(
            endpoint,
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
        )

    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert send.call_count == 1
    with app.app_context():
        update = db.session.query(ProcessedTelegramUpdate).one()
        assert update.bot_name == "customer"
        assert update.state == "processed"
        assert db.session.query(TelegramRateLimit).count() == 1


def test_security_bot_denies_username_spoof_and_records_only_hashed_id(client, app):
    configure_bots(app)
    payload = telegram_payload(202, 7002, "/audit")
    with patch("app.telegram.security.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/security/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "security-test-secret"},
        )
    assert response.status_code == 200
    send.assert_called_once_with("security", 7002, "Access denied.")
    with app.app_context():
        event = db.session.query(AuditEvent).filter_by(
            action="telegram.security_access_denied"
        ).one()
        assert event.target_id != "7002"
        assert len(event.target_id) == 40
        assert event.detail == "allowlist check failed"


def test_security_bot_authorizes_numeric_id_and_returns_read_only_summary(client, app):
    configure_bots(app)
    payload = telegram_payload(303, 9001, "/status")
    with patch("app.telegram.security.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/security/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "security-test-secret"},
        )
    assert response.status_code == 200
    sent_text = send.call_args.args[2]
    assert "Website: online" in sent_text
    assert "Database: healthy" in sent_text


def test_webhook_rejects_malformed_update_and_unconfigured_bot(client, app):
    configure_bots(app)
    invalid = client.post(
        "/telegram/customer/webhook",
        json={"update_id": "invalid"},
        headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
    )
    assert invalid.status_code == 400

    app.config["TELEGRAM_CUSTOMER_BOT_TOKEN"] = ""
    unconfigured = client.post(
        "/telegram/customer/webhook",
        json=telegram_payload(404, 7001, "/start"),
        headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
    )
    assert unconfigured.status_code == 503


def test_telegram_rate_limit_is_per_user_and_persists_in_database(client, app):
    configure_bots(app)
    app.config["TELEGRAM_RATE_LIMIT_PER_MINUTE"] = 1
    endpoint = "/telegram/customer/webhook"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        first = client.post(endpoint, json=telegram_payload(501, 7001, "/help"), headers=headers)
        limited = client.post(endpoint, json=telegram_payload(502, 7001, "/help"), headers=headers)
    assert first.status_code == 200
    assert limited.status_code == 200
    assert send.call_count == 1
    with app.app_context():
        row = db.session.query(TelegramRateLimit).one()
        assert row.telegram_user_hash != "7001"
        assert len(row.telegram_user_hash) == 64
        assert row.request_count == 2


def test_customer_link_code_is_digest_only_and_one_time(client, app):
    configure_bots(app)
    client.application.config["WTF_CSRF_ENABLED"] = False
    customer = User(email="telegram-link@example.com", role="customer")
    customer.set_password("password123")
    customer.customer_profile = CustomerProfile(
        full_name="Linked Customer", phone="01234567890"
    )
    with app.app_context():
        db.session.add(customer)
        db.session.commit()

    assert client.post(
        "/auth/login",
        data={"email": "telegram-link@example.com", "password": "password123"},
    ).status_code == 302

    payload = telegram_payload(606, 7606, "/link")
    with patch("app.telegram.customer.secrets.randbelow", return_value=123456789), patch(
        "app.telegram.customer.send_message", return_value=True
    ) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
        )
    assert response.status_code == 200
    issued_code = "0123456789"
    assert issued_code in send.call_args.args[2]
    with app.app_context():
        challenge = db.session.query(TelegramAccountLinkChallenge).one()
        assert challenge.code_digest != issued_code

    linked = client.post("/auth/account/telegram/link", data={"code": issued_code})
    assert linked.status_code == 302
    replayed = client.post("/auth/account/telegram/link", data={"code": issued_code})
    assert replayed.status_code == 302
    with app.app_context():
        identity = db.session.query(TelegramIdentity).one()
        assert identity.telegram_user_id == 7606
        assert db.session.query(TelegramIdentity).count() == 1
        assert db.session.query(Order).count() == 0


def test_webhook_registration_uses_private_settings_without_printing_secrets(app):
    configure_bots(app)
    customer_token = "customer-super-secret-token"
    webhook_secret = "customer-webhook-secret"
    app.config.update(
        TELEGRAM_CUSTOMER_BOT_TOKEN=customer_token,
        TELEGRAM_CUSTOMER_WEBHOOK_SECRET=webhook_secret,
        TELEGRAM_SECURITY_BOT_TOKEN="",
        TELEGRAM_SECURITY_WEBHOOK_SECRET="",
    )
    response = type("Response", (), {"status_code": 200, "json": lambda self: {"ok": True}})()
    with patch("requests.post", return_value=response) as post:
        result = app.test_cli_runner().invoke(args=["set-telegram-webhooks"])

    assert result.exit_code == 0
    assert customer_token not in result.output
    assert webhook_secret not in result.output
    assert "https://shop.example.test/telegram/customer/webhook" in result.output
    assert post.call_args.kwargs["json"]["secret_token"] == webhook_secret
    assert post.call_args.kwargs["json"]["drop_pending_updates"] is False


def test_security_audit_queues_and_delivers_redacted_alert(app):
    configure_bots(app)
    app.config["TELEGRAM_SECURITY_ADMIN_IDS"] = "9001,9002"
    with app.test_request_context("/"):
        record_audit(
            "auth.admin_login_denied",
            target_id="private-admin@example.com",
            detail="sensitive internal details",
        )
    with app.app_context():
        alert = db.session.query(TelegramSecurityAlert).one()
        assert alert.status == "pending"

        with patch("app.services.telegram_alerts.send_message", return_value=True) as send:
            delivered = deliver_telegram_security_alerts()

        assert delivered == 1
        assert send.call_count == 2
        message = send.call_args.args[2]
        assert "Admin sign-in was denied" in message
        assert "private-admin@example.com" not in message
        assert "sensitive internal details" not in message
        alert = db.session.query(TelegramSecurityAlert).one()
        assert alert.status == "sent"
        assert alert.attempts == 1
