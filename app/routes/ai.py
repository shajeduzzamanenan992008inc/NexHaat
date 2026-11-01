"""Customer AI web endpoints. Scope is derived from the authenticated session."""

from decimal import Decimal
from io import BytesIO

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select

from ..ai.core.permissions import AI_SCOPE_CUSTOMER
from ..ai.core.provider import AIProviderError, AIService
from ..ai.core.tools import ToolRegistry
from ..ai.marketplace_tools import (
    build_customer_tool_registry,
    get_review_summary_source,
    handle_marketplace_ai_query,
)
from ..extensions import db
from ..models import AIPreferences
from ..security import customer_or_guest_required
from ..services.ai_rate_limit import consume_ai_request

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_AUDIO_BYTES = 8 * 1024 * 1024
_ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg"}


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
    return render_template(
        "ai/customer.html", user=user, csrf_value=None,
        ai_provider_configured=_customer_provider_configured(),
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
    if not _consume(user):
        return _limit_response()
    result = handle_marketplace_ai_query(prompt, user=user, channel="web", rate_limited=True)
    return jsonify(result), 200 if result.get("ok") else 503


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
    if request.content_length and request.content_length > _MAX_IMAGE_BYTES + 64 * 1024:
        return jsonify(ok=False, answer="The image upload is too large."), 413
    raw = upload.stream.read(_MAX_IMAGE_BYTES + 1)
    if not raw or len(raw) > _MAX_IMAGE_BYTES:
        return jsonify(ok=False, answer="The image is empty or larger than 5 MB."), 413
    try:
        image = Image.open(BytesIO(raw))
        image.verify()
        image = Image.open(BytesIO(raw))
        image_format = image.format
        image = ImageOps.exif_transpose(image)
        if (image_format not in {"JPEG", "PNG", "WEBP"} or image.width > 8000
                or image.height > 8000 or image.width * image.height > 40_000_000):
            return jsonify(ok=False, answer="Use a JPEG, PNG, or WebP image under 8,000 × 8,000 pixels."), 415
        image.thumbnail((1024, 1024))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=78, optimize=True)
        normalized = output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify(ok=False, answer="The uploaded file is not a valid product image."), 415
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
        from ..ai.marketplace_tools import _display_price
        from ..models import Product, ProductVariant
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
    from ..services.cart import (
        CartError,
        add_customer_cart_item,
        update_customer_cart_item,
    )

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
        db.session.commit()
        return redirect(url_for("ai.preferences"))
    return render_template("ai/preferences.html", preference=preference,
                           enabled=bool(preference and preference.smart_notifications_enabled))
