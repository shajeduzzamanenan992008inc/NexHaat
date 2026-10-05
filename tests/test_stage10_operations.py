from types import SimpleNamespace

from sqlalchemy.exc import SQLAlchemyError

from app.routes import main as main_routes


def test_health_probes_distinguish_liveness_and_readiness(client):
    assert client.get("/health/live").get_json() == {"status": "ok"}
    assert client.get("/health/ready").get_json() == {"status": "ok"}
    assert client.get("/health").get_json() == {"status": "ok"}
    assert client.get("/health/db").get_json() == {"status": "ok"}


def test_liveness_stays_available_when_database_readiness_fails(client, monkeypatch):
    class OfflineSession:
        @staticmethod
        def execute(_statement):
            raise SQLAlchemyError("simulated unavailable database")

        @staticmethod
        def rollback():
            pass

    monkeypatch.setattr(main_routes, "db", SimpleNamespace(session=OfflineSession()))

    assert client.get("/health/live").status_code == 200
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}


def test_server_timing_is_opt_in(client):
    client.application.config["APP_TIMING_ENABLED"] = False
    assert "Server-Timing" not in client.get("/health/live").headers

    client.application.config["APP_TIMING_ENABLED"] = True
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.headers["Server-Timing"].startswith("app;dur=")


def test_media_smoke_command_refuses_external_write_without_explicit_flag(client):
    result = client.application.test_cli_runner().invoke(args=["catalog-media-smoke-check"])

    assert result.exit_code == 2
    assert "--confirm-external-write" in result.output


def test_restore_command_requires_explicit_target_confirmation(client, tmp_path, monkeypatch):
    source = tmp_path / "backup.sqlite3"
    source.write_bytes(b"verified-backup-placeholder")
    restored = []
    monkeypatch.setattr("app.services.backup.restore_database", lambda path: restored.append(path))
    runner = client.application.test_cli_runner()

    refused = runner.invoke(args=["restore-db", "--from", str(source)])
    assert refused.exit_code == 2
    assert "--confirm-target" in refused.output
    assert not restored

    accepted = runner.invoke(args=["restore-db", "--from", str(source), "--confirm-target"])
    assert accepted.exit_code == 0
    assert restored == [source]


def test_production_postgres_url_requires_encrypted_transport():
    from sqlalchemy.engine import make_url

    from app.config import enforce_production_database_tls

    local_url = "postgresql+psycopg://user:password@db.example.test/nexhaat"
    secured = enforce_production_database_tls(local_url, "production")
    assert make_url(secured).query["sslmode"] == "require"
    assert "password" in secured

    weak_url = local_url + "?sslmode=prefer&application_name=nexhaat"
    upgraded = make_url(enforce_production_database_tls(weak_url, "production"))
    assert upgraded.query["sslmode"] == "require"
    assert upgraded.query["application_name"] == "nexhaat"

    stronger_url = local_url + "?sslmode=verify-full"
    assert enforce_production_database_tls(stronger_url, "production") == stronger_url
    assert enforce_production_database_tls(local_url, "development") == local_url


def test_production_check_reports_missing_settings_without_exposing_values(client):
    client.application.config.update(
        SECRET_KEY="short",
        SESSION_COOKIE_SECURE=False,
        PUBLIC_BASE_URL="",
        BREVO_API_KEY=None,
        MAIL_DEFAULT_SENDER=None,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        ADMIN_EMAIL=None,
        SSLCOMMERZ_STORE_ID="",
        SSLCOMMERZ_STORE_PASSWORD="",
        INVOICE_FONT_PATH="",
        CATALOG_MEDIA_BUCKET=None,
        CATALOG_MEDIA_PUBLIC_BASE_URL="",
        CATALOG_VIRUS_SCANNER="missing-stage10-scanner",
    )
    result = client.application.test_cli_runner().invoke(args=["production-check"])

    assert result.exit_code == 1
    assert "Production readiness review found open items" in result.output
    assert "PostgreSQL" in result.output
    assert "missing-stage10-scanner" not in result.output
