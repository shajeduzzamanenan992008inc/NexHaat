"""Read-only security intelligence tools, reachable only via the numeric allowlist."""

from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import AuditEvent, AuthThrottle
from ..services.ai_rate_limit import consume_ai_request
from .core.permissions import AI_SCOPE_SECURITY
from .core.provider import AIService
from .core.tools import ToolRegistry


ADMIN_ROLES = ("admin", "super_admin", "support")
LOGIN_ACTIONS = ("auth.login", "auth.admin_login", "auth.admin_login_denied")
ALERT_ACTIONS = ("auth.admin_login_denied", "account.delete_self", "account.remove")


def _authorized(user):
    user_id = getattr(user, "telegram_id", None)
    allowed = {
        int(value.strip()) for value in (current_app.config.get("TELEGRAM_SECURITY_ADMIN_IDS", "") or "").split(",")
        if value.strip().isascii() and value.strip().isdigit() and int(value.strip()) > 0
    }
    if not getattr(user, "security_authorized", False) or user_id not in allowed:
        raise ValueError("Security scope is not authorized.")


def get_security_summary_tool(user=None, **_kwargs):
    _authorized(user)
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    denied = db.session.scalar(select(func.count(AuditEvent.id)).where(
        AuditEvent.action == "auth.admin_login_denied", AuditEvent.created_at >= since
    )) or 0
    failed = db.session.scalar(select(func.count(AuditEvent.id)).where(
        AuditEvent.action.in_(LOGIN_ACTIONS), AuditEvent.created_at >= since
    )) or 0
    blocked = db.session.scalar(select(func.count(AuthThrottle.key_hash)).where(
        AuthThrottle.blocked_until > now
    )) or 0
    admin_activity = db.session.scalar(select(func.count(AuditEvent.id)).where(
        AuditEvent.actor_role.in_(ADMIN_ROLES), AuditEvent.created_at >= since
    )) or 0
    risk = "high" if denied >= 10 else "attention" if denied >= 3 or blocked else "not elevated"
    return {"window_hours": 24, "denied_admin_signins": int(denied),
            "recorded_login_events": int(failed), "blocked_sources": int(blocked),
            "admin_activity_events": int(admin_activity),
            "unusual_admin_activity": "review" if admin_activity >= 50 else "no volume threshold reached",
            "risk_indicator": risk, "as_of": now.isoformat()}


def get_security_events_tool(user=None, category="all", limit=10, **_kwargs):
    _authorized(user)
    if category not in {"all", "login", "alert", "admin"}:
        raise ValueError("Choose a valid security event category.")
    limit = max(1, min(int(limit), 20))
    statement = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if category == "login":
        statement = statement.where(AuditEvent.action.in_(LOGIN_ACTIONS))
    elif category == "alert":
        statement = statement.where(AuditEvent.action.in_(ALERT_ACTIONS))
    elif category == "admin":
        statement = statement.where(AuditEvent.actor_role.in_(ADMIN_ROLES))
    events = db.session.scalars(statement.limit(limit)).all()
    # Deliberately omit actor email, target id, details, and IP hashes.
    return [{"time": item.created_at.isoformat(), "action": item.action,
             "actor_role": item.actor_role or "unknown"} for item in events]


def get_system_health_tool(user=None, **_kwargs):
    _authorized(user)
    try:
        db.session.execute(text("SELECT 1"))
        database = "healthy"
    except SQLAlchemyError:
        db.session.rollback()
        database = "unavailable"
    return {
        "application": "healthy" if database == "healthy" else "degraded",
        "database": database,
        "ai_enabled": bool(
            current_app.config.get("AI_ENABLED") or (
                current_app.config.get("AI_LOCAL_ENABLED")
                and current_app.config.get("AI_LOCAL_BASE_URL")
                and current_app.config.get("AI_LOCAL_MODEL")
            )
        ),
        "customer_bot_configured": bool(current_app.config.get("TELEGRAM_CUSTOMER_BOT_TOKEN")),
        "security_bot_configured": bool(current_app.config.get("TELEGRAM_SECURITY_BOT_TOKEN")),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def get_failed_login_analysis_tool(user=None, hours=24, **_kwargs):
    _authorized(user)
    hours = max(1, min(int(hours), 168))
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    counts = db.session.execute(
        select(AuditEvent.action, func.count(AuditEvent.id))
        .where(AuditEvent.action.in_(LOGIN_ACTIONS), AuditEvent.created_at >= since)
        .group_by(AuditEvent.action)
    ).all()
    blocked = db.session.scalar(select(func.count(AuthThrottle.key_hash)).where(
        AuthThrottle.blocked_until > datetime.now(timezone.utc)
    )) or 0
    return {"window_hours": hours, "events_by_action": {str(action): int(count) for action, count in counts},
            "currently_blocked_sources": int(blocked)}


def get_alert_priorities_tool(user=None, hours=24, **_kwargs):
    """Apply transparent read-only thresholds to recent audit event categories."""
    _authorized(user)
    hours = max(1, min(int(hours), 168))
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = db.session.execute(
        select(AuditEvent.action, func.count(AuditEvent.id))
        .where(AuditEvent.created_at >= since,
               AuditEvent.action.in_(ALERT_ACTIONS))
        .group_by(AuditEvent.action)
    ).all()
    counts = {str(action): int(count) for action, count in rows}
    denied = counts.get("auth.admin_login_denied", 0)
    deletion = counts.get("account.delete_self", 0) + counts.get("account.remove", 0)
    priority = "high" if denied >= 10 else "review" if denied >= 3 or deletion >= 5 else "normal"
    return {"window_hours": hours, "priority": priority,
            "counts_by_action": counts,
            "method": "Fixed thresholds over recorded events; not an automated incident determination."}


def build_security_tool_registry(max_tool_calls=5):
    registry = ToolRegistry(max_calls=max_tool_calls)
    registry.register("get_security_summary", get_security_summary_tool,
                      scope=AI_SCOPE_SECURITY, description="Summarize recorded login risk and current blocks.")
    registry.register("get_security_events", get_security_events_tool,
                      scope=AI_SCOPE_SECURITY, description="List redacted security event metadata.",
                      parameters={"type": "object", "properties": {
                          "category": {"type": "string", "enum": ["all", "login", "alert", "admin"]},
                          "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                      }, "additionalProperties": False})
    registry.register("get_system_health", get_system_health_tool,
                      scope=AI_SCOPE_SECURITY, description="Read application and database health only.")
    registry.register("get_failed_login_analysis", get_failed_login_analysis_tool,
                      scope=AI_SCOPE_SECURITY, description="Aggregate failed login events over a bounded time window.",
                      parameters={"type": "object", "properties": {"hours": {"type": "integer", "minimum": 1, "maximum": 168}}, "additionalProperties": False})
    registry.register("get_alert_priorities", get_alert_priorities_tool,
                      scope=AI_SCOPE_SECURITY,
                      description="Prioritize recorded security alert counts using fixed transparent thresholds; read-only.",
                      parameters={"type": "object", "properties": {
                          "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                      }, "additionalProperties": False})
    return registry


def handle_security_ai_query(prompt, *, telegram_user_id, private_chat=True):
    allowed = {
        int(value.strip()) for value in (current_app.config.get("TELEGRAM_SECURITY_ADMIN_IDS", "") or "").split(",")
        if value.strip().isascii() and value.strip().isdigit() and int(value.strip()) > 0
    }
    if not private_chat or telegram_user_id not in allowed:
        return {"ok": False, "answer": "Access denied.", "scope": AI_SCOPE_SECURITY, "tools_used": []}
    try:
        if not consume_ai_request(AI_SCOPE_SECURITY, principal=f"telegram:{telegram_user_id}"):
            return {"ok": False, "answer": "Security assistant request limit reached. Use /help for read-only commands.", "scope": AI_SCOPE_SECURITY, "tools_used": []}
    except Exception:
        db.session.rollback()
        return {"ok": False, "answer": "Security assistant data is temporarily unavailable.", "scope": AI_SCOPE_SECURITY, "tools_used": []}
    actor = type("AuthorizedSecurityPrincipal", (), {
        "security_authorized": True, "telegram_id": telegram_user_id,
    })()
    service = AIService(current_app.config)
    registry = build_security_tool_registry(service.max_tool_calls)
    result = service.respond(prompt, scope=AI_SCOPE_SECURITY, user=actor, tools=registry,
                             context={"channel": "telegram"})
    if result.get("ok") and (result.get("tool_results") or
                              current_app.config.get("AI_LOCAL_BASE_URL")):
        return result
    # Disabled-provider fallback remains deterministic and read-only.
    lowered = str(prompt or "").lower()
    security_data_request = any(word in lowered for word in (
        "priority", "prioritize", "alert", "health", "status", "login", "failed", "suspicious",
        "audit", "security", "অগ্রাধিকার", "সতর্কতা", "স্বাস্থ্য", "সিস্টেম", "লগইন", "সন্দেহজনক",
    ))
    if not security_data_request:
        return {"ok": False, "scope": AI_SCOPE_SECURITY,
                "answer": "The private local AI endpoint is not connected. Read-only security commands remain available.",
                "tools_used": []}
    if any(word in lowered for word in ("priority", "prioritize", "alert", "অগ্রাধিকার", "সতর্কতা")):
        name = "get_alert_priorities"
    elif any(word in lowered for word in ("health", "status", "স্বাস্থ্য", "সিস্টেম")):
        name = "get_system_health"
    elif any(word in lowered for word in ("login", "failed", "suspicious", "লগইন", "সন্দেহজনক")):
        name = "get_failed_login_analysis"
    else:
        name = "get_security_summary"
    data = registry.call(name, scope=AI_SCOPE_SECURITY, user=actor)
    return {"ok": bool(data.get("ok")), "scope": AI_SCOPE_SECURITY,
            "answer": f"Security summary (verified data): {data.get('result', data.get('error', 'unavailable'))}",
            "tools_used": [name]}
