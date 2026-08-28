import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "(channel_id IS NOT NULL AND conversation_id IS NULL) OR "
            "(channel_id IS NULL AND conversation_id IS NOT NULL)",
            name="ck_messages_exactly_one_context",
        ),
        CheckConstraint("length(btrim(content)) > 0", name="ck_messages_content_not_empty"),
        CheckConstraint("length(content) <= 4000", name="ck_messages_content_length"),
        Index("ix_messages_channel_created_id", "channel_id", "created_at", "id"),
        Index("ix_messages_conversation_created_id", "conversation_id", "created_at", "id"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = db.Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    channel_id = db.Column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=True
    )
    conversation_id = db.Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=True
    )
    content = db.Column(Text, nullable=False)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_edited = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    deleted_at = db.Column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", back_populates="messages", lazy="joined")
    channel = relationship("Channel", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
    reactions = relationship("MessageReaction", back_populates="message")
    reads = relationship("MessageRead", back_populates="message")
    attachments = relationship("Attachment", back_populates="message")

    def to_dict(self) -> dict[str, object]:
        is_deleted = self.deleted_at is not None
        return {
            "id": str(self.id),
            "content": None if is_deleted else self.content,
            "sender": self.sender.to_dict() if self.sender else None,
            "channel_id": str(self.channel_id) if self.channel_id else None,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_edited": self.is_edited,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "is_deleted": is_deleted,
            "attachments": [] if is_deleted else [attachment.to_dict() for attachment in self.attachments if attachment.deleted_at is None],
        }
