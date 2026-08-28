from uuid import UUID

from flask import request

from app.extensions.socketio import socketio
from app.schemas.read import validate_message_ids
from app.services import read_service


def _failure(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def _room(message) -> str:
    prefix = "channel" if message.channel_id else "conversation"
    value = message.channel_id or message.conversation_id
    return f"{prefix}:{value}"


def _mark_id(data: object):
    if not isinstance(data, dict):
        return None
    try:
        return UUID(str(data.get("message_id")))
    except (ValueError, TypeError, AttributeError):
        return None


@socketio.on("mark_message_read")
def mark_message_read(data: object):
    user = getattr(request, "current_user", None)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    message_id = _mark_id(data)
    if message_id is None:
        return _failure("INVALID_MESSAGE_IDS", "Message ID must be a valid UUID")
    try:
        item, message, created = read_service.mark_read(user, message_id)
    except read_service.ReadError as error:
        return _failure(error.code, error.message)
    payload = {"message_id": str(message.id), "user_id": str(user.id), "read_at": item.read_at.isoformat()}
    if created:
        socketio.emit("message_read", payload, to=_room(message))
    return {"success": True, "data": payload}


@socketio.on("mark_messages_read")
def mark_messages_read(data: object):
    user = getattr(request, "current_user", None)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    message_ids, errors = validate_message_ids(data)
    if errors:
        return _failure("INVALID_MESSAGE_IDS", "Invalid message IDs")
    try:
        created, messages = read_service.mark_many(user, message_ids)
    except read_service.ReadError as error:
        return _failure(error.code, error.message)
    payload = {
        "user_id": str(user.id),
        "messages": [{"message_id": str(item.message_id), "read_at": item.read_at.isoformat()} for item in created],
    }
    for message in messages:
        if any(item.message_id == message.id for item in created):
            socketio.emit("messages_read", payload, to=_room(message))
    return {"success": True, "data": payload}
