from dataclasses import dataclass, field
from threading import RLock, Timer
from uuid import UUID


@dataclass
class TypingState:
    sources: set[str] = field(default_factory=set)
    timer: Timer | None = None


class TypingManager:
    """Thread-safe, process-local typing state keyed by user and context."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self._states: dict[tuple[UUID, str, UUID], TypingState] = {}
        self._lock = RLock()

    def start(self, user_id: UUID, socket_id: str, context_type: str, context_id: UUID, on_timeout) -> bool:
        key = (user_id, context_type, context_id)
        with self._lock:
            state = self._states.setdefault(key, TypingState())
            became_typing = not state.sources
            state.sources.add(socket_id)
            if state.timer:
                state.timer.cancel()
            state.timer = Timer(self.timeout_seconds, self._expire, args=(key, on_timeout))
            state.timer.daemon = True
            state.timer.start()
            return became_typing

    def stop(self, user_id: UUID, socket_id: str, context_type: str, context_id: UUID) -> bool:
        key = (user_id, context_type, context_id)
        with self._lock:
            state = self._states.get(key)
            if state is None:
                return False
            state.sources.discard(socket_id)
            if state.sources:
                return False
            if state.timer:
                state.timer.cancel()
            self._states.pop(key, None)
            return True

    def cleanup_socket(self, socket_id: str) -> list[tuple[UUID, str, UUID]]:
        stopped: list[tuple[UUID, str, UUID]] = []
        with self._lock:
            for key, state in list(self._states.items()):
                state.sources.discard(socket_id)
                if state.sources:
                    continue
                if state.timer:
                    state.timer.cancel()
                self._states.pop(key, None)
                stopped.append(key)
        return stopped

    def _expire(self, key, on_timeout) -> None:
        with self._lock:
            state = self._states.pop(key, None)
            if state is None:
                return
            state.timer = None
        on_timeout(key)

    def is_typing(self, user_id: UUID, context_type: str, context_id: UUID) -> bool:
        with self._lock:
            state = self._states.get((user_id, context_type, context_id))
            return bool(state and state.sources)


typing_manager = TypingManager()
