from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from flask import current_app, g, request

from app.extensions.database import db
from app.models.rate_limit_bucket import RateLimitBucket
from app.repositories.security_repository import SecurityRepository


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    scope: str


def normalize_ip(value: str | None) -> str:
    if not value:
        return "unknown"
    candidate = value.strip().split(":", 1)[0] if value.count(":") == 1 and value.rsplit(":", 1)[1].isdigit() and "." in value else value.strip()
    try:
        ip_obj = ipaddress.ip_address(candidate)
    except ValueError:
        return "unknown"
    if ip_obj.version == 6 and ip_obj.ipv4_mapped is not None:
        return str(ip_obj.ipv4_mapped)
    return str(ip_obj)


def _bucket_key(scope: str, *, user_id: UUID | str | None = None, route: str | None = None, ip_address: str | None = None) -> str:
    if user_id is not None:
        return f"user:{user_id}"
    if route and ip_address:
        return f"route:{route}:ip:{ip_address}"
    if route:
        return f"route:{route}"
    if ip_address:
        return f"ip:{ip_address}"
    return "global"


def _window_start(now: datetime, window_seconds: int) -> datetime:
    epoch = now.astimezone(timezone.utc)
    bucket = epoch.replace(microsecond=0)
    return bucket


def _allowed_limit(scope: str, *, route: str | None = None) -> tuple[int, int]:
    config = current_app.config
    if scope == "AUTH":
        return config.get("AUTH_RATE_LIMIT_REQUESTS", 10), config.get("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)
    if scope == "SOCKET":
        return config.get("SOCKET_RATE_LIMIT_EVENTS", 60), config.get("SOCKET_RATE_LIMIT_WINDOW_SECONDS", 60)
    if scope == "ROUTE":
        route_limit = config.get("RATE_LIMIT_DEFAULT_REQUESTS", 120)
        return route_limit, config.get("RATE_LIMIT_DEFAULT_WINDOW_SECONDS", 60)
    return config.get("RATE_LIMIT_DEFAULT_REQUESTS", 120), config.get("RATE_LIMIT_DEFAULT_WINDOW_SECONDS", 60)


def check_rate_limit(*, key: str, scope: str, limit: int | None = None, window_seconds: int | None = None, user_id: UUID | str | None = None, route: str | None = None) -> RateLimitResult:
    if not current_app.config.get("RATE_LIMIT_ENABLED", True):
        return RateLimitResult(allowed=True, limit=limit or 0, remaining=limit or 0, reset_at=datetime.now(timezone.utc), scope=scope)

    limit_value = limit if limit is not None else _allowed_limit(scope, route=route)[0]
    window_value = window_seconds if window_seconds is not None else _allowed_limit(scope, route=route)[1]
    now = datetime.now(timezone.utc)
    window_start = _window_start(now, window_value)
    expires_at = window_start + timedelta(seconds=window_value)

    repo = SecurityRepository()
    bucket = repo.get_bucket(key=key, scope=scope, window_start=window_start)
    count = 1 if bucket is None else bucket.request_count + 1
    allowed = count <= limit_value
    if bucket is None:
        repo.add_rate_limit_event(key=key, scope=scope, window_start=window_start, request_count=count, expires_at=expires_at)
    else:
        bucket.request_count = count
        bucket.expires_at = expires_at
    db.session.commit()

    return RateLimitResult(
        allowed=allowed,
        limit=limit_value,
        remaining=max(0, limit_value - count),
        reset_at=expires_at,
        scope=scope,
    )


def check_socket_rate_limit(*, user_id: UUID | str | None = None, event: str, connection: str | None = None, route: str | None = None) -> RateLimitResult:
    key = _bucket_key("SOCKET", user_id=user_id, route=route, ip_address=getattr(g, "client_ip", None))
    return check_rate_limit(key=key, scope="SOCKET", limit=current_app.config.get("SOCKET_RATE_LIMIT_EVENTS", 60), window_seconds=current_app.config.get("SOCKET_RATE_LIMIT_WINDOW_SECONDS", 60), user_id=user_id, route=route)


def rate_limit(scope: str, *, limit: int | None = None, window_seconds: int | None = None, route: str | None = None, user_key: bool = True):
    def decorator(fn: Callable[..., Any]):
        def wrapped(*args: Any, **kwargs: Any):
            from app.utils.responses import error_response

            ip = getattr(g, "client_ip", None) or normalize_ip(request.remote_addr)
            if user_key and getattr(g, "current_user", None) is not None:
                key = f"user:{g.current_user.id}"
            else:
                key = f"ip:{ip}"
            if route is None:
                route = request.endpoint or request.path
            result = check_rate_limit(key=key, scope=scope, limit=limit, window_seconds=window_seconds, user_id=getattr(g, "current_user", None).id if getattr(g, "current_user", None) is not None else None, route=route)
            if not result.allowed:
                response = error_response("RATE_LIMIT_EXCEEDED", "Too many requests", 429)
                response[0].headers["Retry-After"] = str(max(1, int((result.reset_at - datetime.now(timezone.utc)).total_seconds())))
                response[0].headers["RateLimit-Limit"] = str(result.limit)
                response[0].headers["RateLimit-Remaining"] = str(result.remaining)
                response[0].headers["RateLimit-Reset"] = str(int(result.reset_at.timestamp()))
                return response
            return fn(*args, **kwargs)
        return wrapped
    return decorator
