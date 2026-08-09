"""Polite HTTP against free community infrastructure. Spec 081, FR-023..FR-027.

RIPE NCC and PeeringDB are volunteer- and membership-funded. They publish no
rate-limit headers — measured 2026-08-03 on live 200 responses — so there is
nothing to negotiate against at runtime and the ceiling must be self-imposed.

    <= 4 requests/second per source, and STRICTLY SERIAL (concurrency 1).

Deliberately slower than possible. `peerglass`, the community server evaluated in
research R1, parallelises for latency; this does the opposite on purpose. Against
free infrastructure, being over-polite costs latency nobody notices, and being
under-polite costs the integration for everyone using NetClaw.

The limit is enforced HERE, at the request layer, not by caller discipline — so a
tool added later inherits it without needing to know it exists (FR-023b). The
composite `resource_report` is the tool most likely to attract an
`asyncio.gather`; routing it through this client is what prevents that.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_MAX_RPS = 4.0

#: Per-source cache TTLs in seconds. These differ by an order of magnitude
#: because the sources do (FR-026): a ROA can be published or withdrawn within
#: minutes, while an RIR allocation changes on the scale of months.
#:
#: A stale `valid` is the most dangerous stale value in this feature, which is
#: why RPKI gets the shortest life.
TTL_SECONDS: dict[str, float] = {
    "rpki": 300.0,        # 5 minutes
    "routing": 900.0,     # 15 minutes
    "rdap": 86400.0,      # 24 hours
    "peeringdb": 86400.0,
    "atlas": 86400.0,
}

USER_AGENT = os.environ.get(
    "BGP_INTEL_USER_AGENT",
    "NetClaw-bgp-intel/1.0 (+https://github.com/automateyournetwork/netclaw)",
)


def _max_rps() -> float:
    """Configurable downward only.

    An operator may wish to be *more* polite. Raising the ceiling is not a
    supported operation, so a value above the default is clamped rather than
    honoured.
    """
    raw = os.environ.get("BGP_INTEL_MAX_RPS")
    if not raw:
        return DEFAULT_MAX_RPS
    try:
        val = float(raw)
    except ValueError:
        return DEFAULT_MAX_RPS
    return min(val, DEFAULT_MAX_RPS) if val > 0 else DEFAULT_MAX_RPS


class RateLimited(RuntimeError):
    """The remote asked us to slow down. Backed off, not retried blindly."""


class SourceUnavailable(RuntimeError):
    """Transport-level failure. Distinct from "no record exists"."""

    def __init__(self, message: str, *, refused: bool = False) -> None:
        super().__init__(message)
        #: True when the remote actively rejected us (e.g. ARIN's connection
        #: reset) rather than merely timing out.
        self.refused = refused


@dataclass
class _CacheEntry:
    value: Any
    stored_at: float


class PoliteClient:
    """One rate-limited, cached HTTP client shared by every source module.

    In-memory and session-scoped: nothing persists across a restart, and there is
    no on-disk store (FR-026a). Deliberately unlike spec 078, which caches PSIRT
    data on disk because that data is large and genuinely slow-moving. Here the
    cache is a courtesy buffer for one investigation, not a registry mirror.
    """

    def __init__(self, *, timeout: float = 20.0) -> None:
        self._timeout = timeout
        self._cache: dict[tuple[str, str], _CacheEntry] = {}
        # One lock per source enforces concurrency 1 *per source* while still
        # allowing different sources to proceed independently.
        self._locks: dict[str, asyncio.Lock] = {}
        # Timestamps of recent requests per source, for a true SLIDING WINDOW.
        #
        # A simple "minimum gap of 1/rps" only bounds the rate asymptotically:
        # N requests spaced 250ms apart span (N-1)*0.25s, so five of them fit
        # inside a single second — 5 requests/second against a ceiling of 4. A
        # contract test caught exactly that. Against volunteer-funded
        # infrastructure the literal reading of "<= 4 requests per second" is the
        # one that matters, so the window is enforced properly.
        self._recent: dict[str, list[float]] = {}

    def _lock(self, source_key: str) -> asyncio.Lock:
        if source_key not in self._locks:
            self._locks[source_key] = asyncio.Lock()
        return self._locks[source_key]

    async def _await_window_slot(self, source_key: str) -> None:
        """Block until issuing a request keeps this source under the ceiling.

        Guarantees that **no one-second window ever contains more than `max_rps`
        requests** to a given source — the literal reading of FR-023, rather than
        the weaker "minimum gap" property that lets a burst of five slip into one
        second.
        """
        limit = int(_max_rps())
        recent = self._recent.setdefault(source_key, [])
        while True:
            now = time.monotonic()
            # Drop anything older than the window; it no longer constrains us.
            recent[:] = [t for t in recent if now - t < 1.0]
            if len(recent) < limit:
                recent.append(now)
                return
            # Wait until the oldest request falls out of the window.
            await asyncio.sleep(max(0.0, 1.0 - (now - recent[0])) + 0.001)

    def cached_age(self, source_key: str, url: str) -> float | None:
        entry = self._cache.get((source_key, url))
        if entry is None:
            return None
        age = time.monotonic() - entry.stored_at
        return age if age <= TTL_SECONDS.get(source_key, 300.0) else None

    async def get_json(
        self,
        source_key: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        fresh: bool = False,
    ) -> tuple[Any, bool, float | None]:
        """GET JSON. Returns `(payload, was_cached, cache_age_seconds)`.

        `source_key` selects both the TTL and the rate-limit bucket.
        `fresh=True` bypasses the cache — for when a ROA was just published and
        the 5-minute TTL is the only thing between the operator and the truth.
        """
        cache_key = (source_key, url + repr(sorted((params or {}).items())))

        if not fresh:
            entry = self._cache.get(cache_key)
            if entry is not None:
                age = time.monotonic() - entry.stored_at
                if age <= TTL_SECONDS.get(source_key, 300.0):
                    return entry.value, True, age

        async with self._lock(source_key):
            # Serial per source, and rate-limited by a sliding window. Sleeping
            # while holding the lock is what makes the pacing real rather than
            # advisory — a caller cannot race past it.
            await self._await_window_slot(source_key)

            merged_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            merged_headers.update(headers or {})

            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url, params=params, headers=merged_headers)
            except httpx.HTTPError as exc:
                # `from None`: an httpx repr can carry the full URL. No credentials
                # exist in this feature, but the habit is worth keeping.
                raise SourceUnavailable(
                    f"{type(exc).__name__}", refused="Connect" in type(exc).__name__
                ) from None
            # The window slot was already claimed in _await_window_slot(), before
            # the request went out — claiming it after would let concurrent callers
            # slip past the ceiling in the gap between issuing and recording.

            if response.status_code in (429, 503):
                raise RateLimited(
                    f"{source_key} returned {response.status_code}; backing off "
                    "rather than retrying"
                )
            if response.status_code == 404:
                # A 404 from a registry means "no such resource", which is a real
                # answer — NOT a transport failure. The caller maps it to
                # NO_RECORD. Conflating the two is exactly what FR-011 forbids.
                return None, False, None
            response.raise_for_status()

            try:
                payload = response.json()
            except ValueError:
                raise SourceUnavailable(f"{source_key} returned non-JSON") from None

            self._cache[cache_key] = _CacheEntry(payload, time.monotonic())
            return payload, False, None


#: Module-level singleton. A single instance is what makes the per-source
#: serialisation meaningful — one lock per source, shared by every tool.
CLIENT = PoliteClient()
