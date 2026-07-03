"""Device / asset tools for the Claroty xDome MCP server.

xDome endpoints (verified against the OpenAPI spec):
  POST /api/v1/devices/                         -> list_devices (+ get_device_details via filter)
  POST /api/v1/device/communication-map/        -> get_device_communication_map
  POST /api/v1/purdue-level/set                 -> set_device_purdue_level (write)
  POST /api/v1/custom-attributes/set            -> set_device_custom_attribute (write)

Key xDome conventions (different from the typical REST style):
  - Every list endpoint requires a non-empty ``fields`` array in the body.
  - ``filter_by`` uses the SimpleQueryFilter shape: {field, operation, value}
    (not {field_name: {op: value}}).
  - xDome devices use ``asset_id`` / ``uid`` (not ``id``), ``local_name``
    (not ``name``), ``manufacturer`` (not ``vendor``).
  - No GET-by-id endpoint exists; ``get_device_details`` filters the list
    endpoint by asset_id.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from clients.claroty_client import client, format_exception
from models.responses import from_xdome_device, to_dict
from utils.itsm_gate import validate_change_request
from utils.gcf_helper import gcf_dumps
from utils.xdome_constants import (
    DEFAULT_DEVICE_FIELDS,
    ENDPOINTS,
    RESPONSE_ITEMS_KEY,
    make_filter,
)

logger = logging.getLogger("claroty-mcp.devices")


async def list_devices(
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    limit: int = 100,
    offset: int = 0,
    page_size: Optional[int] = None,
) -> str:
    """List OT / IoT / IoMT devices managed by Claroty xDome.

    Args:
        fields: Device fields to return. Defaults to a sensible set
            (asset_id, uid, local_name, ip_list, mac_list, manufacturer,
            model, os_name, os_version, purdue_level, device_category,
            device_type, criticality, risk_score, labels).
        filter_field: Optional xDome device field to filter on, e.g.
            ``purdue_level``, ``device_category``, ``device_type``,
            ``manufacturer``, ``local_name``, ``ip_list``, ``mac_list``,
            ``criticality``, ``labels``.
        filter_operation: ``in``, ``not_in``, ``contains``,
            ``not_contains``, ``in_subnet``, ``not_in_subnet``.
        filter_value: Operation-specific value.
        limit: Maximum TOTAL items returned (default 100). The wrapper
            paginates internally if needed; you'll never get more than
            ``limit`` items back.
        offset: Starting offset into the result set.
        page_size: Advanced — internal batch size for paginated fetches.
            Defaults to ``min(limit, 500)``. Tune this only if you want
            to trade round-trip count against per-request payload size.

    Returns:
        GCF-serialised ``{"count": N, "devices": [...]}``.
    """
    if limit < 1:
        return json.dumps({"error": "limit must be >= 1"}, indent=2)
    effective_page_size = min(page_size if page_size else limit, 500)
    body: dict = {
        "fields": list(fields or DEFAULT_DEVICE_FIELDS),
        "offset": offset,
        "limit": effective_page_size,
    }
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        items = await client.collect(
            ENDPOINTS["list_devices"],
            body,
            items_key=RESPONSE_ITEMS_KEY["list_devices"],
            page_size=effective_page_size,
            max_items=limit,
        )
        devices = [to_dict(from_xdome_device(item)) for item in items]
        return gcf_dumps({"count": len(devices), "devices": devices})
    except Exception as exc:
        logger.exception("list_devices failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def get_device_details(
    asset_id: Optional[str] = None,
    uid: Optional[str] = None,
    fields: Optional[list[str]] = None,
) -> str:
    """Fetch a single device by asset_id or uid.

    xDome has no GET-by-id endpoint; this filters the list endpoint by the
    given identifier and returns the first match.

    Args:
        asset_id: xDome device asset_id. Either this or ``uid`` is required.
        uid: xDome device uid. Either this or ``asset_id`` is required.
        fields: Optional field list; defaults to the full sensible set.

    Returns:
        GCF-serialised ``{"device": {...}, "raw": {...}}`` or
        ``{"error": "not found"}``.
    """
    if not asset_id and not uid:
        return json.dumps(
            {"error": "Either asset_id or uid is required"}, indent=2
        )

    filter_field = "asset_id" if asset_id else "uid"
    filter_value = [asset_id if asset_id else uid]
    body = {
        "fields": list(fields or DEFAULT_DEVICE_FIELDS),
        "offset": 0,
        "limit": 1,
        "filter_by": make_filter(filter_field, "in", filter_value),
    }
    try:
        resp = await client.post(ENDPOINTS["list_devices"], body)
        items = client._extract_items(
            resp, ENDPOINTS["list_devices"], RESPONSE_ITEMS_KEY["list_devices"]
        )
        if not items:
            return json.dumps(
                {"error": "device not found", "lookup": {filter_field: filter_value[0]}},
                indent=2,
            )
        raw = items[0]
        return gcf_dumps({"device": to_dict(from_xdome_device(raw)), "raw": raw})
    except Exception as exc:
        logger.exception("get_device_details failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def get_device_communication_map(
    asset_id: Optional[str] = None,
    uid: Optional[str] = None,
    fields: Optional[list[str]] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
) -> str:
    """Fetch OT / IoT device-to-device communication links for one device.

    xDome scopes communication queries to a single device — provide
    ``asset_id`` OR ``uid``, not both.

    Args:
        asset_id: xDome device asset_id.
        uid: xDome device uid.
        fields: Optional projection (e.g. ``["side_b_ip", "protocol",
            "port", "direction", "data_bytes"]``). xDome supports many
            communication-map fields; see the xDome OpenAPI for the full
            list.
        filter_field / filter_operation / filter_value: Optional filter
            on the communication records. Filterable fields include
            ``comm_type``, ``protocol``, ``ip_protocol``, ``port``,
            ``direction``, ``side_b_asset_id``.

    Returns:
        GCF-serialised communication map data.
    """
    if not asset_id and not uid:
        return json.dumps(
            {"error": "Either asset_id or uid is required"}, indent=2
        )
    if asset_id and uid:
        return json.dumps(
            {"error": "Provide asset_id OR uid, not both"}, indent=2
        )

    body: dict = {}
    if asset_id:
        body["asset_id"] = asset_id
    if uid:
        body["uid"] = uid
    if fields:
        body["fields"] = list(fields)
    if filter_field and filter_operation is not None:
        body["filter_by"] = make_filter(filter_field, filter_operation, filter_value)

    try:
        raw = await client.post(ENDPOINTS["device_communication_map"], body)
        return gcf_dumps({"communication_map": raw})
    except Exception as exc:
        logger.exception("get_device_communication_map failed")
        return json.dumps({"error": format_exception(exc)}, indent=2)


async def set_device_purdue_level(
    purdue_level: str,
    cr_number: str,
    asset_id: Optional[str] = None,
    uid: Optional[str] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
) -> str:
    """Assign a Purdue Model layer to one or more devices (ITSM-gated write).

    The xDome endpoint accepts a filter_by spec describing WHICH devices
    to update — pass ``asset_id`` or ``uid`` for a single device, or
    pass an explicit ``filter_field``/``filter_operation``/``filter_value``
    triple for a batch.

    Args:
        purdue_level: Target layer (e.g. ``"Level 1"``, ``"Level 3.5"``).
        cr_number: ServiceNow CR (``CHG\\d+``) authorising the change.
        asset_id: Single-device target by asset_id.
        uid: Single-device target by uid.
        filter_field / filter_operation / filter_value: Batch target.
    """
    gate = validate_change_request(cr_number)
    if not gate["valid"]:
        return json.dumps({"itsm_gate": gate, "applied": False}, indent=2)
    if not purdue_level:
        return json.dumps({"error": "purdue_level is required"}, indent=2)

    if asset_id:
        flt = make_filter("asset_id", "in", [asset_id])
    elif uid:
        flt = make_filter("uid", "in", [uid])
    elif filter_field and filter_operation is not None:
        flt = make_filter(filter_field, filter_operation, filter_value)
    else:
        return json.dumps(
            {
                "error": "Provide asset_id, uid, or a filter_field/operation/value triple "
                "identifying the target device(s)"
            },
            indent=2,
        )

    body = {"filter_by": flt, "purdue_level": purdue_level}
    try:
        raw = await client.post(ENDPOINTS["set_purdue_level"], body)
        return gcf_dumps({"itsm_gate": gate, "applied": True, "response": raw})
    except Exception as exc:
        logger.exception("set_device_purdue_level failed")
        return json.dumps(
            {"itsm_gate": gate, "applied": False, "error": format_exception(exc)},
            indent=2,
        )


async def set_device_custom_attribute(
    custom_attribute_api_name: str,
    cr_number: str,
    asset_id: Optional[str] = None,
    uid: Optional[str] = None,
    filter_field: Optional[str] = None,
    filter_operation: Optional[str] = None,
    filter_value=None,
    values_to_add: Optional[list[str]] = None,
    values_to_remove: Optional[list[str]] = None,
) -> str:
    """Add or remove custom-attribute values on one or more devices (ITSM-gated).

    Args:
        custom_attribute_api_name: xDome custom attribute api_name (e.g.
            ``"custom_attribute_device_color"``). Custom attributes must
            be pre-created in xDome before they can be set via this API.
        cr_number: ServiceNow CR authorising the change.
        asset_id / uid: Single-device target (mutually exclusive).
        filter_field / filter_operation / filter_value: Batch target.
        values_to_add: Values to add.
        values_to_remove: Values to remove.
    """
    gate = validate_change_request(cr_number)
    if not gate["valid"]:
        return json.dumps({"itsm_gate": gate, "applied": False}, indent=2)
    if not custom_attribute_api_name:
        return json.dumps(
            {"error": "custom_attribute_api_name is required"}, indent=2
        )
    if not values_to_add and not values_to_remove:
        return json.dumps(
            {"error": "Provide at least one of values_to_add or values_to_remove"},
            indent=2,
        )

    if asset_id:
        flt = make_filter("asset_id", "in", [asset_id])
    elif uid:
        flt = make_filter("uid", "in", [uid])
    elif filter_field and filter_operation is not None:
        flt = make_filter(filter_field, filter_operation, filter_value)
    else:
        return json.dumps(
            {
                "error": "Provide asset_id, uid, or a filter_field/operation/value triple "
                "identifying the target device(s)"
            },
            indent=2,
        )

    body: dict = {
        "custom_attribute_api_name": custom_attribute_api_name,
        "target_specification": {"filter_by": flt, "target_type": "device"},
    }
    if values_to_add:
        body["values_to_add"] = list(values_to_add)
    if values_to_remove:
        body["values_to_remove"] = list(values_to_remove)

    try:
        raw = await client.post(ENDPOINTS["set_custom_attribute"], body)
        return gcf_dumps({"itsm_gate": gate, "applied": True, "response": raw})
    except Exception as exc:
        logger.exception("set_device_custom_attribute failed")
        return json.dumps(
            {"itsm_gate": gate, "applied": False, "error": format_exception(exc)},
            indent=2,
        )
