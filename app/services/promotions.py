"""Promotion code validation and discount calculations."""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sqlalchemy import select

from ..extensions import db
from ..models import PromotionCode


class PromotionError(ValueError):
    """Raised when a promotion code is invalid, expired, or not eligible."""


def _coerce_decimal(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise PromotionError(f"Invalid {label}.") from exc
    if not amount.is_finite():
        raise PromotionError(f"Invalid {label}.")
    return amount


def _as_utc(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def get_active_promotion(code, *, lock=False):
    """Return the active promotion object for a supplied code."""
    if code is None:
        raise PromotionError("Promotion code is required.")

    normalized = str(code).strip().upper()
    if not normalized:
        raise PromotionError("Promotion code is required.")

    statement = select(PromotionCode).where(PromotionCode.code == normalized)
    if lock:
        statement = statement.with_for_update()
    promotion = db.session.scalar(statement)
    if promotion is None:
        raise PromotionError("This promotion code is not valid.")
    if not promotion.is_active:
        raise PromotionError("This promotion is not active.")

    starts_at = _as_utc(promotion.starts_at)
    expires_at = _as_utc(promotion.expires_at)

    now = datetime.now(UTC)
    if starts_at and now < starts_at:
        raise PromotionError("This promotion is not active yet.")
    if expires_at and now > expires_at:
        raise PromotionError("This promotion has expired.")
    if promotion.usage_limit is not None and promotion.used_count >= promotion.usage_limit:
        raise PromotionError("This promotion has reached its usage limit.")

    return promotion


def calculate_discount_for_order(total_amount, code, *, seller_id=None, promotion=None):
    """Compute the discount amount for a given order total and promotion code."""
    order_total = _coerce_decimal(total_amount, "order total")
    promotion = promotion or get_active_promotion(code)
    if promotion.seller_id is not None and promotion.seller_id != seller_id:
        raise PromotionError("This seller deal does not apply to the items in your cart.")
    if order_total <= Decimal("0.00"):
        raise PromotionError("This promotion does not apply to the items in your cart.")

    if order_total < promotion.minimum_order_amount:
        raise PromotionError(
            f"Spend at least ৳{promotion.minimum_order_amount.quantize(Decimal('0.01'))} to use this promotion."
        )

    if promotion.discount_type == "percent":
        raw_discount = (order_total * promotion.discount_value) / Decimal("100")
        if promotion.max_discount_amount is not None:
            raw_discount = min(raw_discount, promotion.max_discount_amount)
    elif promotion.discount_type == "fixed":
        raw_discount = promotion.discount_value
    else:
        raise PromotionError("This promotion type is not supported.")

    if raw_discount < Decimal("0.00"):
        raw_discount = Decimal("0.00")
    if raw_discount > order_total:
        raw_discount = order_total

    return raw_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def allocate_discount_shares(discount_amount, seller_subtotals):
    """Allocate a rounded discount across eligible seller subtotals without losing cents."""
    shares = {seller_id: Decimal("0.00") for seller_id in seller_subtotals}
    total = sum(seller_subtotals.values(), Decimal("0.00"))
    remaining = min(Decimal(discount_amount), total)
    seller_ids = list(seller_subtotals)
    if total <= Decimal("0.00") or remaining <= Decimal("0.00"):
        return shares
    for seller_id in seller_ids[:-1]:
        share = (Decimal(discount_amount) * seller_subtotals[seller_id] / total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        share = min(share, seller_subtotals[seller_id], remaining)
        shares[seller_id] = share
        remaining -= share
    if seller_ids:
        final_seller = seller_ids[-1]
        shares[final_seller] = min(remaining, seller_subtotals[final_seller])
    return shares


def promotion_values_from_form(form, *, seller_id=None):
    """Validate an Admin coupon or seller-owned deal form into model values."""
    code = str(form.get("code", "")).strip().upper()
    name = str(form.get("name", "")).strip()
    description = str(form.get("description", "")).strip() or None
    discount_type = str(form.get("discount_type", "percent")).strip()
    if not 3 <= len(code) <= 40 or not 2 <= len(name) <= 120:
        raise PromotionError("Enter a code and campaign name within the allowed lengths.")
    if description and len(description) > 500:
        raise PromotionError("Campaign description must be 500 characters or fewer.")
    if discount_type not in {"percent", "fixed"}:
        raise PromotionError("Choose a valid discount type.")

    discount_value = _coerce_decimal(form.get("discount_value", ""), "discount value")
    minimum = _coerce_decimal(form.get("minimum_order_amount", "0"), "minimum order")
    maximum_text = str(form.get("max_discount_amount", "")).strip()
    maximum = _coerce_decimal(maximum_text, "maximum discount") if maximum_text else None
    if discount_value <= 0 or (discount_type == "percent" and discount_value > 100):
        raise PromotionError("Discount must be greater than zero and percentage discounts cannot exceed 100%.")
    if minimum < 0 or (maximum is not None and maximum < 0):
        raise PromotionError("Minimum order and maximum discount amounts cannot be negative.")

    def parse_datetime(raw, *, fallback=None):
        raw = str(raw or "").strip()
        if not raw:
            return fallback
        try:
            value = datetime.fromisoformat(raw)
        except ValueError as error:
            raise PromotionError("Enter valid campaign dates.") from error
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    starts_at = parse_datetime(form.get("starts_at"), fallback=datetime.now(UTC))
    expires_at = parse_datetime(form.get("expires_at"))
    if expires_at is not None and expires_at <= starts_at:
        raise PromotionError("Campaign end must be after its start.")

    usage_text = str(form.get("usage_limit", "")).strip()
    try:
        usage_limit = int(usage_text) if usage_text else None
    except ValueError as error:
        raise PromotionError("Usage limit must be a positive whole number.") from error
    if usage_limit is not None and usage_limit < 1:
        raise PromotionError("Usage limit must be a positive whole number.")

    return {
        "seller_id": seller_id,
        "campaign_type": "seller_deal" if seller_id is not None else "coupon",
        "code": code,
        "name": name,
        "description": description,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "minimum_order_amount": minimum,
        "max_discount_amount": maximum,
        "starts_at": starts_at,
        "expires_at": expires_at,
        "usage_limit": usage_limit,
        "is_active": True,
    }
