"""Sliding-window rate limiter and Retry-After header parser for Auvik MCP.

SlidingWindowRateLimiter enforces a maximum number of calls per rolling
time window using a monotonic clock and asyncio.Lock + deque.

parse_retry_after() extracts the integer delay from a Retry-After response
header, returning None (and logging a warning) if the value is absent or
cannot be parsed as an integer.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """Async sliding-window rate limiter.

    Allows at most *max_calls* calls within any rolling *period* seconds.
    Callers await ``acquire()``; if the window is full, it sleeps until
    the oldest recorded call falls outside the window, then proceeds.
    """

    def __init__(self, max_calls: int, period: float) -> None:
        self._max_calls = max_calls
        self._period = period
        self._timestamps: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a call slot is available, then record the call."""
        async with self._lock:
            now = time.monotonic()
            # Evict timestamps older than the window.
            while self._timestamps and now - self._timestamps[0] >= self._period:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_calls:
                # Sleep until the oldest call exits the window.
                oldest = self._timestamps[0]
                sleep_for = self._period - (now - oldest)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                # Re-evict after sleeping (time has passed).
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._period:
                    self._timestamps.popleft()

            self._timestamps.append(time.monotonic())


def parse_retry_after(headers) -> Optional[int]:
    """Parse the Retry-After header value into integer seconds.

    Accepts either an httpx ``Headers`` object (case-insensitive) or a plain
    dict. The lookup is case-insensitive because ``dict(response.headers)``
    lowercases header names, which would otherwise miss the canonical
    ``Retry-After`` spelling and silently fall back to the caller's default.

    Returns:
        Integer seconds if the header is present and parsable as int.
        None if the header is absent or contains a non-integer value
        (a warning is logged in the latter case).
    """
    value = headers.get("Retry-After")
    if value is None:
        value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning("Could not parse Retry-After header value: %r", value)
        return None
