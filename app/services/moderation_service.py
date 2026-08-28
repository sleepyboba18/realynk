from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.extensions.database import db
from app.models.moderation_action import ModerationAction
from app.permissions import moderation_permissions as permissions
from app.repositories import channel_repository, moderation_repository
from app.services.user_service import get_user, UserNotFoundError
from app.models.message import Message


class ModerationError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _target(user_id: UUID):
    try:
        return get_user(user_id)
    except UserNotFoundError as exc:
        raise ModerationError("TARGET_NOT_FOUND", "Target user not found", 404) from exc


def _reason(reason: str | None) -> str | None:
    return reason.strip() if isinstance(reason, str) and reason.strip() else None


def _authorize(actor, target, check) -> None:
    if not check(actor, target):
        raise ModerationError("MODERATION_PERMISSION_DENIED", "You cannot moderate this account", 403)


def _record(actor, action, reason, target_user=None, target_channel=None, target_message=None, expires_at=None, metadata=None):
    record = ModerationAction(
        moderator_id=actor.id,
        target_user_id=target_user.id if target_user else None,
        target_channel_id=target_channel.id if target_channel else None,
        target_message_id=target_message.id if target_message else None,
        action=action,
        reason=_reason(reason),
        expires_at=expires_at,
        metadata_json=metadata,
    )
    db.session.add(record)
    return record


def warn_user(actor, user_id: UUID, reason: str | None):
    target = _target(user_id)
    _authorize(actor, target, permissions.can_warn_user)
    record = _record(actor, "USER_WARN", reason, target_user=target)
    db.session.commit()
    return record


def suspend_user(actor, user_id: UUID, reason: str | None, duration_seconds: int | None):
    target = _target(user_id)
    _authorize(actor, target, permissions.can_suspend_user)
    if target.suspended_at and (target.suspension_expires_at is None or target.suspension_expires_at > datetime.now(timezone.utc)):
        raise ModerationError("ALREADY_SUSPENDED", "User is already suspended", 409)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=duration_seconds) if duration_seconds else None
    target.suspended_at, target.suspension_expires_at = now, expires
    record = _record(actor, "USER_SUSPEND", reason, target_user=target, expires_at=expires)
    db.session.commit()
    return record


def unsuspend_user(actor, user_id: UUID, reason: str | None):
    target = _target(user_id)
    _authorize(actor, target, permissions.can_suspend_user)
    if not target.suspended_at or (target.suspension_expires_at and target.suspension_expires_at <= datetime.now(timezone.utc)):
        raise ModerationError("NOT_SUSPENDED", "User is not suspended", 409)
    target.suspended_at = target.suspension_expires_at = None
    record = _record(actor, "USER_UNSUSPEND", reason, target_user=target)
    db.session.commit()
    return record


def ban_user(actor, user_id: UUID, reason: str | None, duration_seconds: int | None):
    target = _target(user_id)
    _authorize(actor, target, permissions.can_ban_user)
    if target.banned_at:
        raise ModerationError("ALREADY_BANNED", "User is already banned", 409)
    target.banned_at = datetime.now(timezone.utc)
    record = _record(actor, "USER_BAN", reason, target_user=target)
    db.session.commit()
    return record


def unban_user(actor, user_id: UUID, reason: str | None):
    target = _target(user_id)
    _authorize(actor, target, permissions.can_ban_user)
    if not target.banned_at:
        raise ModerationError("NOT_BANNED", "User is not banned", 409)
    target.banned_at = None
    record = _record(actor, "USER_UNBAN", reason, target_user=target)
    db.session.commit()
    return record


def lock_channel(actor, channel_id: UUID, reason: str | None, locked: bool):
    channel = channel_repository.get_channel(channel_id)
    if channel is None:
        raise ModerationError("TARGET_NOT_FOUND", "Channel not found", 404)
    if not permissions.can_lock_channel(actor):
        raise ModerationError("MODERATION_PERMISSION_DENIED", "You cannot lock this channel", 403)
    if bool(channel.locked_at) == locked:
        raise ModerationError("CHANNEL_ALREADY_LOCKED" if locked else "CHANNEL_NOT_LOCKED", "Channel state is unchanged", 409)
    channel.locked_at = datetime.now(timezone.utc) if locked else None
    channel.locked_by = actor.id if locked else None
    action = "CHANNEL_LOCK" if locked else "CHANNEL_UNLOCK"
    record = _record(actor, action, reason, target_channel=channel)
    db.session.commit()
    return record, channel


def remove_channel_member(actor, channel_id: UUID, user_id: UUID, reason: str | None):
    channel = channel_repository.get_channel(channel_id)
    target = _target(user_id)
    membership = channel_repository.get_membership(channel_id, user_id)
    if channel is None or membership is None:
        raise ModerationError("TARGET_NOT_FOUND", "Channel member not found", 404)
    if not permissions.can_remove_member(actor, membership):
        raise ModerationError("MODERATION_PERMISSION_DENIED", "You cannot remove this member", 403)
    if membership.role == "owner":
        raise ModerationError("TARGET_PROTECTED", "The channel owner cannot be removed", 403)
    db.session.delete(membership)
    record = _record(actor, "REMOVE_FROM_CHANNEL", reason, target_user=target, target_channel=channel)
    db.session.commit()
    return record


def delete_message(actor, message_id: UUID, reason: str | None):
    from app.repositories.message_repository import get_by_id
    message = get_by_id(message_id)
    if message is None:
        raise ModerationError("TARGET_NOT_FOUND", "Message not found", 404)
    if not permissions.can_delete_message(actor):
        raise ModerationError("MODERATION_PERMISSION_DENIED", "You cannot moderate messages", 403)
    if message.deleted_at is None:
        message.deleted_at = datetime.now(timezone.utc)
        message.content = ""
    record = _record(actor, "MESSAGE_DELETE", reason, target_message=message)
    db.session.commit()
    return record, message


def get_user_history(actor, user_id: UUID):
    if not permissions.can_view_audit_logs(actor):
        raise ModerationError("MODERATION_PERMISSION_DENIED", "You cannot view moderation history", 403)
    return moderation_repository.get_user_actions(user_id)


def get_audit_logs(actor, limit: int, offset: int):
    if not permissions.can_view_audit_logs(actor):
        raise ModerationError("MODERATION_PERMISSION_DENIED", "You cannot view audit logs", 403)
    return moderation_repository.list_actions(limit, offset)
