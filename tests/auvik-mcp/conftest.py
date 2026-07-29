"""Pytest configuration for auvik-mcp tests."""

import os
import sys

import pytest

# Add the auvik-mcp server package directory to sys.path so imports like
# `from utils.constants import ...` resolve correctly.
_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "mcp-servers",
    "auvik-mcp",
)
sys.path.insert(0, os.path.abspath(_SERVER_DIR))

# Set dummy credentials so modules that read env vars at import time don't fail.
os.environ.setdefault("AUVIK_USERNAME", "test_user")
os.environ.setdefault("AUVIK_API_KEY", "test_key")


# ---------------------------------------------------------------------------
# Fake client helpers for resolver tests
# ---------------------------------------------------------------------------

_PAGE_RESULT_TEMPLATE = {
    "page_count": 1,
    "truncated": False,
    "next_cursor": None,
}

_DEVICE_ONE = {
    "id": "999",
    "type": "device",
    "attributes": {
        "deviceName": "core-switch-01",
        "ipAddresses": ["10.4.1.1"],
    },
}

_DEVICE_TWO = {
    "id": "888",
    "type": "device",
    "attributes": {
        "deviceName": "access-switch-02",
        "ipAddresses": ["10.4.1.2"],
    },
}

_NETWORK_ONE = {
    "id": "777",
    "type": "network",
    "attributes": {
        "description": "Corporate LAN",
        "networkType": "routed",
    },
}

_TENANT_ONE = {
    "id": "111",
    "type": "tenant",
    "attributes": {
        "domainPrefix": "acme",
        "displayName": "Acme Corp",
        "tenantType": "client",
    },
}

_TENANT_TWO = {
    "id": "222",
    "type": "tenant",
    "attributes": {
        "domainPrefix": "acme-staging",
        "displayName": "Acme Corp Staging",
        "tenantType": "client",
    },
}


class _FakeClient:
    """Minimal fake AuvikClient exposing only get_all, for resolver tests."""

    def __init__(self, items_by_path: dict):
        self._items_by_path = items_by_path

    async def get_all(self, path: str, params=None, max_pages: int = 50) -> dict:
        items = self._items_by_path.get(path, [])
        return {**_PAGE_RESULT_TEMPLATE, "items": list(items)}


@pytest.fixture
def fake_client_one_match():
    return _FakeClient({
        "/v1/inventory/device/info": [_DEVICE_ONE],
        "/v1/inventory/network/info": [_NETWORK_ONE],
        "/v1/tenants": [_TENANT_ONE],
    })


@pytest.fixture
def fake_client_two_matches():
    return _FakeClient({
        "/v1/inventory/device/info": [_DEVICE_ONE, _DEVICE_TWO],
        "/v1/tenants": [_TENANT_ONE, _TENANT_TWO],
    })


@pytest.fixture
def fake_client_no_match():
    return _FakeClient({
        "/v1/inventory/device/info": [],
        "/v1/inventory/network/info": [],
        "/v1/tenants": [],
    })
