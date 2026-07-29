"""Tests for 429 Retry-After handling in AuvikClient.get() — Task B2.

Uses httpx.MockTransport (no respx dependency).
Retry-After: 0 keeps tests instantaneous.
"""

import httpx
import pytest

from clients.auvik_client import AuvikClient
from utils.constants import DEFAULT_BASE_URL


def _make_transport(handler):
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# B2-1: one 429 then 200 → success (one retry consumed)
# ---------------------------------------------------------------------------


async def test_get_retries_once_on_429_then_200():
    """A single 429 followed by 200 returns success after one retry."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json={"data": {"ok": True}})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get("/v1/authentication/verify")
    await client.close()

    assert result["success"] is True
    assert result["data"] == {"data": {"ok": True}}
    assert call_count == 2


# ---------------------------------------------------------------------------
# B2-2: 429 on first call, then 200 — verify Retry-After header is respected
# ---------------------------------------------------------------------------


async def test_get_retry_uses_retry_after_value(monkeypatch):
    """The server-supplied Retry-After value drives the backoff delay.

    Uses a NON-ZERO value and asserts the observed sleep, so this can actually
    distinguish "honored the header" from "fell back to the 1-second default".
    A ``Retry-After: 0`` cannot: both paths sleep 1 second, because
    ``0 or 1`` and ``None or 1`` are both 1.
    """
    import asyncio

    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return httpx.Response(429, headers={"Retry-After": "7"}, json={})
        return httpx.Response(200, json={"data": []})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get("/v1/authentication/verify")
    await client.close()

    assert result["success"] is True
    assert call_count == 2
    assert sleep_calls == [7], (
        "Retry-After: 7 must drive a 7-second backoff, not the 1s fallback"
    )


# ---------------------------------------------------------------------------
# B2-3: always 429 → exhausts max_retries → structured error
# ---------------------------------------------------------------------------


async def test_get_exhaust_retries_returns_rate_limited_error():
    """Persistent 429 responses exhaust retries and return a RateLimited error."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, headers={"Retry-After": "0"}, json={})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get("/v1/authentication/verify")
    await client.close()

    assert result["success"] is False
    assert result["data"] is None
    error = result["error"]
    assert error is not None
    # Must mention rate-limiting; "RateLimited" or "rate limit" in the message
    assert "429" in error or "RateLimited" in error or "rate limit" in error.lower()
    # Should have attempted initial call + 3 retries = 4 total
    assert call_count == 4  # 1 initial + 3 retries


# ---------------------------------------------------------------------------
# B2-4: two 429s then 200 — succeeds within retry budget
# ---------------------------------------------------------------------------


async def test_get_two_429s_then_200_succeeds():
    """Two consecutive 429s followed by 200 still succeeds (within 3-retry budget)."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json={"data": {"items": []}})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get("/v1/authentication/verify")
    await client.close()

    assert result["success"] is True
    assert call_count == 3


# ---------------------------------------------------------------------------
# B2-5: 429 without Retry-After falls back to 1 second (mocked sleep)
# ---------------------------------------------------------------------------


async def test_get_429_no_retry_after_falls_back_to_default(monkeypatch):
    """Missing Retry-After header falls back to 1-second default (sleep is patched)."""
    import asyncio

    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # No Retry-After header
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"data": {}})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get("/v1/authentication/verify")
    await client.close()

    assert result["success"] is True
    # Fell back to 1-second sleep
    assert sleep_calls == [1]
