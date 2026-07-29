#!/usr/bin/env python3
"""Auvik API MCP Server (Feature 036).

Read-only FastMCP server exposing 20 tools across 4 modules:
  inventory  (9 tools)  — devices, networks, interfaces, components, tenants,
                           entity notes/audits, usage, credential verify
  alerts     (1 tool)   — alert history
  lifecycle  (3 tools)  — device lifecycle, warranty, configuration backups
  performance(7 tools)  — device/interface/service/component/OID stats,
                           SNMP poller settings + history

Transport: stdio (stdout reserved for MCP JSON-RPC; all logging goes to stderr).
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Bootstrap: env + logging BEFORE any internal imports that read env vars
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("auvik-mcp")

# ---------------------------------------------------------------------------
# Configuration (read at module load)
# ---------------------------------------------------------------------------

AUVIK_USERNAME: str = os.getenv("AUVIK_USERNAME", "")
AUVIK_API_KEY: str = os.getenv("AUVIK_API_KEY", "")
AUVIK_VERIFY_SSL: bool = os.getenv("AUVIK_VERIFY_SSL", "true").lower() == "true"
AUVIK_TIMEOUT: int = int(os.getenv("AUVIK_TIMEOUT", "30"))
AUVIK_RATE_LIMIT: int = int(os.getenv("AUVIK_RATE_LIMIT", "600"))  # calls per 60 s
AUVIK_MAX_PAGES: int = int(os.getenv("AUVIK_MAX_PAGES", "50"))

# AUVIK_BASE_URL defaults to the US-1 cluster
from utils.constants import DEFAULT_BASE_URL  # noqa: E402 (after sys.path ready)

AUVIK_BASE_URL: str = os.getenv("AUVIK_BASE_URL", DEFAULT_BASE_URL)

# ---------------------------------------------------------------------------
# Internal imports
# ---------------------------------------------------------------------------

from clients.auvik_client import AuvikClient  # noqa: E402
from utils.rate_limiter import SlidingWindowRateLimiter  # noqa: E402

# Tool core functions — injected with a client by each thin wrapper below
from tools.inventory import (  # noqa: E402
    auvik_get_usage as _get_usage,
    auvik_list_components as _list_components,
    auvik_list_devices as _list_devices,
    auvik_list_entity_audits as _list_entity_audits,
    auvik_list_entity_notes as _list_entity_notes,
    auvik_list_interfaces as _list_interfaces,
    auvik_list_networks as _list_networks,
    auvik_list_tenants as _list_tenants,
    auvik_verify_credentials as _verify_credentials,
)
from tools.alerts import auvik_list_alerts as _list_alerts  # noqa: E402
from tools.lifecycle import (  # noqa: E402
    auvik_list_configurations as _list_configurations,
    auvik_list_device_lifecycle as _list_device_lifecycle,
    auvik_list_device_warranty as _list_device_warranty,
)
from tools.performance import (  # noqa: E402
    auvik_get_component_statistics as _get_component_statistics,
    auvik_get_device_statistics as _get_device_statistics,
    auvik_get_interface_statistics as _get_interface_statistics,
    auvik_get_oid_statistics as _get_oid_statistics,
    auvik_get_service_statistics as _get_service_statistics,
    auvik_get_snmp_poller_history as _get_snmp_poller_history,
    auvik_list_snmp_poller_settings as _list_snmp_poller_settings,
)

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: Optional[AuvikClient] = None


def get_client() -> AuvikClient:
    """Return the shared AuvikClient, creating it on first call.

    Raises:
        ValueError: If AUVIK_USERNAME or AUVIK_API_KEY are not set.
    """
    global _client
    if _client is None:
        if not AUVIK_USERNAME:
            raise ValueError(
                "AUVIK_USERNAME environment variable is required but not set. "
                "Set it to your Auvik account email address."
            )
        if not AUVIK_API_KEY:
            raise ValueError(
                "AUVIK_API_KEY environment variable is required but not set. "
                "Set it to your Auvik API key (Admin → API keys)."
            )
        _client = AuvikClient(
            base_url=AUVIK_BASE_URL,
            username=AUVIK_USERNAME,
            password=AUVIK_API_KEY,
            verify_ssl=AUVIK_VERIFY_SSL,
            timeout=AUVIK_TIMEOUT,
            rate_limiter=SlidingWindowRateLimiter(AUVIK_RATE_LIMIT, 60.0),
        )
        logger.info(
            "AuvikClient initialised: base_url=%s verify_ssl=%s timeout=%ss "
            "rate_limit=%d/60s max_pages=%d",
            AUVIK_BASE_URL,
            AUVIK_VERIFY_SSL,
            AUVIK_TIMEOUT,
            AUVIK_RATE_LIMIT,
            AUVIK_MAX_PAGES,
        )
    return _client


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("auvik-mcp")

# ---------------------------------------------------------------------------
# Inventory tools (9)
# ---------------------------------------------------------------------------


@mcp.tool()
async def auvik_list_devices(
    detail_level: str = "info",
    device: Optional[str] = None,
    device_type: Optional[str] = None,
    make_model: Optional[str] = None,
    vendor_name: Optional[str] = None,
    online_status: Optional[str] = None,
    modified_after: Optional[str] = None,
    not_seen_since: Optional[str] = None,
    networks: Optional[str] = None,
    state_known: Optional[bool] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List or inspect discovered devices from Auvik.

    Fetches device inventory at one of three detail levels: 'info' (default,
    lightweight), 'detail' (management status, discovery flags), or 'extended'
    (extended attributes; requires device_type). When 'device' is supplied, a
    single device is returned instead of a list; the identifier is resolved from
    name / hostname / IP address / Auvik numeric ID. Ambiguous names return
    ResolutionCandidate[] so the caller can disambiguate.

    device_type is REQUIRED by the Auvik API when detail_level='extended'.
    Paginated list results include 'truncated' and 'next_cursor' when the
    AUVIK_MAX_PAGES cap is reached.
    """
    return await _list_devices(
        get_client(),
        detail_level=detail_level,
        device=device,
        device_type=device_type,
        make_model=make_model,
        vendor_name=vendor_name,
        online_status=online_status,
        modified_after=modified_after,
        not_seen_since=not_seen_since,
        networks=networks,
        state_known=state_known,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_networks(
    detail_level: str = "info",
    network: Optional[str] = None,
    network_type: Optional[str] = None,
    scan_status: Optional[str] = None,
    devices: Optional[str] = None,
    modified_after: Optional[str] = None,
    scope: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List or inspect networks discovered by Auvik.

    Returns network inventory at 'info' (default) or 'detail' level. When
    'network' is supplied, a single network is returned; the identifier is
    resolved from network name or Auvik numeric ID. The 'scope' filter is
    only applied at detail_level='detail'. Returns standard pagination meta
    ('truncated', 'next_cursor') when the page cap is reached.
    """
    return await _list_networks(
        get_client(),
        detail_level=detail_level,
        network=network,
        network_type=network_type,
        scan_status=scan_status,
        devices=devices,
        modified_after=modified_after,
        scope=scope,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_interfaces(
    interface: Optional[str] = None,
    parent_device: Optional[str] = None,
    interface_type: Optional[str] = None,
    admin_status: Optional[str] = None,
    operational_status: Optional[str] = None,
    modified_after: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List network interfaces discovered by Auvik.

    Returns interface inventory for all discovered devices. When 'interface'
    is supplied it must be an Auvik numeric ID (name-based interface resolution
    is not supported by the Auvik API). 'parent_device' narrows results to a
    single device and accepts name / IP / Auvik ID for resolution. Filters
    include interface_type, admin_status, and operational_status.
    """
    return await _list_interfaces(
        get_client(),
        interface=interface,
        parent_device=parent_device,
        interface_type=interface_type,
        admin_status=admin_status,
        operational_status=operational_status,
        modified_after=modified_after,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_components(
    component: Optional[str] = None,
    device: Optional[str] = None,
    current_status: Optional[str] = None,
    modified_after: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List hardware components (CPU, memory, disk, fan, PSU, etc.) from Auvik.

    Returns component inventory. When 'component' is an Auvik numeric ID, the
    single component record is returned. 'device' filters components to a
    specific device and accepts name / IP / Auvik ID for resolution.
    current_status accepts 'ok', 'degraded', or 'failed'.
    """
    return await _list_components(
        get_client(),
        component=component,
        device=device,
        current_status=current_status,
        modified_after=modified_after,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_tenants(
    detail: bool = False,
    tenant_domain_prefix: Optional[str] = None,
    available_tenants: Optional[bool] = None,
    raw: bool = False,
) -> str:
    """List Auvik tenants (clients) visible to the authenticated API key.

    Without detail=True, returns the flat tenant catalog from /v1/tenants
    (no filters, no paging — Auvik does not support them on this endpoint).
    This is the source of truth for tenant names used by the 'tenants'
    parameter in all other tools. With detail=True, fetches /v1/tenants/detail,
    which requires tenant_domain_prefix (Auvik API mandate).
    """
    return await _list_tenants(
        get_client(),
        detail=detail,
        tenant_domain_prefix=tenant_domain_prefix,
        available_tenants=available_tenants,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_entity_notes(
    entity: Optional[str] = None,
    entity_type: Optional[str] = None,
    last_modified_by: Optional[str] = None,
    modified_after: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List notes attached to Auvik managed entities.

    Returns entity notes across devices, networks, and interfaces. When
    'entity' is an Auvik numeric ID, the single note is returned directly.
    Otherwise 'entity' is first attempted as a device name resolution; on
    failure the value is passed as-is to filter[entityId]. entity_type
    accepts 'root', 'device', 'network', or 'interface'.
    """
    return await _list_entity_notes(
        get_client(),
        entity=entity,
        entity_type=entity_type,
        last_modified_by=last_modified_by,
        modified_after=modified_after,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_entity_audits(
    audit_id: Optional[str] = None,
    user: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    modified_after: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List audit log entries for Auvik managed entities.

    Returns an audit trail of changes made by users or automated processes.
    When 'audit_id' is supplied, the single audit record is returned.
    Filter by 'user' (email), 'category', 'status', and 'modified_after'
    (ISO-8601 datetime string).
    """
    return await _list_entity_audits(
        get_client(),
        audit_id=audit_id,
        user=user,
        category=category,
        status=status,
        modified_after=modified_after,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_get_usage(
    scope: str = "client",
    device: Optional[str] = None,
    from_date: Optional[str] = None,
    thru_date: Optional[str] = None,
    tenants: Optional[str] = None,
    raw: bool = False,
) -> str:
    """Get Auvik billing/usage data for a date range.

    scope='client' (default) returns aggregate usage for the tenant.
    scope='device' returns per-device usage and requires 'device' (resolved
    from name / IP / Auvik ID). Both scopes require from_date and thru_date
    as ISO-8601 date strings (e.g. '2026-01-01'). The 'tenants' parameter
    applies only to client scope.
    """
    return await _get_usage(
        get_client(),
        scope=scope,
        device=device,
        from_date=from_date,
        thru_date=thru_date,
        tenants=tenants,
        raw=raw,
    )


@mcp.tool()
async def auvik_verify_credentials() -> str:
    """Verify that the configured Auvik API credentials are valid.

    Calls GET /v1/authentication/verify with no parameters. Returns
    authentication status and basic account info on success, or a clear
    AuthError on failure. Use as a health-check before other tool calls.
    """
    return await _verify_credentials(get_client())


# ---------------------------------------------------------------------------
# Alerts tool (1)
# ---------------------------------------------------------------------------


@mcp.tool()
async def auvik_list_alerts(
    alert_id: Optional[str] = None,
    entity: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    dismissed: Optional[bool] = None,
    dispatched: Optional[bool] = None,
    detected_time_after: Optional[str] = None,
    detected_time_before: Optional[str] = None,
    alert_definition_id: Optional[str] = None,
    alert_specification_id: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List or inspect alert history from Auvik.

    Returns alerts from GET /v1/alert/history/info. When 'alert_id' is
    supplied, the single alert record is returned. 'entity' is resolved from
    device name / IP / Auvik ID to filter[entityId]. severity accepts
    'unknown', 'emergency', 'critical', 'warning', or 'info'. status accepts
    'created', 'resolved', 'paused', or 'unpaused'. detected_time_after and
    detected_time_before are ISO-8601 datetime strings (despite the Auvik
    OpenAPI spec mislabelling them as booleans, the API expects datetime values).
    """
    return await _list_alerts(
        get_client(),
        alert_id=alert_id,
        entity=entity,
        severity=severity,
        status=status,
        dismissed=dismissed,
        dispatched=dispatched,
        detected_time_after=detected_time_after,
        detected_time_before=detected_time_before,
        alert_definition_id=alert_definition_id,
        alert_specification_id=alert_specification_id,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Lifecycle tools (3)
# ---------------------------------------------------------------------------


@mcp.tool()
async def auvik_list_device_lifecycle(
    device: Optional[str] = None,
    sales_availability: Optional[str] = None,
    software_maintenance_status: Optional[str] = None,
    security_software_maintenance_status: Optional[str] = None,
    last_support_status: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List device lifecycle (EoL / EoS) information from Auvik.

    Returns end-of-life and end-of-support status for network devices. When
    'device' is supplied (name / IP / Auvik ID), a single device record is
    returned. Filter the list by lifecycle status fields: sales_availability,
    software_maintenance_status, security_software_maintenance_status, and
    last_support_status. Accepted values include 'covered', 'available',
    'expired', 'securityOnly', 'unpublished', 'empty'.
    """
    return await _list_device_lifecycle(
        get_client(),
        device=device,
        sales_availability=sales_availability,
        software_maintenance_status=software_maintenance_status,
        security_software_maintenance_status=security_software_maintenance_status,
        last_support_status=last_support_status,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_device_warranty(
    device: Optional[str] = None,
    covered_under_warranty: Optional[bool] = None,
    covered_under_service: Optional[bool] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List device warranty coverage information from Auvik.

    Returns warranty and service contract status for network devices. When
    'device' is supplied (name / IP / Auvik ID), a single device's warranty
    record is returned. Filter by covered_under_warranty (bool) or
    covered_under_service (bool) to find covered or uncovered devices.
    """
    return await _list_device_warranty(
        get_client(),
        device=device,
        covered_under_warranty=covered_under_warranty,
        covered_under_service=covered_under_service,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_configurations(
    config_id: Optional[str] = None,
    device: Optional[str] = None,
    backup_time_after: Optional[str] = None,
    backup_time_before: Optional[str] = None,
    is_running: Optional[bool] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List device configuration backups stored by Auvik.

    Returns configuration backup records from GET /v1/inventory/configuration.
    When 'config_id' is supplied, the full backup body for that record is
    returned. 'device' filters to a specific device (name / IP / Auvik ID).
    'backup_time_after' and 'backup_time_before' are ISO-8601 datetime strings.
    'is_running' filters for the active running configuration.
    """
    return await _list_configurations(
        get_client(),
        config_id=config_id,
        device=device,
        backup_time_after=backup_time_after,
        backup_time_before=backup_time_before,
        is_running=is_running,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Performance tools (7)
# ---------------------------------------------------------------------------


@mcp.tool()
async def auvik_get_device_statistics(
    stat_id: str,
    availability: bool = False,
    from_time: Optional[str] = None,
    interval: Optional[str] = None,
    thru_time: Optional[str] = None,
    device: Optional[str] = None,
    device_type: Optional[str] = None,
    omit_undiscovered: Optional[bool] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get device performance statistics from Auvik.

    Returns time-series statistics for network devices. stat_id and from_time
    and interval are REQUIRED. availability=False (default) uses
    /v1/stat/device/{statId}; availability=True uses
    /v1/stat/deviceAvailability/{statId}.

    stat_id for availability=False: bandwidth, cpuUtilization,
    memoryUtilization, storageUtilization, packetUnicast, packetMulticast,
    packetBroadcast.
    stat_id for availability=True: uptime, outage.

    from_time and thru_time accept ISO-8601 strings or relative shorthand
    like '-1h', '-30m', '-7d'. interval must be 'minute', 'hour', or 'day'.
    omit_undiscovered (bool) applies only when availability=True.
    """
    return await _get_device_statistics(
        get_client(),
        stat_id=stat_id,
        availability=availability,
        from_time=from_time,
        interval=interval,
        thru_time=thru_time,
        device=device,
        device_type=device_type,
        omit_undiscovered=omit_undiscovered,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_get_interface_statistics(
    stat_id: str,
    from_time: Optional[str] = None,
    interval: Optional[str] = None,
    thru_time: Optional[str] = None,
    interface: Optional[str] = None,
    interface_type: Optional[str] = None,
    parent_device: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get interface performance statistics from Auvik.

    Returns time-series statistics for network interfaces. stat_id, from_time,
    and interval are REQUIRED. stat_id must be one of: bandwidth, utilization,
    packetLoss, packetDiscard, packetMulticast, packetUnicast, packetBroadcast.
    from_time and thru_time accept ISO-8601 strings or relative shorthand
    ('-1h', '-30m', '-7d'). interval must be 'minute', 'hour', or 'day'.
    parent_device is resolved from name / IP / Auvik ID to filter[parentDevice].
    """
    return await _get_interface_statistics(
        get_client(),
        stat_id=stat_id,
        from_time=from_time,
        interval=interval,
        thru_time=thru_time,
        interface=interface,
        interface_type=interface_type,
        parent_device=parent_device,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_get_service_statistics(
    stat_id: str,
    from_time: Optional[str] = None,
    interval: Optional[str] = None,
    thru_time: Optional[str] = None,
    service_id: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get service (ping) statistics from Auvik.

    Returns time-series statistics for monitored services. stat_id, from_time,
    and interval are REQUIRED. stat_id must be 'pingTime' or 'pingPacket'.
    from_time and thru_time accept ISO-8601 strings or relative shorthand
    ('-1h', '-30m', '-7d'). interval must be 'minute', 'hour', or 'day'.
    service_id filters to a specific service.
    """
    return await _get_service_statistics(
        get_client(),
        stat_id=stat_id,
        from_time=from_time,
        interval=interval,
        thru_time=thru_time,
        service_id=service_id,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_get_component_statistics(
    component_type: str,
    stat_id: str,
    from_time: Optional[str] = None,
    interval: Optional[str] = None,
    thru_time: Optional[str] = None,
    component_id: Optional[str] = None,
    parent_device: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get hardware component statistics from Auvik.

    Returns time-series statistics for hardware components. component_type,
    stat_id, from_time, and interval are REQUIRED.
    component_type must be one of: cpu, cpuCore, disk, fan, memory,
    powerSupply, systemBoard.
    stat_id must be one of: capacity, counters, idle, latency, power,
    queueLatency, rate, readiness, ready, speed, swap, swapRate, temperature,
    totalLatency, utilization.
    from_time and thru_time accept ISO-8601 strings or relative shorthand.
    interval must be 'minute', 'hour', or 'day'.
    parent_device is resolved from name / IP / Auvik ID.
    """
    return await _get_component_statistics(
        get_client(),
        component_type=component_type,
        stat_id=stat_id,
        from_time=from_time,
        interval=interval,
        thru_time=thru_time,
        component_id=component_id,
        parent_device=parent_device,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_get_oid_statistics(
    device: Optional[str] = None,
    device_type: Optional[str] = None,
    oid: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get OID (SNMP object identifier) point-in-time statistics from Auvik.

    Returns current OID values from GET /v1/stat/oid/deviceMonitor. Unlike
    other statistics tools, this is a point-in-time read with no time window
    — from_time and interval are not used. 'device' is resolved from name /
    IP / Auvik ID to filter[deviceId]. 'oid' filters to a specific OID value.
    """
    return await _get_oid_statistics(
        get_client(),
        device=device,
        device_type=device_type,
        oid=oid,
        tenants=tenants,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_list_snmp_poller_settings(
    tenants: Optional[str] = None,
    poller_id: Optional[str] = None,
    with_devices: bool = False,
    device: Optional[str] = None,
    use_as: Optional[str] = None,
    type: Optional[str] = None,
    device_type: Optional[str] = None,
    make_model: Optional[str] = None,
    vendor_name: Optional[str] = None,
    oid: Optional[str] = None,
    name: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List SNMP poller settings configured in Auvik.

    'tenants' is REQUIRED by the Auvik API for all SNMP poller endpoints.
    When 'poller_id' is supplied, the single poller setting is returned; if
    'with_devices' is also True, the devices assigned to that poller are
    returned instead. Filter the list by device (resolved from name / IP /
    Auvik ID), use_as ('serialNo' or 'poller'), type ('string' or 'numeric'),
    device_type, make_model, vendor_name, oid, or name.
    """
    return await _list_snmp_poller_settings(
        get_client(),
        tenants=tenants,
        poller_id=poller_id,
        with_devices=with_devices,
        device=device,
        use_as=use_as,
        type=type,
        device_type=device_type,
        make_model=make_model,
        vendor_name=vendor_name,
        oid=oid,
        name=name,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


@mcp.tool()
async def auvik_get_snmp_poller_history(
    value_type: str = "int",
    tenants: Optional[str] = None,
    from_time: Optional[str] = None,
    thru_time: Optional[str] = None,
    interval: Optional[str] = None,
    compact: Optional[bool] = None,
    snmp_poller_setting_id: Optional[str] = None,
    device: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get historical SNMP poller data from Auvik.

    'tenants' and 'from_time' are REQUIRED. value_type selects the data path:
    'int' (default) → /v1/stat/snmppoller/int (requires interval: minute|hour|day).
    'string' → /v1/stat/snmppoller/string (no interval; accepts compact bool).
    from_time and thru_time accept ISO-8601 strings or relative shorthand
    ('-1h', '-30m', '-7d'). snmp_poller_setting_id and device (resolved from
    name / IP / Auvik ID) narrow results to a specific poller or device.
    """
    return await _get_snmp_poller_history(
        get_client(),
        value_type=value_type,
        tenants=tenants,
        from_time=from_time,
        thru_time=thru_time,
        interval=interval,
        compact=compact,
        snmp_poller_setting_id=snmp_poller_setting_id,
        device=device,
        page_first=page_first,
        fetch_all=fetch_all,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Testability exports
# ---------------------------------------------------------------------------

#: The 20 core tool functions (module-level, for test introspection).
TOOL_FUNCS = [
    _list_devices,
    _list_networks,
    _list_interfaces,
    _list_components,
    _list_tenants,
    _list_entity_notes,
    _list_entity_audits,
    _get_usage,
    _verify_credentials,
    _list_alerts,
    _list_device_lifecycle,
    _list_device_warranty,
    _list_configurations,
    _get_device_statistics,
    _get_interface_statistics,
    _get_service_statistics,
    _get_component_statistics,
    _get_oid_statistics,
    _list_snmp_poller_settings,
    _get_snmp_poller_history,
]

#: The 20 registered MCP tool names (authoritative for test assertions).
REGISTERED_TOOL_NAMES = [
    "auvik_list_devices",
    "auvik_list_networks",
    "auvik_list_interfaces",
    "auvik_list_components",
    "auvik_list_tenants",
    "auvik_list_entity_notes",
    "auvik_list_entity_audits",
    "auvik_get_usage",
    "auvik_verify_credentials",
    "auvik_list_alerts",
    "auvik_list_device_lifecycle",
    "auvik_list_device_warranty",
    "auvik_list_configurations",
    "auvik_get_device_statistics",
    "auvik_get_interface_statistics",
    "auvik_get_service_statistics",
    "auvik_get_component_statistics",
    "auvik_get_oid_statistics",
    "auvik_list_snmp_poller_settings",
    "auvik_get_snmp_poller_history",
]

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(
        "Starting auvik-mcp server (transport=stdio, base_url=%s, max_pages=%d)",
        AUVIK_BASE_URL,
        AUVIK_MAX_PAGES,
    )
    mcp.run()
