"""Tests for utils.resolver — looks_like_id, resolve_or_error, resolve_* helpers.

The resolve_* helpers hit ``client.get_all(<list path>)``; the ``_FakeClient``
fixtures (see conftest) provide those list rows without any HTTP transport.
"""

import pytest

from utils.resolver import (
    Resolution,
    looks_like_id,
    resolve_asset,
    resolve_client,
    resolve_or_error,
    resolve_site,
    resolve_ticket_type,
)


# ---------------------------------------------------------------------------
# looks_like_id
# ---------------------------------------------------------------------------


def test_looks_like_id_int():
    assert looks_like_id(9) is True


def test_looks_like_id_digit_string():
    assert looks_like_id("9") is True
    assert looks_like_id("123456") is True


def test_looks_like_id_digit_string_with_whitespace():
    assert looks_like_id("  42  ") is True


def test_looks_like_id_name_is_false():
    assert looks_like_id("Change Request") is False


def test_looks_like_id_alphanumeric_is_false():
    assert looks_like_id("12a") is False


def test_looks_like_id_empty_is_false():
    assert looks_like_id("") is False


def test_looks_like_id_none_is_false():
    assert looks_like_id(None) is False


# ---------------------------------------------------------------------------
# resolve_or_error
# ---------------------------------------------------------------------------


def test_resolve_or_error_success():
    id_, err = resolve_or_error(Resolution(id="9"), "ticket type")
    assert id_ == "9"
    assert err is None


def test_resolve_or_error_ambiguous():
    res = Resolution(ambiguous=True, candidates=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
    id_, err = resolve_or_error(res, "client")
    assert id_ is None
    assert err["error"]["code"] == "Ambiguous"
    assert "client" in err["error"]["message"]
    assert err["error"]["details"]["candidates"] == res.candidates


def test_resolve_or_error_not_found():
    id_, err = resolve_or_error(Resolution(), "asset")
    assert id_ is None
    assert err["error"]["code"] == "NotFound"
    assert "asset" in err["error"]["message"]


# ---------------------------------------------------------------------------
# resolve_* — passthrough for numeric ids (no HTTP call)
# ---------------------------------------------------------------------------


async def test_resolve_client_numeric_passthrough(fake_client_one_match):
    res = await resolve_client(fake_client_one_match, "501")
    assert res.id == "501"
    assert fake_client_one_match.calls == [], "numeric id must not trigger a list call"


async def test_resolve_ticket_type_numeric_passthrough(fake_client_one_match):
    res = await resolve_ticket_type(fake_client_one_match, 9)
    assert res.id == "9"
    assert fake_client_one_match.calls == []


# ---------------------------------------------------------------------------
# resolve_* — exact / substring single match
# ---------------------------------------------------------------------------


async def test_resolve_client_exact_match(fake_client_one_match):
    res = await resolve_client(fake_client_one_match, "Acme Corp")
    assert res.id == "501"
    assert res.ambiguous is False


async def test_resolve_client_case_insensitive(fake_client_one_match):
    res = await resolve_client(fake_client_one_match, "acme corp")
    assert res.id == "501"


async def test_resolve_ticket_type_by_name(fake_client_one_match):
    res = await resolve_ticket_type(fake_client_one_match, "Change Request")
    assert res.id == "9"
    # resolve_ticket_type reads the /TicketType list.
    assert fake_client_one_match.calls[0][0] == "/TicketType"


async def test_resolve_site_by_name(fake_client_one_match):
    res = await resolve_site(fake_client_one_match, "Acme HQ")
    assert res.id == "601"


async def test_resolve_asset_by_inventory_number(fake_client_one_match):
    res = await resolve_asset(fake_client_one_match, "SW-CORE-01")
    assert res.id == "701"


async def test_resolve_asset_substring_match(fake_client_one_match):
    # "Core Switch" is a substring of the asset name for the single asset.
    res = await resolve_asset(fake_client_one_match, "Core Switch")
    assert res.id == "701"


# ---------------------------------------------------------------------------
# resolve_* — ambiguous
# ---------------------------------------------------------------------------


async def test_resolve_client_ambiguous(fake_client_two_matches):
    res = await resolve_client(fake_client_two_matches, "Acme")
    assert res.ambiguous is True
    assert res.id is None
    assert len(res.candidates) == 2


async def test_resolve_ticket_type_ambiguous(fake_client_two_matches):
    res = await resolve_ticket_type(fake_client_two_matches, "Change")
    assert res.ambiguous is True
    assert {c["id"] for c in res.candidates} == {9, 10}


# ---------------------------------------------------------------------------
# resolve_* — not found
# ---------------------------------------------------------------------------


async def test_resolve_client_not_found(fake_client_no_match):
    res = await resolve_client(fake_client_no_match, "Nonexistent")
    assert res.id is None
    assert res.ambiguous is False
    assert res.candidates == []


async def test_resolve_asset_not_found(fake_client_no_match):
    res = await resolve_asset(fake_client_no_match, "ghost-device")
    assert res.id is None
