"""Tests for AuvikClient construction and get() — Task B1.

Uses httpx.MockTransport (no respx dependency).
"""

import base64

import httpx
import pytest

from clients.auvik_client import AuvikClient
from utils.constants import DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transport(handler):
    """Wrap a handler callable into an httpx.MockTransport."""
    return httpx.MockTransport(handler)


def _decode_basic(auth_header: str) -> tuple[str, str]:
    """Decode 'Basic <b64>' → (username, password)."""
    assert auth_header.startswith("Basic "), f"Expected Basic auth, got: {auth_header!r}"
    encoded = auth_header[len("Basic "):]
    decoded = base64.b64decode(encoded).decode()
    username, _, password = decoded.partition(":")
    return username, password


# ---------------------------------------------------------------------------
# B1-1: 200 success path + auth header verification
# ---------------------------------------------------------------------------


async def test_get_200_empty_body_returns_success_none_data():
    """An empty 200 body (e.g. /authentication/verify) must NOT crash on .json()."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    client = AuvikClient(base_url=DEFAULT_BASE_URL, username="u", password="k",
                         transport=_make_transport(handler))
    result = await client.get("/v1/authentication/verify")
    assert result == {"success": True, "data": None, "error": None}


async def test_get_200_non_json_body_returns_raw():
    """A 200 with a non-JSON body returns success with the raw text, not a crash."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"OK plain text")

    client = AuvikClient(base_url=DEFAULT_BASE_URL, username="u", password="k",
                         transport=_make_transport(handler))
    result = await client.get("/v1/x")
    assert result["success"] is True and result["data"] == {"raw": "OK plain text"}


async def test_get_200_returns_success_dict():
    """A 200 response returns success=True with the parsed JSON body."""

    def handler(request: httpx.Request) -> httpx.Response:
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
    assert result["error"] is None
    assert result["data"] == {"data": {"ok": True}}


async def test_get_200_async_returns_success_dict():
    """Async variant of the 200 success test."""

    def handler(request: httpx.Request) -> httpx.Response:
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
    assert result["error"] is None
    assert result["data"] == {"data": {"ok": True}}


async def test_get_sends_basic_auth_header():
    """The outgoing request must carry a valid Basic auth header for u:k."""

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json={"data": {}})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="myuser",
        password="myapikey",
        transport=mt,
    )

    await client.get("/v1/authentication/verify")
    await client.close()

    auth = captured["auth"]
    assert auth.startswith("Basic ")
    username, password = _decode_basic(auth)
    assert username == "myuser"
    assert password == "myapikey"


async def test_get_sends_accept_json_api_header():
    """The outgoing request must carry Accept: application/vnd.api+json."""

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["accept"] = request.headers.get("accept", "")
        return httpx.Response(200, json={"data": {}})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    await client.get("/v1/authentication/verify")
    await client.close()

    assert captured["accept"] == "application/vnd.api+json"


# ---------------------------------------------------------------------------
# B1-2: 401 returns a structured auth error
# ---------------------------------------------------------------------------


async def test_get_401_returns_auth_error():
    """A 401 response maps to success=False with an error mentioning env vars."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": [{"title": "Unauthorized"}]})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="bad",
        password="creds",
        transport=mt,
    )

    result = await client.get("/v1/authentication/verify")
    await client.close()

    assert result["success"] is False
    assert result["data"] is None
    error = result["error"]
    assert error is not None
    assert "AUVIK_USERNAME" in error
    assert "AUVIK_API_KEY" in error


async def test_get_403_returns_auth_error():
    """A 403 response also maps to a structured auth error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"errors": [{"title": "Forbidden"}]})

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
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# B1-3: Network-level errors
# ---------------------------------------------------------------------------


async def test_get_connect_error_returns_error_dict():
    """A ConnectError returns a structured error with success=False."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

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
    assert result["error"] is not None


async def test_get_timeout_returns_error_dict():
    """A TimeoutException returns a structured error with success=False."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

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
    assert result["error"] is not None


async def test_get_passes_query_params():
    """Query params are forwarded in the request URL."""

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=mt,
    )

    await client.get("/v1/inventory/device/info", params={"filter[tenants]": "abc"})
    await client.close()

    assert "filter%5Btenants%5D=abc" in captured["url"] or "filter[tenants]=abc" in captured["url"]


async def test_rate_limiter_acquire_called():
    """When a rate_limiter is provided, acquire() is called before each request."""

    call_count = 0

    class FakeRateLimiter:
        async def acquire(self):
            nonlocal call_count
            call_count += 1

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {}})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        rate_limiter=FakeRateLimiter(),
        transport=mt,
    )

    await client.get("/v1/authentication/verify")
    await client.close()

    assert call_count == 1
