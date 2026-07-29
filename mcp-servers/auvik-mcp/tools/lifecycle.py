"""Lifecycle module tools for the Auvik MCP Server (036).

Each tool is an ``async def auvik_xxx(client, *, <params>) -> str`` core
function.  The first positional argument is an ``AuvikClient`` injected by the
server entrypoint (or by tests via httpx.MockTransport).

Convention (shared by all modules):
1. Validate required params → return ``{"error": ...}`` JSON without any HTTP
   call when invalid.
2. Resolve identifier params via ``utils/resolver.py`` → return the resolver's
   error envelope verbatim on failure.
3. Build EXACT query params per the mcp-tools.md contract.
4. Call ``client.get`` (single by id) or ``client.get_all`` (list).
5. Shape results via ``models.responses.*`` and return ``to_json(...)`` — or
   raw JSON when ``raw=True``; list results include pagination meta.
6. Wrap everything in try/except → ``{"error": {"code": "UpstreamError", …}}``.
"""

from __future__ import annotations

import json
from typing import Optional

from models.responses import Configuration, DeviceLifecycle, DeviceWarranty, to_json
from utils.resolver import looks_like_id, resolve_device, resolve_or_error, resolve_tenants


# ---------------------------------------------------------------------------
# Internal helpers (same pattern as inventory.py)
# ---------------------------------------------------------------------------


def _upstream_error(exc: Exception) -> str:
    """Return a JSON UpstreamError envelope."""
    return json.dumps({
        "error": {
            "code": "UpstreamError",
            "message": str(exc),
            "details": None,
        }
    })


def _list_result(page_result: dict, model_cls, raw: bool = False) -> str:
    """Shape a get_all page_result into a tool response string.

    If get_all encountered a mid-pagination error, surfaces it as an "error"
    key alongside any partial items already collected.
    """
    items = page_result.get("items", [])

    if raw:
        result = {
            "items": items,
            "truncated": page_result.get("truncated", False),
            "next_cursor": page_result.get("next_cursor"),
        }
    else:
        models = [model_cls.from_resource(item) for item in items]
        items_dicts = json.loads(to_json(models)) if models else []
        result = {
            "items": items_dicts,
            "truncated": page_result.get("truncated", False),
            "next_cursor": page_result.get("next_cursor"),
        }

    if page_result.get("error"):
        result["error"] = {
            "code": "UpstreamError",
            "message": page_result["error"],
            "details": None,
        }

    return json.dumps(result, default=str)


def _single_result(get_result: dict, model_cls, raw: bool = False) -> str:
    """Shape a single-resource get() result into a tool response string."""
    if not get_result["success"]:
        return json.dumps({
            "error": {
                "code": "UpstreamError",
                "message": get_result["error"],
                "details": None,
            }
        })

    data = get_result["data"]
    resource = data.get("data") if isinstance(data, dict) else data

    if raw:
        return json.dumps(data, default=str)

    if resource is None:
        return json.dumps({
            "error": {"code": "NotFound", "message": "No resource returned.", "details": None}
        })

    model = model_cls.from_resource(resource)
    return to_json(model)


# ---------------------------------------------------------------------------
# auvik_list_device_lifecycle
# ---------------------------------------------------------------------------


async def auvik_list_device_lifecycle(
    client,
    *,
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
    """List device lifecycle information.

    GET /v1/inventory/device/lifecycle (+ /{id} when a single device resolves).
    device → resolves to Auvik ID → single resource fetch at /{id}.
    """
    try:
        base_path = "/v1/inventory/device/lifecycle"

        # 1. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 2. Resolve device → single fetch
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

            result = await client.get(f"{base_path}/{device_id}")
            return _single_result(result, DeviceLifecycle, raw=raw)

        # 3. Build list params
        raw_params: dict = {}
        if sales_availability:
            raw_params["filter[salesAvailability]"] = sales_availability
        if software_maintenance_status:
            raw_params["filter[softwareMaintenanceStatus]"] = software_maintenance_status
        if security_software_maintenance_status:
            raw_params["filter[securitySoftwareMaintenanceStatus]"] = (
                security_software_maintenance_status
            )
        if last_support_status:
            raw_params["filter[lastSupportStatus]"] = last_support_status
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, DeviceLifecycle, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_device_warranty
# ---------------------------------------------------------------------------


async def auvik_list_device_warranty(
    client,
    *,
    device: Optional[str] = None,
    covered_under_warranty: Optional[bool] = None,
    covered_under_service: Optional[bool] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List device warranty information.

    GET /v1/inventory/device/warranty (+ /{id} when a single device resolves).
    device → resolves to Auvik ID → single resource fetch at /{id}.
    """
    try:
        base_path = "/v1/inventory/device/warranty"

        # 1. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 2. Resolve device → single fetch
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

            result = await client.get(f"{base_path}/{device_id}")
            return _single_result(result, DeviceWarranty, raw=raw)

        # 3. Build list params
        raw_params: dict = {}
        if covered_under_warranty is not None:
            raw_params["filter[coveredUnderWarranty]"] = (
                "true" if covered_under_warranty else "false"
            )
        if covered_under_service is not None:
            raw_params["filter[coveredUnderService]"] = (
                "true" if covered_under_service else "false"
            )
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, DeviceWarranty, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_configurations
# ---------------------------------------------------------------------------


async def auvik_list_configurations(
    client,
    *,
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
    """List device configuration backups.

    GET /v1/inventory/configuration (+ /{id} for the backup body).
    config_id → single fetch at /{id} (returns the fuller backup record).
    device → filter[deviceId] (resolved to Auvik ID via resolve_device).
    """
    try:
        base_path = "/v1/inventory/configuration"

        # 1. Single config by ID (returns backup body)
        if config_id is not None:
            result = await client.get(f"{base_path}/{config_id}")
            return _single_result(result, Configuration, raw=raw)

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve device → filter[deviceId]
        raw_params: dict = {}
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)
            raw_params["filter[deviceId]"] = device_id

        # 4. Build list params
        if backup_time_after:
            raw_params["filter[backupTimeAfter]"] = backup_time_after
        if backup_time_before:
            raw_params["filter[backupTimeBefore]"] = backup_time_before
        if is_running is not None:
            raw_params["filter[isRunning]"] = "true" if is_running else "false"
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, Configuration, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)
