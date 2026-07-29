"""Shared helpers and conventions for Halo tool core functions.

Every tool is ``async def halo_xxx(client, *, <params>) -> str`` and follows:
  1. Validate required params -> ``_validation_error(...)`` with NO HTTP call.
  2. Resolve name identifiers via ``utils.resolver`` -> return the resolver's
     error envelope verbatim on failure.
  3. Build query params with ``_build_params(...)`` (drops None).
  4. Call ``client.get`` (single by id) or ``client.get_all`` (list).
  5. Shape via ``models.responses`` + ``_single_result`` / ``_list_result`` -> a
     JSON/TOON string. Pass ``raw=True`` to return the untouched Halo payload.
  6. Errors surface uniformly as ``{"error": {"code","message","details"}}`` with
     codes ``ValidationError | Ambiguous | NotFound | UpstreamError``.
"""

import json
from typing import Any, Optional

from models.responses import to_dict, to_json


def _validation_error(message: str, details: Any = None) -> str:
    return json.dumps(
        {"error": {"code": "ValidationError", "message": message, "details": details}}
    )


def _upstream_error(err: Any) -> str:
    return json.dumps(
        {"error": {"code": "UpstreamError", "message": str(err), "details": None}}
    )


def _not_found(message: str = "No resource returned.") -> str:
    return json.dumps({"error": {"code": "NotFound", "message": message, "details": None}})


def _build_params(**kwargs) -> dict:
    """Return a params dict with all None-valued keys omitted."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _single_result(get_result: dict, model_cls, raw: bool = False, from_kwargs: Optional[dict] = None) -> str:
    """Shape a ``client.get`` result for a single resource into a response string."""
    if not get_result["success"]:
        return _upstream_error(get_result["error"])
    data = get_result["data"]
    if raw:
        return json.dumps(data, default=str)
    if data is None:
        return _not_found()
    # Some Halo single-gets return the object directly; others may return a list.
    if isinstance(data, list):
        models = [model_cls.from_resource(r, **(from_kwargs or {})) for r in data if isinstance(r, dict)]
        return to_json({"items": [to_dict(m) for m in models]})
    return to_json(model_cls.from_resource(data, **(from_kwargs or {})))


def _list_result(page_result: dict, model_cls, raw: bool = False, from_kwargs: Optional[dict] = None) -> str:
    """Shape a ``client.get_all`` page result (items + meta) into a response string."""
    items = page_result.get("items", [])
    if raw:
        shaped: Any = items
    else:
        shaped = [
            to_dict(model_cls.from_resource(it, **(from_kwargs or {})))
            for it in items
            if isinstance(it, dict)
        ]
    out = {"items": shaped, "truncated": page_result.get("truncated", False)}
    if page_result.get("next_page"):
        out["next_page"] = page_result["next_page"]
    if page_result.get("record_count") is not None:
        out["record_count"] = page_result["record_count"]
    if page_result.get("error"):
        out["error"] = {"code": "UpstreamError", "message": page_result["error"], "details": None}
    return to_json(out)
