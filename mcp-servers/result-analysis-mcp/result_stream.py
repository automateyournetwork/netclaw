"""Bounded stream window with explicit drop and gap accounting (spec 187, US5).

A live feed is never "complete". This buffer keeps at most `capacity` events, drops the oldest
on overflow, and counts everything it did not keep, so any answer built from a snapshot can
state dropped events and reconnect gaps. Wiring a concrete live source is a follow-up.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

import result_retention as retention


class StreamBuffer:
    def __init__(self, capacity: int = 10000, name: str = "stream") -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self.name = name
        self._events: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self.received = 0
        self.dropped = 0
        self.gaps: list[dict] = []
        self.started_at = time.time()

    def push(self, event: Any) -> None:
        with self._lock:
            if len(self._events) == self.capacity:
                self.dropped += 1
            self._events.append(event)
            self.received += 1

    def record_gap(self, reason: str, *, started_at: float | None = None,
                   ended_at: float | None = None) -> None:
        """Record a discontinuity, e.g. a reconnect during which events may have been missed."""
        with self._lock:
            self.gaps.append({"reason": reason,
                              "started_at": started_at or time.time(),
                              "ended_at": ended_at})

    def stats(self) -> dict:
        with self._lock:
            return {"name": self.name, "capacity": self.capacity, "received": self.received,
                    "kept": len(self._events), "dropped": self.dropped,
                    "gaps": list(self.gaps), "started_at": self.started_at}

    def snapshot(self, *, tool: str, notes: list[str] | None = None) -> dict:
        """Retain the current window; the metadata carries the drop/gap counters."""
        with self._lock:
            events = list(self._events)
        return retention.retain(events, tool=tool, command=f"stream:{self.name}",
                                notes=notes, stream=self.stats())
