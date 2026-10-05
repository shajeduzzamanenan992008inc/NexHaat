"""Production launch readiness checks used by the ``production-check`` CLI."""

import shutil
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

from ..config import POSTGRES_TLS_MODES


def _scanner_available(config):
    scanner = (config.get("CATALOG_VIRUS_SCANNER") or "").strip()
    if not scanner:
        return False
    return shutil.which(scanner) is not None or Path(scanner).is_file()


def production_readiness(config):
    """Return (ok, issues) describing anything blocking a production launch."""
    issues = []

    secret = config.get("SECRET_KEY") or ""
    if secret == "dev-only-change-me" or len(secret) < 32:
        issues.append("SECRET_KEY must be a random value of at least 32 characters.")

    if not config.get("SESSION_COOKIE_SECURE"):
        issues.append("SESSION_COOKIE_SECURE must be enabled for HTTPS deployments.")

    parsed = urlsplit((config.get("PUBLIC_BASE_URL") or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        issues.append("PUBLIC_BASE_URL must be a canonical HTTPS site URL.")

    if not (config.get("BREVO_API_KEY") and config.get("MAIL_DEFAULT_SENDER")):
        issues.append("Set BREVO_API_KEY and MAIL_DEFAULT_SENDER so transaction email can send.")

    database_uri = (config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    try:
        database_url = make_url(database_uri) if database_uri else None
    except Exception:  # noqa: BLE001 - report invalid configuration without exposing URL contents
        database_url = None
    if database_url is None:
        issues.append("Set DATABASE_URL to a valid PostgreSQL connection for production.")
    elif database_url.get_backend_name() == "sqlite":
        issues.append("Use a managed PostgreSQL DATABASE_URL instead of SQLite in production.")
    elif database_url.get_backend_name() != "postgresql":
        issues.append("Set DATABASE_URL to a PostgreSQL connection for production.")
    else:
        sslmode = database_url.query.get("sslmode")
        if not isinstance(sslmode, str) or sslmode.lower() not in POSTGRES_TLS_MODES:
            issues.append("Use sslmode=require or stronger for encrypted PostgreSQL connections.")

    if not (config.get("ADMIN_EMAIL") or "").strip():
        issues.append("Set ADMIN_EMAIL so the primary Admin account can be provisioned.")

    if not (config.get("SSLCOMMERZ_STORE_ID") and config.get("SSLCOMMERZ_STORE_PASSWORD")):
        issues.append("Set SSLCOMMERZ_STORE_ID and SSLCOMMERZ_STORE_PASSWORD before enabling online payments.")
    elif config.get("SSLCOMMERZ_SANDBOX", True):
        issues.append("Disable SSLCOMMERZ_SANDBOX and use live credentials before accepting production payments.")

    font_path = (config.get("INVOICE_FONT_PATH") or "").strip()
    if not font_path or not Path(font_path).is_file():
        issues.append("Set INVOICE_FONT_PATH to a Unicode font so invoices render non-Latin scripts.")

    media_public_url = (config.get("CATALOG_MEDIA_PUBLIC_BASE_URL") or "").strip()
    if not (config.get("CATALOG_MEDIA_BUCKET") and media_public_url):
        issues.append("Configure the catalog media bucket and public URL before enabling uploads.")
    elif (
        urlsplit(media_public_url).scheme != "https"
        or not urlsplit(media_public_url).hostname
        or urlsplit(media_public_url).username
        or urlsplit(media_public_url).password
        or urlsplit(media_public_url).query
        or urlsplit(media_public_url).fragment
    ):
        issues.append("CATALOG_MEDIA_PUBLIC_BASE_URL must be a clean HTTPS URL for production image delivery.")

    media_endpoint = (config.get("CATALOG_MEDIA_ENDPOINT_URL") or "").strip()
    if media_endpoint:
        endpoint = urlsplit(media_endpoint)
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.query
            or endpoint.fragment
        ):
            issues.append("CATALOG_MEDIA_ENDPOINT_URL must be a clean HTTPS endpoint for production storage.")

    if not _scanner_available(config):
        issues.append("Install the configured ClamAV scanner so catalog uploads can be scanned.")

    return (not issues), issues
