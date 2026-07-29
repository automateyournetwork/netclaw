"""Sliding-window rate limiter and Retry-After header parser for the Halo MCP.

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
            while self._timestamps and now - self._timestamps[0] >= self._period:
                self._timestamps.popleft()

            if len(self._timestamps) >= self._max_calls:
                oldest = self._timestamps[0]
                sleep_for = self._period - (now - oldest)
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._period:
                    self._timestamps.popleft()

            self._timestamps.append(time.monotonic())


def parse_retry_after(headers: dict) -> Optional[int]:
    """Parse the Retry-After header value into integer seconds.

    Returns:
        Integer seconds if the header is present and parsable as int.
        None if the header is absent or contains a non-integer value
        (a warning is logged in the latter case).
    """
    value = headers.get("Retry-After")
    if value is None:
        # A plain dict(resp.headers) lowercases header names — be case-insensitive.
        value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning("Could not parse Retry-After header value: %r", value)
        return None
