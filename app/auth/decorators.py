from functools import wraps
from typing import Any, Callable

from flask import g, request

from app.auth.jwt import TokenError, decode_access_token
from app.repositories.user_repository import get_by_id
from app.permissions.moderation_permissions import is_restricted
from app.utils.responses import error_response


def auth_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return error_response("AUTHENTICATION_REQUIRED", "Authentication is required", 401)
        try:
            user_id = decode_access_token(token.strip())
        except TokenError:
            return error_response("INVALID_TOKEN", "Invalid or expired access token", 401)

        user = get_by_id(user_id)
        if user is None:
            return error_response("INVALID_TOKEN", "Invalid or expired access token", 401)

        is_active = getattr(user, "is_active", True)
        status = getattr(user, "status", "active")
        if not is_active or status != "active":
            return error_response("ACCOUNT_INACTIVE", "Account is inactive", 403)
        if is_restricted(user):
            return error_response("ACCOUNT_RESTRICTED", "Account is suspended or banned", 403)
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped
