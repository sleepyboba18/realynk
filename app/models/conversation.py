import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class Conversation(db.Model):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("conversation_type = 'direct'", name="ck_conversations_type"),
        CheckConstraint("participant_a_id <> participant_b_id", name="ck_conversations_distinct_pair"),
        UniqueConstraint("participant_a_id", "participant_b_id", name="uq_conversations_participant_pair"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_type = db.Column(String(16), nullable=False, default="direct", server_default="direct")
    participant_a_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    participant_b_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    participant_a = relationship("User", foreign_keys=[participant_a_id])
    participant_b = relationship("User", foreign_keys=[participant_b_id])
    participants = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ConversationParticipant.joined_at.asc()",
    )
    messages = relationship("Message", back_populates="conversation")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "type": self.conversation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "participants": [participant.user.to_dict() for participant in self.participants if participant.user],
        }
