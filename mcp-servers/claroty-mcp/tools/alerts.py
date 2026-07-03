"""Alert tools for the Claroty xDome MCP server.

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/alerts/                          -> list_alerts
  POST /api/v1/alerts/{alert_id}/devices        -> get_alert_with_devices (composite)
  POST /api/v1/device-alert-status/set          -> acknowledge_alert (write)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from models.responses import from_xdome_alert, to_dict
from utils.itsm_gate import validate_change_request
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import (
    DEFAULT_ALERT_FIELDS,
    DEFAULT_DEVICE_FIELDS,
    ENDPOINTS,
    RESPONSE_ITEMS_KEY,
    make_filter,
)

logger = logging.getLogger("claroty-mcp.alerts")


async def list_alerts(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 100,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List Claroty xDome security alerts.

    Args:
        fields: Alert fields to return. Defaults to a sensible set
            (id, alert_name, alert_type_name, alert_class, category,
            detected_time, updated_time, devices_count, status, description).
        filter_field: xDome alert field to filter on, e.g. ``status``,
            ``category``, ``alert_class``, ``alert_name``.
        filter_operation: ``in``, ``not_in``, ``contains``, etc.
        filter_value: Value the operation expects.

            NOTE on the ``status`` field: xDome READ responses return
            TitleCase (``"Unresolved"`` / ``"Resolved"``) while the WRITE
            endpoint accepts lowercase per ``PublicAlertStatus``. When
            filtering reads, pass the TitleCase form xDome returns
            (e.g. ``filter_value=["Unresolved"]``).
        limit: Maximum TOTAL items returned (default 100). You will
            never get more than ``limit`` items — the wrapper paginates
            internally if needed.
        offset: Starting offset into the result set.
        page_size: Advanced — internal batch size. Defaults to
            ``min(limit, 500)``.

    Returns:
        GCF-serialised ``{"count": N, "alerts": [...]}``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_ALERT_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_alerts"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_alerts"],
            page_size=effective_page_size,
            max_items=limit,
        )
        alerts = [to_dict(from_xdome_alert(item)) for item in items]
        return gcf_dumps({"count": len(alerts), "alerts": alerts})
    except Exception as exc:
        logger.exception("list_alerts failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def get_alert_with_devices(
    alert_id,
    device_limit: int = 200,
    device_fields: Optional[list[str]] = None,
) -> str:
    """Fetch an alert and the devices it affects (composite of two xDome calls).

    Args:
        alert_id: xDome alert id (xDome IDs are typically integers; either
            int or str is accepted).
        device_limit: Max affected devices to return.
        device_fields: Optional projection for the device list (default:
            sensible Device field set).

    Returns:
        GCF-serialised ``{"alert": {...}, "devices": ...}``.
    """
    if alert_id is None or alert_id == "":
        return json.dumps({"error": "alert_id is required"}, indent=2)

    try:
        # 1) Alert metadata via filter on /alerts/.
        alert_body = {
            "fields": DEFAULT_ALERT_FIELDS,
            "offset": 0,
            "limit": 1,
            "filter_by": make_filter("id", "in", [alert_id]),
        }
        alert_resp = await client.post(ENDPOINTS["list_alerts"], alert_body)
        items = client._extract_items(
            alert_resp, ENDPOINTS["list_alerts"], RESPONSE_ITEMS_KEY["list_alerts"]
        )
        alert = to_dict(from_xdome_alert(items[0])) if items else None

        # 2) Affected devices via /alerts/{alert_id}/devices.
        path = ENDPOINTS["alert_devices"].replace("{alert_id}", str(alert_id))
        device_body = {
            "fields": list(device_fields or DEFAULT_DEVICE_FIELDS),
            "offset": 0,
            "limit": device_limit,
        }
        devices_resp = await client.post(path, device_body)
        return gcf_dumps({"alert": alert, "devices": devices_resp})
    except Exception as exc:
        logger.exception("get_alert_with_devices failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


_ALERT_STATUS_VALUES = ("resolved", "unresolved")


async def acknowledge_alert(
    cr_number: str,
    status: str,
    alert_ids: Optional[list] = None,
    alert_id=None,
    device_filter_field: Optional[str] = None,
    device_filter_operation: Optional[str] = None,
    device_filter_value=None,
) -> str:
    """Set the resolution status of one or more alerts (ITSM-gated write).

    Mapped to xDome's POST /api/v1/device-alert-status/set, which takes:
      - ``alerts``: ``TargetAlertIds`` shape — ``{"alert_ids": [...]}``
        (NOT a filter spec — this endpoint accepts alert ids directly).
      - ``devices``: optional ``DeviceFilterBy`` shape —
        ``{"filter_by": {...}}`` — to scope the status change to a subset
        of affected devices.
      - ``status``: ``PublicAlertStatus`` enum — **only ``"resolved"``
        or ``"unresolved"`` are valid** (lowercase).

    CASE-MISMATCH HEADS UP: xDome read endpoints (``list_alerts``)
    return ``"Resolved"`` / ``"Unresolved"`` (TitleCase) but the write
    endpoint above accepts lowercase. We normalise the input you pass
    here — ``"Resolved"``, ``"resolved"``, and ``"RESOLVED"`` are all
    valid and all map to lowercase ``"resolved"`` before the POST.

    Args:
        cr_number: ServiceNow CR (``CHG\\d+``) authorising the change.
        status: ``"resolved"`` / ``"Resolved"`` / ``"unresolved"`` /
            ``"Unresolved"`` (case-insensitive on input).
        alert_ids: List of xDome alert ids (preferred).
        alert_id: Single alert id (alternative to alert_ids).
        device_filter_field / device_filter_operation / device_filter_value:
            Optional device filter to scope the status change.

    Returns:
        ``{"itsm_gate": ..., "applied": bool, "response": ...}``.
    """
    gate = validate_change_request(cr_number)
    if not gate["valid"]:
        return json.dumps({"itsm_gate": gate, "applied": False}, indent=2)
    if not status:
        return json.dumps({"error": "status is required"}, indent=2)

    normalised_status = status.strip().lower()
    if normalised_status not in _ALERT_STATUS_VALUES:
        return json.dumps(
            {
                "error": (
                    f"Invalid status {status!r}. xDome PublicAlertStatus accepts "
                    f"only {list(_ALERT_STATUS_VALUES)} (case-insensitive on input)."
                )
            },
            indent=2,
        )

    ids = list(alert_ids) if alert_ids else []
    if alert_id is not None and alert_id != "":
        ids.append(alert_id)
    if not ids:
        return json.dumps(
            {"error": "Provide alert_ids (list) or alert_id"}, indent=2
        )

    body: dict = {
        # TargetAlertIds shape: {"alert_ids": [...]}, NOT a filter_by.
        "alerts": {"alert_ids": ids},
        "status": normalised_status,
    }
    if device_filter_field and device_filter_operation is not None:
        body["devices"] = {
            "filter_by": make_filter(
                device_filter_field, device_filter_operation, device_filter_value
            )
        }
    try:
        raw = await client.post(ENDPOINTS["set_alert_resolution"], body)
        return gcf_dumps({"itsm_gate": gate, "applied": True, "response": raw})
    except Exception as exc:
        logger.exception("acknowledge_alert failed")
        return json.dumps(
            {"itsm_gate": gate, "applied": False, "error": format_exception(exc)},
            indent=2,
        )
