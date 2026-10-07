from io import BytesIO
import zipfile

from app.extensions import db
from app.models import AIBuilderJob, User
from app.services.ai_external_notices import external_call_notices_ready


def _zip_project(files):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()


def _admin(app, client, suffix):
    with app.app_context():
        user = User(email=f"builder-{suffix}@example.test", role="admin")
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
        identity = (user.id, user.auth_version)
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = identity
    return identity[0]


def test_admin_project_analysis_is_transient_owner_scoped_and_deletable(client, app, monkeypatch):
    captured = {}
    source = _zip_project({
        "project/app.py": "def answer():\n    return 42\n",
        "project/.env": "TOKEN=must-not-be-submitted",
    })

    class LocalAnalysis:
        def __init__(self, _config):
            pass

        def respond(self, prompt, **kwargs):
            captured.update(prompt=prompt, kwargs=kwargs)
            return {"ok": True, "answer": "app.py defines a small answer function."}

    monkeypatch.setattr("app.routes.ai_builder.AIService", LocalAnalysis)
    owner_id = _admin(app, client, "owner")
    created = client.post(
        "/admin/ai-builder/jobs",
        data={
            "prompt": "Review this project for defects.",
            "allow_external_code": "false",
            "archive": (BytesIO(source), "project.zip"),
        },
        content_type="multipart/form-data",
    )

    assert created.status_code == 201, created.get_json()
    payload = created.get_json()["job"]
    assert payload["status"] == "completed"
    assert payload["inspected_file_count"] == 1
    assert payload["external_code_allowed"] is False
    assert payload["result"] == "app.py defines a small answer function."
    assert "def answer" in captured["kwargs"]["context"]["untrusted_project_source"]
    assert "must-not-be-submitted" not in captured["kwargs"]["context"]["untrusted_project_source"]
    assert len(captured["prompt"]) < 2000
    assert captured["kwargs"]["allow_external"] is False
    assert captured["kwargs"]["external_payload"] is None
    assert captured["kwargs"]["context"]["job_id"] == payload["id"]
    assert captured["kwargs"]["scope"] == "admin_ai"

    read = client.get(f"/admin/ai-builder/jobs/{payload['id']}")
    assert read.status_code == 200
    assert read.get_json()["job"]["result"] == payload["result"]

    with app.app_context():
        job = db.session.get(AIBuilderJob, payload["id"])
        assert job is not None and job.admin_user_id == owner_id
        assert job.source_sha256 and len(job.source_sha256) == 64
        assert not hasattr(job, "source_archive")
        other = User(email="builder-other@example.test", role="admin")
        other.set_password("test-password")
        db.session.add(other)
        db.session.commit()
        other_identity = (other.id, other.auth_version)
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = other_identity
    assert client.get(f"/admin/ai-builder/jobs/{payload['id']}").status_code == 404
    assert client.delete(f"/admin/ai-builder/jobs/{payload['id']}").status_code == 404

    with app.app_context():
        owner = db.session.get(User, owner_id)
        owner_version = owner.auth_version
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = owner_id, owner_version
    assert client.delete(f"/admin/ai-builder/jobs/{payload['id']}").status_code == 204
    with app.app_context():
        assert db.session.get(AIBuilderJob, payload["id"]) is None


def test_builder_ai_action_notices_exclude_prompt_and_project_source(client, app, monkeypatch):
    app.config.update(
        TELEGRAM_SECURITY_BOT_TOKEN="security-test-token",
        TELEGRAM_SECURITY_ADMIN_IDS="9001",
        PUBLIC_BASE_URL="https://shop.example.test",
    )

    class LocalAnalysis:
        def __init__(self, _config):
            pass

        def respond(self, _prompt, **_kwargs):
            return {"ok": True, "answer": "A bounded analysis result."}

    monkeypatch.setattr("app.routes.ai_builder.AIService", LocalAnalysis)
    _admin(app, client, "notice")
    project = _zip_project({"src/app.py": "SENSITIVE_SOURCE_LITERAL = 'private'\n"})
    from unittest.mock import patch

    with patch("app.services.telegram_alerts.send_message", return_value=True) as send:
        response = client.post(
            "/admin/ai-builder/jobs",
            data={
                "prompt": "SENSITIVE_PROMPT_LITERAL",
                "allow_external_code": "false",
                "archive": (BytesIO(project), "project.zip"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 201
    assert send.call_count == 2
    messages = [call.args[2] for call in send.call_args_list]
    assert any("project analysis started" in message.lower() for message in messages)
    assert any("project analysis completed" in message.lower() for message in messages)
    assert all("SENSITIVE_PROMPT_LITERAL" not in message for message in messages)
    assert all("SENSITIVE_SOURCE_LITERAL" not in message for message in messages)
    assert all("private" not in message for message in messages)
    assert all(
        call.args[3]["inline_keyboard"][0][0]["url"]
        == "https://shop.example.test/admin/ai"
        for call in send.call_args_list
    )


def test_builder_jobs_reject_non_admins_and_invalid_archives(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.routes.ai_builder.AIService",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("invalid input must not call AI")),
    )
    with app.app_context():
        customer = User(email="builder-customer@example.test", role="customer")
        customer.set_password("test-password")
        db.session.add(customer)
        db.session.commit()
        identity = (customer.id, customer.auth_version)
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = identity
    denied = client.post(
        "/admin/ai-builder/jobs",
        data={"prompt": "Analyze this.", "archive": (BytesIO(b"bad"), "bad.zip")},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 403

    _admin(app, client, "invalid")
    invalid = client.post(
        "/admin/ai-builder/jobs",
        data={"prompt": "Analyze this.", "archive": (BytesIO(b"not a zip"), "bad.zip")},
        content_type="multipart/form-data",
    )
    assert invalid.status_code == 415
    with app.app_context():
        assert AIBuilderJob.query.count() == 0


def test_builder_external_code_requires_admin_consent(client, app, monkeypatch):
    from app.ai.core.consent import set_external_consent

    called = []

    class LocalAnalysis:
        def __init__(self, _config):
            pass

        def respond(self, _prompt, **kwargs):
            called.append(kwargs)
            return {"ok": True, "answer": "Analysis complete."}

    monkeypatch.setattr("app.routes.ai_builder.AIService", LocalAnalysis)
    admin_id = _admin(app, client, "consent")
    project = _zip_project({"src/app.py": "def f(): return 1\n"})
    missing_consent = client.post(
        "/admin/ai-builder/jobs",
        data={
            "prompt": "Analyze source.",
            "allow_external_code": "true",
            "archive": (BytesIO(project), "project.zip"),
        },
        content_type="multipart/form-data",
    )
    assert missing_consent.status_code == 403
    assert called == []

    with app.app_context():
        admin = db.session.get(User, admin_id)
        assert set_external_consent(True, user=admin)
    approved = client.post(
        "/admin/ai-builder/jobs",
        data={
            "prompt": "Analyze source.",
            "allow_external_code": "true",
            "archive": (BytesIO(project), "project.zip"),
        },
        content_type="multipart/form-data",
    )
    assert approved.status_code == 201
    assert called[-1]["allow_external"] is True
    assert "def f()" in called[-1]["external_payload"]
    with app.app_context():
        job = db.session.get(AIBuilderJob, approved.get_json()["job"]["id"])
        assert job.external_code_allowed is True


def test_builder_external_call_gate_requires_telegram_configuration(app):
    with app.app_context():
        assert not external_call_notices_ready({
            "TELEGRAM_SECURITY_BOT_TOKEN": "",
            "TELEGRAM_SECURITY_ADMIN_IDS": "",
        })
