from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.repositories import read_repository
from app.services.message_service import MessageError, get_message_for_user


class ReadError(ValueError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _message(user_id: UUID, message_id: UUID):
    try:
        return get_message_for_user(user_id, message_id)
    except MessageError as error:
        raise ReadError("READ_ACCESS_DENIED", "You cannot mark this message as read", 403) from error


def mark_read(user, message_id: UUID):
    message = _message(user.id, message_id)
    if message.deleted_at is not None:
        raise ReadError("MESSAGE_DELETED", "Deleted messages cannot be newly marked as read", 409)
    existing = read_repository.get(message_id, user.id)
    if existing:
        return existing, message, False
    read_at = datetime.now(timezone.utc)
    item = read_repository.create(message_id, user.id, read_at)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = read_repository.get(message_id, user.id)
        if existing is None:
            raise ReadError("READ_MARK_FAILED", "Unable to mark message as read", 500)
        return existing, message, False
    return item, message, True


def mark_many(user, message_ids: list[UUID]):
    messages = [_message(user.id, message_id) for message_id in message_ids]
    if any(message.deleted_at is not None for message in messages):
        raise ReadError("MESSAGE_DELETED", "Deleted messages cannot be newly marked as read", 409)
    now = datetime.now(timezone.utc)
    created = []
    for message in messages:
        if read_repository.get(message.id, user.id) is None:
            created.append(read_repository.create(message.id, user.id, now))
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ReadError("READ_MARK_FAILED", "Unable to mark messages as read", 500) from exc
    return created, messages


def summary(user, message_id: UUID):
    message = _message(user.id, message_id)
    existing = read_repository.get(message_id, user.id)
    return {
        "message_id": str(message_id),
        "read_count": read_repository.count(message_id),
        "read_by_me": existing is not None,
        "read_at": existing.read_at.isoformat() if existing else None,
    }, message
