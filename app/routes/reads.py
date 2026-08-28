from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.repositories import read_repository
from app.schemas.read import validate_message_ids
from app.services import read_service
from app.utils.responses import error_response, success_response


reads_bp = Blueprint("reads", __name__, url_prefix="/api/v1/messages")


def _id(value: str):
    try:
        return UUID(value)
    except ValueError:
        return None


def _error(error: read_service.ReadError):
    return error_response(error.code, error.message, error.status)


def _room(message) -> str:
    prefix = "channel" if message.channel_id else "conversation"
    value = message.channel_id or message.conversation_id
    return f"{prefix}:{value}"


def _emit_read(message, item):
    from app.extensions.socketio import socketio
    socketio.emit("message_read", {"message_id": str(message.id), "user_id": str(item.user_id), "read_at": item.read_at.isoformat()}, to=_room(message))


@reads_bp.post("/<message_id>/read")
@auth_required
def mark_read(message_id: str):
    parsed = _id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    try:
        item, message, created = read_service.mark_read(g.current_user, parsed)
    except read_service.ReadError as error:
        return _error(error)
    if created:
        _emit_read(message, item)
    return success_response(item.to_dict())


@reads_bp.post("/read")
@auth_required
def mark_many():
    message_ids, errors = validate_message_ids(request.get_json(silent=True))
    if errors:
        return error_response("INVALID_MESSAGE_IDS", "Invalid message IDs", 422, errors)
    try:
        created, messages = read_service.mark_many(g.current_user, message_ids)
    except read_service.ReadError as error:
        return _error(error)
    if created:
        from app.extensions.socketio import socketio
        message_by_id = {message.id: message for message in messages}
        events_by_room = {}
        for item in created:
            message = message_by_id[item.message_id]
            events_by_room.setdefault(_room(message), []).append(
                {"message_id": str(item.message_id), "read_at": item.read_at.isoformat()}
            )
        for room, event_messages in events_by_room.items():
            socketio.emit(
                "messages_read",
                {"user_id": str(g.current_user.id), "messages": event_messages},
                to=room,
            )
    return success_response({"items": [item.to_dict() for item in created]})


@reads_bp.get("/<message_id>/reads")
@auth_required
def read_summary(message_id: str):
    parsed = _id(message_id)
    if parsed is None:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    try:
        summary, _ = read_service.summary(g.current_user, parsed)
    except read_service.ReadError as error:
        return _error(error)
    return success_response(summary)


@reads_bp.get("/unread")
@auth_required
def unread():
    return success_response({"total_unread": read_repository.unread_count(g.current_user.id)})
