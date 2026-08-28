import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class Channel(db.Model):
    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint("channel_type = 'text'", name="ck_channels_type"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(80), nullable=False)
    description = db.Column(Text, nullable=True)
    channel_type = db.Column(String(16), nullable=False, default="text", server_default="text")
    is_private = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    owner_id = db.Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    locked_at = db.Column(DateTime(timezone=True), nullable=True)
    locked_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    owner = relationship("User", back_populates="owned_channels", foreign_keys=[owner_id])
    memberships = relationship(
        "ChannelMembership",
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    messages = relationship("Message", back_populates="channel")

    def to_dict(self, include_membership: "ChannelMembership | None" = None) -> dict[str, object]:
        data = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "channel_type": self.channel_type,
            "is_private": self.is_private,
            "owner_id": str(self.owner_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_membership:
            data["membership"] = include_membership.to_dict()
        return data
