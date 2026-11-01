import hmac
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...extensions import csrf, db
from ...models import Order, TelegramAccountLinkChallenge, TelegramIdentity, User
from ...services.cart import (
    CartError,
    add_customer_cart_item,
    customer_cart_rows,
    update_customer_cart_item,
)
from ...services.catalog import (
    get_active_categories,
    get_catalog_products,
    get_product_by_slug,
)
from ..common import (
    answer_callback,
    credentials_ready,
    receive_update,
    send_message,
    valid_webhook_secret,
)

telegram_customer_bp = Blueprint(
    "telegram_customer", __name__, url_prefix="/telegram/customer"
)


def _site_url(path):
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"https", "http"} or not parsed.hostname
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or (current_app.config.get("ENVIRONMENT") == "production" and parsed.scheme != "https")
    ):
        return None
    return f"{base}/{path.lstrip('/')}"


def _keyboard(rows):
    return {"inline_keyboard": rows}


def _send_start(chat_id, telegram_user_id):
    shop_url = _site_url("menu")
    if chat_id == telegram_user_id:
        rows = [
            ([{"text": "Shop Now", "url": shop_url}] if shop_url else [{"text": "Shop Now", "callback_data": "cmd|shop"}]),
            [
                {"text": "Search", "callback_data": "cmd|search"},
                {"text": "Categories", "callback_data": "cmd|categories"},
            ],
            [
                {"text": "My Cart", "callback_data": "cmd|cart"},
                {"text": "My Orders", "callback_data": "cmd|orders"},
            ],
            [
                {"text": "My Account", "callback_data": "cmd|account"},
                {"text": "Support", "callback_data": "cmd|support"},
            ],
        ]
    else:
        rows = [[{"text": "Shop Now", "url": shop_url}]] if shop_url else []
    return send_message(
        "customer",
        chat_id,
        "Welcome to NexHaat! Browse products or search the catalog here.\n\nCommands: /shop, /products, /categories, /search <query>, /link, /cart, /orders, /account, /support, /help",
        _keyboard(rows) if rows else None,
    )


def _send_categories(chat_id):
    categories = get_active_categories()
    rows = []
    for category in categories[:20]:
        url = _site_url(f"category/{category.slug}")
        if url:
            rows.append([{"text": category.name[:60], "url": url}])
    text = "Browse active categories:" if rows else "There are no active categories right now."
    return send_message("customer", chat_id, text, _keyboard(rows) if rows else None)


def _send_products(chat_id, query=""):
    from ...ai.marketplace_tools import handle_marketplace_ai_query

    telegram_user_id = getattr(g, "telegram_user_id", None)
    user = _linked_customer(telegram_user_id) if telegram_user_id else None
    if query:
        result = handle_marketplace_ai_query(
            query, user=user, channel="telegram",
            context={"principal": f"telegram:{telegram_user_id}"} if telegram_user_id else None,
        )
        products = result.get("products") or []
        if not products:
            text = result.get("answer") or result.get("fallback") or "I could not find matching catalog products."
            return send_message("customer", chat_id, text[:3500])
        rows = []
        for item in products[:5]:
            slug = item.get("slug")
            if not slug:
                continue
            product = get_product_by_slug(slug)
            if product and product.is_available and product.moderation_status == "approved" and product.available_stock > 0:
                rows.append(product)
    else:
        products, _pagination = get_catalog_products(page=1, per_page=5, in_stock=True)
        rows = products
    if not rows:
        return send_message("customer", chat_id, "No available products matched that search.")

    return _send_product_cards(chat_id, rows)


def _send_product_cards(chat_id, products):
    if not products:
        return send_message("customer", chat_id, "No available products matched that search.")

    lines = ["Matching available products:"]
    rows = []
    for product in products[:5]:
        price = product.discount_price or product.price
        lines.append(f"{product.name[:120]} - BDT {price}")
        url = _site_url(f"food/{product.slug}")
        if url:
            buttons = [{"text": f"View {product.name[:35]}", "url": url}]
            active_variants = [variant for variant in product.variants if variant.is_active and variant.stock_quantity > 0]
            if active_variants:
                if len(active_variants) == 1:
                    buttons.append({"text": "Add", "callback_data": f"product-add|{product.id}|{active_variants[0].id}"})
                else:
                    rows.append(buttons)
                    for variant in active_variants[:5]:
                        option = f"{variant.option_name}: {variant.option_value}"[:25]
                        rows.append([{"text": f"Add {option}",
                                      "callback_data": f"product-add|{product.id}|{variant.id}"}])
                    continue
            elif product.stock_quantity > 0:
                buttons.append({"text": "Add", "callback_data": f"product-add|{product.id}"})
            rows.append(buttons)
    return send_message(
        "customer", chat_id, "\n".join(lines), _keyboard(rows) if rows else None
    )


def _link_digest(code):
    secret = current_app.secret_key
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    return hmac.new(secret, b"telegram-link:" + code.encode("ascii"), "sha256").hexdigest()


def _create_link_code(telegram_user_id):
    identity = db.session.scalar(
        select(TelegramIdentity).where(TelegramIdentity.telegram_user_id == telegram_user_id)
    )
    if identity:
        return None, "linked"
    now = datetime.now(UTC)
    challenge = db.session.scalar(
        select(TelegramAccountLinkChallenge)
        .where(TelegramAccountLinkChallenge.telegram_user_id == telegram_user_id)
        .with_for_update()
    )
    sent_at = challenge.sent_at if challenge else None
    expires_at = challenge.expires_at if challenge else None
    if sent_at and sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=UTC)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        challenge and challenge.consumed_at is None and expires_at and expires_at > now
        and sent_at and (now - sent_at).total_seconds() < 60
    ):
        return None, "cooldown"

    code = f"{secrets.randbelow(10_000_000_000):010d}"
    if challenge is None:
        challenge = TelegramAccountLinkChallenge(telegram_user_id=telegram_user_id)
        db.session.add(challenge)
    challenge.code_digest = _link_digest(code)
    challenge.sent_at = now
    challenge.expires_at = now + timedelta(minutes=10)
    challenge.failed_attempts = 0
    challenge.consumed_at = None
    db.session.commit()
    return code, "created"


def _linked_customer(telegram_user_id):
    identity = db.session.scalar(
        select(TelegramIdentity)
        .options(selectinload(TelegramIdentity.user).selectinload(User.customer_profile))
        .where(TelegramIdentity.telegram_user_id == telegram_user_id)
    )
    user = identity.user if identity else None
    return user if user and user.is_active and user.role == "customer" else None


def _send_account(chat_id, telegram_user_id):
    user = _linked_customer(telegram_user_id)
    if user is None:
        return send_message("customer", chat_id, "Link your NexHaat account first with /link.")
    name = user.customer_profile.full_name if user.customer_profile else "Customer"
    return send_message("customer", chat_id, f"NexHaat account linked. Name: {name[:100]}")


def _send_orders(chat_id, telegram_user_id):
    user = _linked_customer(telegram_user_id)
    if user is None:
        return send_message("customer", chat_id, "Link your NexHaat account first with /link.")
    orders = db.session.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(5)
    ).all()
    if not orders:
        return send_message("customer", chat_id, "No orders were found for your linked account.")
    lines = ["Your recent orders:"]
    for order in orders:
        names = ", ".join(item.product_name[:45] for item in order.items[:3])
        lines.append(f"{order.order_number} | {order.status} | BDT {order.total:.2f}\n{names}")
    url = _site_url("my-orders")
    keyboard = _keyboard([[{"text": "View Orders", "url": url}]]) if url else None
    return send_message("customer", chat_id, "\n".join(lines), keyboard)


def _send_cart(chat_id, telegram_user_id):
    user = _linked_customer(telegram_user_id)
    if user is None:
        return send_message("customer", chat_id, "Link your NexHaat account first with /link.")
    rows = customer_cart_rows(user.id)
    if not rows:
        return send_message("customer", chat_id, "Your cart is empty.")
    lines = ["Your cart:"]
    buttons = []
    subtotal = 0
    for row in rows[:10]:
        product = row["product"]
        variant = row["variant"]
        label = f" ({variant.option_name}: {variant.option_value})" if variant else ""
        lines.append(
            f"{product.name[:80]}{label} x{row['quantity']} | BDT {row['price']:.2f} each | BDT {row['subtotal']:.2f}"
        )
        subtotal += row["subtotal"]
        key = row["item"].item_key
        buttons.append([
            {"text": "+1", "callback_data": f"cart|add|{key}"},
            {"text": "-1", "callback_data": f"cart|remove|{key}"},
            {"text": "Delete", "callback_data": f"cart|delete|{key}"},
        ])
    lines.append(f"Items subtotal: BDT {subtotal:.2f}\nDelivery is calculated at checkout.")
    links = []
    cart_url = _site_url("cart")
    checkout_url = _site_url("checkout")
    if cart_url:
        links.append({"text": "Open Cart", "url": cart_url})
    if checkout_url:
        links.append({"text": "Checkout", "url": checkout_url})
    if links:
        buttons.append(links)
    return send_message("customer", chat_id, "\n".join(lines), _keyboard(buttons))


def _handle_callback(payload, telegram_user_id, chat_id):
    callback = payload.get("callback_query") or {}
    callback_id = callback.get("id")
    data = callback.get("data", "")
    user = _linked_customer(telegram_user_id)
    if data.startswith("cmd|"):
        action = data.split("|", 1)[1]
        answer_callback("customer", callback_id)
        if action == "shop":
            url = _site_url("menu")
            return send_message(
                "customer", chat_id, "Open the NexHaat marketplace.",
                _keyboard([[{"text": "Shop Now", "url": url}]]) if url else None,
            )
        if action == "search":
            return send_message("customer", chat_id, "Search the catalog with /search <query>.")
        if action == "categories":
            return _send_categories(chat_id)
        if action == "support":
            return _send_support(chat_id)
        if action == "cart":
            return _send_cart(chat_id, telegram_user_id)
        if action == "orders":
            return _send_orders(chat_id, telegram_user_id)
        if action == "account":
            return _send_account(chat_id, telegram_user_id)
        return send_message("customer", chat_id, "That action is unavailable.")
    if user is None:
        answer_callback("customer", callback_id, "Link your account first with /link.")
        return send_message("customer", chat_id, "Link your NexHaat account first with /link.")
    try:
        if data.startswith("product-add|"):
            parts = data.split("|")
            if len(parts) not in {2, 3}:
                raise CartError("Unavailable action.")
            product_id = int(parts[1])
            variant_id = int(parts[2]) if len(parts) == 3 else None
            add_customer_cart_item(user.id, product_id, quantity=1, variant_id=variant_id)
            answer_callback("customer", callback_id, "Added to your cart.")
        elif data.startswith("cart|"):
            _prefix, action, key = data.split("|", 2)
            row = next((row for row in customer_cart_rows(user.id) if row["item"].item_key == key), None)
            if row is None:
                raise CartError("Cart item not found.")
            if action == "delete":
                update_customer_cart_item(user.id, key, 0)
            elif action in {"add", "remove"}:
                delta = 1 if action == "add" else -1
                update_customer_cart_item(user.id, key, max(0, row["quantity"] + delta))
            else:
                raise CartError("Invalid cart action.")
            answer_callback("customer", callback_id, "Cart updated.")
        else:
            raise CartError("Unavailable action.")
    except (CartError, TypeError, ValueError):
        answer_callback("customer", callback_id, "That item is no longer available.")
    return _send_cart(chat_id, telegram_user_id)


def _send_support(chat_id):
    support_url = current_app.config.get("TELEGRAM_SUPPORT_URL", "").strip()
    parsed = urlsplit(support_url)
    if (
        parsed.scheme not in {"https", "http"} or not parsed.hostname
        or parsed.username or parsed.password
        or (current_app.config.get("ENVIRONMENT") == "production" and parsed.scheme != "https")
    ):
        support_url = _site_url("")
    markup = _keyboard([[{"text": "NexHaat Support", "url": support_url}]]) if support_url else None
    return send_message("customer", chat_id, "Open the configured NexHaat support page.", markup)


def handle_customer_update(payload, telegram_user_id, chat_id):
    from flask import g

    g.telegram_user_id = telegram_user_id
    if isinstance(payload.get("callback_query"), dict):
        if chat_id != telegram_user_id:
            answer_callback(
                "customer", payload["callback_query"].get("id"),
                "Use cart controls in a private chat.",
            )
            return send_message("customer", chat_id, "Account and cart controls are available only in a private chat.")
        return _handle_callback(payload, telegram_user_id, chat_id)
    message = payload.get("message") or payload.get("edited_message") or {}
    text = message.get("text", "")
    if not isinstance(text, str):
        return send_message("customer", chat_id, "Please send a text search or use /help.")
    text = text.strip()[:200]
    if not text:
        return send_message("customer", chat_id, "Use /search followed by a product name.")

    first, _, remainder = text.partition(" ")
    command = first.split("@", 1)[0].lower()
    query = remainder.strip()[:100]
    if command in {"/link", "/cart", "/orders", "/account"} and chat_id != telegram_user_id:
        return send_message(
            "customer", chat_id,
            "Account, order, and cart commands are available only in a private chat.",
        )
    if command in {"/start", "/help"}:
        return _send_start(chat_id, telegram_user_id) if command == "/start" else send_message(
            "customer", chat_id,
            "Commands: /shop, /products, /categories, /search <query>, /help",
        )
    if command == "/shop":
        url = _site_url("menu")
        return send_message(
            "customer", chat_id,
            "Open the NexHaat marketplace." if url else "Marketplace link is not configured.",
            _keyboard([[{"text": "Shop Now", "url": url}]]) if url else None,
        )
    if command in {"/categories", "/category"}:
        return _send_categories(chat_id)
    if command == "/link":
        code, status = _create_link_code(telegram_user_id)
        if status == "linked":
            return send_message("customer", chat_id, "This Telegram account is already linked. Unlink it from your NexHaat account page first.")
        if status == "cooldown":
            return send_message("customer", chat_id, "A link code was sent recently. Enter that code on your NexHaat Account page.")
        account_url = _site_url("auth/account")
        text = f"Your one-time link code is {code}. It expires in 10 minutes. Sign in to NexHaat and enter it on your Account page. Never share this code."
        markup = _keyboard([[{"text": "Open Account", "url": account_url}]]) if account_url else None
        return send_message("customer", chat_id, text, markup)
    if command == "/cart":
        return _send_cart(chat_id, telegram_user_id)
    if command == "/orders":
        return _send_orders(chat_id, telegram_user_id)
    if command == "/account":
        return _send_account(chat_id, telegram_user_id)
    if command == "/support":
        return _send_support(chat_id)
    if command in {"/products", "/search"}:
        query = query if command == "/search" else ""
        return _send_products(chat_id, query)
    if text.startswith("/"):
        return send_message("customer", chat_id, "Unknown command. Use /help to see available commands.")
    return _send_products(chat_id, text[:100])


@telegram_customer_bp.post("/webhook")
@csrf.exempt
def webhook():
    if not credentials_ready("customer"):
        return jsonify(ok=False), 503
    if not valid_webhook_secret(
        "customer", request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    ):
        return jsonify(ok=False), 403
    return receive_update("customer", handle_customer_update)
