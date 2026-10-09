from unittest.mock import patch

from app.extensions import db
from app.models import (
    AIProductPriceAlert, AIProductPriceHistory, AuditEvent, Category,
    CustomerCartItem, CustomerProfile, Notification, Order, Product, Review,
    ProductVariant, ProcessedTelegramUpdate, TelegramAccountLinkChallenge,
    SellerProfile, TelegramIdentity, TelegramRateLimit, TelegramSecurityAlert,
    TelegramSecurityAlertRecipient, TelegramShoppingContext, User,
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
    bind_security_admin(app)


def bind_security_admin(app, telegram_user_id=9001, role="admin"):
    email = f"telegram-{telegram_user_id}-admin@example.test"
    user = db.session.query(User).filter_by(email=email).one_or_none()
    if user is None:
        user = User(email=email, role=role)
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()
    app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = (
        f"{telegram_user_id}:{user.id}"
    )
    return user.id


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


def test_customer_telegram_ai_uses_shared_catalog_and_validates_variant_callback(client, app, caplog):
    configure_bots(app)
    telegram_id = 7711
    with app.app_context():
        customer = User(email="telegram-ai@example.test", role="customer")
        customer.set_password("password123")
        category = Category(name="Electronics", slug="electronics", is_active=True)
        db.session.add_all([customer, category])
        db.session.flush()
        product = Product(category_id=category.id, name="Wireless Headphone",
                          slug="wireless-headphone", description="Wireless headset for music.",
                          price=1800, stock_quantity=0, is_available=True,
                          moderation_status="approved")
        db.session.add(product)
        db.session.flush()
        variants = [
            ProductVariant(product_id=product.id, sku="HEADPHONE-BLACK", option_name="Color",
                           option_value="Black", price=1800, stock_quantity=3, is_active=True),
            ProductVariant(product_id=product.id, sku="HEADPHONE-WHITE", option_name="Color",
                           option_value="White", price=1850, stock_quantity=2, is_active=True),
        ]
        db.session.add_all(variants)
        db.session.add(TelegramIdentity(user_id=customer.id, telegram_user_id=telegram_id))
        db.session.commit()
        product_id, variant_id = product.id, variants[0].id

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        searched = client.post("/telegram/customer/webhook",
                               json=telegram_payload(1011, telegram_id, "/search wireless headphone"),
                               headers=headers)
    assert searched.status_code == 200, caplog.text
    markup = send.call_args.kwargs.get("reply_markup") or send.call_args.args[3]
    callback_values = [button["callback_data"] for row in markup["inline_keyboard"]
                       for button in row if "callback_data" in button]
    assert f"product-add|{product_id}|{variant_id}" in callback_values
    assert any(value.startswith(f"product-add|{product_id}|") for value in callback_values)

    callback = {
        "update_id": 1012,
        "callback_query": {
            "id": "callback-1012", "from": {"id": telegram_id},
            "message": {"message_id": 1012,
                        "chat": {"id": telegram_id, "type": "private"}},
            "data": f"product-add|{product_id}|{variant_id}",
        },
    }
    with patch("app.telegram.customer.answer_callback", return_value=True), \
            patch("app.telegram.customer.send_message", return_value=True):
        added = client.post("/telegram/customer/webhook", json=callback, headers=headers)
    assert added.status_code == 200
    with app.app_context():
        cart_item = db.session.query(CustomerCartItem).one()
        assert cart_item.variant_id == variant_id
        assert cart_item.product_id == product_id
        assert cart_item.quantity == 1


def test_customer_telegram_ai_sends_unicode_emoji_in_answer(client, app):
    configure_bots(app)
    answer = "A quick tip for you 🌱✨"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}

    with patch(
        "app.ai.marketplace_tools.handle_marketplace_ai_query",
        return_value={"answer": answer, "products": []},
    ), patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1013, 7713, "Tell me a quick tip"),
            headers=headers,
        )

    assert response.status_code == 200
    assert send.call_args.args[2] == answer


def test_customer_natural_language_routes_to_visible_catalog_and_support_replies(client, app):
    configure_bots(app)
    with app.app_context():
        category = Category(name="Phones", slug="phones", is_active=True)
        db.session.add(category)
        db.session.flush()
        db.session.add(Product(
            category_id=category.id, name="Nova Phone", slug="nova-phone",
            description="A currently available phone.", price=4500, stock_quantity=4,
            is_available=True, moderation_status="approved",
        ))
        db.session.commit()

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    prompts = [
        (1201, "Hello"),
        (1202, "Show me products"),
        (1203, "Search for a phone"),
        (1204, "Show me categories"),
        (1205, "I need help"),
    ]
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        responses = [
            client.post(
                "/telegram/customer/webhook",
                json=telegram_payload(update_id, 7811, prompt),
                headers=headers,
            )
            for update_id, prompt in prompts
        ]

    assert all(response.status_code == 200 for response in responses)
    messages = [call.args[2] for call in send.call_args_list]
    assert "Hello! 👋" in messages[0]
    assert "Nova Phone" in messages[1] and "BDT 4500.00" in messages[1]
    assert "Nova Phone" in messages[2] and "BDT 4500.00" in messages[2]
    assert "Phones" in messages[3]
    assert "Open the configured NexHaat support page." in messages[4]
    category_markup = (
        send.call_args_list[3].kwargs.get("reply_markup")
        or send.call_args_list[3].args[3]
    )
    assert category_markup["inline_keyboard"][0][0]["text"] == "Phones"


def test_customer_cart_and_order_questions_return_owned_marketplace_data(client, app):
    configure_bots(app)
    telegram_id = 7812
    with app.app_context():
        customer = User(email="telegram-conversation@example.test", role="customer")
        customer.set_password("password123")
        category = Category(name="Gadgets", slug="gadgets", is_active=True)
        db.session.add_all([customer, category])
        db.session.flush()
        product = Product(
            category_id=category.id, name="Pocket Speaker", slug="pocket-speaker",
            description="Portable speaker.", price=1200, stock_quantity=4,
            is_available=True, moderation_status="approved",
        )
        db.session.add(product)
        db.session.add(TelegramIdentity(user_id=customer.id, telegram_user_id=telegram_id))
        db.session.flush()
        from app.services.cart import add_customer_cart_item
        add_customer_cart_item(customer.id, product.id, quantity=1)
        db.session.add(Order(
            order_number="NH-TELEGRAM-TRACK", user_id=customer.id,
            customer_name="Private Customer", phone="01234567890",
            address="Private address", total=1200, status="preparing",
            delivery_status="out_for_delivery",
        ))
        db.session.commit()

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    prompts = [
        (1206, "What is in my cart?"),
        (1207, "Where is my order?"),
    ]
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        responses = [
            client.post(
                "/telegram/customer/webhook",
                json=telegram_payload(update_id, telegram_id, prompt),
                headers=headers,
            )
            for update_id, prompt in prompts
        ]

    assert all(response.status_code == 200 for response in responses)
    cart_text, order_text = [call.args[2] for call in send.call_args_list]
    assert "Pocket Speaker" in cart_text and "BDT 1200.00" in cart_text
    assert "NH-TELEGRAM-TRACK" in order_text
    assert "Delivery: out_for_delivery" in order_text
    assert "01234567890" not in order_text
    assert "Private address" not in order_text


def test_customer_add_to_cart_prompt_shows_product_selection_without_mutating_cart(client, app):
    configure_bots(app)
    telegram_id = 7813
    with app.app_context():
        customer = User(email="telegram-add-flow@example.test", role="customer")
        customer.set_password("password123")
        category = Category(name="Audio", slug="audio", is_active=True)
        db.session.add_all([customer, category])
        db.session.flush()
        product = Product(
            category_id=category.id, name="Pocket Speaker", slug="pocket-speaker-add",
            description="Portable speaker.", price=1200, stock_quantity=4,
            is_available=True, moderation_status="approved",
        )
        db.session.add(product)
        db.session.add(TelegramIdentity(user_id=customer.id, telegram_user_id=telegram_id))
        db.session.commit()
        product_id = product.id

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1208, telegram_id, "Add a product to my cart"),
            headers=headers,
        )

    assert response.status_code == 200
    assert "Pocket Speaker" in send.call_args.args[2]
    markup = send.call_args.kwargs.get("reply_markup") or send.call_args.args[3]
    buttons = markup["inline_keyboard"]
    assert any(
        button.get("callback_data") == f"product-add|{product_id}"
        for row in buttons for button in row
    )
    with app.app_context():
        assert db.session.query(CustomerCartItem).count() == 0


def test_customer_bangla_budget_recommendation_shows_grounded_products_and_approved_ratings(client, app):
    configure_bots(app)
    with app.app_context():
        category = Category(name="Phones", slug="phones-budget", is_active=True)
        db.session.add(category)
        db.session.flush()
        products = [
            Product(
                category_id=category.id, name="Nova Phone", slug="nova-phone-budget",
                description="Affordable phone.", price=4500, stock_quantity=3,
                is_available=True, moderation_status="approved",
            ),
            Product(
                category_id=category.id, name="Orbit Phone", slug="orbit-phone-budget",
                description="Phone under the requested budget.", price=3990, stock_quantity=2,
                is_available=True, moderation_status="approved",
            ),
            Product(
                category_id=category.id, name="Premium Phone", slug="premium-phone-budget",
                description="Higher-priced phone.", price=5800, stock_quantity=2,
                is_available=True, moderation_status="approved",
            ),
        ]
        db.session.add_all(products)
        db.session.flush()
        db.session.add_all([
            Review(product_id=products[0].id, rating=5, author_name="Reviewer", status="approved"),
            Review(product_id=products[0].id, rating=1, author_name="Reviewer", status="pending"),
        ])
        db.session.commit()

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(
                1211, 7815, "আমার বাজেট ৫০০০ টাকা, ভালো একটা product suggest করো"
            ),
            headers=headers,
        )

    assert response.status_code == 200
    answer = send.call_args.args[2]
    assert "Nova Phone" in answer and "৳4500.00" in answer
    assert "Orbit Phone" in answer and "৳3990.00" in answer
    assert "Premium Phone" not in answer
    assert "⭐ 5.0 (1 reviews)" in answer
    assert "কোনটি সম্পর্কে বিস্তারিত জানতে চান?" in answer


def test_customer_compare_prompt_asks_for_names_then_compares_verified_ratings(client, app):
    configure_bots(app)
    with app.app_context():
        category = Category(name="Phones", slug="phones-compare", is_active=True)
        db.session.add(category)
        db.session.flush()
        first = Product(
            category_id=category.id, name="Nova Phone", slug="nova-phone-compare",
            description="First phone.", price=4500, stock_quantity=3,
            is_available=True, moderation_status="approved",
        )
        second = Product(
            category_id=category.id, name="Orbit Phone", slug="orbit-phone-compare",
            description="Second phone.", price=4900, stock_quantity=2,
            is_available=True, moderation_status="approved",
        )
        db.session.add_all([first, second])
        db.session.flush()
        db.session.add(Review(
            product_id=first.id, rating=5, author_name="Reviewer", status="approved",
        ))
        db.session.add(Review(
            product_id=second.id, rating=3, author_name="Reviewer", status="pending",
        ))
        db.session.commit()

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        clarify = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1209, 7814, "Compare two products"),
            headers=headers,
        )
        compared = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1210, 7814, "Compare Nova Phone vs Orbit Phone"),
            headers=headers,
        )

    assert clarify.status_code == 200
    assert "Which two product names" in send.call_args_list[0].args[2]
    assert compared.status_code == 200
    comparison = send.call_args_list[1].args[2]
    assert "Nova Phone — BDT 4500.00 | ⭐ 5.0/5 (1 reviews)" in comparison
    assert "Orbit Phone — BDT 4900.00" in comparison
    assert "⭐" not in comparison.split("Orbit Phone", 1)[1]


def test_telegram_shopping_context_is_private_expires_and_resolves_followups(client, app):
    from datetime import datetime, timedelta, timezone
    from app.services.telegram_shopping_context import (
        get_shopping_context, save_shopping_context,
    )

    configure_bots(app)
    with app.app_context():
        category = Category(name="Phones", slug="phones-context", is_active=True)
        db.session.add(category)
        db.session.flush()
        products = [
            Product(category_id=category.id, name=name, slug=slug,
                    description=f"{name} details.", price=price, stock_quantity=3,
                    is_available=True, moderation_status="approved")
            for name, slug, price in (
                ("Nova Phone", "nova-phone-context", 4500),
                ("Orbit Phone", "orbit-phone-context", 4900),
                ("Pixel Phone", "pixel-phone-context", 5200),
            )
        ]
        db.session.add_all(products)
        db.session.commit()
        save_shopping_context(7815, products)
        assert get_shopping_context(7816) == {"products": [], "selected_product": None}
        assert get_shopping_context(7815)["products"] == [
            "nova-phone-context", "orbit-phone-context", "pixel-phone-context",
        ]
        context = db.session.query(TelegramShoppingContext).one()
        context.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
        assert get_shopping_context(7815) == {"products": [], "selected_product": None}
        save_shopping_context(7815, products)

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        detail = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1211, 7815, "second product ta koto?"),
            headers=headers,
        )
        compared = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1212, 7815, "compare first and third"),
            headers=headers,
        )

    assert detail.status_code == 200
    assert "Orbit Phone" in send.call_args_list[0].args[2]
    assert "BDT 4900.00" in send.call_args_list[0].args[2]
    assert compared.status_code == 200
    comparison = send.call_args_list[1].args[2]
    assert "Nova Phone" in comparison and "Pixel Phone" in comparison
    assert "Orbit Phone" not in comparison


def test_telegram_contextual_add_to_cart_requires_explicit_callback_confirmation(client, app):
    configure_bots(app)
    telegram_id = 7817
    with app.app_context():
        customer = User(email="telegram-context-cart@example.test", role="customer")
        customer.set_password("password123")
        category = Category(name="Phones", slug="phones-context-cart", is_active=True)
        db.session.add_all([customer, category])
        db.session.flush()
        product = Product(
            category_id=category.id, name="Nova Phone", slug="nova-phone-context-cart",
            description="Available phone listing.", price=4500, stock_quantity=3,
            is_available=True, moderation_status="approved",
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(TelegramIdentity(user_id=customer.id, telegram_user_id=telegram_id))
        db.session.commit()
        from app.services.telegram_shopping_context import save_shopping_context

        save_shopping_context(telegram_id, [product], selected_product=product.slug)
        product_id = product.id

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1213, telegram_id, "eta cart e dao"),
            headers=headers,
        )

    assert response.status_code == 200
    assert "Nova Phone" in send.call_args.args[2]
    markup = send.call_args.kwargs.get("reply_markup") or send.call_args.args[3]
    confirmation = next(
        button["callback_data"]
        for row in markup["inline_keyboard"] for button in row
        if button.get("callback_data", "").startswith("cart-confirm|")
    )
    with app.app_context():
        assert db.session.query(CustomerCartItem).count() == 0
    callback = {
        "update_id": 1214,
        "callback_query": {
            "id": "callback-1214", "from": {"id": telegram_id},
            "message": {
                "message_id": 1214,
                "chat": {"id": telegram_id, "type": "private"},
            },
            "data": confirmation,
        },
    }
    with patch("app.telegram.customer.answer_callback", return_value=True), \
            patch("app.telegram.customer.send_message", return_value=True):
        confirmed = client.post(
            "/telegram/customer/webhook", json=callback, headers=headers,
        )
    assert confirmed.status_code == 200
    with app.app_context():
        assert db.session.query(CustomerCartItem).count() == 1


def test_customer_telegram_price_history_and_target_alert_are_account_scoped(client, app):
    configure_bots(app)
    telegram_id = 7722
    with app.app_context():
        customer = User(email="telegram-price@example.test", role="customer")
        customer.set_password("password123")
        category = Category(name="Electronics", slug="electronics-price", is_active=True)
        db.session.add_all([customer, category])
        db.session.flush()
        product = Product(
            category_id=category.id, name="Wireless Headphone",
            slug="wireless-headphone-price", description="Wireless headset.",
            price=1800, stock_quantity=3, is_available=True,
            moderation_status="approved",
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(TelegramIdentity(user_id=customer.id, telegram_user_id=telegram_id))
        db.session.commit()
        product.price = 1750
        db.session.commit()
        product_id = product.id

    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        history = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1120, telegram_id, "/price-history wireless headphone"),
            headers=headers,
        )
    assert history.status_code == 200
    history_text = send.call_args.args[2]
    assert "Recorded NexHaat listing prices" in history_text
    assert "BDT 1750.00" in history_text and "BDT 1800.00" in history_text

    group_payload = telegram_payload(1121, telegram_id, "/price-alert 1700 wireless headphone")
    group_payload["message"]["chat"] = {"id": -1001, "type": "group"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        group_result = client.post(
            "/telegram/customer/webhook", json=group_payload, headers=headers,
        )
    assert group_result.status_code == 200
    assert "private chat" in send.call_args.args[2]
    with app.app_context():
        assert AIProductPriceAlert.query.count() == 0

    with patch("app.telegram.customer.send_message", return_value=True) as send:
        fuzzy = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1122, telegram_id, "/price-alert 1700 wireless headfone"),
            headers=headers,
        )
    assert fuzzy.status_code == 200
    assert "exact product name or slug" in send.call_args.args[2]
    with app.app_context():
        assert AIProductPriceAlert.query.count() == 0

    with patch("app.telegram.customer.send_message", return_value=True) as send:
        invalid = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1123, telegram_id, "/price-alert 1700.001 wireless headphone"),
            headers=headers,
        )
    assert invalid.status_code == 200
    assert "up to two decimal places" in send.call_args.args[2]
    with app.app_context():
        assert AIProductPriceAlert.query.count() == 0

    with patch("app.telegram.customer.send_message", return_value=True) as send:
        saved = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1124, telegram_id, "/price-alert 1700 wireless headphone"),
            headers=headers,
        )
    assert saved.status_code == 200
    assert "BDT 1700.00" in send.call_args.args[2]
    with app.app_context():
        alert = db.session.query(AIProductPriceAlert).one()
        assert alert.product_id == product_id and alert.active
        product = db.session.get(Product, product_id)
        product.price = 1650
        db.session.commit()
        assert not alert.active
        assert Notification.query.filter_by(user_id=alert.user_id).count() == 1

    with patch("app.telegram.customer.send_message", return_value=True) as send:
        cancelled = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1125, telegram_id, "/price-alert off wireless headphone"),
            headers=headers,
        )
    assert cancelled.status_code == 200
    assert "no active price alert" in send.call_args.args[2]


def test_customer_telegram_reply_keeps_ai_answer_with_grounded_products(client, app, monkeypatch):
    configure_bots(app)
    with app.app_context():
        category = Category(name="Kitchen", slug="kitchen", is_active=True)
        db.session.add(category)
        db.session.flush()
        product = Product(
            category_id=category.id, name="Compact Blender", slug="compact-blender",
            description="Five-speed kitchen blender.", price=2500, stock_quantity=4,
            is_available=True, moderation_status="approved",
        )
        db.session.add(product)
        db.session.commit()
        product_summary = {"slug": product.slug, "name": product.name, "price": "2500.00"}

    requested = {}

    def answer_with_products(prompt, **kwargs):
        requested.update(prompt=prompt, kwargs=kwargs)
        return {
            "ok": True,
            "answer": "আপনার বাজেটের জন্য Compact Blender একটি ভালো পছন্দ; এতে পাঁচটি speed setting আছে।",
            "products": [product_summary],
        }

    monkeypatch.setattr("app.ai.marketplace_tools.handle_marketplace_ai_query", answer_with_products)
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1014, 7733, "কম দামে ভালো blender চাই"),
            headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
        )

    assert response.status_code == 200
    assert requested["prompt"] == "কম দামে ভালো blender চাই"
    reply = send.call_args.args[2]
    assert "পাঁচটি speed setting" in reply
    assert "Compact Blender - BDT 2500" in reply
    assert send.call_args.args[3]["inline_keyboard"]


def test_customer_telegram_voice_uses_local_transcription_and_shared_ai(client, app, monkeypatch):
    configure_bots(app)
    telegram_id = 7722
    captured = {}

    class LocalVoice:
        def __init__(self, _config):
            pass

        def transcribe(self, audio, *, filename, content_type):
            assert audio == b"OggSvoice-data"
            assert filename == "telegram-voice.ogg"
            assert content_type == "audio/ogg"
            return "বাংলায় Python recursion ব্যাখ্যা করো"

    def shared_query(prompt, **kwargs):
        captured.update(prompt=prompt, kwargs=kwargs)
        return {"ok": True, "answer": "Recursion হলো function নিজের ভেতর নিজেকে call করা।"}

    monkeypatch.setattr("app.telegram.customer.download_telegram_file", lambda *_args, **_kwargs: b"OggSvoice-data")
    monkeypatch.setattr("app.ai.core.provider.AIService", LocalVoice)
    monkeypatch.setattr("app.ai.marketplace_tools.handle_marketplace_ai_query", shared_query)
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json={"update_id": 1013, "message": {
                "from": {"id": telegram_id}, "chat": {"id": telegram_id, "type": "private"},
                "voice": {"file_id": "voice-id", "file_size": 100},
            }},
            headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
        )
    assert response.status_code == 200
    assert captured["prompt"] == "বাংলায় Python recursion ব্যাখ্যা করো"
    assert captured["kwargs"]["channel"] == "telegram-voice"
    assert "Recursion" in send.call_args.args[2]


def test_customer_telegram_photo_search_uses_transient_local_image_and_shared_catalog(client, app, monkeypatch):
    from io import BytesIO
    from PIL import Image

    configure_bots(app)
    telegram_id = 7723
    image = BytesIO()
    Image.new("RGB", (12, 8), color="blue").save(image, format="JPEG")
    photo_bytes = image.getvalue()
    captured = {}

    class LocalVision:
        def __init__(self, _config):
            pass

        def describe_image(self, normalized, *, content_type):
            assert content_type == "image/jpeg"
            with Image.open(BytesIO(normalized)) as decoded:
                assert decoded.format == "JPEG"
                assert decoded.size == (12, 8)
            return "a blue ceramic mug"

    def shared_query(prompt, **kwargs):
        captured.update(prompt=prompt, kwargs=kwargs)
        return {"ok": True, "answer": "আমি নীল সিরামিক মগ খুঁজেছি।"}

    monkeypatch.setattr(
        "app.telegram.customer.download_telegram_file",
        lambda _bot, _file_id, *, max_bytes: photo_bytes if max_bytes == 5 * 1024 * 1024 else None,
    )
    monkeypatch.setattr("app.ai.core.provider.AIService", LocalVision)
    monkeypatch.setattr("app.ai.marketplace_tools.handle_marketplace_ai_query", shared_query)
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/customer/webhook",
            json={"update_id": 1015, "message": {
                "from": {"id": telegram_id}, "chat": {"id": telegram_id, "type": "private"},
                "photo": [{"file_id": "photo-id", "file_size": len(photo_bytes)}],
                "caption": "সাদা রঙেও আছে?",
            }},
            headers={"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"},
        )

    assert response.status_code == 200
    assert "a blue ceramic mug" in captured["prompt"]
    assert "সাদা রঙেও আছে?" in captured["prompt"]
    assert captured["kwargs"]["channel"] == "telegram-image"
    assert captured["kwargs"]["user"] is None
    assert "নীল সিরামিক মগ" in send.call_args.args[2]


def test_customer_telegram_photo_rejects_oversized_and_invalid_images(app, monkeypatch):
    from app.telegram.customer import handle_customer_update

    app.config["TELEGRAM_CUSTOMER_BOT_TOKEN"] = "customer-test-token"
    monkeypatch.setattr("app.telegram.customer.download_telegram_file", lambda *_args, **_kwargs: b"not-image")
    def unexpected_vision(*_args, **_kwargs):
        raise AssertionError("invalid images must not reach vision")
    monkeypatch.setattr("app.ai.core.provider.AIService", unexpected_vision)
    sent = []
    monkeypatch.setattr(
        "app.telegram.customer.send_message",
        lambda _bot, _chat, text, *_args, **_kwargs: sent.append(text) or True,
    )
    with app.test_request_context("/"):
        handle_customer_update(
            {"message": {
                "caption": "check my order",
                "photo": [{"file_id": "photo", "file_size": 8}],
            }},
            7724, -1001,
        )
        handle_customer_update(
            {"message": {"photo": [{"file_id": "large", "file_size": 5 * 1024 * 1024 + 1}]}},
            7724, 7724,
        )
        handle_customer_update(
            {"message": {"photo": [{"file_id": "invalid", "file_size": 8}]}},
            7724, 7724,
        )
    assert any("private chat only" in message for message in sent)
    assert any("under 5 MB" in message for message in sent)
    assert any("not a valid product image" in message for message in sent)


def test_security_telegram_voice_stays_private_and_uses_local_scope(app, monkeypatch):
    from app.telegram.security import handle_security_update

    app.config.update(TELEGRAM_SECURITY_ADMIN_IDS="9001", TELEGRAM_SECURITY_BOT_TOKEN="security-test-token")
    bind_security_admin(app)
    captured = {}

    class LocalVoice:
        def __init__(self, _config):
            pass

        def transcribe(self, audio, *, filename, content_type):
            assert audio.startswith(b"OggS")
            return "Explain a suspicious login alert"

    def security_query(prompt, *, telegram_user_id, private_chat):
        captured.update(prompt=prompt, telegram_user_id=telegram_user_id, private_chat=private_chat)
        return {"answer": "Review the recorded audit events."}

    monkeypatch.setattr("app.telegram.security.download_telegram_file", lambda *_args, **_kwargs: b"OggSvoice-data")
    monkeypatch.setattr("app.ai.core.provider.AIService", LocalVoice)
    monkeypatch.setattr("app.ai.security_tools.handle_security_ai_query", security_query)
    sent = []
    monkeypatch.setattr("app.telegram.security.send_message", lambda _bot, _chat, text, *_args, **_kwargs:
                        sent.append(text) or True)
    with app.test_request_context("/"):
        assert handle_security_update({"message": {"voice": {"file_id": "voice", "file_size": 50}}}, 9001, 9001)
    assert captured == {"prompt": "Explain a suspicious login alert", "telegram_user_id": 9001, "private_chat": True}
    assert sent == ["Review the recorded audit events."]


def test_telegram_file_download_is_bounded_and_closes_response(app, monkeypatch):
    from app.telegram.common import download_telegram_file

    app.config["TELEGRAM_CUSTOMER_BOT_TOKEN"] = "customer-test-token"

    class Response:
        status_code = 200
        headers = {"Content-Length": "4"}

        def __init__(self, body):
            self.body = body
            self.closed = False

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"file_path": "voice/file.oga"}}

        def iter_content(self, chunk_size):
            assert chunk_size == 64 * 1024
            yield self.body

        def close(self):
            self.closed = True

    responses = [Response(b""), Response(b"OggS")]
    requested_urls = []

    def get(url, **kwargs):
        requested_urls.append(url)
        if url.endswith("/getFile"):
            return responses[0]
        return responses[1]

    monkeypatch.setattr("app.telegram.common.requests.get", get)
    with app.app_context():
        downloaded = download_telegram_file("customer", "file-id", max_bytes=8)
    assert downloaded == b"OggS", requested_urls
    assert responses[1].closed


def test_telegram_voice_reply_uses_optional_local_tts_and_send_voice(app, monkeypatch):
    from app.telegram.common import send_voice, synthesize_local_speech

    app.config.update(
        TELEGRAM_CUSTOMER_BOT_TOKEN="customer-test-token",
        AI_TTS_BASE_URL="https://voice.internal/v1", AI_TTS_MODEL="cosyvoice",
        AI_LOCAL_API_KEY="local-key", AI_TTS_VOICE="bn",
    )

    class SpeechResponse:
        headers = {"Content-Type": "audio/wav"}
        status_code = 200

        def __init__(self):
            self.closed = False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size == 64 * 1024
            yield b"RIFFvoice"

        def close(self):
            self.closed = True

        def json(self):
            return {"ok": True}

    speech_response = SpeechResponse()
    requests_seen = []

    def post(url, **kwargs):
        requests_seen.append((url, kwargs))
        return speech_response

    monkeypatch.setattr("app.telegram.common.requests.post", post)
    with app.app_context():
        speech = synthesize_local_speech("বাংলা উত্তর")
        assert speech == (b"RIFFvoice", "audio/wav")
        assert send_voice("customer", 8811, *speech)
        assert not send_voice("customer", 8811, b"not audio", "text/plain")

    assert speech_response.closed
    assert requests_seen[0][0] == "https://voice.internal/v1/audio/speech"
    assert requests_seen[0][1]["headers"]["Authorization"] == "Bearer local-key"
    assert requests_seen[1][0].endswith("/sendVoice")
    assert requests_seen[1][1]["data"] == {"chat_id": 8811}
    assert requests_seen[1][1]["files"]["voice"][0] == "answer.wav"
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
    with patch("app.telegram.customer.send_message", return_value=True) as send, patch(
        "app.telegram.common.send_message", return_value=True
    ) as limit_notice:
        first = client.post(endpoint, json=telegram_payload(501, 7001, "/help"), headers=headers)
        limited = client.post(endpoint, json=telegram_payload(502, 7001, "/help"), headers=headers)
        still_limited = client.post(
            endpoint, json=telegram_payload(503, 7001, "/help"), headers=headers
        )
    assert first.status_code == 200
    assert limited.status_code == 200
    assert still_limited.status_code == 200
    assert send.call_count == 1
    limit_notice.assert_called_once()
    assert "Too many requests" in limit_notice.call_args.args[2]
    with app.app_context():
        row = db.session.query(TelegramRateLimit).one()
        assert row.telegram_user_hash != "7001"
        assert len(row.telegram_user_hash) == 64
        assert row.request_count == 3


def test_security_bot_uses_stricter_limit_and_only_notifies_once(client, app):
    configure_bots(app)
    app.config.update(
        TELEGRAM_RATE_LIMIT_PER_MINUTE=30,
        TELEGRAM_SECURITY_RATE_LIMIT_PER_MINUTE=1,
    )
    endpoint = "/telegram/security/webhook"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "security-test-secret"}
    with patch("app.telegram.security.send_message", return_value=True) as send, patch(
        "app.telegram.common.send_message", return_value=True
    ) as limit_notice:
        first = client.post(
            endpoint, json=telegram_payload(701, 9001, "/status"), headers=headers
        )
        limited = client.post(
            endpoint, json=telegram_payload(702, 9001, "/status"), headers=headers
        )
        still_limited = client.post(
            endpoint, json=telegram_payload(703, 9001, "/status"), headers=headers
        )
    assert first.status_code == limited.status_code == still_limited.status_code == 200
    assert send.call_count == 1
    limit_notice.assert_called_once()
    assert "Too many requests" in limit_notice.call_args.args[2]


def test_security_bot_requires_active_mapped_website_admin(client, app):
    configure_bots(app)
    customer = User(email="telegram-customer-binding@example.test", role="customer")
    customer.set_password("password123")
    db.session.add(customer)
    db.session.flush()
    app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = f"9001:{customer.id}"

    with patch("app.telegram.security.send_message", return_value=True) as send:
        response = client.post(
            "/telegram/security/webhook",
            json=telegram_payload(704, 9001, "/audit"),
            headers={"X-Telegram-Bot-Api-Secret-Token": "security-test-secret"},
        )

    assert response.status_code == 200
    assert "Access denied" in send.call_args.args[2]


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


def test_customer_group_chat_cannot_start_link_or_change_ai_consent(client, app):
    from app.ai.core.consent import external_consent_enabled, set_external_consent

    configure_bots(app)
    principal = "telegram:customer:7007"
    set_external_consent(True, principal=principal)
    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        for update_id, text in ((708, "/link"), (709, "/ai-revoke")):
            payload = telegram_payload(update_id, 7007, text)
            payload["message"]["chat"] = {"id": -1007, "type": "group"}
            response = client.post(
                "/telegram/customer/webhook", json=payload, headers=headers,
            )
            assert response.status_code == 200

    assert send.call_count == 2
    assert all("private chat" in call.args[2].lower() for call in send.call_args_list)
    assert db.session.query(TelegramAccountLinkChallenge).count() == 0
    assert external_consent_enabled(principal=principal)


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
    health = type("HealthResponse", (), {"status_code": 200, "json": lambda self: {"status": "ok"}})()
    with patch("requests.get", return_value=health) as get, \
            patch("requests.post", return_value=response) as post:
        result = app.test_cli_runner().invoke(args=["set-telegram-webhooks", "--bot", "customer"])

    assert result.exit_code == 0
    assert customer_token not in result.output
    assert webhook_secret not in result.output
    assert "https://shop.example.test/telegram/customer/webhook" in result.output
    assert "Security bot" not in result.output
    get.assert_called_once_with("https://shop.example.test/health/live", timeout=10, allow_redirects=False)
    assert post.call_args.kwargs["json"]["secret_token"] == webhook_secret
    assert post.call_args.kwargs["json"]["drop_pending_updates"] is False


def test_webhook_registration_refuses_unhealthy_public_app_without_changing_webhooks(app):
    configure_bots(app)
    health = type("HealthResponse", (), {"status_code": 503, "json": lambda self: {"status": "unavailable"}})()
    with patch("requests.get", return_value=health), patch("requests.post") as post:
        result = app.test_cli_runner().invoke(args=["set-telegram-webhooks", "--bot", "customer"])

    assert result.exit_code != 0
    assert "no webhook was changed" in result.output.lower()
    post.assert_not_called()


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
        assert db.session.query(TelegramSecurityAlertRecipient).count() == 2


def test_security_alert_retry_skips_recipients_already_delivered(app):
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
        with patch(
            "app.services.telegram_alerts.send_message", side_effect=[True, False]
        ) as send:
            assert deliver_telegram_security_alerts() == 0
        assert [call.args[1] for call in send.call_args_list] == [9001, 9002]
        assert alert.status == "pending"
        assert db.session.query(TelegramSecurityAlertRecipient).count() == 1

        with patch("app.services.telegram_alerts.send_message", return_value=True) as retry:
            assert deliver_telegram_security_alerts() == 1
        assert [call.args[1] for call in retry.call_args_list] == [9002]
        assert alert.status == "sent"
        assert db.session.query(TelegramSecurityAlertRecipient).count() == 2


def test_admin_ai_action_notice_is_metadata_only_and_links_to_protected_workspace(app):
    configure_bots(app)
    from app.services.ai_action_notices import notify_admin_ai_action

    with app.test_request_context("/"):
        admin = User(email="ai-notice-admin@example.test", role="admin")
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()

        with patch("app.services.telegram_alerts.send_message", return_value=True) as send:
            recorded = notify_admin_ai_action(
                "admin.ai.query.completed",
                actor=admin,
                target_id="query-reference-123",
            )

    assert recorded is True
    assert send.call_count == 1
    message = send.call_args.args[2]
    assert "Admin AI read-only query completed" in message
    assert "query-reference-123" not in message
    assert admin.email not in message
    markup = send.call_args.args[3]
    assert markup["inline_keyboard"][0][0]["url"] == "https://shop.example.test/admin/ai"
    with app.app_context():
        event = db.session.query(AuditEvent).filter_by(
            action="admin.ai.query.completed"
        ).one()
        assert event.detail is None
        assert event.target_id == "query-reference-123"
        alert = db.session.query(TelegramSecurityAlert).one()
        assert alert.status == "sent"


def test_admin_ai_notice_delivers_only_its_own_queued_alert(app):
    configure_bots(app)
    from app.services.ai_action_notices import notify_admin_ai_action

    with app.test_request_context("/"):
        admin = User(email="ai-notice-target@example.test", role="admin")
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()
        record_audit("auth.admin_login_denied")
        with patch("app.services.telegram_alerts.send_message", return_value=True) as send:
            notify_admin_ai_action(
                "admin.ai.query.completed", actor=admin, target_id="query-only"
            )

    assert send.call_count == 1
    assert "Admin AI read-only query completed" in send.call_args.args[2]
    with app.app_context():
        alerts = db.session.query(TelegramSecurityAlert).order_by(
            TelegramSecurityAlert.id
        ).all()
        assert len(alerts) == 2
        assert alerts[0].status == "pending"
        assert alerts[1].status == "sent"


def test_security_bot_approvals_require_mapped_active_admin_and_update_website(client, app):
    configure_bots(app)
    with app.app_context():
        admin = User(email="telegram-approval-admin@example.test", role="admin")
        admin.set_password("password123")
        seller = User(email="telegram-approval-seller@example.test", role="seller")
        seller.set_password("password123")
        seller_profile = SellerProfile(
            user=seller,
            store_name="Telegram Review Store",
            contact_name="Seller",
            phone="01712345678",
            approval_status="pending",
        )
        db.session.add_all([admin, seller, seller_profile])
        db.session.commit()
        admin_id, seller_profile_id = admin.id, seller_profile.id
    app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = ""

    endpoint = "/telegram/security/webhook"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "security-test-secret"}
    with patch("app.telegram.security.send_message", return_value=True) as send:
        unlinked = client.post(
            endpoint, json=telegram_payload(5501, 9001, "/approvals"), headers=headers,
        )
    assert unlinked.status_code == 200
    assert "TELEGRAM_SECURITY_ADMIN_USER_MAP" in send.call_args.args[2]
    assert send.call_args.args[3] is None

    app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = f"9001:{admin_id}"
    with patch("app.telegram.security.send_message", return_value=True) as send:
        pending = client.post(
            endpoint, json=telegram_payload(5502, 9001, "/approvals"), headers=headers,
        )
    assert pending.status_code == 200
    assert "Telegram Review Store" in send.call_args.args[2]
    markup = send.call_args.args[3]
    callback_data = markup["inline_keyboard"][0][0]["callback_data"]
    assert callback_data == f"approval|seller|{seller_profile_id}|approved"

    callback_payload = {
        "update_id": 5503,
        "callback_query": {
            "id": "approval-5503",
            "from": {"id": 9001},
            "message": {
                "message_id": 5503,
                "chat": {"id": 9001, "type": "private"},
            },
            "data": callback_data,
        },
    }
    with patch("app.telegram.security.answer_callback", return_value=True), \
            patch("app.telegram.security.send_message", return_value=True) as send, \
            patch("app.services.telegram_alerts.send_message", return_value=True):
        approved = client.post(endpoint, json=callback_payload, headers=headers)
    assert approved.status_code == 200
    assert "website now shows" in send.call_args.args[2]
    with app.app_context():
        profile = db.session.get(SellerProfile, seller_profile_id)
        assert profile.approval_status == "approved"
        assert profile.reviewed_by_id == admin_id
        event = db.session.query(AuditEvent).filter_by(
            action="seller.review", target_id=str(seller_profile_id)
        ).one()
        assert event.actor_id == admin_id
        assert db.session.query(TelegramSecurityAlert).filter_by(
            audit_event_id=event.id, status="sent"
        ).one()

    callback_payload["update_id"] = 5504
    callback_payload["callback_query"]["id"] = "approval-5504"
    with patch("app.telegram.security.answer_callback", return_value=True), \
            patch("app.telegram.security.send_message", return_value=True) as send:
        stale = client.post(endpoint, json=callback_payload, headers=headers)
    assert stale.status_code == 200
    assert "no longer pending" in send.call_args.args[2]
    with app.app_context():
        assert db.session.query(AuditEvent).filter_by(
            action="seller.review", target_id=str(seller_profile_id)
        ).count() == 1


def test_telegram_natural_languages_call_grounded_search_tool(client, app, monkeypatch):
    import json
    from app.ai.core.provider import OpenAICompatibleProvider

    configure_bots(app)
    with app.app_context():
        phones = Category(name="Phones", slug="phones-nl-search", is_active=True)
        audio = Category(name="Audio", slug="audio-nl-search", is_active=True)
        db.session.add_all([phones, audio])
        db.session.flush()
        db.session.add_all([
            Product(
                category_id=phones.id, name="Nova Phone", slug="nova-phone-nl-search",
                description="Available phone.", price=4500, stock_quantity=4,
                is_available=True, moderation_status="approved",
            ),
            Product(
                category_id=audio.id, name="Gaming Headphones",
                slug="gaming-headphones-nl-search",
                description="Gaming headset.", price=4200, stock_quantity=3,
                is_available=True, moderation_status="approved",
            ),
        ])
        db.session.commit()

    requests_by_prompt = {
        "show me a good phone": {
            "query": "phone", "category": "Phones", "max_price": 5000, "limit": 5,
        },
        "আমার ৫ হাজারের মধ্যে ভালো একটা headphone দেখাও": {
            "query": "headphone", "category": "Audio", "max_price": 5000, "limit": 5,
        },
        "amar 5k budget er moddhe valo headphone lagbe": {
            "query": "headphone", "category": "Audio", "max_price": 5000, "limit": 5,
        },
    }
    turn_counts = {}
    submitted_tools = []

    def generate(self, *, prompt, **kwargs):
        submitted_tools.append(kwargs["tools"])
        turn_counts[prompt] = turn_counts.get(prompt, 0) + 1
        if turn_counts[prompt] == 1:
            return {
                "content": "",
                "tool_calls": [{
                    "id": f"search-{turn_counts[prompt]}",
                    "function": {
                        "name": "search_products",
                        "arguments": json.dumps(requests_by_prompt[prompt]),
                    },
                }],
            }
        return {"content": "I found verified marketplace matches.", "tool_calls": []}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    app.config.update(
        AI_ENABLED=True,
        AI_PROVIDER="openai_compatible",
        AI_API_KEY="test-key",
        AI_MODEL="test-model",
        AI_BASE_URL="https://provider.example/v1",
        AI_LOCAL_ENABLED=False,
        AI_EXTERNAL_ENABLED=False,
    )
    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        responses = [
            client.post(
                "/telegram/customer/webhook",
                json=telegram_payload(1400 + index, 7900, prompt),
                headers=headers,
            )
            for index, prompt in enumerate(requests_by_prompt)
        ]

    assert all(response.status_code == 200 for response in responses)
    messages = [call.args[2] for call in send.call_args_list]
    assert "Nova Phone" in messages[0] and "BDT 4500.00" in messages[0]
    assert "Gaming Headphones" in messages[1]
    assert "Gaming Headphones" in messages[2]
    assert all(
        "search_products" in {tool["function"]["name"] for tool in turn_tools}
        for turn_tools in submitted_tools
    )


def test_telegram_followup_uses_recent_real_product_results(client, app, monkeypatch):
    import json
    from app.ai.core.provider import OpenAICompatibleProvider
    from app.services.telegram_shopping_context import get_shopping_context

    configure_bots(app)
    telegram_id = 7901
    with app.app_context():
        category = Category(name="Phones", slug="phones-followup-ai", is_active=True)
        db.session.add(category)
        db.session.flush()
        db.session.add_all([
            Product(
                category_id=category.id, name=name, slug=slug,
                description=f"{name} listing.", price=price, stock_quantity=3,
                is_available=True, moderation_status="approved",
            )
            for name, slug, price in (
                ("Nova Phone", "nova-phone-followup-ai", 4500),
                ("Orbit Phone", "orbit-phone-followup-ai", 4900),
                ("Pixel Phone", "pixel-phone-followup-ai", 5200),
            )
        ])
        db.session.commit()

    seen_context = []
    turn_counts = {}

    def generate(self, *, prompt, context, **kwargs):
        turn_counts[prompt] = turn_counts.get(prompt, 0) + 1
        seen_context.append(context)
        if turn_counts[prompt] == 1 and prompt == "show me phones":
            arguments = {"query": "phone", "category": "Phones", "limit": 5}
            function = "search_products"
        elif turn_counts[prompt] == 1:
            recent = context["recent_products"]
            arguments = {"slug": recent[1]}
            function = "get_product"
        else:
            return {"content": "Here are the verified phone details.", "tool_calls": []}
        return {
            "content": "",
            "tool_calls": [{
                "id": f"followup-{turn_counts[prompt]}",
                "function": {
                    "name": function, "arguments": json.dumps(arguments),
                },
            }],
        }

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    app.config.update(
        AI_ENABLED=True,
        AI_PROVIDER="openai_compatible",
        AI_API_KEY="test-key",
        AI_MODEL="test-model",
        AI_BASE_URL="https://provider.example/v1",
        AI_LOCAL_ENABLED=False,
        AI_EXTERNAL_ENABLED=False,
    )
    headers = {"X-Telegram-Bot-Api-Secret-Token": "customer-test-secret"}
    with patch("app.telegram.customer.send_message", return_value=True) as send:
        first = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1410, telegram_id, "show me phones"),
            headers=headers,
        )
        followup = client.post(
            "/telegram/customer/webhook",
            json=telegram_payload(1411, telegram_id, "second product ta koto?"),
            headers=headers,
        )

    assert first.status_code == followup.status_code == 200
    assert len(seen_context[2]["recent_products"]) == 3
    assert "Orbit Phone" in send.call_args_list[-1].args[2]
    assert "BDT 4900.00" in send.call_args_list[-1].args[2]
    with app.app_context():
        assert get_shopping_context(telegram_id)["products"] == [
            "nova-phone-followup-ai", "orbit-phone-followup-ai",
            "pixel-phone-followup-ai",
        ]
