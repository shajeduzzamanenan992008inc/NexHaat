"""Versioned, authenticated AI endpoints backed by NexHaat's shared Core."""

import secrets

from flask import Blueprint, current_app, request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from ...ai.core.consent import external_consent_enabled, set_external_consent
from ...ai.core.customer_documents import (
    MAX_DOCUMENT_BYTES,
    MAX_DOCUMENTS_PER_CUSTOMER,
    CustomerDocumentError,
    ingest_customer_document,
    search_customer_documents,
)
from ...ai.core.external_budget import decimal_setting
from ...ai.core.guardrails import sanitize_ai_response, sanitize_history
from ...ai.core.permissions import (
    AI_SCOPE_CUSTOMER,
)
from ...ai.core.provider import AIService
from ...ai.marketplace_tools import handle_marketplace_ai_query
from ...extensions import db
from ...models import AICustomerDocument, AIPreferences, AIUserMemory
from ...security import current_session_user
from ...services.ai_rate_limit import consume_ai_request, get_ai_request_usage
from ..errors import ApiError
from ..responses import success_response


ai_api = Blueprint("api_ai", __name__, url_prefix="/ai")
_AI_ROLES = {"customer", "seller", "rider", "admin", "super_admin"}
_CUSTOMER_ONLY_SETTINGS = {
    "long_term_memory_enabled",
    "personalized_recommendations_enabled",
    "smart_notifications_enabled",
}


def _require_user(*, customer_only=False):
    user = current_session_user()
    if user is None:
        raise ApiError("Sign in to use the AI API.", "UNAUTHENTICATED", 401)
    if user.role not in _AI_ROLES or (customer_only and user.role != "customer"):
        raise ApiError(
            "This AI feature is not available to this account.",
            "FORBIDDEN",
            403,
        )
    return user


def _raise_ai_error(message, code, status, *, retryable=False):
    raise ApiError(
        message,
        code,
        status,
        details={"request_id": secrets.token_hex(16), "retryable": retryable},
    )


def _cloud_gate_open(user):
    config = current_app.config
    return bool(
        config.get("AI_EXTERNAL_ENABLED")
        and decimal_setting(config.get("AI_EXTERNAL_MONTHLY_BUDGET_USD")) > 0
        and external_consent_enabled(user=user)
    )


def _external_models(user):
    if not _cloud_gate_open(user):
        return []
    service = AIService(current_app.config)
    return [
        {
            "id": spec["model"],
            "provider": name,
            "local": False,
            "capabilities": ["text"],
        }
        for name, spec in service._external_fallback_specs()
    ]


def _validate_document_ownership(user, document_ids):
    if document_ids is None:
        return
    owned = set(db.session.scalars(
        select(AICustomerDocument.id).where(
            AICustomerDocument.user_id == user.id,
            AICustomerDocument.id.in_(document_ids),
        )
    ).all())
    if owned != set(document_ids):
        _raise_ai_error("One or more documents were not found.", "NOT_FOUND", 404)


def _public_chat_metadata(result):
    """Expose only bounded, non-secret provider diagnostics in the customer API."""
    provider = result.get("provider")
    model = result.get("model")
    usage = result.get("usage")
    latency_ms = result.get("latency_ms")
    return {
        "provider": provider[:80] if isinstance(provider, str) else None,
        "model": model[:160] if isinstance(model, str) else None,
        "fallback_used": result.get("fallback_used") is True,
        "usage": {
            key: value
            for key, value in usage.items()
            if key in {"prompt_tokens", "completion_tokens"}
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
        } if isinstance(usage, dict) else {},
        "latency_ms": (
            min(latency_ms, 600_000)
            if isinstance(latency_ms, int) and not isinstance(latency_ms, bool)
            and latency_ms >= 0 else None
        ),
        "warnings": (
            ["External specialist assistance was used for this response."]
            if result.get("external_assistance") is True else []
        ),
    }


@ai_api.get("/providers")
def providers():
    """Return a redacted provider readiness summary for the signed-in caller."""
    user = _require_user()
    service = AIService(current_app.config)
    external = _external_models(user)
    items = []
    if service.local_enabled:
        items.append({
            "id": "local",
            "configured": service.local_available,
            "available_for_request": service.local_available,
        })
    external_names = sorted({item["provider"] for item in external})
    items.extend(
        {
            "id": name,
            "configured": True,
            "available_for_request": True,
        }
        for name in external_names
    )
    return success_response({
        "providers": items,
        "external_consent": external_consent_enabled(user=user),
        "external_gate_open": bool(external),
    })


@ai_api.get("/models")
def models():
    """List configured model IDs without exposing credentials, URLs, or prices."""
    user = _require_user()
    service = AIService(current_app.config)
    items = []
    if service.local_available:
        items.append({
            "id": service.local_model,
            "provider": "local",
            "local": True,
            "capabilities": ["text"],
        })
    items.extend(_external_models(user))
    return success_response(items)


@ai_api.get("/health")
def health():
    """Probe only the configured local service; never ping cloud providers."""
    _require_user()
    result = AIService(current_app.config).health_check()
    data = {
        "status": result.get("status", "unavailable"),
        "message": result.get("message", "AI service is unavailable."),
        "providers": result.get("providers", {}),
    }
    if not result.get("ok"):
        _raise_ai_error(data["message"], "AI_UNAVAILABLE", 503, retryable=True)
    return success_response(data)


@ai_api.get("/usage")
def usage():
    """Return only this customer's current request quota; never expose prompts or spend."""
    user = _require_user(customer_only=True)
    return success_response(get_ai_request_usage(AI_SCOPE_CUSTOMER, user=user))


@ai_api.get("/documents")
def list_documents():
    user = _require_user(customer_only=True)
    rows = db.session.scalars(
        select(AICustomerDocument)
        .where(AICustomerDocument.user_id == user.id)
        .order_by(AICustomerDocument.created_at.desc(), AICustomerDocument.id.desc())
        .limit(MAX_DOCUMENTS_PER_CUSTOMER)
    ).all()
    return success_response([{
        "id": row.id,
        "filename": row.filename,
        "content_type": row.content_type,
        "characters": len(row.content),
        "created_at": row.created_at.isoformat(),
    } for row in rows])


@ai_api.post("/documents")
def upload_document():
    user = _require_user(customer_only=True)
    if request.content_length and request.content_length > MAX_DOCUMENT_BYTES + 64 * 1024:
        _raise_ai_error("Documents must be no larger than 2 MB.", "UPLOAD_TOO_LARGE", 413)
    upload = request.files.get("file")
    if upload is None:
        _raise_ai_error("Choose a PDF, TXT, or Markdown document.", "VALIDATION_ERROR", 422)
    try:
        data = upload.stream.read(MAX_DOCUMENT_BYTES + 1)
        document = ingest_customer_document(user, upload.filename or "", data)
    except CustomerDocumentError as error:
        status = 413 if "2 MB" in str(error) else 422
        _raise_ai_error(str(error), "DOCUMENT_REJECTED", status)
    except SQLAlchemyError as error:
        db.session.rollback()
        raise ApiError(
            "The document could not be saved.",
            "AI_UNAVAILABLE",
            503,
            details={"request_id": secrets.token_hex(16), "retryable": True},
        ) from error
    return success_response({
        "id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "characters": len(document.content),
        "created_at": document.created_at.isoformat(),
    }, message="Document added to your private AI library.", status=201)


@ai_api.delete("/documents/<int:document_id>")
def delete_document(document_id):
    user = _require_user(customer_only=True)
    document = db.session.scalar(select(AICustomerDocument).where(
        AICustomerDocument.id == document_id,
        AICustomerDocument.user_id == user.id,
    ))
    if document is None:
        _raise_ai_error("Document not found.", "NOT_FOUND", 404)
    try:
        db.session.delete(document)
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise ApiError(
            "The document could not be deleted.",
            "AI_UNAVAILABLE",
            503,
            details={"request_id": secrets.token_hex(16), "retryable": True},
        ) from error
    return success_response({"id": document_id, "deleted": True})


@ai_api.post("/documents/search")
def search_documents():
    user = _require_user(customer_only=True)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) - {"query", "document_ids"}:
        _raise_ai_error("Send a document search query and optional document IDs.", "VALIDATION_ERROR", 422)
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        _raise_ai_error("Send a search query under 1,000 characters.", "VALIDATION_ERROR", 422)
    document_ids = payload.get("document_ids")
    if document_ids is not None and (
        not isinstance(document_ids, list)
        or not document_ids
        or len(document_ids) > 3
        or any(type(document_id) is not int or document_id < 1 for document_id in document_ids)
        or len(set(document_ids)) != len(document_ids)
    ):
        _raise_ai_error("Choose up to three valid document IDs.", "VALIDATION_ERROR", 422)
    _validate_document_ownership(user, document_ids)
    try:
        allowed = consume_ai_request(AI_SCOPE_CUSTOMER, user=user)
    except (SQLAlchemyError, RuntimeError) as error:
        db.session.rollback()
        raise ApiError(
            "The assistant is temporarily unavailable.",
            "AI_UNAVAILABLE",
            503,
            details={"request_id": secrets.token_hex(16), "retryable": True},
        ) from error
    if not allowed:
        _raise_ai_error("You have reached the assistant request limit.", "RATE_LIMITED", 429, retryable=True)
    return success_response(search_customer_documents(
        user, query.strip(), document_ids=document_ids, limit=5,
    ))


@ai_api.get("/settings")
def get_settings():
    user = _require_user(customer_only=True)
    preference = db.session.get(AIPreferences, user.id)
    return success_response({
        "external_ai_enabled": external_consent_enabled(user=user),
        "long_term_memory_enabled": bool(preference and preference.long_term_memory_enabled),
        "personalized_recommendations_enabled": bool(
            preference and preference.personalized_recommendations_enabled
        ),
        "smart_notifications_enabled": bool(
            preference and preference.smart_notifications_enabled
        ),
    })


@ai_api.patch("/settings")
def update_settings():
    user = _require_user(customer_only=True)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        _raise_ai_error("Send at least one AI preference.", "VALIDATION_ERROR", 422)
    allowed_fields = _CUSTOMER_ONLY_SETTINGS | {"external_ai_enabled"}
    if set(payload) - allowed_fields or any(type(value) is not bool for value in payload.values()):
        _raise_ai_error("Choose valid boolean AI preferences.", "VALIDATION_ERROR", 422)

    preference = db.session.get(AIPreferences, user.id)
    if preference is None:
        preference = AIPreferences(user_id=user.id)
        db.session.add(preference)
    for field in _CUSTOMER_ONLY_SETTINGS & payload.keys():
        setattr(preference, field, payload[field])

    if "external_ai_enabled" in payload:
        if not set_external_consent(payload["external_ai_enabled"], user=user):
            db.session.rollback()
            _raise_ai_error("The AI preference could not be saved.", "AI_UNAVAILABLE", 503, retryable=True)
    else:
        try:
            db.session.commit()
        except SQLAlchemyError as error:
            db.session.rollback()
            raise ApiError(
                "The AI preference could not be saved.",
                "AI_UNAVAILABLE",
                503,
                details={"request_id": secrets.token_hex(16), "retryable": True},
            ) from error
    return get_settings()


@ai_api.get("/memory")
def list_memories():
    user = _require_user(customer_only=True)
    preference = db.session.get(AIPreferences, user.id)
    if not preference or not preference.long_term_memory_enabled:
        _raise_ai_error("Enable opt-in memory in AI settings first.", "MEMORY_DISABLED", 409)
    rows = db.session.scalars(
        select(AIUserMemory)
        .where(AIUserMemory.user_id == user.id)
        .order_by(AIUserMemory.created_at.desc(), AIUserMemory.id.desc())
        .limit(20)
    ).all()
    return success_response([
        {"id": row.id, "content": row.content, "created_at": row.created_at.isoformat()}
        for row in rows
    ])


@ai_api.post("/memory")
def create_memory():
    user = _require_user(customer_only=True)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"content"}:
        _raise_ai_error("Send one memory note.", "VALIDATION_ERROR", 422)
    content = payload.get("content")
    if not isinstance(content, str) or not content.strip() or len(content.strip()) > 500:
        _raise_ai_error("Save one note under 500 characters.", "VALIDATION_ERROR", 422)
    preference = db.session.get(AIPreferences, user.id)
    if not preference or not preference.long_term_memory_enabled:
        _raise_ai_error("Enable opt-in memory in AI settings first.", "MEMORY_DISABLED", 409)
    count = db.session.scalar(
        select(func.count(AIUserMemory.id)).where(AIUserMemory.user_id == user.id)
    )
    if count >= 20:
        _raise_ai_error("Delete a saved note before adding another.", "MEMORY_LIMIT", 429)
    memory = AIUserMemory(user_id=user.id, content=content.strip())
    db.session.add(memory)
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise ApiError(
            "The memory note could not be saved.",
            "AI_UNAVAILABLE",
            503,
            details={"request_id": secrets.token_hex(16), "retryable": True},
        ) from error
    return success_response(
        {"id": memory.id, "content": memory.content, "created_at": memory.created_at.isoformat()},
        message="Memory saved.",
        status=201,
    )


@ai_api.delete("/memory/<int:memory_id>")
def delete_memory(memory_id):
    user = _require_user(customer_only=True)
    memory = db.session.scalar(
        select(AIUserMemory).where(
            AIUserMemory.id == memory_id,
            AIUserMemory.user_id == user.id,
        )
    )
    if memory is None:
        _raise_ai_error("Memory note not found.", "NOT_FOUND", 404)
    db.session.delete(memory)
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise ApiError(
            "The memory note could not be deleted.",
            "AI_UNAVAILABLE",
            503,
            details={"request_id": secrets.token_hex(16), "retryable": True},
        ) from error
    return success_response({"id": memory_id, "deleted": True})


@ai_api.post("/chat")
def chat():
    """Run a bounded customer query without persisting conversation history."""
    user = _require_user(customer_only=True)
    request_id = secrets.token_hex(16)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        _raise_ai_error("Send a JSON object.", "VALIDATION_ERROR", 422)
    unsupported = set(payload) - {"message", "mode", "privacy_mode", "history", "document_ids"}
    if unsupported:
        _raise_ai_error(
            "One or more requested chat options are not supported.",
            "UNSUPPORTED_OPTION", 422,
        )

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip() or len(message) > 2000:
        _raise_ai_error("Send a message under 2,000 characters.", "VALIDATION_ERROR", 422)
    if payload.get("mode", "auto") != "auto":
        _raise_ai_error("Only automatic model routing is currently supported.", "UNSUPPORTED_MODE", 422)
    privacy_mode = payload.get("privacy_mode", "standard")
    if privacy_mode not in {"standard", "local_only"}:
        _raise_ai_error("Choose standard or local_only privacy mode.", "VALIDATION_ERROR", 422)
    try:
        history = sanitize_history(payload.get("history"))
    except ValueError as error:
        raise ApiError(
            str(error),
            "VALIDATION_ERROR",
            422,
            details={"request_id": request_id, "retryable": False},
        ) from error
    document_ids = payload.get("document_ids")
    if document_ids is not None and (
        not isinstance(document_ids, list)
        or not document_ids
        or len(document_ids) > 3
        or any(type(document_id) is not int or document_id < 1 for document_id in document_ids)
        or len(set(document_ids)) != len(document_ids)
    ):
        _raise_ai_error("Choose up to three valid document IDs.", "VALIDATION_ERROR", 422)
    _validate_document_ownership(user, document_ids)
    document_sources = search_customer_documents(
        user, message.strip(), document_ids=document_ids, limit=3,
    ) if document_ids else []

    try:
        allowed = consume_ai_request(AI_SCOPE_CUSTOMER, user=user)
    except (SQLAlchemyError, RuntimeError) as error:
        db.session.rollback()
        raise ApiError(
            "The assistant is temporarily unavailable.",
            "AI_UNAVAILABLE",
            503,
            details={"request_id": request_id, "retryable": True},
        ) from error
    if not allowed:
        raise ApiError(
            "You have reached the assistant request limit. Please try again shortly.",
            "RATE_LIMITED",
            429,
            details={"request_id": request_id, "retryable": True},
        )

    result = handle_marketplace_ai_query(
        message,
        user=user,
        channel="api",
        context={"history": history, "customer_documents": document_sources},
        rate_limited=True,
        allow_external=(
            privacy_mode != "local_only"
            and not document_ids
            and external_consent_enabled(user=user)
        ),
    )
    answer = sanitize_ai_response(result.get("answer") or result.get("fallback"))
    if not result.get("ok"):
        raise ApiError(
            answer,
            "AI_UNAVAILABLE",
            503,
            details={"request_id": request_id, "retryable": True},
        )
    return success_response(
        {
            "request_id": request_id,
            "content": answer,
            "answer": answer,
            "products": result.get("products", []),
            **_public_chat_metadata(result),
            "sources": [
                {"document_id": item["document_id"], "filename": item["filename"]}
                for item in document_sources
            ],
            "scope": AI_SCOPE_CUSTOMER,
        }
    )
