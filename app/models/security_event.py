import uuid

from sqlalchemy import DateTime, Index, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions.database import db


class SecurityEvent(db.Model):
    __tablename__ = "security_events"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = db.Column(String(64), nullable=False, index=True)
    user_id = db.Column(UUID(as_uuid=True), nullable=True, index=True)
    ip_address = db.Column(String(45), nullable=True, index=True)
    request_id = db.Column(String(64), nullable=True)
    route = db.Column(String(255), nullable=True)
    event_metadata = db.Column("event_metadata", JSON, nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_security_event_type_user_ip_created", "event_type", "user_id", "ip_address", "created_at"),
    )
