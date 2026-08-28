from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.channel import Channel
from app.models.channel_membership import ChannelMembership
from app.permissions.channel_permissions import can_manage_member, has_channel_role
from app.repositories import channel_repository
from app.services.channel_service import ChannelError
from app.services.user_service import get_user, UserNotFoundError


def require_channel_membership(channel: Channel, user_id: UUID) -> ChannelMembership:
    membership = channel_repository.get_membership(channel.id, user_id)
    if membership is None:
        raise ChannelError("CHANNEL_ACCESS_DENIED", "You do not have access to this channel", 403)
    return membership


def join_public(channel: Channel, user_id: UUID) -> ChannelMembership:
    if channel.is_private:
        raise ChannelError("CHANNEL_ACCESS_DENIED", "Private channels require an invitation", 403)
    if channel_repository.get_membership(channel.id, user_id):
        raise ChannelError("ALREADY_MEMBER", "You are already a member of this channel", 409)
    membership = ChannelMembership(channel_id=channel.id, user_id=user_id, role="member")
    db.session.add(membership)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ChannelError("ALREADY_MEMBER", "You are already a member of this channel", 409) from exc
    return membership


def leave(channel: Channel, user_id: UUID) -> None:
    membership = require_channel_membership(channel, user_id)
    if membership.role == "owner":
        raise ChannelError("OWNER_CANNOT_LEAVE", "Ownership must be transferred before leaving", 409)
    db.session.delete(membership)
    db.session.commit()


def add_member(channel: Channel, actor_id: UUID, user_id: UUID) -> ChannelMembership:
    actor = require_channel_membership(channel, actor_id)
    if not can_manage_member(actor):
        raise ChannelError("MEMBERSHIP_FORBIDDEN", "You cannot manage members in this channel", 403)
    try:
        get_user(user_id)
    except UserNotFoundError as exc:
        raise ChannelError("USER_NOT_FOUND", "User not found", 404) from exc
    if channel_repository.get_membership(channel.id, user_id):
        raise ChannelError("ALREADY_MEMBER", "User is already a member of this channel", 409)
    membership = ChannelMembership(channel_id=channel.id, user_id=user_id, role="member")
    db.session.add(membership)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ChannelError("ALREADY_MEMBER", "User is already a member of this channel", 409) from exc
    return membership


def remove_member(channel: Channel, actor_id: UUID, user_id: UUID) -> None:
    actor = require_channel_membership(channel, actor_id)
    target = channel_repository.get_membership(channel.id, user_id)
    if target is None:
        raise ChannelError("MEMBERSHIP_NOT_FOUND", "Membership not found", 404)
    if not can_manage_member(actor, target):
        raise ChannelError("MEMBERSHIP_FORBIDDEN", "You cannot remove this member", 403)
    db.session.delete(target)
    db.session.commit()


def change_role(channel: Channel, actor_id: UUID, user_id: UUID, role: str) -> ChannelMembership:
    actor = require_channel_membership(channel, actor_id)
    target = channel_repository.get_membership(channel.id, user_id)
    if target is None:
        raise ChannelError("MEMBERSHIP_NOT_FOUND", "Membership not found", 404)
    if not has_channel_role(actor, "owner") or target.role == "owner":
        raise ChannelError("MEMBERSHIP_FORBIDDEN", "Only the owner can change member roles", 403)
    target.role = role
    db.session.commit()
    return target
