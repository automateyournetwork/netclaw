"""Read-only asset (Device) tools for the Halo MCP server (069).

Halo calls assets "Devices" but exposes them at ``/api/Asset``. These core
functions follow the shared convention (see ``tools/_common.py``):

    validate -> resolve names -> build params -> call client -> shape result,
    with the HTTP call wrapped in try/except -> ``_upstream_error``.

The Halo "Client" entity (customer) collides with the ``client`` positional
(the ``HaloClient``), so the customer-scoping parameter is named ``customer``.
"""

import json

from models.responses import Asset
from tools._common import (
    _build_params,
    _list_result,
    _single_result,
    _upstream_error,
    _validation_error,
)
from utils.resolver import resolve_asset, resolve_client, resolve_or_error


async def halo_get_asset(client, *, asset, raw=False) -> str:
    """Get a single asset (Device) by id or name, with detail fields included."""
    if asset is None or (isinstance(asset, str) and not asset.strip()):
        return _validation_error("asset is required (an asset id or name).")

    resolution = await resolve_asset(client, asset)
    asset_id, err = resolve_or_error(resolution, "asset")
    if err:
        return json.dumps(err)

    try:
        res = await client.get(f"/Asset/{asset_id}", _build_params(includedetails="true"))
        return _single_result(res, Asset, raw=raw, from_kwargs={"include_fields": True})
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)


async def halo_list_assets(client, *, customer=None, assettype_id=None, search=None, raw=False) -> str:
    """List assets (Devices), optionally scoped by customer, asset type, or search."""
    client_id = None
    if customer is not None:
        resolution = await resolve_client(client, customer)
        client_id, err = resolve_or_error(resolution, "client")
        if err:
            return json.dumps(err)

    try:
        page = await client.get_all(
            "/Asset",
            _build_params(client_id=client_id, assettype_id=assettype_id, search=search),
        )
        return _list_result(page, Asset, raw=raw)
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)


async def halo_get_asset_relationships(client, *, asset, raw=False) -> str:
    """Return an asset's CMDB hierarchy / relationship view (children, related ticket)."""
    if asset is None or (isinstance(asset, str) and not asset.strip()):
        return _validation_error("asset is required (an asset id or name).")

    resolution = await resolve_asset(client, asset)
    asset_id, err = resolve_or_error(resolution, "asset")
    if err:
        return json.dumps(err)

    try:
        res = await client.get(
            f"/Asset/{asset_id}",
            _build_params(includedetails="true", includehierarchy="true"),
        )
        if not res["success"]:
            return _upstream_error(res["error"])
        data = res["data"]
        if raw:
            return json.dumps(data, default=str)
        return json.dumps(
            {
                "asset_id": asset_id,
                "hierarchy": data.get("hierarchy") if isinstance(data, dict) else None,
                "related_ticket_id": (data or {}).get("related_ticket_id"),
                "child_count": (data or {}).get("child_count"),
            },
            default=str,
        )
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)
