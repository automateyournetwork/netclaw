"""Inventory module tools for the Auvik MCP Server (036).

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

from models.responses import (
    Component,
    Device,
    DeviceDetail,
    EntityAudit,
    EntityNote,
    Interface,
    Network,
    Tenant,
    Usage,
    to_json,
)
from utils.resolver import looks_like_id, resolve_device, resolve_network, resolve_or_error, resolve_tenants


# ---------------------------------------------------------------------------
# Internal helpers
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

    When raw=True, return the raw aggregated items list.
    Otherwise, convert each item via model_cls.from_resource and to_json.
    Always includes pagination meta (truncated, next_cursor).
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
        # Build the structure manually so we can include pagination meta
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

    # Some endpoints (e.g. /v1/billing/usage/client on multi-client/MSP accounts)
    # return `data` as a JSON:API collection — a list, one row per tenant. Shape
    # each element instead of treating the whole list as a single resource
    # (which would call list.get() and raise "'list' object has no attribute 'get'").
    if isinstance(resource, list):
        models = [model_cls.from_resource(item) for item in resource]
        items = json.loads(to_json(models)) if models else []
        return json.dumps({"items": items}, default=str)

    model = model_cls.from_resource(resource)
    return to_json(model)


def _build_params(**kwargs) -> dict:
    """Build a params dict, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# auvik_list_devices
# ---------------------------------------------------------------------------

_DEVICE_DETAIL_LEVELS = {"info", "detail", "extended"}


async def auvik_list_devices(
    client,
    *,
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
    """List/inspect discovered devices.

    GET /v1/inventory/device/info | .../detail | .../detail/extended
    (+ /{id} when a single device resolves).

    detail_level=extended REQUIRES device_type (API mandate).
    """
    try:
        # 1. Validate
        if detail_level not in _DEVICE_DETAIL_LEVELS:
            return _validation_error(
                f"detail_level must be one of {sorted(_DEVICE_DETAIL_LEVELS)}, "
                f"got {detail_level!r}."
            )

        if detail_level == "extended" and not device_type:
            return _validation_error(
                "detail_level='extended' requires device_type to be specified "
                "(Auvik API mandates filter[deviceType] on the extended endpoint)."
            )

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve device identifier
        if device is not None:
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device, tenants=tenants)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

            # Single device fetch — use the appropriate base path
            if detail_level == "info":
                path = f"/v1/inventory/device/info/{device_id}"
            elif detail_level == "detail":
                path = f"/v1/inventory/device/detail/{device_id}"
            else:  # extended
                path = f"/v1/inventory/device/detail/extended/{device_id}"

            model_cls = Device if detail_level == "info" else DeviceDetail
            params = _build_params(
                **{"filter[deviceType]": device_type} if device_type else {},
            )
            result = await client.get(path, params=params or None)
            return _single_result(result, model_cls, raw=raw)

        # 4. Build list path and params
        if detail_level == "info":
            path = "/v1/inventory/device/info"
            model_cls = Device
        elif detail_level == "detail":
            path = "/v1/inventory/device/detail"
            model_cls = DeviceDetail
        else:  # extended
            path = "/v1/inventory/device/detail/extended"
            model_cls = DeviceDetail

        # Assemble query params
        raw_params: dict = {}
        if detail_level == "info":
            raw_params["include"] = "deviceDetail"
            if device_type:
                raw_params["filter[deviceType]"] = device_type
            if make_model:
                raw_params["filter[makeModel]"] = make_model
            if vendor_name:
                raw_params["filter[vendorName]"] = vendor_name
            if online_status:
                raw_params["filter[onlineStatus]"] = online_status
            if modified_after:
                raw_params["filter[modifiedAfter]"] = modified_after
            if not_seen_since:
                raw_params["filter[notSeenSince]"] = not_seen_since
            if networks:
                raw_params["filter[networks]"] = networks
            if state_known is not None:
                raw_params["filter[stateKnown]"] = "true" if state_known else "false"
        elif detail_level == "detail":
            if modified_after:
                raw_params["filter[modifiedAfter]"] = modified_after
            if not_seen_since:
                raw_params["filter[notSeenSince]"] = not_seen_since
            if state_known is not None:
                raw_params["filter[stateKnown]"] = "true" if state_known else "false"
        else:  # extended
            raw_params["filter[deviceType]"] = device_type  # already validated non-None
            if modified_after:
                raw_params["filter[modifiedAfter]"] = modified_after
            if not_seen_since:
                raw_params["filter[notSeenSince]"] = not_seen_since
            if state_known is not None:
                raw_params["filter[stateKnown]"] = "true" if state_known else "false"

        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(path, params=params)
        return _list_result(page_result, model_cls, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_networks
# ---------------------------------------------------------------------------

_NETWORK_DETAIL_LEVELS = {"info", "detail"}


async def auvik_list_networks(
    client,
    *,
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
    """List/inspect networks.

    GET /v1/inventory/network/info | .../detail (+ /{id}).
    """
    try:
        # 1. Validate
        if detail_level not in _NETWORK_DETAIL_LEVELS:
            return _validation_error(
                f"detail_level must be one of {sorted(_NETWORK_DETAIL_LEVELS)}, "
                f"got {detail_level!r}."
            )

        base_path = (
            "/v1/inventory/network/info"
            if detail_level == "info"
            else "/v1/inventory/network/detail"
        )

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve network identifier
        if network is not None:
            if looks_like_id(network):
                network_id = network
            else:
                resolution = await resolve_network(client, network, tenants=tenants)
                network_id, err = resolve_or_error(resolution, label="network")
                if err:
                    return json.dumps(err)

            path = f"{base_path}/{network_id}"
            result = await client.get(path)
            return _single_result(result, Network, raw=raw)

        # 4. Build list params
        raw_params: dict = {}
        if network_type:
            raw_params["filter[networkType]"] = network_type
        if scan_status:
            raw_params["filter[scanStatus]"] = scan_status
        if devices:
            raw_params["filter[devices]"] = devices
        if modified_after:
            raw_params["filter[modifiedAfter]"] = modified_after
        if scope and detail_level == "detail":
            raw_params["filter[scope]"] = scope
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, Network, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_interfaces
# ---------------------------------------------------------------------------


async def auvik_list_interfaces(
    client,
    *,
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
    """List interfaces.

    GET /v1/inventory/interface/info (+ /{id}).

    Note: The interface/info endpoint has no server-side name filter.
    The ``interface`` param is accepted only as an Auvik ID (≥6 digits).
    Interface-name resolution would require fetching the full list and
    matching client-side (out of scope for v1 — pass an Auvik ID directly).

    The ``parent_device`` param resolves via resolve_device → filter[parentDevice].
    """
    try:
        base_path = "/v1/inventory/interface/info"

        # Single interface by ID
        if interface is not None:
            if looks_like_id(interface):
                result = await client.get(f"{base_path}/{interface}")
                return _single_result(result, Interface, raw=raw)
            # Non-ID interface identifier: document limitation, treat as filter pass-through
            # (full name resolution out of scope per contract note)
            # Fall through to list with no filter if not an ID — not useful but not wrong
            # Per spec: "accept interface only as an id for now"
            return _validation_error(
                f"interface={interface!r} does not look like an Auvik ID. "
                "Interface-name resolution is not supported; pass the Auvik numeric ID."
            )

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve parent_device
        raw_params: dict = {}
        if parent_device is not None:
            if looks_like_id(parent_device):
                parent_device_id = parent_device
            else:
                resolution = await resolve_device(client, parent_device, tenants=tenants)
                parent_device_id, err = resolve_or_error(resolution, label="parent_device")
                if err:
                    return json.dumps(err)
            raw_params["filter[parentDevice]"] = parent_device_id

        # 4. Build params
        if interface_type:
            raw_params["filter[interfaceType]"] = interface_type
        if admin_status:
            raw_params["filter[adminStatus]"] = admin_status
        if operational_status:
            raw_params["filter[operationalStatus]"] = operational_status
        if modified_after:
            raw_params["filter[modifiedAfter]"] = modified_after
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, Interface, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_components
# ---------------------------------------------------------------------------


async def auvik_list_components(
    client,
    *,
    component: Optional[str] = None,
    device: Optional[str] = None,
    current_status: Optional[str] = None,
    modified_after: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List components.

    GET /v1/inventory/component/info (+ /{id}).
    device → filter[deviceId] (resolved to Auvik ID via resolve_device).
    """
    try:
        base_path = "/v1/inventory/component/info"

        # Single component by ID — or ValidationError for non-ID names
        if component is not None:
            if looks_like_id(component):
                result = await client.get(f"{base_path}/{component}")
                return _single_result(result, Component, raw=raw)
            return _validation_error(
                f"component={component!r} does not look like an Auvik ID. "
                "Component name resolution is not supported; pass the Auvik numeric ID."
            )

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve device
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

        # 4. Build params
        if current_status:
            raw_params["filter[currentStatus]"] = current_status
        if modified_after:
            raw_params["filter[modifiedAfter]"] = modified_after
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, Component, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_tenants
# ---------------------------------------------------------------------------


async def auvik_list_tenants(
    client,
    *,
    detail: bool = False,
    tenant_domain_prefix: Optional[str] = None,
    available_tenants: Optional[bool] = None,
    raw: bool = False,
) -> str:
    """List tenants.

    GET /v1/tenants (no params) | /v1/tenants/detail (when detail=True,
    requires tenant_domain_prefix).

    Note: /v1/tenants accepts NO query params (no filter, no paging).
    """
    try:
        if detail:
            # 1. Validate
            if not tenant_domain_prefix:
                return _validation_error(
                    "tenant_domain_prefix is required when detail=True "
                    "(Auvik API mandates tenantDomainPrefix on /v1/tenants/detail)."
                )

            path = "/v1/tenants/detail"
            raw_params: dict = {"tenantDomainPrefix": tenant_domain_prefix}
            if available_tenants is not None:
                raw_params["availableTenants"] = available_tenants

            page_result = await client.get_all(path, params=raw_params)
            return _list_result(page_result, Tenant, raw=raw)
        else:
            # /v1/tenants accepts no params
            page_result = await client.get_all("/v1/tenants")
            return _list_result(page_result, Tenant, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_entity_notes
# ---------------------------------------------------------------------------


async def auvik_list_entity_notes(
    client,
    *,
    entity: Optional[str] = None,
    entity_type: Optional[str] = None,
    last_modified_by: Optional[str] = None,
    modified_after: Optional[str] = None,
    tenants: Optional[str] = None,
    page_first: Optional[int] = None,
    fetch_all: bool = True,
    raw: bool = False,
) -> str:
    """List entity notes.

    GET /v1/inventory/entity/note (+ /{id}).

    entity param:
    - If it looks like an Auvik ID (≥6 digits) → GET /entity/note/{id} directly.
    - Otherwise → attempt to resolve as a device name → use resolved ID as
      filter[entityId].  If resolution fails, pass as-is to filter[entityId]
      (allows passing an entity ID string that doesn't match the digit heuristic).
    """
    try:
        base_path = "/v1/inventory/entity/note"

        # Single note by ID
        if entity is not None and looks_like_id(entity):
            result = await client.get(f"{base_path}/{entity}")
            return _single_result(result, EntityNote, raw=raw)

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve entity identifier for filter
        raw_params: dict = {}
        if entity is not None:
            # Try device resolution first (most common entity type)
            resolution = await resolve_device(client, entity, tenants=tenants)
            entity_id, err = resolve_or_error(resolution, label="entity")
            if err:
                # Could not resolve as device — pass the value as-is (might be another entity type)
                raw_params["filter[entityId]"] = entity
            else:
                raw_params["filter[entityId]"] = entity_id

        # 4. Build params
        if entity_type:
            raw_params["filter[entityType]"] = entity_type
        if last_modified_by:
            raw_params["filter[lastModifiedBy]"] = last_modified_by
        if modified_after:
            raw_params["filter[modifiedAfter]"] = modified_after
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, EntityNote, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_list_entity_audits
# ---------------------------------------------------------------------------


async def auvik_list_entity_audits(
    client,
    *,
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
    """List entity audit entries.

    GET /v1/inventory/entity/audit (+ /{id}).
    """
    try:
        base_path = "/v1/inventory/entity/audit"

        # Single audit by ID
        if audit_id is not None:
            result = await client.get(f"{base_path}/{audit_id}")
            return _single_result(result, EntityAudit, raw=raw)

        # Resolve tenant name → ID early
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # Build list params
        raw_params: dict = {}
        if user:
            raw_params["filter[user]"] = user
        if category:
            raw_params["filter[category]"] = category
        if status:
            raw_params["filter[status]"] = status
        if modified_after:
            raw_params["filter[modifiedAfter]"] = modified_after
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, EntityAudit, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_get_usage
# ---------------------------------------------------------------------------

_USAGE_SCOPES = {"client", "device"}


async def auvik_get_usage(
    client,
    *,
    scope: str = "client",
    device: Optional[str] = None,
    from_date: Optional[str] = None,
    thru_date: Optional[str] = None,
    tenants: Optional[str] = None,
    raw: bool = False,
) -> str:
    """Get usage/billing data.

    GET /v1/billing/usage/client | /v1/billing/usage/device/{id}.
    from_date and thru_date are REQUIRED for both scopes.
    scope=device additionally requires the device param.
    """
    try:
        # 1. Validate scope
        if scope not in _USAGE_SCOPES:
            return _validation_error(
                f"scope must be one of {sorted(_USAGE_SCOPES)}, got {scope!r}."
            )

        # 2. Validate required dates
        missing = []
        if not from_date:
            missing.append("from_date")
        if not thru_date:
            missing.append("thru_date")
        if missing:
            return _validation_error(
                f"Required parameter(s) missing: {', '.join(missing)}. "
                "Both from_date and thru_date are required."
            )

        # 3. Resolve tenant name → ID early (client scope only; device scope has no tenants param)
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 4. Build date params (shared)
        date_params: dict = {
            "filter[fromDate]": from_date,
            "filter[thruDate]": thru_date,
        }

        if scope == "client":
            if tenants:
                date_params["tenants"] = tenants
            result = await client.get("/v1/billing/usage/client", params=date_params)
            return _single_result(result, Usage, raw=raw)

        else:  # scope == "device"
            # device is required for device scope
            if not device:
                return _validation_error(
                    "device is required when scope='device'."
                )

            # Resolve device
            if looks_like_id(device):
                device_id = device
            else:
                resolution = await resolve_device(client, device)
                device_id, err = resolve_or_error(resolution, label="device")
                if err:
                    return json.dumps(err)

            # Note: /v1/billing/usage/device/{id} accepts no tenants param
            result = await client.get(f"/v1/billing/usage/device/{device_id}", params=date_params)
            return _single_result(result, Usage, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)


# ---------------------------------------------------------------------------
# auvik_verify_credentials
# ---------------------------------------------------------------------------


async def auvik_verify_credentials(client) -> str:
    """Verify Auvik API credentials.

    GET /v1/authentication/verify. No params. Returns auth/health status.
    """
    try:
        result = await client.get("/v1/authentication/verify")
        if not result["success"]:
            return json.dumps({
                "error": {
                    "code": "AuthError",
                    "message": result["error"],
                    "details": None,
                }
            })
        # Auvik returns an empty 200 body on success; treat that as verified.
        return json.dumps({"verified": True, "data": result["data"]}, default=str)

    except Exception as exc:
        return _upstream_error(exc)
