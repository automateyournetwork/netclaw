"""Performance module tools for the Auvik MCP Server (036).

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

Time params: ``from_time`` / ``thru_time`` accept both ISO-8601 strings and
relative shorthand (e.g. ``-1h``, ``-30m``, ``-7d``), resolved via
``_resolve_time()``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from models.responses import (
    Statistic,
    SnmpPollerSetting,
    SnmpPollerHistory,
    to_json,
)
from utils.constants import (
    COMPONENT_STAT_IDS,
    COMPONENT_TYPES,
    DEVICE_AVAILABILITY_STAT_IDS,
    DEVICE_STAT_IDS,
    INTERFACE_STAT_IDS,
    INTERVALS,
    OID_STAT_IDS,
    SERVICE_STAT_IDS,
)
from utils.resolver import looks_like_id, resolve_device, resolve_or_error, resolve_tenants


# ---------------------------------------------------------------------------
# Internal helpers (shared with inventory.py style)
# ---------------------------------------------------------------------------


def _validation_error(message: str, details=None) -> str:
    """Return a JSON ValidationError envelope (no HTTP call)."""
    return json.dumps({
        "error": {
            "code": "ValidationError",
            "message": message,
            "details": details,
        }
    })


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
        return json.dumps({"error": {"code": "NotFound", "message": "No resource returned.", "details": None}})

    model = model_cls.from_resource(resource)
    return to_json(model)


def _build_params(**kwargs) -> dict:
    """Build a params dict, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------

_RELATIVE_RE = re.compile(r"^-(\d+)([mhd])$")


def _resolve_time(value: str) -> str:
    """Resolve a time value to an ISO-8601 UTC string when relative.

    If *value* matches ``^-\\d+[mhd]$`` (e.g. ``-1h``, ``-30m``, ``-7d``),
    convert to an ISO-8601 UTC timestamp ending in ``Z`` using
    ``datetime.now(timezone.utc)`` minus the delta.

    Otherwise return *value* unchanged (caller passed an ISO-8601 string or
    an opaque value).
    """
    m = _RELATIVE_RE.match(value)
    if not m:
        return value

    amount = int(m.group(1))
    unit = m.group(2)

    if unit == "m":
        delta = timedelta(minutes=amount)
    elif unit == "h":
        delta = timedelta(hours=amount)
    else:  # "d"
        delta = timedelta(days=amount)

    dt = datetime.now(timezone.utc) - delta
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# auvik_get_device_statistics
# ---------------------------------------------------------------------------


async def auvik_get_device_statistics(
    client,
    *,
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
    """Get device statistics.

    GET /v1/stat/device/{statId} | /v1/stat/deviceAvailability/{statId}.

    availability=False (default): stat_id must be in DEVICE_STAT_IDS.
    availability=True: stat_id must be in DEVICE_AVAILABILITY_STAT_IDS;
      omit_undiscovered (bool) is accepted.

    from_time and interval are REQUIRED.
    from_time accepts relative shorthand (e.g. -1h).
    """
    try:
        # 1. Validate stat_id against the correct set
        if availability:
            if stat_id not in DEVICE_AVAILABILITY_STAT_IDS:
                return _validation_error(
                    f"stat_id must be one of {sorted(DEVICE_AVAILABILITY_STAT_IDS)} "
                    f"when availability=True, got {stat_id!r}."
                )
        else:
            if stat_id not in DEVICE_STAT_IDS:
                return _validation_error(
                    f"stat_id must be one of {sorted(DEVICE_STAT_IDS)}, got {stat_id!r}."
                )

        # 2. Validate required time params
        if not from_time:
            return _validation_error(
                "from_time is required for device statistics."
            )
        if not interval:
            return _validation_error(
                "interval is required for device statistics."
            )
        if interval not in INTERVALS:
            return _validation_error(
                f"interval must be one of {sorted(INTERVALS)}, got {interval!r}."
            )

        # 3. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 4. Resolve device identifier
        device_id: Optional[str] = None
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

        # 5. Build path and params
        base = "deviceAvailability" if availability else "device"
        path = f"/v1/stat/{base}/{stat_id}"

        raw_params: dict = {
            "filter[fromTime]": _resolve_time(from_time),
            "filter[interval]": interval,
        }
        if thru_time:
            raw_params["filter[thruTime]"] = _resolve_time(thru_time)
        if device_id:
            raw_params["filter[deviceId]"] = device_id
        if device_type:
            raw_params["filter[deviceType]"] = device_type
        if availability and omit_undiscovered is not None:
            raw_params["filter[omitUndiscovered]"] = "true" if omit_undiscovered else "false"
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        page_result = await client.get_all(path, params=raw_params)
        return _list_result(page_result, Statistic, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_get_interface_statistics
# ---------------------------------------------------------------------------


async def auvik_get_interface_statistics(
    client,
    *,
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
    """Get interface statistics.

    GET /v1/stat/interface/{statId}.

    stat_id must be in INTERFACE_STAT_IDS.
    from_time and interval are REQUIRED.
    """
    try:
        # 1. Validate
        if stat_id not in INTERFACE_STAT_IDS:
            return _validation_error(
                f"stat_id must be one of {sorted(INTERFACE_STAT_IDS)}, got {stat_id!r}."
            )

        if not from_time:
            return _validation_error(
                "from_time is required for interface statistics."
            )
        if not interval:
            return _validation_error(
                "interval is required for interface statistics."
            )
        if interval not in INTERVALS:
            return _validation_error(
                f"interval must be one of {sorted(INTERVALS)}, got {interval!r}."
            )

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve parent_device
        parent_device_id: Optional[str] = None
        if parent_device is not None:
            if looks_like_id(parent_device):
                parent_device_id = parent_device
            else:
                resolution = await resolve_device(client, parent_device, tenants=tenants)
                parent_device_id, err = resolve_or_error(resolution, label="parent_device")
                if err:
                    return json.dumps(err)

        # 4. Build path and params
        path = f"/v1/stat/interface/{stat_id}"

        raw_params: dict = {
            "filter[fromTime]": _resolve_time(from_time),
            "filter[interval]": interval,
        }
        if thru_time:
            raw_params["filter[thruTime]"] = _resolve_time(thru_time)
        if interface:
            raw_params["filter[interfaceId]"] = interface
        if interface_type:
            raw_params["filter[interfaceType]"] = interface_type
        if parent_device_id:
            raw_params["filter[parentDevice]"] = parent_device_id
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        page_result = await client.get_all(path, params=raw_params)
        return _list_result(page_result, Statistic, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_get_service_statistics
# ---------------------------------------------------------------------------


async def auvik_get_service_statistics(
    client,
    *,
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
    """Get service statistics.

    GET /v1/stat/service/{statId}.

    stat_id must be in SERVICE_STAT_IDS.
    from_time and interval are REQUIRED.
    """
    try:
        # 1. Validate
        if stat_id not in SERVICE_STAT_IDS:
            return _validation_error(
                f"stat_id must be one of {sorted(SERVICE_STAT_IDS)}, got {stat_id!r}."
            )

        if not from_time:
            return _validation_error(
                "from_time is required for service statistics."
            )
        if not interval:
            return _validation_error(
                "interval is required for service statistics."
            )
        if interval not in INTERVALS:
            return _validation_error(
                f"interval must be one of {sorted(INTERVALS)}, got {interval!r}."
            )

        # 2. Resolve tenant name → ID early
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Build path and params
        path = f"/v1/stat/service/{stat_id}"

        raw_params: dict = {
            "filter[fromTime]": _resolve_time(from_time),
            "filter[interval]": interval,
        }
        if thru_time:
            raw_params["filter[thruTime]"] = _resolve_time(thru_time)
        if service_id:
            raw_params["filter[serviceId]"] = service_id
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        page_result = await client.get_all(path, params=raw_params)
        return _list_result(page_result, Statistic, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_get_component_statistics
# ---------------------------------------------------------------------------


async def auvik_get_component_statistics(
    client,
    *,
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
    """Get component statistics.

    GET /v1/stat/component/{componentType}/{statId}.

    component_type must be in COMPONENT_TYPES.
    stat_id must be in COMPONENT_STAT_IDS.
    from_time and interval are REQUIRED.
    """
    try:
        # 1. Validate
        if component_type not in COMPONENT_TYPES:
            return _validation_error(
                f"component_type must be one of {sorted(COMPONENT_TYPES)}, "
                f"got {component_type!r}."
            )

        if stat_id not in COMPONENT_STAT_IDS:
            return _validation_error(
                f"stat_id must be one of {sorted(COMPONENT_STAT_IDS)}, got {stat_id!r}."
            )

        if not from_time:
            return _validation_error(
                "from_time is required for component statistics."
            )
        if not interval:
            return _validation_error(
                "interval is required for component statistics."
            )
        if interval not in INTERVALS:
            return _validation_error(
                f"interval must be one of {sorted(INTERVALS)}, got {interval!r}."
            )

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve parent_device
        parent_device_id: Optional[str] = None
        if parent_device is not None:
            if looks_like_id(parent_device):
                parent_device_id = parent_device
            else:
                resolution = await resolve_device(client, parent_device, tenants=tenants)
                parent_device_id, err = resolve_or_error(resolution, label="parent_device")
                if err:
                    return json.dumps(err)

        # 4. Build path and params
        path = f"/v1/stat/component/{component_type}/{stat_id}"

        raw_params: dict = {
            "filter[fromTime]": _resolve_time(from_time),
            "filter[interval]": interval,
        }
        if thru_time:
            raw_params["filter[thruTime]"] = _resolve_time(thru_time)
        if component_id:
            raw_params["filter[componentId]"] = component_id
        if parent_device_id:
            raw_params["filter[parentDevice]"] = parent_device_id
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        page_result = await client.get_all(path, params=raw_params)
        return _list_result(page_result, Statistic, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_get_oid_statistics
# ---------------------------------------------------------------------------


async def auvik_get_oid_statistics(
    client,
    *,
    device: Optional[str] = None,
    device_type: Optional[str] = None,
    oid: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """Get OID statistics (point-in-time; no time window).

    GET /v1/stat/oid/deviceMonitor.

    No from_time or interval — this is a point-in-time OID read.
    device → filter[deviceId] (resolved if not an ID).
    """
    try:
        # 1. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 2. Resolve device identifier
        device_id: Optional[str] = None
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

        # 3. Build params (no time params for OID stats)
        raw_params: dict = {}
        if device_id:
            raw_params["filter[deviceId]"] = device_id
        if device_type:
            raw_params["filter[deviceType]"] = device_type
        if oid:
            raw_params["filter[oid]"] = oid
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all("/v1/stat/oid/deviceMonitor", params=params)
        return _list_result(page_result, Statistic, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_snmp_poller_settings
# ---------------------------------------------------------------------------


async def auvik_list_snmp_poller_settings(
    client,
    *,
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
    """List SNMP poller settings.

    tenants is REQUIRED (ValidationError if missing).

    GET /v1/settings/snmppoller
        | /{snmpPollerSettingId}               (when poller_id set)
        | /{snmpPollerSettingId}/devices       (when poller_id set + with_devices=True).
    """
    try:
        # 1. Validate tenants (REQUIRED)
        if not tenants:
            return _validation_error(
                "tenants is required for auvik_list_snmp_poller_settings "
                "(Auvik API mandates tenants on SNMP poller endpoints)."
            )

        # 1b. Resolve tenant names → IDs early so all downstream calls use IDs
        resolved_tenants, terr = await resolve_tenants(client, tenants)
        if terr:
            return json.dumps(terr)

        # 2. Resolve device identifier
        device_id: Optional[str] = None
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=resolved_tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

        # 3. Determine path
        if poller_id:
            if with_devices:
                path = f"/v1/settings/snmppoller/{poller_id}/devices"
                # /devices returns a list of devices
                raw_params: dict = {"tenants": resolved_tenants}
                if page_first is not None:
                    raw_params["page[first]"] = page_first
                page_result = await client.get_all(path, params=raw_params)
                # Return raw list result (devices, not SnmpPollerSetting)
                items = page_result.get("items", [])
                return json.dumps({
                    "items": items,
                    "truncated": page_result.get("truncated", False),
                    "next_cursor": page_result.get("next_cursor"),
                }, default=str)
            else:
                path = f"/v1/settings/snmppoller/{poller_id}"
                result = await client.get(path, params={"tenants": resolved_tenants})
                return _single_result(result, SnmpPollerSetting, raw=raw)

        # 4. Build list params
        raw_params = {"tenants": resolved_tenants}
        if device_id:
            raw_params["filter[deviceId]"] = device_id
        if use_as:
            raw_params["filter[useAs]"] = use_as
        if type:
            raw_params["filter[type]"] = type
        if device_type:
            raw_params["filter[deviceType]"] = device_type
        if make_model:
            raw_params["filter[makeModel]"] = make_model
        if vendor_name:
            raw_params["filter[vendorName]"] = vendor_name
        if oid:
            raw_params["filter[oid]"] = oid
        if name:
            raw_params["filter[name]"] = name
        if page_first is not None:
            raw_params["page[first]"] = page_first

        page_result = await client.get_all("/v1/settings/snmppoller", params=raw_params)
        return _list_result(page_result, SnmpPollerSetting, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_get_snmp_poller_history
# ---------------------------------------------------------------------------


async def auvik_get_snmp_poller_history(
    client,
    *,
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
    """Get SNMP poller history.

    tenants is REQUIRED.
    from_time is REQUIRED.

    value_type=int  → GET /v1/stat/snmppoller/int  (interval REQUIRED, ∈ INTERVALS)
    value_type=string → GET /v1/stat/snmppoller/string (no interval; compact bool accepted)
    """
    try:
        # 1. Validate tenants (REQUIRED)
        if not tenants:
            return _validation_error(
                "tenants is required for auvik_get_snmp_poller_history "
                "(Auvik API mandates tenants on SNMP poller endpoints)."
            )

        # 2. Validate from_time (REQUIRED)
        if not from_time:
            return _validation_error(
                "from_time is required for auvik_get_snmp_poller_history."
            )

        # 3. value_type-specific validation
        if value_type == "int":
            if not interval:
                return _validation_error(
                    "interval is required when value_type='int'."
                )
            if interval not in INTERVALS:
                return _validation_error(
                    f"interval must be one of {sorted(INTERVALS)}, got {interval!r}."
                )
        # string type: interval not needed (and not sent even if provided)

        # 4. Resolve tenant name → ID early so all downstream calls use the ID
        tenants, terr = await resolve_tenants(client, tenants)
        if terr:
            return json.dumps(terr)

        # 5. Resolve device identifier
        device_id: Optional[str] = None
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

        # 6. Build path and params
        path = f"/v1/stat/snmppoller/{value_type}"

        raw_params: dict = {
            "tenants": tenants,
            "filter[fromTime]": _resolve_time(from_time),
        }
        if thru_time:
            raw_params["filter[thruTime]"] = _resolve_time(thru_time)
        if value_type == "int" and interval:
            raw_params["filter[interval]"] = interval
        if value_type == "string" and compact is not None:
            raw_params["filter[compact]"] = "true" if compact else "false"
        if snmp_poller_setting_id:
            raw_params["filter[snmpPollerSettingId]"] = snmp_poller_setting_id
        if device_id:
            raw_params["filter[deviceId]"] = device_id
        if page_first is not None:
            raw_params["page[first]"] = page_first

        page_result = await client.get_all(path, params=raw_params)
        return _list_result(page_result, SnmpPollerHistory, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)
