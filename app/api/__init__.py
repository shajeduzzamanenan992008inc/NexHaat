"""Versioned JSON REST API (Bravo-compatible), mounted under ``/api/v1``.

The API is intentionally thin: it reuses the shared services and repositories
used by the server-rendered pages so it stays frontend-independent and can be
consumed by the website, Bravo, or a future mobile client.

All blueprint setup happens at import time. ``create_app`` may run many times
(for tests and workers), so a registered blueprint must not be modified later.
"""

from flask import Blueprint, request

from .errors import ApiError, register_error_handlers
from .routes.admin import admin_api
from .routes.auth import auth_api
from .routes.banners import banners_api
from .routes.catalog import catalog_api
from .routes.commerce import commerce_api
from .routes.health import health_api
from .routes.notifications import notifications_api
from .routes.wishlist import wishlist_api

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# Error handlers and sub-blueprints are set up once, before first registration.
register_error_handlers(api_bp)


@api_bp.before_request
def validate_json_object():
    """Reject JSON arrays and scalar values before route handlers access fields."""
    if request.is_json:
        payload = request.get_json(silent=True)
        if payload is not None and not isinstance(payload, dict):
            raise ApiError(
                "The request body must be a JSON object.",
                "VALIDATION_ERROR",
                422,
            )


api_bp.register_blueprint(health_api)
api_bp.register_blueprint(auth_api)
api_bp.register_blueprint(admin_api)
api_bp.register_blueprint(catalog_api)
api_bp.register_blueprint(commerce_api)
api_bp.register_blueprint(notifications_api)
api_bp.register_blueprint(wishlist_api)
api_bp.register_blueprint(banners_api)


def register_api(app):
    """Attach the prepared versioned API blueprint to a Flask app."""
    app.register_blueprint(api_bp)

