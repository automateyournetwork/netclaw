"""Tests for tools/performance.py — performance module tool functions.

Uses httpx.MockTransport (NOT respx). Per tool:
- happy path (correct endpoint + key params including path segments)
- enum/required-param ValidationError (no HTTP call made)
- missing-tenants ValidationError for SNMP poller endpoints
- value_type routing for snmp_poller_history (int requires interval; string does not)
- _resolve_time helper: passthrough + relative conversion
- resolve edge (device name → filter[deviceId])
"""

from __future__ import annotations

import json
import re

import httpx
import pytest

from clients.auvik_client import AuvikClient
from tools.performance import (
    _resolve_time,
    auvik_get_device_statistics,
    auvik_get_interface_statistics,
    auvik_get_service_statistics,
    auvik_get_component_statistics,
    auvik_get_oid_statistics,
    auvik_list_snmp_poller_settings,
    auvik_get_snmp_poller_history,
)
from utils.constants import DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_list_payload(items):
    """Build a minimal JSON:API list payload."""
    return {"data": items, "links": {}, "meta": {}}


def _make_single_payload(item):
    return {"data": item, "links": {}, "meta": {}}


def _stat_item(id_="111111", stat_id="bandwidth"):
    return {
        "id": id_,
        "type": "statDevice",
        "attributes": {
            "statId": stat_id,
            "deviceId": "123456",
            "interval": "hour",
            "series": [{"time": "2024-01-01T00:00:00Z", "value": 42}],
        },
    }


def _snmp_setting_item(id_="222222"):
    return {
        "id": id_,
        "type": "snmpPollerSetting",
        "attributes": {
            "snmpPollerSettingId": id_,
            "name": "My OID",
            "oid": "1.3.6.1.2.1.1.1.0",
            "type": "numeric",
            "useAs": "poller",
        },
    }


def _snmp_history_item(id_="333333"):
    return {
        "id": id_,
        "type": "snmpPollerHistory",
        "attributes": {
            "snmpPollerSettingId": "222222",
            "deviceId": "123456",
            "interval": "hour",
            "data": [{"time": "2024-01-01T00:00:00Z", "value": 100}],
        },
    }


def _device_item(id_="123456", name="core-sw"):
    return {
        "id": id_,
        "type": "device",
        "attributes": {
            "deviceName": name,
            "ipAddresses": ["10.0.0.1"],
            "deviceType": "switch",
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
# _resolve_time helper
# ---------------------------------------------------------------------------


class TestResolveTime:
    def test_iso_string_passthrough(self):
        """An ISO-8601 string is returned unchanged."""
        ts = "2024-06-01T12:00:00Z"
        assert _resolve_time(ts) == ts

    def test_relative_minus_hours(self):
        """-1h → returns a string ending with Z (UTC ISO-8601)."""
        result = _resolve_time("-1h")
        assert isinstance(result, str)
        assert result.endswith("Z")

    def test_relative_minus_minutes(self):
        """-30m → returns a string ending with Z."""
        result = _resolve_time("-30m")
        assert result.endswith("Z")

    def test_relative_minus_days(self):
        """-7d → returns a string ending with Z."""
        result = _resolve_time("-7d")
        assert result.endswith("Z")

    def test_passthrough_non_relative_string(self):
        """A plain string that is not ISO-8601 and not relative is returned as-is."""
        val = "some-opaque-value"
        assert _resolve_time(val) == val

    def test_relative_result_is_earlier_than_now(self):
        """-1h result must be a timestamp in the past."""
        from datetime import datetime, timezone
        result = _resolve_time("-1h")
        # strip trailing Z and parse
        dt = datetime.fromisoformat(result.rstrip("Z")).replace(tzinfo=timezone.utc)
        assert dt < datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# auvik_get_device_statistics
# ---------------------------------------------------------------------------


class TestGetDeviceStatistics:
    async def test_happy_path_device_stat(self):
        """bandwidth stat → GET /v1/stat/device/bandwidth with from_time + interval."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_stat_item()]))

        client = _client_for(handler)
        result_str = await auvik_get_device_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/device/bandwidth"
        assert captured["params"].get("filter[fromTime]") == "2024-01-01T00:00:00Z"
        assert captured["params"].get("filter[interval]") == "hour"
        data = json.loads(result_str)
        assert "items" in data

    async def test_availability_path_switches_endpoint(self):
        """availability=True + uptime stat → /v1/stat/deviceAvailability/uptime."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_device_statistics(
            client,
            stat_id="uptime",
            availability=True,
            from_time="2024-01-01T00:00:00Z",
            interval="day",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/deviceAvailability/uptime"

    async def test_invalid_stat_id_is_validation_error(self):
        """stat_id not in DEVICE_STAT_IDS → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_device_statistics(
            client,
            stat_id="bogus",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_wrong_stat_id_for_availability_is_validation_error(self):
        """availability=True with a device stat_id (not in DEVICE_AVAILABILITY_STAT_IDS) → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_device_statistics(
            client,
            stat_id="bandwidth",  # valid device stat, invalid for availability
            availability=True,
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_missing_from_time_is_validation_error(self):
        """Missing from_time → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_device_statistics(
            client, stat_id="bandwidth", interval="hour"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_invalid_interval_is_validation_error(self):
        """interval not in INTERVALS → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_device_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="weekly",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_device_name_resolved_to_filter(self):
        """device=name → resolved to ID → filter[deviceId]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_device_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            device="core-sw",
        )
        await client.close()

        assert captured_params.get("filter[deviceId]") == "123456"

    async def test_device_id_used_directly(self):
        """device=<id> → filter[deviceId] without resolution HTTP call."""
        call_paths = []

        def handler(req: httpx.Request) -> httpx.Response:
            call_paths.append(req.url.path)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_device_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            device="123456",
        )
        await client.close()

        # Should NOT have called the device resolver endpoint
        assert "/v1/inventory/device/info" not in call_paths

    async def test_availability_omit_undiscovered_param(self):
        """availability=True + omit_undiscovered=True → omitUndiscovered param sent."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_device_statistics(
            client,
            stat_id="uptime",
            availability=True,
            from_time="2024-01-01T00:00:00Z",
            interval="day",
            omit_undiscovered=True,
        )
        await client.close()

        assert captured["params"].get("filter[omitUndiscovered]") in ("true", "True", True)

    async def test_relative_from_time_is_resolved(self):
        """-1h from_time → resolved to ISO-8601 UTC string before sending."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_device_statistics(
            client,
            stat_id="bandwidth",
            from_time="-1h",
            interval="hour",
        )
        await client.close()

        ft = captured["params"].get("filter[fromTime]", "")
        assert ft.endswith("Z"), f"Expected ISO-8601 UTC timestamp, got {ft!r}"


# ---------------------------------------------------------------------------
# auvik_get_interface_statistics
# ---------------------------------------------------------------------------


class TestGetInterfaceStatistics:
    async def test_happy_path(self):
        """bandwidth stat → GET /v1/stat/interface/bandwidth."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_stat_item()]))

        client = _client_for(handler)
        result_str = await auvik_get_interface_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="minute",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/interface/bandwidth"
        assert captured["params"].get("filter[fromTime]") == "2024-01-01T00:00:00Z"
        assert captured["params"].get("filter[interval]") == "minute"
        data = json.loads(result_str)
        assert "items" in data

    async def test_invalid_stat_id_is_validation_error(self):
        """stat_id not in INTERFACE_STAT_IDS → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_interface_statistics(
            client,
            stat_id="cpuUtilization",  # valid for device, not for interface
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_missing_from_time_is_validation_error(self):
        """Missing from_time → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_interface_statistics(
            client, stat_id="bandwidth", interval="hour"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_invalid_interval_is_validation_error(self):
        """interval not in INTERVALS → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_interface_statistics(
            client, stat_id="bandwidth", from_time="2024-01-01T00:00:00Z", interval="weekly"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_interface_filter_sent(self):
        """interface param → filter[interfaceId]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_interface_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            interface="300001",
        )
        await client.close()

        assert captured["params"].get("filter[interfaceId]") == "300001"

    async def test_parent_device_name_resolved(self):
        """parent_device name → resolved to ID → filter[parentDevice]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_interface_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            parent_device="core-sw",
        )
        await client.close()

        assert captured_params.get("filter[parentDevice]") == "123456"


# ---------------------------------------------------------------------------
# auvik_get_service_statistics
# ---------------------------------------------------------------------------


class TestGetServiceStatistics:
    async def test_happy_path(self):
        """pingTime stat → GET /v1/stat/service/pingTime."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_stat_item(stat_id="pingTime")]))

        client = _client_for(handler)
        result_str = await auvik_get_service_statistics(
            client,
            stat_id="pingTime",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/service/pingTime"
        assert captured["params"].get("filter[fromTime]") == "2024-01-01T00:00:00Z"
        assert captured["params"].get("filter[interval]") == "hour"
        data = json.loads(result_str)
        assert "items" in data

    async def test_invalid_stat_id_is_validation_error(self):
        """stat_id not in SERVICE_STAT_IDS → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_service_statistics(
            client,
            stat_id="bandwidth",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_missing_from_time_is_validation_error(self):
        """Missing from_time → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_service_statistics(
            client, stat_id="pingTime", interval="hour"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_invalid_interval_is_validation_error(self):
        """Invalid interval → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_service_statistics(
            client, stat_id="pingTime", from_time="2024-01-01T00:00:00Z", interval="yearly"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_service_id_filter_sent(self):
        """service_id → filter[serviceId]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_service_statistics(
            client,
            stat_id="pingTime",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            service_id="svc-001",
        )
        await client.close()

        assert captured["params"].get("filter[serviceId]") == "svc-001"


# ---------------------------------------------------------------------------
# auvik_get_component_statistics
# ---------------------------------------------------------------------------


class TestGetComponentStatistics:
    async def test_happy_path(self):
        """cpu/utilization → GET /v1/stat/component/cpu/utilization."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_stat_item()]))

        client = _client_for(handler)
        result_str = await auvik_get_component_statistics(
            client,
            component_type="cpu",
            stat_id="utilization",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/component/cpu/utilization"
        assert captured["params"].get("filter[fromTime]") == "2024-01-01T00:00:00Z"
        assert captured["params"].get("filter[interval]") == "hour"
        data = json.loads(result_str)
        assert "items" in data

    async def test_invalid_component_type_is_validation_error(self):
        """component_type not in COMPONENT_TYPES → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_component_statistics(
            client,
            component_type="bogus",
            stat_id="utilization",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_invalid_stat_id_is_validation_error(self):
        """stat_id not in COMPONENT_STAT_IDS → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_component_statistics(
            client,
            component_type="cpu",
            stat_id="bandwidth",  # valid for device/interface, not component
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_missing_from_time_is_validation_error(self):
        """Missing from_time → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_component_statistics(
            client, component_type="cpu", stat_id="utilization", interval="hour"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_invalid_interval_is_validation_error(self):
        """Invalid interval → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_component_statistics(
            client,
            component_type="cpu",
            stat_id="utilization",
            from_time="2024-01-01T00:00:00Z",
            interval="weekly",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_parent_device_name_resolved(self):
        """parent_device name → resolved to ID → filter[parentDevice]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_component_statistics(
            client,
            component_type="cpu",
            stat_id="utilization",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            parent_device="core-sw",
        )
        await client.close()

        assert captured_params.get("filter[parentDevice]") == "123456"

    async def test_component_id_filter_sent(self):
        """component_id → filter[componentId]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_component_statistics(
            client,
            component_type="disk",
            stat_id="capacity",
            from_time="2024-01-01T00:00:00Z",
            interval="day",
            component_id="comp-001",
        )
        await client.close()

        assert captured["params"].get("filter[componentId]") == "comp-001"


# ---------------------------------------------------------------------------
# auvik_get_oid_statistics
# ---------------------------------------------------------------------------


class TestGetOidStatistics:
    async def test_happy_path(self):
        """GET /v1/stat/oid/deviceMonitor (no time params)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_stat_item()]))

        client = _client_for(handler)
        result_str = await auvik_get_oid_statistics(client)
        await client.close()

        assert captured["path"] == "/v1/stat/oid/deviceMonitor"
        # No time params
        assert "filter[fromTime]" not in captured["params"]
        assert "filter[interval]" not in captured["params"]
        data = json.loads(result_str)
        assert "items" in data

    async def test_device_id_filter(self):
        """device=<id> → filter[deviceId]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_oid_statistics(client, device="123456")
        await client.close()

        assert captured["params"].get("filter[deviceId]") == "123456"

    async def test_device_name_resolved_to_filter(self):
        """device name → resolved → filter[deviceId]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_oid_statistics(client, device="core-sw")
        await client.close()

        assert captured_params.get("filter[deviceId]") == "123456"

    async def test_oid_filter_sent(self):
        """oid param → filter[oid]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_oid_statistics(client, oid="1.3.6.1.2.1.1.1.0")
        await client.close()

        assert captured["params"].get("filter[oid]") == "1.3.6.1.2.1.1.1.0"

    async def test_tenants_filter_sent(self):
        """tenants (as ID) → tenants query param forwarded unchanged."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_get_oid_statistics(client, tenants="500001")
        await client.close()

        assert captured["params"].get("tenants") == "500001"


# ---------------------------------------------------------------------------
# auvik_list_snmp_poller_settings
# ---------------------------------------------------------------------------


class TestListSnmpPollerSettings:
    async def test_happy_path_list(self):
        """tenants REQUIRED (as ID) → GET /v1/settings/snmppoller."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_snmp_setting_item()]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        result_str = await auvik_list_snmp_poller_settings(client, tenants="500001")
        await client.close()

        assert captured["path"] == "/v1/settings/snmppoller"
        assert captured["params"].get("tenants") == "500001"
        data = json.loads(result_str)
        assert "items" in data

    async def test_missing_tenants_is_validation_error(self):
        """tenants not provided → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_snmp_poller_settings(client)
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "tenants" in data["error"]["message"].lower()

    async def test_single_poller_by_id(self):
        """poller_id → GET /v1/settings/snmppoller/{id}."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_snmp_setting_item()))

        client = _client_for(handler)
        result_str = await auvik_list_snmp_poller_settings(
            client, tenants="500001", poller_id="222222"
        )
        await client.close()

        assert captured["path"] == "/v1/settings/snmppoller/222222"

    async def test_with_devices_hits_devices_subresource(self):
        """with_devices=True → GET /v1/settings/snmppoller/{id}/devices."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_list_payload([_device_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_snmp_poller_settings(
            client, tenants="500001", poller_id="222222", with_devices=True
        )
        await client.close()

        assert captured["path"] == "/v1/settings/snmppoller/222222/devices"

    async def test_device_filter_by_name_resolved(self):
        """device name → resolved to ID → filter[deviceId]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric tenant ID so no /v1/tenants lookup is needed
        await auvik_list_snmp_poller_settings(
            client, tenants="500001", device="core-sw"
        )
        await client.close()

        assert captured_params.get("filter[deviceId]") == "123456"

    async def test_use_as_filter_sent(self):
        """use_as → filter[useAs]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_snmp_poller_settings(client, tenants="500001", use_as="poller")
        await client.close()

        assert captured["params"].get("filter[useAs]") == "poller"

    async def test_type_filter_sent(self):
        """type param → filter[type]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_snmp_poller_settings(client, tenants="500001", type="numeric")
        await client.close()

        assert captured["params"].get("filter[type]") == "numeric"

    async def test_name_filter_sent(self):
        """name param → filter[name]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_snmp_poller_settings(client, tenants="500001", name="My OID")
        await client.close()

        assert captured["params"].get("filter[name]") == "My OID"


# ---------------------------------------------------------------------------
# auvik_get_snmp_poller_history
# ---------------------------------------------------------------------------


class TestGetSnmpPollerHistory:
    async def test_int_type_happy_path(self):
        """value_type=int → GET /v1/stat/snmppoller/int with interval."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_snmp_history_item()]))

        client = _client_for(handler)
        result_str = await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            value_type="int",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/snmppoller/int"
        assert captured["params"].get("filter[fromTime]") == "2024-01-01T00:00:00Z"
        assert captured["params"].get("filter[interval]") == "hour"
        data = json.loads(result_str)
        assert "items" in data

    async def test_string_type_happy_path(self):
        """value_type=string → GET /v1/stat/snmppoller/string (no interval)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_snmp_history_item()]))

        client = _client_for(handler)
        result_str = await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            value_type="string",
        )
        await client.close()

        assert captured["path"] == "/v1/stat/snmppoller/string"
        assert captured["params"].get("filter[fromTime]") == "2024-01-01T00:00:00Z"
        # No interval for string type
        assert "filter[interval]" not in captured["params"]

    async def test_missing_tenants_is_validation_error(self):
        """tenants not provided → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_snmp_poller_history(
            client, from_time="2024-01-01T00:00:00Z", interval="hour"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "tenants" in data["error"]["message"].lower()

    async def test_missing_from_time_is_validation_error(self):
        """Missing from_time → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_snmp_poller_history(
            client, tenants="500001", interval="hour"
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "from_time" in data["error"]["message"].lower()

    async def test_int_type_missing_interval_is_validation_error(self):
        """value_type=int without interval → ValidationError, no HTTP call."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            value_type="int",
            # interval omitted
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"
        assert "interval" in data["error"]["message"].lower()

    async def test_int_type_invalid_interval_is_validation_error(self):
        """value_type=int with invalid interval → ValidationError."""
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            value_type="int",
            interval="weekly",
        )
        await client.close()

        assert not called
        data = json.loads(result_str)
        assert data["error"]["code"] == "ValidationError"

    async def test_string_type_compact_param_sent(self):
        """value_type=string + compact=True → filter[compact]=true."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            value_type="string",
            compact=True,
        )
        await client.close()

        val = captured["params"].get("filter[compact]")
        assert val in ("true", "True", True)

    async def test_device_name_resolved_to_filter(self):
        """device name → resolved to ID → filter[deviceId]."""
        captured_params = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([_device_item("123456", "core-sw")]))
            captured_params.update(dict(req.url.params))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            value_type="int",
            device="core-sw",
        )
        await client.close()

        assert captured_params.get("filter[deviceId]") == "123456"

    async def test_relative_from_time_resolved(self):
        """-1h from_time → resolved to ISO UTC string before sending."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="-1h",
            value_type="int",
            interval="hour",
        )
        await client.close()

        ft = captured["params"].get("filter[fromTime]", "")
        assert ft.endswith("Z"), f"Expected ISO UTC timestamp, got {ft!r}"

    async def test_snmp_poller_setting_id_filter_sent(self):
        """snmp_poller_setting_id → filter[snmpPollerSettingId]."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_get_snmp_poller_history(
            client,
            tenants="500001",
            from_time="2024-01-01T00:00:00Z",
            interval="hour",
            value_type="int",
            snmp_poller_setting_id="222222",
        )
        await client.close()

        assert captured["params"].get("filter[snmpPollerSettingId]") == "222222"
