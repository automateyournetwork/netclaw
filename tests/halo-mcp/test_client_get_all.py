"""HaloClient.get_all() page-based pagination tests.

Halo list endpoints wrap results as ``{record_count, <entity>: [...]}`` and
paginate with ``pageinate``/``page_no``/``page_size``. ``get_all`` aggregates the
pages and stops on: the full record_count, a short/empty page, or the max_pages
truncation guard. A small ``page_size`` keeps the fixtures compact.
"""

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


def _page_no(request: httpx.Request) -> int:
    return int(request.url.params.get("page_no", "1"))


# ---------------------------------------------------------------------------
# Stop condition: full record_count reached
# ---------------------------------------------------------------------------


async def test_get_all_stops_at_record_count():
    """Aggregation halts once len(items) reaches record_count, even on a full page."""
    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        page = _page_no(request)
        if page == 1:
            return httpx.Response(200, json={"record_count": 4, "tickets": [{"id": 1}, {"id": 2}]})
        if page == 2:
            return httpx.Response(200, json={"record_count": 4, "tickets": [{"id": 3}, {"id": 4}]})
        # Page 3 must never be requested.
        return httpx.Response(200, json={"record_count": 4, "tickets": [{"id": 99}]})

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tickets")
    await client.close()

    assert [i["id"] for i in result["items"]] == [1, 2, 3, 4]
    assert result["page_count"] == 2
    assert result["truncated"] is False
    assert result["record_count"] == 4
    assert result["next_page"] is None
    assert counts["resource"] == 2, "must not request a third page"


async def test_get_all_stops_on_short_page():
    """A page returning fewer than page_size items ends pagination."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        page = _page_no(request)
        if page == 1:
            return httpx.Response(200, json={"tickets": [{"id": 1}, {"id": 2}]})
        return httpx.Response(200, json={"tickets": [{"id": 3}]})

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tickets")
    await client.close()

    assert [i["id"] for i in result["items"]] == [1, 2, 3]
    assert result["page_count"] == 2
    assert result["truncated"] is False


async def test_get_all_stops_on_empty_page():
    """An empty page ends pagination and keeps the items gathered so far."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        page = _page_no(request)
        if page == 1:
            return httpx.Response(200, json={"tickets": [{"id": 1}, {"id": 2}]})
        return httpx.Response(200, json={"tickets": []})

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tickets")
    await client.close()

    assert [i["id"] for i in result["items"]] == [1, 2]
    assert result["page_count"] == 2
    assert result["truncated"] is False


async def test_get_all_truncates_at_max_pages():
    """Never-ending full pages are capped by max_pages and marked truncated."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        page = _page_no(request)
        base = (page - 1) * 2
        return httpx.Response(
            200,
            json={"record_count": 100, "tickets": [{"id": base + 1}, {"id": base + 2}]},
        )

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tickets", max_pages=2)
    await client.close()

    assert len(result["items"]) == 4
    assert result["page_count"] == 2
    assert result["truncated"] is True
    assert result["next_page"] == 3


async def test_get_all_error_on_first_page():
    """A failure on the first page returns empty items plus an error key."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        return httpx.Response(500, text="boom")

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tickets")
    await client.close()

    assert result["items"] == []
    assert result["page_count"] == 0
    assert result["truncated"] is True
    assert "error" in result and result["error"]


async def test_get_all_partial_then_error_on_second_page():
    """An error mid-pagination returns the page-1 items plus an error key."""
    counts = {"resource": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        counts["resource"] += 1
        if _page_no(request) == 1:
            return httpx.Response(200, json={"record_count": 100, "tickets": [{"id": 1}, {"id": 2}]})
        return httpx.Response(503, text="unavailable")

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tickets")
    await client.close()

    assert [i["id"] for i in result["items"]] == [1, 2]
    assert result["page_count"] == 1
    assert "error" in result and result["error"]
    assert counts["resource"] == 2


async def test_get_all_bare_list_shape():
    """A bare-list endpoint (no wrapper) is aggregated too."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        if _page_no(request) == 1:
            return httpx.Response(200, json=[{"id": 1}, {"id": 2}])
        return httpx.Response(200, json=[])

    client = _client(handler, page_size=2)
    result = await client.get_all("/Tags")
    await client.close()

    assert [i["id"] for i in result["items"]] == [1, 2]
    assert result["page_count"] == 2
    assert result["truncated"] is False


async def test_get_all_sets_pagination_params():
    """get_all injects pageinate/page_size/page_no on the outgoing request."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=TOKEN_BODY)
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"tickets": []})

    client = _client(handler, page_size=25)
    await client.get_all("/Tickets")
    await client.close()

    assert captured["params"].get("pageinate") == "true"
    assert captured["params"].get("page_size") == "25"
    assert captured["params"].get("page_no") == "1"
