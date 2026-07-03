"""Canonical Claroty xDome endpoint paths and default field lists.

The xDome OpenAPI spec uses **inconsistent** path naming (some segments use
underscores, some hyphens, some both) and every list endpoint **requires**
a non-empty ``fields`` array in the request body. This module keeps both
in one place so individual tool modules don't drift.

Sourced from the xDome OpenAPI spec at:
- ``components.schemas.<Resource>.fields_enum``
- ``paths.*.<method>.requestBody``
"""

# ---------------------------------------------------------------------------
# Endpoint paths (xDome is unusual in its naming — verify against the spec
# before changing any of these).
# ---------------------------------------------------------------------------
ENDPOINTS = {
    # Devices
    "list_devices": "/api/v1/devices/",
    "device_communication_map": "/api/v1/device/communication-map/",
    "set_purdue_level": "/api/v1/purdue-level/set",
    "set_custom_attribute": "/api/v1/custom-attributes/set",
    # Alerts
    "list_alerts": "/api/v1/alerts/",
    "alert_devices": "/api/v1/alerts/{alert_id}/devices",
    "set_alert_resolution": "/api/v1/device-alert-status/set",
    # Vulnerabilities
    "list_vulnerabilities": "/api/v1/vulnerabilities/",
    "vulnerable_devices": "/api/v1/vulnerabilities/{vulnerability_id}/devices",
    "set_vulnerability_relevance": "/api/v1/device_vulnerability_relations/relevance/set",
    # Sites & edge
    "list_sites": "/api/v1/sites/get",
    "list_edge_locations": "/api/v1/edge-management/locations/get",
    # Servers & OT
    "list_servers": "/api/v1/servers/",
    "list_server_interfaces": "/api/v1/server_interfaces/",
    "list_ot_activity_events": "/api/v1/ot_activity_events/",
    # Audit & governance
    "audit_log": "/api/v1/audit_log/get",
    "list_organization_zones": "/api/v1/organization_zones/",
    # User actions
    "set_labels": "/api/v1/user-actions/labels/set",
    "replace_labels": "/api/v1/user-actions/labels/replace",
    "set_assignees": "/api/v1/user-actions/assignees/set",
}


# ---------------------------------------------------------------------------
# Response wrapper keys. xDome wraps list results in a property named after
# the resource (verified against the OpenAPI response schemas). Falling back
# to common alternatives (``items``, ``results``, ``data``) silently
# misses every real response — the wrapper key MUST be passed explicitly.
# ---------------------------------------------------------------------------
RESPONSE_ITEMS_KEY = {
    "list_devices": "devices",
    "list_alerts": "alerts",
    "alert_devices": "devices",
    "list_vulnerabilities": "vulnerabilities",
    "vulnerable_devices": "devices",
    "list_sites": "sites",
    "list_edge_locations": "records",
    "list_servers": "servers",
    "list_server_interfaces": "server_interfaces",
    "list_ot_activity_events": "ot_activity_events",
    "audit_log": "audit_log",
    "list_organization_zones": "organization_zones",
}


# ---------------------------------------------------------------------------
# Default field lists per resource. Every list endpoint requires a non-empty
# ``fields`` array. These defaults give the agent a useful baseline; tools
# expose an optional ``fields`` parameter so callers can override.
# ---------------------------------------------------------------------------
DEFAULT_DEVICE_FIELDS = [
    "asset_id",
    "uid",
    "local_name",
    "ip_list",
    "mac_list",
    "manufacturer",
    "model",
    "os_name",
    "os_version",
    "purdue_level",
    "device_category",
    "device_type",
    "criticality",
    "risk_score",
    "labels",
]

DEFAULT_SITE_FIELDS = [
    "id",
    "name",
    "location",
    "country_code",
    "description",
    "devices_count",
    "site_group_id",
    "site_group_name",
]

DEFAULT_ALERT_FIELDS = [
    "id",
    "alert_name",
    "alert_type_name",
    "alert_class",
    "category",
    "detected_time",
    "updated_time",
    "devices_count",
    "status",
    "description",
]

DEFAULT_VULNERABILITY_FIELDS = [
    # Note: ``id`` is documented as a Vulnerability field in the spec
    # description table AND is used in spec examples, but it is NOT in
    # the OpenAPI ``Vulnerability.fields_enum`` (a documented spec
    # inconsistency). We do NOT add it to this default list to avoid a
    # potential 422 on validators that strictly enforce the enum. The
    # ``from_xdome_vulnerability`` mapper still surfaces ``id`` if it's
    # present in the response — xDome appears to return it implicitly.
    # If a caller needs ``id`` explicitly projected, pass it via the
    # ``fields=...`` argument.
    "name",
    "vulnerability_type",
    "cve_ids",
    "cvss_v3_score",
    "cvss_v3_vector_string",
    "description",
    "affected_devices_count",
    "is_known_exploited",
    "published_date",
]

DEFAULT_SERVER_FIELDS = [
    "server_name",
    "server_location",
    "server_status",
    "site_id",
    "model",
    "os_version",
    "serial_number",
    "num_of_interfaces",
    "management_ip",
    "uptime_days",
]

DEFAULT_SERVER_INTERFACE_FIELDS = [
    "server_name",
    "interface_name",
    "interface_status",
    "interface_type",
    "interface_connection_type",
    "site_id",
    "avg_traffic_past_month_mbps",
]

DEFAULT_OT_ACTIVITY_FIELDS = [
    "detection_time",
    "event_type",
    "related_alert_ids",
    "description",
    "dest_asset_id",
    "dest_ip",
    "dest_device_name",
    "dest_site_name",
    "protocol",
    "dest_port",
    "source_port",
    "source_asset_id",
    "source_ip",
]

DEFAULT_ZONE_FIELDS = [
    "zone_name",
    "zone_description",
    "zone_source",
    "priority",
    "attributed_devices",
    "exportable_attributed_devices",
    "enabled",
    "created_time",
    "last_update",
    "updated_by",
]


# ---------------------------------------------------------------------------
# SimpleQueryFilter helper.
# xDome's filter_by shape is {"field": str, "operation": str, "value": Any}.
# The full canonical operator list (extracted from the OpenAPI spec
# description tables — different fields support different subsets):
# ---------------------------------------------------------------------------
SIMPLE_QUERY_FILTER_OPERATIONS = (
    # set membership / exact match
    "in",
    "not_in",
    "equals",
    "not_equals",
    # string operations
    "contains",
    "not_contains",
    "starts_with",
    "not_starts_with",
    "ends_with",
    "not_ends_with",
    # null check
    "is_null",
    "is_not_null",
    # numeric comparison (NOT "min", "max", "gte", "gt", ">=", or "greater_than"
    # — those will 422. The canonical name is "greater". Use it for fields
    # like cvss_v3_score, affected_devices_count, devices_count.)
    "greater",
    # CIDR
    "in_subnet",
)


def make_filter(field: str, operation: str, value):
    """Build a SimpleQueryFilter dict.

    Note: the schema key is ``operation``, not ``operator``. (The OpenAPI
    example has ``operator`` in one place, but the schema is
    ``additionalProperties: false`` on ``operation`` — schema wins.)

    See ``SIMPLE_QUERY_FILTER_OPERATIONS`` for the canonical operator list.
    For numeric fields use ``"greater"`` (NOT ``"min"`` / ``"gte"`` /
    ``"greater_than"`` — those will 422).
    """
    return {"field": field, "operation": operation, "value": value}
