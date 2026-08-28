from uuid import UUID

from app.extensions.socketio import socketio


def room(user_id: UUID) -> str:
    return f"user:{user_id}"


def emit_to_user(user_id: UUID, event: str, payload: dict[str, object]) -> None:
    socketio.emit(event, payload, to=room(user_id))
