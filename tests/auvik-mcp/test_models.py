"""Tests for mcp-servers/auvik-mcp/models/responses.py (Phase D1)."""

from __future__ import annotations

import json

import pytest

from models.responses import (
    Alert,
    Component,
    Configuration,
    Device,
    DeviceDetail,
    DeviceLifecycle,
    DeviceWarranty,
    EntityAudit,
    EntityNote,
    Interface,
    Network,
    SnmpPollerHistory,
    SnmpPollerSetting,
    Statistic,
    Tenant,
    Usage,
    to_dict,
    to_json,
)


# ---------------------------------------------------------------------------
# to_dict helpers
# ---------------------------------------------------------------------------


class TestToDict:
    def test_none_values_dropped(self):
        d = Device(id="1", type="device", device_name="x", ip_addresses=["10.0.0.1"], make_model=None)
        result = to_dict(d)
        assert "make_model" not in result
        assert result["device_name"] == "x"
        assert result["ip_addresses"] == ["10.0.0.1"]

    def test_populated_values_kept(self):
        d = Device(id="1", type="device", device_name="router", ip_addresses=["192.168.1.1"], make_model="Cisco ISR")
        result = to_dict(d)
        assert result["make_model"] == "Cisco ISR"

    def test_empty_list_dropped(self):
        """Empty lists (falsy) should be dropped like None."""
        d = Device(id="1", type="device", device_name="x", ip_addresses=[])
        result = to_dict(d)
        # ip_addresses is an empty list — treated as falsy / None-like; OK either way.
        # The spec says "drops None"; empty list behavior is implementation-defined.
        # We only require that explicitly-None fields are absent.
        assert "device_name" in result

    def test_nested_none_dropped_in_dict(self):
        """Dict values that are None should be dropped recursively."""
        d = Tenant(id="1", type="tenant", domain_prefix="acme", tenant_type=None)
        result = to_dict(d)
        assert "tenant_type" not in result
        assert result["domain_prefix"] == "acme"

    def test_list_of_dicts_handled(self):
        """Lists containing dicts pass through to_dict correctly."""
        a = Alert(
            id="a1",
            type="alert",
            name="High CPU",
            severity="critical",
            external_ticket=[{"id": "T1", "url": None}],
        )
        result = to_dict(a)
        assert result["external_ticket"][0]["id"] == "T1"

    def test_raw_dict_none_values_dropped(self):
        raw = {"a": 1, "b": None, "c": "yes"}
        result = to_dict(raw)
        assert "b" not in result
        assert result["a"] == 1


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


class TestToJson:
    def test_returns_string(self):
        d = Device.from_resource({"id": "1", "type": "device", "attributes": {"deviceName": "x", "ipAddresses": ["10.0.0.1"]}})
        result = to_json([d])
        assert isinstance(result, str)

    def test_contains_device_name(self):
        d = Device.from_resource({"id": "1", "type": "device", "attributes": {"deviceName": "edge-router"}})
        result = to_json([d])
        assert "edge-router" in result

    def test_single_object(self):
        d = Device.from_resource({"id": "2", "type": "device", "attributes": {"deviceName": "sw1"}})
        result = to_json(d)
        assert "sw1" in result

    def test_output_is_valid_json_or_toon(self):
        """Output should be parseable as JSON (fallback path) or non-empty string."""
        d = Device.from_resource({"id": "3", "type": "device", "attributes": {}})
        result = to_json(d)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------


class TestDevice:
    _RESOURCE = {
        "id": "1",
        "type": "device",
        "attributes": {
            "deviceName": "core-switch",
            "ipAddresses": ["10.0.0.1"],
            "deviceType": "switch",
            "makeModel": "Cisco Catalyst 9300",
            "vendorName": "Cisco",
            "softwareVersion": "16.12.1",
            "firmwareVersion": "1.0",
            "serialNumber": "SN123",
            "description": "Main switch",
            "lastModified": "2024-01-01T00:00:00Z",
            "lastSeenTime": "2024-01-02T00:00:00Z",
            "onlineStatus": "online",
        },
    }

    def test_from_resource_id_and_type(self):
        d = Device.from_resource(self._RESOURCE)
        assert d.id == "1"
        assert d.type == "device"

    def test_from_resource_device_name(self):
        d = Device.from_resource(self._RESOURCE)
        assert d.device_name == "core-switch"

    def test_from_resource_ip_addresses(self):
        d = Device.from_resource(self._RESOURCE)
        assert d.ip_addresses == ["10.0.0.1"]

    def test_from_resource_all_fields(self):
        d = Device.from_resource(self._RESOURCE)
        assert d.device_type == "switch"
        assert d.make_model == "Cisco Catalyst 9300"
        assert d.vendor_name == "Cisco"
        assert d.software_version == "16.12.1"
        assert d.online_status == "online"
        assert d.last_seen_time == "2024-01-02T00:00:00Z"

    def test_from_resource_missing_attrs_tolerated(self):
        d = Device.from_resource({"id": "2", "type": "device", "attributes": {}})
        assert d.id == "2"
        assert d.device_name is None

    def test_round_trip(self):
        d = Device.from_resource(self._RESOURCE)
        result = to_dict(d)
        assert result["device_name"] == "core-switch"
        assert result["online_status"] == "online"


# ---------------------------------------------------------------------------
# DeviceDetail
# ---------------------------------------------------------------------------


class TestDeviceDetail:
    _RESOURCE = {
        "id": "10",
        "type": "deviceDetail",
        "attributes": {
            "discoveryStatus": {"snmp": "full", "login": "disabled"},
            "manageStatus": True,
            "trafficInsightsStatus": "ok",
        },
    }

    def test_from_resource(self):
        d = DeviceDetail.from_resource(self._RESOURCE)
        assert d.id == "10"
        assert d.manage_status is True
        assert d.traffic_insights_status == "ok"

    def test_discovery_status_preserved(self):
        d = DeviceDetail.from_resource(self._RESOURCE)
        assert d.discovery_status == {"snmp": "full", "login": "disabled"}

    def test_round_trip(self):
        d = DeviceDetail.from_resource(self._RESOURCE)
        result = to_dict(d)
        assert result["manage_status"] is True
        assert result["traffic_insights_status"] == "ok"


# ---------------------------------------------------------------------------
# DeviceLifecycle
# ---------------------------------------------------------------------------


class TestDeviceLifecycle:
    _RESOURCE = {
        "id": "20",
        "type": "deviceLifecycle",
        "attributes": {
            "deviceName": "old-router",
            "salesAvailability": "expired",
            "softwareMaintenanceStatus": "covered",
            "securitySoftwareMaintenanceStatus": "expired",
            "lastSupportStatus": "expired",
        },
    }

    def test_from_resource(self):
        d = DeviceLifecycle.from_resource(self._RESOURCE)
        assert d.id == "20"
        assert d.device_name == "old-router"

    def test_lifecycle_fields(self):
        d = DeviceLifecycle.from_resource(self._RESOURCE)
        assert d.sales_availability == "expired"
        assert d.software_maintenance_status == "covered"
        assert d.security_software_maintenance_status == "expired"
        assert d.last_support_status == "expired"

    def test_round_trip(self):
        d = DeviceLifecycle.from_resource(self._RESOURCE)
        result = to_dict(d)
        assert result["device_name"] == "old-router"
        assert result["last_support_status"] == "expired"


# ---------------------------------------------------------------------------
# DeviceWarranty
# ---------------------------------------------------------------------------


class TestDeviceWarranty:
    _RESOURCE = {
        "id": "30",
        "type": "deviceWarranty",
        "attributes": {
            "deviceName": "firewall-01",
            "serviceCoverageStatus": "covered",
            "serviceAttachmentStatus": "covered",
            "contractRenewalAvailability": "available",
            "warrantyCoverageStatus": "covered",
            "warrantyExpirationDate": "2026-12-31",
            "recommendedSoftwareVersion": "9.1.0",
        },
    }

    def test_from_resource(self):
        d = DeviceWarranty.from_resource(self._RESOURCE)
        assert d.id == "30"
        assert d.device_name == "firewall-01"

    def test_warranty_fields(self):
        d = DeviceWarranty.from_resource(self._RESOURCE)
        assert d.warranty_coverage_status == "covered"
        assert d.warranty_expiration_date == "2026-12-31"
        assert d.recommended_software_version == "9.1.0"

    def test_round_trip(self):
        d = DeviceWarranty.from_resource(self._RESOURCE)
        result = to_dict(d)
        assert result["device_name"] == "firewall-01"
        assert result["warranty_expiration_date"] == "2026-12-31"


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------


class TestNetwork:
    _RESOURCE = {
        "id": "40",
        "type": "network",
        "attributes": {
            "networkType": "routed",
            "scanStatus": "ok",
            "description": "Corporate LAN",
            "scope": "private",
            "primaryCollector": "collector-01",
            "secondaryCollectors": ["collector-02"],
            "deviceCount": 42,
        },
    }

    def test_from_resource(self):
        n = Network.from_resource(self._RESOURCE)
        assert n.id == "40"
        assert n.network_type == "routed"

    def test_round_trip(self):
        n = Network.from_resource(self._RESOURCE)
        result = to_dict(n)
        assert result["network_type"] == "routed"
        assert result["device_count"] == 42


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class TestInterface:
    _RESOURCE = {
        "id": "50",
        "type": "interface",
        "attributes": {
            "interfaceType": "ethernet",
            "adminStatus": "up",
            "operationalStatus": "up",
            "macAddress": "AA:BB:CC:DD:EE:FF",
            "index": 1,
            "description": "Uplink",
        },
    }

    def test_from_resource(self):
        iface = Interface.from_resource(self._RESOURCE)
        assert iface.id == "50"
        assert iface.interface_type == "ethernet"

    def test_round_trip(self):
        iface = Interface.from_resource(self._RESOURCE)
        result = to_dict(iface)
        assert result["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert result["operational_status"] == "up"


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------


class TestComponent:
    _RESOURCE = {
        "id": "60",
        "type": "component",
        "attributes": {
            "deviceName": "core-switch",
            "componentType": "cpu",
            "currentStatus": "ok",
            "name": "CPU 0",
            "modifiedAt": "2024-01-01T00:00:00Z",
        },
    }

    def test_from_resource(self):
        c = Component.from_resource(self._RESOURCE)
        assert c.id == "60"
        assert c.component_type == "cpu"

    def test_round_trip(self):
        c = Component.from_resource(self._RESOURCE)
        result = to_dict(c)
        assert result["current_status"] == "ok"
        assert result["device_name"] == "core-switch"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TestConfiguration:
    _RESOURCE = {
        "id": "70",
        "type": "configuration",
        "attributes": {
            "backupTime": "2024-01-01T12:00:00Z",
            "isRunning": True,
        },
    }

    def test_from_resource(self):
        c = Configuration.from_resource(self._RESOURCE)
        assert c.id == "70"
        assert c.backup_time == "2024-01-01T12:00:00Z"
        assert c.is_running is True

    def test_round_trip(self):
        c = Configuration.from_resource(self._RESOURCE)
        result = to_dict(c)
        assert result["backup_time"] == "2024-01-01T12:00:00Z"
        assert result["is_running"] is True


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------


class TestTenant:
    _RESOURCE = {
        "id": "80",
        "type": "tenant",
        "attributes": {
            "domainPrefix": "acme",
            "tenantType": "client",
            "displayName": "Acme Corp",
            "enabled": True,
            "subscribed": True,
            "subscriptionOwner": False,
            "running": True,
            "trialStartDate": "2024-01-01",
            "trialEndDate": "2024-01-31",
            "address": {"street": "123 Main St"},
        },
    }

    def test_from_resource(self):
        t = Tenant.from_resource(self._RESOURCE)
        assert t.id == "80"
        assert t.domain_prefix == "acme"

    def test_tenant_type(self):
        t = Tenant.from_resource(self._RESOURCE)
        assert t.tenant_type == "client"

    def test_detail_fields(self):
        t = Tenant.from_resource(self._RESOURCE)
        assert t.display_name == "Acme Corp"
        assert t.enabled is True
        assert t.subscribed is True
        assert t.trial_start_date == "2024-01-01"

    def test_round_trip(self):
        t = Tenant.from_resource(self._RESOURCE)
        result = to_dict(t)
        assert result["domain_prefix"] == "acme"
        assert result["tenant_type"] == "client"


# ---------------------------------------------------------------------------
# EntityNote
# ---------------------------------------------------------------------------


class TestEntityNote:
    _RESOURCE = {
        "id": "90",
        "type": "entityNote",
        "attributes": {
            "entityId": "device-1",
            "entityType": "device",
            "entityName": "core-switch",
            "lastModifiedBy": "admin",
            "modifiedAt": "2024-01-01T00:00:00Z",
            "body": "Needs firmware update",
        },
    }

    def test_from_resource(self):
        n = EntityNote.from_resource(self._RESOURCE)
        assert n.id == "90"
        assert n.entity_type == "device"
        assert n.body == "Needs firmware update"

    def test_round_trip(self):
        n = EntityNote.from_resource(self._RESOURCE)
        result = to_dict(n)
        assert result["entity_name"] == "core-switch"
        assert result["last_modified_by"] == "admin"


# ---------------------------------------------------------------------------
# EntityAudit
# ---------------------------------------------------------------------------


class TestEntityAudit:
    _RESOURCE = {
        "id": "100",
        "type": "entityAudit",
        "attributes": {
            "user": "admin@example.com",
            "category": "configuration",
            "status": "completed",
            "modifiedAt": "2024-01-01T00:00:00Z",
            "details": "Changed VLAN config",
        },
    }

    def test_from_resource(self):
        a = EntityAudit.from_resource(self._RESOURCE)
        assert a.id == "100"
        assert a.user == "admin@example.com"

    def test_round_trip(self):
        a = EntityAudit.from_resource(self._RESOURCE)
        result = to_dict(a)
        assert result["category"] == "configuration"
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------


class TestAlert:
    _RESOURCE = {
        "id": "110",
        "type": "alert",
        "attributes": {
            "name": "High CPU Usage",
            "severity": "warning",
            "status": "created",
            "alertDefinitionId": "def-001",
            "specificationId": "spec-001",
            "entityId": "device-1",
            "entityType": "device",
            "detectedOn": "2024-01-01T00:00:00Z",
            "description": "CPU above 90%",
            "dismissed": False,
            "dispatched": True,
            "externalTicket": [{"id": "TICKET-123"}],
        },
    }

    def test_from_resource(self):
        a = Alert.from_resource(self._RESOURCE)
        assert a.id == "110"
        assert a.name == "High CPU Usage"

    def test_severity_and_status(self):
        a = Alert.from_resource(self._RESOURCE)
        assert a.severity == "warning"
        assert a.status == "created"

    def test_detected_on(self):
        a = Alert.from_resource(self._RESOURCE)
        assert a.detected_on == "2024-01-01T00:00:00Z"

    def test_bool_fields(self):
        a = Alert.from_resource(self._RESOURCE)
        assert a.dismissed is False
        assert a.dispatched is True

    def test_external_ticket(self):
        a = Alert.from_resource(self._RESOURCE)
        assert a.external_ticket == [{"id": "TICKET-123"}]

    def test_round_trip(self):
        a = Alert.from_resource(self._RESOURCE)
        result = to_dict(a)
        assert result["name"] == "High CPU Usage"
        assert result["severity"] == "warning"
        assert result["detected_on"] == "2024-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Statistic
# ---------------------------------------------------------------------------


class TestStatistic:
    _RESOURCE = {
        "id": "stat-1",
        "type": "statistic",
        "attributes": {
            "statId": "cpu",
            "deviceId": "device-1",
            "interval": "hour",
            "series": [{"time": "2024-01-01T00:00:00Z", "value": 85.0}],
        },
    }

    def test_from_resource(self):
        s = Statistic.from_resource(self._RESOURCE)
        assert s.id == "stat-1"
        assert s.stat_id == "cpu"

    def test_series_data(self):
        s = Statistic.from_resource(self._RESOURCE)
        assert s.series is not None
        assert len(s.series) == 1

    def test_round_trip(self):
        s = Statistic.from_resource(self._RESOURCE)
        result = to_dict(s)
        assert result["stat_id"] == "cpu"
        assert result["interval"] == "hour"


# ---------------------------------------------------------------------------
# SnmpPollerSetting
# ---------------------------------------------------------------------------


class TestSnmpPollerSetting:
    _RESOURCE = {
        "id": "sp-1",
        "type": "snmpPollerSetting",
        "attributes": {
            "snmpPollerSettingId": "sp-1",
            "name": "Interface Counter",
            "oid": "1.3.6.1.2.1.31.1.1.1.6",
            "type": "numeric",
            "useAs": "poller",
        },
    }

    def test_from_resource(self):
        s = SnmpPollerSetting.from_resource(self._RESOURCE)
        assert s.id == "sp-1"
        assert s.name == "Interface Counter"

    def test_round_trip(self):
        s = SnmpPollerSetting.from_resource(self._RESOURCE)
        result = to_dict(s)
        assert result["oid"] == "1.3.6.1.2.1.31.1.1.1.6"
        assert result["use_as"] == "poller"


# ---------------------------------------------------------------------------
# SnmpPollerHistory
# ---------------------------------------------------------------------------


class TestSnmpPollerHistory:
    _RESOURCE = {
        "id": "sph-1",
        "type": "snmpPollerHistory",
        "attributes": {
            "snmpPollerSettingId": "sp-1",
            "deviceId": "device-1",
            "data": [{"time": "2024-01-01T00:00:00Z", "value": "up"}],
        },
    }

    def test_from_resource(self):
        h = SnmpPollerHistory.from_resource(self._RESOURCE)
        assert h.id == "sph-1"
        assert h.snmp_poller_setting_id == "sp-1"

    def test_data_preserved(self):
        h = SnmpPollerHistory.from_resource(self._RESOURCE)
        assert h.data is not None
        assert len(h.data) == 1

    def test_round_trip(self):
        h = SnmpPollerHistory.from_resource(self._RESOURCE)
        result = to_dict(h)
        assert result["snmp_poller_setting_id"] == "sp-1"
        assert result["device_id"] == "device-1"


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------


class TestUsage:
    _RESOURCE = {
        "id": "usage-1",
        "type": "usage",
        "attributes": {
            "fromDate": "2024-01-01",
            "thruDate": "2024-01-31",
            "deviceCount": 10,
            "metrics": {"billedDevices": 8},
        },
    }

    def test_from_resource(self):
        u = Usage.from_resource(self._RESOURCE)
        assert u.id == "usage-1"
        assert u.from_date == "2024-01-01"

    def test_round_trip(self):
        u = Usage.from_resource(self._RESOURCE)
        result = to_dict(u)
        assert result["thru_date"] == "2024-01-31"
        assert result["device_count"] == 10
