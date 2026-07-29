"""HaloClient behaviour tests (OAuth token lifecycle, auth retry, 429 backoff).

Uses httpx.MockTransport. A single transport handler intercepts BOTH the OAuth
token POST (path ends with ``/auth/token``) and the ``/api/*`` resource requests,
so the tests can assert on how often each endpoint is hit.
"""

import asyncio

import httpx
import pytest

from clients.halo_client import HaloClient

BASE = "https://test.halopsa.com"
TOKEN_BODY = {"access_token": "tok", "token_type": "Bearer", "expires_in": 3600}


def _client(handler, **kwargs) -> HaloClient:
    return HaloClient(
        base_url=BASE,
        client_id="cid",
        client_secret="secret",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _is_token(request: httpx.Request) -> bool:
    return request.url.path.endswith("/auth/token")


# ---------------------------------------------------------------------------
# Token acquisition, caching and reuse
# ---------------------------------------------------------------------------


async def test_token_fetched_once_and_reused():
    """The bearer token is fetched on the first call and reused on the second."""
    counts = {"token": 0, "resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            counts["token"] += 1
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    r1 = await client.get("/Tickets/1")
    r2 = await client.get("/Tickets/2")
    await client.close()

    assert r1["success"] is True and r2["success"] is True
    assert counts["token"] == 1, "token endpoint must be hit exactly once"
    assert counts["resource"] == 2


async def test_get_sends_bearer_authorization_header():
    """Every /api request carries Authorization: Bearer <token>."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        captured["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    await client.get("/Tickets/1")
    await client.close()

    assert captured["auth"] == "Bearer tok"


async def test_token_request_uses_client_credentials_grant():
    """The token POST carries grant_type=client_credentials + client id/secret."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            captured["body"] = request.content.decode()
            return httpx.Response(200, json=TOKEN_BODY)
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    await client.get("/Tickets/1")
    await client.close()

    body = captured["body"]
    assert "grant_type=client_credentials" in body
    assert "client_id=cid" in body
    assert "client_secret=secret" in body


# ---------------------------------------------------------------------------
# 401 → exactly one forced refresh + retry
# ---------------------------------------------------------------------------


async def test_401_triggers_one_forced_refresh_and_retry():
    """A 401 on a resource call forces one token refresh then retries once."""
    counts = {"token": 0, "resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            counts["token"] += 1
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        if counts["resource"] == 1:
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is True
    assert result["data"] == {"ok": True}
    # One initial token + one forced refresh.
    assert counts["token"] == 2
    # Initial attempt + exactly one retry.
    assert counts["resource"] == 2


async def test_persistent_401_returns_auth_error_after_single_retry():
    """A resource that always 401s retries exactly once then surfaces auth error."""
    counts = {"token": 0, "resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            counts["token"] += 1
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        return httpx.Response(401, json={"error": "nope"})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert result["data"] is None
    assert "401" in result["error"]
    # Only ONE forced refresh + retry (no infinite loop).
    assert counts["resource"] == 2
    assert counts["token"] == 2


async def test_403_returns_auth_error_without_retry():
    """A 403 is a hard auth error — no refresh, no retry."""
    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        return httpx.Response(403, json={"error": "forbidden"})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "403" in result["error"]
    assert counts["resource"] == 1


# ---------------------------------------------------------------------------
# Token endpoint failures surface as {success: False}
# ---------------------------------------------------------------------------


async def test_non_200_token_response_surfaces_error():
    """A non-200 token response returns {success:False} and skips the resource."""
    resource_hit = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(400, text="invalid_client")
        resource_hit["n"] += 1
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert result["data"] is None
    assert "400" in result["error"]
    assert resource_hit["n"] == 0, "resource must not be called without a token"


async def test_token_non_json_body_surfaces_error():
    """A 200 token response with a non-JSON body surfaces a structured error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, content=b"not json")
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "non-JSON" in result["error"]


async def test_token_missing_access_token_surfaces_error():
    """A token body without access_token surfaces a structured error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json={"token_type": "Bearer"})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "access_token" in result["error"]


# ---------------------------------------------------------------------------
# 429 Retry-After backoff
# ---------------------------------------------------------------------------


async def test_429_then_200_backs_off_then_succeeds(monkeypatch):
    """A 429 backs off (one patched sleep) then the retry succeeds."""
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        if counts["resource"] == 1:
            return httpx.Response(429, headers={"Retry-After": "5"}, json={})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is True
    assert counts["resource"] == 2
    assert len(sleeps) == 1, "exactly one backoff before the successful retry"


async def test_429_honors_retry_after_value(monkeypatch):
    """The server-supplied Retry-After value drives the backoff delay.

    ``HaloClient.get`` passes the case-insensitive ``resp.headers`` to
    ``parse_retry_after`` (which is also case-insensitive), so a ``Retry-After: 9``
    yields a 9-second backoff rather than the 1-second fallback.
    """
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        if counts["resource"] == 1:
            return httpx.Response(429, headers={"Retry-After": "9"}, json={})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is True
    assert sleeps == [9], "the Retry-After: 9 value drives the backoff delay"


async def test_429_exhausts_retries_returns_rate_limited_error(monkeypatch):
    """Persistent 429s exhaust the retry budget and return a rate-limited error."""

    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        return httpx.Response(429, headers={"Retry-After": "0"}, json={})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "429" in result["error"] or "rate limit" in result["error"].lower()
    # 1 initial attempt + 3 retries = 4 resource hits.
    assert counts["resource"] == 4


async def test_429_without_retry_after_falls_back_to_one_second(monkeypatch):
    """A 429 lacking Retry-After falls back to a 1-second delay."""
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        if counts["resource"] == 1:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is True
    assert sleeps == [1]


# ---------------------------------------------------------------------------
# Response body handling
# ---------------------------------------------------------------------------


async def test_get_empty_body_returns_success_none_data():
    """An empty 200 body returns success with data=None (no .json() crash)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        return httpx.Response(200, content=b"")

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result == {"success": True, "data": None, "error": None}


async def test_get_non_json_body_returns_raw():
    """A 200 with a non-JSON body returns the raw text under 'raw'."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        return httpx.Response(200, content=b"plain text")

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is True
    assert result["data"] == {"raw": "plain text"}


async def test_get_500_returns_upstream_error():
    """A 500 maps to success=False with the status in the message."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        return httpx.Response(500, text="boom")

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "500" in result["error"]


async def test_get_connect_error_returns_error_dict():
    """A ConnectError is caught and returned as a structured error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        raise httpx.ConnectError("refused")

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "connection error" in result["error"].lower()


async def test_get_timeout_returns_error_dict():
    """A TimeoutException is caught and returned as a structured error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        raise httpx.TimeoutException("slow")

    client = _client(handler)
    result = await client.get("/Tickets/1")
    await client.close()

    assert result["success"] is False
    assert "timed out" in result["error"].lower()


async def test_get_forwards_query_params():
    """Query params are forwarded on the outgoing request URL."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        captured["params"] = dict(request.url.params)
        captured["path"] = request.url.path
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    await client.get("/Tickets", params={"client_id": "3"})
    await client.close()

    assert captured["path"] == "/api/Tickets"
    assert captured["params"].get("client_id") == "3"


# ---------------------------------------------------------------------------
# post()
# ---------------------------------------------------------------------------


async def test_post_sends_bearer_and_json_body():
    """post() sends the bearer token and the JSON body to /api/<path>."""
    import json as _json

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        captured["path"] = request.url.path
        captured["auth"] = request.headers.get("authorization", "")
        captured["body"] = _json.loads(request.content)
        return httpx.Response(201, json=[{"id": 42}])

    client = _client(handler)
    result = await client.post("/Tickets", [{"summary": "x"}])
    await client.close()

    assert captured["path"] == "/api/Tickets"
    assert captured["auth"] == "Bearer tok"
    assert captured["body"] == [{"summary": "x"}]
    assert result["success"] is True
    assert result["data"] == [{"id": 42}]


async def test_post_401_returns_auth_error():
    """post() maps a 401 to a structured auth error (no retry path)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if _is_token(request):
            return httpx.Response(200, json=TOKEN_BODY)
        return httpx.Response(401, json={"error": "no"})

    client = _client(handler)
    result = await client.post("/Tickets", [{"summary": "x"}])
    await client.close()

    assert result["success"] is False
    assert "401" in result["error"]
