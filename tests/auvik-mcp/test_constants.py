"""Tests for utils/constants.py (enum vocabularies and defaults)."""

from utils.constants import (
    DEFAULT_BASE_URL,
    INTERVALS,
    DEVICE_STAT_IDS,
    DEVICE_AVAILABILITY_STAT_IDS,
    INTERFACE_STAT_IDS,
    SERVICE_STAT_IDS,
    COMPONENT_STAT_IDS,
    OID_STAT_IDS,
    COMPONENT_TYPES,
    DEVICE_TYPES,
    INTERFACE_TYPES,
    ALERT_SEVERITIES,
    ALERT_STATUSES,
    LIFECYCLE_STATUSES,
    ONLINE_STATUSES,
    NETWORK_TYPES,
)


def test_default_base_url():
    assert DEFAULT_BASE_URL == "https://auvikapi.us1.my.auvik.com"


def test_intervals():
    assert INTERVALS == {"minute", "hour", "day"}


def test_device_stat_ids_contains_cpu():
    assert "cpuUtilization" in DEVICE_STAT_IDS


def test_device_stat_ids_all_values():
    expected = {
        "bandwidth",
        "cpuUtilization",
        "memoryUtilization",
        "storageUtilization",
        "packetUnicast",
        "packetMulticast",
        "packetBroadcast",
    }
    assert DEVICE_STAT_IDS == expected


def test_device_availability_stat_ids():
    assert DEVICE_AVAILABILITY_STAT_IDS == {"uptime", "outage"}


def test_interface_stat_ids():
    expected = {
        "bandwidth",
        "utilization",
        "packetLoss",
        "packetDiscard",
        "packetMulticast",
        "packetUnicast",
        "packetBroadcast",
    }
    assert INTERFACE_STAT_IDS == expected


def test_service_stat_ids():
    assert SERVICE_STAT_IDS == {"pingTime", "pingPacket"}


def test_component_stat_ids():
    expected = {
        "capacity",
        "counters",
        "idle",
        "latency",
        "power",
        "queueLatency",
        "rate",
        "readiness",
        "ready",
        "speed",
        "swap",
        "swapRate",
        "temperature",
        "totalLatency",
        "utilization",
    }
    assert COMPONENT_STAT_IDS == expected


def test_oid_stat_ids():
    assert OID_STAT_IDS == {"deviceMonitor"}


def test_component_types_contains_power_supply():
    assert "powerSupply" in COMPONENT_TYPES


def test_component_types_all_values():
    expected = {"cpu", "cpuCore", "disk", "fan", "memory", "powerSupply", "systemBoard"}
    assert COMPONENT_TYPES == expected


def test_alert_severities():
    expected = {"unknown", "emergency", "critical", "warning", "info"}
    assert ALERT_SEVERITIES == expected


def test_alert_statuses():
    expected = {"created", "resolved", "paused", "unpaused"}
    assert ALERT_STATUSES == expected


def test_lifecycle_statuses():
    expected = {"covered", "available", "expired", "securityOnly", "unpublished", "empty"}
    assert LIFECYCLE_STATUSES == expected


def test_online_statuses():
    expected = {
        "online",
        "offline",
        "unreachable",
        "testing",
        "unknown",
        "dormant",
        "notPresent",
        "lowerLayerDown",
    }
    assert ONLINE_STATUSES == expected


def test_network_types():
    expected = {"routed", "vlan", "wifi", "loopback", "network", "layer2", "internet"}
    assert NETWORK_TYPES == expected


def test_device_types_authoritative():
    # 48 values verbatim from Auvik DeviceTypeSchema. Pin count + sample real
    # values, and assert hallucinated values are NOT present.
    assert len(DEVICE_TYPES) == 48
    for v in ("multimedia", "phone", "tablet", "ups", "camera", "pdu", "voipSwitch", "utm"):
        assert v in DEVICE_TYPES
    for bogus in ("tablets", "alloy", "sambaServer", "containerPlatform"):
        assert bogus not in DEVICE_TYPES


def test_interface_types_authoritative():
    # 30 values verbatim from Auvik filter[interfaceType] enum.
    assert len(INTERFACE_TYPES) == 30
    for v in ("ethernet", "wifi", "distributedVirtualSwitch", "linkAggregation", "vlan"):
        assert v in INTERFACE_TYPES
    for bogus in ("gigabitEthernet", "tengigabitEthernet", "softwareLoopback"):
        assert bogus not in INTERFACE_TYPES
