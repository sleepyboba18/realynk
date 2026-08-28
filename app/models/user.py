import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions.database import db


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_users_status"),
        CheckConstraint("moderation_role IN ('member', 'moderator', 'admin')", name="ck_users_moderation_role"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(String(30), nullable=False, unique=True, index=True)
    email = db.Column(String(320), nullable=False, unique=True, index=True)
    password_hash = db.Column(String(255), nullable=False)
    display_name = db.Column(String(100), nullable=True)
    avatar_url = db.Column(String(2048), nullable=True)
    status = db.Column(String(16), nullable=False, default="active", server_default="active")
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    last_login_at = db.Column(DateTime(timezone=True), nullable=True)
    last_seen_at = db.Column(DateTime(timezone=True), nullable=True)
    moderation_role = db.Column(String(16), nullable=False, default="member", server_default="member")
    suspended_at = db.Column(DateTime(timezone=True), nullable=True)
    suspension_expires_at = db.Column(DateTime(timezone=True), nullable=True)
    banned_at = db.Column(DateTime(timezone=True), nullable=True)

    owned_channels = relationship("Channel", back_populates="owner", foreign_keys="Channel.owner_id")
    channel_memberships = relationship(
        "ChannelMembership", back_populates="user", cascade="all, delete-orphan"
    )
    conversation_participants = relationship(
        "ConversationParticipant", back_populates="user", cascade="all, delete-orphan"
    )
    messages = relationship("Message", back_populates="sender")
    message_reactions = relationship("MessageReaction", back_populates="user")
    message_reads = relationship("MessageRead", back_populates="user")
    notification_preferences = relationship("NotificationPreference", back_populates="user", cascade="all, delete-orphan")
    notifications_received = relationship("Notification", foreign_keys="Notification.recipient_id", back_populates="recipient")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_private: bool = False) -> dict[str, object]:
        data: dict[str, object] = {
            "id": str(self.id),
            "username": self.username,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "status": self.status,
            "created_at": _isoformat(self.created_at),
            "updated_at": _isoformat(self.updated_at),
        }
        if include_private:
            data.update(
                {
                    "email": self.email,
                    "last_login_at": _isoformat(self.last_login_at),
                }
            )
        return data


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
