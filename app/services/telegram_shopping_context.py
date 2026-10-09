"""Short-lived Telegram shopping state without storing message transcripts."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re

from flask import current_app
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..extensions import db
from ..models import TelegramShoppingContext

_CONTEXT_TTL = timedelta(minutes=30)
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _conversation_hash(telegram_user_id):
    if (isinstance(telegram_user_id, bool) or not isinstance(telegram_user_id, int)
            or telegram_user_id <= 0):
        raise ValueError("A valid Telegram user ID is required.")
    secret = current_app.secret_key
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not secret:
        raise RuntimeError("Application secret is required for Telegram context.")
    return hmac.new(
        secret,
        f"telegram-shopping-context:{telegram_user_id}".encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _valid_slug(value):
    return value if isinstance(value, str) and len(value) <= 180 and _SLUG.fullmatch(value) else None


def get_shopping_context(telegram_user_id):
    key = _conversation_hash(telegram_user_id)
    now = datetime.now(timezone.utc)
    row = db.session.get(TelegramShoppingContext, key)
    if row is None:
        return {"products": [], "selected_product": None}
    expiry = row.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        db.session.delete(row)
        db.session.commit()
        return {"products": [], "selected_product": None}
    value = row.context if isinstance(row.context, dict) else {}
    products = []
    raw_products = value.get("products", [])
    if not isinstance(raw_products, list):
        raw_products = []
    for slug in raw_products:
        valid = _valid_slug(slug)
        if valid and valid not in products:
            products.append(valid)
        if len(products) == 5:
            break
    selected = _valid_slug(value.get("selected_product"))
    return {
        "products": products,
        "selected_product": selected if selected in products else None,
    }


def save_shopping_context(telegram_user_id, products, *, selected_product=None):
    key = _conversation_hash(telegram_user_id)
    slugs = []
    for product in products or []:
        slug = _valid_slug(getattr(product, "slug", product))
        if slug and slug not in slugs:
            slugs.append(slug)
        if len(slugs) == 5:
            break
    selected = _valid_slug(selected_product)
    context = {
        "products": slugs,
        "selected_product": selected if selected in slugs else None,
    }
    now = datetime.now(timezone.utc)
    values = {
        "conversation_hash": key,
        "context": context,
        "updated_at": now,
        "expires_at": now + _CONTEXT_TTL,
    }
    table = TelegramShoppingContext.__table__
    dialect = db.session.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else postgres_insert if dialect == "postgresql" else None
    if insert is None:
        raise RuntimeError("Telegram conversation context requires SQLite or PostgreSQL.")
    statement = insert(table).values(**values).on_conflict_do_update(
        index_elements=["conversation_hash"],
        set_={key: values[key] for key in ("context", "updated_at", "expires_at")},
    )
    db.session.execute(statement)
    db.session.execute(delete(table).where(table.c.expires_at <= now))
    db.session.commit()
