"""Sliding-window rate limiter for the Claroty xDome REST API.

xDome enforces 2000 requests per minute per endpoint and returns HTTP 429
with a Retry-After header on quota exhaustion. This module gates outgoing
requests with a monotonic-clock sliding window so the client never trips
the upstream limit under normal load. The window is shared across all
endpoints because the limiter sits in front of every POST in
``ClarotyClient.post()``.
"""

from __future__ import annotations

import asyncio
import collections
import logging
import time
from typing import Deque

logger = logging.getLogger("claroty-mcp.rate")

_WINDOW_SECONDS = 60.0


class SlidingWindowRateLimiter:
    """Async sliding-window rate limiter.

    Tracks call timestamps in a deque. On each acquire():
      1. Drop timestamps older than the window.
      2. If the deque is at capacity, sleep until the oldest timestamp
         falls outside the window.
      3. Record the new timestamp and return.

    Safe for concurrent use under asyncio; a single asyncio.Lock guards
    the deque so two coroutines cannot both decide there is room.
    """

    def __init__(self, max_per_minute: int) -> None:
        if max_per_minute <= 0:
            raise ValueError("max_per_minute must be positive")
        self._max = max_per_minute
        self._calls: Deque[float] = collections.deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - _WINDOW_SECONDS
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()

            if len(self._calls) >= self._max:
                wait = self._calls[0] + _WINDOW_SECONDS - now
                if wait > 0:
                    logger.info(
                        "Rate limit reached (%d/min); sleeping %.2fs",
                        self._max,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    # Re-trim after waking
                    now = time.monotonic()
                    cutoff = now - _WINDOW_SECONDS
                    while self._calls and self._calls[0] < cutoff:
                        self._calls.popleft()

            self._calls.append(time.monotonic())
