from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.schemas.reaction import validate_reaction
from app.services import reaction_service
from app.utils.responses import error_response, success_response


reactions_bp = Blueprint("reactions", __name__, url_prefix="/api/v1/messages")


def _message_id(value: str):
    try:
        return UUID(value)
    except ValueError:
        return None


def _error(error: reaction_service.ReactionError):
    return error_response(error.code, error.message, error.status)


@reactions_bp.post("/<message_id>/reactions")
@auth_required
def add_reaction(message_id: str):
    parsed = _message_id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    data = request.get_json(silent=True)
    errors = validate_reaction(data)
    if errors:
        return error_response("INVALID_REACTION", "Invalid reaction", 422, errors)
    try:
        reaction, message = reaction_service.add_reaction(g.current_user, parsed, data["emoji"])
    except reaction_service.ReactionError as error:
        return _error(error)
    from app.extensions.socketio import socketio
    socketio.emit("reaction_added", {"message_id": str(message.id), "reaction": reaction.to_dict()}, to=_room(message))
    return success_response(reaction.to_dict(), 201)


@reactions_bp.delete("/<message_id>/reactions")
@auth_required
def remove_reaction(message_id: str):
    parsed = _message_id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    data = request.get_json(silent=True)
    errors = validate_reaction(data)
    if errors:
        return error_response("INVALID_REACTION", "Invalid reaction", 422, errors)
    try:
        reaction, message = reaction_service.remove_reaction(g.current_user, parsed, data["emoji"])
    except reaction_service.ReactionError as error:
        return _error(error)
    from app.extensions.socketio import socketio
    socketio.emit("reaction_removed", {"message_id": str(message.id), "user_id": str(g.current_user.id), "emoji": reaction.emoji}, to=_room(message))
    return success_response({"message": "Reaction removed"})


@reactions_bp.get("/<message_id>/reactions")
@auth_required
def list_reactions(message_id: str):
    parsed = _message_id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    try:
        reactions, _ = reaction_service.list_reactions(g.current_user, parsed)
    except reaction_service.ReactionError as error:
        return _error(error)
    return success_response({"reactions": reactions})


def _room(message) -> str:
    prefix = "channel" if message.channel_id else "conversation"
    value = message.channel_id or message.conversation_id
    return f"{prefix}:{value}"
