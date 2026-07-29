"""Tests for tools/alerts.py — auvik_list_alerts tool.

Uses httpx.MockTransport (NOT respx). Each tool gets:
- happy-path test (correct endpoint + key params)
- filter tests
- resolution edge-cases (ambiguous device → Ambiguous error)
- critical detected_time_after/before test: value must be the timestamp string, NOT a boolean
"""

import json

import httpx
import pytest

from clients.auvik_client import AuvikClient
from tools.alerts import auvik_list_alerts
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


def _alert_item(
    id_="111111",
    name="High CPU",
    severity="critical",
    status="created",
):
    return {
        "id": id_,
        "type": "alert",
        "attributes": {
            "name": name,
            "severity": severity,
            "status": status,
            "alertDefinitionId": "def-001",
            "specificationId": "spec-001",
            "entityId": "999999",
            "entityType": "device",
            "detectedOn": "2026-06-01T10:00:00Z",
            "description": "CPU utilization exceeded threshold",
            "dismissed": False,
            "dispatched": True,
            "externalTicket": [],
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
            "onlineStatus": "online",
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
# TestListAlerts — happy path
# ---------------------------------------------------------------------------


class TestListAlerts:
    async def test_happy_path_list(self):
        """Default call hits /v1/alert/history/info and returns items list."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([_alert_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_alerts(client)
        await client.close()

        assert captured["path"] == "/v1/alert/history/info"
        data = json.loads(result_str)
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["severity"] == "critical"

    async def test_happy_path_includes_pagination_meta(self):
        """List result includes truncated and next_cursor."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_alert_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_alerts(client)
        await client.close()

        data = json.loads(result_str)
        assert "truncated" in data
        assert "next_cursor" in data

    async def test_single_alert_by_id(self):
        """alert_id → GET /v1/alert/history/info/{id}, returns single alert."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(200, json=_make_single_payload(_alert_item()))

        client = _client_for(handler)
        result_str = await auvik_list_alerts(client, alert_id="111111")
        await client.close()

        assert captured["path"] == "/v1/alert/history/info/111111"
        data = json.loads(result_str)
        # Single alert → not wrapped in items
        assert "error" not in data
        assert data.get("id") == "111111" or data.get("severity") == "critical"

    async def test_single_alert_by_id_no_list_params_sent(self):
        """When alert_id is given, no filter params are added."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_single_payload(_alert_item()))

        client = _client_for(handler)
        await auvik_list_alerts(client, alert_id="111111")
        await client.close()

        assert captured["params"] == {}


# ---------------------------------------------------------------------------
# Filter param tests
# ---------------------------------------------------------------------------


class TestListAlertsFilters:
    async def test_severity_filter(self):
        """severity → filter[severity] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, severity="critical")
        await client.close()

        assert captured["params"].get("filter[severity]") == "critical"

    async def test_status_filter(self):
        """status → filter[status] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, status="resolved")
        await client.close()

        assert captured["params"].get("filter[status]") == "resolved"

    async def test_dismissed_true_filter(self):
        """dismissed=True → filter[dismissed]=true (lowercase string)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, dismissed=True)
        await client.close()

        assert captured["params"].get("filter[dismissed]") == "true"

    async def test_dismissed_false_filter(self):
        """dismissed=False → filter[dismissed]=false (lowercase string)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, dismissed=False)
        await client.close()

        assert captured["params"].get("filter[dismissed]") == "false"

    async def test_dispatched_true_filter(self):
        """dispatched=True → filter[dispatched]=true (lowercase string)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, dispatched=True)
        await client.close()

        assert captured["params"].get("filter[dispatched]") == "true"

    async def test_dispatched_false_filter(self):
        """dispatched=False → filter[dispatched]=false (lowercase string)."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, dispatched=False)
        await client.close()

        assert captured["params"].get("filter[dispatched]") == "false"

    async def test_detected_time_after_is_timestamp_string_not_bool(self):
        """CRITICAL: detected_time_after must be sent as the ISO-8601 timestamp string.

        The Auvik OpenAPI spec mislabels this as a boolean, but the actual
        API expects the datetime string value (e.g. "2026-06-01T00:00:00Z").
        This test verifies we send the string, not a boolean like True/False.
        """
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        ts = "2026-06-01T00:00:00Z"
        await auvik_list_alerts(client, detected_time_after=ts)
        await client.close()

        param_value = captured["params"].get("filter[detectedTimeAfter]")
        # Must be the timestamp string exactly — NOT "true", "false", True, or False
        assert param_value == ts, (
            f"Expected timestamp string {ts!r}, got {param_value!r}. "
            "The API expects the datetime value, not a boolean."
        )
        assert param_value not in ("true", "false"), (
            "filter[detectedTimeAfter] must NOT be a boolean string."
        )

    async def test_detected_time_before_is_timestamp_string_not_bool(self):
        """CRITICAL: detected_time_before must be sent as the ISO-8601 timestamp string."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        ts = "2026-06-30T23:59:59Z"
        await auvik_list_alerts(client, detected_time_before=ts)
        await client.close()

        param_value = captured["params"].get("filter[detectedTimeBefore]")
        assert param_value == ts, (
            f"Expected timestamp string {ts!r}, got {param_value!r}."
        )
        assert param_value not in ("true", "false"), (
            "filter[detectedTimeBefore] must NOT be a boolean string."
        )

    async def test_alert_definition_id_filter(self):
        """alert_definition_id → filter[alertDefinitionId] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, alert_definition_id="def-001")
        await client.close()

        assert captured["params"].get("filter[alertDefinitionId]") == "def-001"

    async def test_alert_specification_id_filter(self):
        """alert_specification_id → filter[alertSpecificationId] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, alert_specification_id="spec-001")
        await client.close()

        assert captured["params"].get("filter[alertSpecificationId]") == "spec-001"

    async def test_tenants_filter(self):
        """tenants (as ID) → tenants query param forwarded unchanged."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        # Use a numeric ID so no /v1/tenants lookup is needed
        await auvik_list_alerts(client, tenants="500001")
        await client.close()

        assert captured["params"].get("tenants") == "500001"

    async def test_page_first_param(self):
        """page_first → page[first] query param."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, page_first=50)
        await client.close()

        assert captured["params"].get("page[first]") == "50"

    async def test_raw_true_returns_raw_api_response(self):
        """raw=True returns items without model mapping."""
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_list_payload([_alert_item()]))

        client = _client_for(handler)
        result_str = await auvik_list_alerts(client, raw=True)
        await client.close()

        data = json.loads(result_str)
        assert "items" in data


# ---------------------------------------------------------------------------
# Entity resolution tests
# ---------------------------------------------------------------------------


class TestListAlertsEntityResolution:
    async def test_entity_as_id_uses_filter_directly(self):
        """entity param that looks like ID → filter[entityId] without device resolution."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(client, entity="999999")
        await client.close()

        assert captured["path"] == "/v1/alert/history/info"
        assert captured["params"].get("filter[entityId]") == "999999"

    async def test_entity_as_name_resolved_to_id(self):
        """entity param as device name → resolved to ID → filter[entityId]."""
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
        await auvik_list_alerts(client, entity="core-sw")
        await client.close()

        assert captured_params.get("filter[entityId]") == "123456"

    async def test_entity_ambiguous_returns_ambiguous_error(self):
        """entity that resolves to multiple devices → Ambiguous error envelope."""

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
        result_str = await auvik_list_alerts(client, entity="sw-core")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "Ambiguous"
        assert "candidates" in data["error"]["details"]

    async def test_entity_not_found_returns_not_found_error(self):
        """entity that resolves to no devices → NotFound error envelope."""

        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path == "/v1/inventory/device/info":
                return httpx.Response(200, json=_make_list_payload([]))
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        result_str = await auvik_list_alerts(client, entity="nonexistent-device")
        await client.close()

        data = json.loads(result_str)
        assert data["error"]["code"] == "NotFound"

    async def test_multiple_filters_combined(self):
        """Multiple filters are all sent as query params together."""
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["params"] = dict(req.url.params)
            return httpx.Response(200, json=_make_list_payload([]))

        client = _client_for(handler)
        await auvik_list_alerts(
            client,
            severity="warning",
            status="created",
            dismissed=False,
            tenants="500001",
        )
        await client.close()

        assert captured["params"].get("filter[severity]") == "warning"
        assert captured["params"].get("filter[status]") == "created"
        assert captured["params"].get("filter[dismissed]") == "false"
        assert captured["params"].get("tenants") == "500001"
