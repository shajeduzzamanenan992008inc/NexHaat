"""Small server-side SSLCOMMERZ hosted-checkout client."""

from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import requests
from flask import current_app, url_for


class SSLCOMMERZError(RuntimeError):
    """A safe payment-provider error with no credential or response leakage."""


def gateway_is_configured():
    config = current_app.config
    public_url = urlsplit((config.get("PUBLIC_BASE_URL") or "").strip())
    production_https = (
        config.get("ENVIRONMENT") != "production" or public_url.scheme == "https"
    )
    return bool(
        config.get("SSLCOMMERZ_STORE_ID")
        and config.get("SSLCOMMERZ_STORE_PASSWORD")
        and public_url.scheme in {"http", "https"}
        and public_url.hostname
        and production_https
    )


def _root():
    return (
        "https://sandbox.sslcommerz.com"
        if current_app.config.get("SSLCOMMERZ_SANDBOX", True)
        else "https://securepay.sslcommerz.com"
    )


def _credentials():
    store_id = current_app.config.get("SSLCOMMERZ_STORE_ID") or ""
    store_password = current_app.config.get("SSLCOMMERZ_STORE_PASSWORD") or ""
    if not store_id or not store_password:
        raise SSLCOMMERZError("Online payment is not configured.")
    return store_id, store_password


def _request(method, url, *, params=None, data=None):
    try:
        response = requests.request(
            method,
            url,
            params=params,
            data=data,
            timeout=max(2, int(current_app.config.get("SSLCOMMERZ_TIMEOUT", 12))),
            allow_redirects=False,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as error:
        raise SSLCOMMERZError("The payment service could not be reached. Please retry.") from error
    if not isinstance(result, dict):
        raise SSLCOMMERZError("The payment service returned an invalid response.")
    return result


def _callback_url(endpoint):
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base:
        raise SSLCOMMERZError("A public callback URL is not configured.")
    return f"{base}{url_for(endpoint)}"


def create_hosted_session(payment, attempt, order):
    store_id, store_password = _credentials()
    payload = {
        "store_id": store_id,
        "store_passwd": store_password,
        "total_amount": f"{payment.amount:.2f}",
        "currency": payment.currency,
        "tran_id": attempt.transaction_id,
        "success_url": _callback_url("orders.sslcommerz_success"),
        "fail_url": _callback_url("orders.sslcommerz_return"),
        "cancel_url": _callback_url("orders.sslcommerz_return"),
        "ipn_url": _callback_url("orders.sslcommerz_ipn"),
        "cus_name": order.customer_name[:120],
        "cus_email": (order.email or "")[:100],
        "cus_add1": order.address[:100],
        "cus_city": (order.city or "")[:50],
        "cus_country": "Bangladesh",
        "cus_phone": order.phone[:20],
        "shipping_method": "NO",
        "product_name": "NexHaat marketplace order",
        "product_category": "Marketplace",
        "product_profile": "general",
        "value_a": payment.checkout_group,
    }
    result = _request("POST", f"{_root()}/gwprocess/v4/api.php", data=payload)
    gateway_url = result.get("GatewayPageURL")
    parsed = urlsplit(gateway_url or "")
    allowed_hosts = (
        {"sandbox.sslcommerz.com"}
        if current_app.config.get("SSLCOMMERZ_SANDBOX", True)
        else {"securepay.sslcommerz.com"}
    )
    if (
        result.get("status") != "SUCCESS"
        or not result.get("sessionkey")
        or parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
    ):
        raise SSLCOMMERZError("The payment service could not start checkout. Please retry.")
    return result["sessionkey"][:80], gateway_url


def validate_transaction(validation_id):
    store_id, store_password = _credentials()
    if not validation_id or len(validation_id) > 50:
        raise SSLCOMMERZError("The payment notification is incomplete.")
    return _request(
        "GET",
        f"{_root()}/validator/api/validationserverAPI.php",
        params={
            "val_id": validation_id,
            "store_id": store_id,
            "store_passwd": store_password,
            "format": "json",
        },
    )


def initiate_refund(bank_tran_id, refund_trans_id, amount, reason, order_number):
    store_id, store_password = _credentials()
    return _request(
        "GET",
        f"{_root()}/validator/api/merchantTransIDvalidationAPI.php",
        params={
            "bank_tran_id": bank_tran_id,
            "refund_trans_id": refund_trans_id,
            "refund_amount": f"{amount:.2f}",
            "refund_remarks": reason[:255],
            "refe_id": order_number[:50],
            "store_id": store_id,
            "store_passwd": store_password,
            "format": "json",
        },
    )


def query_refund(refund_ref_id):
    store_id, store_password = _credentials()
    return _request(
        "GET",
        f"{_root()}/validator/api/merchantTransIDvalidationAPI.php",
        params={
            "refund_ref_id": refund_ref_id,
            "store_id": store_id,
            "store_passwd": store_password,
            "format": "json",
        },
    )


def query_transaction(transaction_id):
    store_id, store_password = _credentials()
    return _request(
        "GET",
        f"{_root()}/validator/api/merchantTransIDvalidationAPI.php",
        params={
            "tran_id": transaction_id,
            "store_id": store_id,
            "store_passwd": store_password,
            "format": "json",
        },
    )


def normalized_decimal(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount.is_finite() else None
