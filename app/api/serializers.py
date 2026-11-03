"""Model-to-dict serializers shared by the versioned REST API."""

from flask import has_request_context
from flask_babel import get_locale

DEFAULT_LOCALE = "en_US"


def _current_locale():
    if has_request_context():
        return str(get_locale() or DEFAULT_LOCALE).replace("-", "_")
    return DEFAULT_LOCALE


def _money(value):
    # Return money as a fixed-precision string so JSON never loses cents.
    return None if value is None else f"{value:.2f}"


def _iso(value):
    return value.isoformat() if value is not None else None


def _product_sku(product):
    return next((variant.sku for variant in product.variants if variant.is_active), None)


def category_to_dict(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "image": category.image,
        "display_image": category.display_image,
        "is_active": category.is_active,
    }


def product_to_dict(product, locale=None):
    locale = locale or _current_locale()
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "brand_name": product.brand_name,
        "localized_name": product.localized_name(locale),
        "localized_description": product.localized_description(locale),
        "source_language": product.original_locale,
        "price": _money(product.price),
        "discount_price": _money(product.discount_price),
        "display_price": _money(product.display_price),
        "stock": product.available_stock,
        "sku": _product_sku(product),
        "variants": [
            {
                "id": variant.id,
                "sku": variant.sku,
                "option_name": variant.option_name,
                "option_value": variant.option_value,
                "price": _money(variant.price if variant.price is not None else product.display_price),
                "stock": variant.stock_quantity,
            }
            for variant in product.variants if variant.is_active
        ],
        "image": product.image,
        # Mirrors the website's product.display_image so clients render the same
        # category artwork when a seller has not uploaded a photo.
        "display_image": product.display_image,
        "is_available": product.is_available,
        "is_featured": product.is_featured,
        "moderation_status": product.moderation_status,
        "category_id": product.category_id,
        "seller_id": product.seller_id,
        "created_at": _iso(product.created_at),
        "updated_at": _iso(product.updated_at),
    }


def order_item_to_dict(item):
    return {
        "id": item.id,
        "product_id": item.product_id,
        "variant_id": item.variant_id,
        "name": item.product_name,
        "variant_label": item.variant_label,
        "sku": item.sku_snapshot,
        "price": _money(item.price),
        "quantity": item.quantity,
        "subtotal": _money(item.subtotal),
    }


def order_to_dict(order):
    return_request = order.return_request
    return_refund = next(
        (refund for refund in order.payment.refunds if refund.order_id == order.id),
        None,
    ) if order.payment and return_request else None
    return {
        "id": order.id,
        "order_number": order.order_number,
        "checkout_group": order.checkout_group,
        "status": order.status,
        "delivery_status": order.delivery_status,
        "payment_method": order.payment_method,
        "payment_status": order.payment.status if order.payment else None,
        "customer_name": order.customer_name,
        "phone": order.phone,
        "email": order.email,
        "address": order.address,
        "total": _money(order.total),
        "delivery_fee": _money(order.delivery_fee),
        "discount_amount": _money(order.discount_amount),
        "promotion_code": order.promotion_code,
        "items_subtotal": _money(order.items_subtotal),
        "return_deadline": _iso(order.return_deadline),
        "return_eligible": order.is_return_eligible,
        "return_request": ({
            "id": return_request.id,
            "status": return_request.status,
            "reason": return_request.reason,
            "refund_amount": _money(return_request.refund_amount),
            "refund_status": return_refund.status if return_refund else None,
            "review_note": return_request.review_note,
            "provider_refund_id": return_request.provider_refund_id,
            "manual_refund_reference": return_request.manual_refund_reference,
            "created_at": _iso(return_request.created_at),
            "reviewed_at": _iso(return_request.reviewed_at),
            "resolved_at": _iso(return_request.resolved_at),
        } if return_request else None),
        "seller_id": order.seller_id,
        "rider_id": order.rider_id,
        "created_at": _iso(order.created_at),
        "items": [order_item_to_dict(item) for item in order.items],
    }


def order_event_to_dict(event):
    """Serialize one timeline entry without exposing actor identifiers."""
    return {
        "id": event.id,
        "event_type": event.event_type,
        "previous_status": event.previous_status,
        "new_status": event.new_status,
        "actor_role": event.actor_role,
        "description": event.description,
        "tracking_reference": event.tracking_reference,
        "carrier": event.carrier,
        "estimated_delivery_at": _iso(event.estimated_delivery_at),
        "created_at": _iso(event.created_at),
    }


def review_to_dict(review):
    return {
        "id": review.id,
        "product_id": review.product_id,
        "rating": review.rating,
        "comment": review.comment,
        "author_name": review.author_name,
        "status": review.status,
        "created_at": _iso(review.created_at),
    }


def notification_to_dict(notification):
    return {
        "id": notification.id,
        "type": notification.type,
        "message": notification.message,
        "link": notification.link,
        "is_read": notification.is_read,
        "created_at": _iso(notification.created_at),
    }


def banner_to_dict(banner):
    return {
        "id": banner.id,
        "title": banner.title,
        "subtitle": banner.subtitle,
        "image_url": banner.display_image,
        "link_url": banner.link_url,
        "link_type": banner.link_type,
        "is_active": banner.is_active,
        "display_order": banner.display_order,
    }


def user_to_dict(user):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "preferred_locale": user.preferred_locale,
        "is_totp_enabled": bool(getattr(user, "is_totp_enabled", False)),
    }

