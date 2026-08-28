from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.channel import Channel
from app.models.channel_membership import ChannelMembership
from app.permissions.channel_permissions import can_delete_channel, can_manage_channel, can_view_channel
from app.repositories import channel_repository


class ChannelError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def get_channel_for_user(channel_id: UUID, user_id: UUID) -> tuple[Channel, ChannelMembership | None]:
    channel = channel_repository.get_channel(channel_id)
    if channel is None:
        raise ChannelError("CHANNEL_NOT_FOUND", "Channel not found", 404)
    membership = channel_repository.get_membership(channel_id, user_id)
    if not can_view_channel(channel, membership):
        raise ChannelError("CHANNEL_NOT_FOUND", "Channel not found", 404)
    return channel, membership


def create_channel(user_id: UUID, name: str, description: str | None, is_private: bool) -> Channel:
    channel = Channel(
        name=name.strip(),
        description=description.strip() if description else None,
        is_private=is_private,
        owner_id=user_id,
    )
    db.session.add(channel)
    db.session.flush()
    db.session.add(ChannelMembership(channel_id=channel.id, user_id=user_id, role="owner"))
    db.session.commit()
    return channel


def update_channel(channel: Channel, membership: ChannelMembership, updates: dict[str, object]) -> Channel:
    if not can_manage_channel(membership):
        raise ChannelError("CHANNEL_UPDATE_FORBIDDEN", "You cannot update this channel", 403)
    if "is_private" in updates and membership.role != "owner":
        raise ChannelError("CHANNEL_UPDATE_FORBIDDEN", "Only the owner can change channel privacy", 403)
    for field in ("name", "description", "is_private"):
        if field in updates:
            value = updates[field]
            setattr(channel, field, value.strip() if isinstance(value, str) else value)
    db.session.commit()
    return channel


def delete_channel(channel: Channel, membership: ChannelMembership) -> None:
    if not can_delete_channel(membership):
        raise ChannelError("CHANNEL_DELETE_FORBIDDEN", "Only the channel owner can delete it", 403)
    db.session.delete(channel)
    db.session.commit()
