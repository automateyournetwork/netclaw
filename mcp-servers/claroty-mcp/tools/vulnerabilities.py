"""Vulnerability tools for the Claroty xDome MCP server.

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/vulnerabilities/                                     -> list_vulnerabilities
  POST /api/v1/vulnerabilities/{vulnerability_id}/devices            -> get_vulnerable_devices
  POST /api/v1/device_vulnerability_relations/relevance/set          -> set_vulnerability_relevance (write)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from models.responses import from_xdome_vulnerability, to_dict
from utils.itsm_gate import validate_change_request
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import (
    DEFAULT_DEVICE_FIELDS,
    DEFAULT_VULNERABILITY_FIELDS,
    ENDPOINTS,
    RESPONSE_ITEMS_KEY,
    make_filter,
)

logger = logging.getLogger("claroty-mcp.vulns")


async def list_vulnerabilities(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 100,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List Claroty xDome vulnerability findings (CVE-aligned).

    The response includes an ``id`` field on each vulnerability — xDome
    surfaces it implicitly even though it isn't in the default fields
    list. Use that ``id`` (NOT ``name``) when calling
    ``get_vulnerable_devices``.

    Args:
        fields: Vulnerability fields to return. Defaults to a sensible
            set (name, vulnerability_type, cve_ids, cvss_v3_score,
            cvss_v3_vector_string, description, affected_devices_count,
            is_known_exploited, published_date).
        filter_field: xDome vulnerability field to filter on, e.g.
            ``cve_ids``, ``cvss_v3_score``, ``is_known_exploited``,
            ``vulnerability_type``, ``affected_devices_count``.
        filter_operation: SimpleQueryFilter operation. Canonical set:
            ``in``, ``not_in``, ``equals``, ``not_equals``, ``contains``,
            ``not_contains``, ``starts_with``, ``ends_with``, ``is_null``,
            ``is_not_null``, ``greater`` (for numeric fields — NOT
            ``min``/``max``/``gte``/``greater_than``), ``in_subnet``.
        filter_value: Operation-specific value (list for ``in``/``not_in``,
            string for ``contains``, number for ``greater``, etc.).
        limit: Maximum TOTAL items returned (default 100).
        offset: Starting offset into the result set.
        page_size: Advanced — internal batch size. Defaults to
            ``min(limit, 500)``.

    Examples:
        Only vulnerabilities with at least one affected device::

            list_vulnerabilities(
                filter_field="affected_devices_count",
                filter_operation="greater",   # NOT "min" or "gte"
                filter_value=0,
            )

        Only known-exploited::

            list_vulnerabilities(
                filter_field="is_known_exploited",
                filter_operation="equals",
                filter_value=True,
            )

    Returns:
        GCF-serialised ``{"count": N, "vulnerabilities": [...]}``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_VULNERABILITY_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_vulnerabilities"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_vulnerabilities"],
            page_size=effective_page_size,
            max_items=limit,
        )
        vulns = [to_dict(from_xdome_vulnerability(item)) for item in items]
        return gcf_dumps({"count": len(vulns), "vulnerabilities": vulns})
    except Exception as exc:
        logger.exception("list_vulnerabilities failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def get_vulnerable_devices(
    vulnerability_id: str,
    device_fields: Optional[list[str]] = None,
    limit: int = 200,
    offset: int = 0,
) -> str:
    """List devices affected by a single vulnerability (blast radius).

    IMPORTANT: ``vulnerability_id`` must be xDome's internal ``id`` field
    from a Vulnerability response — NOT the human-friendly ``name``.

    Common mistake (will 404):
      - Passing ``"CVE-YYYY-NNNNN"`` (that's the ``name`` field)
      - Passing ``"cisco-sa-sdwan-rpa2-v69WY2SW"`` (also the ``name`` field)
      - Passing a vendor advisory id (still ``name``)

    Right way:
      1. Call ``list_vulnerabilities(...)``.
      2. Read the ``id`` field of the vulnerability you care about
         (it's surfaced by the wrapper even when not explicitly in
         ``fields``).
      3. Pass that ``id`` here.

    Args:
        vulnerability_id: xDome internal vulnerability ``id`` (not name,
            not CVE id, not advisory id).
        device_fields: Optional device-field projection. Defaults to the
            sensible Device field set.
        limit: Max devices to return (the endpoint paginates
            offset/limit internally).
        offset: Starting offset.

    Returns:
        GCF-serialised ``{"vulnerability_id": ..., "devices": {...wrapper...}}``.
    """
    if not vulnerability_id:
        return json.dumps({"error": "vulnerability_id is required"}, indent=2)
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    path = ENDPOINTS["vulnerable_devices"].replace(
        "{vulnerability_id}", str(vulnerability_id)
    )
    body = {
        "fields": list(device_fields or DEFAULT_DEVICE_FIELDS),
        "offset": offset,
        "limit": min(limit, 500),
    }
    try:
        raw = await client.post(path, body)
        return gcf_dumps(
            {"vulnerability_id": vulnerability_id, "devices": raw}
        )
    except Exception as exc:
        logger.exception("get_vulnerable_devices failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


_VULNERABILITY_RELEVANCE_VALUES = (
    "Confirmed",
    "Potentially Relevant",
    "Fixed",
    "Irrelevant",
)


async def set_vulnerability_relevance(
    relevance: str,
    cr_number: str,
    vulnerability_ids: Optional[list[str]] = None,
    vulnerability_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    uid: Optional[str] = None,
    device_filter_field: Optional[str] = None,
    device_filter_operation: Optional[str] = None,
    device_filter_value=None,
) -> str:
    """Set the relevance of one or more vulnerabilities for one or more devices (ITSM-gated).

    xDome's ``VulnerabilityRelevance`` enum is **exactly four values**
    (verified against the OpenAPI spec):
      - ``"Confirmed"`` — this CVE is confirmed exposed on the device.
      - ``"Potentially Relevant"`` — exposure suspected but not confirmed.
      - ``"Fixed"`` — patched / no longer exposed.
      - ``"Irrelevant"`` — does not apply (mitigation, false positive, etc.).

    These values are **case-sensitive** in xDome — we reject unknown
    values up front rather than letting xDome 422.

    Args:
        relevance: One of the four ``VulnerabilityRelevance`` values above.
        cr_number: ServiceNow CR (``CHG\\d+``).
        vulnerability_ids: List of xDome vulnerability ids.
        vulnerability_id: Single vulnerability id.
        asset_id / uid: Single device target.
        device_filter_field / device_filter_operation / device_filter_value:
            Optional batch device target.
    """
    gate = validate_change_request(cr_number)
    if not gate["valid"]:
        return json.dumps({"itsm_gate": gate, "applied": False}, indent=2)
    if not relevance:
        return json.dumps({"error": "relevance is required"}, indent=2)
    if relevance not in _VULNERABILITY_RELEVANCE_VALUES:
        return json.dumps(
            {
                "error": (
                    f"Invalid relevance {relevance!r}. xDome VulnerabilityRelevance "
                    f"accepts only {list(_VULNERABILITY_RELEVANCE_VALUES)} (case-sensitive)."
                )
            },
            indent=2,
        )

    vids = list(vulnerability_ids) if vulnerability_ids else []
    if vulnerability_id:
        vids.append(vulnerability_id)
    if not vids:
        return json.dumps(
            {"error": "Provide vulnerability_ids (list) or vulnerability_id"},
            indent=2,
        )

    body: dict = {
        "vulnerabilities": {"filter_by": make_filter("id", "in", vids)},
        "relevance": relevance,
    }
    if asset_id:
        body["devices"] = {"filter_by": make_filter("asset_id", "in", [asset_id])}
    elif uid:
        body["devices"] = {"filter_by": make_filter("uid", "in", [uid])}
    elif device_filter_field and device_filter_operation is not None:
        body["devices"] = {
            "filter_by": make_filter(
                device_filter_field, device_filter_operation, device_filter_value
            )
        }

    try:
        raw = await client.post(ENDPOINTS["set_vulnerability_relevance"], body)
        return gcf_dumps({"itsm_gate": gate, "applied": True, "response": raw})
    except Exception as exc:
        logger.exception("set_vulnerability_relevance failed")
        return json.dumps(
            {"itsm_gate": gate, "applied": False, "error": format_exception(exc)},
            indent=2,
        )
