from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.models.message import Message
from app.permissions.message_permissions import (
    can_delete_message,
    can_edit_message,
    can_send_channel_message,
    can_send_conversation_message,
)
from app.repositories import channel_repository, conversation_repository, message_repository
from app.schemas.message import MAX_MESSAGE_LENGTH
from app.services.channel_service import get_channel_for_user
from app.services.conversation_service import get_for_user


class MessageError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _context(user_id: UUID, channel_id: UUID | None, conversation_id: UUID | None):
    if bool(channel_id) == bool(conversation_id):
        raise MessageError("INVALID_MESSAGE_CONTEXT", "Exactly one message context is required", 422)
    if channel_id:
        try:
            channel, membership = get_channel_for_user(channel_id, user_id)
        except Exception as error:
            if hasattr(error, "code"):
                raise MessageError("MESSAGE_ACCESS_DENIED", "You do not have access to this channel", 403) from error
            raise
        if not can_send_channel_message(type("UserRef", (), {"id": user_id, "is_active": True, "status": "active"})(), channel, membership):
            raise MessageError("MESSAGE_ACCESS_DENIED", "You do not have access to this channel", 403)
        return channel, membership
    try:
        conversation, participant = get_for_user(conversation_id, user_id)
    except Exception as error:
        if hasattr(error, "code"):
            raise MessageError("MESSAGE_ACCESS_DENIED", "You do not have access to this conversation", 403) from error
        raise
    user = type("UserRef", (), {"id": user_id, "is_active": True, "status": "active"})()
    if not can_send_conversation_message(user, conversation, participant):
        raise MessageError("MESSAGE_ACCESS_DENIED", "You do not have access to this conversation", 403)
    return conversation, participant


def create_message(user, content: str, channel_id: UUID | None = None, conversation_id: UUID | None = None) -> Message:
    from app.permissions.moderation_permissions import is_restricted
    if is_restricted(user):
        raise MessageError("ACCOUNT_RESTRICTED", "Account is suspended or banned", 403)
    if not isinstance(content, str) or not content.strip():
        raise MessageError("MESSAGE_CONTENT_REQUIRED", "Message content is required", 422)
    if len(content) > MAX_MESSAGE_LENGTH:
        raise MessageError("MESSAGE_CONTENT_TOO_LONG", "Message content is too long", 422)
    context, _ = _context(user.id, channel_id, conversation_id)
    message = Message(
        sender_id=user.id,
        channel_id=channel_id,
        conversation_id=conversation_id,
        content=content,
    )
    db.session.add(message)
    context.updated_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise MessageError("MESSAGE_SEND_FAILED", "Unable to send message", 500) from exc
    try:
        from app.services.notification_service import notify_message
        notify_message(message)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Unable to create message notifications")
    return message_repository.get_by_id(message.id) or message


def get_message_for_user(user_id: UUID, message_id: UUID) -> Message:
    message = message_repository.get_by_id(message_id)
    if message is None:
        raise MessageError("MESSAGE_NOT_FOUND", "Message not found", 404)
    _context(user_id, message.channel_id, message.conversation_id)
    return message


def edit_message(user, message: Message, content: str) -> Message:
    if message.deleted_at is not None:
        raise MessageError("MESSAGE_ALREADY_DELETED", "Message has already been deleted", 409)
    if not can_edit_message(user, message):
        raise MessageError("MESSAGE_EDIT_NOT_ALLOWED", "Only the message sender can edit it", 403)
    message.content = content
    message.is_edited = True
    message.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return message_repository.get_by_id(message.id) or message


def delete_message(user, message: Message) -> Message:
    if message.deleted_at is not None:
        raise MessageError("MESSAGE_ALREADY_DELETED", "Message has already been deleted", 409)
    if not can_delete_message(user, message):
        raise MessageError("MESSAGE_DELETE_NOT_ALLOWED", "Only the message sender can delete it", 403)
    message.deleted_at = datetime.now(timezone.utc)
    message.content = ""
    message.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return message_repository.get_by_id(message.id) or message


def list_messages(
    user_id: UUID,
    channel_id: UUID | None,
    conversation_id: UUID | None,
    limit: int,
    before_id: UUID | None,
    offset: int = 0,
):
    context, _ = _context(user_id, channel_id, conversation_id)
    before = message_repository.get_by_id(before_id) if before_id else None
    if before and ((channel_id and before.channel_id != channel_id) or (conversation_id and before.conversation_id != conversation_id)):
        raise MessageError("INVALID_MESSAGE_CURSOR", "Cursor does not belong to this context", 422)
    return message_repository.list_history(channel_id, conversation_id, limit, before, offset)
