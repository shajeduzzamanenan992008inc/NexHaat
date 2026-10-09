from pathlib import Path
import re
import secrets
import time
import zipfile
from urllib.parse import urlsplit

import click

from flask import Flask, g, render_template, session
from flask_babel import get_locale
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import func, inspect, text

from .api import register_api
from .api.responses import error_response, is_api_request
from .config import get_config
from .extensions import babel, csrf, db, login_manager, migrate
from .i18n import SUPPORTED_LOCALES, get_request_locale


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or get_config())
    if app.config.get("ENVIRONMENT") == "production":
        secret = app.config.get("SECRET_KEY") or ""
        if secret == "dev-only-change-me" or len(secret) < 32:
            raise RuntimeError("Set a random SECRET_KEY of at least 32 characters before starting in production.")
        # Trust only proxy-provided client and scheme headers. X-Host remains
        # untrusted so a client cannot poison externally generated host URLs.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=get_request_locale)

    from .models import AdminProfile, AppSetting, CustomerProfile, User  # noqa: F401
    from .services import ai_notifications, ai_price_alerts  # noqa: F401 - register opt-in product alert hooks
    from .routes.auth import admin_login, auth_bp
    from .routes.ai import ai_bp
    from .routes.ai_builder import ai_builder_bp
    from .routes.ai_builder_workspace import ai_builder_workspace_bp
    from .routes.main import main_bp
    from .routes.notifications import notifications_bp
    from .routes.orders import orders_bp
    from .routes.portals import admin_bp, customer_bp, rider_bp
    from .routes.seller import seller_bp
    from .routes.support import support_bp
    from .routes.wishlist import wishlist_bp
    from .telegram.customer import telegram_customer_bp
    from .telegram.security import telegram_security_bp
    from .security import current_session_user

    app.register_blueprint(main_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(ai_builder_bp)
    app.register_blueprint(ai_builder_workspace_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(seller_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(rider_bp)
    app.register_blueprint(admin_bp)
    # Keep the former URL as the dedicated Admin OTP login entry point.
    app.add_url_rule("/admin/login", endpoint="auth.admin_login", view_func=admin_login, methods=["GET", "POST"])
    app.register_blueprint(orders_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(telegram_customer_bp)
    app.register_blueprint(telegram_security_bp)

    # Versioned, frontend-independent JSON API under /api/v1.
    register_api(app)

    @app.before_request
    def reject_revoked_sessions():
        g.app_request_started_at = time.perf_counter()
        g.current_user = None
        if session.get("user_id") is not None:
            user = current_session_user()
            if user is None:
                session.clear()
            else:
                session["role"] = user.role
                g.current_user = user

    @app.context_processor
    def branding():
        setting = db.session.get(AppSetting, 1)
        logo_path = setting.logo_path if setting and setting.logo_path else "logo.svg"
        if logo_path.lower().endswith(".svg"):
            logo_path = "logo.svg"
        return {
            "app_name": setting.app_name if setting else app.config["APP_NAME"],
            "app_logo": logo_path,
            "min_password_length": app.config["MIN_PASSWORD_LENGTH"],
            "max_password_length": app.config["MAX_PASSWORD_LENGTH"],
            "current_locale": str(get_locale() or app.config["BABEL_DEFAULT_LOCALE"]).replace("-", "_"),
            "supported_locales": SUPPORTED_LOCALES,
        }

    @app.context_processor
    def notification_badge():
        """Expose the signed-in user's unread notification count to templates."""
        user = getattr(g, "current_user", None)
        if user is None:
            return {"unread_notifications": 0}
        from .services.notifications import unread_count

        try:
            return {"unread_notifications": unread_count(user)}
        except Exception:  # noqa: BLE001 - a missing table must not break rendering
            db.session.rollback()
            return {"unread_notifications": 0}

    @app.after_request
    def security_headers(response):
        if app.config.get("APP_TIMING_ENABLED"):
            started_at = getattr(g, "app_request_started_at", None)
            if started_at is not None:
                duration_ms = max(0.0, (time.perf_counter() - started_at) * 1000)
                response.headers.setdefault("Server-Timing", f"app;dur={duration_ms:.2f}")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
        image_sources = ["'self'", "data:", "https://images.unsplash.com"]
        media_origin = urlsplit(app.config.get("CATALOG_MEDIA_PUBLIC_BASE_URL", ""))
        if (
            media_origin.scheme in {"http", "https"}
            and media_origin.hostname
            and not media_origin.username
            and not media_origin.password
        ):
            image_sources.append(f"{media_origin.scheme}://{media_origin.netloc}")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
            f"form-action 'self'; img-src {' '.join(image_sources)}; "
            "style-src 'self' https://cdn.jsdelivr.net; script-src 'self'; "
            "connect-src 'self'",
        )
        if app.config.get("ENVIRONMENT") == "production" and request_is_secure():
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.cli.command("seed-catalog")
    def seed_catalog():
        from .seed import seed_catalog_data

        created = seed_catalog_data()
        click.echo(f"Catalog seeded: {created} records created.")

    @app.cli.command("index-ai-knowledge")
    @click.option("--scope", type=click.Choice(["public", "customer", "seller", "admin", "rider", "security"]), default="public", show_default=True)
    def index_ai_knowledge(scope):
        """Index operator-curated Markdown from docs/ai-knowledge using local embeddings."""
        if not app.config.get("AI_EMBEDDING_BASE_URL") or not app.config.get("AI_EMBEDDING_MODEL"):
            raise click.ClickException("Configure the private AI_EMBEDDING_BASE_URL and AI_EMBEDDING_MODEL first.")
        from .ai.core.knowledge import index_curated_knowledge
        try:
            count = index_curated_knowledge(app.root_path and Path(app.root_path).parent, scope=scope)
        except (OSError, RuntimeError, ValueError) as error:
            db.session.rollback()
            raise click.ClickException("AI knowledge indexing failed safely.") from error
        click.echo(f"Curated AI knowledge chunks indexed: {count} (scope: {scope}).")

    @app.cli.command("benchmark-ai")
    def benchmark_ai():
        """Run private-local AI quality checks without storing prompts or answers."""
        if not (
            app.config.get("AI_LOCAL_ENABLED")
            and app.config.get("AI_LOCAL_BASE_URL")
            and app.config.get("AI_LOCAL_MODEL")
        ):
            raise click.ClickException(
                "Configure the private local AI endpoint and model before running the benchmark."
            )
        from .ai.core.permissions import AI_SCOPE_ADMIN
        from .ai.core.provider import AIService
        from .ai.evaluation import evaluate_ai

        service = AIService(app.config)
        if not service.local_available:
            raise click.ClickException("The private local AI endpoint is not available in this configuration.")
        report = evaluate_ai(lambda prompt: service.respond(
            prompt, scope=AI_SCOPE_ADMIN, allow_external=False,
        ))
        for result in report["results"]:
            state = "PASS" if result["passed"] else "FAIL"
            click.echo(f"{state} {result['category']}: {result['case_id']}")
        click.echo(
            f"Automated checks: {report['passed_count']}/{report['case_count']} passed; "
            "human review is still required. Answers were not stored or printed."
        )
        if report["failed_count"]:
            raise click.ClickException("AI benchmark has failed automated checks.")

    @app.cli.command("import-fdc")
    @click.option("--zip-path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--release", required=True, help="USDA FoodData Central release label, such as 2024-10-31.")
    @click.option("--max-db-mib", default=400, show_default=True, type=click.IntRange(min=1, max=400))
    @click.option("--batch-size", default=2000, show_default=True, type=click.IntRange(min=100, max=10000))
    def import_fdc(zip_path, release, max_db_mib, batch_size):
        """Import a USDA FoodData Central CSV archive within a strict DB size limit."""
        from .services.food_data_import import import_fdc_archive

        try:
            counts = import_fdc_archive(zip_path, release, max_db_mib * 1024 * 1024, batch_size)
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
            raise click.ClickException(str(error)) from error
        click.echo("USDA FoodData Central import completed:")
        for table, count in counts.items():
            click.echo(f"  {table}: {count:,}")

    @app.cli.command("import-foodon")
    @click.option("--owl-path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--max-db-mib", default=400, show_default=True, type=click.IntRange(min=1, max=400))
    @click.option("--batch-size", default=2000, show_default=True, type=click.IntRange(min=100, max=10000))
    def import_foodon(owl_path, max_db_mib, batch_size):
        """Import FoodOn food-product taxonomy terms without inventing records."""
        from .services.food_data_import import import_foodon_ontology

        try:
            count = import_foodon_ontology(owl_path, max_db_mib * 1024 * 1024, batch_size)
        except (OSError, ValueError, RuntimeError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"FoodOn categories imported: {count:,}")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    def create_admin(email, name):
        from .models import AdminProfile, User

        if User.query.filter_by(email=email.lower().strip()).first():
            raise click.ClickException("An account with this email already exists.")
        user = User(email=email.lower().strip(), role="admin")
        # The shared User schema requires a hash; Admin sign-in never accepts it.
        user.set_password(secrets.token_urlsafe(48))
        user.admin_profile = AdminProfile(full_name=name.strip())
        db.session.add(user)
        db.session.commit()
        click.echo("Admin account created.")

    @app.cli.command("ensure-admin")
    def ensure_admin():
        """Create or reconcile the configured primary Admin after migrations."""
        bootstrap_result = _bootstrap_admin(app)
        if bootstrap_result == "not_configured":
            raise click.ClickException("Set ADMIN_EMAIL in the environment before ensuring the primary Admin.")
        messages = {
            "created": "Configured primary Admin account created.",
            "promoted": "Configured account promoted to primary Admin; existing account data was preserved.",
            "profile_created": "Configured primary Admin profile created.",
            "exists": "Configured primary Admin account is ready.",
        }
        click.echo(messages[bootstrap_result])

    @app.cli.command("check-mail")
    def check_mail():
        """Check Brevo credentials and sender status without sending an email."""
        from .services.mail import check_brevo_configuration

        status = check_brevo_configuration(
            app.config.get("BREVO_API_KEY"),
            app.config.get("MAIL_DEFAULT_SENDER"),
            timeout=app.config.get("MAIL_TIMEOUT", 15),
        )
        click.echo(f"Brevo API key configured: {'yes' if status['api_key_configured'] else 'no'}")
        click.echo(f"Brevo API key accepted: {'yes' if status['api_key_valid'] else 'no'}")
        click.echo(f"Mail sender configured: {'yes' if status['sender_configured'] else 'no'}")
        click.echo(f"Mail sender active in Brevo: {'yes' if status['sender_active'] else 'no'}")
        if not status["api_key_valid"] or not status["sender_active"]:
            raise click.ClickException("Brevo mail configuration check failed; no email was sent.")

    @app.cli.command("retry-emails")
    def retry_emails():
        """Retry queued transactional emails that failed to deliver."""
        from .services.mail import retry_pending_emails

        delivered = retry_pending_emails()
        click.echo(f"Queued emails retried: {delivered} delivered.")

    @app.cli.command("retry-telegram-alerts")
    @click.option("--limit", default=50, show_default=True, type=click.IntRange(min=1, max=200))
    def retry_telegram_alerts(limit):
        """Deliver pending Telegram security alerts and external AI notices."""
        from .services.telegram_alerts import deliver_telegram_security_alerts
        from .services.ai_external_notices import deliver_pending_external_call_notices

        delivered = deliver_telegram_security_alerts(limit=limit)
        delivered += deliver_pending_external_call_notices(limit=limit)
        click.echo(f"Telegram security notices delivered: {delivered}.")

    @app.cli.command("guardian-scan")
    @click.option(
        "--trigger",
        type=click.Choice(["nightly", "deployment"]),
        default="nightly",
        show_default=True,
    )
    @click.option("--project-id", default=None, help="Scan one saved Admin Builder project.")
    def guardian_scan(trigger, project_id):
        """Run signed local Guardian scans for nightly monitoring or deployment review."""
        from .routes.ai_builder_workspace import run_guardian_sweep

        result = run_guardian_sweep(trigger=trigger, project_id=project_id)
        click.echo(
            f"Guardian projects: {result['projects']}; completed: {result['completed']}; "
            f"warnings: {result['warnings']}; confirmed blocking findings: {result['blocking_findings']}."
        )
        if trigger == "deployment" and result["blocking_findings"]:
            raise click.ClickException("Deployment blocked by an Admin-confirmed high-risk Guardian finding.")

    @app.cli.command("benchmark-builder")
    @click.option("--minimum-pass-rate", default=70, show_default=True, type=click.IntRange(min=1, max=100))
    def benchmark_builder(minimum_pass_rate):
        """Measure one coding task against hidden tests in the restricted sandbox."""
        if not (
            app.config.get("AI_LOCAL_ENABLED")
            and app.config.get("AI_LOCAL_BASE_URL")
            and app.config.get("AI_LOCAL_MODEL")
        ):
            raise click.ClickException(
                "Configure the private local AI endpoint and model before running the Builder benchmark."
            )
        from .ai.builder.benchmark import BuilderBenchmarkUnavailable, run_builder_benchmark
        from .ai.core.provider import AIService

        service = AIService(app.config)
        try:
            result = run_builder_benchmark(
                service=service,
                image=app.config.get("AI_BUILDER_SANDBOX_IMAGE", ""),
                timeout_seconds=app.config.get("AI_BUILDER_TEST_TIMEOUT_SECONDS", 60),
            )
        except BuilderBenchmarkUnavailable as error:
            raise click.ClickException(str(error)) from error
        click.echo(
            f"Hidden coding tests: {result['passed']}/{result['total']} passed "
            f"({result['score_percent']}%)."
        )
        if result["score_percent"] < minimum_pass_rate:
            raise click.ClickException(
                f"Builder benchmark did not reach the {minimum_pass_rate}% acceptance threshold."
            )

    @app.cli.command("smart-ai-notification-digest")
    @click.option("--limit", default=200, show_default=True, type=click.IntRange(min=1, max=1000))
    def smart_ai_notification_digest(limit):
        """Create rate-capped, opt-in in-app cart and product recommendation alerts."""
        from .services.ai_notifications import send_smart_notification_digest

        result = send_smart_notification_digest(limit=limit)
        click.echo(
            "Created {cart_reminders} cart reminder(s) and {recommendations} recommendation(s); "
            "skipped {skipped}.".format(**result)
        )

    @app.cli.command("expire-payments")
    @click.option("--batch-size", default=200, show_default=True, type=click.IntRange(min=1, max=2000))
    def expire_payments_command(batch_size):
        """Expire unpaid checkout sessions and release their reserved stock."""
        from .services.payments import expire_pending_payments

        total = 0
        while True:
            expired = expire_pending_payments(limit=batch_size)
            total += expired
            if expired < batch_size:
                break
        click.echo(f"Expired online payments and released stock for {total} checkout(s).")

    @app.cli.command("db-size")
    def db_size():
        """Report the current database size against the configured ceiling."""
        from .services.backup import database_ceiling_bytes, database_size_bytes

        size = database_size_bytes()
        ceiling = database_ceiling_bytes()
        click.echo(
            f"Database size: {size / (1024 * 1024):.2f} MiB "
            f"(ceiling {ceiling / (1024 * 1024):.0f} MiB)."
        )

    @app.cli.command("backup-db")
    @click.option("--to", "destination", required=True, type=click.Path(dir_okay=False, path_type=Path))
    def backup_db(destination):
        """Write and verify a database backup."""
        from .services.backup import assert_within_ceiling, backup_database

        try:
            assert_within_ceiling()
            path = backup_database(destination)
        except (OSError, RuntimeError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Backup verified and written to {path}.")

    @app.cli.command("restore-db")
    @click.option("--from", "source", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option(
        "--confirm-target",
        is_flag=True,
        help="Confirm that the configured database is the intended isolated restore target.",
    )
    def restore_db(source, confirm_target):
        """Restore a verified backup over the configured database."""
        if not confirm_target:
            raise click.UsageError(
                "This operation replaces the configured database. Verify that it is an isolated "
                "restore target, then pass --confirm-target."
            )
        from .services.backup import restore_database

        try:
            restore_database(source)
        except (OSError, RuntimeError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Database restored from {source}.")

    @app.cli.command("production-check")
    def production_check():
        """Review production launch readiness and list anything still missing."""
        from .services.review import production_readiness

        ok, issues = production_readiness(app.config)
        if ok:
            click.echo("Production readiness review passed.")
            return
        click.echo("Production readiness review found open items:")
        for issue in issues:
            click.echo(f"  - {issue}")
        raise SystemExit(1)

    @app.cli.command("set-telegram-webhooks")
    @click.option(
        "--bot",
        "selected_bot",
        type=click.Choice(["customer", "security"]),
        default=None,
        help="Register only this bot. By default, every configured bot is registered.",
    )
    def set_telegram_webhooks(selected_bot):
        """Register configured Telegram bots after the public app passes liveness."""
        import requests

        base_url = (app.config.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or (app.config.get("ENVIRONMENT") == "production" and parsed.scheme != "https")
        ):
            raise click.ClickException("Set a valid PUBLIC_BASE_URL before registering webhooks.")

        timeout = max(1, int(app.config.get("TELEGRAM_API_TIMEOUT", 10)))
        try:
            health_response = requests.get(
                f"{base_url}/health/live", timeout=timeout, allow_redirects=False
            )
            health_payload = health_response.json()
        except (requests.RequestException, ValueError) as error:
            raise click.ClickException(
                f"Public application health check failed ({type(error).__name__}); no webhook was changed."
            ) from error
        if (
            health_response.status_code != 200
            or not isinstance(health_payload, dict)
            or health_payload.get("status") != "ok"
        ):
            raise click.ClickException(
                "Public application health check failed; no webhook was changed."
            )

        configured = 0
        bot_configs = (
            ("customer", ["message", "callback_query"]),
            ("security", ["message", "callback_query"]),
        )
        if selected_bot:
            bot_configs = tuple(item for item in bot_configs if item[0] == selected_bot)
        for bot_name, update_types in bot_configs:
            prefix = f"TELEGRAM_{bot_name.upper()}"
            token = app.config.get(f"{prefix}_BOT_TOKEN") or ""
            secret = app.config.get(f"{prefix}_WEBHOOK_SECRET") or ""
            if not token and not secret:
                click.echo(f"{bot_name.title()} bot skipped; credentials are not configured.")
                continue
            if (
                not token or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret)
                or (bot_name == "security" and not app.config.get("TELEGRAM_SECURITY_ADMIN_IDS", "").strip())
            ):
                raise click.ClickException(f"{bot_name.title()} bot configuration is incomplete or invalid.")
            endpoint = f"{base_url}/telegram/{bot_name}/webhook"
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{token}/setWebhook",
                    json={
                        "url": endpoint,
                        "secret_token": secret,
                        "allowed_updates": update_types,
                        "drop_pending_updates": False,
                    },
                    timeout=timeout,
                )
                payload = response.json()
            except (requests.RequestException, ValueError) as error:
                raise click.ClickException(
                    f"{bot_name.title()} webhook registration failed ({type(error).__name__})."
                ) from error
            if response.status_code != 200 or not isinstance(payload, dict) or payload.get("ok") is not True:
                raise click.ClickException(f"{bot_name.title()} webhook registration was rejected.")
            click.echo(f"{bot_name.title()} webhook registered: {endpoint}")
            configured += 1
        if not configured:
            raise click.ClickException("No Telegram bot credentials are configured.")

    @app.cli.command("catalog-media-smoke-check")
    @click.option(
        "--confirm-external-write",
        is_flag=True,
        help="Allow a temporary image upload and cleanup in the configured media bucket.",
    )
    def catalog_media_smoke_check(confirm_external_write):
        """Exercise live image scanning and storage with a disposable image."""
        if not confirm_external_write:
            raise click.UsageError(
                "This command writes and deletes a temporary object in the configured bucket. "
                "Review the target environment, then pass --confirm-external-write."
            )
        from .services.catalog_media import catalog_media_smoke_check as run_smoke_check

        try:
            run_smoke_check()
        except (RuntimeError, ValueError, OSError) as error:
            raise click.ClickException(str(error)) from error
        except Exception as error:  # noqa: BLE001 - avoid printing provider details or credentials
            raise click.ClickException(
                f"Catalog media smoke check failed ({error.__class__.__name__})."
            ) from error
        click.echo("Catalog media scan, sanitized upload, object read, and cleanup passed.")

    @app.errorhandler(404)
    def not_found(error):
        if is_api_request():
            return error_response("NOT_FOUND", "Resource not found.", 404)
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        # Routing-level 405s have no matched blueprint, so handle them here.
        if is_api_request():
            return error_response("METHOD_NOT_ALLOWED", "Method not allowed.", 405)
        return error.get_response()

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        if is_api_request():
            return error_response("INTERNAL_ERROR", "Something went wrong.", 500)
        return render_template("errors/500.html"), 500

    with app.app_context():
        # Local and test databases remain convenient. Production schema changes
        # are applied through Flask-Migrate before serving traffic.
        if app.testing or app.config.get("ENVIRONMENT") != "production":
            db.create_all()
            _ensure_legacy_local_columns()
            _bootstrap_admin(app)

    return app


def _ensure_legacy_local_columns():
    """Keep local databases from the prototype usable during migration setup."""
    profile_tables = ("customers", "admins")
    for table in profile_tables:
        columns = {column["name"] for column in inspect(db.engine).get_columns(table)}
        if "profile_image" not in columns:
            with db.engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN profile_image VARCHAR(255)"))
    user_columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    local_additions = {
        "auth_version": "INTEGER NOT NULL DEFAULT 0",
        "preferred_locale": "VARCHAR(12)",
        "password_reset_hash": "VARCHAR(64)",
        "password_reset_expires_at": "TIMESTAMP",
        "password_reset_sent_at": "TIMESTAMP",
        "password_reset_attempts": "INTEGER NOT NULL DEFAULT 0",
    }
    has_settings = inspect(db.engine).has_table("app_settings")
    with db.engine.begin() as connection:
        for column_name, column_type in local_additions.items():
            if column_name not in user_columns:
                connection.execute(
                    text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                )
        if has_settings:
            connection.execute(
                text("UPDATE app_settings SET app_name = 'NexHaat' WHERE lower(trim(app_name)) = 'freshbite'")
            )


def _bootstrap_admin(app):
    """Make ADMIN_EMAIL the primary OTP-only Admin, preserving existing account data."""
    email = (app.config.get("ADMIN_EMAIL") or "").strip().lower()
    if not email or "@" not in email:
        return "not_configured"

    from .models import AdminProfile, User

    existing = db.session.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        promoted = existing.role != "admin"
        if promoted:
            existing.role = "admin"
            existing.auth_version += 1

        profile_created = existing.admin_profile is None
        if profile_created:
            full_name = (
                (existing.customer_profile.full_name if existing.customer_profile else None)
                or (existing.seller_profile.contact_name if existing.seller_profile else None)
                or (existing.rider_profile.full_name if existing.rider_profile else None)
                or "NexHaat Admin"
            )
            existing.admin_profile = AdminProfile(full_name=full_name)

        if promoted or profile_created:
            db.session.commit()
        if promoted:
            return "promoted"
        if profile_created:
            return "profile_created"
        return "exists"

    admin = User(email=email, role="admin")
    # Keep the required shared-schema field populated with an unusable secret.
    admin.set_password(secrets.token_urlsafe(48))
    admin.admin_profile = AdminProfile(full_name="NexHaat Admin")
    db.session.add(admin)
    db.session.commit()
    return "created"


def request_is_secure():
    from flask import request

    return request.is_secure


# Gunicorn/Azure expects a module-level WSGI object named "app".
app = create_app()
