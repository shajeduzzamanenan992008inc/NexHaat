"""Regression guards for guest checkout and the auth-page chrome.

Guest cart/checkout must stay open to anonymous visitors (the storefront ships a
guest checkout form), while a signed-in staff account is refused. The registration
verification page must render with the same minimal auth chrome as the Admin
verification page.
"""

from pathlib import Path

from app.extensions import db
from app.models import SellerProfile, User


def csrf_off(client):
    client.application.config["WTF_CSRF_ENABLED"] = False


def test_guest_can_reach_the_cart_and_checkout(client):
    csrf_off(client)
    assert client.get("/cart").status_code == 200
    # An empty cart bounces checkout back to the cart page instead of to login.
    response = client.get("/checkout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")


def test_logged_in_staff_is_forbidden_from_the_cart(client, app):
    csrf_off(client)
    with app.app_context():
        seller = User(email="cart-staff@example.com", role="seller")
        seller.set_password("password123")
        seller.seller_profile = SellerProfile(
            store_name="Cart Store", contact_name="Owner", phone="01234567890",
            approval_status="approved",
        )
        db.session.add(seller)
        db.session.commit()
    client.post("/auth/login", data={"email": "cart-staff@example.com", "password": "password123"})
    assert client.get("/cart").status_code == 403
    assert client.post("/cart/update", data={}).status_code == 403


def test_auth_chrome_list_covers_every_otp_page():
    source = Path("app/templates/auth/base.html").read_text(encoding="utf-8")
    for endpoint in (
        "auth.login", "auth.admin_login", "auth.verify_admin_login",
        "auth.verify_registration", "auth.register", "auth.forgot_password",
        "auth.verify_reset_code", "auth.reset_password",
        "auth.seller_application", "auth.accept_invitation",
    ):
        assert endpoint in source, f"{endpoint} is missing from the auth chrome list"


def test_verify_registration_page_renders_the_auth_chrome(client, monkeypatch):
    csrf_off(client)
    monkeypatch.setattr("app.routes.auth.queue_registration_code", lambda *args, **kwargs: None)
    client.application.config.update(
        BREVO_API_KEY="test-key", MAIL_DEFAULT_SENDER="noreply@example.com"
    )
    response = client.post(
        "/auth/register",
        data={
            "email": "otp-chrome@example.com", "full_name": "Otp Chrome",
            "phone": "01234567890", "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/verify-registration")

    page = client.get("/auth/verify-registration").get_data(as_text=True)
    assert "auth-topbar" in page
    assert "auth-footer" in page
    assert '<header class="site-header">' not in page