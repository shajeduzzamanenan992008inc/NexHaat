"""Optional self-hosted SearXNG lookup with strict result-link validation."""

import ipaddress
from urllib.parse import urlsplit

import requests
from flask import current_app


def _public_http_url(value):
    try:
        parsed = urlsplit(str(value or ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return False
        except ValueError:
            pass
        return True
    except (TypeError, ValueError):
        return False


def needs_live_sources(prompt):
    text = str(prompt or "").lower()
    return any(term in text for term in (
        "latest", "today", "right now", "current news", "current price", "live link", "source link",
        "recent update", "latest version", "link dao", "source dao", "ajker", "ekhon",
        "আজকের", "এখনকার", "সাম্প্রতিক", "বর্তমান খবর", "লিংক দাও", "সূত্র দাও",
        "नवीनतम", "आज", "अभी", "वर्तमान समाचार", "आज का", "अभी का", "लिंक दो", "स्रोत लिंक",
    ))


def search_public_web(prompt):
    base = str(current_app.config.get("AI_SEARCH_BASE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(base)
    if not base or not parsed.hostname or parsed.username or parsed.password:
        return []
    if current_app.config.get("ENVIRONMENT") == "production" and parsed.scheme != "https":
        return []
    try:
        response = requests.get(f"{base}/search", params={"q": str(prompt)[:500], "format": "json"}, timeout=8)
        response.raise_for_status()
        results = response.json().get("results", [])
        output = []
        for item in results if isinstance(results, list) else []:
            if not isinstance(item, dict) or not _public_http_url(item.get("url")):
                continue
            output.append({"title": str(item.get("title") or "Source")[:160],
                           "url": str(item["url"])[:1000],
                           "snippet": str(item.get("content") or "")[:500]})
            if len(output) >= 5:
                break
        return output
    except (requests.RequestException, ValueError, AttributeError, TypeError):
        return []
