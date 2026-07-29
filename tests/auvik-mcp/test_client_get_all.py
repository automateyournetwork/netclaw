"""Tests for AuvikClient.get_all() auto-pagination — Task B3.

Uses httpx.MockTransport (no respx dependency).
Pagination follows links.next (absolute URLs); meta.totalPages is never used.
"""

import httpx
import pytest

from clients.auvik_client import AuvikClient
from utils.constants import DEFAULT_BASE_URL

BASE = DEFAULT_BASE_URL
PATH = "/v1/inventory/device/info"
PAGE2_URL = f"{BASE}{PATH}?page[after]=CUR&page[first]=300"


def _make_transport(handler):
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# B3-1: two-page happy path — all items collected
# ---------------------------------------------------------------------------


async def test_get_all_two_pages_collects_all_items():
    """Two pages are followed and all items merged into one list."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        url = str(request.url)
        if "page[after]" not in url:
            # Page 1
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "1"}, {"id": "2"}],
                    "links": {"next": PAGE2_URL},
                },
            )
        else:
            # Page 2
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "3"}, {"id": "4"}],
                    "links": {},
                },
            )

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH, params={"page[first]": 300})
    await client.close()

    assert result["items"] == [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}]
    assert result["page_count"] == 2
    assert result["truncated"] is False
    assert result["next_cursor"] is None
    assert call_count == 2


# ---------------------------------------------------------------------------
# B3-2: max_pages=1 stops early → truncated=True, next_cursor set
# ---------------------------------------------------------------------------


async def test_get_all_max_pages_1_truncates():
    """max_pages=1 stops after the first page and marks truncated=True."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json={
                "data": [{"id": "1"}, {"id": "2"}],
                "links": {"next": PAGE2_URL},
            },
        )

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH, params={"page[first]": 300}, max_pages=1)
    await client.close()

    assert result["items"] == [{"id": "1"}, {"id": "2"}]
    assert result["page_count"] == 1
    assert result["truncated"] is True
    assert result["next_cursor"] == PAGE2_URL
    assert call_count == 1  # Second page was NOT requested


# ---------------------------------------------------------------------------
# B3-3: single page, no links.next → not truncated
# ---------------------------------------------------------------------------


async def test_get_all_single_page_no_next():
    """A single page with no links.next returns truncated=False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"id": "A"}, {"id": "B"}],
                "links": {},
            },
        )

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH)
    await client.close()

    assert result["items"] == [{"id": "A"}, {"id": "B"}]
    assert result["page_count"] == 1
    assert result["truncated"] is False
    assert result["next_cursor"] is None


# ---------------------------------------------------------------------------
# B3-4: first page errors → returns error dict with empty items
# ---------------------------------------------------------------------------


async def test_get_all_error_on_first_page():
    """An error on the first page returns items=[] and includes error key."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"errors": [{"title": "Server Error"}]})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH)
    await client.close()

    assert result["items"] == []
    assert result["page_count"] == 0
    assert "error" in result
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# B3-5: error on second page → returns items collected so far + error
# ---------------------------------------------------------------------------


async def test_get_all_error_on_second_page_returns_partial():
    """An error mid-pagination returns partial items and includes error key."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "1"}, {"id": "2"}],
                    "links": {"next": PAGE2_URL},
                },
            )
        return httpx.Response(503, json={"errors": [{"title": "Unavailable"}]})

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH)
    await client.close()

    assert result["items"] == [{"id": "1"}, {"id": "2"}]
    assert result["page_count"] == 1
    assert "error" in result
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# B3-6: three pages → page_count=3
# ---------------------------------------------------------------------------


async def test_get_all_three_pages():
    """Three pages are all followed with correct page_count."""
    PAGE3_URL = f"{BASE}{PATH}?page[after]=CUR2&page[first]=300"
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        url = str(request.url)
        if "CUR2" in url:
            return httpx.Response(
                200,
                json={"data": [{"id": "5"}], "links": {}},
            )
        elif "CUR" in url:
            return httpx.Response(
                200,
                json={"data": [{"id": "3"}, {"id": "4"}], "links": {"next": PAGE3_URL}},
            )
        else:
            return httpx.Response(
                200,
                json={"data": [{"id": "1"}, {"id": "2"}], "links": {"next": PAGE2_URL}},
            )

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH)
    await client.close()

    assert result["page_count"] == 3
    assert len(result["items"]) == 5
    assert result["truncated"] is False
    assert result["next_cursor"] is None


# ---------------------------------------------------------------------------
# B3-7: meta.totalPages is NOT used — only links.next drives pagination
# ---------------------------------------------------------------------------


async def test_get_all_ignores_meta_total_pages():
    """meta.totalPages in the payload is ignored; links.next drives pagination."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"id": "1"}],
                # meta says there are 5 pages — but no links.next
                "meta": {"totalPages": 5},
                "links": {},
            },
        )

    mt = _make_transport(handler)
    client = AuvikClient(
        base_url=BASE,
        username="u",
        password="k",
        transport=mt,
    )

    result = await client.get_all(PATH)
    await client.close()

    # Should stop after 1 page because links.next is absent
    assert result["page_count"] == 1
    assert result["truncated"] is False
