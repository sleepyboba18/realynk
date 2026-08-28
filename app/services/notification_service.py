import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.channel_membership import ChannelMembership
from app.models.conversation_participant import ConversationParticipant
from app.models.notification import Notification
from app.notifications.manager import emit_to_user
from app.notifications.types import NotificationType
from app.permissions.notification_permissions import can_delete_notification, can_mark_notification_read, can_view_notification
from app.repositories import notification_repository
from app.services.notification_preference_service import is_enabled

MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_]{3,30})")


class NotificationError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def create_notification(
    recipient,
    notification_type: str | NotificationType,
    title: str,
    body: str,
    entity_type: str,
    entity_id: UUID | None = None,
    actor=None,
    metadata: dict[str, object] | None = None,
    deduplication_key: str | None = None,
):
    if recipient is None or not recipient.is_active or recipient.status != "active":
        return None
    try:
        notification_type = NotificationType(notification_type).value
    except (ValueError, TypeError) as exc:
        raise NotificationError("INVALID_NOTIFICATION_TYPE", "Unknown notification type", 422) from exc
    if not is_enabled(recipient.id, notification_type):
        return None
    existing = notification_repository.find_duplicate(recipient.id, deduplication_key)
    if existing:
        return existing
    notification = Notification(
        recipient_id=recipient.id,
        actor_id=actor.id if actor else None,
        type=notification_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
        deduplication_key=deduplication_key,
    )
    notification_repository.create(notification)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        existing = notification_repository.find_duplicate(recipient.id, deduplication_key)
        if existing:
            return existing
        raise NotificationError("NOTIFICATION_CREATE_FAILED", "Unable to create notification", 500) from exc
    _deliver_created(notification)
    return notification


def create_many_notifications(items: list[dict[str, object]]) -> list[Notification]:
    created: list[Notification] = []
    for item in items:
        recipient = item["recipient"]
        notification_type = NotificationType(item["notification_type"]).value
        if not recipient.is_active or recipient.status != "active" or not is_enabled(recipient.id, notification_type):
            continue
        dedup = item.get("deduplication_key")
        if notification_repository.find_duplicate(recipient.id, dedup):
            continue
        notification = Notification(
            recipient_id=recipient.id,
            actor_id=item["actor"].id if item.get("actor") else None,
            type=notification_type,
            title=item["title"],
            body=item["body"],
            entity_type=item["entity_type"],
            entity_id=item.get("entity_id"),
            metadata_json=item.get("metadata"),
            deduplication_key=dedup,
        )
        db.session.add(notification)
        created.append(notification)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise NotificationError("NOTIFICATION_CREATE_FAILED", "Unable to create notifications", 500) from exc
    for notification in created:
        _deliver_created(notification)
    return created


def get_notification(user, notification_id: UUID) -> Notification:
    notification = notification_repository.get_by_id(notification_id)
    if notification is None or not can_view_notification(user, notification):
        raise NotificationError("NOTIFICATION_NOT_FOUND", "Notification not found", 404)
    return notification


def list_notifications(user, page: int, limit: int, unread_only: bool):
    return notification_repository.list_for_user(user.id, page, limit, unread_only)


def mark_as_read(user, notification_id: UUID):
    notification = get_notification(user, notification_id)
    if notification.is_read:
        return notification, False
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    db.session.commit()
    emit_to_user(user.id, "notification_read", {"notification_id": str(notification.id), "read_at": notification.read_at.isoformat()})
    _emit_count(user.id)
    return notification, True


def mark_all_as_read(user):
    read_at = datetime.now(timezone.utc)
    changed = notification_repository.mark_all_read(user.id, read_at)
    db.session.commit()
    if changed:
        emit_to_user(user.id, "notifications_read_all", {"read_at": read_at.isoformat()})
        _emit_count(user.id)
    return changed, read_at


def delete_notification(user, notification_id: UUID):
    notification = get_notification(user, notification_id)
    if not can_delete_notification(user, notification):
        raise NotificationError("NOTIFICATION_NOT_FOUND", "Notification not found", 404)
    if notification.deleted_at is None:
        notification.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        emit_to_user(user.id, "notification_deleted", {"notification_id": str(notification.id)})
        _emit_count(user.id)
    return notification


def get_unread_count(user_id: UUID) -> int:
    return notification_repository.count_unread(user_id)


def cleanup_old_notifications(before_datetime: datetime) -> int:
    from sqlalchemy import delete
    result = db.session.execute(
        delete(Notification).where(Notification.created_at < before_datetime)
    )
    db.session.commit()
    return result.rowcount


def notify_message(message) -> None:
    from app.repositories.user_repository import get_by_usernames
    if message.channel_id:
        recipients_ids = db.session.scalars(
            select(ChannelMembership.user_id).where(ChannelMembership.channel_id == message.channel_id, ChannelMembership.user_id != message.sender_id)
        ).all()
        notification_type = NotificationType.NEW_MESSAGE
        body = "New activity in a channel"
    else:
        recipients_ids = db.session.scalars(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == message.conversation_id,
                ConversationParticipant.user_id != message.sender_id,
                ConversationParticipant.left_at.is_(None),
            )
        ).all()
        notification_type = NotificationType.DIRECT_MESSAGE
        body = "You received a new direct message"
    recipients = _active_users(set(recipients_ids))
    mentioned_names = {match.group(1).lower() for match in MENTION_PATTERN.finditer(message.content)}
    mentioned_users = {user.id: user for user in get_by_usernames(mentioned_names)} if mentioned_names else {}
    mentioned_ids = set(mentioned_users) & set(recipients)
    items = []
    for user_id, recipient in recipients.items():
        if user_id in mentioned_ids:
            items.append(_message_item(recipient, message, NotificationType.MENTION, "You were mentioned", "You were mentioned in a conversation", f"mention:{message.id}:{recipient.id}", {"username": recipient.username}))
        else:
            items.append(_message_item(recipient, message, notification_type, "New message", body, f"{notification_type.value}:{message.id}:{recipient.id}"))
    if items:
        create_many_notifications(items)


def notify_reaction(message, actor, emoji: str, event_id=None) -> None:
    if message.sender_id == actor.id:
        return
    recipient = _active_users({message.sender_id}).get(message.sender_id)
    if recipient:
        create_notification(
            recipient,
            NotificationType.REACTION,
            "Someone reacted to your message",
            "Someone reacted to your message",
            "message",
            message.id,
            actor,
            {"message_id": str(message.id), "emoji": emoji},
            f"reaction:{message.id}:{actor.id}:{emoji}:{event_id or message.id}",
        )


def _message_item(recipient, message, notification_type, title, body, dedup, metadata=None):
    return {
        "recipient": recipient,
        "notification_type": notification_type,
        "title": title,
        "body": body,
        "entity_type": "message",
        "entity_id": message.id,
        "actor": message.sender,
        "metadata": metadata,
        "deduplication_key": dedup,
    }


def _active_users(user_ids: set[UUID]):
    from app.repositories.presence_repository import get_users
    return {user.id: user for user in get_users(list(user_ids)) if user.is_active and user.status == "active"}


def _deliver_created(notification: Notification) -> None:
    emit_to_user(notification.recipient_id, "notification_created", notification.to_dict())
    _emit_count(notification.recipient_id)


def _emit_count(user_id: UUID) -> None:
    emit_to_user(user_id, "notification_count_updated", {"count": get_unread_count(user_id)})
