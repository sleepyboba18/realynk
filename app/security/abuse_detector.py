from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class AbuseSignal:
    event_type: str
    user_id: str | None = None
    ip_address: str | None = None
    route: str | None = None
    score: int = 0
    window_seconds: int = 60
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "route": self.route,
            "score": self.score,
            "window_seconds": self.window_seconds,
            "created_at": (self.created_at or datetime.now(timezone.utc)).isoformat(),
        }


class AbuseDetector:
    def __init__(self) -> None:
        self._signals: dict[tuple[str, str | None, str | None], list[datetime]] = {}

    def record(self, event_type: str, *, user_id: str | None = None, ip_address: str | None = None, route: str | None = None) -> int:
        window = datetime.now(timezone.utc) - timedelta(minutes=1)
        key = (event_type, user_id, ip_address)
        timestamps = self._signals.setdefault(key, [])
        timestamps[:] = [stamp for stamp in timestamps if stamp >= window]
        timestamps.append(datetime.now(timezone.utc))
        return len(timestamps)

    def score(self, *, user_id: str | None = None, ip_address: str | None = None, route: str | None = None) -> int:
        score = 0
        for key, timestamps in self._signals.items():
            event_type, key_user, key_ip = key
            if user_id and key_user and key_user == user_id:
                score += len(timestamps)
            if ip_address and key_ip and key_ip == ip_address:
                score += len(timestamps)
            if route and event_type == "rate_limit_exceeded" and route == route:
                score += 1
        return score


def default_abuse_signal(event_type: str, **kwargs: Any) -> AbuseSignal:
    return AbuseSignal(event_type=event_type, created_at=datetime.now(timezone.utc), **kwargs)
