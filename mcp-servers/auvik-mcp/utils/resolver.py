"""Entity resolver: turn human identifiers (name / hostname / IP) into Auvik IDs.

Resolution strategy (decision D1, research.md):
- ``/v1/inventory/device/info``, ``/network/info``, and ``/interface/info`` expose NO
  server-side name filter; resolution therefore fetches the full (paginated) list
  via ``client.get_all`` and matches client-side.
- ID heuristic: a value matching ``^[0-9]{6,}$`` is treated as an existing Auvik ID
  and returned directly, skipping any API call.
- For devices:
    - IP input  → match items where ``attributes.ipAddresses`` contains the value.
    - Name input → case-insensitive exact ``deviceName`` match first; fall back to
      substring matches.
- For networks:
    - Match on ``attributes.description`` (the only reliably populated name-like
      field on the network info resource; ``networkType`` is an enum, not a name).
- For tenants:
    - Match on ``attributes.domainPrefix`` or ``attributes.displayName``
      (case-insensitive exact first, then substring).
- Ambiguous (>1 match) → ``Resolution(ambiguous=True, candidates=[...])``.
- No match  → ``Resolution()`` (id=None, ambiguous=False, candidates=[]).
"""

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Optional

# Six or more consecutive digits → treat as an existing Auvik numeric ID.
_ID_RE = re.compile(r"^\d{6,}$")


def looks_like_id(value: str) -> bool:
    """Return True when *value* looks like an Auvik resource ID (≥6 digits)."""
    return bool(_ID_RE.match(value))


def _is_ip(value: str) -> bool:
    """Return True when *value* is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


@dataclass
class Resolution:
    """Result of a name/IP → ID resolution attempt."""

    id: Optional[str] = None
    ambiguous: bool = False
    candidates: list = field(default_factory=list)


def _device_candidate(item: dict) -> dict:
    attrs = item.get("attributes", {})
    ip_list = attrs.get("ipAddresses") or []
    return {
        "id": item["id"],
        "name": attrs.get("deviceName"),
        "ipAddress": ip_list[0] if ip_list else None,
        "entityType": "device",
        "tenant": None,
    }


def _network_candidate(item: dict) -> dict:
    attrs = item.get("attributes", {})
    return {
        "id": item["id"],
        "name": attrs.get("description"),
        "ipAddress": None,
        "entityType": "network",
        "tenant": None,
    }


def _tenant_candidate(item: dict) -> dict:
    attrs = item.get("attributes", {})
    return {
        "id": item["id"],
        "name": attrs.get("displayName") or attrs.get("domainPrefix"),
        "ipAddress": None,
        "entityType": "tenant",
        "tenant": attrs.get("domainPrefix"),
    }


def _to_resolution(candidates: list) -> Resolution:
    """Convert a candidate list to the appropriate Resolution."""
    if len(candidates) == 1:
        return Resolution(id=candidates[0]["id"])
    if len(candidates) > 1:
        return Resolution(ambiguous=True, candidates=candidates)
    return Resolution()


async def resolve_device(
    client,
    value: str,
    tenants=None,
) -> Resolution:
    """Resolve *value* (name, IP, or ID) to an Auvik device ID.

    Args:
        client:  AuvikClient (or compatible fake) with ``get_all``.
        value:   Human identifier — hostname, IP address, or numeric Auvik ID.
        tenants: Optional tenant scope forwarded to the API.

    Returns:
        :class:`Resolution` with ``id`` set on unique match, ``ambiguous=True``
        and ``candidates`` on multiple matches, or empty on no match.
    """
    if looks_like_id(value):
        return Resolution(id=value)

    params = {"tenants": tenants} if tenants else None
    result = await client.get_all("/v1/inventory/device/info", params=params)
    items = result.get("items", [])

    if _is_ip(value):
        candidates = [
            _device_candidate(item)
            for item in items
            if value in (item.get("attributes", {}).get("ipAddresses") or [])
        ]
        return _to_resolution(candidates)

    # Name matching: exact first, then substring (both case-insensitive).
    lower_value = value.lower()
    exact = [
        _device_candidate(item)
        for item in items
        if (item.get("attributes", {}).get("deviceName") or "").lower() == lower_value
    ]
    if exact:
        return _to_resolution(exact)

    substring = [
        _device_candidate(item)
        for item in items
        if lower_value in (item.get("attributes", {}).get("deviceName") or "").lower()
    ]
    return _to_resolution(substring)


async def resolve_network(
    client,
    value: str,
    tenants=None,
) -> Resolution:
    """Resolve *value* to an Auvik network ID.

    Matches client-side on ``attributes.description`` (case-insensitive exact,
    then substring).  The network info resource has no dedicated ``name`` field;
    ``description`` is the only human-readable label available on the list
    endpoint — ``networkType`` is an enum, not a name.

    Args:
        client:  AuvikClient (or compatible fake) with ``get_all``.
        value:   Network name / description fragment, or numeric Auvik ID.
        tenants: Optional tenant scope forwarded to the API.

    Returns:
        :class:`Resolution`.
    """
    if looks_like_id(value):
        return Resolution(id=value)

    params = {"tenants": tenants} if tenants else None
    result = await client.get_all("/v1/inventory/network/info", params=params)
    items = result.get("items", [])

    lower_value = value.lower()
    exact = [
        _network_candidate(item)
        for item in items
        if (item.get("attributes", {}).get("description") or "").lower() == lower_value
    ]
    if exact:
        return _to_resolution(exact)

    substring = [
        _network_candidate(item)
        for item in items
        if lower_value in (item.get("attributes", {}).get("description") or "").lower()
    ]
    return _to_resolution(substring)


async def resolve_tenant(
    client,
    value: str,
) -> Resolution:
    """Resolve *value* to an Auvik tenant ID.

    Matches client-side on ``attributes.domainPrefix`` or
    ``attributes.displayName`` (case-insensitive exact first, then substring).
    The ``/v1/tenants`` endpoint accepts no query params.

    Args:
        client: AuvikClient (or compatible fake) with ``get_all``.
        value:  Domain prefix, display name, or numeric Auvik ID.

    Returns:
        :class:`Resolution`.
    """
    if looks_like_id(value):
        return Resolution(id=value)

    result = await client.get_all("/v1/tenants")
    items = result.get("items", [])

    lower_value = value.lower()

    def _names(item: dict) -> tuple[str, str]:
        attrs = item.get("attributes", {})
        return (
            (attrs.get("domainPrefix") or "").lower(),
            (attrs.get("displayName") or "").lower(),
        )

    exact = [
        _tenant_candidate(item)
        for item in items
        if lower_value in _names(item)
    ]
    if exact:
        return _to_resolution(exact)

    substring = [
        _tenant_candidate(item)
        for item in items
        if any(lower_value in n for n in _names(item))
    ]
    return _to_resolution(substring)


async def resolve_tenants(
    client,
    tenants,
) -> tuple[Optional[str], Optional[dict]]:
    """Resolve a comma-separated *tenants* value (names/domain-prefixes/IDs)
    to a comma-joined string of Auvik tenant IDs.

    Resolution rules per part:
    - Empty / None input  → (None, None)  — caller should omit the param.
    - Part matching ``looks_like_id`` → kept as-is (no API call).
    - Otherwise          → ``resolve_tenant`` + ``resolve_or_error``.
    - On the first error  → (None, error_envelope) immediately.

    Returns:
        ``(resolved_str, None)`` on success.
        ``(None, error_envelope)`` if any part is ambiguous or not found.
    """
    if not tenants:
        return (None, None)

    parts = [p.strip() for p in str(tenants).split(",") if p.strip()]
    if not parts:
        return (None, None)

    ids: list[str] = []
    for part in parts:
        if looks_like_id(part):
            ids.append(part)
        else:
            resolution = await resolve_tenant(client, part)
            id_, err = resolve_or_error(resolution, label="tenant")
            if err:
                return (None, err)
            ids.append(id_)

    return (",".join(ids), None)


def resolve_or_error(
    resolution: Resolution,
    label: str = "entity",
) -> tuple[Optional[str], Optional[dict]]:
    """Convert a :class:`Resolution` into a ``(id, error_envelope)`` pair.

    Returns:
        ``(id, None)`` on unambiguous success.
        ``(None, error_envelope)`` on ambiguous or no-match.

    The error envelope follows the uniform ToolError shape::

        {"error": {"code": ..., "message": ..., "details": ...}}
    """
    if resolution.id is not None and not resolution.ambiguous:
        return (resolution.id, None)

    if resolution.ambiguous:
        return (
            None,
            {
                "error": {
                    "code": "Ambiguous",
                    "message": (
                        f"Multiple {label} matches found. "
                        "Refine the identifier or choose from the candidates."
                    ),
                    "details": {"candidates": resolution.candidates},
                }
            },
        )

    # No match
    return (
        None,
        {
            "error": {
                "code": "NotFound",
                "message": f"No {label} found matching the given identifier.",
                "details": None,
            }
        },
    )
