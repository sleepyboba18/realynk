import uuid

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class ModerationAction(db.Model):
    __tablename__ = "moderation_actions"
    __table_args__ = (
        Index("ix_moderation_actions_target_user_created", "target_user_id", "created_at", "id"),
        Index("ix_moderation_actions_actor_created", "moderator_id", "created_at", "id"),
        Index("ix_moderation_actions_action_created", "action", "created_at", "id"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    moderator_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    target_user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    target_channel_id = db.Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=True)
    target_message_id = db.Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=True)
    action = db.Column(String(32), nullable=False)
    reason = db.Column(Text, nullable=True)
    metadata_json = db.Column("metadata", JSON, nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = db.Column(DateTime(timezone=True), nullable=True)
    revoked_at = db.Column(DateTime(timezone=True), nullable=True)

    moderator = relationship("User", foreign_keys=[moderator_id])
    target_user = relationship("User", foreign_keys=[target_user_id])

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "action": self.action,
            "moderator": self.moderator.to_dict() if self.moderator else None,
            "target_user": self.target_user.to_dict() if self.target_user else None,
            "target_channel_id": str(self.target_channel_id) if self.target_channel_id else None,
            "target_message_id": str(self.target_message_id) if self.target_message_id else None,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
