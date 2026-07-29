"""Human-identifier -> Halo-id resolution.

Halo addresses everything by numeric id, but operators speak in names ("the
Acme client", "SW-CORE-01", "Change Request"). These helpers resolve a name to
an id via the relevant list endpoint, returning a ``Resolution`` that callers
turn into either an id or a uniform error envelope (``resolve_or_error``).

Matching is exact (case-insensitive) first, then substring; a single match wins,
multiple matches return ``ambiguous`` with the candidates, and none returns a
NotFound. A value that ``looks_like_id`` (all digits) is passed through without
any API call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def looks_like_id(value) -> bool:
    """True if *value* is a bare numeric id (int, or an all-digit string)."""
    if isinstance(value, int):
        return True
    return isinstance(value, str) and value.strip().isdigit()


@dataclass
class Resolution:
    """Outcome of a name->id resolution attempt."""

    id: Optional[str] = None
    ambiguous: bool = False
    candidates: list = field(default_factory=list)


def resolve_or_error(resolution: Resolution, label: str):
    """Convert a ``Resolution`` into ``(id, error_envelope)``.

    On success -> ``(id, None)``. On ambiguity -> ``(None, {error: Ambiguous, ...})``
    with candidates. On no match -> ``(None, {error: NotFound, ...})``.
    """
    if resolution.ambiguous:
        return None, {
            "error": {
                "code": "Ambiguous",
                "message": f"Multiple {label}s matched; disambiguate by id.",
                "details": {"candidates": resolution.candidates},
            }
        }
    if resolution.id is None:
        return None, {
            "error": {
                "code": "NotFound",
                "message": f"No {label} matched the supplied value.",
                "details": None,
            }
        }
    return resolution.id, None


def _match(items: list, value: str, name_keys) -> Resolution:
    """Match *value* against the given name keys of *items* (exact then substring)."""
    needle = str(value).strip().lower()
    exact, partial = [], []
    for it in items:
        if not isinstance(it, dict):
            continue
        names = [str(it.get(k)).lower() for k in name_keys if it.get(k) is not None]
        if needle in names:
            exact.append(it)
        elif any(needle in n for n in names):
            partial.append(it)

    pool = exact or partial
    if not pool:
        return Resolution()
    if len(pool) > 1:
        return Resolution(
            ambiguous=True,
            candidates=[
                {"id": it.get("id"), "name": next((it.get(k) for k in name_keys if it.get(k)), None)}
                for it in pool
            ],
        )
    return Resolution(id=str(pool[0].get("id")))


async def _resolve(client, path: str, value, name_keys, params: Optional[dict] = None) -> Resolution:
    """Generic resolver: fetch a list from *path* and match *value* by name."""
    if looks_like_id(value):
        return Resolution(id=str(value))
    page = await client.get_all(path, params={**(params or {}), "search": value})
    if page.get("error"):
        return Resolution()
    return _match(page.get("items", []), value, name_keys)


async def resolve_ticket_type(client, value) -> Resolution:
    """Resolve a ticket type by name (``/TicketType``). No server-side search filter."""
    if looks_like_id(value):
        return Resolution(id=str(value))
    page = await client.get_all("/TicketType", params={})
    if page.get("error"):
        return Resolution()
    return _match(page.get("items", []), value, ("name",))


async def resolve_client(client, value) -> Resolution:
    return await _resolve(client, "/Client", value, ("name",))


async def resolve_site(client, value) -> Resolution:
    return await _resolve(client, "/Site", value, ("name",))


async def resolve_asset(client, value) -> Resolution:
    return await _resolve(client, "/Asset", value, ("inventory_number", "key_field", "name"))
