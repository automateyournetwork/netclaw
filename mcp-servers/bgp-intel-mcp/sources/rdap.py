"""Registry records via RDAP. Spec 081, FR-008..FR-011.

RDAP replaces scraped WHOIS with structured JSON, and RFC 7484 defines how to find
the responsible registry: fetch IANA's bootstrap file, match the resource to an
RIR, query that RIR directly.

Doing it that way is not pedantry — it means FR-010's "name the responding
registry" is satisfied **by construction**. We know which RIR we chose and why,
rather than following an opaque redirect and reporting "the registry".

ARIN
----
Measured 2026-08-03: `rdap.arin.net` resets the connection from this host
(`Recv failure: Connection reset by peer`). Whether that is host-specific,
transient, or a policy is unresolved (research open item 2), so it is handled as a
generic per-source failure with a fallback — deliberately **not** hardcoded as
"ARIN is broken."

THE CATEGORY ERROR THIS MODULE MUST NOT MAKE
--------------------------------------------
RDAP says who a block is **allocated to**. It says nothing about who is
**announcing** it. Presenting an RDAP holder as evidence about routing is the same
mistake as presenting FortiManager intent as observed device state (spec 080), and
every result here carries a caveat saying so.
"""

from __future__ import annotations

import ipaddress
from typing import Any

import envelope
from http_client import CLIENT, RateLimited, SourceUnavailable
from outcomes import Outcome

_BOOTSTRAP_V4 = "https://data.iana.org/rdap/ipv4.json"
_BOOTSTRAP_V6 = "https://data.iana.org/rdap/ipv6.json"
_BOOTSTRAP_ASN = "https://data.iana.org/rdap/asn.json"
_FALLBACK = "https://rdap.org"

ALLOCATION_CAVEAT = (
    "This is allocation data: it says who the address space is registered to. It "
    "is NOT evidence about who is currently announcing it. For that, use the "
    "routing tools."
)


async def _bootstrap(url: str) -> list[Any]:
    payload, _, _ = await CLIENT.get_json("rdap", url)
    return (payload or {}).get("services") or []


async def _resolve_registry_v4v6(network: Any) -> tuple[str | None, str | None]:
    """Return `(base_url, registry_label)` for an IP network, per RFC 7484."""
    url = _BOOTSTRAP_V4 if network.version == 4 else _BOOTSTRAP_V6
    try:
        services = await _bootstrap(url)
    except (SourceUnavailable, RateLimited):
        return None, None

    best: tuple[int, str] | None = None
    for entry in services:
        ranges, urls = (entry + [[], []])[:2]
        for cidr in ranges:
            try:
                candidate = ipaddress.ip_network(cidr, strict=False)
            except ValueError:
                continue
            if candidate.version != network.version:
                continue
            if network.subnet_of(candidate):
                # Longest match wins — bootstrap entries can overlap.
                if best is None or candidate.prefixlen > best[0]:
                    if urls:
                        best = (candidate.prefixlen, urls[0].rstrip("/"))
    if best is None:
        return None, None
    base = best[1]
    return base, base.split("//")[-1].split("/")[0]


async def _resolve_registry_asn(asn_number: int) -> tuple[str | None, str | None]:
    try:
        services = await _bootstrap(_BOOTSTRAP_ASN)
    except (SourceUnavailable, RateLimited):
        return None, None
    for entry in services:
        ranges, urls = (entry + [[], []])[:2]
        for rng in ranges:
            lo, _, hi = rng.partition("-")
            try:
                low = int(lo)
                high = int(hi) if hi else low
            except ValueError:
                continue
            if low <= asn_number <= high and urls:
                base = urls[0].rstrip("/")
                return base, base.split("//")[-1].split("/")[0]
    return None, None


async def lookup(resource_kind: str, resource: str, *, tool: str) -> dict[str, Any]:
    """Look up an IP/prefix or ASN. `resource_kind` is 'prefix' or 'asn'."""
    query = {"resource": resource, "kind": resource_kind}

    if resource_kind == "asn":
        number = int(resource.removeprefix("AS"))
        base, label = await _resolve_registry_asn(number)
        path = f"/autnum/{number}"
    else:
        network = ipaddress.ip_network(resource, strict=False)
        base, label = await _resolve_registry_v4v6(network)
        path = f"/ip/{network}"

    attempts: list[tuple[str, str]] = []
    if base:
        attempts.append((base + path, label or base))
    # rdap.org follows the bootstrap itself; used when direct resolution failed or
    # the direct endpoint refused us (ARIN).
    attempts.append((_FALLBACK + path, "rdap.org (bootstrap redirector)"))

    last_error: str | None = None
    refused = False
    for url, registry in attempts:
        try:
            payload, cached, age = await CLIENT.get_json("rdap", url)
        except RateLimited as exc:
            return envelope.emit(
                source=registry, tool=tool, query=query,
                outcome=Outcome.RATE_LIMITED, message=str(exc),
            )
        except SourceUnavailable as exc:
            last_error = str(exc)
            refused = refused or exc.refused
            continue

        if payload is None:
            # A 404 is a real answer: the registry has no such record.
            return envelope.emit(
                source=registry, tool=tool, query=query,
                outcome=Outcome.NO_RECORD,
                message=f"{registry} has no record for {resource}.",
                caveats=[ALLOCATION_CAVEAT],
            )

        return envelope.emit(
            source=registry,
            tool=tool,
            query=query,
            data=_shape(payload, registry, base, attempts[0][1] == registry),
            caveats=[ALLOCATION_CAVEAT],
            cached=cached,
            cache_age_seconds=age,
        )

    # FR-011: a source failure, naming the source — never "no record".
    tried = ", ".join(r for _, r in attempts)
    return envelope.unavailable(
        source=tried,
        tool=tool,
        query=query,
        reason=last_error or "no registry answered",
        outcome=Outcome.SOURCE_REFUSED if refused else Outcome.SOURCE_UNAVAILABLE,
    )


def _shape(payload: dict[str, Any], registry: str, base: str | None, direct: bool) -> dict[str, Any]:
    """Extract the fields an operator actually wants from an RDAP object."""
    entities = payload.get("entities") or []

    def _vcard_value(entity: dict[str, Any], key: str) -> str | None:
        for item in (entity.get("vcardArray") or [None, []])[1] or []:
            if isinstance(item, list) and item and item[0] == key:
                return item[3] if len(item) > 3 else None
        return None

    holder = payload.get("name") or None
    abuse: list[str] = []
    contacts: list[dict[str, Any]] = []
    for ent in entities:
        roles = [str(r).lower() for r in (ent.get("roles") or [])]
        email = _vcard_value(ent, "email")
        contacts.append({
            "handle": ent.get("handle"),
            "roles": roles,
            "name": _vcard_value(ent, "fn"),
            "email": email,
        })
        if "abuse" in roles and email:
            abuse.append(email)

    return {
        "holder": holder,
        "handle": payload.get("handle"),
        "allocation_range": payload.get("startAddress") and
        f"{payload.get('startAddress')} - {payload.get('endAddress')}" or None,
        "cidr": payload.get("cidr0_cidrs") or None,
        "asn_range": (
            f"{payload.get('startAutnum')} - {payload.get('endAutnum')}"
            if payload.get("startAutnum") is not None else None
        ),
        "country": payload.get("country"),
        "type": payload.get("type"),
        "status": payload.get("status"),
        "registry": registry,
        # FR-010: not just which registry, but HOW it was chosen.
        "registry_selected_via": "iana_bootstrap" if direct and base else "rdap_org_fallback",
        "abuse_contacts": abuse,
        "contacts": contacts,
        "events": [
            {"action": e.get("eventAction"), "date": e.get("eventDate")}
            for e in (payload.get("events") or [])
        ],
    }
