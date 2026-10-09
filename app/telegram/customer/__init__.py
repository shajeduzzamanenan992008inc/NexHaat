import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...extensions import csrf, db
from ...models import Order, Product, TelegramAccountLinkChallenge, TelegramIdentity, User
from ...services.audit import record_audit
from ...services.product_images import MAX_PRODUCT_IMAGE_BYTES, ProductImageError, normalize_product_image
from ...services.cart import (
    CartError, add_customer_cart_item, customer_cart_rows,
    update_customer_cart_item,
)
from ...services.catalog import get_active_categories, get_catalog_products, get_product_by_slug, search_products
from ..common import (
    answer_callback, credentials_ready, download_telegram_file, receive_update, send_message,
    send_voice, synthesize_local_speech,
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
        "Welcome to NexHaat! Ask general questions or coding questions, or shop from the live catalog here.\n\nCommands: /shop, /products, /categories, /search <query>, /price-history <product>, /price-alert <target BDT> <product>, /link, /cart, /orders, /account, /support, /ai-consent, /ai-revoke, /help",
        _keyboard(rows) if rows else None,
    )


def _send_categories(chat_id):
    categories = get_active_categories()
    rows = []
    lines = ["🗂️ Active marketplace categories:"]
    for category in categories[:20]:
        lines.append(f"• {category.name[:60]}")
        url = _site_url(f"category/{category.slug}")
        if url:
            rows.append([{"text": category.name[:60], "url": url}])
    text = "\n".join(lines) if categories else "There are no active categories right now."
    return send_message("customer", chat_id, text, _keyboard(rows) if rows else None)


def _send_products(chat_id, query="", *, answer=None):
    from ...ai.marketplace_tools import handle_marketplace_ai_query

    telegram_user_id = getattr(g, "telegram_user_id", None)
    user = (
        _linked_customer(telegram_user_id)
        if telegram_user_id and chat_id == telegram_user_id else None
    )
    products_in_answer = False
    if query:
        result = handle_marketplace_ai_query(
            query, user=user, channel="telegram",
            context={
                **({"principal": f"telegram:customer:{telegram_user_id}"} if telegram_user_id else {}),
                **_conversation_ai_context(telegram_user_id),
            },
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
        answer = result.get("answer") or result.get("fallback")
        products_in_answer = "get_recommendations" in (result.get("tools_used") or [])
    else:
        products, _pagination = get_catalog_products(page=1, per_page=5, in_stock=True)
        rows = products
    if not rows:
        text = answer or "No available products matched that search."
        return send_message("customer", chat_id, text[:3500])

    return _send_product_cards(
        chat_id, rows, answer=answer, products_in_answer=products_in_answer
    )


def _resolve_price_command_product(query):
    slug_product = get_product_by_slug(query)
    if (slug_product and slug_product.is_available
            and slug_product.moderation_status == "approved"
            and getattr(slug_product.category, "is_active", True)):
        return slug_product, [slug_product]

    products, _pagination = get_catalog_products(
        page=1, per_page=5, query=query, in_stock=False,
    )
    products = [
        product for product in products
        if product.is_available and product.moderation_status == "approved"
        and getattr(product.category, "is_active", True)
    ]
    exact = [
        product for product in products
        if product.name.casefold() == query.casefold()
        or product.slug.casefold() == query.casefold()
    ]
    if len(exact) == 1 and _pagination["total"] == len(products):
        return exact[0], products
    return None, products


def _send_price_history(chat_id, query):
    if not query:
        return send_message("customer", chat_id, "Use /price-history followed by a product name.")
    product, matches = _resolve_price_command_product(query)
    if product is None:
        if matches:
            return _send_product_cards(
                chat_id, matches,
                answer="I found matching products. Use an exact product name or slug from the list.",
            )
        return send_message("customer", chat_id, "I could not find an available matching product.")

    from ...services.ai_price_alerts import observed_price_history

    history = observed_price_history(product.id)
    if not history:
        return send_message(
            "customer", chat_id,
            f"No earlier observed NexHaat price records are available for {product.name[:120]}; "
            "I will not invent a price history.",
        )
    lines = [
        f"Recorded NexHaat listing prices for {product.name[:120]} "
        "(not a complete market history):"
    ]
    lines.extend(
        f"{row['recorded_at'][:10]}: BDT {row['effective_price']}"
        for row in history[:8]
    )
    url = _site_url(f"food/{product.slug}")
    markup = _keyboard([[{"text": "View product", "url": url}]]) if url else None
    return send_message("customer", chat_id, "\n".join(lines), markup)


def _handle_price_alert(chat_id, telegram_user_id, query):
    if chat_id != telegram_user_id:
        return send_message("customer", chat_id, "Manage personal price alerts in a private chat.")
    user = _linked_customer(telegram_user_id)
    if user is None:
        return send_message("customer", chat_id, "Link your NexHaat customer account first with /link.")

    action = "set"
    product_query = query
    if query.lower().startswith("off "):
        action, product_query = "off", query[4:].strip()
    elif query.lower().startswith("cancel "):
        action, product_query = "off", query[7:].strip()
    target = None
    if action == "set":
        target_text, separator, product_query = query.partition(" ")
        product_query = product_query.strip()
        if not separator or not product_query:
            return send_message(
                "customer", chat_id,
                "Use /price-alert <target BDT price> <product name>, or /price-alert off <product name>.",
            )
        try:
            target = Decimal(target_text)
        except (InvalidOperation, ValueError):
            target = Decimal("NaN")
        if (not target.is_finite() or target < 0 or target > Decimal("99999999.99")
                or target != target.quantize(Decimal("0.01"))):
            return send_message("customer", chat_id, "Enter a valid target price with up to two decimal places.")
    if not product_query:
        return send_message("customer", chat_id, "Include the product name after the price-alert command.")

    product, matches = _resolve_price_command_product(product_query)
    if product is None:
        if matches:
            return _send_product_cards(
                chat_id, matches,
                answer="I found matching products. Retry with an exact product name or slug.",
            )
        return send_message("customer", chat_id, "I could not find an available matching product.")

    from ...services.ai_price_alerts import cancel_price_alert, save_price_alert

    if action == "off":
        cancelled = cancel_price_alert(user, product)
        message = ("Your price alert is off." if cancelled
                   else "There is no active price alert for this product.")
    else:
        alert = save_price_alert(user, product, target)
        message = (f"Your target-price alert is set for {product.name[:120]} at "
                   f"BDT {alert.target_price:.2f}. We will notify you in the NexHaat inbox "
                   "when an observed listing price reaches the target.")
    return send_message("customer", chat_id, message)


def _send_product_cards(
    chat_id, products, *, answer=None, products_in_answer=False,
    context_products=None, selected_product=None,
):
    if not products:
        return send_message("customer", chat_id, "No available products matched that search.")

    telegram_user_id = getattr(g, "telegram_user_id", None)
    if telegram_user_id:
        from ...services.telegram_shopping_context import save_shopping_context

        save_shopping_context(
            telegram_user_id,
            products if context_products is None else context_products,
            selected_product=(
                products[0].slug if context_products is None and len(products) == 1
                else selected_product
            ),
        )
    lines = ([answer.strip()[:1500], "", "Matching available products:"]
             if isinstance(answer, str) and answer.strip()
             else ["Matching available products:"])
    rows = []
    can_add_to_cart = bool(
        telegram_user_id is not None and chat_id == telegram_user_id
        and _linked_customer(telegram_user_id) is not None
    )
    for product in products[:5]:
        price = product.discount_price or product.price
        details = []
        if product.brand_name:
            details.append(f"Brand: {product.brand_name[:60]}")
        if product.category:
            details.append(f"Category: {product.category.name[:60]}")
        details.append(f"Available: {product.available_stock}")
        if product.description:
            details.append(product.description[:180].strip())
        lines.append(
            f"\n{product.name[:120]} - BDT {price}\n" + " | ".join(details)
        )
        url = _site_url(f"food/{product.slug}")
        buttons = []
        if url:
            buttons.append({"text": f"View Details", "url": url})
        buttons.append({"text": "Compare", "callback_data": f"compare|{product.id}"})
        active_variants = [
            variant for variant in product.variants
            if variant.is_active and variant.stock_quantity > 0
        ]
        if can_add_to_cart and active_variants:
            if len(active_variants) == 1:
                buttons.append({
                    "text": "Add",
                    "callback_data": f"product-add|{product.id}|{active_variants[0].id}",
                })
            else:
                rows.append(buttons)
                for variant in active_variants[:5]:
                    option = f"{variant.option_name}: {variant.option_value}"[:25]
                    rows.append([{
                        "text": f"Add {option}",
                        "callback_data": f"product-add|{product.id}|{variant.id}",
                    }])
                continue
        elif can_add_to_cart and product.stock_quantity > 0:
            buttons.append({
                "text": "Add", "callback_data": f"product-add|{product.id}",
            })
        rows.append(buttons)
    return send_message(
        "customer", chat_id, "\n".join(lines), _keyboard(rows) if rows else None
    )


def _conversation_intent(text):
    lowered = text.casefold().strip()
    if any(term in lowered for term in (
        "add a product to my cart", "add product to cart", "add to my cart",
        "add this to cart", "cart e add", "কার্টে যোগ", "কার্টে দাও",
    )):
        return "add_to_cart"
    if any(term in lowered for term in (
        "compare", "comparison", "versus", " vs ", "তুলনা", "কোনটা ভালো",
    )):
        return "compare"
    if any(term in lowered for term in (
        "category", "categories", "browse categories", "ক্যাটাগরি", "বিভাগগুলো",
    )):
        return "categories"
    if any(term in lowered for term in (
        "my order", "my orders", "show my orders", "where is my order",
        "order status", "track my order", "অর্ডার কোথায়", "আমার অর্ডার",
    )):
        return "orders"
    if any(term in lowered for term in (
        "my cart", "what is in my cart", "what's in my cart", "show my cart",
        "view my cart", "cart contents", "কার্টে কী", "আমার কার্ট",
    )):
        return "cart"
    if any(term in lowered for term in (
        "i need help", "need help", "help me", "contact support", "support agent",
        "human support", "সাহায্য চাই", "সাপোর্ট",
    )):
        return "support"
    if lowered in {"hi", "hello", "hey", "hiya", "হ্যালো", "হাই", "আসসালামু আলাইকুম"}:
        return "greeting"
    if any(term in lowered for term in (
        "show me products", "show products", "list products", "browse products",
        "all products", "দেখাও পণ্য", "সব পণ্য",
    )):
        return "browse_products"
    if any(term in lowered for term in ("suggest", "recommend", "recommendation", "সাজেস্ট", "পরামর্শ")):
        return "recommend"
    if re.search(r"\b(?:search|find|look for)\b", lowered):
        return "search"
    return "question"


def _conversation_ai_context(telegram_user_id):
    if not telegram_user_id:
        return {}
    from ...services.telegram_shopping_context import get_shopping_context

    state = get_shopping_context(telegram_user_id)
    return {
        "recent_products": state["products"],
        "selected_product": state["selected_product"],
    }


def _context_products(telegram_user_id):
    from ...services.telegram_shopping_context import get_shopping_context

    state = get_shopping_context(telegram_user_id)
    products = []
    for slug in state["products"]:
        product = get_product_by_slug(slug)
        if (product and product.is_available and product.moderation_status == "approved"
                and product.available_stock > 0 and getattr(product.category, "is_active", True)):
            products.append(product)
    selected = next(
        (product for product in products if product.slug == state["selected_product"]), None
    )
    return state, products, selected


def _ordinal_positions(text, count):
    patterns = (
        (r"\b(?:first|1st|1)\b|প্রথম|১ম", 0),
        (r"\b(?:second|2nd|2)\b|দ্বিতীয়|দ্বিতীয়|২য়|২য়", 1),
        (r"\b(?:third|3rd|3)\b|তৃতীয়|তৃতীয়|৩য়|৩য়", 2),
        (r"\b(?:fourth|4th|4)\b|চতুর্থ|৪র্থ", 3),
        (r"\b(?:fifth|5th|5)\b|পঞ্চম|৫ম", 4),
        (r"\b(?:last|final)\b|শেষেরটা|শেষটা", count - 1),
    )
    positions = []
    for pattern, index in patterns:
        if re.search(pattern, text, re.IGNORECASE) and 0 <= index < count and index not in positions:
            positions.append(index)
    return positions


def _is_product_reference(text):
    return bool(re.search(
        r"\b(?:this|that|it|its|same as before|another one|cheaper|cheapest|"
        r"second|third|first|last|compare|cart)\b|"
        r"\b(?:eta|eita|ota|oitā|ager|arekta|sosta|kom dam|cart e|cart-e)\b|"
        r"(?:এটা|এইটা|ওটা|ওইটা|আগেরটা|আরেকটা|সস্তা|কম দামের|কার্টে|দ্বিতীয়|দ্বিতীয়|প্রথম|তৃতীয়|তৃতীয়|তুলনা)",
        text, re.IGNORECASE,
    ))


def _send_contextual_product_facts(chat_id, product, question):
    from ...ai.marketplace_tools import get_product_tool

    details = get_product_tool(product.slug)
    if "error" in details:
        return send_message("customer", chat_id, "That product is no longer available.")
    bengali = any("\u0980" <= char <= "\u09ff" for char in question)
    currency = "৳" if bengali else "BDT "
    lines = [f"🛍️ {details['name']}", f"Price: {currency}{details['price']}"]
    lines.append(
        (f"স্টক: {details['stock']}টি" if bengali else f"Available stock: {details['stock']}")
    )
    if details.get("brand"):
        lines.append(f"Brand: {details['brand']}")
    if details.get("description"):
        lines.append(f"Listing details: {details['description']}")
    if re.search(r"battery|ব্যাটারি|বেটারি", question, re.IGNORECASE) and not re.search(
        r"battery|ব্যাটারি|বেটারি", details.get("description", ""), re.IGNORECASE,
    ):
        lines.append(
            "এই তথ্যটি পণ্যের তালিকায় নেই।" if bengali
            else "The listing does not provide battery information."
        )
    state, _products, _selected = _context_products(getattr(g, "telegram_user_id", None))
    return _send_product_cards(
        chat_id, [product], answer="\n".join(lines),
        context_products=state["products"], selected_product=product.slug,
    )


def _handle_contextual_product_message(chat_id, telegram_user_id, text):
    state, products, selected = _context_products(telegram_user_id)
    if not products or not _is_product_reference(text):
        return None

    positions = _ordinal_positions(text, len(state["products"]))
    chosen = []
    for index in positions:
        if index >= len(state["products"]):
            continue
        product = get_product_by_slug(state["products"][index])
        if (product and product.is_available and product.moderation_status == "approved"
                and product.available_stock > 0 and getattr(product.category, "is_active", True)):
            chosen.append(product)
    lowered = text.casefold()
    compare_requested = _conversation_intent(text) == "compare"
    add_requested = (
        "cart" in lowered
        and any(word in lowered for word in ("add", "put", "into", "to my", "dao", "rakho", "দাও", "রাখো"))
    ) or any(phrase in lowered for phrase in ("কার্টে দাও", "কার্টে যোগ", "কার্টে রাখ"))
    cheaper_requested = any(
        word in lowered for word in ("cheaper", "cheapest", "lower price", "কম দামের", "সস্তা", "কম দাম")
    )
    another_requested = any(
        word in lowered for word in ("another one", "show another", "arekta", "আরেকটা")
    )
    repeat_requested = any(
        phrase in lowered for phrase in ("same as before", "আগেরটার মতো", "আগের মতো")
    )
    reference_requested = bool(
        positions or re.search(r"\b(?:this|that|it|its|eta|eita|ota)\b|এটা|এইটা|ওটা|ওইটা", text, re.I)
    )

    if compare_requested:
        candidates = chosen
        if not candidates and len(products) == 2:
            candidates = products
        if len(candidates) < 2:
            return send_message(
                "customer", chat_id,
                "Which products should I compare? Choose two by position, such as “compare first and third”.",
            )
        return _send_product_comparison(
            chat_id, text, product_slugs=[product.slug for product in candidates[:3]]
        )

    if repeat_requested:
        return _send_product_cards(chat_id, products, answer="Here are the products from your recent search.")

    if cheaper_requested or another_requested:
        source = chosen[0] if len(chosen) == 1 else selected
        has_comparison_target = bool(re.search(
            r"\b(?:than|from)\b|theke|থেকে|এর চেয়ে|এর চেয়ে", text, re.IGNORECASE,
        ))
        if cheaper_requested and source is None and not chosen and not has_comparison_target:
            source = min(products, key=lambda item: item.discount_price or item.price)
            return _send_product_cards(
                chat_id, [source],
                answer="This is the lowest-priced currently available option from your recent results.",
            )
        if source is None and len(products) == 1:
            source = products[0]
        if source is None:
            return send_message(
                "customer", chat_id,
                "Which product should I use as the reference? Choose one by position, for example “cheaper than the second one”.",
            )
        if cheaper_requested:
            reference_price = source.discount_price or source.price
            alternatives, _page = get_catalog_products(
                page=1, per_page=24, category_id=source.category_id,
                max_price=reference_price, in_stock=True, sort="price_asc",
            )
            alternatives = [
                item for item in alternatives
                if item.id != source.id
                and (item.discount_price or item.price) < reference_price
            ]
        else:
            alternatives, _page = get_catalog_products(
                page=1, per_page=24, category_id=source.category_id,
                in_stock=True, sort="featured",
            )
            previous = set(state["products"])
            alternatives = [item for item in alternatives if item.slug not in previous]
        return _send_product_cards(
            chat_id, alternatives[:5],
            answer=(
                f"Currently available options in {source.category.name} below "
                f"BDT {reference_price:.2f}:" if cheaper_requested and alternatives
                else f"More currently available options in {source.category.name}:"
                if alternatives else
                "I couldn't find another currently available product in that category."
            ),
        )

    if add_requested or positions or reference_requested:
        product = chosen[0] if len(chosen) == 1 else selected
        if product is None and len(products) == 1 and reference_requested:
            product = products[0]
        if product is None:
            return send_message(
                "customer", chat_id,
                "Which product do you mean? Choose it by position, for example “the second one”.",
            )
        from ...services.telegram_shopping_context import save_shopping_context

        save_shopping_context(
            telegram_user_id, state["products"], selected_product=product.slug,
        )
        if add_requested:
            if chat_id != telegram_user_id:
                return send_message("customer", chat_id, "Cart actions are available in a private chat.")
            if _linked_customer(telegram_user_id) is None:
                return send_message("customer", chat_id, "Link your NexHaat customer account first with /link.")
            return _send_product_cards(
                chat_id, [product],
                answer="Choose the Add button to add this product to your linked NexHaat cart.",
                context_products=state["products"], selected_product=product.slug,
            )
        return _send_contextual_product_facts(chat_id, product, text)
    return None


def _search_query_from_message(text):
    query = re.sub(
        r"(?i)^\s*(?:please\s+)?(?:search\s+(?:for\s+)?|find\s+|look\s+for\s+|"
        r"show\s+me\s+|show\s+|find\s+me\s+)",
        "",
        text,
    )
    query = re.sub(r"(?i)^\s*(?:a|an|the)\s+", "", query)
    return query.strip(" \t\r\n?!.,")[:100]


def _send_product_comparison(chat_id, text, *, product_slugs=None):
    if product_slugs is None:
        parts = re.split(r"(?i)\s+(?:vs\.?|versus|and)\s+|[,;]", re.sub(
            r"(?i)^\s*(?:please\s+)?compare\s+", "", text,
        ))
        names = [part.strip(" ?.!") for part in parts if part.strip(" ?.!")]
        if len(names) != 2:
            return send_message(
                "customer", chat_id,
                "Which two product names should I compare? Send them like: compare Phone A vs Phone B.",
            )

        products = []
        for name in names:
            product, matches = _resolve_price_command_product(name)
            if product is None:
                if matches:
                    return _send_product_cards(
                        chat_id, matches,
                        answer=f"I found several matches for “{name[:80]}”. Choose the exact product, then send both exact names to compare.",
                    )
                return send_message(
                    "customer", chat_id,
                    f"I couldn't identify “{name[:80]}” as an exact available product. Please send the exact product names.",
                )
            products.append(product)
        product_slugs = [product.slug for product in products]

    from sqlalchemy import func
    from ...models import Review
    from ...ai.marketplace_tools import build_customer_tool_registry
    from ...ai.core.permissions import AI_SCOPE_CUSTOMER

    comparison = build_customer_tool_registry().call(
        "compare_products",
        scope=AI_SCOPE_CUSTOMER,
        arguments={"slugs": product_slugs},
    )
    if not comparison.get("ok"):
        return send_message(
            "customer", chat_id,
            "I couldn't verify those products for a current comparison. Please search again and retry.",
        )
    products = [
        get_product_by_slug(item["slug"])
        for item in comparison["result"]
        if isinstance(item, dict) and item.get("slug")
    ]
    products = [product for product in products if product is not None]
    if len(products) < 2:
        return send_message(
            "customer", chat_id,
            "At least two of those products are no longer available for comparison. Please search again.",
        )
    telegram_user_id = getattr(g, "telegram_user_id", None)
    if telegram_user_id:
        from ...services.telegram_shopping_context import save_shopping_context

        save_shopping_context(telegram_user_id, products)
    ratings = {
        product_id: (float(average), int(count))
        for product_id, average, count in db.session.execute(
            select(Review.product_id, func.avg(Review.rating), func.count(Review.id))
            .where(Review.product_id.in_([product.id for product in products]),
                   Review.status == "approved")
            .group_by(Review.product_id)
        ).all()
    }
    lines = ["📊 Verified product comparison:"]
    buttons = []
    for product in products:
        price = product.discount_price or product.price
        line = f"• {product.name[:100]} — BDT {price:.2f}"
        rating = ratings.get(product.id)
        if rating:
            line += f" | ⭐ {rating[0]:.1f}/5 ({rating[1]} reviews)"
        if product.brand_name:
            line += f" | Brand: {product.brand_name[:60]}"
        line += f" | In stock: {product.available_stock}"
        lines.append(line)
        url = _site_url(f"food/{product.slug}")
        if url:
            buttons.append([{"text": f"View {product.name[:35]}", "url": url}])
    return send_message(
        "customer", chat_id, "\n".join(lines), _keyboard(buttons) if buttons else None
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
    now = datetime.now(timezone.utc)
    challenge = db.session.scalar(
        select(TelegramAccountLinkChallenge)
        .where(TelegramAccountLinkChallenge.telegram_user_id == telegram_user_id)
        .with_for_update()
    )
    sent_at = challenge.sent_at if challenge else None
    expires_at = challenge.expires_at if challenge else None
    if sent_at and sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
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
        lines.append(
            f"{order.order_number} | {order.status} | Delivery: {order.delivery_status} "
            f"| BDT {order.total:.2f}\n{names}"
        )
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
        if action in {"cart", "orders", "account"} and chat_id != telegram_user_id:
            return send_message(
                "customer", chat_id,
                "Account, order, and cart actions are available only in a private chat.",
            )
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
    if data.startswith("compare|"):
        try:
            product_id = int(data.split("|", 1)[1])
            product = db.session.get(Product, product_id)
        except (TypeError, ValueError):
            product = None
        if (product is None or not product.is_available
                or product.moderation_status != "approved"
                or product.available_stock < 1):
            answer_callback("customer", callback_id, "That product is no longer available.")
            return send_message("customer", chat_id, "Please search again for an available product.")
        state, products, _selected = _context_products(telegram_user_id)
        candidate = next((item for item in products if item.slug == product.slug), None)
        if candidate is None:
            answer_callback("customer", callback_id, "Search for products before comparing.")
            return send_message(
                "customer", chat_id,
                "Search for products first, then use Compare on the products you want.",
            )
        if state["selected_product"] and state["selected_product"] != candidate.slug:
            answer_callback("customer", callback_id, "Comparing products.")
            return _send_product_comparison(
                chat_id, "",
                product_slugs=[state["selected_product"], candidate.slug],
            )
        from ...services.telegram_shopping_context import save_shopping_context

        save_shopping_context(
            telegram_user_id, products, selected_product=candidate.slug,
        )
        answer_callback("customer", callback_id, "Choose a second product.")
        return send_message(
            "customer", chat_id,
            f"Compare {candidate.name} with another product by tapping its Compare button.",
        )
    if user is None:
        answer_callback("customer", callback_id, "Link your account first with /link.")
        return send_message("customer", chat_id, "Link your NexHaat account first with /link.")
    if chat_id != telegram_user_id and data.startswith(
        ("product-add|", "cart|", "cart-confirm|")
    ):
        answer_callback("customer", callback_id, "Use a private chat for cart actions.")
        return send_message(
            "customer", chat_id, "Cart changes are available only in a private chat."
        )
    try:
        if data.startswith("product-add|"):
            parts = data.split("|")
            if len(parts) not in {2, 3}:
                raise CartError("Unavailable action.")
            product_id = int(parts[1])
            variant_id = int(parts[2]) if len(parts) == 3 else None
            add_customer_cart_item(user.id, product_id, quantity=1, variant_id=variant_id)
            answer_callback("customer", callback_id, "Added to your cart.")
        elif data.startswith("cart-confirm|"):
            parts = data.split("|")
            if len(parts) == 5 and parts[1] == "add":
                _, _, product_id, quantity, variant_id = parts
                add_customer_cart_item(
                    user.id, int(product_id), quantity=int(quantity),
                    variant_id=int(variant_id) if variant_id else None,
                )
            elif len(parts) == 4 and parts[1] in {"set_quantity", "remove"}:
                _, action, item_key, quantity = parts
                row = next(
                    (row for row in customer_cart_rows(user.id)
                     if row["item"].item_key == item_key),
                    None,
                )
                if row is None:
                    raise CartError("Cart item not found.")
                update_customer_cart_item(
                    user.id, item_key,
                    0 if action == "remove" else int(quantity),
                )
            else:
                raise CartError("Unavailable action.")
            answer_callback("customer", callback_id, "Cart updated.")
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


def _handle_customer_photo(chat_id, telegram_user_id, photos, caption=""):
    if (chat_id != telegram_user_id and isinstance(caption, str)
            and any(term in caption.lower() for term in (
                "my cart", "cart", "basket", "my order", "order status", "my account", "কার্ট", "অর্ডার",
            ))):
        return send_message(
            "customer", chat_id,
            "Personal cart, account, and order questions are available in a private chat only.",
        )
    if not isinstance(photos, list) or not photos:
        return send_message("customer", chat_id, "Please send a product photo in JPEG, PNG, or WebP format.")
    photo = max(
        (item for item in photos if isinstance(item, dict)),
        key=lambda item: item.get("file_size", 0) if isinstance(item.get("file_size", 0), int) else 0,
        default=None,
    )
    file_size = photo.get("file_size") if photo else None
    if (not photo or not isinstance(photo.get("file_id"), str)
            or isinstance(file_size, bool) or not isinstance(file_size, int)
            or file_size <= 0 or file_size > MAX_PRODUCT_IMAGE_BYTES):
        return send_message("customer", chat_id, "That photo is empty or too large. Please send one under 5 MB.")
    raw = download_telegram_file("customer", photo["file_id"], max_bytes=MAX_PRODUCT_IMAGE_BYTES)
    if raw is None:
        return send_message("customer", chat_id, "I could not download that photo. Please try again.")
    try:
        normalized = normalize_product_image(raw)
    except ProductImageError as error:
        return send_message("customer", chat_id, str(error))

    try:
        from ...ai.core.provider import AIProviderError, AIService
        description = AIService(current_app.config).describe_image(
            normalized, content_type="image/jpeg"
        )
    except (AIProviderError, ValueError):
        return send_message("customer", chat_id, "Visual search is unavailable. Please search by text instead.")

    query = f"Find products matching this image: {description[:1500]}"
    if isinstance(caption, str) and caption.strip():
        query = f"{query}\nCustomer request: {caption.strip()[:500]}"
    user = _linked_customer(telegram_user_id) if chat_id == telegram_user_id else None
    from ...ai.marketplace_tools import handle_marketplace_ai_query
    result = handle_marketplace_ai_query(
        query, user=user, channel="telegram-image",
        context={"input_mode": "image", "principal": f"telegram:customer:{telegram_user_id}"}
        if user else {"input_mode": "image"},
    )
    return _send_products_from_result(chat_id, result)


def _send_products_from_result(
    chat_id, result, *, context_products=None, selected_product=None,
):
    products = result.get("products") or []
    rows = []
    for item in products[:5]:
        slug = item.get("slug")
        if not slug:
            continue
        product = get_product_by_slug(slug)
        if (product and product.is_available and product.moderation_status == "approved"
                and product.available_stock > 0):
            rows.append(product)
    answer = result.get("answer") or result.get("fallback")
    if not rows:
        return send_message(
            "customer", chat_id,
            (answer or "I could not find matching catalog products.")[:3500],
        )
    return _send_product_cards(
        chat_id, rows, answer=answer,
        context_products=context_products,
        selected_product=selected_product,
    )


def _respond_to_conversation(chat_id, telegram_user_id, text):
    from ...ai.marketplace_tools import handle_marketplace_ai_query

    private_chat = chat_id == telegram_user_id
    user = _linked_customer(telegram_user_id) if private_chat else None
    context = _conversation_ai_context(telegram_user_id) if private_chat else {}
    if user is not None:
        context["principal"] = f"telegram:customer:{telegram_user_id}"
    result = handle_marketplace_ai_query(
        text, user=user, channel="telegram", context=context,
    )
    tools_used = set(result.get("tools_used") or ())
    if private_chat and "get_customer_cart" in tools_used:
        return _send_cart(chat_id, telegram_user_id)
    if private_chat and "get_customer_orders" in tools_used:
        return _send_orders(chat_id, telegram_user_id)
    if "get_categories" in tools_used:
        return _send_categories(chat_id)
    if "get_support_info" in tools_used:
        return _send_support(chat_id)
    if "compare_products" in tools_used:
        products = result.get("products") or []
        slugs = [item.get("slug") for item in products if item.get("slug")]
        if len(slugs) >= 2:
            return _send_product_comparison(
                chat_id, "", product_slugs=slugs[:3],
            )
    if private_chat and "get_product" in tools_used:
        _state, context_products, _selected = _context_products(telegram_user_id)
        products = result.get("products") or []
        selected = products[0].get("slug") if products else None
        return _send_products_from_result(
            chat_id, result, context_products=context_products or None,
            selected_product=selected,
        )

    proposal = next(
        (
            item.get("result")
            for item in result.get("tool_results", [])
            if isinstance(item, dict)
            and item.get("ok") is True
            and isinstance(item.get("result"), dict)
            and item["result"].get("requires_confirmation")
        ),
        None,
    )
    if proposal and private_chat:
        action = proposal.get("action")
        if action == "add":
            callback_data = (
                f"cart-confirm|add|{proposal.get('product_id')}|"
                f"{proposal.get('quantity')}|{proposal.get('variant_id') or ''}"
            )
        else:
            callback_data = (
                f"cart-confirm|{action}|{proposal.get('item_key')}|"
                f"{proposal.get('quantity')}"
            )
        if len(callback_data.encode("utf-8")) <= 64:
            price = proposal.get("price")
            answer = result.get("answer") or "Confirm this cart change?"
            if action == "add" and price is not None:
                answer = (
                    f"{answer}\n{proposal.get('product')}: BDT {price} "
                    f"× {proposal.get('quantity')}."
                )
            return send_message(
                "customer", chat_id, answer[:3000],
                _keyboard([[{
                    "text": "Confirm cart change",
                    "callback_data": callback_data,
                }]]),
            )

    needs_variant = next(
        (
            item.get("result")
            for item in result.get("tool_results", [])
            if isinstance(item, dict)
            and item.get("ok") is True
            and isinstance(item.get("result"), dict)
            and item["result"].get("needs_variant")
        ),
        None,
    )
    if needs_variant and private_chat:
        product = needs_variant.get("product") or {}
        variants = product.get("variants") or []
        rows = [
            [{
                "text": f"Add {item.get('label', 'option')}"[:50],
                "callback_data": f"product-add|{product.get('id')}|{item.get('id')}",
            }]
            for item in variants
            if item.get("available") and isinstance(item.get("id"), int)
        ][:8]
        return send_message(
            "customer", chat_id,
            "Choose an available product option to add it to your cart."
            if rows else "This product has no available options right now.",
            _keyboard(rows) if rows else None,
        )
    return _send_products_from_result(chat_id, result)


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
    if not isinstance(text, str) or not text.strip():
        photos = message.get("photo")
        if photos is not None:
            return _handle_customer_photo(
                chat_id, telegram_user_id, photos, message.get("caption", "")
            )
        voice = message.get("voice")
        if not isinstance(voice, dict):
            return send_message("customer", chat_id, "Please send a text question or a voice note.")
        file_id = voice.get("file_id")
        file_size = voice.get("file_size", 0)
        if (isinstance(file_size, bool) or not isinstance(file_size, int)
                or file_size <= 0 or file_size > 8 * 1024 * 1024):
            return send_message("customer", chat_id, "That voice note is empty or too large. Please send one under 8 MB.")
        audio = download_telegram_file("customer", file_id)
        if not audio or not audio.startswith(b"OggS"):
            return send_message("customer", chat_id, "I could not read that voice note. Please try again or type your question.")
        try:
            from ...ai.core.provider import AIProviderError, AIService
            transcript = AIService(current_app.config).transcribe(
                audio, filename="telegram-voice.ogg", content_type="audio/ogg"
            )
        except (AIProviderError, ValueError):
            return send_message("customer", chat_id, "Local voice transcription is unavailable. Please type your question instead.")
        if chat_id != telegram_user_id and any(term in transcript.lower() for term in (
            "my cart", "cart", "basket", "my order", "order status", "my account", "কার্ট", "অর্ডার",
        )):
            return send_message("customer", chat_id, "Personal cart, account, and order questions are available in a private chat only.")
        from ...ai.marketplace_tools import handle_marketplace_ai_query
        user = _linked_customer(telegram_user_id) if chat_id == telegram_user_id else None
        result = handle_marketplace_ai_query(
            transcript, user=user, channel="telegram-voice",
            context={"principal": f"telegram:customer:{telegram_user_id}"} if user else None,
        )
        answer = result.get("answer") or result.get("fallback") or "I could not answer that voice question."
        delivered = send_message("customer", chat_id, f"Heard: {transcript[:500]}\n\n{answer[:3000]}")
        speech = synthesize_local_speech(answer[:1200])
        if speech:
            delivered = send_voice("customer", chat_id, *speech) and delivered
        return delivered
    text = text.strip()[:2000]
    if not text:
        return send_message("customer", chat_id, "Use /search followed by a product name.")

    first, _, remainder = text.partition(" ")
    command = first.split("@", 1)[0].lower()
    query = remainder.strip()[:100]
    if command in {"/link", "/cart", "/orders", "/account", "/ai-revoke"} and chat_id != telegram_user_id:
        return send_message(
            "customer", chat_id,
            "Account, order, and cart commands are available only in a private chat.",
        )
    if command == "/ai-consent":
        if chat_id != telegram_user_id:
            return send_message("customer", chat_id, "Manage external AI consent in a private chat only.")
        if query.lower() not in {"yes", "on", "enable"}:
            return send_message(
                "customer", chat_id,
                "External specialist AI can receive only complex general questions, never your cart/order records. "
                "Provider usage may cost money under the site's configured monthly cap. "
                "To opt in, send /ai-consent yes. Revoke any time with /ai-revoke.",
            )
        from ...ai.core.consent import set_external_consent
        set_external_consent(True, principal=f"telegram:customer:{telegram_user_id}")
        return send_message("customer", chat_id, "External specialist help is enabled for complex general questions. Use /ai-revoke to turn it off.")
    if command == "/ai-revoke":
        from ...ai.core.consent import set_external_consent
        set_external_consent(False, principal=f"telegram:customer:{telegram_user_id}")
        return send_message("customer", chat_id, "External specialist AI consent is off. The local Core will still answer when it is available.")
    if command in {"/start", "/help"}:
        return _send_start(chat_id, telegram_user_id) if command == "/start" else send_message(
            "customer", chat_id,
            "Send a general or coding question here, or use commands: /shop, /products, /categories, /search <query>, /price-history <product>, /price-alert <target BDT> <product>, /cart, /orders, /help, /ai-consent, /ai-revoke",
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
    if command == "/price-history":
        return _send_price_history(chat_id, query)
    if command == "/price-alert":
        return _handle_price_alert(chat_id, telegram_user_id, query)
    if command in {"/products", "/search"}:
        query = query if command == "/search" else ""
        return _send_products(chat_id, query)
    if text.startswith("/"):
        return send_message("customer", chat_id, "Unknown command. Use /help to see available commands.")
    return _respond_to_conversation(chat_id, telegram_user_id, text)


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
