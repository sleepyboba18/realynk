from uuid import UUID

from flask import request

from app.extensions.socketio import socketio
from app.schemas.reaction import validate_reaction
from app.services import reaction_service


def _failure(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def _room(message) -> str:
    prefix = "channel" if message.channel_id else "conversation"
    value = message.channel_id or message.conversation_id
    return f"{prefix}:{value}"


@socketio.on("add_reaction")
def add_reaction(data: object):
    user = getattr(request, "current_user", None)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    if not isinstance(data, dict) or not isinstance(data.get("message_id"), str):
        return _failure("INVALID_REACTION", "A valid message ID and emoji are required")
    try:
        message_id = UUID(data["message_id"])
    except ValueError:
        return _failure("MESSAGE_NOT_FOUND", "Message not found")
    errors = validate_reaction({"emoji": data.get("emoji")})
    if errors:
        return _failure("INVALID_REACTION", "Invalid reaction")
    try:
        reaction, message = reaction_service.add_reaction(user, message_id, data["emoji"])
    except reaction_service.ReactionError as error:
        return _failure(error.code, error.message)
    payload = {"message_id": str(message.id), "reaction": reaction.to_dict()}
    socketio.emit("reaction_added", payload, to=_room(message))
    return {"success": True, "data": payload}


@socketio.on("remove_reaction")
def remove_reaction(data: object):
    user = getattr(request, "current_user", None)
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    if not isinstance(data, dict):
        return _failure("INVALID_REACTION", "A valid message ID and emoji are required")
    try:
        message_id = UUID(str(data.get("message_id")))
    except (ValueError, TypeError, AttributeError):
        return _failure("MESSAGE_NOT_FOUND", "Message not found")
    errors = validate_reaction({"emoji": data.get("emoji")})
    if errors:
        return _failure("INVALID_REACTION", "Invalid reaction")
    try:
        reaction, message = reaction_service.remove_reaction(user, message_id, data["emoji"])
    except reaction_service.ReactionError as error:
        return _failure(error.code, error.message)
    payload = {"message_id": str(message.id), "user_id": str(user.id), "emoji": reaction.emoji}
    socketio.emit("reaction_removed", payload, to=_room(message))
    return {"success": True, "data": payload}
