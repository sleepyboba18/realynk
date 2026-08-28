import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", name="uq_notification_preference_user_type"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = db.Column(String(32), nullable=False)
    enabled = db.Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="notification_preferences")
