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
from app.ai.core.provider import AIProviderError, AIService, OpenAICompatibleProvider
from app.ai.core.tools import ToolRegistry
from app.ai.marketplace_tools import build_customer_tool_registry
from app.ai.security_tools import build_security_tool_registry
from app.ai.seller_tools import build_seller_tool_registry
from app.extensions import db
from app.models import (
    AIProductPriceAlert, AIProductPriceHistory, AIPreferences, AuditEvent, Category, CustomerCartItem, CustomerProfile,
    Notification, Product, ProductVariant, RecentViewedProduct, Review,
    SellerProfile, SupportConversation, SupportMessage, TelegramSecurityAlert, User, WishlistItem,
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


def test_cart_proposals_need_confirmation_and_revalidate_current_price(client, app, monkeypatch):
    from app.models import AuditEvent

    notices = []
    monkeypatch.setattr(
        "app.services.ai_action_notices.deliver_telegram_security_alerts",
        lambda *, alert_id: notices.append(alert_id) or 1,
    )
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
        assert db.session.query(AuditEvent).filter_by(
            action="customer.ai.cart_change.confirmed"
        ).count() == 0

    fresh = client.post("/ai/cart/proposal", json={
        "action": "add", "product_slug": product_slug, "quantity": 1,
    })
    assert fresh.status_code == 200
    confirmed = client.post("/ai/cart/confirm", json={
        "proposal_id": fresh.get_json()["proposal_id"],
    })
    assert confirmed.status_code == 200
    assert confirmed.get_json()["ok"] is True
    assert len(notices) == 1
    with app.app_context():
        assert db.session.query(CustomerCartItem).filter_by(user_id=customer_id).count() == 1
        event = db.session.query(AuditEvent).filter_by(
            action="customer.ai.cart_change.confirmed"
        ).one()
        alert = db.session.query(TelegramSecurityAlert).filter_by(
            audit_event_id=event.id
        ).one()
        assert alert.status == "pending"


def test_customer_language_fallback_extracts_banglish_and_hindi_budget(app):
    from app.ai.marketplace_tools import handle_marketplace_ai_query
    with app.app_context():
        _product()
        db.session.commit()
        banglish = handle_marketplace_ai_query("amar 2k er moddhe headphone lagbe")
        hindi = handle_marketplace_ai_query("मुझे headphone दो हजार के अंदर दिखाओ")
    assert [item["slug"] for item in banglish["products"]] == ["wireless-headphone"]
    assert [item["slug"] for item in hindi["products"]] == ["wireless-headphone"]


def test_catalog_listing_questions_return_real_products_without_ai(app, monkeypatch):
    from app.ai.marketplace_tools import handle_marketplace_ai_query

    def fail_if_provider_called(*_args, **_kwargs):
        raise AssertionError("Catalog listing must use verified marketplace data.")

    monkeypatch.setattr("app.ai.marketplace_tools.AIService.respond", fail_if_provider_called)
    with app.app_context():
        _product("Wireless Headphone", "wireless-headphone", price="1800.00")
        _product("Compact Blender", "compact-blender", price="1250.00")
        db.session.commit()

        english = handle_marketplace_ai_query("What products do you have?")
        banglish = handle_marketplace_ai_query("ki ki product ache?")

    expected_slugs = {"wireless-headphone", "compact-blender"}
    assert {item["slug"] for item in english["products"]} == expected_slugs
    assert {item["slug"] for item in banglish["products"]} == expected_slugs
    assert english["tools_used"] == ["search_products"]
    assert banglish["tools_used"] == ["search_products"]


def test_web_ai_followup_resolves_recent_product_and_bounds_context(client, app):
    with app.app_context():
        first = _product("Wireless Headphone", "wireless-headphone", price="1800.00")
        second = _product("Compact Blender", "compact-blender", price="1250.00")
        db.session.commit()
        slugs = [first.slug, second.slug]

    search = client.post("/ai/chat", json={"prompt": "What products do you have?"})
    products = search.get_json()["products"]
    compared = client.post("/ai/chat", json={
        "prompt": "Compare them",
        "recent_products": [item["slug"] for item in products],
    })
    followup = client.post("/ai/chat", json={
        "prompt": "Tell me more about the second one",
        "recent_products": [item["slug"] for item in products],
    })
    invalid_context = client.post("/ai/chat", json={
        "prompt": "Tell me more about it",
        "recent_products": slugs * 3,
    })

    assert search.status_code == 200
    assert {item["slug"] for item in products} == set(slugs)
    assert compared.status_code == 200
    assert compared.get_json()["tools_used"] == ["compare_products"]
    assert {item["slug"] for item in compared.get_json()["products"]} == set(slugs)
    assert followup.status_code == 200
    assert followup.get_json()["tools_used"] == ["get_product"]
    assert products[1]["name"] in followup.get_json()["answer"]
    assert invalid_context.status_code == 400


def test_bangla_budget_and_gift_prompts_use_grounded_catalog_without_ai(app, monkeypatch):
    from app.ai.marketplace_tools import handle_marketplace_ai_query

    def fail_if_provider_called(*_args, **_kwargs):
        raise AssertionError("Bangla shopping requests must use verified catalog data.")

    monkeypatch.setattr("app.ai.marketplace_tools.AIService.respond", fail_if_provider_called)
    with app.app_context():
        _product("Compact Blender", "compact-blender", price="1250.00")
        _product("Premium Blender", "premium-blender", price="4200.00")
        _product("Gardening Gloves", "gardening-gloves", price="500.00")
        db.session.commit()

        budget = handle_marketplace_ai_query("কম দামে ভালো blender চাই")
        gift = handle_marketplace_ai_query("মায়ের জন্য gardening gift সাজেস্ট করো")

    assert [item["slug"] for item in budget["products"]] == ["compact-blender", "premium-blender"]
    assert budget["products"][0]["price"] == "1250.00"
    assert "মিলে যাওয়া" in budget["answer"]
    assert [item["slug"] for item in gift["products"]] == ["gardening-gloves"]
    assert "Gardening Gloves" in gift["answer"]
    assert "৳500.00" in gift["answer"]
    assert "🛍️" in gift["answer"]


def test_broad_budget_recommendation_returns_matching_products_and_prices(app, monkeypatch):
    from app.ai.marketplace_tools import handle_marketplace_ai_query

    def fail_if_provider_called(*_args, **_kwargs):
        raise AssertionError("Catalog recommendations must use verified marketplace data.")

    monkeypatch.setattr("app.ai.marketplace_tools.AIService.respond", fail_if_provider_called)
    with app.app_context():
        _product("Budget Earbuds", "budget-earbuds", price="450.00")
        _product("Premium Headphones", "premium-headphones", price="1800.00")
        db.session.commit()

        result = handle_marketplace_ai_query(
            "my budget 500BDT suggest me some product this bujjet"
        )

    assert [item["slug"] for item in result["products"]] == ["budget-earbuds"]
    assert "Budget Earbuds" in result["answer"]
    assert "BDT 450.00" in result["answer"]
    assert "BDT 1800.00" not in result["answer"]


def test_budget_recommendation_explains_when_no_product_fits(app):
    from app.ai.marketplace_tools import handle_marketplace_ai_query

    with app.app_context():
        _product("Wireless Headphone", "wireless-headphone", price="1800.00")
        db.session.commit()

        result = handle_marketplace_ai_query(
            "suggest me some product under 500 BDT"
        )

    assert result["products"] == []
    assert "within BDT 500.00" in result["answer"]
    assert "higher budget" in result["answer"]


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
                AIPreferences(user_id=customer.id, smart_notifications_enabled=True,
                              personalized_recommendations_enabled=True),
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
        db.session.add(AIPreferences(user_id=customer.id))
        db.session.commit()
        assert personalized_products_for_user(customer) == []
        preference = db.session.get(AIPreferences, customer.id)
        preference.personalized_recommendations_enabled = True
        db.session.commit()
        results = personalized_products_for_user(customer)
        assert related in results
        assert viewed not in results


def test_price_history_uses_observed_catalog_prices_and_missing_history_is_honest(app):
    from app.ai.marketplace_tools import handle_marketplace_ai_query

    with app.app_context():
        product = _product()
        db.session.commit()
        first = AIProductPriceHistory.query.filter_by(product_id=product.id).one()
        assert first.effective_price == Decimal("1800.00")
        product.price = Decimal("1700.00")
        db.session.commit()
        history = AIProductPriceHistory.query.filter_by(product_id=product.id).order_by(
            AIProductPriceHistory.recorded_at.desc()
        ).all()
        assert [row.effective_price for row in history] == [Decimal("1700.00"), Decimal("1800.00")]
        answer = handle_marketplace_ai_query("price history for wireless headphone")
        assert answer["tools_used"] == ["get_product_price_history"]
        assert answer["data"]["observation_count"] == 2

        AIProductPriceHistory.query.filter_by(product_id=product.id).delete()
        db.session.commit()
        missing = handle_marketplace_ai_query("price history for wireless headphone")
        assert missing["data"]["observations"] == []
        assert "No earlier observed" in missing["answer"]


def test_target_price_alert_notifies_once_when_price_crosses_target(app):
    from app.services.ai_price_alerts import save_price_alert

    with app.app_context():
        customer = _user("customer", "target-price")
        product = _product()
        db.session.commit()
        alert = save_price_alert(customer, product, Decimal("1700.00"))
        assert alert.active
        product.price = Decimal("1750.00")
        db.session.commit()
        assert alert.active
        assert AIProductPriceHistory.query.filter_by(product_id=product.id).order_by(
            AIProductPriceHistory.recorded_at.desc(), AIProductPriceHistory.id.desc()
        ).first().effective_price == Decimal("1750.00")
        product.price = Decimal("1700.00")
        db.session.commit()
        assert AIProductPriceHistory.query.filter_by(product_id=product.id).order_by(
            AIProductPriceHistory.recorded_at.desc(), AIProductPriceHistory.id.desc()
        ).first().effective_price == Decimal("1700.00")
        assert not alert.active and alert.notified_at is not None
        notice = Notification.query.filter_by(user_id=customer.id).one()
        assert "BDT 1700.00" in notice.message
        assert notice.link == f"/food/{product.slug}?from=ai-price-alert"
        product.price = Decimal("1600.00")
        db.session.commit()
        assert Notification.query.filter_by(user_id=customer.id).count() == 1


def test_price_alert_form_is_scoped_to_signed_in_customer(client, app):
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        owner = _user("customer", "price-alert-owner")
        other = _user("customer", "price-alert-other")
        product = _product()
        db.session.commit()
        product_slug = product.slug
        owner_id, owner_version = owner.id, owner.auth_version
        other_id, other_version = other.id, other.auth_version

    _sign_in(client, type("Identity", (), {"id": owner_id, "auth_version": owner_version})())
    detail = client.get(f"/food/{product_slug}")
    assert detail.status_code == 200
    assert b"Set price alert" in detail.data
    history_response = client.get(f"/ai/price-history/{product_slug}")
    assert history_response.status_code == 200
    assert history_response.get_json()["history"]
    saved = client.post(f"/ai/price-alert/{product_slug}", data={"target_price": "1700.00"})
    assert saved.status_code == 302
    _sign_in(client, type("Identity", (), {"id": other_id, "auth_version": other_version})())
    cancelled = client.post(f"/ai/price-alert/{product_slug}", data={"action": "cancel"})
    assert cancelled.status_code == 302
    with app.app_context():
        alert = AIProductPriceAlert.query.one()
        assert alert.user_id == owner_id and alert.active


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


def test_admin_ai_query_logs_without_prompt_and_shows_web_activity(client, app, monkeypatch):
    app.config.update(
        TELEGRAM_SECURITY_BOT_TOKEN="security-test-token",
        TELEGRAM_SECURITY_ADMIN_IDS="9001",
        PUBLIC_BASE_URL="https://shop.example.test",
    )
    with app.app_context():
        admin = _user("admin", "ai-notice")
        db.session.commit()
        identity = (admin.id, admin.auth_version)
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = identity

    prompt = "Private weekly sales question must never appear in Telegram."
    monkeypatch.setattr(
        "app.ai.admin_tools.handle_admin_ai_query",
        lambda _prompt, *, user: {"ok": True, "answer": "Sales report ready.", "tools_used": []},
    )
    from unittest.mock import patch

    with patch("app.services.telegram_alerts.send_message", return_value=True) as send:
        response = client.post("/admin/ai/query", json={"prompt": prompt})
        page = client.get("/admin/ai")

    assert response.status_code == 200
    assert page.status_code == 200
    assert b"Recent AI activity" in page.data
    assert b"Admin AI query started" in page.data
    assert b"Admin AI query completed" in page.data
    assert send.call_count == 2
    assert all(prompt not in call.args[2] for call in send.call_args_list)
    with app.app_context():
        events = db.session.query(AuditEvent).filter(
            AuditEvent.actor_id == identity[0],
            AuditEvent.action.in_(("admin.ai.query.started", "admin.ai.query.completed")),
        ).all()
        assert len(events) == 2
        assert all(event.detail is None for event in events)


def test_ai_settings_urls_and_malformed_model_tool_calls_are_safe():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Verified response", "tool_calls": []}}],
                    "text": "Recognized test audio"}

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
    assert session.calls[0][1]["headers"]["Authorization"] == "Bearer mock-only"
    provider.transcribe(audio=b"audio", filename="voice.wav", content_type="audio/wav")
    assert session.calls[1][1]["headers"]["Authorization"] == "Bearer mock-only"
    assert "Content-Type" not in session.calls[1][1]["headers"]
    try:
        provider.generate(prompt="x", base_url="file:///etc/passwd")
    except Exception as error:
        assert "invalid" in str(error).lower()
    else:
        raise AssertionError("Unsafe provider URL was accepted")
    secure_provider = OpenAICompatibleProvider(
        api_key="mock-only", model="mock-model", base_url="http://ai.example.test/v1",
        session=session, require_https=True,
    )
    with pytest.raises(AIProviderError, match="HTTPS"):
        secure_provider.generate(messages=[{"role": "user", "content": "test"}])
    assert len(session.calls) == 2


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
    assert "data:image/jpeg;base64," in fake.calls[0][1]["json"]["messages"][1]["content"][1]["image_url"]["url"]
    assert provider.transcribe(audio=b"mock audio", filename="voice.webm", content_type="audio/webm") == "headphones under 2000"


def test_vision_provider_http_errors_become_safe_provider_errors():
    import requests

    class FailingSession:
        def post(self, *_args, **_kwargs):
            raise requests.exceptions.HTTPError("429 private provider detail")

    provider = OpenAICompatibleProvider(
        api_key="mock-only", model="vision-model",
        base_url="https://ai.example.test/v1", session=FailingSession(),
    )
    with pytest.raises(AIProviderError, match="AI provider request failed"):
        provider.describe_image(image_bytes=b"mock image", content_type="image/jpeg")


def test_private_local_vision_and_asr_can_use_internal_https_without_api_key():
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
                FakeResponse({"choices": [{"message": {"content": "blue backpack"}}]}),
                FakeResponse({"text": "backpack under 3000"}),
            ]
            self.calls = []

        def post(self, *args, **kwargs):
            self.calls.append(kwargs)
            return self.responses.pop(0)

    fake = FakeSession()
    provider = OpenAICompatibleProvider(
        api_key="", model="local-model", base_url="https://gpu.internal/v1",
        session=fake, allow_missing_key=True, require_https=True,
    )
    assert provider.describe_image(image_bytes=b"image") == "blue backpack"
    assert provider.transcribe(audio=b"audio", filename="voice.webm",
                               content_type="audio/webm") == "backpack under 3000"
    assert all("Authorization" not in call["headers"] for call in fake.calls)


def test_security_assistant_is_numeric_allowlist_scoped_and_read_only(app):
    from app.ai.security_tools import handle_security_ai_query
    with app.app_context():
        current_app.config.update(TELEGRAM_SECURITY_ADMIN_IDS="34567", AI_ENABLED=False)
        admin = User(email="security-ai-admin@example.test", role="admin")
        admin.set_password("password123")
        db.session.add(admin)
        db.session.flush()
        current_app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = f"34567:{admin.id}"
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
        admin = User(email="security-summary-admin@example.test", role="admin")
        admin.set_password("password123")
        db.session.add(admin)
        db.session.flush()
        current_app.config["TELEGRAM_SECURITY_ADMIN_USER_MAP"] = f"34567:{admin.id}"
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


def test_image_search_fails_closed_when_provider_errors(client, monkeypatch):
    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (8, 8), color="black").save(image_buffer, format="JPEG")
    image_buffer.seek(0)

    class FailingService:
        def __init__(self, _config):
            pass

        def describe_image(self, *_args, **_kwargs):
            raise AIProviderError("AI provider request failed.")

    monkeypatch.setattr("app.routes.ai.AIService", FailingService)
    response = client.post("/ai/image-search", data={
        "image": (image_buffer, "product.jpg", "image/jpeg")
    })

    assert response.status_code == 503
    assert response.get_json()["answer"] == (
        "Visual search is unavailable. Use the catalog search instead."
    )


def test_voice_search_fails_closed_without_local_transcription_config(client, app, monkeypatch):
    called = []

    class UnexpectedService:
        def __init__(self, _config):
            pass

        def transcribe(self, *_args, **_kwargs):
            called.append(True)
            raise AssertionError("Unconfigured voice transcription must not make a provider call.")

    monkeypatch.setattr("app.routes.ai.AIService", UnexpectedService)
    response = client.post("/ai/voice-search", data={
        "audio": (BytesIO(bytes.fromhex("1A45DFA3") + b"mock voice"), "voice.webm", "audio/webm")
    })

    assert response.status_code == 503
    assert "not configured" in response.get_json()["answer"].lower()
    assert called == []


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
    app.config.update(AI_ASR_BASE_URL="https://asr.example.test/v1", AI_ASR_MODEL="whisper-test")

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
        assert {"ai_request_windows", "ai_preferences", "support_conversations", "support_messages",
            "ai_external_consents", "ai_external_spend", "ai_user_memories", "ai_knowledge_chunks",
            "ai_external_call_notices", "ai_external_call_recipients",
            "ai_product_price_history", "ai_product_price_alerts", "ai_builder_jobs",
            "telegram_shopping_contexts", "telegram_security_alert_recipients"} <= tables
        columns = {item["name"] for item in inspect(db.engine).get_columns("ai_preferences")}
        assert {"last_cart_reminder_at", "last_recommendation_notification_at",
                "long_term_memory_enabled", "personalized_recommendations_enabled"} <= columns
        heads = db.session.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        assert heads == ["20261009_33"]

    downgraded = migration_app.test_cli_runner().invoke(args=["db", "downgrade", "20261007_30"])
    assert downgraded.exit_code == 0, downgraded.output
    with migration_app.app_context():
        inspector = inspect(db.engine)
        assert inspector.has_table("ai_builder_jobs")
        assert not inspector.has_table("telegram_shopping_contexts")
        assert not inspector.has_table("telegram_security_alert_recipients")
        assert inspector.has_table("ai_product_price_history")
        assert inspector.has_table("ai_product_price_alerts")
        columns = {item["name"] for item in inspector.get_columns("ai_preferences")}
        assert "personalized_recommendations_enabled" in columns
    upgraded = migration_app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert upgraded.exit_code == 0, upgraded.output
    with migration_app.app_context():
        heads = db.session.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        assert heads == ["20261009_33"]
