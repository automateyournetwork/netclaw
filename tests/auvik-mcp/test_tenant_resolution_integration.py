"""Integration tests: tenant name → ID resolution through tool calls.

Each test uses httpx.MockTransport that serves BOTH:
  - GET /v1/tenants  (tenant lookup)
  - GET /v1/<target-endpoint>  (the actual tool call)

Tests assert:
  1. When tenants="frontier" (a name), the outgoing request carries the
     resolved ID ("698055778108510973"), NOT the name.
  2. When tenants="698055778108510973" (already an ID), /v1/tenants is
     NOT called and the ID is forwarded unchanged.
  3. A bad name produces an error envelope (no upstream call to the tool endpoint).
"""

import json

import httpx
import pytest

from clients.auvik_client import AuvikClient
from tools.inventory import auvik_list_devices, auvik_list_networks
from tools.alerts import auvik_list_alerts
from utils.constants import DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FRONTIER_ID = "698055778108510973"
_FRONTIER_DOMAIN = "frontier"

_TENANT_LIST_PAYLOAD = {
    "data": [
        {
            "id": _FRONTIER_ID,
            "type": "tenant",
            "attributes": {
                "domainPrefix": _FRONTIER_DOMAIN,
                "displayName": "Frontier Networks",
                "tenantType": "client",
            },
        }
    ],
    "links": {},
    "meta": {},
}

_EMPTY_LIST_PAYLOAD = {"data": [], "links": {}, "meta": {}}

_DEVICE_PAYLOAD = {
    "data": [
        {
            "id": "123456789",
            "type": "device",
            "attributes": {
                "deviceName": "sw-01",
                "ipAddresses": ["10.0.0.1"],
                "deviceType": "switch",
                "onlineStatus": "online",
                "makeModel": "Cisco",
                "vendorName": "Cisco",
            },
        }
    ],
    "links": {},
    "meta": {},
}

_NETWORK_PAYLOAD = {
    "data": [
        {
            "id": "200000001",
            "type": "network",
            "attributes": {
                "description": "Corp LAN",
                "networkType": "routed",
                "scanStatus": "ok",
            },
        }
    ],
    "links": {},
    "meta": {},
}

_ALERT_PAYLOAD = {
    "data": [
        {
            "id": "300000001",
            "type": "alert",
            "attributes": {
                "alertDefinitionId": "adef-001",
                "severity": "high",
                "status": "active",
                "detectedTime": "2026-06-01T00:00:00Z",
            },
        }
    ],
    "links": {},
    "meta": {},
}


def _client_for(handler):
    """Build AuvikClient with MockTransport."""
    return AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=httpx.MockTransport(handler),
    )


# ---------------------------------------------------------------------------
# Helper: build multi-endpoint handler
# ---------------------------------------------------------------------------

def _multi_handler(tenant_payload, target_path: str, target_payload: dict):
    """Return a handler that serves tenant lookup + target endpoint."""
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append({"path": req.url.path, "params": dict(req.url.params)})
        if req.url.path == "/v1/tenants":
            return httpx.Response(200, json=tenant_payload)
        if req.url.path == target_path:
            return httpx.Response(200, json=target_payload)
        return httpx.Response(404, json={"errors": [{"title": "Not Found"}]})

    return handler, calls


# ---------------------------------------------------------------------------
# Test 1: name "frontier" → ID in outgoing request (auvik_list_devices)
# ---------------------------------------------------------------------------


class TestTenantNameResolutionListDevices:
    async def test_name_resolved_to_id_in_outgoing_request(self):
        """auvik_list_devices(tenants='frontier') must send tenants=<ID>."""
        handler, calls = _multi_handler(
            _TENANT_LIST_PAYLOAD,
            "/v1/inventory/device/info",
            _DEVICE_PAYLOAD,
        )
        client = _client_for(handler)
        result_str = await auvik_list_devices(client, tenants=_FRONTIER_DOMAIN)
        await client.close()

        # Should succeed
        data = json.loads(result_str)
        assert "error" not in data, f"Unexpected error: {data}"

        # Find the device-endpoint call and verify tenants param is the ID
        device_calls = [c for c in calls if c["path"] == "/v1/inventory/device/info"]
        assert device_calls, "Expected a call to /v1/inventory/device/info"
        assert device_calls[0]["params"].get("tenants") == _FRONTIER_ID

    async def test_id_passthrough_no_tenant_lookup(self):
        """auvik_list_devices(tenants=<ID>) must NOT call /v1/tenants."""
        handler, calls = _multi_handler(
            _TENANT_LIST_PAYLOAD,
            "/v1/inventory/device/info",
            _DEVICE_PAYLOAD,
        )
        client = _client_for(handler)
        result_str = await auvik_list_devices(client, tenants=_FRONTIER_ID)
        await client.close()

        data = json.loads(result_str)
        assert "error" not in data, f"Unexpected error: {data}"

        # /v1/tenants must NOT have been called
        tenant_calls = [c for c in calls if c["path"] == "/v1/tenants"]
        assert tenant_calls == [], "Expected NO /v1/tenants call when input is already an ID"

        # The ID must reach the device endpoint unchanged
        device_calls = [c for c in calls if c["path"] == "/v1/inventory/device/info"]
        assert device_calls, "Expected a call to /v1/inventory/device/info"
        assert device_calls[0]["params"].get("tenants") == _FRONTIER_ID

    async def test_unknown_name_returns_error_envelope(self):
        """An unresolvable tenant name returns NotFound without calling device endpoint."""
        handler, calls = _multi_handler(
            _TENANT_LIST_PAYLOAD,
            "/v1/inventory/device/info",
            _DEVICE_PAYLOAD,
        )
        client = _client_for(handler)
        result_str = await auvik_list_devices(client, tenants="nosuchtenantxyz")
        await client.close()

        data = json.loads(result_str)
        assert "error" in data
        assert data["error"]["code"] == "NotFound"

        # Device endpoint should NOT have been called
        device_calls = [c for c in calls if c["path"] == "/v1/inventory/device/info"]
        assert device_calls == []


# ---------------------------------------------------------------------------
# Test 2: auvik_list_networks — name → ID
# ---------------------------------------------------------------------------


class TestTenantNameResolutionListNetworks:
    async def test_name_resolved_to_id(self):
        """auvik_list_networks(tenants='frontier') sends ID in outgoing request."""
        handler, calls = _multi_handler(
            _TENANT_LIST_PAYLOAD,
            "/v1/inventory/network/info",
            _NETWORK_PAYLOAD,
        )
        client = _client_for(handler)
        result_str = await auvik_list_networks(client, tenants=_FRONTIER_DOMAIN)
        await client.close()

        data = json.loads(result_str)
        assert "error" not in data, f"Unexpected error: {data}"

        network_calls = [c for c in calls if c["path"] == "/v1/inventory/network/info"]
        assert network_calls
        assert network_calls[0]["params"].get("tenants") == _FRONTIER_ID

    async def test_id_passthrough_no_tenant_lookup(self):
        """auvik_list_networks(tenants=<ID>) must NOT call /v1/tenants."""
        handler, calls = _multi_handler(
            _TENANT_LIST_PAYLOAD,
            "/v1/inventory/network/info",
            _NETWORK_PAYLOAD,
        )
        client = _client_for(handler)
        result_str = await auvik_list_networks(client, tenants=_FRONTIER_ID)
        await client.close()

        data = json.loads(result_str)
        assert "error" not in data, f"Unexpected error: {data}"

        tenant_calls = [c for c in calls if c["path"] == "/v1/tenants"]
        assert tenant_calls == []


# ---------------------------------------------------------------------------
# Test 3: auvik_list_alerts — name → ID
# ---------------------------------------------------------------------------


class TestTenantNameResolutionAlerts:
    async def test_name_resolved_to_id(self):
        """auvik_list_alerts(tenants='frontier') sends ID in outgoing request."""
        handler, calls = _multi_handler(
            _TENANT_LIST_PAYLOAD,
            "/v1/alert/history/info",
            _ALERT_PAYLOAD,
        )
        client = _client_for(handler)
        result_str = await auvik_list_alerts(client, tenants=_FRONTIER_DOMAIN)
        await client.close()

        data = json.loads(result_str)
        assert "error" not in data, f"Unexpected error: {data}"

        alert_calls = [c for c in calls if c["path"] == "/v1/alert/history/info"]
        assert alert_calls
        assert alert_calls[0]["params"].get("tenants") == _FRONTIER_ID


# ---------------------------------------------------------------------------
# Regression test: ordering bug — entity resolution must use resolved tenant ID
# ---------------------------------------------------------------------------

_CAMPUS_DEVICE_ID = "456789012345678"
_CAMPUS_DEVICE_NAME = "campus-dininghall-as01v"

_DEVICE_INFO_PAYLOAD_CAMPUS = {
    "data": [
        {
            "id": _CAMPUS_DEVICE_ID,
            "type": "device",
            "attributes": {
                "deviceName": "campus-dininghall-as01v.frontier.edu",
                "ipAddresses": ["192.168.10.5"],
                "deviceType": "switch",
                "onlineStatus": "online",
                "makeModel": "Aruba",
                "vendorName": "Aruba",
            },
        }
    ],
    "links": {},
    "meta": {},
}


class TestTenantResolvedBeforeEntityResolution:
    """Regression: auvik_list_devices(device=<name>, tenants=<name>) was broken.

    The bug: resolve_device was called with the raw tenant *name* (e.g. "frontier")
    instead of the resolved tenant *ID*.  The Auvik API rejects a name in the
    ``tenants`` query-param with HTTP 400, returning empty items, so the device
    resolution failed with NotFound even though the device exists.

    The fix: resolve tenants FIRST at the TOP of the tool, then use the resolved
    ID for all downstream calls (entity resolution AND final query params).
    """

    async def test_device_found_when_tenant_name_given(self):
        """auvik_list_devices(device='campus-dininghall-as01v', tenants='frontier')
        must resolve the tenant name → ID, use that ID during device lookup,
        find the device, and return it (NOT a NotFound).
        """
        # This handler records which tenants= value each outgoing request carries.
        # The device-info endpoint serves the campus device ONLY when tenants=ID.
        # When called with tenants=name (the bug), it returns empty (mimics real API).
        seen_params = []

        def handler(req: httpx.Request) -> httpx.Response:
            params = dict(req.url.params)
            seen_params.append({"path": req.url.path, "params": params})

            if req.url.path == "/v1/tenants":
                return httpx.Response(200, json=_TENANT_LIST_PAYLOAD)

            if req.url.path == "/v1/inventory/device/info":
                # Simulate real Auvik: only return device when tenants param is the ID
                if params.get("tenants") == _FRONTIER_ID:
                    return httpx.Response(200, json=_DEVICE_INFO_PAYLOAD_CAMPUS)
                # Name (or missing) → empty result (mimics API rejecting name)
                return httpx.Response(200, json=_EMPTY_LIST_PAYLOAD)

            # Single-device fetch after name resolution: /v1/inventory/device/info/{id}
            if req.url.path == f"/v1/inventory/device/info/{_CAMPUS_DEVICE_ID}":
                return httpx.Response(
                    200,
                    json={"data": _DEVICE_INFO_PAYLOAD_CAMPUS["data"][0], "links": {}, "meta": {}},
                )

            return httpx.Response(404, json={"errors": [{"title": "Not Found"}]})

        client = _client_for(handler)
        result_str = await auvik_list_devices(
            client,
            device=_CAMPUS_DEVICE_NAME,
            tenants=_FRONTIER_DOMAIN,
        )
        await client.close()

        data = json.loads(result_str)

        # The device must be found — not a NotFound error
        assert "error" not in data, (
            f"Got error (ordering bug still present): {data}\n"
            f"Calls made: {seen_params}"
        )

        # The device-info calls must all carry the resolved tenant ID, never the name
        device_info_calls = [
            c for c in seen_params if c["path"] == "/v1/inventory/device/info"
        ]
        assert device_info_calls, "Expected at least one call to /v1/inventory/device/info"
        for call in device_info_calls:
            tenants_param = call["params"].get("tenants")
            assert tenants_param == _FRONTIER_ID, (
                f"device-info call carried tenants={tenants_param!r} "
                f"instead of ID {_FRONTIER_ID!r} — ordering bug not fixed"
            )

    async def test_tenant_id_passthrough_with_device_name(self):
        """When tenants is already an ID, no /v1/tenants call; device still resolves."""
        seen_params = []

        def handler(req: httpx.Request) -> httpx.Response:
            params = dict(req.url.params)
            seen_params.append({"path": req.url.path, "params": params})

            if req.url.path == "/v1/tenants":
                return httpx.Response(200, json=_TENANT_LIST_PAYLOAD)

            if req.url.path == "/v1/inventory/device/info":
                if params.get("tenants") == _FRONTIER_ID:
                    return httpx.Response(200, json=_DEVICE_INFO_PAYLOAD_CAMPUS)
                return httpx.Response(200, json=_EMPTY_LIST_PAYLOAD)

            # Single-device fetch after name resolution: /v1/inventory/device/info/{id}
            if req.url.path == f"/v1/inventory/device/info/{_CAMPUS_DEVICE_ID}":
                return httpx.Response(
                    200,
                    json={"data": _DEVICE_INFO_PAYLOAD_CAMPUS["data"][0], "links": {}, "meta": {}},
                )

            return httpx.Response(404, json={"errors": [{"title": "Not Found"}]})

        client = _client_for(handler)
        result_str = await auvik_list_devices(
            client,
            device=_CAMPUS_DEVICE_NAME,
            tenants=_FRONTIER_ID,  # already an ID
        )
        await client.close()

        data = json.loads(result_str)
        assert "error" not in data, f"Unexpected error: {data}"

        # /v1/tenants must NOT have been called (ID is idempotent)
        tenant_calls = [c for c in seen_params if c["path"] == "/v1/tenants"]
        assert tenant_calls == [], (
            f"Expected NO /v1/tenants call when tenants is already an ID; got {tenant_calls}"
        )
