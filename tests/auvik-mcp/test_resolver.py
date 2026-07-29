"""Tests for utils/resolver.py — ID detection and entity resolution."""

import pytest

from utils.resolver import Resolution, looks_like_id, resolve_device


# ---------------------------------------------------------------------------
# looks_like_id
# ---------------------------------------------------------------------------


def test_looks_like_id_numeric_long():
    assert looks_like_id("242216279026467843") is True


def test_looks_like_id_hostname():
    assert looks_like_id("core-sw-01") is False


def test_looks_like_id_ip():
    assert looks_like_id("10.4.1.1") is False


def test_looks_like_id_short_numeric():
    # Fewer than 6 digits → not an ID
    assert looks_like_id("12345") is False


def test_looks_like_id_exactly_six_digits():
    assert looks_like_id("123456") is True


def test_looks_like_id_alphanumeric():
    assert looks_like_id("abc123def") is False


# ---------------------------------------------------------------------------
# resolve_device — single match
# ---------------------------------------------------------------------------


async def test_resolve_device_single_by_name(fake_client_one_match):
    res = await resolve_device(fake_client_one_match, "core-switch-01")
    assert res.id == "999"
    assert res.ambiguous is False
    assert res.candidates == []


async def test_resolve_device_by_ip(fake_client_one_match):
    res = await resolve_device(fake_client_one_match, "10.4.1.1")
    assert res.id == "999"
    assert res.ambiguous is False


async def test_resolve_device_case_insensitive(fake_client_one_match):
    res = await resolve_device(fake_client_one_match, "CORE-SWITCH-01")
    assert res.id == "999"


async def test_resolve_device_substring_match(fake_client_one_match):
    # "core" is a substring of "core-switch-01"
    res = await resolve_device(fake_client_one_match, "core")
    assert res.id == "999"


# ---------------------------------------------------------------------------
# resolve_device — passthrough if already an ID
# ---------------------------------------------------------------------------


async def test_resolve_device_already_id(fake_client_one_match):
    res = await resolve_device(fake_client_one_match, "242216279026467843")
    assert res.id == "242216279026467843"
    assert res.ambiguous is False


# ---------------------------------------------------------------------------
# resolve_device — ambiguous
# ---------------------------------------------------------------------------


async def test_resolve_device_ambiguous(fake_client_two_matches):
    res = await resolve_device(fake_client_two_matches, "switch")
    assert res.ambiguous is True
    assert len(res.candidates) == 2
    assert res.id is None


async def test_resolve_device_ambiguous_candidates_have_id(fake_client_two_matches):
    # Both "core-switch-01" and "access-switch-02" contain "switch"
    res = await resolve_device(fake_client_two_matches, "switch")
    ids = {c["id"] for c in res.candidates}
    assert "999" in ids
    assert "888" in ids


# ---------------------------------------------------------------------------
# resolve_device — no match
# ---------------------------------------------------------------------------


async def test_resolve_device_none(fake_client_no_match):
    res = await resolve_device(fake_client_no_match, "nope")
    assert res.ambiguous is False
    assert res.id is None
    assert res.candidates == []
