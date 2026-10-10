from decimal import Decimal
from io import BytesIO
import json

import pytest
from flask import current_app
from sqlalchemy import inspect, text

from app.ai.admin_tools import (
    get_product_performance_tool, get_review_spam_risk_tool,
    get_support_conversation_summaries_tool, handle_admin_ai_query,
)
from app.ai.core.permissions import AI_SCOPE_CUSTOMER, AI_SCOPE_SECURITY, AI_SCOPE_SELLER
from app.ai.core.provider import AIService, OpenAICompatibleProvider
from app.ai.core.tools import ToolRegistry
from app.ai.marketplace_tools import build_customer_tool_registry
from app.ai.security_tools import build_security_tool_registry
from app.ai.seller_tools import build_seller_tool_registry
from app.extensions import db
from app.models import (
    AIPreferences, AuditEvent, Category, CustomerCartItem, CustomerProfile,
    Notification, Product, ProductVariant, RecentViewedProduct, Review,
    SellerProfile, SupportConversation, SupportMessage, User, WishlistItem,
)
from app.services.ai_notifications import _emit_opted_in_alerts, send_smart_notification_digest
from app.services.cart import add_customer_cart_item
from app.services.personalization import personalized_products_for_user


def _user(role, suffix):
    user = User(email=f"{role}-{suffix}@example.test", role=role)
    user.set_password("test-password")
    db.session.add(user)
    db.session.flush()
    return user


def _seller(suffix):
    user = _user("seller", suffix)
    profile = SellerProfile(user_id=user.id, store_name=f"Store {suffix}",
                            contact_name="Seller", phone="01712345678",
                            approval_status="approved")
    db.session.add(profile)
    db.session.flush()
    return user


def _product(name="Wireless Headphone", slug="wireless-headphone", *, seller_id=None, stock=8, price="1800.00"):
    category = db.session.query(Category).filter_by(slug="electronics").first()
    if category is None:
        category = Category(name="Electronics", slug="electronics", is_active=True)
        db.session.add(category)
        db.session.flush()
    product = Product(category_id=category.id, seller_id=seller_id, name=name, slug=slug,
                      description="Wireless audio product with microphone and adjustable fit.",
                      price=Decimal(price), stock_quantity=stock, is_available=True,
                      moderation_status="approved")
    db.session.add(product)
    db.session.flush()
    return product


def _sign_in(client, user):
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = user.id
        browser_session["auth_version"] = user.auth_version


def test_customer_tool_cannot_read_another_customers_cart_or_override_identity(app):
    with app.app_context():
        customer_a = _user("customer", "cart-a")
        customer_b = _user("customer", "cart-b")
        product = _product()
        db.session.commit()
        add_customer_cart_item(customer_a.id, product.id, quantity=2)
        registry = build_customer_tool_registry()
        result = registry.call("get_customer_cart", scope=AI_SCOPE_CUSTOMER, user=customer_b)
        forged = registry.call("get_customer_cart", scope=AI_SCOPE_CUSTOMER, user=customer_b,
                               arguments={"user_id": customer_a.id})
        assert result["ok"] and result["result"]["items"] == []
        assert forged["ok"] is False


def test_cart_proposals_need_confirmation_and_revalidate_current_price(client, app):
    with app.app_context():
        customer = _user("customer", "cart-confirm")
        product = _product()
        db.session.commit()
        customer_id, auth_version, product_id, product_slug = customer.id, customer.auth_version, product.id, product.slug
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = customer_id
        browser_session["auth_version"] = auth_version
    proposed = client.post("/ai/cart/proposal", json={
        "action": "add", "product_slug": product_slug, "quantity": 1,
    })
    assert proposed.status_code == 200
    proposal_id = proposed.get_json()["proposal_id"]
    with app.app_context():
        Product.query.filter_by(id=product_id).one().price = Decimal("1750.00")
        db.session.commit()
    stale = client.post("/ai/cart/confirm", json={"proposal_id": proposal_id})
    assert stale.status_code == 409
    with app.app_context():
        from app.models import CustomerCartItem
        assert CustomerCartItem.query.filter_by(user_id=customer_id).count() == 0


def test_customer_language_fallback_extracts_banglish_and_hindi_budget(app):
    from app.ai.marketplace_tools import handle_marketplace_ai_query
    with app.app_context():
        _product()
        db.session.commit()
        banglish = handle_marketplace_ai_query("amar 2k er moddhe headphone lagbe")
        hindi = handle_marketplace_ai_query("मुझे headphone दो हजार के अंदर दिखाओ")
    assert [item["slug"] for item in banglish["products"]] == ["wireless-headphone"]
    assert [item["slug"] for item in hindi["products"]] == ["wireless-headphone"]


def test_seller_listing_tool_is_owner_scoped_and_suggestions_are_read_only(app):
    with app.app_context():
        owner = _seller("owner")
        other = _seller("other")
        product = _product(seller_id=owner.id)
        db.session.commit()
        registry = build_seller_tool_registry()
        denied = registry.call("get_seller_listing_context", scope=AI_SCOPE_SELLER,
                               user=other, arguments={"product_id": product.id})
        quality = registry.call("get_seller_listing_quality", scope=AI_SCOPE_SELLER,
                                user=owner, arguments={"product_id": product.id})
        assert denied["ok"] is False
        assert quality["ok"] is True
        assert "score" in quality["result"]
        assert product.name == "Wireless Headphone"


def test_admin_tools_are_role_scoped_and_product_performance_is_read_only(app):
    with app.app_context():
        admin = _user("admin", "ai")
        support = _user("support", "ai")
        product = _product()
        db.session.commit()
        low = get_product_performance_tool(user=admin)
        with pytest.raises(ValueError):
            get_product_performance_tool(user=support)
        assert low["low_performing_products"][0]["product"] == product.name
        assert product.is_available is True


def test_pending_review_risk_only_flags_for_human_moderation(app):
    with app.app_context():
        admin = _user("admin", "review-risk")
        product = _product()
        review = Review(product_id=product.id, rating=1, comment="Buy now at https://example.test",
                        author_name="Reviewer", status="pending")
        db.session.add(review)
        db.session.commit()
        flags = get_review_spam_risk_tool(user=admin)
        assert flags[0]["review_id"] == review.id
        assert flags[0]["risk"] == "high"
        assert review.status == "pending"


def test_smart_notification_digest_is_opt_in_and_rate_capped(app):
    from datetime import datetime, timedelta, timezone
    with app.app_context():
        customer = _user("customer", "cart-reminder")
        product = _product()
        now = datetime.now(timezone.utc)
        db.session.add(AIPreferences(user_id=customer.id, smart_notifications_enabled=True))
        db.session.add(CustomerCartItem(user_id=customer.id, product_id=product.id,
                                        item_key=str(product.id), quantity=1,
                                        created_at=now - timedelta(days=3),
                                        updated_at=now - timedelta(days=3)))
        db.session.commit()
        first = send_smart_notification_digest(now=now)
        second = send_smart_notification_digest(now=now + timedelta(hours=1))
        notice = Notification.query.filter_by(user_id=customer.id).one()
        assert first["cart_reminders"] == 1
        assert second["cart_reminders"] == 0
        assert second["skipped"] == 1
        assert notice.link == "/cart?from=ai-cart-reminder"
        assert "still in your cart" in notice.message


def test_smart_notification_digest_recommends_only_after_customer_signal(app):
    from datetime import datetime, timezone
    with app.app_context():
        customer = _user("customer", "recommendation-notice")
        viewed = _product("Viewed Product", "viewed-product")
        pick = _product("Recommended Product", "recommended-product")
        db.session.add_all([
            AIPreferences(user_id=customer.id, smart_notifications_enabled=True),
            RecentViewedProduct(user_id=customer.id, product_id=viewed.id,
                                viewed_at=datetime.now(timezone.utc)),
        ])
        db.session.commit()
        result = send_smart_notification_digest()
        notice = Notification.query.filter_by(user_id=customer.id).one()
        assert result["recommendations"] == 1
        assert notice.link == f"/food/{pick.slug}?from=ai-recommendation"


def test_low_history_inventory_does_not_claim_a_stockout_forecast(app):
    with app.app_context():
        seller = _seller("low-history")
        product = _product(seller_id=seller.id, stock=3)
        result = build_seller_tool_registry().call(
            "get_seller_inventory_forecast", scope=AI_SCOPE_SELLER,
            user=seller, arguments={"days": 30},
        )
        assert result["ok"]
        forecast = result["result"]["products"][0]
        assert forecast["product"] == product.name
        assert forecast["low_stock"] is True
        assert forecast["estimated_days_until_stockout"] is None
        assert forecast["confidence"] == "low"


def test_model_cannot_invoke_a_mutating_tool_without_confirmation():
    registry = ToolRegistry()
    registry.register("change_inventory", lambda **kwargs: {"changed": True},
                      scope=AI_SCOPE_CUSTOMER, mutation=True)
    blocked = registry.call("change_inventory", scope=AI_SCOPE_CUSTOMER)
    assert blocked["ok"] is False
    assert blocked["error"] == "Tool is not available in this assistant scope."


def test_support_summaries_redact_personal_data_and_cases_are_owner_scoped(app, client):
    with app.app_context():
        customer = _user("customer", "support-case")
        other = _user("customer", "support-other")
        admin = _user("admin", "support-reader")
        case = SupportConversation(user_id=customer.id, subject="Delivery help", category="delivery")
        case.messages.append(SupportMessage(sender_user_id=customer.id, sender_role="customer",
                                            body="Call me at 01712345678 or person@example.test"))
        db.session.add(case)
        db.session.commit()
        case_id = case.id
        result = get_support_conversation_summaries_tool(user=admin)
        assert "[email removed]" in result[0]["messages"][0]["text"]
        assert "[phone removed]" in result[0]["messages"][0]["text"]
        other_id = other.id
    _sign_in(client, other)
    response = client.get(f"/support/{case_id}")
    assert response.status_code == 404


def test_review_summary_uses_approved_reviews_only(app):
    from app.ai.marketplace_tools import get_review_summary_source
    with app.app_context():
        product = _product()
        db.session.add_all([
            Review(product_id=product.id, rating=5, comment="Good build", author_name="A", status="approved"),
            Review(product_id=product.id, rating=1, comment="Pending text", author_name="B", status="pending"),
        ])
        db.session.commit()
        source = get_review_summary_source(product_slug=product.slug)
    assert source["count"] == 1
    assert source["reviews"] == ["Good build"]


def test_opt_in_smart_alerts_are_daily_capped_and_only_for_interested_customers(app):
    with app.app_context():
        interested = _user("customer", "notify")
        opted_out = _user("customer", "no-notify")
        product = _product()
        db.session.add_all([
            AIPreferences(user_id=interested.id, smart_notifications_enabled=True),
            AIPreferences(user_id=opted_out.id, smart_notifications_enabled=False),
            WishlistItem(user_id=interested.id, product_id=product.id),
            WishlistItem(user_id=opted_out.id, product_id=product.id),
        ])
        db.session.commit()
        product.price = Decimal("1700.00")
        db.session.commit()
        product.stock_quantity = 4
        db.session.commit()
        assert Notification.query.filter_by(user_id=interested.id).count() == 1
        assert Notification.query.filter_by(user_id=opted_out.id).count() == 0


def test_personalized_home_recommendations_use_private_customer_signals(app):
    with app.app_context():
        customer = _user("customer", "personalized")
        viewed = _product("Viewed Item", "viewed-item")
        related = _product("Related Item", "related-item")
        db.session.add(WishlistItem(user_id=customer.id, product_id=viewed.id))
        db.session.commit()
        results = personalized_products_for_user(customer)
        assert related in results
        assert viewed not in results


def test_admin_and_seller_ai_pages_reject_customer_scope(client, app):
    with app.app_context():
        customer = _user("customer", "route-scope")
        db.session.commit()
        customer_identity = (customer.id, customer.auth_version)
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = customer_identity[0]
        browser_session["auth_version"] = customer_identity[1]
    assert client.get("/admin/ai").status_code == 403
    assert client.post("/admin/ai/query", json={"prompt": "show sales"}).status_code == 403
    assert client.get("/seller/ai").status_code == 403
    assert client.post("/seller/ai/suggest", json={"title": "x"}).status_code == 403


def test_seller_suggestion_endpoint_only_uses_own_listing_and_never_saves(client, app):
    with app.app_context():
        seller_a = _seller("endpoint-owner")
        seller_b = _seller("endpoint-other")
        product = _product(seller_id=seller_a.id)
        db.session.commit()
        seller_id, auth_version, product_id = seller_b.id, seller_b.auth_version, product.id
    with client.session_transaction() as browser_session:
        browser_session["user_id"] = seller_id
        browser_session["auth_version"] = auth_version
    response = client.post("/seller/ai/suggest", json={"product_id": product_id,
                                                        "title": "My fake listing",
                                                        "description": "Some draft"})
    assert response.status_code == 503
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.name == "Wireless Headphone"
        assert product.price == Decimal("1800.00")


def test_admin_copilot_returns_real_read_only_data(client, app):
    with app.app_context():
        admin = _user("admin", "copilot")
        _product()
        db.session.commit()
        admin_id = admin.id
    with app.app_context():
        admin = db.session.get(User, admin_id)
        result = handle_admin_ai_query("Show low stock and product performance", user=admin)
        assert result["ok"] is True
        assert "get_product_performance" in result["tools_used"]


def test_ai_settings_urls_and_malformed_model_tool_calls_are_safe():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Verified response", "tool_calls": []}}]}

    class FakeSession:
        def __init__(self):
            self.calls = []

        def post(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return FakeResponse()

    session = FakeSession()
    provider = OpenAICompatibleProvider(api_key="mock-only", model="mock-model",
                                        base_url="https://ai.example.test/v1", session=session)
    result = provider.generate(messages=[{"role": "user", "content": "test"}], model="mock-model")
    assert result["content"] == "Verified response"
    assert session.calls[0][0][0] == "https://ai.example.test/v1/chat/completions"
    try:
        provider.generate(prompt="x", base_url="file:///etc/passwd")
    except Exception as error:
        assert "invalid" in str(error).lower()
    else:
        raise AssertionError("Unsafe provider URL was accepted")


def test_provider_timeout_and_malformed_tool_arguments_fall_back_safely():
    import requests

    class TimeoutProvider:
        def generate(self, **kwargs):
            raise requests.Timeout("private provider detail")

    service = AIService({"AI_ENABLED": True, "AI_PROVIDER": "mock",
                         "AI_MODEL": "test", "AI_MAX_TOOL_CALLS": 1},
                        provider=TimeoutProvider())
    timeout = service.respond("search headphones", scope=AI_SCOPE_CUSTOMER,
                              tools=build_customer_tool_registry())
    assert timeout["ok"] is False
    assert "private provider detail" not in str(timeout)

    class MalformedProvider:
        def generate(self, **kwargs):
            return {"content": "", "tool_calls": [{"id": "1", "function": {
                "name": "search_products", "arguments": "{bad json"}}]}

    malformed = AIService({"AI_ENABLED": True, "AI_PROVIDER": "mock", "AI_MODEL": "test"},
                          provider=MalformedProvider()).respond(
        "search headphones", scope=AI_SCOPE_CUSTOMER,
        tools=build_customer_tool_registry(),
    )
    assert malformed["ok"] is False
    assert "temporarily unavailable" in malformed["fallback"].lower()


def test_mocked_vision_and_transcription_never_need_live_provider():
    class FakeResponse:
        def __init__(self, value):
            self.value = value

        def raise_for_status(self):
            return None

        def json(self):
            return self.value

    class FakeSession:
        def __init__(self):
            self.responses = [
                FakeResponse({"choices": [{"message": {"content": "black running shoe"}}]}),
                FakeResponse({"text": "headphones under 2000"}),
            ]
            self.calls = []

        def post(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return self.responses.pop(0)

    fake = FakeSession()
    provider = OpenAICompatibleProvider(api_key="mock-only", model="vision-model",
                                        base_url="https://ai.example.test/v1", session=fake)
    assert provider.describe_image(image_bytes=b"mock image", content_type="image/jpeg") == "black running shoe"
    assert "data:image/jpeg;base64," in fake.calls[0][1]["json"]["messages"][0]["content"][1]["image_url"]["url"]
    assert provider.transcribe(audio=b"mock audio", filename="voice.webm", content_type="audio/webm") == "headphones under 2000"


def test_security_assistant_is_numeric_allowlist_scoped_and_read_only(app):
    from app.ai.security_tools import handle_security_ai_query
    with app.app_context():
        current_app.config.update(TELEGRAM_SECURITY_ADMIN_IDS="34567", AI_ENABLED=False)
        allowed = handle_security_ai_query("any suspicious login alerts?", telegram_user_id=34567)
        denied = handle_security_ai_query("show health", telegram_user_id=45678)
        assert allowed["ok"] is True
        assert allowed["scope"] == AI_SCOPE_SECURITY
        assert denied["ok"] is False
        registry = build_security_tool_registry()
        blocked = registry.call("get_security_summary", scope=AI_SCOPE_CUSTOMER)
        assert blocked["ok"] is False


def test_security_summary_flags_admin_activity_for_human_review(app):
    from datetime import datetime, timezone
    from app.ai.security_tools import get_security_summary_tool
    with app.app_context():
        current_app.config["TELEGRAM_SECURITY_ADMIN_IDS"] = "34567"
        now = datetime.now(timezone.utc)
        db.session.add_all([
            AuditEvent(action="admin.settings.updated", actor_role="admin", created_at=now)
            for _ in range(50)
        ])
        db.session.commit()
        actor = type("AuthorizedSecurityPrincipal", (), {
            "security_authorized": True, "telegram_id": 34567,
        })()
        result = get_security_summary_tool(user=actor)
        assert result["admin_activity_events"] == 50
        assert result["unusual_admin_activity"] == "review"


def test_image_and_voice_endpoints_reject_invalid_upload_signatures(client):
    image = client.post("/ai/image-search", data={"image": (BytesIO(b"not an image"), "bad.png", "image/png")})
    audio = client.post("/ai/voice-search", data={"audio": (BytesIO(b"not webm"), "bad.webm", "audio/webm")})
    assert image.status_code == 415
    assert audio.status_code == 415


def test_mocked_image_and_voice_routes_search_catalog_without_persisting_uploads(client, app, monkeypatch):
    image_buffer = BytesIO()
    from PIL import Image
    Image.new("RGB", (8, 8), color="black").save(image_buffer, format="JPEG")
    image_buffer.seek(0)
    with app.app_context():
        product = _product()
        db.session.commit()
        from app.ai.marketplace_tools import handle_marketplace_ai_query
        assert product.available_stock > 0 and product.category.is_active is True
        direct = handle_marketplace_ai_query("wireless headphone")
        assert direct["products"], direct

    class MockService:
        def __init__(self, _config):
            pass

        def describe_image(self, _raw, content_type="image/jpeg"):
            assert content_type == "image/jpeg"
            return "wireless headphone"

        def transcribe(self, _raw, filename, content_type):
            assert filename == "voice-audio"
            return "wireless headphone under 2k"

    monkeypatch.setattr("app.routes.ai.AIService", MockService)
    image_response = client.post("/ai/image-search", data={
        "image": (image_buffer, "product.jpg", "image/jpeg")
    })
    audio_response = client.post("/ai/voice-search", data={
        "audio": (BytesIO(bytes.fromhex("1A45DFA3") + b"mock voice"), "voice.webm", "audio/webm")
    })
    assert image_response.status_code == 200
    assert audio_response.status_code == 200
    image_body = image_response.get_json()
    audio_body = audio_response.get_json()
    assert image_body.get("search_description") == "wireless headphone", image_body
    assert audio_body.get("transcript") == "wireless headphone under 2k", audio_body
    assert image_body.get("products"), image_body
    assert audio_body.get("products"), audio_body
    assert image_body["products"][0]["slug"] == "wireless-headphone"
    assert audio_body["products"][0]["slug"] == "wireless-headphone"
    with app.app_context():
        assert SupportMessage.query.count() == 0


def test_ai_request_rate_limit_is_shared_and_enforced(client, app):
    app.config.update(AI_RATE_LIMIT=1, AI_RATE_LIMIT_WINDOW_SECONDS=60)
    first = client.post("/ai/chat", json={"prompt": "search burgers"})
    second = client.post("/ai/chat", json={"prompt": "search pizza"})
    assert first.status_code == 200
    assert second.status_code == 429


def test_support_escalation_returns_safe_contact_links(app):
    from app.ai.marketplace_tools import handle_marketplace_ai_query
    with app.test_request_context("/"):
        current_app.config["SUPPORT_EMAIL"] = "help@example.test"
        user = _user("customer", "support-link")
        result = handle_marketplace_ai_query("contact support", user=user)
        assert result["support_contact"]["support_page"] == "/support"
        assert result["support_contact"]["email"] == "help@example.test"


def test_migration_reaches_single_head_with_ai_and_support_tables(tmp_path):
    class MigrationConfig:
        TESTING = False
        ENVIRONMENT = "production"
        SECRET_KEY = "migration-test-secret-that-is-long-enough-123456"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'ai-migration.sqlite3').as_posix()}"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SESSION_COOKIE_SECURE = False

    from app import create_app
    migration_app = create_app(MigrationConfig)
    with migration_app.app_context():
        db.drop_all()
    result = migration_app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with migration_app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        assert {"ai_request_windows", "ai_preferences", "support_conversations", "support_messages"} <= tables
        columns = {item["name"] for item in inspect(db.engine).get_columns("ai_preferences")}
        assert {"last_cart_reminder_at", "last_recommendation_notification_at"} <= columns
        heads = db.session.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        assert heads == ["20261006_26"]
