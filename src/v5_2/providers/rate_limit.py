from __future__ import annotations

from collections.abc import Callable
from threading import Lock


class RateLimiter:
    def __init__(self, *, min_interval_seconds: float) -> None:
        if isinstance(min_interval_seconds, bool) or min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be non-negative")
        self.min_interval_seconds = float(min_interval_seconds)
        self._next_allowed: float | None = None
        self._lock = Lock()

    def acquire(
        self, monotonic_clock: Callable[[], float], sleeper: Callable[[float], None]
    ) -> None:
        with self._lock:
            now = monotonic_clock()
            if self._next_allowed is not None and now < self._next_allowed:
                sleeper(self._next_allowed - now)
                now = monotonic_clock()
            self._next_allowed = now + self.min_interval_seconds
