"""AI scopes and authorization checks."""

AI_SCOPE_CUSTOMER = "customer_ai"
AI_SCOPE_SELLER = "seller_ai"
AI_SCOPE_ADMIN = "admin_ai"
AI_SCOPE_SECURITY = "security_ai"
AI_SCOPE_RIDER = "rider_ai"

_SCOPE_MATRIX = {
    AI_SCOPE_CUSTOMER: {AI_SCOPE_CUSTOMER},
    AI_SCOPE_SELLER: {AI_SCOPE_SELLER},
    AI_SCOPE_ADMIN: {AI_SCOPE_ADMIN},
    AI_SCOPE_SECURITY: {AI_SCOPE_SECURITY},
    AI_SCOPE_RIDER: {AI_SCOPE_RIDER},
}


def has_ai_scope(scope, required_scope):
    """Return True when the caller is allowed to use the requested AI scope."""
    if not scope or not required_scope:
        return False
    allowed = _SCOPE_MATRIX.get(scope, set())
    return required_scope in allowed
