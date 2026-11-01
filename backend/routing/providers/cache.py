from copy import deepcopy
from threading import Lock
from time import monotonic
from typing import Any


class TtlCache:
    """Tiny process-local cache for repeat provider reads; no persistence required."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            created_at, value = entry
            if monotonic() - created_at >= self.ttl_seconds:
                self._entries.pop(key, None)
                return None
            return deepcopy(value)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._entries[key] = (monotonic(), deepcopy(value))

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
