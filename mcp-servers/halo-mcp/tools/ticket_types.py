"""Ticket-type (Halo "Request Type") tools.

``halo_get_ticket_type`` is the authoritative field-schema read: with
``includedetails=true`` Halo returns the type's ``fields[]`` placement list,
which ``TicketType.from_resource(..., include_fields=True)`` shapes into the
per-type field schema (mandatory flags, visibility, and each field's
``FieldInfo`` definition, including dropdown options).
"""

import json

from models.responses import TicketType
from tools._common import (
    _build_params,
    _list_result,
    _single_result,
    _upstream_error,
    _validation_error,
)
from utils.resolver import resolve_client, resolve_or_error, resolve_ticket_type


async def halo_list_ticket_types(
    client,
    *,
    can_create_only=None,
    customer=None,
    showcounts=None,
    raw=False,
) -> str:
    """List ticket types (``/TicketType``), optionally scoped to a customer."""
    try:
        customer_id = None
        if customer is not None:
            resolution = await resolve_client(client, customer)
            customer_id, err = resolve_or_error(resolution, "client")
            if err:
                return json.dumps(err)

        params = _build_params(
            can_create_only=can_create_only,
            client_id=customer_id,
            showcounts=showcounts,
        )
        page = await client.get_all("/TicketType", params)
        return _list_result(page, TicketType, raw=raw)
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)


async def halo_get_ticket_type(client, *, ticket_type, raw=False) -> str:
    """Read a ticket type with its full field schema (authoritative)."""
    if ticket_type is None or (isinstance(ticket_type, str) and not ticket_type.strip()):
        return _validation_error("ticket_type is required.")
    try:
        resolution = await resolve_ticket_type(client, ticket_type)
        tt_id, err = resolve_or_error(resolution, "ticket type")
        if err:
            return json.dumps(err)

        res = await client.get(
            f"/TicketType/{tt_id}", _build_params(includedetails="true")
        )
        return _single_result(
            res, TicketType, raw=raw, from_kwargs={"include_fields": True}
        )
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)
