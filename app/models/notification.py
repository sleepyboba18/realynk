import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.extensions.database import db


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('new_message', 'mention', 'direct_message', 'reaction', 'channel_invitation', 'system')",
            name="ck_notifications_type",
        ),
        Index("ix_notifications_recipient_created", "recipient_id", "created_at", "id"),
        Index("ix_notifications_recipient_unread", "recipient_id", "is_read", "deleted_at", "created_at"),
        UniqueConstraint("recipient_id", "deduplication_key", name="uq_notification_recipient_deduplication"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type = db.Column(String(32), nullable=False)
    title = db.Column(String(160), nullable=False)
    body = db.Column(Text, nullable=False)
    entity_type = db.Column(String(32), nullable=False)
    entity_id = db.Column(UUID(as_uuid=True), nullable=True)
    metadata_json = db.Column("metadata", JSONB, nullable=True)
    deduplication_key = db.Column(String(255), nullable=True)
    is_read = db.Column(Boolean, nullable=False, default=False, server_default="false")
    read_at = db.Column(DateTime(timezone=True), nullable=True)
    deleted_at = db.Column(DateTime(timezone=True), nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="notifications_received")
    actor = relationship("User", foreign_keys=[actor_id])

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "metadata": self.metadata_json,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
