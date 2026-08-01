"""Rate budget enforcement: 5 calls/second and 30 calls/minute.

Spec 078 FR-013, FR-013a, FR-013b. Research R5.

**The order here is contractual, not stylistic:**

    1. de-duplicate by (ostype, normalised version)
    2. serve from the on-disk cache
    3. pace what remains to 5/sec and 30/min
    4. back off on 429, and report if it persists

De-duplication comes first because it is by far the largest win and costs a
dictionary lookup: a 60-device fleet running 12 distinct versions costs 12 calls
de-duplicated, or 60 not — one-third of the minute budget versus twice it. Pacing
an un-de-duplicated sweep does not fix that; it just spreads the same excess over
more minutes.

30/min is the binding constraint, not 5/sec. Anything that respects 30/min at a
steady rate is nowhere near 5/sec, so the per-second limiter only matters for a
burst.
"""

from __future__ import annotations

import threading
import time

PER_SECOND = 5
PER_MINUTE = 30

# 429 backoff. Deliberately short and few: a caller waiting on a fleet sweep is
# better served by an api_error naming the rate limit than by a five-minute hang.
BACKOFF_S = (2, 5, 15)


class RateLimiter:
    """Sliding-window pacer shared by every caller of the credential.

    Thread-safe because fleet fan-out is concurrent, and two threads each believing
    they hold the last slot is how a 429 happens.
    """

    def __init__(self, per_second: int = PER_SECOND, per_minute: int = PER_MINUTE):
        self.per_second = per_second
        self.per_minute = per_minute
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - 60
        self._calls = [t for t in self._calls if t > cutoff]

    def calls_remaining(self) -> int:
        """Estimated calls left in the current minute. For psirt_status."""
        with self._lock:
            self._prune(time.time())
            return max(0, self.per_minute - len(self._calls))

    def acquire(self) -> float:
        """Block until a call is permitted. Returns the seconds spent waiting."""
        waited = 0.0
        while True:
            with self._lock:
                now = time.time()
                self._prune(now)
                recent_second = [t for t in self._calls if t > now - 1]
                if len(recent_second) >= self.per_second:
                    sleep_for = 1 - (now - min(recent_second)) + 0.01
                elif len(self._calls) >= self.per_minute:
                    sleep_for = 60 - (now - min(self._calls)) + 0.01
                else:
                    self._calls.append(now)
                    return waited
            sleep_for = max(0.01, sleep_for)
            time.sleep(sleep_for)
            waited += sleep_for


def dedupe(keys) -> dict:
    """Collapse an iterable of hashable keys, preserving first-seen order.

    Step 1 of the contractual order. Returns {key: [positions]} so a fleet caller
    can fan one result back out to every device that shares the version — the whole
    point of de-duplicating rather than merely counting.
    """
    grouped: dict = {}
    for index, key in enumerate(keys):
        grouped.setdefault(key, []).append(index)
    return grouped
