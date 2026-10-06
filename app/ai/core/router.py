"""Simple router that chooses an AI scope based on the caller context."""

from .permissions import AI_SCOPE_ADMIN, AI_SCOPE_CUSTOMER, AI_SCOPE_SECURITY, AI_SCOPE_SELLER


def route_ai_request(user=None, *, is_security=False, is_admin=False, is_seller=False):
    if is_security or user is not None and getattr(user, "role", None) == "support":
        return AI_SCOPE_SECURITY
    if is_admin or user is not None and getattr(user, "role", None) == "admin":
        return AI_SCOPE_ADMIN
    if is_seller or user is not None and getattr(user, "role", None) == "seller":
        return AI_SCOPE_SELLER
    return AI_SCOPE_CUSTOMER
