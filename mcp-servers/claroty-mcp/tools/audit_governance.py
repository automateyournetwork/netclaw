"""Audit log and organization governance tools for the Claroty xDome MCP server.

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/audit_log/get        -> get_audit_log
  POST /api/v1/organization_zones/  -> list_organization_zones

Note: ``audit_log/get`` does NOT require a ``fields`` parameter (unlike
most other list endpoints) — it returns a fixed shape. ``organization_zones``
does require fields.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import (
    DEFAULT_ZONE_FIELDS,
    ENDPOINTS,
    RESPONSE_ITEMS_KEY,
    make_filter,
)

logger = logging.getLogger("claroty-mcp.audit")


async def get_audit_log(
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 200,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """Fetch the xDome audit log (user actions, config changes, policy updates).

    Args:
        filter_field / filter_operation / filter_value: Optional filter
            on the audit entries.
        limit: Maximum TOTAL items returned (default 200).
        offset: Starting offset.
        page_size: Advanced — defaults to ``min(limit, 500)``.

    Returns:
        GCF-serialised list of audit entries. Pair with GAIT to
        cross-reference NetClaw-initiated changes against xDome's own log.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {"offset": offset, "limit": effective_page_size}
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["audit_log"],
            body,
            items_key=RESPONSE_ITEMS_KEY["audit_log"],
            page_size=effective_page_size,
            max_items=limit,
        )
        return gcf_dumps({"count": len(items), "entries": items})
    except Exception as exc:
        logger.exception("get_audit_log failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def list_organization_zones(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 200,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List network segmentation zones defined in xDome.

    Args:
        fields: Defaults to zone_name, zone_description, zone_source,
            priority, attributed_devices, exportable_attributed_devices,
            enabled, created_time, last_update, updated_by.
        filter_field / filter_operation / filter_value: Optional filter.
        limit: Maximum TOTAL items returned (default 200).
        offset: Starting offset.
        page_size: Advanced — defaults to ``min(limit, 500)``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_ZONE_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_organization_zones"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_organization_zones"],
            page_size=effective_page_size,
            max_items=limit,
        )
        return gcf_dumps({"count": len(items), "zones": items})
    except Exception as exc:
        logger.exception("list_organization_zones failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)
