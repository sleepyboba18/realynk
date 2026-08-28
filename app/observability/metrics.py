from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = defaultdict(int)
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._active_connections = 0

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counts[name] += value

    def observe(self, name: str, duration_ms: float) -> None:
        with self._lock:
            self._timings.setdefault(name, []).append(duration_ms)
            if len(self._timings[name]) > 1000:
                self._timings[name] = self._timings[name][-1000:]

    def add_connection(self) -> None:
        with self._lock:
            self._active_connections += 1

    def remove_connection(self) -> None:
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counts": dict(self._counts),
                "active_connections": self._active_connections,
                "timings": {key: list(values) for key, values in self._timings.items()},
            }


metrics = Metrics()
