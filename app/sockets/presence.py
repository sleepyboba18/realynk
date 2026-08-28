from flask import request
from app.extensions.socketio import socketio
from app.services import presence_service, typing_service


def _failure(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def _context(data: object):
    user = getattr(request, "current_user", None)
    if user is None:
        return None, _failure("AUTHENTICATION_REQUIRED", "Authentication is required")
    try:
        return (user, *typing_service.validate_context(user.id, data)), None
    except typing_service.TypingError as error:
        return None, _failure(error.code, error.message)


def _handle_typing(data: object, starting: bool):
    context, error = _context(data)
    if error:
        return error
    user, context_type, context_id = context
    changed = (
        typing_service.start(user.id, request.sid, context_type, context_id)
        if starting
        else typing_service.stop(user.id, request.sid, context_type, context_id)
    )
    if changed:
        event = "user_typing" if starting else "user_stopped_typing"
        socketio.emit(
            event,
            typing_service.event_payload(user.id, context_type, context_id),
            to=typing_service.room(context_type, context_id),
        )
    return {"success": True, "typing": starting, "changed": changed}


@socketio.on("typing_start")
def handle_typing_start(data: object):
    return _handle_typing(data, True)


@socketio.on("typing_stop")
def handle_typing_stop(data: object):
    return _handle_typing(data, False)


def cleanup_typing_socket(socket_id: str) -> None:
    for user_id, context_type, context_id in typing_service.cleanup_socket(socket_id):
        socketio.emit(
            "user_stopped_typing",
            typing_service.event_payload(user_id, context_type, context_id),
            to=typing_service.room(context_type, context_id),
        )


def broadcast_presence(user_id, last_seen_at=None) -> None:
    event = presence_service.payload(user_id, last_seen_at)
    for socket_id in presence_service.recipient_socket_ids(user_id):
        socketio.emit("presence_update", event, to=socket_id)
