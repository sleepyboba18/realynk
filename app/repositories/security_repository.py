from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select

from app.extensions.database import db
from app.models.rate_limit_bucket import RateLimitBucket
from app.models.security_event import SecurityEvent


class SecurityRepository:
    def add_rate_limit_event(
        self,
        *,
        key: str,
        scope: str,
        window_start: datetime,
        request_count: int,
        expires_at: datetime,
    ) -> RateLimitBucket:
        bucket = db.session.execute(
            select(RateLimitBucket).where(RateLimitBucket.key == key, RateLimitBucket.scope == scope, RateLimitBucket.window_start == window_start)
        ).scalar_one_or_none()
        if bucket is None:
            bucket = RateLimitBucket(
                key=key,
                scope=scope,
                window_start=window_start,
                request_count=request_count,
                expires_at=expires_at,
            )
            db.session.add(bucket)
        else:
            bucket.request_count = request_count
            bucket.expires_at = expires_at
        db.session.flush()
        return bucket

    def get_bucket(self, *, key: str, scope: str, window_start: datetime) -> RateLimitBucket | None:
        return db.session.scalar(
            select(RateLimitBucket).where(
                RateLimitBucket.key == key,
                RateLimitBucket.scope == scope,
                RateLimitBucket.window_start == window_start,
            )
        )

    def increment_bucket(self, *, key: str, scope: str, window_start: datetime, expires_at: datetime, limit: int) -> tuple[bool, int, int]:
        bucket = self.get_bucket(key=key, scope=scope, window_start=window_start)
        if bucket is None:
            bucket = RateLimitBucket(
                key=key,
                scope=scope,
                window_start=window_start,
                request_count=1,
                expires_at=expires_at,
            )
            db.session.add(bucket)
            db.session.flush()
            return True, 1, limit

        bucket.request_count += 1
        bucket.expires_at = expires_at
        db.session.flush()
        allowed = bucket.request_count <= limit
        return allowed, bucket.request_count, limit

    def prune_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = db.session.execute(
            delete(RateLimitBucket).where(RateLimitBucket.expires_at < now)
        )
        db.session.flush()
        return result.rowcount or 0

    def log_event(self, *, event_type: str, user_id: UUID | None = None, ip_address: str | None = None, request_id: str | None = None, route: str | None = None, metadata: dict[str, Any] | None = None) -> SecurityEvent:
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            request_id=request_id,
            route=route,
            event_metadata=metadata or {},
        )
        db.session.add(event)
        db.session.flush()
        return event

    def cleanup_events(self, *, older_than_days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        result = db.session.execute(delete(SecurityEvent).where(SecurityEvent.created_at < cutoff))
        db.session.flush()
        return result.rowcount or 0

    def count_recent(self, *, event_type: str, window_seconds: int = 60, ip_address: str | None = None, user_id: UUID | None = None) -> int:
        deadline = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        statement = select(func.count(SecurityEvent.id)).where(SecurityEvent.event_type == event_type, SecurityEvent.created_at >= deadline)
        if ip_address:
            statement = statement.where(SecurityEvent.ip_address == ip_address)
        if user_id:
            statement = statement.where(SecurityEvent.user_id == user_id)
        return db.session.scalar(statement) or 0
