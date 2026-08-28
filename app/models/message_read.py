import uuid

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class MessageRead(db.Model):
    __tablename__ = "message_reads"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_read_user"),
        Index("ix_message_reads_message_id", "message_id"),
        Index("ix_message_reads_user_id", "user_id"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = db.Column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False
    )
    user_id = db.Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    read_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message = relationship("Message", back_populates="reads")
    user = relationship("User", back_populates="message_reads")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "message_id": str(self.message_id),
            "user_id": str(self.user_id),
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
