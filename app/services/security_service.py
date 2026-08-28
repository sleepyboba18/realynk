from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from flask import current_app

from app.extensions.database import db
from app.repositories.security_repository import SecurityRepository
from app.security.request_context import get_client_ip, get_request_id


class SecurityService:
    def __init__(self, repository: SecurityRepository | None = None) -> None:
        self.repository = repository or SecurityRepository()

    def log_event(self, *, event_type: str, user_id: UUID | None = None, ip_address: str | None = None, route: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        if not current_app or not current_app.config.get("RATE_LIMIT_ENABLED", True):
            return
        try:
            self.repository.log_event(
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address or get_client_ip(),
                request_id=get_request_id(),
                route=route,
                metadata=metadata,
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

    def cleanup_expired(self) -> int:
        return self.repository.prune_expired()

    def default_rate_limit(self, *, key: str, scope: str, limit: int, window_seconds: int) -> tuple[bool, int, int, datetime]:
        now = datetime.now(timezone.utc)
        window_start = now.replace(microsecond=0)
        expires_at = window_start + timedelta(seconds=window_seconds)
        allowed, count, _ = self.repository.increment_bucket(
            key=key,
            scope=scope,
            window_start=window_start,
            expires_at=expires_at,
            limit=limit,
        )
        return allowed, count, limit, expires_at
