import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class Attachment(db.Model):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint("attachment_type IN ('image', 'document', 'video', 'audio', 'file')", name="ck_attachments_type"),
        CheckConstraint("file_size > 0", name="ck_attachments_file_size"),
        Index("ix_attachments_message_active", "message_id", "deleted_at", "created_at"),
        Index("ix_attachments_uploader_created", "uploader_id", "created_at"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = db.Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False)
    uploader_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    original_filename = db.Column(String(255), nullable=False)
    storage_path = db.Column(String(512), nullable=False, unique=True)
    mime_type = db.Column(String(128), nullable=False)
    file_size = db.Column(Integer, nullable=False)
    extension = db.Column(String(16), nullable=False)
    attachment_type = db.Column(String(16), nullable=False)
    checksum = db.Column(String(64), nullable=True)
    width = db.Column(Integer, nullable=True)
    height = db.Column(Integer, nullable=True)
    duration = db.Column(db.Float, nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at = db.Column(DateTime(timezone=True), nullable=True)

    message = relationship("Message", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploader_id])

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "message_id": str(self.message_id),
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "attachment_type": self.attachment_type,
            "extension": self.extension,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
