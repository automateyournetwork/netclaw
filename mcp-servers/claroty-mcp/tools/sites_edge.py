"""Site and edge sensor read-only tools for the Claroty xDome MCP server.

Edge sensor lifecycle (add/update/delete locations, generate/rotate API
keys) is OUT OF SCOPE for v1 — see specs/035-claroty-mcp/research.md.

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/sites/get                            -> list_sites / get_site
  POST /api/v1/edge-management/locations/get        -> list_edge_locations
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from models.responses import from_xdome_site, to_dict
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import (
    DEFAULT_SITE_FIELDS,
    ENDPOINTS,
    RESPONSE_ITEMS_KEY,
    make_filter,
)

logger = logging.getLogger("claroty-mcp.sites")


async def list_sites(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 100,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List Claroty xDome sites.

    Args:
        fields: Defaults to id, name, location, country_code, description,
            devices_count, site_group_id, site_group_name.
        filter_field / filter_operation / filter_value: Optional filter.
        limit: Maximum TOTAL items returned (default 100).
        offset: Starting offset into the result set.
        page_size: Advanced — internal batch size. Defaults to
            ``min(limit, 500)``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_SITE_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_sites"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_sites"],
            page_size=effective_page_size,
            max_items=limit,
        )
        sites = [to_dict(from_xdome_site(item)) for item in items]
        return gcf_dumps({"count": len(sites), "sites": sites})
    except Exception as exc:
        logger.exception("list_sites failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def get_site(site_id, fields: Optional[list[str]] = None) -> str:
    """Fetch a single site by id (filters the list endpoint).

    Args:
        site_id: xDome site id (int or str).
        fields: Optional field projection.
    """
    if site_id is None or site_id == "":
        return json.dumps({"error": "site_id is required"}, indent=2)
    body = {
        "fields": list(fields or DEFAULT_SITE_FIELDS),
        "offset": 0,
        "limit": 1,
        "filter_by": make_filter("id", "in", [site_id]),
    }
    try:
        resp = await client.post(ENDPOINTS["list_sites"], body)
        items = client._extract_items(
            resp, ENDPOINTS["list_sites"], RESPONSE_ITEMS_KEY["list_sites"]
        )
        if not items:
            return json.dumps(
                {"error": "site not found", "site_id": site_id}, indent=2
            )
        return gcf_dumps({"site": to_dict(from_xdome_site(items[0])), "raw": items[0]})
    except Exception as exc:
        logger.exception("get_site failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def list_edge_locations() -> str:
    """List edge sensor / collector locations (read-only).

    xDome's edge-management/locations/get takes no request body.

    Returns:
        GCF-serialised list of edge locations.
    """
    try:
        raw = await client.post(ENDPOINTS["list_edge_locations"], {})
        return gcf_dumps({"edge_locations": raw})
    except Exception as exc:
        logger.exception("list_edge_locations failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)
