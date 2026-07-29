"""Tests for tools/lifecycle.py — lifecycle, warranty, and configuration tools.

Uses httpx.MockTransport (NOT respx). Each tool gets:
- happy-path test (correct endpoint + key params)
- filter tests
- resolution edge-cases (ambiguous/not-found device)
"""

import json

import httpx
import pytest

from clients.auvik_client import AuvikClient
from tools.lifecycle import (
    auvik_list_configurations,
    auvik_list_device_lifecycle,
    auvik_list_device_warranty,
)
from utils.constants import DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_list_payload(items):
    return {"data": items, "links": {}, "meta": {}}


def _make_single_payload(item):
    return {"data": item, "links": {}, "meta": {}}


def _device_item(id_="123456", name="core-sw"):
    return {
        "id": id_,
        "type": "device",
        "attributes": {
            "deviceName": name,
            "ipAddresses": ["10.0.0.1"],
            "deviceType": "switch",
            "onlineStatus": "online",
        },
    }


def _lifecycle_item(id_="111111", name="core-sw"):
    return {
        "id": id_,
        "type": "deviceLifecycle",
        "attributes": {
            "deviceName": name,
            "salesAvailability": "available",
            "softwareMaintenanceStatus": "covered",
            "securitySoftwareMaintenanceStatus": "covered",
            "lastSupportStatus": "covered",
        },
    }


def _warranty_item(id_="222222", name="core-sw"):
    return {
        "id": id_,
        "type": "deviceWarranty",
        "attributes": {
            "deviceName": name,
            "serviceCoverageStatus": "covered",
            "serviceAttachmentStatus": "attached",
            "contractRenewalAvailability": "available",
            "warrantyCoverageStatus": "covered",
            "warrantyExpirationDate": "2027-12-31",
            "recommendedSoftwareVersion": "16.12.4",
        },
    }


def _config_item(id_="333333"):
    return {
        "id": id_,
        "type": "configuration",
        "attributes": {
            "backupTime": "2026-06-20T12:00:00Z",
            "isRunning": True,
        },
    }


def _client_for(handler):
    return AuvikClient(
        base_url=DEFAULT_BASE_URL,
        username="u",
        password="k",
        transport=httpx.MockTransport(handler),
    )


# ---------------------------------------------------------------------------
# TestListDeviceLifecycle
# ---------------------------------------------------------------------------


class TestListDeviceLifecycle:
    async def test_happy_path_list(self):
        """Default call hits /v1/inventory/device/lifecycle."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_lifecycle_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_device_lifecycle(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/device/lifecycle"
        data = json.loads(result_str)
        assert "items" in data
        assert data["items"][0]["sales_availability"] == "available"

    async def test_pagination_meta_included(self):
        """List result includes truncated and next_cursor."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_lifecycle_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_device_lifecycle(client)
        await client.close()

        data = json.loads(result_str)
        assert "truncated" in data
        assert "next_cursor" in data

    async def test_single_lifecycle_by_device_id(self):
        """device param as ID → GET /v1/inventory/device/lifecycle/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_lifecycle_item()))

        client = _client_for(handler)
        result_str = await auvik_list_device_lifecycle(client, device="111111")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/lifecycle/111111"
        data = json.loads(result_str)
        assert "error" not in data

    async def test_device_name_resolved_to_id(self):
        """device param as name → resolve → GET /v1/inventory/device/lifecycle/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(
                    200,
                    json=_make_list_payload([_device_item("123456", "core-sw")]),
                )
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_lifecycle_item()))

        client = _client_for(handler)
        result_str = await auvik_list_device_lifecycle(client, device="core-sw")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/lifecycle/123456"

    async def test_device_ambiguous_returns_error(self):
        """Ambiguous device name → Ambiguous error without making lifecycle call."""

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(
                    200,
                    json=_make_list_payload([
                        _device_item("111111", "sw-core-01"),
                        _device_item("222222", "sw-core-02"),
                    ]),
                )
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_device_lifecycle(client, device="sw-core")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "Ambiguous"

    async def test_sales_availability_filter(self):
        """sales_availability → filter[salesAvailability] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_lifecycle(client, sales_availability="available")
        await client.close()

        assert captured["params"].get("filter[salesAvailability]") == "available"

    async def test_software_maintenance_status_filter(self):
        """software_maintenance_status → filter[softwareMaintenanceStatus]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_lifecycle(client, software_maintenance_status="expired")
        await client.close()

        assert captured["params"].get("filter[softwareMaintenanceStatus]") == "expired"

    async def test_security_software_maintenance_status_filter(self):
        """security_software_maintenance_status → filter[securitySoftwareMaintenanceStatus]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_lifecycle(
            client, security_software_maintenance_status="securityOnly"
        )
        await client.close()

        assert (
            captured["params"].get("filter[securitySoftwareMaintenanceStatus]")
            == "securityOnly"
        )

    async def test_last_support_status_filter(self):
        """last_support_status → filter[lastSupportStatus]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_lifecycle(client, last_support_status="covered")
        await client.close()

        assert captured["params"].get("filter[lastSupportStatus]") == "covered"

    async def test_tenants_filter(self):
        """tenants (as ID) → tenants query param forwarded unchanged."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_list_device_lifecycle(client, tenants="500001")
        await client.close()

        assert captured["params"].get("tenants") == "500001"

    async def test_page_first_param(self):
        """page_first → page[first] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_lifecycle(client, page_first=25)
        await client.close()

        assert captured["params"].get("page[first]") == "25"

    async def test_raw_true(self):
        """raw=True returns items without model mapping."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_lifecycle_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_device_lifecycle(client, raw=True)
        await client.close()

        data = json.loads(result_str)
        assert "items" in data


# ---------------------------------------------------------------------------
# TestListDeviceWarranty
# ---------------------------------------------------------------------------


class TestListDeviceWarranty:
    async def test_happy_path_list(self):
        """Default call hits /v1/inventory/device/warranty."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_warranty_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_device_warranty(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/device/warranty"
        data = json.loads(result_str)
        assert "items" in data
        assert data["items"][0]["warranty_coverage_status"] == "covered"

    async def test_pagination_meta_included(self):
        """List result includes truncated and next_cursor."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_warranty_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_device_warranty(client)
        await client.close()

        data = json.loads(result_str)
        assert "truncated" in data
        assert "next_cursor" in data

    async def test_single_warranty_by_device_id(self):
        """device param as ID → GET /v1/inventory/device/warranty/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_warranty_item()))

        client = _client_for(handler)
        result_str = await auvik_list_device_warranty(client, device="222222")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/warranty/222222"
        data = json.loads(result_str)
        assert "error" not in data

    async def test_device_name_resolved_to_id(self):
        """device param as name → resolve → GET /v1/inventory/device/warranty/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(
                    200,
                    json=_make_list_payload([_device_item("123456", "core-sw")]),
                )
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_warranty_item()))

        client = _client_for(handler)
        await auvik_list_device_warranty(client, device="core-sw")
        await client.close()

        assert captured["path"] == "/v1/inventory/device/warranty/123456"

    async def test_device_ambiguous_returns_error(self):
        """Ambiguous device name → Ambiguous error."""

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(
                    200,
                    json=_make_list_payload([
                        _device_item("111111", "rtr-edge-01"),
                        _device_item("222222", "rtr-edge-02"),
                    ]),
                )
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_device_warranty(client, device="rtr-edge")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "Ambiguous"

    async def test_covered_under_warranty_true(self):
        """covered_under_warranty=True → filter[coveredUnderWarranty]=true."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_warranty(client, covered_under_warranty=True)
        await client.close()

        assert captured["params"].get("filter[coveredUnderWarranty]") == "true"

    async def test_covered_under_warranty_false(self):
        """covered_under_warranty=False → filter[coveredUnderWarranty]=false."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_warranty(client, covered_under_warranty=False)
        await client.close()

        assert captured["params"].get("filter[coveredUnderWarranty]") == "false"

    async def test_covered_under_service_true(self):
        """covered_under_service=True → filter[coveredUnderService]=true."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_warranty(client, covered_under_service=True)
        await client.close()

        assert captured["params"].get("filter[coveredUnderService]") == "true"

    async def test_covered_under_service_false(self):
        """covered_under_service=False → filter[coveredUnderService]=false."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_warranty(client, covered_under_service=False)
        await client.close()

        assert captured["params"].get("filter[coveredUnderService]") == "false"

    async def test_tenants_filter(self):
        """tenants (as ID) → tenants query param forwarded unchanged."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_list_device_warranty(client, tenants="500001")
        await client.close()

        assert captured["params"].get("tenants") == "500001"

    async def test_page_first_param(self):
        """page_first → page[first] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_device_warranty(client, page_first=10)
        await client.close()

        assert captured["params"].get("page[first]") == "10"

    async def test_raw_true(self):
        """raw=True returns items without model mapping."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_warranty_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_device_warranty(client, raw=True)
        await client.close()

        data = json.loads(result_str)
        assert "items" in data


# ---------------------------------------------------------------------------
# TestListConfigurations
# ---------------------------------------------------------------------------


class TestListConfigurations:
    async def test_happy_path_list(self):
        """Default call hits /v1/inventory/configuration."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_config_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_configurations(client)
        await client.close()

        assert captured["path"] == "/v1/inventory/configuration"
        data = json.loads(result_str)
        assert "items" in data
        assert data["items"][0]["is_running"] is True

    async def test_pagination_meta_included(self):
        """List result includes truncated and next_cursor."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_config_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_configurations(client)
        await client.close()

        data = json.loads(result_str)
        assert "truncated" in data
        assert "next_cursor" in data

    async def test_single_config_by_config_id(self):
        """config_id → GET /v1/inventory/configuration/{id} for backup body."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_config_item()))

        client = _client_for(handler)
        result_str = await auvik_list_configurations(client, config_id="333333")
        await client.close()

        assert captured["path"] == "/v1/inventory/configuration/333333"
        data = json.loads(result_str)
        assert "error" not in data

    async def test_device_id_filter(self):
        """device param as ID → filter[deviceId] on list endpoint."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, device="123456")
        await client.close()

        assert captured["path"] == "/v1/inventory/configuration"
        assert captured["params"].get("filter[deviceId]") == "123456"

    async def test_device_name_resolved_to_id_for_filter(self):
        """device param as name → resolve → filter[deviceId]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(
                    200,
                    json=_make_list_payload([_device_item("123456", "core-sw")]),
                )
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, device="core-sw")
        await client.close()

        assert captured_params.get("filter[deviceId]") == "123456"

    async def test_device_ambiguous_returns_error(self):
        """Ambiguous device name → Ambiguous error for configurations."""

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(
                    200,
                    json=_make_list_payload([
                        _device_item("111111", "fw-edge-01"),
                        _device_item("222222", "fw-edge-02"),
                    ]),
                )
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_configurations(client, device="fw-edge")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "Ambiguous"

    async def test_backup_time_after_filter(self):
        """backup_time_after → filter[backupTimeAfter] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, backup_time_after="2026-06-01T00:00:00Z")
        await client.close()

        assert (
            captured["params"].get("filter[backupTimeAfter]") == "2026-06-01T00:00:00Z"
        )

    async def test_backup_time_before_filter(self):
        """backup_time_before → filter[backupTimeBefore] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, backup_time_before="2026-06-30T23:59:59Z")
        await client.close()

        assert (
            captured["params"].get("filter[backupTimeBefore]") == "2026-06-30T23:59:59Z"
        )

    async def test_is_running_true_filter(self):
        """is_running=True → filter[isRunning]=true (lowercase string)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, is_running=True)
        await client.close()

        assert captured["params"].get("filter[isRunning]") == "true"

    async def test_is_running_false_filter(self):
        """is_running=False → filter[isRunning]=false (lowercase string)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, is_running=False)
        await client.close()

        assert captured["params"].get("filter[isRunning]") == "false"

    async def test_tenants_filter(self):
        """tenants (as ID) → tenants query param forwarded unchanged."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_list_configurations(client, tenants="500001")
        await client.close()

        assert captured["params"].get("tenants") == "500001"

    async def test_page_first_param(self):
        """page_first → page[first] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_configurations(client, page_first=100)
        await client.close()

        assert captured["params"].get("page[first]") == "100"

    async def test_raw_true(self):
        """raw=True returns items without model mapping."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_config_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_configurations(client, raw=True)
        await client.close()

        data = json.loads(result_str)
        assert "items" in data
