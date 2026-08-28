from uuid import UUID

from flask import request
from flask_socketio import emit, join_room, leave_room

from app.extensions.socketio import socketio
from app.services.conversation_service import ConversationError, get_for_user


def _result(success: bool, conversation_id: UUID | None = None, code: str | None = None, message: str | None = None):
    if success:
        return {"success": True, "conversation_id": str(conversation_id)}
    return {"success": False, "error": {"code": code, "message": message}}


def _current_user():
    return getattr(request, "current_user", None)


def _conversation_id(data: object):
    if not isinstance(data, dict):
        return None
    try:
        return UUID(str(data.get("conversation_id")))
    except (ValueError, TypeError, AttributeError):
        return None


def _authorize(data: object):
    user = _current_user()
    if user is None:
        return None, _result(False, code="AUTHENTICATION_REQUIRED", message="Authentication is required")
    conversation_id = _conversation_id(data)
    if conversation_id is None:
        return None, _result(False, code="CONVERSATION_NOT_FOUND", message="Conversation not found")
    try:
        conversation, _ = get_for_user(conversation_id, user.id)
    except ConversationError as error:
        return None, _result(False, code=error.code, message=error.message)
    return conversation_id, None


@socketio.on("join_conversation")
def handle_join_conversation(data: object):
    conversation_id, error = _authorize(data)
    if error:
        return error
    join_room(f"conversation:{conversation_id}")
    response = _result(True, conversation_id)
    emit("conversation_joined", response, to=request.sid)
    return response


@socketio.on("leave_conversation")
def handle_leave_conversation(data: object):
    conversation_id, error = _authorize(data)
    if error:
        return error
    leave_room(f"conversation:{conversation_id}")
    response = _result(True, conversation_id)
    emit("conversation_left", response, to=request.sid)
    return response
