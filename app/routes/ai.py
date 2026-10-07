"""Customer AI web endpoints. Scope is derived from the authenticated session."""

from io import BytesIO
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for, send_file
from sqlalchemy import func, select

from ..ai.core.permissions import AI_SCOPE_CUSTOMER
from ..ai.core.provider import AIProviderError, AIService
from ..ai.core.tools import ToolRegistry
from ..ai.marketplace_tools import (
    build_customer_tool_registry, get_review_summary_source,
    handle_marketplace_ai_query,
)
from ..extensions import db
from ..models import AIPreferences, AIUserMemory
from ..models import AIProductPriceAlert
from ..ai.core.consent import external_consent_enabled, set_external_consent
from ..ai.core.guardrails import sanitize_history
from ..security import customer_or_guest_required, current_session_user, role_required
from ..services.ai_rate_limit import consume_ai_request
from ..services.ai_price_alerts import cancel_price_alert, observed_price_history, save_price_alert
from ..services.catalog import get_product_by_slug
from ..services.product_images import (
    MAX_PRODUCT_IMAGE_BYTES, ProductImageError, normalize_product_image,
)


ai_bp = Blueprint("ai", __name__, url_prefix="/ai")
_MAX_AUDIO_BYTES = 8 * 1024 * 1024
_ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg"}
_ALLOWED_TTS_TYPES = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/webm"}


def _customer_user():
    user = getattr(g, "current_user", None)
    if user is not None and user.role != "customer":
        abort(403)
    return user


def _customer_provider_configured():
    config = current_app.config
    provider = str(config.get("AI_PROVIDER") or "").strip().lower()
    return bool(
        config.get("AI_ENABLED")
        and provider in {"openai_compatible", "openai-compatible", "openai"}
        and config.get("AI_API_KEY")
        and config.get("AI_MODEL")
        and config.get("AI_BASE_URL")
    )


def _consume(user):
    try:
        return consume_ai_request(AI_SCOPE_CUSTOMER, user=user)
    except Exception:
        db.session.rollback()
        return False


def _limit_response():
    message = "You have reached the assistant request limit. Please try again shortly."
    return jsonify(ok=False, scope=AI_SCOPE_CUSTOMER, answer=message, fallback=message), 429


def _audio_signature_matches(content_type, data):
    if content_type in {"audio/wav", "audio/x-wav"}:
        return data.startswith(b"RIFF") and data[8:12] == b"WAVE"
    if content_type == "audio/webm":
        return data.startswith(bytes.fromhex("1A45DFA3"))
    if content_type == "audio/ogg":
        return data.startswith(b"OggS")
    if content_type == "audio/mpeg":
        return data.startswith(b"ID3") or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0)
    if content_type == "audio/mp4":
        return len(data) > 8 and data[4:8] == b"ftyp"
    return False


@ai_bp.get("/")
@customer_or_guest_required
def index():
    user = _customer_user()
    initial_prompt = (request.args.get("q") or request.args.get("prompt") or "").strip()[:2000]
    return render_template(
        "ai/customer.html", user=user, csrf_value=None,
        ai_provider_configured=bool(current_app.config.get("AI_LOCAL_BASE_URL")
                                     and current_app.config.get("AI_LOCAL_MODEL")),
        external_ai_consent=external_consent_enabled(user=user),
        initial_prompt=initial_prompt,
    )


@ai_bp.post("/chat")
@customer_or_guest_required
def chat():
    user = _customer_user()
    payload = request.get_json(silent=True) if request.is_json else request.form
    if not hasattr(payload, "get"):
        return jsonify(ok=False, answer="Send a text question."), 400
    prompt = payload.get("prompt") or payload.get("message") or payload.get("query") or ""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
        return jsonify(ok=False, answer="Send a question under 2,000 characters."), 400
    try:
        history = sanitize_history(payload.get("history"))
    except ValueError as error:
        return jsonify(ok=False, answer=str(error)), 400
    if not _consume(user):
        return _limit_response()
    if user is None and isinstance(payload.get("external_ai_consent"), bool):
        set_external_consent(payload["external_ai_consent"])
    result = handle_marketplace_ai_query(prompt, user=user, channel="web", rate_limited=True,
                                         context={"history": history})
    return jsonify(result), 200 if result.get("ok") else 503


@ai_bp.post("/external-consent")
@customer_or_guest_required
def external_consent():
    user = _customer_user()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("enabled"), bool):
        return jsonify(ok=False, answer="Choose whether external specialist assistance is enabled."), 400
    if not set_external_consent(payload["enabled"], user=user):
        return jsonify(ok=False, answer="The consent setting could not be saved."), 503
    return jsonify(ok=True, enabled=payload["enabled"])


@ai_bp.post("/role-external-consent")
@role_required("seller", "rider", "admin", "super_admin")
def role_external_consent():
    """Let authenticated Seller/Admin accounts control paid-provider consent."""
    user = current_session_user()
    if request.is_json:
        payload = request.get_json(silent=True)
        enabled = payload.get("enabled") if isinstance(payload, dict) else None
    else:
        enabled = request.form.get("enabled") == "1"
    if not isinstance(enabled, bool):
        return jsonify(ok=False, answer="Choose whether external specialist assistance is enabled."), 400
    if not set_external_consent(enabled, user=user):
        return jsonify(ok=False, answer="The consent setting could not be saved."), 503
    if request.is_json:
        return jsonify(ok=True, enabled=enabled)
    destination = ("admin.ai_workspace" if user.role in {"admin", "super_admin"}
                   else "rider.ai_workspace" if user.role == "rider"
                   else "seller.ai_workspace")
    return redirect(url_for(destination))


@ai_bp.post("/voice-search")
@customer_or_guest_required
def voice_search():
    user = _customer_user()
    upload = request.files.get("audio")
    if upload is None:
        return jsonify(ok=False, answer="Choose an audio recording first."), 400
    content_type = (upload.mimetype or "").lower().split(";", 1)[0]
    if content_type not in _ALLOWED_AUDIO_TYPES:
        return jsonify(ok=False, answer="Use a supported voice recording format."), 415
    if request.content_length and request.content_length > _MAX_AUDIO_BYTES + 64 * 1024:
        return jsonify(ok=False, answer="The voice recording is too large."), 413
    audio = upload.stream.read(_MAX_AUDIO_BYTES + 1)
    if not audio or len(audio) > _MAX_AUDIO_BYTES:
        return jsonify(ok=False, answer="The voice recording is empty or too large."), 413
    if not _audio_signature_matches(content_type, audio):
        return jsonify(ok=False, answer="The voice recording format does not match its file type."), 415
    if not _consume(user):
        return _limit_response()
    try:
        service = AIService(current_app.config)
        prompt = service.transcribe(audio, filename="voice-audio", content_type=content_type)
        result = handle_marketplace_ai_query(
            prompt, user=user, channel="voice", rate_limited=True,
            context={"input_mode": "voice"},
        )
        result["transcript"] = prompt
        return jsonify(result), 200 if result.get("ok") else 503
    except (AIProviderError, ValueError):
        return jsonify(ok=False, answer="Voice search is unavailable. You can type the same search instead."), 503


@ai_bp.post("/image-search")
@customer_or_guest_required
def image_search():
    user = _customer_user()
    upload = request.files.get("image")
    if upload is None:
        return jsonify(ok=False, answer="Choose a product image first."), 400
    if request.content_length and request.content_length > MAX_PRODUCT_IMAGE_BYTES + 64 * 1024:
        return jsonify(ok=False, answer="The image upload is too large."), 413
    try:
        raw = upload.stream.read(MAX_PRODUCT_IMAGE_BYTES + 1)
        normalized = normalize_product_image(raw)
    except ProductImageError as error:
        status = 413 if not raw or len(raw) > MAX_PRODUCT_IMAGE_BYTES else 415
        return jsonify(ok=False, answer=str(error)), status
    if not _consume(user):
        return _limit_response()
    try:
        service = AIService(current_app.config)
        description = service.describe_image(normalized, content_type="image/jpeg")
    except (AIProviderError, ValueError):
        return jsonify(ok=False, answer="Visual search is unavailable. Use the catalog search instead."), 503
    result = handle_marketplace_ai_query(
        description, user=user, channel="image", rate_limited=True,
        context={"input_mode": "image"},
    )
    result["search_description"] = description
    return jsonify(result), 200 if result.get("ok") else 503


@ai_bp.post("/speak")
@customer_or_guest_required
def speak():
    """Synthesize a short answer through the configured private Bengali-capable TTS service."""
    user = _customer_user()
    if not _consume(user):
        return _limit_response()
    payload = request.get_json(silent=True)
    text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip() or len(text) > 1200:
        return jsonify(ok=False, answer="Send a response under 1,200 characters."), 400
    config = current_app.config
    base_url = str(config.get("AI_TTS_BASE_URL") or "").strip().rstrip("/")
    model = str(config.get("AI_TTS_MODEL") or "").strip()
    from urllib.parse import urlsplit
    parsed = urlsplit(base_url)
    if (not base_url or not model or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or config.get("ENVIRONMENT") == "production" and parsed.scheme != "https"):
        return jsonify(ok=False, answer="Local speech output is not configured."), 503
    headers = {"Content-Type": "application/json"}
    key = str(config.get("AI_LOCAL_API_KEY") or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        import requests
        response = requests.post(
            f"{base_url}/audio/speech",
            json={"model": model, "input": text.strip(),
                  "voice": str(config.get("AI_TTS_VOICE") or "default"), "response_format": "wav"},
            headers=headers, timeout=min(45, int(config.get("AI_TIMEOUT", 15)) * 2), stream=True,
        )
        try:
            response.raise_for_status()
            audio_buffer = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if len(audio_buffer) + len(chunk) > 10 * 1024 * 1024:
                    return jsonify(ok=False, answer="Local speech response was too large."), 503
                audio_buffer.extend(chunk)
            content_type = response.headers.get("Content-Type", "audio/wav").split(";", 1)[0]
            if not audio_buffer or content_type not in _ALLOWED_TTS_TYPES:
                return jsonify(ok=False, answer="Local speech response was invalid."), 503
            audio = bytes(audio_buffer)
        finally:
            response.close()
        if not audio:
            return jsonify(ok=False, answer="Local speech response was invalid."), 503
        result = send_file(BytesIO(audio), mimetype=content_type, download_name="nexhaat-response.wav")
        result.headers["Cache-Control"] = "no-store"
        result.headers["X-Content-Type-Options"] = "nosniff"
        return result
    except Exception:
        return jsonify(ok=False, answer="Local speech output is temporarily unavailable."), 503


@ai_bp.post("/cart/confirm")
@customer_or_guest_required
def confirm_cart_change():
    user = _customer_user()
    if user is None:
        abort(401)
    if not _consume(user):
        return _limit_response()
    payload = request.get_json(silent=True) if request.is_json else request.form
    proposal_id = payload.get("proposal_id", "") if hasattr(payload, "get") else ""
    pending = session.get("ai_cart_proposal")
    if not proposal_id or not isinstance(pending, dict) or pending.get("id") != proposal_id:
        return jsonify(ok=False, answer="This cart suggestion is no longer active. Ask the assistant again."), 400
    if pending.get("action") == "add":
        from ..models import Product, ProductVariant
        from ..ai.marketplace_tools import _display_price
        product = db.session.scalar(select(Product).where(
            Product.id == pending.get("product_id"), Product.is_available.is_(True),
            Product.moderation_status == "approved",
        ))
        variant = db.session.get(ProductVariant, pending.get("variant_id")) if pending.get("variant_id") else None
        if (product is None or product.slug != pending.get("product_slug")
                or not product.category.is_active
                or bool(pending.get("variant_id")) and variant is None
                or variant is not None and (variant.product_id != product.id or not variant.is_active)
                or str(Decimal(str(_display_price(product, variant))).quantize(Decimal("0.01"))) != str(pending.get("price"))):
            session.pop("ai_cart_proposal", None)
            return jsonify(ok=False, answer="The current price or product option changed. Ask for a fresh cart suggestion."), 409
    # Consume before executing so the signed, session-bound confirmation is one-use.
    session.pop("ai_cart_proposal", None)
    from ..services.cart import CartError, add_customer_cart_item, update_customer_cart_item

    try:
        action = pending["action"]
        if action == "add":
            add_customer_cart_item(user.id, int(pending["product_id"]),
                                   quantity=int(pending["quantity"]),
                                   variant_id=int(pending["variant_id"]) if pending.get("variant_id") else None)
        elif action in {"set_quantity", "remove"}:
            update_customer_cart_item(user.id, pending["item_key"],
                                      0 if action == "remove" else int(pending["quantity"]))
        else:
            raise ValueError("Unsupported cart action.")
    except (CartError, ValueError, TypeError, KeyError):
        db.session.rollback()
        return jsonify(ok=False, answer="The item or stock changed. Please review your cart and try again."), 409
    from ..services.ai_action_notices import notify_admin_ai_action

    notify_admin_ai_action(
        "customer.ai.cart_change.confirmed",
        actor=user,
        target_id=user.id,
    )
    return jsonify(ok=True, answer="Your cart was updated. Checkout remains a separate step.", cart_url=url_for("orders.cart"))


@ai_bp.post("/cart/proposal")
@customer_or_guest_required
def create_cart_proposal():
    user = _customer_user()
    if user is None:
        abort(401)
    if not _consume(user):
        return _limit_response()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(ok=False, answer="A cart change proposal is required."), 400
    action = payload.get("action")
    allowed = {"action", "product_slug", "quantity", "variant_id", "item_key"}
    if set(payload) - allowed:
        return jsonify(ok=False, answer="The cart change has unsupported fields."), 400
    registry = build_customer_tool_registry()
    proposal = registry.call("propose_cart_change", scope=AI_SCOPE_CUSTOMER, user=user, arguments=payload)
    if not proposal.get("ok"):
        return jsonify(ok=False, answer="That cart change could not be prepared. Please check product and quantity."), 400
    data = proposal.get("result") or {}
    if data.get("needs_variant"):
        return jsonify(ok=False, needs_variant=True, product=data["product"], answer="Choose an available product option first."), 409
    import secrets

    proposal_id = secrets.token_urlsafe(18)
    session["ai_cart_proposal"] = {**data, "id": proposal_id}
    return jsonify(ok=True, proposal_id=proposal_id, proposal=data,
                   answer="Review the current price and quantity, then confirm to update your cart.")


@ai_bp.get("/review-summary/<slug>")
@customer_or_guest_required
def review_summary(slug):
    _customer_user()
    if not _consume(getattr(g, "current_user", None)):
        return _limit_response()
    source = get_review_summary_source(product_slug=slug)
    if source.get("error"):
        abort(404)
    count = source["count"]
    if not count:
        return jsonify(ok=True, summary="There are no approved reviews to summarize yet.", count=0)
    registry = ToolRegistry(max_calls=1)
    registry.register("get_review_summary_source", get_review_summary_source,
                      scope=AI_SCOPE_CUSTOMER, description="Return only approved public reviews.",
                      parameters={"type": "object", "properties": {"product_slug": {"type": "string", "maxLength": 180}}, "required": ["product_slug"], "additionalProperties": False})
    prompt = f"Summarize the verified review themes for product {slug!r}. Use only approved reviews, identify uncertainty, and do not infer product facts."
    result = AIService(current_app.config).respond(prompt, scope=AI_SCOPE_CUSTOMER,
                                                    user=getattr(g, "current_user", None), tools=registry)
    grounded = any(isinstance(item, dict) and item.get("ok") is True
                   for item in result.get("tool_results", []))
    summary = result.get("answer") if result.get("ok") and grounded else None
    if not summary:
        summary = f"{count} approved reviews; average rating {source['average_rating']}/5. A written summary is available when AI is configured."
    return jsonify(ok=True, summary=summary, count=count,
                   average_rating=source["average_rating"], source="approved reviews only")


@ai_bp.get("/price-history/<slug>")
@customer_or_guest_required
def price_history(slug):
    _customer_user()
    product = get_product_by_slug(slug)
    if (not product or product.moderation_status != "approved" or not product.is_available
            or not getattr(product.category, "is_active", True)):
        abort(404)
    observations = observed_price_history(product.id)
    return jsonify(ok=True, product=product.name, source="recorded NexHaat listing prices",
                   history=observations,
                   answer=("No earlier observed price records are available."
                           if not observations else "Only stored catalog observations are shown."))


@ai_bp.post("/price-alert/<slug>")
@customer_or_guest_required
def price_alert(slug):
    user = _customer_user()
    if user is None:
        abort(401)
    product = get_product_by_slug(slug)
    if (not product or product.moderation_status != "approved" or not product.is_available
            or not getattr(product.category, "is_active", True)):
        abort(404)
    if request.form.get("action") == "cancel":
        cancel_price_alert(user, product)
        flash("Your price alert is off.", "success")
        return redirect(url_for("main.food", slug=product.slug))
    raw_target = request.form.get("target_price", "").strip()
    try:
        target = Decimal(raw_target)
    except (InvalidOperation, ValueError):
        target = Decimal("NaN")
    if (not target.is_finite() or target < 0 or target > Decimal("99999999.99")
            or target != target.quantize(Decimal("0.01"))):
        flash("Enter a valid target price with up to two decimal places.", "error")
        return redirect(url_for("main.food", slug=product.slug))
    save_price_alert(user, product, target)
    flash("Your target-price alert is saved.", "success")
    return redirect(url_for("main.food", slug=product.slug))


@ai_bp.route("/preferences", methods=["GET", "POST"])
@customer_or_guest_required
def preferences():
    user = _customer_user()
    if user is None:
        abort(401)
    preference = db.session.get(AIPreferences, user.id)
    if request.method == "POST":
        enabled = request.form.get("smart_notifications_enabled") == "1"
        if preference is None:
            preference = AIPreferences(user_id=user.id)
            db.session.add(preference)
        preference.smart_notifications_enabled = enabled
        preference.personalized_recommendations_enabled = (
            request.form.get("personalized_recommendations_enabled") == "1"
        )
        preference.long_term_memory_enabled = request.form.get("long_term_memory_enabled") == "1"
        db.session.commit()
        set_external_consent(request.form.get("external_ai_consent") == "1", user=user)
        return redirect(url_for("ai.preferences"))
    return render_template("ai/preferences.html", preference=preference,
                           enabled=bool(preference and preference.smart_notifications_enabled),
                           personalization_enabled=bool(
                               preference and preference.personalized_recommendations_enabled
                           ),
                           memory_enabled=bool(preference and preference.long_term_memory_enabled),
                           external_consent=external_consent_enabled(user=user),
                           memories=db.session.scalars(
                               select(AIUserMemory).where(AIUserMemory.user_id == user.id)
                               .order_by(AIUserMemory.created_at.desc()).limit(20)
                           ).all())


@ai_bp.post("/memory")
@customer_or_guest_required
def add_memory():
    user = _customer_user()
    if user is None:
        abort(401)
    payload = request.get_json(silent=True) if request.is_json else request.form
    content = payload.get("content") if hasattr(payload, "get") else None
    preference = db.session.get(AIPreferences, user.id)
    if not preference or not preference.long_term_memory_enabled:
        return jsonify(ok=False, answer="Enable opt-in memory in AI preferences first."), 409
    if not isinstance(content, str) or not content.strip() or len(content.strip()) > 500:
        return jsonify(ok=False, answer="Save one note under 500 characters."), 400
    if db.session.scalar(select(func.count(AIUserMemory.id)).where(AIUserMemory.user_id == user.id)) >= 20:
        return jsonify(ok=False, answer="Delete a saved note before adding another. The limit is 20 notes."), 429
    memory = AIUserMemory(user_id=user.id, content=content.strip())
    db.session.add(memory)
    db.session.commit()
    if not request.is_json:
        return redirect(url_for("ai.preferences"))
    return jsonify(ok=True, id=memory.id, content=memory.content)


@ai_bp.route("/memory/<int:memory_id>", methods=["DELETE", "POST"])
@customer_or_guest_required
def delete_memory(memory_id):
    user = _customer_user()
    if user is None:
        abort(401)
    memory = db.session.scalar(select(AIUserMemory).where(
        AIUserMemory.id == memory_id, AIUserMemory.user_id == user.id
    ))
    if memory is not None:
        db.session.delete(memory)
        db.session.commit()
    if request.method == "POST":
        return redirect(url_for("ai.preferences"))
    return jsonify(ok=True)
