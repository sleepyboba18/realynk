from uuid import UUID

from flask import current_app

from app.extensions.socketio import socketio
from app.presence.typing_manager import typing_manager
from app.services.channel_service import ChannelError, get_channel_for_user
from app.services.conversation_service import get_for_user


class TypingError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def validate_context(user_id: UUID, data: object) -> tuple[str, UUID]:
    if not isinstance(data, dict):
        raise TypingError("INVALID_TYPING_CONTEXT", "Exactly one typing context is required")
    values = [(key, data.get(key)) for key in ("channel_id", "conversation_id") if data.get(key) is not None]
    if len(values) != 1:
        raise TypingError("INVALID_TYPING_CONTEXT", "Exactly one typing context is required")
    context_type, raw_id = values[0]
    try:
        context_id = UUID(str(raw_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise TypingError("INVALID_TYPING_CONTEXT", "Context ID must be a valid UUID") from exc
    try:
        if context_type == "channel_id":
            get_channel_for_user(context_id, user_id)
            return "channel", context_id
        get_for_user(context_id, user_id)
        return "conversation", context_id
    except Exception as exc:
        if isinstance(exc, (ChannelError,)) or hasattr(exc, "code"):
            raise TypingError("TYPING_ACCESS_DENIED", "You do not have access to this context") from exc
        raise


def start(user_id: UUID, socket_id: str, context_type: str, context_id: UUID) -> bool:
    typing_manager.timeout_seconds = current_app.config["TYPING_TIMEOUT_SECONDS"]
    return typing_manager.start(user_id, socket_id, context_type, context_id, on_timeout)


def stop(user_id: UUID, socket_id: str, context_type: str, context_id: UUID) -> bool:
    return typing_manager.stop(user_id, socket_id, context_type, context_id)


def cleanup_socket(socket_id: str) -> list[tuple[UUID, str, UUID]]:
    return typing_manager.cleanup_socket(socket_id)


def on_timeout(key: tuple[UUID, str, UUID]) -> None:
    user_id, context_type, context_id = key
    socketio.emit("user_stopped_typing", event_payload(user_id, context_type, context_id), to=room(context_type, context_id))


def event_payload(user_id: UUID, context_type: str, context_id: UUID) -> dict[str, object]:
    return {
        "user_id": str(user_id),
        "channel_id": str(context_id) if context_type == "channel" else None,
        "conversation_id": str(context_id) if context_type == "conversation" else None,
    }


def room(context_type: str, context_id: UUID) -> str:
    return f"{context_type}:{context_id}"
