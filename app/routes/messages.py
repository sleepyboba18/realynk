from uuid import UUID

from flask import Blueprint, g, request
from flask_socketio import emit

from app.auth.decorators import auth_required
from app.extensions.socketio import socketio
from app.repositories import message_repository
from app.schemas.message import validate_create_message, validate_update_message
from app.services import message_service
from app.utils.responses import error_response, success_response


messages_bp = Blueprint("messages", __name__, url_prefix="/api/v1/messages")


def _error(error: message_service.MessageError):
    return error_response(error.code, error.message, error.status)


def _uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _room(message):
    prefix, value = ("channel", message.channel_id) if message.channel_id else ("conversation", message.conversation_id)
    return f"{prefix}:{value}"


def _broadcast(event: str, message):
    socketio.emit(event, message.to_dict(), to=_room(message))


@messages_bp.post("")
@auth_required
def create_message():
    data = request.get_json(silent=True)
    errors = validate_create_message(data)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    try:
        message = message_service.create_message(
            g.current_user,
            data["content"],
            _uuid(data.get("channel_id")),
            _uuid(data.get("conversation_id")),
        )
    except message_service.MessageError as error:
        return _error(error)
    _broadcast("message_created", message)
    return success_response({"message": message.to_dict()}, 201)


@messages_bp.get("")
@auth_required
def list_messages():
    context_values = {key: request.args.get(key) for key in ("channel_id", "conversation_id")}
    present = [key for key, value in context_values.items() if value is not None]
    if len(present) != 1:
        return error_response("MESSAGE_CONTEXT_REQUIRED", "Exactly one message context is required", 422)
    context_id = _uuid(context_values[present[0]])
    if context_id is None:
        return error_response("INVALID_MESSAGE_CONTEXT", "Message context must be a valid UUID", 422)

    try:
        limit = int(request.args.get("limit", request.args.get("per_page", 50)))
        page = int(request.args.get("page", 1))
    except ValueError:
        return error_response("VALIDATION_ERROR", "Invalid pagination", 422)
    if limit < 1 or limit > 100 or page < 1:
        return error_response("VALIDATION_ERROR", "Invalid pagination", 422)
    before_id = _uuid(request.args.get("before"))
    if request.args.get("before") is not None and before_id is None:
        return error_response("INVALID_MESSAGE_CURSOR", "Cursor must be a valid message ID", 422)
    if before_id and request.args.get("page"):
        return error_response("VALIDATION_ERROR", "Use either page or before, not both", 422)

    channel_id = context_id if present[0] == "channel_id" else None
    conversation_id = context_id if present[0] == "conversation_id" else None
    try:
        messages, has_more = message_service.list_messages(
            g.current_user.id,
            channel_id,
            conversation_id,
            limit,
            before_id,
            offset=(page - 1) * limit if before_id is None and request.args.get("page") else 0,
        )
    except message_service.MessageError as error:
        return _error(error)
    return success_response({
        "items": [message.to_dict() for message in messages],
        "pagination": {
            "page": page,
            "per_page": limit,
            "limit": limit,
            "has_more": has_more,
            "before": request.args.get("before"),
        },
    })


@messages_bp.patch("/<message_id>")
@auth_required
def edit_message(message_id: str):
    try:
        parsed_id = UUID(message_id)
    except ValueError:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    errors = validate_update_message(request.get_json(silent=True))
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    try:
        message = message_service.get_message_for_user(g.current_user.id, parsed_id)
        message = message_service.edit_message(g.current_user, message, request.json["content"])
    except message_service.MessageError as error:
        return _error(error)
    _broadcast("message_updated", message)
    return success_response({"message": message.to_dict()})


@messages_bp.delete("/<message_id>")
@auth_required
def delete_message(message_id: str):
    try:
        parsed_id = UUID(message_id)
    except ValueError:
        return error_response("MESSAGE_NOT_FOUND", "Message not found", 404)
    try:
        message = message_service.get_message_for_user(g.current_user.id, parsed_id)
        message = message_service.delete_message(g.current_user, message)
    except message_service.MessageError as error:
        return _error(error)
    socketio.emit(
        "message_deleted",
        {
            "id": str(message.id),
            "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
            "channel_id": str(message.channel_id) if message.channel_id else None,
            "conversation_id": str(message.conversation_id) if message.conversation_id else None,
        },
        to=_room(message),
    )
    return success_response({"message": message.to_dict()})
