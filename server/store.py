import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional, Protocol


@dataclass
class SessionState:
    forward: dict[str, str] = field(default_factory=dict)
    reverse: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    expires_at: float = 0.0


class Store(Protocol):
    def get_or_create(self, session_id: str) -> SessionState: ...
    def get(self, session_id: str) -> Optional[SessionState]: ...
    def delete(self, session_id: str) -> bool: ...


class InMemoryStore:
    def __init__(self, ttl_seconds: float = 3600.0) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, SessionState] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str) -> SessionState:
        now = time.monotonic()
        with self._lock:
            self._purge_locked(now)
            state = self._data.get(session_id)
            if state is None:
                state = SessionState()
                self._data[session_id] = state
            state.expires_at = now + self._ttl
            return state

    def get(self, session_id: str) -> Optional[SessionState]:
        now = time.monotonic()
        with self._lock:
            state = self._data.get(session_id)
            if state is None:
                return None
            if state.expires_at < now:
                self._data.pop(session_id, None)
                return None
            state.expires_at = now + self._ttl
            return state

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._data.pop(session_id, None) is not None

    def _purge_locked(self, now: float) -> None:
        expired = [sid for sid, s in self._data.items() if s.expires_at < now]
        for sid in expired:
            self._data.pop(sid, None)
