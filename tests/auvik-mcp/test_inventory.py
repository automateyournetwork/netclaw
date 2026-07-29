"""Tests for tools/inventory.py — inventory module tool functions.

Uses httpx.MockTransport (NOT respx). Each tool gets:
- happy-path test (correct endpoint + key params)
- at least one filter test
- validation / resolution edge-case tests
"""

import json

import httpx
import pytest

from clients.auvik_client import AuvikClient
from tools.inventory import (
    auvik_list_devices,
    auvik_list_networks,
    auvik_list_interfaces,
    auvik_list_components,
    auvik_list_tenants,
    auvik_list_entity_notes,
    auvik_list_entity_audits,
    auvik_get_usage,
    auvik_verify_credentials,
)
from utils.constants import DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_list_payload(items):
    """Build a minimal JSON:API list payload."""
    return {
        "data": items,
        "links": {},
        "meta": {},
    }


def _make_single_payload(item):
    """Build a minimal JSON:API single-resource payload."""
    return {"data": item, "links": {}, "meta": {}}


def _device_item(id_="123456", name="core-sw", device_type="switch"):
    return {
        "id": id_,
        "type": "device",
        "attributes": {
            "deviceName": name,
            "ipAddresses": ["10.0.0.1"],
            "deviceType": device_type,
            "onlineStatus": "online",
            "makeModel": "Cisco Catalyst",
            "vendorName": "Cisco",
        },
    }


def _network_item(id_="200001", desc="Corp LAN", network_type="routed"):
    return {
        "id": id_,
        "type": "network",
        "attributes": {
            "description": desc,
            "networkType": network_type,
            "scanStatus": "ok",
        },
    }


def _interface_item(id_="300001"):
    return {
        "id": id_,
        "type": "interface",
        "attributes": {
            "interfaceType": "ethernet",
            "adminStatus": "up",
            "operationalStatus": "up",
        },
    }


def _component_item(id_="400001"):
    return {
        "id": id_,
        "type": "component",
        "attributes": {
            "deviceId": "123456",
            "deviceName": "core-sw",
            "componentType": "cpu",
            "currentStatus": "ok",
            "name": "CPU 0",
        },
    }


def _tenant_item(id_="500001", domain="acme"):
    return {
        "id": id_,
        "type": "tenant",
        "attributes": {
            "domainPrefix": domain,
            "displayName": "Acme Corp",
            "tenantType": "client",
        },
    }


def _note_item(id_="600001"):
    return {
        "id": id_,
        "type": "entityNote",
        "attributes": {
            "entityId": "123456",
            "entityType": "device",
            "entityName": "core-sw",
            "lastModifiedBy": "admin",
            "modifiedAt": "2024-01-01T00:00:00Z",
            "body": "Some note",
        },
    }


def _audit_item(id_="700001"):
    return {
        "id": id_,
        "type": "entityAudit",
        "attributes": {
            "user": "alice",
            "category": "config",
            "status": "success",
            "modifiedAt": "2024-01-01T00:00:00Z",
            "details": "Changed something",
        },
    }


def _usage_item(id_="800001"):
    return {
        "id": id_,
        "type": "clientUsage",
        "attributes": {
            "fromDate": "2024-01-01",
            "thruDate": "2024-01-31",
            "deviceCount": 42,
        },
    }


def _client_for(handler):
    """Create a real AuvikClient backed by a MockTransport."""
    return AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=httpx.MockTransport(handler),
    )


# ---------------------------------------------------------------------------
# auvik_list_devices
# ---------------------------------------------------------------------------


class TestListDevices:
    async def test_happy_path_info_list(self):
        """Default detail_level=info hits /v1/inventory/device/info."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_device_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_devices(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/device/info"
        data = json.loads(result_str)
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["device_name"] == "core-sw"

    async def test_info_detail_level_includes_device_detail(self):
        """detail_level=info should add include=deviceDetail param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, detail_level="info")
        await client.close()

        assert captured["params"].get("include") == "deviceDetail"

    async def test_detail_level_detail_hits_detail_endpoint(self):
        """detail_level=detail hits /v1/inventory/device/detail."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, detail_level="detail")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/detail"

    async def test_detail_level_extended_hits_extended_endpoint(self):
        """detail_level=extended with device_type hits /v1/inventory/device/detail/extended."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, detail_level="extended", device_type="switch")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/detail/extended"
        assert captured["params"].get("filter[deviceType]") == "switch"

    async def test_extended_without_device_type_is_validation_error(self):
        """detail_level=extended without device_type → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_devices(client, detail_level="extended")
        await client.close()

        assert not called, "Handler should NOT be invoked for ValidationError"
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "device_type" in data["error"]["message"].lower()

    async def test_invalid_detail_level_is_validation_error(self):
        """detail_level=bogus → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_devices(client, detail_level="bogus")
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_single_device_by_id(self):
        """device=<id> → GET /v1/inventory/device/info/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_device_item()))

        client = _client_for(handler)
        result_str = await auvik_list_devices(client, device="123456")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/info/123456"
        data = json.loads(result_str)
        # Single device returns the item directly (not under "items")
        assert data.get("id") == "123456" or (isinstance(data.get("items"), list) and len(data["items"]) == 1)

    async def test_filter_online_status(self):
        """online_status filter → filter[onlineStatus] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, online_status="online")
        await client.close()

        assert captured["params"].get("filter[onlineStatus]") == "online"

    async def test_filter_make_model(self):
        """make_model filter → filter[makeModel] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, make_model="Catalyst")
        await client.close()

        assert captured["params"].get("filter[makeModel]") == "Catalyst"

    async def test_tenants_param(self):
        """tenants (as ID) → tenants query param forwarded unchanged."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_list_devices(client, tenants="500001")
        await client.close()

        assert captured["params"].get("tenants") == "500001"

    async def test_device_name_resolution_ambiguous(self):
        """When device name resolves to multiple matches → Ambiguous error returned."""
        call_count = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return two devices with similar names for resolution
            if req.url.path == "/v1/inventory/device/info" and "filter" not in str(req.url.params):
                return httpx.Response(200, json=_make_list_payload([
                    _device_item("111111", "sw-01"),
                    _device_item("222222", "sw-02"),
                ]))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # "sw" is a substring of both device names → ambiguous
        result_str = await auvik_list_devices(client, device="sw")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "Ambiguous"

    async def test_raw_true_returns_json_not_toon(self):
        """raw=True returns the raw API response without model mapping."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_device_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_devices(client, raw=True)
        await client.close()

        data = json.loads(result_str)
        # Raw mode should include the data key as returned by the API
        assert "data" in data or "items" in data

    async def test_pagination_meta_included(self):
        """List result includes truncated and next_cursor pagination meta."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_device_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_devices(client)
        await client.close()

        data = json.loads(result_str)
        assert "truncated" in data
        assert "next_cursor" in data


# ---------------------------------------------------------------------------
# auvik_list_networks
# ---------------------------------------------------------------------------


class TestListNetworks:
    async def test_happy_path_info_list(self):
        """Default detail_level=info hits /v1/inventory/network/info."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_network_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_networks(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/network/info"
        data = json.loads(result_str)
        assert "items" in data
        assert data["items"][0]["description"] == "Corp LAN"

    async def test_detail_level_detail_hits_detail_endpoint(self):
        """detail_level=detail hits /v1/inventory/network/detail."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_networks(client, detail_level="detail")
        await client.close()

        assert captured["path"] == "/v1/inventory/network/detail"

    async def test_invalid_detail_level_is_validation_error(self):
        """detail_level=bogus → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_networks(client, detail_level="bogus")
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_single_network_by_id(self):
        """network=<id> → GET /v1/inventory/network/info/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_network_item()))

        client = _client_for(handler)
        await auvik_list_networks(client, network="200001")
        await client.close()

        assert captured["path"] == "/v1/inventory/network/info/200001"

    async def test_filter_network_type(self):
        """network_type → filter[networkType] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_networks(client, network_type="routed")
        await client.close()

        assert captured["params"].get("filter[networkType]") == "routed"

    async def test_filter_scan_status(self):
        """scan_status → filter[scanStatus] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_networks(client, scan_status="ok")
        await client.close()

        assert captured["params"].get("filter[scanStatus]") == "ok"

    async def test_network_not_found_by_name(self):
        """network by name that doesn't match → NotFound error."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_network_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_networks(client, network="nonexistent-network")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "NotFound"


# ---------------------------------------------------------------------------
# auvik_list_interfaces
# ---------------------------------------------------------------------------


class TestListInterfaces:
    async def test_happy_path_list(self):
        """Hits /v1/inventory/interface/info."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_interface_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_interfaces(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/interface/info"
        data = json.loads(result_str)
        assert "items" in data

    async def test_single_interface_by_id(self):
        """interface=<id> → GET /v1/inventory/interface/info/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_interface_item()))

        client = _client_for(handler)
        await auvik_list_interfaces(client, interface="300001")
        await client.close()

        assert captured["path"] == "/v1/inventory/interface/info/300001"

    async def test_parent_device_id_adds_filter(self):
        """parent_device as ID → filter[parentDevice] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_interfaces(client, parent_device="123456")
        await client.close()

        assert captured["path"] == "/v1/inventory/interface/info"
        assert captured["params"].get("filter[parentDevice]") == "123456"

    async def test_parent_device_name_resolved(self):
        """parent_device as name → resolve to ID → filter[parentDevice]."""
        call_count = 0
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_interfaces(client, parent_device="core-sw")
        await client.close()

        assert captured_params.get("filter[parentDevice]") == "123456"

    async def test_filter_interface_type(self):
        """interface_type → filter[interfaceType] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_interfaces(client, interface_type="ethernet")
        await client.close()

        assert captured["params"].get("filter[interfaceType]") == "ethernet"

    async def test_filter_admin_status(self):
        """admin_status → filter[adminStatus] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_interfaces(client, admin_status="up")
        await client.close()

        assert captured["params"].get("filter[adminStatus]") == "up"

    async def test_filter_operational_status(self):
        """operational_status → filter[operationalStatus] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_interfaces(client, operational_status="down")
        await client.close()

        assert captured["params"].get("filter[operationalStatus]") == "down"


# ---------------------------------------------------------------------------
# auvik_list_components
# ---------------------------------------------------------------------------


class TestListComponents:
    async def test_happy_path_list(self):
        """Hits /v1/inventory/component/info."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_component_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_components(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/component/info"
        data = json.loads(result_str)
        assert "items" in data

    async def test_single_component_by_id(self):
        """component=<id> → GET /v1/inventory/component/info/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_component_item()))

        client = _client_for(handler)
        await auvik_list_components(client, component="400001")
        await client.close()

        assert captured["path"] == "/v1/inventory/component/info/400001"

    async def test_device_id_adds_filter_device_id(self):
        """device=<id> → filter[deviceId] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_components(client, device="123456")
        await client.close()

        assert captured["params"].get("filter[deviceId]") == "123456"

    async def test_device_name_resolved_to_id(self):
        """device=name → resolve to ID → filter[deviceId]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_components(client, device="core-sw")
        await client.close()

        assert captured_params.get("filter[deviceId]") == "123456"

    async def test_current_status_filter(self):
        """current_status → filter[currentStatus] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_components(client, current_status="degraded")
        await client.close()

        assert captured["params"].get("filter[currentStatus]") == "degraded"

    async def test_modified_after_filter(self):
        """modified_after → filter[modifiedAfter] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_components(client, modified_after="2024-01-01T00:00:00Z")
        await client.close()

        assert captured["params"].get("filter[modifiedAfter]") == "2024-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# auvik_list_tenants
# ---------------------------------------------------------------------------


class TestListTenants:
    async def test_happy_path_simple_list(self):
        """detail=False hits /v1/tenants."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_tenant_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_tenants(client)
        await client.close()

        assert captured["path"] == "/v1/tenants"
        data = json.loads(result_str)
        assert "items" in data

    async def test_detail_true_hits_detail_endpoint(self):
        """detail=True with tenant_domain_prefix → /v1/tenants/detail with param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_tenant_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_tenants(client, detail=True, tenant_domain_prefix="acme")
        await client.close()

        assert captured["path"] == "/v1/tenants/detail"
        assert captured["params"].get("tenantDomainPrefix") == "acme"

    async def test_detail_true_without_prefix_is_validation_error(self):
        """detail=True without tenant_domain_prefix → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_tenants(client, detail=True)
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "tenant_domain_prefix" in data["error"]["message"].lower()

    async def test_available_tenants_param(self):
        """available_tenants=True → availableTenants=True param on detail endpoint."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_tenants(client, detail=True, tenant_domain_prefix="acme", available_tenants=True)
        await client.close()

        assert captured["params"].get("availableTenants") == "True" or captured["params"].get("availableTenants") is True or str(captured["params"].get("availableTenants")).lower() == "true"


# ---------------------------------------------------------------------------
# auvik_list_entity_notes
# ---------------------------------------------------------------------------


class TestListEntityNotes:
    async def test_happy_path_list(self):
        """Hits /v1/inventory/entity/note."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_note_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_entity_notes(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/entity/note"
        data = json.loads(result_str)
        assert "items" in data

    async def test_single_note_by_id(self):
        """entity=<id> that looks like ID → GET /v1/inventory/entity/note/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_note_item()))

        client = _client_for(handler)
        await auvik_list_entity_notes(client, entity="600001")
        await client.close()

        assert captured["path"] == "/v1/inventory/entity/note/600001"

    async def test_entity_id_filter_non_id(self):
        """entity param that doesn't look like ID → try device resolve then filter[entityId]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_notes(client, entity="core-sw")
        await client.close()

        assert captured["params"].get("filter[entityId]") == "123456"

    async def test_entity_type_filter(self):
        """entity_type → filter[entityType] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_notes(client, entity_type="device")
        await client.close()

        assert captured["params"].get("filter[entityType]") == "device"

    async def test_last_modified_by_filter(self):
        """last_modified_by → filter[lastModifiedBy] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_notes(client, last_modified_by="alice")
        await client.close()

        assert captured["params"].get("filter[lastModifiedBy]") == "alice"

    async def test_modified_after_filter(self):
        """modified_after → filter[modifiedAfter] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_notes(client, modified_after="2024-01-01T00:00:00Z")
        await client.close()

        assert captured["params"].get("filter[modifiedAfter]") == "2024-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# auvik_list_entity_audits
# ---------------------------------------------------------------------------


class TestListEntityAudits:
    async def test_happy_path_list(self):
        """Hits /v1/inventory/entity/audit."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_audit_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_entity_audits(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/entity/audit"
        data = json.loads(result_str)
        assert "items" in data

    async def test_single_audit_by_id(self):
        """audit_id → GET /v1/inventory/entity/audit/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_audit_item()))

        client = _client_for(handler)
        await auvik_list_entity_audits(client, audit_id="700001")
        await client.close()

        assert captured["path"] == "/v1/inventory/entity/audit/700001"

    async def test_filter_user(self):
        """user → filter[user] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_audits(client, user="alice")
        await client.close()

        assert captured["params"].get("filter[user]") == "alice"

    async def test_filter_category(self):
        """category → filter[category] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_audits(client, category="config")
        await client.close()

        assert captured["params"].get("filter[category]") == "config"

    async def test_filter_status(self):
        """status → filter[status] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_audits(client, status="success")
        await client.close()

        assert captured["params"].get("filter[status]") == "success"

    async def test_filter_modified_after(self):
        """modified_after → filter[modifiedAfter] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_entity_audits(client, modified_after="2024-06-01T00:00:00Z")
        await client.close()

        assert captured["params"].get("filter[modifiedAfter]") == "2024-06-01T00:00:00Z"


# ---------------------------------------------------------------------------
# auvik_get_usage
# ---------------------------------------------------------------------------


class TestGetUsage:
    async def test_client_scope_happy_path(self):
        """scope=client hits /v1/billing/usage/client with from/thru date params."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(
            client, from_date="2024-01-01", thru_date="2024-01-31"
        )
        await client.close()

        assert captured["path"] == "/v1/billing/usage/client"
        assert captured["params"].get("filter[fromDate]") == "2024-01-01"
        assert captured["params"].get("filter[thruDate]") == "2024-01-31"
        data = json.loads(result_str)
        assert "error" not in data

    async def test_client_scope_list_data_msp_account(self):
        """MSP accounts: /v1/billing/usage/client returns `data` as a LIST (one
        row per tenant). Must shape each row into items[] instead of crashing
        with "'list' object has no attribute 'get'".
        """
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_make_list_payload([_usage_item("800001"), _usage_item("800002")]),
            )

        client = _client_for(handler)
        result_str = await auvik_get_usage(
            client, from_date="2024-01-01", thru_date="2024-01-31"
        )
        await client.close()

        data = json.loads(result_str)
        assert "error" not in data, data
        assert isinstance(data.get("items"), list)
        assert len(data["items"]) == 2

    async def test_client_scope_missing_from_date_is_validation_error(self):
        """Missing from_date → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(client, thru_date="2024-01-31")
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "from_date" in data["error"]["message"].lower()

    async def test_client_scope_missing_thru_date_is_validation_error(self):
        """Missing thru_date → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(client, from_date="2024-01-01")
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "thru_date" in data["error"]["message"].lower()

    async def test_client_scope_missing_both_dates_is_validation_error(self):
        """Missing both from_date and thru_date → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(client)
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_device_scope_happy_path(self):
        """scope=device with device ID → /v1/billing/usage/device/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(
            client,
            scope="device",
            device="123456",
            from_date="2024-01-01",
            thru_date="2024-01-31",
        )
        await client.close()

        assert captured["path"] == "/v1/billing/usage/device/123456"
        assert captured["params"].get("filter[fromDate]") == "2024-01-01"
        assert captured["params"].get("filter[thruDate]") == "2024-01-31"

    async def test_device_scope_missing_device_is_validation_error(self):
        """scope=device without device param → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(
            client, scope="device", from_date="2024-01-01", thru_date="2024-01-31"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "device" in data["error"]["message"].lower()

    async def test_device_scope_resolves_device_name(self):
        """scope=device with device name → resolve to ID → /v1/billing/usage/device/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        await auvik_get_usage(
            client,
            scope="device",
            device="core-sw",
            from_date="2024-01-01",
            thru_date="2024-01-31",
        )
        await client.close()

        assert captured["path"] == "/v1/billing/usage/device/123456"

    async def test_invalid_scope_is_validation_error(self):
        """scope=bogus → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        result_str = await auvik_get_usage(
            client, scope="bogus", from_date="2024-01-01", thru_date="2024-01-31"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_client_scope_with_tenants(self):
        """scope=client with tenants (as ID) → tenants param forwarded."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_single_payload(_usage_item()))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_get_usage(
            client,
            from_date="2024-01-01",
            thru_date="2024-01-31",
            tenants="500001",
        )
        await client.close()

        assert captured["params"].get("tenants") == "500001"


# ---------------------------------------------------------------------------
# auvik_verify_credentials
# ---------------------------------------------------------------------------


class TestVerifyCredentials:
    async def test_happy_path(self):
        """Hits /v1/authentication/verify."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json={"data": {"status": "authenticated"}})

        client = _client_for(handler)
        result_str = await auvik_verify_credentials(client)
        await client.close()

        assert captured["path"] == "/v1/authentication/verify"
        data = json.loads(result_str)
        assert "error" not in data

    async def test_upstream_error_wrapped(self):
        """Auth failure → structured error response."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"errors": [{"title": "Unauthorized"}]})

        client = _client_for(handler)
        result_str = await auvik_verify_credentials(client)
        await client.close()

        data = json.loads(result_str)
        assert "error" in data

    async def test_no_params_sent(self):
        """verify_credentials sends no query params."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json={"data": {}})

        client = _client_for(handler)
        await auvik_verify_credentials(client)
        await client.close()

        assert captured["params"] == {}


# ---------------------------------------------------------------------------
# Fix 1: state_known bool serialized as lowercase string
# ---------------------------------------------------------------------------


class TestStateKnownBoolSerialization:
    async def test_state_known_true_sends_lowercase_string(self):
        """state_known=True → filter[stateKnown]='true' (not Python 'True')."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, state_known=True)
        await client.close()

        assert captured["params"].get("filter[stateKnown]") == "true"

    async def test_state_known_false_sends_lowercase_string(self):
        """state_known=False → filter[stateKnown]='false' (not Python 'False')."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, state_known=False)
        await client.close()

        assert captured["params"].get("filter[stateKnown]") == "false"

    async def test_state_known_true_detail_level_detail(self):
        """state_known=True with detail_level=detail → filter[stateKnown]='true'."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, detail_level="detail", state_known=True)
        await client.close()

        assert captured["params"].get("filter[stateKnown]") == "true"

    async def test_state_known_true_detail_level_extended(self):
        """state_known=True with detail_level=extended → filter[stateKnown]='true'."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client, detail_level="extended", device_type="switch", state_known=True)
        await client.close()

        assert captured["params"].get("filter[stateKnown]") == "true"

    async def test_state_known_none_omitted(self):
        """state_known=None (default) → filter[stateKnown] absent from params."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_devices(client)
        await client.close()

        assert "filter[stateKnown]" not in captured["params"]


# ---------------------------------------------------------------------------
# Fix 2: mid-pagination errors surfaced by _list_result
# ---------------------------------------------------------------------------


class TestMidPaginationErrorSurfaced:
    async def test_mid_pagination_503_surfaced_with_partial_items(self):
        """Page 1 succeeds (links.next set); page 2 returns 503.
        Result includes partial items from page 1 AND error with code UpstreamError.
        """
        call_count = 0
        page1_url = f"{DEFAULT_BASE_URL}/v1/inventory/device/info"
        # The MockTransport does not process base_url; path routing is by req.url.path.
        # links.next must be an absolute URL that the client will follow as-is.
        next_page_url = f"{DEFAULT_BASE_URL}/v1/inventory/device/info?page%5Bcursor%5D=abc123"

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First page: one item + links.next to trigger pagination
                payload = {
                    "data": [_device_item("111111", "router-01")],
                    "links": {"next": next_page_url},
                    "meta": {},
                }
                return httpx.Response(200, json=payload)
            else:
                # Second page (following links.next): simulate upstream 503
                return httpx.Response(503, text="Service Unavailable")

        client = _client_for(handler)
        result_str = await auvik_list_devices(client)
        await client.close()

        assert call_count == 2, "Handler should be called twice (page 1 + page 2)"
        data = json.loads(result_str)

        # Partial items from page 1 must be present
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["device_name"] == "router-01"

        # Error must be surfaced
        assert "error" in data
        assert data["error"]["code"] == "UpstreamError"
        assert data["error"]["message"]  # non-empty


# ---------------------------------------------------------------------------
# Fix 3: auvik_list_components rejects non-ID component values
# ---------------------------------------------------------------------------


class TestListComponentsNonIdValidation:
    async def test_non_id_component_returns_validation_error_no_http_call(self):
        """component='CPU 0' (not an Auvik ID) → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_single_payload(_component_item()))

        client = _client_for(handler)
        result_str = await auvik_list_components(client, component="CPU 0")
        await client.close()

        assert not called, "Handler should NOT be invoked for a non-ID component"
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "Auvik numeric ID" in data["error"]["message"]

    async def test_id_component_makes_single_fetch(self):
        """component='242216279026467843' (looks like Auvik ID) → GET /component/info/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_component_item("242216279026467843")))

        client = _client_for(handler)
        result_str = await auvik_list_components(client, component="242216279026467843")
        await client.close()

        assert captured["path"] == "/v1/inventory/component/info/242216279026467843"
        data = json.loads(result_str)
        assert "error" not in data
