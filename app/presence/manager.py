from collections import defaultdict
from threading import RLock
from uuid import UUID


class PresenceManager:
    """Thread-safe user-to-socket presence state for one backend process."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[str]] = defaultdict(set)
        self._socket_users: dict[str, UUID] = {}
        self._lock = RLock()

    def register(self, user_id: UUID, socket_id: str) -> bool:
        with self._lock:
            connections = self._connections[user_id]
            became_online = not connections
            connections.add(socket_id)
            self._socket_users[socket_id] = user_id
            return became_online

    def unregister(self, socket_id: str) -> tuple[UUID | None, bool]:
        with self._lock:
            user_id = self._socket_users.pop(socket_id, None)
            if user_id is None:
                return None, False
            connections = self._connections.get(user_id)
            if not connections:
                return user_id, False
            connections.discard(socket_id)
            became_offline = not connections
            if became_offline:
                self._connections.pop(user_id, None)
            return user_id, became_offline

    def is_online(self, user_id: UUID) -> bool:
        with self._lock:
            return bool(self._connections.get(user_id))

    def status(self, user_id: UUID) -> str:
        return "online" if self.is_online(user_id) else "offline"

    def get_connection_count(self, user_id: UUID) -> int:
        with self._lock:
            return len(self._connections.get(user_id, set()))

    def socket_ids_for_users(self, user_ids: set[UUID]) -> dict[UUID, set[str]]:
        with self._lock:
            return {
                user_id: set(self._connections.get(user_id, set()))
                for user_id in user_ids
                if self._connections.get(user_id)
            }


presence_manager = PresenceManager()
