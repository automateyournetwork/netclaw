"""Alerts module tools for the Auvik MCP Server (036).

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

SPEC GOTCHA — detected_time_after / detected_time_before:
  The Auvik OpenAPI spec mislabels these as boolean. The actual API expects
  ISO-8601 datetime *strings* (e.g. ``"2026-06-01T00:00:00Z"``) sent as
  ``filter[detectedTimeAfter]`` / ``filter[detectedTimeBefore]``.
  We pass through the string value as-is (no conversion to bool).
"""

from __future__ import annotations

import json
from typing import Optional

from models.responses import Alert, to_json
from utils.resolver import looks_like_id, resolve_device, resolve_or_error, resolve_tenants


# ---------------------------------------------------------------------------
# Internal helpers (same pattern as inventory.py)
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
        return json.dumps({
            "error": {"code": "NotFound", "message": "No resource returned.", "details": None}
        })

    model = model_cls.from_resource(resource)
    return to_json(model)


# ---------------------------------------------------------------------------
# auvik_list_alerts
# ---------------------------------------------------------------------------


async def auvik_list_alerts(
    client,
    *,
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
    """List/inspect alert history.

    GET /v1/alert/history/info (+ /{id} when alert_id given).

    SPEC GOTCHA: detected_time_after / detected_time_before are ISO-8601
    *strings* sent as filter values — the Auvik OpenAPI spec mislabels them
    as booleans, but the real API expects the datetime string value.
    """
    try:
        base_path = "/v1/alert/history/info"

        # 1. Single alert by ID
        if alert_id is not None:
            result = await client.get(f"{base_path}/{alert_id}")
            return _single_result(result, Alert, raw=raw)

        # 2. Resolve tenant name → ID early so all downstream calls use the ID
        if tenants:
            tenants, terr = await resolve_tenants(client, tenants)
            if terr:
                return json.dumps(terr)

        # 3. Resolve entity identifier
        raw_params: dict = {}
        if entity is not None:
            if looks_like_id(entity):
                raw_params["filter[entityId]"] = entity
            else:
                resolution = await resolve_device(client, entity, tenants=tenants)
                entity_id, err = resolve_or_error(resolution, label="entity")
                if err:
                    return json.dumps(err)
                raw_params["filter[entityId]"] = entity_id

        # 4. Build list params
        if severity:
            raw_params["filter[severity]"] = severity
        if status:
            raw_params["filter[status]"] = status
        if dismissed is not None:
            raw_params["filter[dismissed]"] = "true" if dismissed else "false"
        if dispatched is not None:
            raw_params["filter[dispatched]"] = "true" if dispatched else "false"
        # CRITICAL: pass timestamp string as-is — NOT a boolean
        if detected_time_after is not None:
            raw_params["filter[detectedTimeAfter]"] = detected_time_after
        if detected_time_before is not None:
            raw_params["filter[detectedTimeBefore]"] = detected_time_before
        if alert_definition_id:
            raw_params["filter[alertDefinitionId]"] = alert_definition_id
        if alert_specification_id:
            raw_params["filter[alertSpecificationId]"] = alert_specification_id
        if tenants:
            raw_params["tenants"] = tenants
        if page_first is not None:
            raw_params["page[first]"] = page_first

        params = raw_params if raw_params else None
        page_result = await client.get_all(base_path, params=params)
        return _list_result(page_result, Alert, raw=raw)

    except Exception as exc:
        return _upstream_error(exc)
