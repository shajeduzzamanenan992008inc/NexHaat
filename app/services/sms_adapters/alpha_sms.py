"""Alpha SMS (sms.bd) adapter.

API verified from official docs: https://sms.bd/api
Endpoint: https://api.sms.net.bd/sendsms
Auth: api_key parameter
"""

import logging

import requests
from flask import current_app

from . import SmsAdapter, SmsErrorClass, SmsResult

logger = logging.getLogger(__name__)


class AlphaSmsAdapter(SmsAdapter):
    """Alpha SMS adapter for sms.bd."""

    SEND_ENDPOINT = "https://api.sms.net.bd/sendsms"
    REPORT_ENDPOINT = "https://api.sms.net.bd/report/request/{id}/"
    BALANCE_ENDPOINT = "https://api.sms.net.bd/user/balance/"

    def send(self, phone: str, message: str, sender_id: str | None = None) -> SmsResult:
        api_key = current_app.config.get("SMS_API_KEY") or ""
        if not api_key:
            return SmsResult(
                success=False,
                error_class=SmsErrorClass.CONFIG,
                error_message="SMS API key not configured",
            )

        timeout = int(current_app.config.get("SMS_TIMEOUT", 10))
        payload = {
            "api_key": api_key,
            "msg": message,
            "to": phone,
        }
        if sender_id:
            payload["sender_id"] = sender_id

        try:
            response = requests.post(self.SEND_ENDPOINT, data=payload, timeout=timeout)
        except requests.Timeout:
            return SmsResult(success=False, error_class=SmsErrorClass.TIMEOUT)
        except requests.RequestException:
            return SmsResult(success=False, error_class=SmsErrorClass.TRANSIENT)

        try:
            data = response.json()
        except ValueError:
            return SmsResult(success=False, error_class=SmsErrorClass.UNKNOWN)

        error_code = data.get("error")
        if error_code == 0:
            msg_data = data.get("data") or {}
            message_id = msg_data.get("request_id")
            if message_id is not None:
                message_id = str(message_id)
            return SmsResult(success=True, message_id=message_id)

        # Map error codes based on documented errors
        if error_code in (403, 405):
            return SmsResult(success=False, error_class=SmsErrorClass.AUTH)
        if error_code == 417:
            return SmsResult(success=False, error_class=SmsErrorClass.QUOTA)
        if error_code in (413,):
            return SmsResult(success=False, error_class=SmsErrorClass.AUTH)  # Invalid sender ID
        if error_code in (416,):
            return SmsResult(success=False, error_class=SmsErrorClass.INVALID_NUMBER)
        if error_code in (410, 411):
            return SmsResult(success=False, error_class=SmsErrorClass.AUTH)
        if error_code in (412, 414, 415, 420):
            return SmsResult(success=False, error_class=SmsErrorClass.UNKNOWN)
        return SmsResult(success=False, error_class=SmsErrorClass.UNKNOWN)
