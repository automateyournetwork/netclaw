"""Ticket (Halo "Faults") read tools + the one gated change-request write.

Read tools address tickets by numeric id (tickets are not name-resolvable) and
filter lists by resolved ticket-type / customer / asset ids.

``halo_create_change_request`` is the ONLY write path in this server. It is
safety-gated: by default (``submit=False``) it assembles and returns the exact
POST body as a preview and performs NO HTTP write. A real POST only happens when
the caller re-invokes with ``submit=True`` after explicit user approval.
"""

import json

from models.responses import Action, Ticket
from tools._common import (
    _build_params,
    _list_result,
    _single_result,
    _upstream_error,
    _validation_error,
)
from utils.resolver import (
    looks_like_id,
    resolve_asset,
    resolve_client,
    resolve_or_error,
    resolve_site,
    resolve_ticket_type,
)


def _to_int(value):
    """Coerce a resolved/numeric id to int, leaving non-numeric values untouched."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _is_blank(value) -> bool:
    """True if *value* is None or a whitespace-only string."""
    return value is None or (isinstance(value, str) and not value.strip())


def _normalize_custom_fields(custom_fields):
    """Normalize custom-field input into ``[{"id"|"name", "value"}, ...]``.

    Accepts either a dict ``{id_or_name: value}`` or a list of
    ``{"id"/"name", "value"}`` objects. A numeric identifier becomes ``{"id":
    <int>}`` (``FieldInfo.id === customfields[].id``); a non-numeric identifier
    becomes ``{"name": <str>}``. Returns None when there is nothing to send.
    """
    if not custom_fields:
        return None

    if isinstance(custom_fields, dict):
        pairs = list(custom_fields.items())
    elif isinstance(custom_fields, list):
        pairs = []
        for item in custom_fields:
            if not isinstance(item, dict):
                continue
            identifier = item.get("id")
            if identifier is None:
                identifier = item.get("name")
            pairs.append((identifier, item.get("value")))
    else:
        return None

    entries = []
    for identifier, value in pairs:
        if identifier is None:
            continue
        if looks_like_id(identifier):
            entries.append({"id": int(identifier), "value": value})
        else:
            entries.append({"name": str(identifier), "value": value})
    return entries or None


async def halo_get_ticket(client, *, ticket, raw=False) -> str:
    """Read a single ticket by numeric id (details + linked objects)."""
    if not looks_like_id(ticket):
        return _validation_error("ticket must be a numeric ticket id.")
    try:
        res = await client.get(
            f"/Tickets/{ticket}",
            _build_params(includedetails="true", includelinkedobjects="true"),
        )
        return _single_result(
            res, Ticket, raw=raw, from_kwargs={"include_details": True}
        )
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)


async def halo_list_tickets(
    client,
    *,
    ticket_type=None,
    customer=None,
    asset_id=None,
    status=None,
    open_only=None,
    search=None,
    raw=False,
) -> str:
    """List tickets, filtered by resolved ticket-type / customer / asset."""
    try:
        requesttype_id = None
        if ticket_type is not None:
            resolution = await resolve_ticket_type(client, ticket_type)
            requesttype_id, err = resolve_or_error(resolution, "ticket type")
            if err:
                return json.dumps(err)

        client_id = None
        if customer is not None:
            resolution = await resolve_client(client, customer)
            client_id, err = resolve_or_error(resolution, "client")
            if err:
                return json.dumps(err)

        params = _build_params(
            requesttype_id=requesttype_id,
            client_id=client_id,
            asset_id=asset_id,
            status=status,
            open_only=open_only,
            search=search,
        )
        page = await client.get_all("/Tickets", params)
        return _list_result(
            page, Ticket, raw=raw, from_kwargs={"include_details": False}
        )
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)


async def halo_get_ticket_actions(client, *, ticket, raw=False) -> str:
    """List a ticket's actions / notes (``/Actions``) by numeric ticket id."""
    if not looks_like_id(ticket):
        return _validation_error("ticket must be a numeric ticket id.")
    try:
        page = await client.get_all("/Actions", _build_params(ticket_id=ticket))
        return _list_result(page, Action, raw=raw)
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)


async def halo_get_asset_tickets(client, *, asset, open_only=None, raw=False) -> str:
    """List tickets attached to an asset (resolved by name or id)."""
    if _is_blank(asset):
        return _validation_error("asset is required.")
    try:
        resolution = await resolve_asset(client, asset)
        asset_id, err = resolve_or_error(resolution, "asset")
        if err:
            return json.dumps(err)

        page = await client.get_all(
            "/Tickets", _build_params(asset_id=asset_id, open_only=open_only)
        )
        return _list_result(
            page, Ticket, raw=raw, from_kwargs={"include_details": False}
        )
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)


async def halo_create_change_request(
    client,
    *,
    summary,
    details,
    ticket_type,
    customer=None,
    site=None,
    user=None,
    asset=None,
    custom_fields=None,
    submit=False,
    raw=False,
) -> str:
    """Create a change-request ticket. GATED: previews unless ``submit=True``.

    With ``submit=False`` (default) this performs NO write — it returns the exact
    array body that *would* be POSTed to ``/api/Tickets`` so a human can review
    it. Only when re-called with ``submit=True`` (after explicit user approval)
    does it actually POST.
    """
    # 1. Required-field validation (no HTTP).
    missing = [
        name
        for name, value in (
            ("summary", summary),
            ("details", details),
            ("ticket_type", ticket_type),
        )
        if _is_blank(value)
    ]
    if missing:
        return _validation_error(
            f"Missing required field(s): {', '.join(missing)}.", details=missing
        )

    try:
        # 2. Resolve identifiers (name -> id). Return the resolver error verbatim.
        resolution = await resolve_ticket_type(client, ticket_type)
        tickettype_id, err = resolve_or_error(resolution, "ticket type")
        if err:
            return json.dumps(err)
        tickettype_id = _to_int(tickettype_id)

        client_id = None
        if customer is not None:
            resolution = await resolve_client(client, customer)
            client_id, err = resolve_or_error(resolution, "client")
            if err:
                return json.dumps(err)
            client_id = _to_int(client_id)

        site_id = None
        if site is not None:
            resolution = await resolve_site(client, site)
            site_id, err = resolve_or_error(resolution, "site")
            if err:
                return json.dumps(err)
            site_id = _to_int(site_id)

        asset_id = None
        if asset is not None:
            resolution = await resolve_asset(client, asset)
            asset_id, err = resolve_or_error(resolution, "asset")
            if err:
                return json.dumps(err)
            asset_id = _to_int(asset_id)

        user_id = None
        if user is not None:
            if not looks_like_id(user):
                return _validation_error("user must be a numeric user id.")
            user_id = _to_int(user)

        # 3. Normalize custom fields.
        customfields = _normalize_custom_fields(custom_fields)

        # 4. Assemble the exact POST body (array with one object; omit empties).
        ticket_obj = {
            "tickettype_id": tickettype_id,
            "summary": summary,
            "details": details,
        }
        if client_id is not None:
            ticket_obj["client_id"] = client_id
        if site_id is not None:
            ticket_obj["site_id"] = site_id
        if user_id is not None:
            ticket_obj["user_id"] = user_id
        if asset_id is not None:
            ticket_obj["assets"] = [{"id": asset_id}]
        if customfields:
            ticket_obj["customfields"] = customfields
        body = [ticket_obj]

        # 5. Preview path (DEFAULT): no POST.
        if not submit:
            return json.dumps(
                {
                    "preview": True,
                    "would_post": "/api/Tickets",
                    "body": body,
                    "note": (
                        "Change request NOT submitted. Review the body, then "
                        "re-call with submit=true after explicit user approval."
                    ),
                },
                default=str,
            )

        # 6. Submit path: the one real write.
        res = await client.post("/Tickets", body)
        if not res["success"]:
            return _upstream_error(res["error"])
        data = res["data"]
        if raw:
            return json.dumps({"created": True, "ticket": data}, default=str)
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        return json.dumps({"created": True, "ticket": data}, default=str)
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)
