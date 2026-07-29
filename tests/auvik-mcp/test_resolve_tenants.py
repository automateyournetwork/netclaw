"""Tests for resolve_tenants() in utils/resolver.py.

TDD: these tests are written BEFORE the implementation.

Uses _FakeClient from conftest.py (same fixture style as test_resolver.py).
All tests are async (pytest-anyio / asyncio mode configured in pytest.ini).
"""

import pytest

from utils.resolver import resolve_tenants


# ---------------------------------------------------------------------------
# Helpers — inline fake clients so tests are self-contained
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = {"page_count": 1, "truncated": False, "next_cursor": None}


def _tenant(id_: str, domain: str, display: str = ""):
    return {
        "id": id_,
        "type": "tenant",
        "attributes": {
            "domainPrefix": domain,
            "displayName": display or domain.title(),
            "tenantType": "client",
        },
    }


class _FakeTenantClient:
    """Fake AuvikClient that returns a fixed tenant list from /v1/tenants."""

    def __init__(self, tenants: list):
        self._tenants = tenants
        self.get_all_calls: list[str] = []

    async def get_all(self, path: str, params=None, max_pages: int = 50) -> dict:
        self.get_all_calls.append(path)
        return {**_PAGE_TEMPLATE, "items": list(self._tenants)}


_TENANT_FRONTIER = _tenant("698055778108510973", "frontier", "Frontier Networks")
_TENANT_ACME = _tenant("111222333444555666", "acme", "Acme Corp")


# ---------------------------------------------------------------------------
# Empty / None input → (None, None) — caller should omit the param
# ---------------------------------------------------------------------------


async def test_resolve_tenants_none_input():
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, None)
    assert resolved is None
    assert err is None


async def test_resolve_tenants_empty_string():
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, "")
    assert resolved is None
    assert err is None


# ---------------------------------------------------------------------------
# Already-an-ID passthrough — no /v1/tenants call
# ---------------------------------------------------------------------------


async def test_resolve_tenants_id_passthrough():
    """A value that looks_like_id should pass through unchanged without API call."""
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, "698055778108510973")
    assert err is None
    assert resolved == "698055778108510973"
    # No /v1/tenants call should have been made
    assert client.get_all_calls == []


async def test_resolve_tenants_id_passthrough_no_api_lookup():
    """Confirm get_all is NOT called when input is already an ID."""
    client = _FakeTenantClient([])  # empty list; would fail a name lookup
    resolved, err = await resolve_tenants(client, "123456789012")
    assert err is None
    assert resolved == "123456789012"
    assert len(client.get_all_calls) == 0


# ---------------------------------------------------------------------------
# Single name → single ID
# ---------------------------------------------------------------------------


async def test_resolve_tenants_single_name_to_id():
    """A domain-prefix name maps to the tenant ID."""
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, "frontier")
    assert err is None
    assert resolved == "698055778108510973"


async def test_resolve_tenants_single_display_name():
    """A display name is resolved to tenant ID."""
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, "Frontier Networks")
    assert err is None
    assert resolved == "698055778108510973"


# ---------------------------------------------------------------------------
# Comma-separated list: mixed names and IDs
# ---------------------------------------------------------------------------


async def test_resolve_tenants_comma_list_names():
    """Two names → two IDs joined by comma."""
    client = _FakeTenantClient([_TENANT_FRONTIER, _TENANT_ACME])
    resolved, err = await resolve_tenants(client, "frontier,acme")
    assert err is None
    # Order matches input order
    assert resolved == "698055778108510973,111222333444555666"


async def test_resolve_tenants_comma_list_mixed_id_and_name():
    """An ID followed by a name: ID passes through, name gets resolved."""
    client = _FakeTenantClient([_TENANT_ACME])
    resolved, err = await resolve_tenants(client, "698055778108510973,acme")
    assert err is None
    assert resolved == "698055778108510973,111222333444555666"


async def test_resolve_tenants_comma_list_whitespace_stripped():
    """Whitespace around comma-separated parts is stripped."""
    client = _FakeTenantClient([_TENANT_FRONTIER, _TENANT_ACME])
    resolved, err = await resolve_tenants(client, " frontier , acme ")
    assert err is None
    assert resolved == "698055778108510973,111222333444555666"


async def test_resolve_tenants_single_id_in_list():
    """A single-element comma input that is an ID passes through."""
    client = _FakeTenantClient([])
    resolved, err = await resolve_tenants(client, "698055778108510973,")
    # Trailing comma produces empty part which is skipped (empty → treated as
    # no-op after stripping); only the ID should appear.
    # OR: we treat empty parts as invalid. Either way, no error for the ID.
    # The implementation skips empty parts (strip produces ""), so:
    assert err is None
    assert resolved == "698055778108510973"


# ---------------------------------------------------------------------------
# Ambiguous name → error envelope with code "Ambiguous"
# ---------------------------------------------------------------------------


async def test_resolve_tenants_ambiguous_name():
    """When a name matches multiple tenants the function returns an error envelope."""
    # Use "Corp" as substring — both "Acme Corp" and "Acme Corp Staging" contain it
    t1 = _tenant("111000000000000001", "acme", "Acme Corp")
    t2 = _tenant("111000000000000002", "acme-staging", "Acme Corp Staging")
    client = _FakeTenantClient([t1, t2])
    # "Corp" is a substring match for both display names → ambiguous
    resolved, err = await resolve_tenants(client, "Corp")
    assert resolved is None
    assert err is not None
    assert err["error"]["code"] == "Ambiguous"


async def test_resolve_tenants_ambiguous_stops_early():
    """An ambiguous first part stops processing immediately (no further lookups)."""
    t1 = _tenant("111000000000000001", "acme", "Acme Corp")
    t2 = _tenant("111000000000000002", "acme-staging", "Acme Corp Staging")
    client = _FakeTenantClient([t1, t2])
    # "Corp" matches both via substring → ambiguous; second part "frontier" never reached
    resolved, err = await resolve_tenants(client, "Corp,frontier")
    assert resolved is None
    assert err is not None
    assert err["error"]["code"] == "Ambiguous"


# ---------------------------------------------------------------------------
# Not-found → error envelope with code "NotFound"
# ---------------------------------------------------------------------------


async def test_resolve_tenants_not_found():
    """A name that matches no tenant returns a NotFound error envelope."""
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, "nosuchtenantxyz")
    assert resolved is None
    assert err is not None
    assert err["error"]["code"] == "NotFound"


async def test_resolve_tenants_not_found_in_list():
    """A bad name within a comma list causes the whole call to fail."""
    client = _FakeTenantClient([_TENANT_FRONTIER])
    resolved, err = await resolve_tenants(client, "frontier,doesnotexist")
    assert resolved is None
    assert err is not None
    assert err["error"]["code"] == "NotFound"
