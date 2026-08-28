from __future__ import annotations

from typing import Any

from flask import g, request


def request_context() -> dict[str, Any]:
    user = getattr(g, "current_user", None)
    return {
        "request_id": getattr(g, "request_id", None),
        "user_id": str(user.id) if getattr(user, "id", None) is not None else None,
        "route": request.endpoint if request else None,
        "method": request.method if request else None,
        "remote_ip": getattr(g, "client_ip", None),
    }
