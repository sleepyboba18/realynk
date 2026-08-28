from uuid import UUID

from flask import request
from flask_socketio import emit

from app.extensions.socketio import socketio
from app.schemas.message import validate_create_message
from app.services import message_service


def _failure(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def _room(message):
    prefix, value = ("channel", message.channel_id) if message.channel_id else ("conversation", message.conversation_id)
    return f"{prefix}:{value}"


@socketio.on("send_message")
def handle_send_message(data: object):
    user = getattr(request, "current_user", None)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    errors = validate_create_message(data)
    if errors:
        return _failure("VALIDATION_ERROR", "Invalid message request")
    try:
        channel_id = UUID(str(data["channel_id"])) if data.get("channel_id") is not None else None
        conversation_id = UUID(str(data["conversation_id"])) if data.get("conversation_id") is not None else None
        message = message_service.create_message(user, data["content"], channel_id, conversation_id)
    except message_service.MessageError as error:
        return _failure(error.code, error.message)
    except (ValueError, TypeError):
        return _failure("INVALID_MESSAGE_CONTEXT", "Message context must be a valid UUID")
    payload = message.to_dict()
    socketio.emit("message_created", payload, to=_room(message))
    return {"success": True, "data": {"message": payload}}
