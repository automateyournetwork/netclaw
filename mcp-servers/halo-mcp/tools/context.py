"""Read-only account-context tools for the Halo MCP server (069).

Covers the entities that give a ticket or asset its business context: clients
(customers), sites, users, and contracts. Each core function follows the shared
convention (see ``tools/_common.py``).

The Halo "Client" entity (customer) collides with the ``client`` positional
(the ``HaloClient``), so the customer-scoping parameter is named ``customer``.
"""

import json

from models.responses import Client, Contract, Site, User
from tools._common import (
    _build_params,
    _list_result,
    _upstream_error,
)
from utils.resolver import resolve_client, resolve_or_error


async def halo_list_clients(client, *, search=None, raw=False) -> str:
    """List clients (customers), optionally filtered by a search term."""
    try:
        page = await client.get_all("/Client", _build_params(search=search))
        return _list_result(page, Client, raw=raw)
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)


async def halo_list_sites(client, *, customer=None, search=None, raw=False) -> str:
    """List sites, optionally scoped to a customer and/or filtered by search."""
    client_id = None
    if customer is not None:
        resolution = await resolve_client(client, customer)
        client_id, err = resolve_or_error(resolution, "client")
        if err:
            return json.dumps(err)

    try:
        page = await client.get_all("/Site", _build_params(client_id=client_id, search=search))
        return _list_result(page, Site, raw=raw)
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)


async def halo_list_users(client, *, customer=None, site_id=None, search=None, raw=False) -> str:
    """List users, optionally scoped to a customer/site and/or filtered by search."""
    client_id = None
    if customer is not None:
        resolution = await resolve_client(client, customer)
        client_id, err = resolve_or_error(resolution, "client")
        if err:
            return json.dumps(err)

    try:
        page = await client.get_all(
            "/Users",
            _build_params(client_id=client_id, site_id=site_id, search=search),
        )
        return _list_result(page, User, raw=raw)
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)


async def halo_list_contracts(client, *, customer=None, raw=False) -> str:
    """List client contracts, optionally scoped to a customer."""
    client_id = None
    if customer is not None:
        resolution = await resolve_client(client, customer)
        client_id, err = resolve_or_error(resolution, "client")
        if err:
            return json.dumps(err)

    try:
        page = await client.get_all("/ClientContract", _build_params(client_id=client_id))
        return _list_result(page, Contract, raw=raw)
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)
