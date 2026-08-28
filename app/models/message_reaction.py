import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class MessageReaction(db.Model):
    __tablename__ = "message_reactions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_reaction_user_emoji"),
        Index("ix_message_reactions_message_id", "message_id"),
        Index("ix_message_reactions_user_id", "user_id"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = db.Column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False
    )
    user_id = db.Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    emoji = db.Column(String(32), nullable=False)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message = relationship("Message", back_populates="reactions")
    user = relationship("User", back_populates="message_reactions")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "message_id": str(self.message_id),
            "user_id": str(self.user_id),
            "emoji": self.emoji,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
