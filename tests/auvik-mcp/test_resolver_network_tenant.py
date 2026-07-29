"""Tests for resolve_network and resolve_tenant in utils/resolver.py."""

import pytest

from utils.resolver import Resolution, looks_like_id, resolve_network, resolve_tenant


# ---------------------------------------------------------------------------
# resolve_network
# ---------------------------------------------------------------------------


async def test_resolve_network_by_description(fake_client_one_match):
    res = await resolve_network(fake_client_one_match, "Corporate LAN")
    assert res.id == "777"
    assert res.ambiguous is False
    assert res.candidates == []


async def test_resolve_network_case_insensitive(fake_client_one_match):
    res = await resolve_network(fake_client_one_match, "corporate lan")
    assert res.id == "777"


async def test_resolve_network_substring(fake_client_one_match):
    res = await resolve_network(fake_client_one_match, "corporate")
    assert res.id == "777"


async def test_resolve_network_passthrough_id(fake_client_one_match):
    res = await resolve_network(fake_client_one_match, "242216279026467843")
    assert res.id == "242216279026467843"
    assert res.ambiguous is False


async def test_resolve_network_no_match(fake_client_no_match):
    res = await resolve_network(fake_client_no_match, "nonexistent")
    assert res.id is None
    assert res.ambiguous is False
    assert res.candidates == []


# ---------------------------------------------------------------------------
# resolve_tenant
# ---------------------------------------------------------------------------


async def test_resolve_tenant_by_domain_prefix(fake_client_one_match):
    res = await resolve_tenant(fake_client_one_match, "acme")
    assert res.id == "111"
    assert res.ambiguous is False


async def test_resolve_tenant_by_display_name(fake_client_one_match):
    res = await resolve_tenant(fake_client_one_match, "Acme Corp")
    assert res.id == "111"


async def test_resolve_tenant_case_insensitive(fake_client_one_match):
    res = await resolve_tenant(fake_client_one_match, "ACME CORP")
    assert res.id == "111"


async def test_resolve_tenant_passthrough_id(fake_client_one_match):
    res = await resolve_tenant(fake_client_one_match, "242216279026467843")
    assert res.id == "242216279026467843"


async def test_resolve_tenant_ambiguous(fake_client_two_matches):
    # "Corp" appears as substring in both displayNames:
    # "Acme Corp" and "Acme Corp Staging" → ambiguous
    res = await resolve_tenant(fake_client_two_matches, "Corp")
    assert res.ambiguous is True
    assert len(res.candidates) == 2


async def test_resolve_tenant_no_match(fake_client_no_match):
    res = await resolve_tenant(fake_client_no_match, "nobody")
    assert res.id is None
    assert res.ambiguous is False
    assert res.candidates == []


async def test_resolve_tenant_substring_domain(fake_client_two_matches):
    # "staging" appears only in "acme-staging" domainPrefix
    res = await resolve_tenant(fake_client_two_matches, "staging")
    assert res.id == "222"
    assert res.ambiguous is False
