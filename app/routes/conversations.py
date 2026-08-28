from math import ceil
from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.repositories import conversation_repository
from app.schemas.conversation import validate_create_conversation
from app.services import conversation_service
from app.utils.responses import error_response, success_response


conversations_bp = Blueprint("conversations", __name__, url_prefix="/api/v1/conversations")


def _domain_error(error: conversation_service.ConversationError):
    return error_response(error.code, error.message, error.status)


def _parse_id(value: str):
    try:
        return UUID(value)
    except ValueError:
        return None


def _pagination():
    try:
        page, per_page = int(request.args.get("page", 1)), int(request.args.get("per_page", 20))
    except ValueError:
        return None, error_response("VALIDATION_ERROR", "Invalid pagination", 422)
    if page < 1 or per_page < 1 or per_page > 100:
        return None, error_response("VALIDATION_ERROR", "Invalid pagination", 422)
    return (page, per_page), None


@conversations_bp.post("")
@auth_required
def create_conversation():
    data = request.get_json(silent=True)
    errors = validate_create_conversation(data)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    try:
        conversation, created = conversation_service.create_or_reopen(
            g.current_user.id, UUID(str(data["user_id"]))
        )
    except conversation_service.ConversationError as error:
        return _domain_error(error)
    return success_response(conversation.to_dict(), 201 if created else 200)


@conversations_bp.get("")
@auth_required
def list_conversations():
    pagination, error = _pagination()
    if error:
        return error
    page, per_page = pagination
    items, total = conversation_repository.list_for_user(g.current_user.id, page, per_page)
    return success_response({
        "items": [item.to_dict() for item in items],
        "pagination": {"page": page, "per_page": per_page, "total": total, "pages": ceil(total / per_page)},
    })


@conversations_bp.get("/<conversation_id>")
@auth_required
def get_conversation(conversation_id: str):
    parsed = _parse_id(conversation_id)
    if parsed is None:
        return error_response("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    try:
        conversation, _ = conversation_service.get_for_user(parsed, g.current_user.id)
    except conversation_service.ConversationError as error:
        return _domain_error(error)
    return success_response(conversation.to_dict())


@conversations_bp.get("/<conversation_id>/participants")
@auth_required
def list_participants(conversation_id: str):
    parsed = _parse_id(conversation_id)
    if parsed is None:
        return error_response("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    try:
        conversation, _ = conversation_service.get_for_user(parsed, g.current_user.id)
    except conversation_service.ConversationError as error:
        return _domain_error(error)
    return success_response({"items": [participant.to_dict() for participant in conversation.participants]})


@conversations_bp.post("/<conversation_id>/leave")
@auth_required
def leave_conversation(conversation_id: str):
    parsed = _parse_id(conversation_id)
    if parsed is None:
        return error_response("CONVERSATION_NOT_FOUND", "Conversation not found", 404)
    try:
        conversation, participant = conversation_service.get_for_user(parsed, g.current_user.id)
        conversation_service.leave(conversation, participant)
    except conversation_service.ConversationError as error:
        return _domain_error(error)
    return success_response({"message": "Left conversation"})
