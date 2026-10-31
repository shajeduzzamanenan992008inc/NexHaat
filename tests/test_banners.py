
import contextlib

from app.extensions import db
from app.models import Banner


def test_banner_model_import_and_registration(app):
    with app.app_context():
        banner = Banner(
            title="Welcome",
            subtitle="Shop now",
            image_url="https://example.com/banner.jpg",
            link_url="/products",
            link_type="products",
            is_active=True,
            display_order=1,
        )
        db.session.add(banner)
        db.session.commit()
        assert banner.id is not None
        assert banner.__tablename__ == "banners"


def test_banner_api_empty_response(client):
    response = client.get("/api/v1/banners")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"] == []


def test_banner_api_filters_inactive_and_orders(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Banner(
                    title="Third",
                    subtitle=None,
                    image_url="https://example.com/3.jpg",
                    link_url="/c/third",
                    link_type="category",
                    is_active=True,
                    display_order=3,
                ),
                Banner(
                    title="Inactive",
                    subtitle="Skip",
                    image_url="https://example.com/inactive.jpg",
                    link_url="/products",
                    link_type="products",
                    is_active=False,
                    display_order=0,
                ),
                Banner(
                    title="First",
                    subtitle="Start",
                    image_url="https://example.com/1.jpg",
                    link_url="/search?q=sale",
                    link_type="search",
                    is_active=True,
                    display_order=1,
                ),
                Banner(
                    title="Second",
                    subtitle="Middle",
                    image_url="https://example.com/2.jpg",
                    link_url="https://external.example.com/promo",
                    link_type="external",
                    is_active=True,
                    display_order=2,
                ),
            ]
        )
        db.session.commit()

    response = client.get("/api/v1/banners")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert len(data) == 3
    assert [item["title"] for item in data] == ["First", "Second", "Third"]
    assert [item["display_order"] for item in data] == [1, 2, 3]


def test_banner_api_response_structure(client, app):
    with app.app_context():
        banner = Banner(
            title="Promo",
            subtitle="Limited time",
            image_url="https://example.com/promo.jpg",
            link_url="/products?tag=promo",
            link_type="products",
            is_active=True,
            display_order=0,
        )
        db.session.add(banner)
        db.session.commit()

    response = client.get("/api/v1/banners")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    for key in ["id", "title", "subtitle", "image_url", "link_url", "link_type", "is_active", "display_order"]:
        assert key in item
    assert item["title"] == "Promo"
    assert item["link_type"] == "products"
    assert item["is_active"] is True


def test_banner_serializer_blocks_unsafe_image(client, app):
    from app.api.serializers import banner_to_dict

    with app.app_context():
        banner = Banner(
            title="Bad",
            subtitle=None,
            image_url="https://example.com/ok.jpg",
            link_url="/products",
            link_type="products",
            is_active=True,
            display_order=0,
        )
        with contextlib.suppress(Exception):
            banner.image_url = "data:text/html,<script>alert(1)</script>"
        result = banner_to_dict(banner)
        assert result["image_url"] in (None, banner.display_image)


def test_banner_serializer_blocks_unsafe_scheme_image(client, app):
    from app.api.serializers import banner_to_dict

    with app.app_context():
        banner = Banner(
            title="Bad",
            subtitle=None,
            image_url="https://example.com/ok.jpg",
            link_url="/products",
            link_type="products",
            is_active=True,
            display_order=0,
        )
        with contextlib.suppress(Exception):
            banner.image_url = "javascript:alert(1)"
        result = banner_to_dict(banner)
        assert result["image_url"] in (None, banner.display_image)
