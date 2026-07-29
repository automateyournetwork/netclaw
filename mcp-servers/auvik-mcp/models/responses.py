"""Response dataclasses for Auvik MCP Server (036).

Each class mirrors one JSON:API resource object from the Auvik API.
``from_resource(obj)`` maps ``{id, type, attributes}`` → snake_case fields.
``to_dict()`` converts a dataclass to a plain dict, dropping None values.
``to_json()`` serializes via TOON (GCF) with a JSON fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (or list/dict) to a plain dict.

    None values are dropped at every level.
    """
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if v is None:
                continue
            converted = to_dict(v)
            # Drop empty lists/dicts that came from default_factory so they
            # don't clutter output, but keep booleans and zero.
            if converted is not None:
                result[k] = converted
        return result
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items() if v is not None}
    return obj


def to_json(obj: Any) -> str:
    """Serialize *obj* (dataclass or list of dataclasses) to a string.

    Uses the TOON/GCF serializer when available; falls back to JSON.
    """
    if isinstance(obj, list):
        data = [to_dict(item) for item in obj]
    else:
        data = to_dict(obj)

    try:
        from utils.toon_helper import gcf_dumps  # type: ignore
        return gcf_dumps(data)
    except Exception:
        return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# Inventory entities
# ---------------------------------------------------------------------------


@dataclass
class Device:
    """``/v1/inventory/device/info``"""

    id: Optional[str] = None
    type: Optional[str] = None
    device_name: Optional[str] = None
    ip_addresses: Optional[list] = None
    device_type: Optional[str] = None
    make_model: Optional[str] = None
    vendor_name: Optional[str] = None
    software_version: Optional[str] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None
    last_modified: Optional[str] = None
    last_seen_time: Optional[str] = None
    online_status: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Device":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            device_name=attrs.get("deviceName"),
            ip_addresses=attrs.get("ipAddresses"),
            device_type=attrs.get("deviceType"),
            make_model=attrs.get("makeModel"),
            vendor_name=attrs.get("vendorName"),
            software_version=attrs.get("softwareVersion"),
            firmware_version=attrs.get("firmwareVersion"),
            serial_number=attrs.get("serialNumber"),
            description=attrs.get("description"),
            last_modified=attrs.get("lastModified"),
            last_seen_time=attrs.get("lastSeenTime"),
            online_status=attrs.get("onlineStatus"),
        )


@dataclass
class DeviceDetail:
    """``/v1/inventory/device/detail`` (and extended)."""

    id: Optional[str] = None
    type: Optional[str] = None
    discovery_status: Optional[dict] = None
    manage_status: Optional[bool] = None
    traffic_insights_status: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "DeviceDetail":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            discovery_status=attrs.get("discoveryStatus"),
            manage_status=attrs.get("manageStatus"),
            traffic_insights_status=attrs.get("trafficInsightsStatus"),
        )


@dataclass
class DeviceLifecycle:
    """``/v1/inventory/device/lifecycle``"""

    id: Optional[str] = None
    type: Optional[str] = None
    device_name: Optional[str] = None
    sales_availability: Optional[str] = None
    software_maintenance_status: Optional[str] = None
    security_software_maintenance_status: Optional[str] = None
    last_support_status: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "DeviceLifecycle":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            device_name=attrs.get("deviceName"),
            sales_availability=attrs.get("salesAvailability"),
            software_maintenance_status=attrs.get("softwareMaintenanceStatus"),
            security_software_maintenance_status=attrs.get("securitySoftwareMaintenanceStatus"),
            last_support_status=attrs.get("lastSupportStatus"),
        )


@dataclass
class DeviceWarranty:
    """``/v1/inventory/device/warranty``"""

    id: Optional[str] = None
    type: Optional[str] = None
    device_name: Optional[str] = None
    service_coverage_status: Optional[str] = None
    service_attachment_status: Optional[str] = None
    contract_renewal_availability: Optional[str] = None
    warranty_coverage_status: Optional[str] = None
    warranty_expiration_date: Optional[str] = None
    recommended_software_version: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "DeviceWarranty":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            device_name=attrs.get("deviceName"),
            service_coverage_status=attrs.get("serviceCoverageStatus"),
            service_attachment_status=attrs.get("serviceAttachmentStatus"),
            contract_renewal_availability=attrs.get("contractRenewalAvailability"),
            warranty_coverage_status=attrs.get("warrantyCoverageStatus"),
            warranty_expiration_date=attrs.get("warrantyExpirationDate"),
            recommended_software_version=attrs.get("recommendedSoftwareVersion"),
        )


@dataclass
class Network:
    """``/v1/inventory/network/info`` and ``/detail``."""

    id: Optional[str] = None
    type: Optional[str] = None
    network_type: Optional[str] = None
    scan_status: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    primary_collector: Optional[str] = None
    secondary_collectors: Optional[list] = None
    device_count: Optional[int] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Network":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            network_type=attrs.get("networkType"),
            scan_status=attrs.get("scanStatus"),
            description=attrs.get("description"),
            scope=attrs.get("scope"),
            primary_collector=attrs.get("primaryCollector"),
            secondary_collectors=attrs.get("secondaryCollectors"),
            device_count=attrs.get("deviceCount"),
        )


@dataclass
class Interface:
    """``/v1/inventory/interface/info``"""

    id: Optional[str] = None
    type: Optional[str] = None
    interface_type: Optional[str] = None
    admin_status: Optional[str] = None
    operational_status: Optional[str] = None
    mac_address: Optional[str] = None
    index: Optional[int] = None
    description: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Interface":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            interface_type=attrs.get("interfaceType"),
            admin_status=attrs.get("adminStatus"),
            operational_status=attrs.get("operationalStatus"),
            mac_address=attrs.get("macAddress"),
            index=attrs.get("index"),
            description=attrs.get("description"),
        )


@dataclass
class Component:
    """``/v1/inventory/component/info``"""

    id: Optional[str] = None
    type: Optional[str] = None
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    component_type: Optional[str] = None
    current_status: Optional[str] = None
    name: Optional[str] = None
    modified_at: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Component":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            device_id=attrs.get("deviceId"),
            device_name=attrs.get("deviceName"),
            component_type=attrs.get("componentType"),
            current_status=attrs.get("currentStatus"),
            name=attrs.get("name"),
            modified_at=attrs.get("modifiedAt"),
        )


@dataclass
class Configuration:
    """``/v1/inventory/configuration``"""

    id: Optional[str] = None
    type: Optional[str] = None
    backup_time: Optional[str] = None
    is_running: Optional[bool] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Configuration":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            backup_time=attrs.get("backupTime"),
            is_running=attrs.get("isRunning"),
        )


@dataclass
class Tenant:
    """``/v1/tenants`` (list) and ``/v1/tenants/detail``."""

    id: Optional[str] = None
    type: Optional[str] = None
    domain_prefix: Optional[str] = None
    tenant_type: Optional[str] = None
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    subscribed: Optional[bool] = None
    subscription_owner: Optional[bool] = None
    running: Optional[bool] = None
    trial_start_date: Optional[str] = None
    trial_end_date: Optional[str] = None
    address: Optional[dict] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Tenant":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            domain_prefix=attrs.get("domainPrefix"),
            tenant_type=attrs.get("tenantType"),
            display_name=attrs.get("displayName"),
            enabled=attrs.get("enabled"),
            subscribed=attrs.get("subscribed"),
            subscription_owner=attrs.get("subscriptionOwner"),
            running=attrs.get("running"),
            trial_start_date=attrs.get("trialStartDate"),
            trial_end_date=attrs.get("trialEndDate"),
            address=attrs.get("address"),
        )


@dataclass
class EntityNote:
    """``/v1/inventory/entity/note``"""

    id: Optional[str] = None
    type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    last_modified_by: Optional[str] = None
    modified_at: Optional[str] = None
    body: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "EntityNote":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            entity_id=attrs.get("entityId"),
            entity_type=attrs.get("entityType"),
            entity_name=attrs.get("entityName"),
            last_modified_by=attrs.get("lastModifiedBy"),
            modified_at=attrs.get("modifiedAt"),
            body=attrs.get("body"),
        )


@dataclass
class EntityAudit:
    """``/v1/inventory/entity/audit``"""

    id: Optional[str] = None
    type: Optional[str] = None
    user: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    modified_at: Optional[str] = None
    details: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "EntityAudit":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            user=attrs.get("user"),
            category=attrs.get("category"),
            status=attrs.get("status"),
            modified_at=attrs.get("modifiedAt"),
            details=attrs.get("details"),
        )


# ---------------------------------------------------------------------------
# Alerts entity
# ---------------------------------------------------------------------------


@dataclass
class Alert:
    """``/v1/alert/history/info``"""

    id: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    alert_definition_id: Optional[str] = None
    specification_id: Optional[str] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    detected_on: Optional[str] = None
    description: Optional[str] = None
    dismissed: Optional[bool] = None
    dispatched: Optional[bool] = None
    external_ticket: Optional[list] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Alert":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            name=attrs.get("name"),
            severity=attrs.get("severity"),
            status=attrs.get("status"),
            alert_definition_id=attrs.get("alertDefinitionId"),
            specification_id=attrs.get("specificationId"),
            entity_id=attrs.get("entityId"),
            entity_type=attrs.get("entityType"),
            detected_on=attrs.get("detectedOn"),
            description=attrs.get("description"),
            dismissed=attrs.get("dismissed"),
            dispatched=attrs.get("dispatched"),
            external_ticket=attrs.get("externalTicket"),
        )


# ---------------------------------------------------------------------------
# Performance entities
# ---------------------------------------------------------------------------


@dataclass
class Statistic:
    """``/v1/stat/{category}/{statId}``

    Time-series data is stored in ``series`` as the raw list of ``{time, value}``
    points from ``attributes``.
    """

    id: Optional[str] = None
    type: Optional[str] = None
    stat_id: Optional[str] = None
    device_id: Optional[str] = None
    interface_id: Optional[str] = None
    service_id: Optional[str] = None
    component_id: Optional[str] = None
    oid: Optional[str] = None
    interval: Optional[str] = None
    series: Optional[list] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Statistic":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            stat_id=attrs.get("statId"),
            device_id=attrs.get("deviceId"),
            interface_id=attrs.get("interfaceId"),
            service_id=attrs.get("serviceId"),
            component_id=attrs.get("componentId"),
            oid=attrs.get("oid"),
            interval=attrs.get("interval"),
            series=attrs.get("series"),
        )


@dataclass
class SnmpPollerSetting:
    """``/v1/settings/snmppoller``"""

    id: Optional[str] = None
    type: Optional[str] = None
    snmp_poller_setting_id: Optional[str] = None
    name: Optional[str] = None
    oid: Optional[str] = None
    poller_type: Optional[str] = None
    use_as: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "SnmpPollerSetting":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            snmp_poller_setting_id=attrs.get("snmpPollerSettingId"),
            name=attrs.get("name"),
            oid=attrs.get("oid"),
            poller_type=attrs.get("type"),
            use_as=attrs.get("useAs"),
        )


@dataclass
class SnmpPollerHistory:
    """``/v1/stat/snmppoller/string`` and ``/int``

    Time-series results stored in ``data`` as the raw ``{time, value}`` list.
    """

    id: Optional[str] = None
    type: Optional[str] = None
    snmp_poller_setting_id: Optional[str] = None
    device_id: Optional[str] = None
    interval: Optional[str] = None
    data: Optional[list] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "SnmpPollerHistory":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            snmp_poller_setting_id=attrs.get("snmpPollerSettingId"),
            device_id=attrs.get("deviceId"),
            interval=attrs.get("interval"),
            data=attrs.get("data"),
        )


# ---------------------------------------------------------------------------
# Billing entity
# ---------------------------------------------------------------------------


@dataclass
class Usage:
    """``/v1/billing/usage/client`` and ``/device/{id}``"""

    id: Optional[str] = None
    type: Optional[str] = None
    from_date: Optional[str] = None
    thru_date: Optional[str] = None
    device_count: Optional[int] = None
    metrics: Optional[dict] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Usage":
        attrs = obj.get("attributes") or {}
        return cls(
            id=obj.get("id"),
            type=obj.get("type"),
            from_date=attrs.get("fromDate"),
            thru_date=attrs.get("thruDate"),
            device_count=attrs.get("deviceCount"),
            metrics=attrs.get("metrics"),
        )
