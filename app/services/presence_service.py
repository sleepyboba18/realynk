import logging
from datetime import datetime, timezone
from uuid import UUID

from flask import current_app

from app.extensions.database import db
from app.permissions.presence_permissions import can_view_presence
from app.presence.manager import presence_manager
from app.repositories import presence_repository


logger = logging.getLogger(__name__)


def payload(user_id: UUID, last_seen_at=None) -> dict[str, object]:
    online = presence_manager.is_online(user_id)
    return {
        "user_id": str(user_id),
        "status": "online" if online else "offline",
        "last_seen_at": None if online else _isoformat(last_seen_at),
    }


def register_connection(user_id: UUID, socket_id: str) -> bool:
    return presence_manager.register(user_id, socket_id)


def unregister_connection(socket_id: str) -> tuple[UUID | None, bool]:
    return presence_manager.unregister(socket_id)


def persist_last_seen(user_id: UUID):
    user = presence_repository.get_user(user_id)
    if user is None:
        return None
    timestamp = datetime.now(timezone.utc)
    user.last_seen_at = timestamp
    db.session.commit()
    return timestamp


def visible_recipient_socket_ids(user_id: UUID) -> set[str]:
    recipient_ids = presence_repository.visible_user_ids(user_id, [user_id])
    return {
        socket_id
        for sockets in presence_manager.socket_ids_for_users(recipient_ids).values()
        for socket_id in sockets
    }


def recipient_socket_ids(user_id: UUID) -> set[str]:
    candidate_ids = presence_repository.shared_observer_ids(user_id)
    candidate_ids.add(user_id)
    return {
        socket_id
        for sockets in presence_manager.socket_ids_for_users(candidate_ids).values()
        for socket_id in sockets
    }


def can_view(viewer, target) -> bool:
    return can_view_presence(viewer, target)


def _isoformat(value) -> str | None:
    return value.isoformat() if value else None
