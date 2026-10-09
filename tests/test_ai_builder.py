from io import BytesIO
import zipfile

import pytest

from app.extensions import db
from app.models import (
    AIGuardianFinding, AIBuilderJob, AIBuilderPatch, AIBuilderProject,
    AIGuardianLesson, AIKnowledgeChunk, User,
)
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


def _create_saved_project(client, app, suffix="saved", *, project_type="python"):
    _admin(app, client, suffix)
    response = client.post(
        "/admin/ai-builder/projects",
        json={
            "name": f"Builder project {suffix}",
            "project_type": project_type,
            "description": "A private test project.",
            "persist": True,
            "external_code_consent": False,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["project"]


def test_saved_builder_project_is_opt_in_owner_scoped_and_exportable(client, app):
    _admin(app, client, "project-owner")
    transient = client.post(
        "/admin/ai-builder/projects",
        json={
            "name": "Transient starter",
            "project_type": "static",
            "description": "",
            "persist": False,
            "external_code_consent": False,
        },
    )
    assert transient.status_code == 200
    assert transient.get_json()["persisted"] is False
    with app.app_context():
        assert AIBuilderProject.query.count() == 0

    project = client.post(
        "/admin/ai-builder/projects",
        json={
            "name": "Saved starter",
            "project_type": "flask",
            "description": "A persisted starter.",
            "persist": True,
            "external_code_consent": False,
        },
    )
    assert project.status_code == 201
    project_data = project.get_json()["project"]
    assert project_data["files"]
    assert project_data["external_code_consent"] is False
    exported = client.get(f"/admin/ai-builder/projects/{project_data['id']}/export")
    assert exported.status_code == 200
    with zipfile.ZipFile(BytesIO(exported.data)) as archive:
        assert "app.py" in archive.namelist()
        assert "tests/test_app.py" in archive.namelist()

    with app.app_context():
        other = User(email="builder-project-other@example.test", role="admin")
        other.set_password("test-password")
        db.session.add(other)
        db.session.commit()
        other_identity = (other.id, other.auth_version)
    with client.session_transaction() as browser_session:
        browser_session["user_id"], browser_session["auth_version"] = other_identity
    assert client.get(f"/admin/ai-builder/projects/{project_data['id']}").status_code == 404
    assert client.delete(f"/admin/ai-builder/projects/{project_data['id']}").status_code == 404


def test_guardian_scans_are_signed_deduplicated_and_only_confirmed_risk_blocks(client, app):
    project = _create_saved_project(client, app, "guardian")
    from app.ai.builder.project_files import encode_project_files, project_digest, project_files_from_json

    with app.app_context():
        saved = db.session.get(AIBuilderProject, project["id"])
        files = project_files_from_json(saved.files_json)
        for item in files:
            if item["path"] == "main.py":
                item["content"] = "eval(input())\n"
        saved.files_json = encode_project_files(files)
        saved.source_sha256 = project_digest(files)
        db.session.commit()
    app.config.update(
        TELEGRAM_SECURITY_BOT_TOKEN="security-test-token",
        TELEGRAM_SECURITY_ADMIN_IDS="9001",
        PUBLIC_BASE_URL="https://shop.example.test",
    )
    from unittest.mock import patch as mock_patch

    with mock_patch("app.services.telegram_alerts.send_message", return_value=True) as send:
        first = client.post(
            f"/admin/ai-builder/projects/{project['id']}/scans",
            json={"trigger": "manual"},
        )
        assert first.status_code == 201, (
            first.get_json()["scan"]["status"] + ": " + first.get_json()["scan"]["result_summary"]
        )
        finding = first.get_json()["scan"]["findings"][0]
        assert finding["severity"] == "high"
        assert "eval(input())" not in finding["summary"]
        assert send.call_count == 1
        second = client.post(
            f"/admin/ai-builder/projects/{project['id']}/scans",
            json={"trigger": "manual"},
        )
        assert second.status_code == 201
        assert send.call_count == 1

    from app.routes.ai_builder_workspace import run_guardian_sweep

    with app.app_context():
        with app.test_request_context("/"):
            before = run_guardian_sweep(trigger="deployment", project_id=project["id"])
        assert before["blocking_findings"] == 0
        finding_row = db.session.get(AIGuardianFinding, finding["id"])
        assert finding_row is not None
        finding_row.confirmed = True
        finding_row.confirmation_note = "Confirmed through a reviewed reproducible risk case."
        db.session.commit()
        with app.test_request_context("/"):
            after = run_guardian_sweep(trigger="deployment", project_id=project["id"])
        assert after["blocking_findings"] == 1


def test_patch_candidate_needs_sandbox_pass_and_admin_approval_before_apply(
    client, app, monkeypatch
):
    project = _create_saved_project(client, app, "patch-lifecycle")
    created = client.post(
        f"/admin/ai-builder/projects/{project['id']}/patches",
        json={"changes": [{
            "path": "main.py",
            "content": '"""Python starter module."""\n\n\ndef main():\n    return "Updated"\n\n\nif __name__ == "__main__":\n    print(main())\n',
        }]},
    )
    assert created.status_code == 201
    patch_data = created.get_json()["patch"]
    assert patch_data["status"] == "draft"
    assert client.post(f"/admin/ai-builder/patches/{patch_data['id']}/approve").status_code == 409

    monkeypatch.setattr(
        "app.routes.ai_builder_workspace.run_project_tests",
        lambda *_args, **_kwargs: {"status": "passed", "summary": "Sandbox tests passed."},
    )
    tested = client.post(f"/admin/ai-builder/patches/{patch_data['id']}/test")
    assert tested.status_code == 200
    assert tested.get_json()["patch"]["test_status"] == "passed"
    approved = client.post(f"/admin/ai-builder/patches/{patch_data['id']}/approve")
    assert approved.status_code == 200
    assert approved.get_json()["patch"]["status"] == "approved"
    applied = client.post(f"/admin/ai-builder/patches/{patch_data['id']}/apply")
    assert applied.status_code == 200
    assert "Updated" in next(
        item["content"] for item in applied.get_json()["project"]["files"]
        if item["path"] == "main.py"
    )
    assert client.post(f"/admin/ai-builder/patches/{patch_data['id']}/apply").status_code == 409
    exported = client.get(f"/admin/ai-builder/patches/{patch_data['id']}/export")
    assert exported.status_code == 200
    with zipfile.ZipFile(BytesIO(exported.data)) as archive:
        assert "main.py" in archive.namelist()


def test_external_media_requires_admin_and_browser_session_consent(
    client, app, monkeypatch
):
    from app.ai.core.consent import set_external_consent

    admin_id = _admin(app, client, "media-consent")
    with app.app_context():
        admin = db.session.get(User, admin_id)
        assert set_external_consent(True, user=admin)
    captured = {}

    class LocalAnalysis:
        def __init__(self, _config):
            pass

        def respond(self, _prompt, **kwargs):
            captured.update(kwargs)
            return {"ok": True, "answer": "Document analysis complete."}

    monkeypatch.setattr("app.routes.ai_builder_workspace.AIService", LocalAnalysis)
    document = BytesIO()
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="urn:test"><w:body><w:p><w:r><w:t>Safe report text</w:t></w:r></w:p></w:body></w:document>',
        )
    document_data = document.getvalue()
    blocked = client.post(
        "/admin/ai-builder/inputs/analyze",
        data={
            "prompt": "Summarize this document.",
            "allow_external_media": "true",
            "attachment": (BytesIO(document_data), "report.docx"),
        },
        content_type="multipart/form-data",
    )
    assert blocked.status_code == 403
    assert captured == {}

    enabled = client.post("/admin/ai-builder/media-consent", json={"enabled": True})
    assert enabled.status_code == 200
    accepted = client.post(
        "/admin/ai-builder/inputs/analyze",
        data={
            "prompt": "Summarize this document.",
            "allow_external_media": "true",
            "attachment": (BytesIO(document_data), "report.docx"),
        },
        content_type="multipart/form-data",
    )
    assert accepted.status_code == 201
    assert accepted.get_json()["source_persisted"] is False
    assert captured["allow_external"] is True
    assert "Safe report text" in captured["external_payload"]
    with app.app_context():
        job = db.session.get(AIBuilderJob, accepted.get_json()["job"]["id"])
        assert job is not None
        assert job.result_text == "Document analysis complete."
        assert "Safe report text" not in (job.result_text or "")


def test_guardian_lesson_requires_passing_patch_and_explicit_review(
    client, app, monkeypatch
):
    project = _create_saved_project(client, app, "lesson")
    created = client.post(
        f"/admin/ai-builder/projects/{project['id']}/patches",
        json={"changes": [{"path": "main.py", "content": "def main():\n    return 1\n"}]},
    )
    patch_id = created.get_json()["patch"]["id"]
    assert client.post(f"/admin/ai-builder/patches/{patch_id}/lessons", json={
        "title": "Reviewable tests", "content": "Keep input validation in a focused helper.",
    }).status_code == 409
    monkeypatch.setattr(
        "app.routes.ai_builder_workspace.run_project_tests",
        lambda *_args, **_kwargs: {"status": "passed", "summary": "Sandbox tests passed."},
    )
    assert client.post(f"/admin/ai-builder/patches/{patch_id}/test").status_code == 200
    proposed = client.post(
        f"/admin/ai-builder/patches/{patch_id}/lessons",
        json={"title": "Reviewable tests", "content": "Keep input validation in a focused helper."},
    )
    assert proposed.status_code == 201
    lesson_id = proposed.get_json()["lesson"]["id"]
    with app.app_context():
        assert AIKnowledgeChunk.query.count() == 0
    monkeypatch.setattr(
        "app.routes.ai_builder_workspace.embed_text",
        lambda _text: [1.0] + [0.0] * 1023,
    )
    approved = client.post(
        f"/admin/ai-builder/lessons/{lesson_id}/review",
        json={"decision": "approve"},
    )
    assert approved.status_code == 200
    with app.app_context():
        lesson = db.session.get(AIGuardianLesson, lesson_id)
        chunk = AIKnowledgeChunk.query.one()
        assert lesson.status == "approved"
        assert chunk.scope == "admin"
        assert chunk.source == f"guardian-lesson-{lesson_id}"
    removed = client.delete(f"/admin/ai-builder/projects/{project['id']}")
    assert removed.status_code == 204
    with app.app_context():
        assert AIKnowledgeChunk.query.count() == 0


def test_invalid_guardian_queue_signature_fails_closed(app, client):
    project = _create_saved_project(client, app, "bad-signature")
    from app.ai.builder.guardian import create_scan, process_scan

    with app.app_context():
        saved = db.session.get(AIBuilderProject, project["id"])
        scan = create_scan(saved, trigger="manual", actor_id=saved.admin_user_id)
        scan.queue_signature = "0" * 64
        db.session.commit()
        scan, findings = process_scan(scan)
        assert scan.status == "failed"
        assert "signature validation failed" in scan.result_summary.lower()
        assert findings == []


def test_sandbox_runner_requires_available_docker_and_starter_has_tests(monkeypatch):
    from app.ai.builder.project_files import starter_project_files
    from app.ai.builder.sandbox import SandboxUnavailable, run_project_tests

    static_files = starter_project_files("static", "Browser starter")
    assert any(item["path"] == "tests/test_static_project.py" for item in static_files)
    monkeypatch.setattr("app.ai.builder.sandbox.shutil.which", lambda _name: None)
    with pytest.raises(SandboxUnavailable, match="Docker is not installed"):
        run_project_tests(
            starter_project_files("python", "Isolated test"),
            image="sha256:" + "a" * 64,
        )


def test_hidden_builder_benchmark_uses_local_only_and_keeps_tests_hidden():
    from app.ai.builder.benchmark import run_builder_benchmark

    captured = {}

    class LocalModel:
        local_available = True

        def respond(self, prompt, **kwargs):
            captured.update(prompt=prompt, kwargs=kwargs)
            return {
                "ok": True,
                "answer": (
                    "from decimal import Decimal, ROUND_HALF_UP\n\n"
                    "def normalize_discounted_total(values):\n"
                    "    total = Decimal('0')\n"
                    "    for value in values:\n"
                    "        if isinstance(value, bool):\n"
                    "            raise ValueError\n"
                    "        amount = Decimal(str(value))\n"
                    "        if not amount.is_finite() or amount < 0:\n"
                    "            raise ValueError\n"
                    "        total += amount\n"
                    "    return format(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), 'f')\n"
                ),
            }

    def sandbox(files, **kwargs):
        captured["files"] = files
        captured["sandbox"] = kwargs
        return {"status": "passed", "passed_count": 10, "failed_count": 0}

    result = run_builder_benchmark(
        service=LocalModel(),
        image="sha256:" + "b" * 64,
        runner=sandbox,
    )
    assert result == {"passed": 10, "total": 10, "score_percent": 100, "status": "passed"}
    assert captured["kwargs"]["allow_external"] is False
    assert "negative values" in captured["prompt"]
    assert "def test_empty_input" not in captured["prompt"]
    assert any(item["path"] == "tests/test_challenge.py" for item in captured["files"])
    assert captured["sandbox"]["image"] == "sha256:" + "b" * 64
