import os
import logging
import json
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)
POSTGRES_TLS_MODES = frozenset({"require", "verify-ca", "verify-full"})


def _load_local_environment(path):
    """Load dotenv files or safe development App Service JSON settings.

    The checked-in example uses Azure's Advanced Edit JSON format. A production
    settings export must never silently redirect a local app to its database,
    mail provider, or Telegram bots, so JSON is accepted locally only when the
    file itself declares development and SQLite.
    """
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError:
        return

    try:
        document = json.loads(content)
    except (TypeError, ValueError):
        load_dotenv(path)
        return

    if not isinstance(document, list) or not all(
        isinstance(item, dict) and isinstance(item.get("name"), str)
        for item in document
    ):
        load_dotenv(path)
        return

    values = {
        item["name"]: item.get("value")
        for item in document
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item["name"])
    }
    file_environment = str(values.get("APP_ENV") or "").strip().lower()
    file_database_url = str(values.get("DATABASE_URL") or "").strip()
    try:
        file_database_backend = make_url(file_database_url).get_backend_name()
    except Exception:  # noqa: BLE001 - invalid settings are not loaded locally
        file_database_backend = ""

    active_environment = str(os.environ.get("APP_ENV") or file_environment).strip().lower()
    active_database_url = str(os.environ.get("DATABASE_URL") or file_database_url).strip()
    try:
        active_database_backend = make_url(active_database_url).get_backend_name()
    except Exception:  # noqa: BLE001 - invalid settings are not loaded locally
        active_database_backend = ""

    if not (
        file_environment == "development"
        and file_database_backend == "sqlite"
        and active_environment == "development"
        and active_database_backend == "sqlite"
    ):
        logger.warning(
            "Ignored JSON .env settings: local JSON settings must declare development and SQLite; configure production settings in the hosting environment."
        )
        return

    for name, value in values.items():
        if isinstance(value, (dict, list)):
            continue
        os.environ.setdefault(name, "" if value is None else str(value))


_load_local_environment(BASE_DIR / ".env")


def enforce_production_database_tls(database_url, environment):
    """Require encrypted PostgreSQL transport in production without weakening stronger modes."""
    if not database_url or environment != "production":
        return database_url
    try:
        parsed_url = make_url(database_url)
    except Exception:  # noqa: BLE001 - leave malformed input for production-check to report
        return database_url
    if parsed_url.get_backend_name() != "postgresql":
        return database_url
    sslmode = parsed_url.query.get("sslmode")
    if not isinstance(sslmode, str) or sslmode.lower() not in POSTGRES_TLS_MODES:
        return parsed_url.set(
            query={**parsed_url.query, "sslmode": "require"}
        ).render_as_string(hide_password=False)
    return database_url


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    logger.warning(
        "Invalid boolean value for %s=%r; using default %s.",
        name,
        value,
        default,
    )
    return default


class Config:
    APP_NAME = "NexHaat"
    BABEL_DEFAULT_LOCALE = "en_US"
    BABEL_DEFAULT_TIMEZONE = "Asia/Dhaka"
    BABEL_TRANSLATION_DIRECTORIES = "translations"
    ENVIRONMENT = os.getenv("APP_ENV", "development").lower()
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    _database_url = os.getenv("DATABASE_URL")
    if _database_url and _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if _database_url and _database_url.startswith("postgresql://"):
        _database_url = _database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if _database_url and _database_url.startswith("sqlite:///"):
        _sqlite_path = Path(_database_url.removeprefix("sqlite:///"))
        if not _sqlite_path.is_absolute():
            _database_url = f"sqlite:///{(BASE_DIR / _sqlite_path).resolve()}"
    _database_url = enforce_production_database_tls(_database_url, ENVIRONMENT)
    SQLALCHEMY_DATABASE_URI = _database_url or f"sqlite:///{BASE_DIR / 'instance' / 'food_ordering.sqlite3'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    if (_database_url or "").startswith("sqlite:") or not _database_url:
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {"timeout": 30}
    else:
        SQLALCHEMY_ENGINE_OPTIONS.update(pool_recycle=1800, pool_size=5, max_overflow=10)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "nexhaat_session"
    SESSION_REFRESH_EACH_REQUEST = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", ENVIRONMENT == "production")
    APP_TIMING_ENABLED = _env_bool("APP_TIMING_ENABLED", False)
    WTF_CSRF_TIME_LIMIT = 3600
    MAIL_TIMEOUT = int(os.getenv("MAIL_TIMEOUT", "15"))
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    TELEGRAM_CUSTOMER_BOT_TOKEN = os.getenv("TELEGRAM_CUSTOMER_BOT_TOKEN", "").strip()
    TELEGRAM_CUSTOMER_WEBHOOK_SECRET = os.getenv("TELEGRAM_CUSTOMER_WEBHOOK_SECRET", "").strip()
    TELEGRAM_SECURITY_BOT_TOKEN = os.getenv("TELEGRAM_SECURITY_BOT_TOKEN", "").strip()
    TELEGRAM_SECURITY_WEBHOOK_SECRET = os.getenv("TELEGRAM_SECURITY_WEBHOOK_SECRET", "").strip()
    TELEGRAM_SECURITY_ADMIN_IDS = os.getenv("TELEGRAM_SECURITY_ADMIN_IDS", "")
    TELEGRAM_SUPPORT_URL = os.getenv("TELEGRAM_SUPPORT_URL", "").strip()
    TELEGRAM_RATE_LIMIT_PER_MINUTE = int(os.getenv("TELEGRAM_RATE_LIMIT_PER_MINUTE", "30"))
    TELEGRAM_API_TIMEOUT = int(os.getenv("TELEGRAM_API_TIMEOUT", "10"))
    _mail_sender = os.getenv("MAIL_DEFAULT_SENDER", "").strip()
    MAIL_DEFAULT_SENDER = (
        _mail_sender
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", _mail_sender)
        else None
    )
    _support_email = os.getenv("SUPPORT_EMAIL", "").strip()
    SUPPORT_EMAIL = (
        _support_email
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", _support_email)
        else None
    )
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower() or None
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    SSLCOMMERZ_STORE_ID = os.getenv("SSLCOMMERZ_STORE_ID", "").strip()
    SSLCOMMERZ_STORE_PASSWORD = os.getenv("SSLCOMMERZ_STORE_PASSWORD", "").strip()
    SSLCOMMERZ_SANDBOX = _env_bool("SSLCOMMERZ_SANDBOX", True)
    SSLCOMMERZ_TIMEOUT = int(os.getenv("SSLCOMMERZ_TIMEOUT", "12"))
    PAYMENT_SESSION_MINUTES = int(os.getenv("PAYMENT_SESSION_MINUTES", "15"))
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    MAX_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024
    MAX_RASTER_IMAGE_PIXELS = int(os.getenv("MAX_RASTER_IMAGE_PIXELS", "20000000"))
    MAX_CATALOG_IMAGE_BYTES = int(os.getenv("MAX_CATALOG_IMAGE_BYTES", str(3 * 1024 * 1024)))
    MAX_CATALOG_IMAGE_PIXELS = int(os.getenv("MAX_CATALOG_IMAGE_PIXELS", "40000000"))
    MAX_CATALOG_QUARANTINE_BYTES = int(os.getenv("MAX_CATALOG_QUARANTINE_BYTES", str(100 * 1024 * 1024)))
    CATALOG_QUARANTINE_RETENTION_HOURS = int(os.getenv("CATALOG_QUARANTINE_RETENTION_HOURS", "24"))
    CATALOG_QUARANTINE_FOLDER = os.getenv(
        "CATALOG_QUARANTINE_FOLDER", str(BASE_DIR / "instance" / "quarantine" / "catalog")
    )
    CATALOG_VIRUS_SCANNER = os.getenv("CATALOG_VIRUS_SCANNER", "clamdscan")
    CATALOG_SCAN_TIMEOUT = int(os.getenv("CATALOG_SCAN_TIMEOUT", "20"))
    CATALOG_MEDIA_BUCKET = os.getenv("CATALOG_MEDIA_BUCKET")
    CATALOG_MEDIA_REGION = os.getenv("CATALOG_MEDIA_REGION", "us-east-1")
    CATALOG_MEDIA_ENDPOINT_URL = os.getenv("CATALOG_MEDIA_ENDPOINT_URL")
    CATALOG_MEDIA_PUBLIC_BASE_URL = os.getenv("CATALOG_MEDIA_PUBLIC_BASE_URL", "").strip().rstrip("/")
    CATALOG_MEDIA_KEY_PREFIX = os.getenv("CATALOG_MEDIA_KEY_PREFIX", "products")
    MAX_SEARCH_LENGTH = 100
    CATALOG_PAGE_SIZE = 48
    MIN_PASSWORD_LENGTH = 12 if ENVIRONMENT == "production" else 8
    MAX_PASSWORD_LENGTH = 128
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads" / "profiles")
    BRANDING_UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads" / "branding")
    PROOF_OF_DELIVERY_FOLDER = str(BASE_DIR / "app" / "static" / "uploads" / "delivery")
    MAX_EMAIL_ATTEMPTS = int(os.getenv("MAX_EMAIL_ATTEMPTS", "5"))
    INVOICE_FONT_PATH = os.getenv("INVOICE_FONT_PATH", "").strip()
    MAX_DATABASE_BYTES = int(os.getenv("MAX_DATABASE_BYTES", str(400 * 1024 * 1024)))
    AI_ENABLED = _env_bool("AI_ENABLED", False)
    AI_PROVIDER = os.getenv("AI_PROVIDER", "").strip() or "disabled"
    AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
    AI_MODEL = os.getenv("AI_MODEL", "").strip()
    AI_BASE_URL = os.getenv("AI_BASE_URL", "").strip()
    AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "15"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1024"))
    AI_RATE_LIMIT = int(os.getenv("AI_RATE_LIMIT", "60"))
    AI_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AI_RATE_LIMIT_WINDOW_SECONDS", "60"))
    AI_MAX_TOOL_CALLS = int(os.getenv("AI_MAX_TOOL_CALLS", "5"))
    AI_MAX_CONTEXT_SIZE = int(os.getenv("AI_MAX_CONTEXT_SIZE", "12000"))
    PREFERRED_URL_SCHEME = "https" if ENVIRONMENT == "production" else "http"


class TestingConfig(Config):
    TESTING = True
    ENVIRONMENT = "testing"
    MIN_PASSWORD_LENGTH = 8
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ASYNC_ORDER_EMAILS = False
    AI_ENABLED = False
    AI_PROVIDER = "disabled"
    AI_API_KEY = ""
    AI_MODEL = ""
    AI_BASE_URL = ""


def get_config():
    return TestingConfig if os.getenv("FLASK_TESTING") == "1" else Config
