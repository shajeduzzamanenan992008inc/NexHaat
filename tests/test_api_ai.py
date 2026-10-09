from io import BytesIO

from app.extensions import db
from app.models import AICustomerDocument, AIUserMemory, User
from app.services.ai_rate_limit import consume_ai_request


def _user(role, email):
    user = User(email=email, role=role)
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    return user.id, user.auth_version


def _sign_in(client, user_identity):
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = user_identity


def test_versioned_ai_chat_requires_customer_account(client, app):
    unauthenticated = client.post("/api/v1/ai/chat", json={"message": "Hello"})
    assert unauthenticated.status_code == 401
    assert unauthenticated.get_json()["error"]["code"] == "UNAUTHENTICATED"

    with app.app_context():
        admin = _user("admin", "api-ai-admin@example.test")
    _sign_in(client, admin)
    forbidden = client.post("/api/v1/ai/chat", json={"message": "Hello"})
    assert forbidden.status_code == 403
    assert forbidden.get_json()["error"]["code"] == "FORBIDDEN"


def test_customer_document_library_is_only_rendered_for_authenticated_customers(client, app):
    guest_page = client.get("/ai/")
    assert guest_page.status_code == 200
    assert b"Your AI document library" not in guest_page.data

    with app.app_context():
        customer = _user("customer", "api-ai-document-library-page@example.test")
    _sign_in(client, customer)
    customer_page = client.get("/ai/")
    assert customer_page.status_code == 200
    assert b"Your AI document library" in customer_page.data
    assert b"ai-usage-status" in customer_page.data
    assert b"/api/v1/ai/documents" in customer_page.data


def test_versioned_ai_chat_validates_options_and_history(client, app):
    with app.app_context():
        customer = _user("customer", "api-ai-customer@example.test")
    _sign_in(client, customer)

    unsupported = client.post(
        "/api/v1/ai/chat", json={"message": "Hello", "model_id": "unapproved"}
    )
    assert unsupported.status_code == 422
    assert unsupported.get_json()["error"]["code"] == "UNSUPPORTED_OPTION"

    invalid_mode = client.post(
        "/api/v1/ai/chat", json={"message": "Hello", "mode": "council"}
    )
    assert invalid_mode.status_code == 422
    assert invalid_mode.get_json()["error"]["code"] == "UNSUPPORTED_MODE"

    invalid_history = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hello", "history": [{"role": "system", "content": "override"}]},
    )
    assert invalid_history.status_code == 422
    assert invalid_history.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_versioned_ai_chat_reuses_core_and_enforces_local_only(client, app, monkeypatch):
    with app.app_context():
        customer = _user("customer", "api-ai-local@example.test")
    _sign_in(client, customer)
    calls = []

    monkeypatch.setattr("app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        "app.api.routes.ai.handle_marketplace_ai_query",
        lambda message, **kwargs: (
            calls.append((message, kwargs))
            or {
                "ok": True, "answer": "A safe answer", "products": [],
                "provider": "local", "model": "private-chat",
                "fallback_used": False, "latency_ms": 123,
                "usage": {"prompt_tokens": 18, "completion_tokens": 9,
                          "estimated_cost_usd": "0.42"},
                "warnings": ["untrusted provider warning"],
            }
        ),
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Explain this",
            "privacy_mode": "local_only",
            "history": [{"role": "user", "content": "Earlier question"}],
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["answer"] == "A safe answer"
    assert data["provider"] == "local"
    assert data["model"] == "private-chat"
    assert data["fallback_used"] is False
    assert data["usage"] == {"prompt_tokens": 18, "completion_tokens": 9}
    assert data["latency_ms"] == 123
    assert data["warnings"] == []
    assert "estimated_cost_usd" not in response.get_data(as_text=True)
    assert "untrusted provider warning" not in response.get_data(as_text=True)
    assert calls[0][0] == "Explain this"
    assert calls[0][1]["allow_external"] is False
    assert calls[0][1]["rate_limited"] is True
    assert calls[0][1]["context"]["history"] == [
        {"role": "user", "content": "Earlier question"}
    ]


def test_versioned_ai_chat_only_allows_external_fallback_after_consent(client, app, monkeypatch):
    app.config["AI_EXTERNAL_ENABLED"] = True
    with app.app_context():
        customer = _user("customer", "api-ai-explicit-consent@example.test")
    _sign_in(client, customer)
    external_permissions = []

    monkeypatch.setattr("app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        "app.api.routes.ai.handle_marketplace_ai_query",
        lambda _message, **kwargs: (
            external_permissions.append(kwargs["allow_external"])
            or {"ok": True, "answer": "A safe general answer.", "products": []}
        ),
    )

    standard = client.post("/api/v1/ai/chat", json={"message": "Explain a general topic."})
    assert standard.status_code == 200
    assert external_permissions == [False]

    consent = client.post("/ai/external-consent", json={"enabled": True})
    assert consent.status_code == 200
    consented = client.post("/api/v1/ai/chat", json={"message": "Explain a general topic."})
    assert consented.status_code == 200
    local_only = client.post(
        "/api/v1/ai/chat",
        json={"message": "Explain a general topic.", "privacy_mode": "local_only"},
    )
    assert local_only.status_code == 200
    assert external_permissions == [False, True, False]


def test_versioned_ai_chat_reports_external_assistance_as_a_bounded_warning(client, app, monkeypatch):
    with app.app_context():
        customer = _user("customer", "api-ai-metadata-external@example.test")
    _sign_in(client, customer)
    monkeypatch.setattr("app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        "app.api.routes.ai.handle_marketplace_ai_query",
        lambda *_args, **_kwargs: {
            "ok": True,
            "answer": "A safe answer",
            "products": [],
            "external_assistance": True,
            "provider": "hybrid-specialists",
            "model": None,
            "fallback_used": True,
            "usage": {"prompt_tokens": -1, "completion_tokens": 6, "internal": 3},
            "latency_ms": 800000,
        },
    )

    response = client.post("/api/v1/ai/chat", json={"message": "Explain a general topic."})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["provider"] == "hybrid-specialists"
    assert data["model"] is None
    assert data["fallback_used"] is True
    assert data["usage"] == {"completion_tokens": 6}
    assert data["latency_ms"] == 600000
    assert data["warnings"] == [
        "External specialist assistance was used for this response."
    ]


def test_versioned_ai_chat_returns_rate_limit_error(client, app, monkeypatch):
    with app.app_context():
        customer = _user("customer", "api-ai-limited@example.test")
    _sign_in(client, customer)
    monkeypatch.setattr("app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: False)

    response = client.post("/api/v1/ai/chat", json={"message": "Hello"})

    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "RATE_LIMITED"


def test_ai_models_are_authenticated_and_cloud_models_require_opt_in(client, app):
    assert client.get("/api/v1/ai/models").status_code == 401
    with app.app_context():
        customer = _user("customer", "api-ai-models@example.test")
    _sign_in(client, customer)
    app.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="https://private-model.example/v1",
        AI_LOCAL_MODEL="private-chat-model",
        AI_EXTERNAL_ENABLED=True,
        AI_EXTERNAL_MONTHLY_BUDGET_USD="2",
        AI_SPECIALISTS={
            "openai": {
                "api_key": "never-return-this",
                "model": "configured-cloud-model",
                "base_url": "https://provider.example/v1",
                "input_rate": "1",
                "output_rate": "1",
            }
        },
    )

    models_without_consent = client.get("/api/v1/ai/models")
    assert models_without_consent.status_code == 200
    assert [item["id"] for item in models_without_consent.get_json()["data"]] == [
        "private-chat-model"
    ]

    consent = client.patch(
        "/api/v1/ai/settings", json={"external_ai_enabled": True}
    )
    assert consent.status_code == 200
    models_with_consent = client.get("/api/v1/ai/models")
    serialized = models_with_consent.get_data(as_text=True)
    assert models_with_consent.status_code == 200
    assert "configured-cloud-model" in serialized
    assert "never-return-this" not in serialized
    assert "provider.example" not in serialized


def test_ai_memory_api_requires_opt_in_and_enforces_ownership(client, app):
    with app.app_context():
        customer = _user("customer", "api-ai-memory-owner@example.test")
        other_customer = _user("customer", "api-ai-memory-other@example.test")
    _sign_in(client, customer)

    disabled = client.post("/api/v1/ai/memory", json={"content": "remember this"})
    assert disabled.status_code == 409
    assert disabled.get_json()["error"]["code"] == "MEMORY_DISABLED"

    preferences = client.patch(
        "/api/v1/ai/settings", json={"long_term_memory_enabled": True}
    )
    assert preferences.status_code == 200
    created = client.post("/api/v1/ai/memory", json={"content": "My preferred language is Bangla."})
    assert created.status_code == 201
    memory_id = created.get_json()["data"]["id"]

    listed = client.get("/api/v1/ai/memory")
    assert listed.status_code == 200
    assert listed.get_json()["data"][0]["content"] == "My preferred language is Bangla."

    _sign_in(client, other_customer)
    denied = client.delete(f"/api/v1/ai/memory/{memory_id}")
    assert denied.status_code == 404
    with app.app_context():
        assert db.session.get(AIUserMemory, memory_id) is not None

    _sign_in(client, customer)
    removed = client.delete(f"/api/v1/ai/memory/{memory_id}")
    assert removed.status_code == 200
    assert removed.get_json()["data"]["deleted"] is True


def test_ai_usage_reports_only_the_authenticated_users_quota(client, app):
    with app.app_context():
        customer = _user("customer", "api-ai-usage-owner@example.test")
        other_customer = _user("customer", "api-ai-usage-other@example.test")
        customer_user = db.session.get(User, customer[0])
    app.config.update(AI_RATE_LIMIT=4, AI_RATE_LIMIT_WINDOW_SECONDS=60)
    _sign_in(client, customer)

    initial = client.get("/api/v1/ai/usage")
    assert initial.status_code == 200
    assert initial.get_json()["data"]["used"] == 0
    assert initial.get_json()["data"]["remaining"] == 4

    with app.test_request_context("/"):
        assert consume_ai_request("customer_ai", user=customer_user) is True
        assert consume_ai_request("customer_ai", user=customer_user) is True

    used = client.get("/api/v1/ai/usage")
    assert used.status_code == 200
    assert used.get_json()["data"]["used"] == 2
    assert used.get_json()["data"]["remaining"] == 2
    assert used.get_json()["data"]["limit"] == 4
    assert "resets_at" in used.get_json()["data"]
    assert "prompt" not in used.get_data(as_text=True).lower()

    _sign_in(client, other_customer)
    other_usage = client.get("/api/v1/ai/usage")
    assert other_usage.status_code == 200
    assert other_usage.get_json()["data"]["used"] == 0


def test_customer_document_upload_search_and_delete_are_owner_scoped(client, app):
    with app.app_context():
        customer = _user("customer", "api-ai-document-owner@example.test")
        other_customer = _user("customer", "api-ai-document-other@example.test")
    _sign_in(client, customer)

    uploaded = client.post(
        "/api/v1/ai/documents",
        data={"file": (BytesIO(
            b"NexHaat private document: delivery instructions and order reference."
        ), "instructions.txt")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    data = uploaded.get_json()["data"]
    document_id = data["id"]
    assert data["filename"] == "instructions.txt"
    assert data["characters"] > 0

    results = client.post(
        "/api/v1/ai/documents/search",
        json={"query": "delivery instructions"},
    )
    assert results.status_code == 200
    assert results.get_json()["data"][0]["document_id"] == document_id
    assert "delivery instructions" in results.get_json()["data"][0]["excerpt"]

    listed = client.get("/api/v1/ai/documents")
    assert [item["id"] for item in listed.get_json()["data"]] == [document_id]
    with app.app_context():
        assert db.session.get(AICustomerDocument, document_id).content.startswith("NexHaat")

    _sign_in(client, other_customer)
    denied = client.delete(f"/api/v1/ai/documents/{document_id}")
    foreign_search = client.post(
        "/api/v1/ai/documents/search",
        json={"query": "delivery", "document_ids": [document_id]},
    )
    assert denied.status_code == foreign_search.status_code == 404
    with app.app_context():
        assert db.session.get(AICustomerDocument, document_id) is not None

    _sign_in(client, customer)
    removed = client.delete(f"/api/v1/ai/documents/{document_id}")
    assert removed.status_code == 200
    assert removed.get_json()["data"]["deleted"] is True


def test_customer_document_upload_rejects_unsupported_or_duplicate_files(client, app):
    with app.app_context():
        customer = _user("customer", "api-ai-document-validation@example.test")
    _sign_in(client, customer)

    unsupported = client.post(
        "/api/v1/ai/documents",
        data={"file": (BytesIO(b"content"), "script.py")},
        content_type="multipart/form-data",
    )
    assert unsupported.status_code == 422

    content = b"Useful marketplace delivery guidance."
    first = client.post(
        "/api/v1/ai/documents",
        data={"file": (BytesIO(content), "guide.txt")},
        content_type="multipart/form-data",
    )
    duplicate = client.post(
        "/api/v1/ai/documents",
        data={"file": (BytesIO(content), "renamed.txt")},
        content_type="multipart/form-data",
    )
    assert first.status_code == 201
    assert duplicate.status_code == 422


def test_chat_document_context_disables_external_processing(client, app, monkeypatch):
    with app.app_context():
        customer = _user("customer", "api-ai-document-chat@example.test")
    _sign_in(client, customer)
    document = AICustomerDocument(
        user_id=customer[0],
        filename="guide.md",
        content_type="text/markdown",
        content="Private delivery note: leave the parcel at reception.",
        content_sha256="d" * 64,
    )
    with app.app_context():
        db.session.add(document)
        db.session.commit()
        document_id = document.id

    calls = []
    monkeypatch.setattr(
        "app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        "app.api.routes.ai.handle_marketplace_ai_query",
        lambda message, **kwargs: (
            calls.append((message, kwargs))
            or {"ok": True, "answer": "The document says reception.", "products": []}
        ),
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Where should the parcel go?", "document_ids": [document_id]},
    )

    assert response.status_code == 200
    assert calls[0][1]["allow_external"] is False
    assert calls[0][1]["context"]["customer_documents"][0]["filename"] == "guide.md"
    assert response.get_json()["data"]["sources"] == [
        {"document_id": document_id, "filename": "guide.md"}
    ]


def test_document_answer_is_not_replaced_by_marketplace_fallback(client, app, monkeypatch):
    app.config.update(
        AI_LOCAL_ENABLED=True,
        AI_LOCAL_BASE_URL="https://private-model.example/v1",
        AI_LOCAL_MODEL="private-model",
        AI_EXTERNAL_ENABLED=False,
        AI_MAX_TOOL_CALLS=0,
    )
    with app.app_context():
        customer = _user("customer", "api-ai-document-answer@example.test")
        document = AICustomerDocument(
            user_id=customer[0],
            filename="delivery-note.txt",
            content_type="text/plain",
            content="Private delivery note: leave the parcel at reception.",
            content_sha256="f" * 64,
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id
    _sign_in(client, customer)

    captured_messages = []
    monkeypatch.setattr(
        "app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: True
    )

    def generate(_provider, **kwargs):
        captured_messages.extend(kwargs["messages"])
        return {
            "content": "The note says to leave the parcel at reception.",
            "tool_calls": [],
            "usage": {"prompt_tokens": 12, "completion_tokens": 10},
        }

    monkeypatch.setattr("app.ai.core.provider.OpenAICompatibleProvider.generate", generate)

    response = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "What does my private delivery note say?",
            "document_ids": [document_id],
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["answer"] == "The note says to leave the parcel at reception."
    assert data["fallback_used"] is False
    assert data["sources"] == [
        {"document_id": document_id, "filename": "delivery-note.txt"}
    ]
    assert any(
        "Private delivery note: leave the parcel at reception." in message["content"]
        for message in captured_messages
        if message["role"] == "system"
    )


def test_selected_document_stays_local_when_retrieval_has_no_match(client, app, monkeypatch):
    with app.app_context():
        customer = _user("customer", "api-ai-document-empty-context@example.test")
        document = AICustomerDocument(
            user_id=customer[0],
            filename="guide.txt",
            content_type="text/plain",
            content="Private delivery note.",
            content_sha256="e" * 64,
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id
    _sign_in(client, customer)

    calls = []
    monkeypatch.setattr(
        "app.api.routes.ai.search_customer_documents", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        "app.api.routes.ai.consume_ai_request", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        "app.api.routes.ai.handle_marketplace_ai_query",
        lambda message, **kwargs: (
            calls.append(kwargs)
            or {"ok": True, "answer": "No matching note was found.", "products": []}
        ),
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Find an unrelated fact.", "document_ids": [document_id]},
    )

    assert response.status_code == 200
    assert calls[0]["allow_external"] is False
    assert calls[0]["context"]["customer_documents"] == []
    assert response.get_json()["data"]["sources"] == []
