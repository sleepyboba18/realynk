import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.extensions.database import db


class ChannelMembership(db.Model):
    __tablename__ = "channel_memberships"
    __table_args__ = (
        UniqueConstraint("channel_id", "user_id", name="uq_channel_membership_channel_user"),
        CheckConstraint("role IN ('owner', 'admin', 'member')", name="ck_channel_membership_role"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = db.Column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = db.Column(String(16), nullable=False, default="member", server_default="member")
    joined_at = db.Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    channel = relationship("Channel", back_populates="memberships")
    user = relationship("User", back_populates="channel_memberships")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "channel_id": str(self.channel_id),
            "user_id": str(self.user_id),
            "role": self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": self.user.to_dict() if self.user else None,
        }
