def test_app_module_exposes_wsgi_entry():
    from app import app

    assert app is not None
    assert hasattr(app, "url_map")
