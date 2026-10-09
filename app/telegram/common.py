import hmac
import logging
import time
from io import BytesIO
from urllib.parse import quote, urlsplit
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app, jsonify
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import ProcessedTelegramUpdate, TelegramRateLimit

logger = logging.getLogger(__name__)
PROCESSING_RETRY_AFTER = timedelta(minutes=2)


def credentials_ready(bot_name):
    prefix = f"TELEGRAM_{bot_name.upper()}"
    return bool(
        current_app.config.get(f"{prefix}_BOT_TOKEN")
        and current_app.config.get(f"{prefix}_WEBHOOK_SECRET")
    )


def valid_webhook_secret(bot_name, supplied):
    expected = current_app.config.get(f"TELEGRAM_{bot_name.upper()}_WEBHOOK_SECRET", "")
    return bool(
        expected and supplied and len(supplied) <= 256
        and hmac.compare_digest(expected, supplied)
    )


def _claim_update(bot_name, update_id):
    now = datetime.now(timezone.utc)
    record = db.session.scalar(
        select(ProcessedTelegramUpdate).where(
            ProcessedTelegramUpdate.bot_name == bot_name,
            ProcessedTelegramUpdate.update_id == update_id,
        )
    )
    if record is None:
        record = ProcessedTelegramUpdate(
            bot_name=bot_name,
            update_id=update_id,
            state="processing",
            attempts=1,
            received_at=now,
            updated_at=now,
        )
        db.session.add(record)
        try:
            db.session.commit()
            return True
        except IntegrityError:
            db.session.rollback()
            record = db.session.scalar(
                select(ProcessedTelegramUpdate).where(
                    ProcessedTelegramUpdate.bot_name == bot_name,
                    ProcessedTelegramUpdate.update_id == update_id,
                )
            )
            if record is None:
                raise

    updated_at = record.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if record.state == "processed":
        return False
    if record.state == "processing" and now - updated_at < PROCESSING_RETRY_AFTER:
        return False
    record.state = "processing"
    record.attempts += 1
    record.updated_at = now
    db.session.commit()
    return True


def _finish_update(bot_name, update_id, succeeded):
    record = db.session.scalar(
        select(ProcessedTelegramUpdate).where(
            ProcessedTelegramUpdate.bot_name == bot_name,
            ProcessedTelegramUpdate.update_id == update_id,
        )
    )
    if record is not None:
        record.state = "processed" if succeeded else "failed"
        record.updated_at = datetime.now(timezone.utc)
        db.session.commit()


def _within_rate_limit(bot_name, telegram_user_id):
    secret = current_app.secret_key
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    telegram_user_hash = hmac.new(
        secret, f"{bot_name}:{telegram_user_id}".encode("ascii"), "sha256"
    ).hexdigest()
    now = int(time.time())
    cutoff = now - 60
    values = {
        "bot_name": bot_name,
        "telegram_user_hash": telegram_user_hash,
        "window_started_at": now,
        "request_count": 1,
    }
    expired_window = TelegramRateLimit.window_started_at <= cutoff
    updates = {
        "window_started_at": case(
            (expired_window, now), else_=TelegramRateLimit.window_started_at
        ),
        "request_count": case(
            (expired_window, 1), else_=TelegramRateLimit.request_count + 1
        ),
    }
    dialect = db.session.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(TelegramRateLimit).values(**values).on_conflict_do_update(
            index_elements=["bot_name", "telegram_user_hash"], set_=updates
        )
    elif dialect == "postgresql":
        statement = postgres_insert(TelegramRateLimit).values(**values).on_conflict_do_update(
            index_elements=["bot_name", "telegram_user_hash"], set_=updates
        )
    else:
        return True, False
    db.session.execute(statement)
    db.session.commit()
    count = db.session.scalar(
        select(TelegramRateLimit.request_count).where(
            TelegramRateLimit.bot_name == bot_name,
            TelegramRateLimit.telegram_user_hash == telegram_user_hash,
        )
    )
    setting = (
        "TELEGRAM_SECURITY_RATE_LIMIT_PER_MINUTE"
        if bot_name == "security"
        else "TELEGRAM_RATE_LIMIT_PER_MINUTE"
    )
    default = 10 if bot_name == "security" else 30
    limit = max(1, int(current_app.config.get(setting, default)))
    return bool(count and count <= limit), count == limit + 1


def send_message(bot_name, chat_id, text, reply_markup=None):
    token = current_app.config.get(f"TELEGRAM_{bot_name.upper()}_BOT_TOKEN")
    if not token or not isinstance(text, str) or not text:
        return False
    payload = {"chat_id": chat_id, "text": text[:4096]}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=max(1, int(current_app.config.get("TELEGRAM_API_TIMEOUT", 10))),
        )
        if response.status_code != 200:
            logger.warning("Telegram %s bot send failed (HTTP %s).", bot_name, response.status_code)
            return False
        result = response.json()
        if not isinstance(result, dict) or result.get("ok") is not True:
            logger.warning("Telegram %s bot rejected a send request.", bot_name)
            return False
        return True
    except (requests.RequestException, ValueError) as error:
        logger.warning("Telegram %s bot request failed (%s).", bot_name, type(error).__name__)
        return False


def synthesize_local_speech(text):
    config = current_app.config
    base_url = str(config.get("AI_TTS_BASE_URL") or "").strip().rstrip("/")
    model = str(config.get("AI_TTS_MODEL") or "").strip()
    parsed = urlsplit(base_url)
    if (not text or len(text) > 1200 or not model or not parsed.hostname
            or parsed.scheme not in {"https", "http"} or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or config.get("ENVIRONMENT") == "production" and parsed.scheme != "https"):
        return None
    headers = {"Content-Type": "application/json"}
    key = str(config.get("AI_LOCAL_API_KEY") or "").strip()
    if key:
        headers["Authorization"] = "Bearer " + key
    try:
        response = requests.post(
            f"{base_url}/audio/speech",
            json={"model": model, "input": text, "voice": str(config.get("AI_TTS_VOICE") or "default"),
                  "response_format": "wav"},
            headers=headers, timeout=min(45, max(1, int(config.get("AI_TIMEOUT", 15))) * 2),
            stream=True,
        )
        try:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if chunk:
                    if len(content) + len(chunk) > 10 * 1024 * 1024:
                        return None
                    content.extend(chunk)
            content_type = response.headers.get("Content-Type", "audio/wav").split(";", 1)[0]
            if not content or content_type not in {"audio/wav", "audio/x-wav", "audio/mpeg",
                                                     "audio/mp4", "audio/ogg", "audio/webm"}:
                return None
            return bytes(content), content_type
        finally:
            response.close()
    except (requests.RequestException, TypeError, ValueError, AttributeError) as error:
        logger.warning("Telegram local speech synthesis failed (%s).", type(error).__name__)
        return None


def send_voice(bot_name, chat_id, audio, content_type="audio/wav"):
    token = current_app.config.get(f"TELEGRAM_{bot_name.upper()}_BOT_TOKEN")
    extensions = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
                  "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/webm": "webm"}
    if not token or not isinstance(audio, bytes) or not audio or len(audio) > 10 * 1024 * 1024:
        return False
    extension = extensions.get(content_type)
    if extension is None:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendVoice",
            data={"chat_id": chat_id},
            files={"voice": (f"answer.{extension}", BytesIO(audio), content_type)},
            timeout=max(1, int(current_app.config.get("TELEGRAM_API_TIMEOUT", 10))),
        )
        if response.status_code != 200:
            logger.warning("Telegram %s voice send failed (HTTP %s).", bot_name, response.status_code)
            return False
        result = response.json()
        return isinstance(result, dict) and result.get("ok") is True
    except (requests.RequestException, ValueError) as error:
        logger.warning("Telegram %s voice send failed (%s).", bot_name, type(error).__name__)
        return False


def download_telegram_file(bot_name, file_id, *, max_bytes=8 * 1024 * 1024):
    token = current_app.config.get(f"TELEGRAM_{bot_name.upper()}_BOT_TOKEN")
    if not token or not isinstance(file_id, str) or not file_id or len(file_id) > 512:
        return None
    timeout = max(1, int(current_app.config.get("TELEGRAM_API_TIMEOUT", 10)))
    try:
        metadata_response = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id}, timeout=timeout,
        )
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        file_path = metadata.get("result", {}).get("file_path") if metadata.get("ok") is True else None
        if (not isinstance(file_path, str) or not file_path or len(file_path) > 1024
                or ".." in file_path.split("/")
            or any(not part or not all(char.isascii() and (char.isalnum() or char in "._-")
                           for char in part)
                   for part in file_path.split("/"))):
            return None
        response = requests.get(
            f"https://api.telegram.org/file/bot{token}/{quote(file_path, safe='/._-')}",
            timeout=timeout, stream=True, allow_redirects=False,
        )
        try:
            response.raise_for_status()
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                return None
            content = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if chunk:
                    if len(content) + len(chunk) > max_bytes:
                        return None
                    content.extend(chunk)
            return bytes(content) if content else None
        finally:
            response.close()
    except (requests.RequestException, TypeError, ValueError, AttributeError) as error:
        logger.warning("Telegram %s file download failed (%s).", bot_name, type(error).__name__)
        return None


def answer_callback(bot_name, callback_id, text=""):
    token = current_app.config.get(f"TELEGRAM_{bot_name.upper()}_BOT_TOKEN")
    if not token or not callback_id:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text[:200]},
            timeout=max(1, int(current_app.config.get("TELEGRAM_API_TIMEOUT", 10))),
        )
        result = response.json()
        return response.status_code == 200 and isinstance(result, dict) and result.get("ok") is True
    except (requests.RequestException, ValueError) as error:
        logger.warning("Telegram %s callback response failed (%s).", bot_name, type(error).__name__)
        return False


def receive_update(bot_name, handler):
    payload = current_app_json()
    update_id = payload.get("update_id") if isinstance(payload, dict) else None
    if isinstance(update_id, bool) or not isinstance(update_id, int) or update_id < 0:
        return jsonify(ok=False), 400

    callback = payload.get("callback_query")
    if isinstance(callback, dict):
        message = callback.get("message")
        sender = callback.get("from")
    else:
        message = payload.get("message") or payload.get("edited_message")
        sender = message.get("from") if isinstance(message, dict) else None
    if not isinstance(message, dict):
        return jsonify(ok=True), 200
    chat = message.get("chat")
    telegram_user_id = sender.get("id") if isinstance(sender, dict) else None
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    if (
        isinstance(telegram_user_id, bool) or not isinstance(telegram_user_id, int)
        or telegram_user_id <= 0 or isinstance(chat_id, bool) or not isinstance(chat_id, int)
    ):
        return jsonify(ok=False), 400

    try:
        if not _claim_update(bot_name, update_id):
            return jsonify(ok=True, duplicate=True), 200
        allowed, notify_rate_limit = _within_rate_limit(bot_name, telegram_user_id)
        if not allowed:
            if notify_rate_limit:
                send_message(
                    bot_name,
                    chat_id,
                    "Too many requests. Please wait a minute before trying again.",
                )
            _finish_update(bot_name, update_id, True)
            return jsonify(ok=True), 200
        succeeded = bool(handler(payload, telegram_user_id, chat_id))
        _finish_update(bot_name, update_id, succeeded)
        return (jsonify(ok=True), 200) if succeeded else (jsonify(ok=False), 503)
    except Exception as error:  # noqa: BLE001 - never expose Telegram or database internals
        db.session.rollback()
        logger.warning("Telegram %s update failed (%s).", bot_name, type(error).__name__)
        try:
            _finish_update(bot_name, update_id, False)
        except Exception:  # noqa: BLE001 - the webhook still returns a generic retry response
            db.session.rollback()
        return jsonify(ok=False), 503


def current_app_json():
    from flask import request

    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}
