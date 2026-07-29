"""Response dataclasses for the Halo MCP server (069).

Halo returns flat JSON objects (not JSON:API ``{id,type,attributes}``), and they
are very large — a ``Faults`` (ticket) object has 100+ fields. Each dataclass here
therefore curates the *relevant* subset for NetClaw's change-request + asset/ticket
context use cases. ``from_resource(obj)`` maps the flat Halo object onto those
fields; ``to_dict()`` drops None; ``to_json()`` serializes via TOON (JSON fallback).

Vocabulary: tickets = "Faults", ticket types = "Request Types", assets = "Devices".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Serialization helpers (shared)
# ---------------------------------------------------------------------------


def to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (or list/dict) to a plain dict, dropping None."""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if v is None:
                continue
            result[k] = to_dict(v)
        return result
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items() if v is not None}
    return obj


def to_json(obj: Any) -> str:
    """Serialize *obj* (dataclass or list of dataclasses) via TOON, JSON fallback."""
    data = [to_dict(item) for item in obj] if isinstance(obj, list) else to_dict(obj)
    try:
        from utils.toon_helper import gcf_dumps  # type: ignore

        return gcf_dumps(data)
    except Exception:
        return json.dumps(data, indent=2, default=str)


def _g(obj: dict, *keys):
    """Return the first present, non-None value among *keys* in *obj*."""
    for k in keys:
        v = obj.get(k)
        if v is not None:
            return v
    return None


# ---------------------------------------------------------------------------
# Custom fields (shared by tickets and assets)
# ---------------------------------------------------------------------------


@dataclass
class CustomField:
    """A custom-field VALUE carried on a ticket/asset (``customfields[]``)."""

    id: Optional[int] = None
    name: Optional[str] = None
    label: Optional[str] = None
    value: Optional[Any] = None
    display: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "CustomField":
        return cls(
            id=obj.get("id"),
            name=obj.get("name"),
            label=obj.get("label"),
            value=_g(obj, "value"),
            display=obj.get("display"),
        )


# ---------------------------------------------------------------------------
# Field definitions (FieldInfo) + ticket-type field placement
# ---------------------------------------------------------------------------


@dataclass
class FieldInfo:
    """A field definition from ``/api/FieldInfo`` (standard or custom)."""

    id: Optional[int] = None
    name: Optional[str] = None
    label: Optional[str] = None
    type: Optional[int] = None
    inputtype: Optional[int] = None
    custom: Optional[int] = None
    usage: Optional[int] = None
    mandatory: Optional[Any] = None
    defaultvalue: Optional[Any] = None
    characterlimit: Optional[int] = None
    regex: Optional[str] = None
    values: Optional[list] = None  # dropdown options [{id, name}]

    @classmethod
    def from_resource(cls, obj: dict) -> "FieldInfo":
        raw_values = obj.get("values") or []
        values = [
            {"id": v.get("id"), "name": _g(v, "name", "value")}
            for v in raw_values
            if isinstance(v, dict)
        ] or None
        return cls(
            id=obj.get("id"),
            name=obj.get("name"),
            label=obj.get("label"),
            type=obj.get("type"),
            inputtype=obj.get("inputtype"),
            custom=obj.get("custom"),
            usage=obj.get("usage"),
            mandatory=obj.get("mandatory"),
            defaultvalue=obj.get("defaultvalue"),
            characterlimit=obj.get("characterlimit"),
            regex=obj.get("regex"),
            values=values,
        )


@dataclass
class TicketTypeField:
    """A field's placement on a ticket type (``RequestTypeField``)."""

    fieldid: Optional[int] = None
    fieldname: Optional[str] = None
    seq: Optional[int] = None
    required_agent: Optional[bool] = None
    required_enduser: Optional[bool] = None
    visible_agent: Optional[bool] = None
    visible_enduser: Optional[bool] = None
    fieldinfo: Optional[FieldInfo] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "TicketTypeField":
        fi = obj.get("fieldinfo")
        return cls(
            fieldid=_g(obj, "fieldid", "fieldid"),
            fieldname=obj.get("fieldname"),
            seq=obj.get("seq"),
            required_agent=obj.get("agentcheckboxmandatory"),
            required_enduser=obj.get("endusercheckboxmandatory"),
            visible_agent=_g(obj, "technew", "techdetail"),
            visible_enduser=_g(obj, "endusernew", "enduserdetail"),
            fieldinfo=FieldInfo.from_resource(fi) if isinstance(fi, dict) else None,
        )


@dataclass
class TicketType:
    """A ticket type (``RequestType``). ``fields`` is populated on the detail read."""

    id: Optional[int] = None
    name: Optional[str] = None
    use: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    ticket_count: Optional[int] = None
    fields: Optional[list] = None  # list[TicketTypeField]

    @classmethod
    def from_resource(cls, obj: dict, include_fields: bool = False) -> "TicketType":
        fields = None
        if include_fields:
            raw = obj.get("fields") or []
            fields = [TicketTypeField.from_resource(f) for f in raw if isinstance(f, dict)] or None
        return cls(
            id=obj.get("id"),
            name=obj.get("name"),
            use=_g(obj, "use", "typename"),
            description=obj.get("description"),
            active=obj.get("active"),
            ticket_count=_g(obj, "count", "ticket_count"),
            fields=fields,
        )


# ---------------------------------------------------------------------------
# Tickets (Faults)
# ---------------------------------------------------------------------------


@dataclass
class Ticket:
    """A ticket (``Faults``) — curated fields for context + change requests."""

    id: Optional[int] = None
    tickettype_id: Optional[int] = None
    summary: Optional[str] = None
    details: Optional[str] = None
    status_id: Optional[int] = None
    status_name: Optional[str] = None
    priority_id: Optional[int] = None
    priority_name: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    site_id: Optional[int] = None
    site_name: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    agent_id: Optional[int] = None
    team: Optional[str] = None
    category_1: Optional[str] = None
    date_occurred: Optional[str] = None
    last_update: Optional[str] = None
    assets: Optional[list] = None
    customfields: Optional[list] = None

    @classmethod
    def from_resource(cls, obj: dict, include_details: bool = True) -> "Ticket":
        assets = None
        raw_assets = obj.get("assets") or []
        if raw_assets:
            assets = [
                {"id": a.get("id"), "name": _g(a, "inventory_number", "key_field", "name")}
                for a in raw_assets
                if isinstance(a, dict)
            ] or None
        customfields = None
        raw_cf = obj.get("customfields") or []
        if raw_cf:
            customfields = [to_dict(CustomField.from_resource(c)) for c in raw_cf if isinstance(c, dict)] or None
        return cls(
            id=obj.get("id"),
            tickettype_id=obj.get("tickettype_id"),
            summary=obj.get("summary"),
            details=obj.get("details") if include_details else None,
            status_id=obj.get("status_id"),
            status_name=_g(obj, "status_name", "status"),
            priority_id=obj.get("priority_id"),
            priority_name=_g(obj, "priority_name", "priority"),
            client_id=obj.get("client_id"),
            client_name=obj.get("client_name"),
            site_id=obj.get("site_id"),
            site_name=obj.get("site_name"),
            user_id=obj.get("user_id"),
            user_name=obj.get("user_name"),
            agent_id=obj.get("agent_id"),
            team=obj.get("team"),
            category_1=obj.get("category_1"),
            date_occurred=_g(obj, "dateoccurred", "datecreated"),
            last_update=_g(obj, "lastactiondate", "last_update"),
            assets=assets,
            customfields=customfields,
        )


@dataclass
class Action:
    """A ticket action / note (``Actions``)."""

    id: Optional[int] = None
    ticket_id: Optional[int] = None
    who: Optional[str] = None
    action_date: Optional[str] = None
    note: Optional[str] = None
    outcome: Optional[str] = None
    hidden_from_user: Optional[bool] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Action":
        return cls(
            id=obj.get("id"),
            ticket_id=_g(obj, "ticket_id", "faultid"),
            who=_g(obj, "who", "agentname"),
            action_date=_g(obj, "actiondate", "datetime"),
            note=_g(obj, "note", "note_html"),
            outcome=obj.get("outcome"),
            hidden_from_user=_g(obj, "hiddenfromuser", "important"),
        )


# ---------------------------------------------------------------------------
# Assets (Devices)
# ---------------------------------------------------------------------------


@dataclass
class Asset:
    """An asset (``Device``) — curated fields + ticket-count context."""

    id: Optional[int] = None
    inventory_number: Optional[str] = None
    key_field: Optional[str] = None
    assettype_id: Optional[int] = None
    assettype_name: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    site_id: Optional[int] = None
    site_name: Optional[str] = None
    status_id: Optional[int] = None
    open_ticket_count: Optional[int] = None
    total_ticket_count: Optional[int] = None
    related_ticket_id: Optional[int] = None
    fields: Optional[list] = None
    customfields: Optional[list] = None

    @classmethod
    def from_resource(cls, obj: dict, include_fields: bool = False) -> "Asset":
        fields = None
        customfields = None
        if include_fields:
            raw_fields = obj.get("fields") or []
            fields = [
                {"name": _g(f, "field_label", "name"), "value": _g(f, "display", "value")}
                for f in raw_fields
                if isinstance(f, dict)
            ] or None
            raw_cf = obj.get("customfields") or []
            customfields = [to_dict(CustomField.from_resource(c)) for c in raw_cf if isinstance(c, dict)] or None
        return cls(
            id=obj.get("id"),
            inventory_number=obj.get("inventory_number"),
            key_field=_g(obj, "key_field", "key_field_name"),
            assettype_id=obj.get("assettype_id"),
            assettype_name=obj.get("assettype_name"),
            client_id=obj.get("client_id"),
            client_name=obj.get("client_name"),
            site_id=obj.get("site_id"),
            site_name=obj.get("site_name"),
            status_id=obj.get("status_id"),
            open_ticket_count=obj.get("open_ticket_count"),
            total_ticket_count=obj.get("total_ticket_count"),
            related_ticket_id=obj.get("related_ticket_id"),
            fields=fields,
            customfields=customfields,
        )


# ---------------------------------------------------------------------------
# Context entities (clients / sites / users / contracts / KB)
# ---------------------------------------------------------------------------


@dataclass
class Client:
    id: Optional[int] = None
    name: Optional[str] = None
    inactive: Optional[bool] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Client":
        return cls(id=obj.get("id"), name=obj.get("name"), inactive=obj.get("inactive"))


@dataclass
class Site:
    id: Optional[int] = None
    name: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Site":
        return cls(
            id=obj.get("id"),
            name=obj.get("name"),
            client_id=_g(obj, "client_id", "client_id"),
            client_name=obj.get("client_name"),
        )


@dataclass
class User:
    id: Optional[int] = None
    name: Optional[str] = None
    emailaddress: Optional[str] = None
    client_id: Optional[int] = None
    site_id: Optional[int] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "User":
        return cls(
            id=obj.get("id"),
            name=obj.get("name"),
            emailaddress=obj.get("emailaddress"),
            client_id=obj.get("client_id"),
            site_id=obj.get("site_id"),
        )


@dataclass
class Contract:
    id: Optional[int] = None
    ref: Optional[str] = None
    client_id: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @classmethod
    def from_resource(cls, obj: dict) -> "Contract":
        return cls(
            id=obj.get("id"),
            ref=_g(obj, "ref", "reference"),
            client_id=obj.get("client_id"),
            start_date=_g(obj, "startdate", "start_date"),
            end_date=_g(obj, "enddate", "end_date"),
        )


@dataclass
class KBArticle:
    id: Optional[int] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    article_body: Optional[str] = None
    views: Optional[int] = None

    @classmethod
    def from_resource(cls, obj: dict, include_body: bool = False) -> "KBArticle":
        return cls(
            id=obj.get("id"),
            name=obj.get("name"),
            summary=_g(obj, "summary", "description"),
            article_body=obj.get("article") if include_body else None,
            views=_g(obj, "views", "viewcount"),
        )
