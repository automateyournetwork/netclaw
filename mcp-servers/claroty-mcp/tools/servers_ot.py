"""Server inventory and OT activity event tools for the Claroty xDome MCP server.

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/servers/                -> list_servers
  POST /api/v1/server_interfaces/      -> get_server_interfaces
  POST /api/v1/ot_activity_events/     -> list_ot_activity_events
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from models.responses import from_xdome_server, to_dict
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import (
    DEFAULT_OT_ACTIVITY_FIELDS,
    DEFAULT_SERVER_FIELDS,
    DEFAULT_SERVER_INTERFACE_FIELDS,
    ENDPOINTS,
    RESPONSE_ITEMS_KEY,
    make_filter,
)

logger = logging.getLogger("claroty-mcp.servers")


async def list_servers(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 100,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List xDome physical / virtual server nodes.

    Args:
        fields: Defaults to server_name, server_location, server_status,
            site_id, model, os_version, serial_number, num_of_interfaces,
            management_ip, uptime_days.
        filter_field / filter_operation / filter_value: Optional filter.
        limit: Maximum TOTAL items returned (default 100).
        offset: Starting offset.
        page_size: Advanced — defaults to ``min(limit, 500)``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_SERVER_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_servers"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_servers"],
            page_size=effective_page_size,
            max_items=limit,
        )
        servers = [to_dict(from_xdome_server(item)) for item in items]
        return gcf_dumps({"count": len(servers), "servers": servers})
    except Exception as exc:
        logger.exception("list_servers failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def get_server_interfaces(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 100,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List xDome server network interfaces (NIC inventory and traffic stats).

    Args:
        fields: Defaults to server_name, interface_name, interface_status,
            interface_type, interface_connection_type, site_id,
            avg_traffic_past_month_mbps.
        filter_field / filter_operation / filter_value: Optional filter
            (e.g. filter on server_name).
        limit: Maximum TOTAL items returned (default 100).
        offset: Starting offset.
        page_size: Advanced — defaults to ``min(limit, 500)``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_SERVER_INTERFACE_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_server_interfaces"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_server_interfaces"],
            page_size=effective_page_size,
            max_items=limit,
        )
        return gcf_dumps({"count": len(items), "interfaces": items})
    except Exception as exc:
        logger.exception("get_server_interfaces failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def list_ot_activity_events(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 200,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List OT-specific activity events (device chatter, protocol observations).

    Args:
        fields: Defaults to detection_time, event_type, related_alert_ids,
            description, dest_asset_id, dest_ip, dest_device_name,
            dest_site_name, protocol, dest_port, source_port,
            source_asset_id, source_ip.
        filter_field / filter_operation / filter_value: Optional filter
            (e.g. on ``detection_time``, ``event_type``, ``protocol``,
            ``source_asset_id``, ``dest_asset_id``).
        limit: Maximum TOTAL items returned (default 200 — event volumes
            can be high).
        offset: Starting offset.
        page_size: Advanced — defaults to ``min(limit, 500)``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_OT_ACTIVITY_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_ot_activity_events"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_ot_activity_events"],
            page_size=effective_page_size,
            max_items=limit,
        )
        return gcf_dumps({"count": len(items), "events": items})
    except Exception as exc:
        logger.exception("list_ot_activity_events failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)
