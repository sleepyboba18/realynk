import uuid

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions.database import db


class RateLimitBucket(db.Model):
    __tablename__ = "rate_limit_buckets"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = db.Column(String(255), nullable=False, index=True)
    scope = db.Column(String(32), nullable=False, index=True)
    window_start = db.Column(DateTime(timezone=True), nullable=False, index=True)
    request_count = db.Column(db.Integer, nullable=False, default=1)
    expires_at = db.Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_rate_limit_bucket_key_scope_window", "key", "scope", "window_start"),
    )
