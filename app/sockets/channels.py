from uuid import UUID

from flask import request
from flask_socketio import emit, join_room, leave_room

from app.extensions.socketio import socketio
from app.repositories import channel_repository
from app.services.channel_service import ChannelError, get_channel_for_user


def _failure(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def _success(channel_id: UUID) -> dict[str, object]:
    return {"success": True, "channel_id": str(channel_id)}


def _socket_user():
    return getattr(request, "current_user", None)


@socketio.on("join_channel")
def handle_join_channel(data: object):
    user = _socket_user()
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    if not isinstance(data, dict):
        return _failure("VALIDATION_ERROR", "A channel_id is required")
    try:
        channel_id = UUID(str(data.get("channel_id")))
    except (ValueError, TypeError, AttributeError):
        return _failure("CHANNEL_NOT_FOUND", "Channel not found")
    try:
        get_channel_for_user(channel_id, user.id)
    except ChannelError as error:
        return _failure(error.code, error.message)
    join_room(f"channel:{channel_id}")
    response = _success(channel_id)
    emit("channel_joined", response, to=request.sid)
    return response


@socketio.on("leave_channel")
def handle_leave_channel(data: object):
    user = _socket_user()
    if user is None:
        return _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    if not isinstance(data, dict):
        return _failure("VALIDATION_ERROR", "A channel_id is required")
    try:
        channel_id = UUID(str(data.get("channel_id")))
    except (ValueError, TypeError, AttributeError):
        return _failure("CHANNEL_NOT_FOUND", "Channel not found")
    try:
        get_channel_for_user(channel_id, user.id)
    except ChannelError as error:
        return _failure(error.code, error.message)
    leave_room(f"channel:{channel_id}")
    response = _success(channel_id)
    emit("channel_left", response, to=request.sid)
    return response
