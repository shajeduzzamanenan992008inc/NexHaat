"""Seller-facing AI workflow. All generated copy is returned as a draft suggestion."""

import json
import re

from flask import current_app

from .core.permissions import AI_SCOPE_SELLER
from .core.provider import AIService
from .seller_tools import (
    build_seller_tool_registry,
    get_seller_price_context_tool,
)


def _bounded(value, maximum):
    return str(value or "").strip()[:maximum]


def _json_suggestion(answer, *, valid_categories=()):
    text = str(answer or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {"description": text[:3000], "bullets": [], "keywords": [], "tags": []}
    if not isinstance(value, dict):
        return {"description": text[:3000], "bullets": [], "keywords": [], "tags": []}
    def string_list(key, maximum, item_limit):
        items = value.get(key, [])
        if not isinstance(items, list):
            return []
        return [_bounded(item, maximum) for item in items[:item_limit] if isinstance(item, str)]

    translations = value.get("translations")
    if not isinstance(translations, dict):
        translations = {}
    category = _bounded(value.get("category"), 100)
    allowed_categories = {str(item) for item in valid_categories}
    return {
        "title": _bounded(value.get("title"), 160),
        "description": _bounded(value.get("description"), 3000),
        "bullets": string_list("bullets", 220, 8),
        "category": category if category in allowed_categories else None,
        "tags": string_list("tags", 40, 12),
        "keywords": string_list("keywords", 60, 12),
        "seo_title": _bounded(value.get("seo_title"), 160),
        "seo_description": _bounded(value.get("seo_description"), 300),
        "translations": {
            locale: {"title": _bounded(item.get("title"), 160),
                     "description": _bounded(item.get("description"), 3000)}
            for locale, item in translations.items()
            if locale in {"en_US", "bn_BD", "hi_IN"} and isinstance(item, dict)
        },
        "unknown_attributes": string_list("unknown_attributes", 160, 10),
    }


def generate_listing_suggestion(user, *, title="", description="", product_id=None,
                                competitor_price=None):
    """Return a validated listing draft and actual owner-scoped quality context."""
    registry = build_seller_tool_registry()
    args = {"title": _bounded(title, 160), "description": _bounded(description, 3000)}
    if product_id:
        args["product_id"] = int(product_id)
    listing = registry.call("get_seller_listing_context", scope=AI_SCOPE_SELLER,
                            user=user, arguments=args)
    if not listing.get("ok"):
        return {"ok": False, "answer": "The listing could not be loaded for this seller account."}
    quality = registry.call("get_seller_listing_quality", scope=AI_SCOPE_SELLER,
                            user=user, arguments=args).get("result", {})
    duplicate_args = {"title": args["title"], "description": args["description"], "limit": 5}
    if product_id:
        duplicate_args["product_id"] = int(product_id)
    duplicates = registry.call("find_seller_duplicates", scope=AI_SCOPE_SELLER,
                               user=user, arguments=duplicate_args).get("result", [])
    facts = {"seller_listing": listing.get("result"), "quality_review": quality,
             "similar_public_listings": duplicates,
             "proposal_only": True}
    prompt = (
        "Create an optional marketplace listing draft from the seller-provided fields. "
        "Return one JSON object with title, description, bullets, category, tags, keywords, "
        "seo_title, seo_description, translations (en_US, bn_BD, hi_IN), and unknown_attributes. "
        "Do not invent specifications, certifications, materials, sizes, or compatibility. "
        "If an attribute is unknown, put its name in unknown_attributes. Suggest a category only "
        "from the supplied active category list. Similar listings are review hints, not proof of copying. "
        "The seller must review and save any changes themselves."
    )
    service = AIService(current_app.config)
    result = service.respond(prompt, scope=AI_SCOPE_SELLER, user=user,
                             context={"draft_title": args["title"],
                                      "draft_description": args["description"],
                                      "seller_facts": facts}, tools=registry)
    if result.get("ok"):
        suggestion = _json_suggestion(
            result.get("answer"),
            valid_categories=(listing.get("result") or {}).get("valid_categories", ()),
        )
        return {"ok": True, "answer": "Draft suggestions are ready for your review.",
                "suggestion": suggestion, "quality": quality,
                "similar_listings": duplicates[:5], "model_generated": True}
    suggestion = {
        "title": args["title"], "description": args["description"],
        "bullets": [], "category": (listing.get("result") or {}).get("existing_product", {}).get("category"),
        "tags": [], "keywords": re.findall(r"[\w-]+", args["title"].lower())[:8],
        "seo_title": args["title"][:160], "seo_description": "",
        "translations": {}, "unknown_attributes": [],
    }
    return {"ok": False, "answer": "AI writing is unavailable. The current listing was not changed; review these data-based quality hints.",
            "suggestion": suggestion, "quality": quality,
            "similar_listings": duplicates[:5], "model_generated": False}


def run_seller_query(user, prompt):
    """Answer seller analytics questions from the authenticated seller's records."""
    registry = build_seller_tool_registry()
    lowered = str(prompt or "").lower()
    if any(term in lowered for term in ("forecast", "stockout", "stock-out", "demand", "inventory", "স্টক", "মজুদ")):
        tool = "get_seller_inventory_forecast"
    elif any(term in lowered for term in ("price", "pricing", "competitor", "দাম", "মূল্য")):
        # Without a selected owned product or seller supplied competitor price, do not fabricate pricing advice.
        tool = "get_seller_insights"
    else:
        tool = "get_seller_insights"
    from flask import current_app
    service = AIService(current_app.config)
    result = service.respond(
        str(prompt or "")[:2000], scope=AI_SCOPE_SELLER, user=user,
        context={"request_kind": "seller analytics"}, tools=registry,
    )
    if result.get("ok") and any(isinstance(item, dict) and item.get("ok") is True
                                  for item in result.get("tool_results", [])):
        return {**result, "data": result.get("tool_results", [])}
    data = registry.call(tool, scope=AI_SCOPE_SELLER, user=user)
    answer = "Seller inventory and sales data from your own account:" if tool == "get_seller_inventory_forecast" else "Sales and inventory insight from your own seller account:"
    return {"ok": True, "scope": AI_SCOPE_SELLER, "answer": answer,
            "data": data.get("result") if data.get("ok") else {}, "tools_used": [tool],
            "fallback": result.get("fallback")}


def get_seller_price_suggestion(user, *, product_id, competitor_price=None):
    """Provide an informational reference from public category data and seller input."""
    from decimal import Decimal
    context = get_seller_price_context_tool(user=user, product_id=product_id,
                                            competitor_price=competitor_price)
    median = Decimal(context["marketplace_category_median_bdt"]) if context.get("marketplace_category_median_bdt") else None
    current = Decimal(context["current_price_bdt"])
    competitor = Decimal(context["seller_supplied_competitor_price_bdt"]) if context.get("seller_supplied_competitor_price_bdt") else None
    if median is None:
        reference = None
        answer = "There are not enough public category prices for a comparison."
    else:
        reference = median.quantize(Decimal("0.01"))
        answer = "Compare your current price with this public category sample; this is only a reference, not a market-wide competitor survey."
    data = {**context, "suggested_reference_bdt": str(reference) if reference is not None else None,
            "current_vs_reference": ("above" if current > reference else "below" if current < reference else "at") if reference is not None else None,
            "competitor_comparison": ("above" if competitor > reference else "below" if competitor < reference else "at") if competitor is not None and reference is not None else None,
            "note": "No listing price was changed. The seller decides whether to update it."}
    return {"ok": True, "scope": AI_SCOPE_SELLER, "answer": answer, "data": data,
            "tools_used": ["get_seller_price_context"]}
