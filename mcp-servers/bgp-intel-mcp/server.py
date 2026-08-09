#!/usr/bin/env python3
"""bgp-intel-mcp — BGP & registry intelligence. Spec 081 (roadmap R9).

The sequel to spec 079's Globalping: R8 *measures* toward a target from outside;
this *looks up* who owns a resource, whether an announcement is legitimate, and
where a network peers.

Four public unauthenticated sources. **No credentials exist in this feature** —
nothing to leak, rotate or scope.

Every response carries its `source` and `retrieved_at` structurally and is
GAIT-audited, because it passes through `envelope.emit()` — a chokepoint, not a
convention. Read-only throughout: there is no write path and therefore no gate.

THE DISTINCTION THIS SERVER EXISTS TO PROTECT
---------------------------------------------
**RPKI `not_found` is not `invalid`.** Most of the internet has no ROA. Reporting
unsigned space as a finding would manufacture false incidents at scale.

Transport: stdio, FastMCP, JSON-RPC lifecycle (Principle V).
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import envelope  # noqa: E402
import validate  # noqa: E402
from sources import atlas, peeringdb, rdap, rpki, routing  # noqa: E402
from validate import InputRefused  # noqa: E402

mcp = FastMCP("bgp-intel-mcp")


# ---------------------------------------------------------------------------
# RPKI — 1 tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def rpki_validate(prefix: str, origin_asn: str, fresh: bool = False) -> dict:
    """Is this prefix legitimately announced by this AS? RPKI origin validation.

    Returns one of four states, which mean very different things:
      valid                  a ROA authorises this origin. Healthy.
      invalid + reason=as    a ROA exists; a DIFFERENT AS is authorised. Actionable.
      invalid + reason=length a ROA exists; the prefix is too specific. Actionable.
      not_found              NO ROA exists. This is the NORMAL state for most of
                             the internet and is NOT a finding.

    Never reports a hijack — it reports state and the ROAs behind it. Escalation is
    an operator judgement. Single validator; results say so explicitly.

    fresh=true bypasses the 5-minute cache, for when a ROA was just published.
    """
    try:
        pfx = str(validate.parse_prefix(prefix))
        asn = validate.normalise_asn(origin_asn)
    except InputRefused as exc:
        return envelope.refused(
            tool="rpki_validate",
            query={"prefix": prefix, "origin_asn": origin_asn},
            reason=str(exc),
        )
    return await rpki.validate(pfx, asn, fresh=fresh)


# ---------------------------------------------------------------------------
# Registry (RDAP) — 2 tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def registry_lookup(resource: str) -> dict:
    """Who is this IP, prefix or ASN allocated to? Registry record via RDAP.

    Returns holder, allocation range, responsible registry, abuse contacts.

    This is ALLOCATION data — it says who the space is registered to, NOT who is
    announcing it. For that use routing_announced_prefixes.
    """
    try:
        kind, value = validate.parse_resource(resource)
    except InputRefused as exc:
        return envelope.refused(
            tool="registry_lookup", query={"resource": resource}, reason=str(exc)
        )
    return await rdap.lookup(kind, value, tool="registry_lookup")


@mcp.tool()
async def registry_abuse_contact(resource: str) -> dict:
    """Abuse contact for an IP, prefix or ASN. The common incident-response ask."""
    try:
        kind, value = validate.parse_resource(resource)
    except InputRefused as exc:
        return envelope.refused(
            tool="registry_abuse_contact", query={"resource": resource}, reason=str(exc)
        )
    result = await rdap.lookup(kind, value, tool="registry_abuse_contact")
    data = result.get("data")
    if isinstance(data, dict):
        result["data"] = {
            "resource": value,
            "holder": data.get("holder"),
            "registry": data.get("registry"),
            "abuse_contacts": data.get("abuse_contacts") or [],
        }
        if not data.get("abuse_contacts"):
            result["caveats"].append(
                "No abuse contact is published for this resource. Try the covering "
                "allocation, or the registry's own abuse-reporting channel."
            )
    return result


# ---------------------------------------------------------------------------
# Routing — 2 tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def routing_as_overview(asn: str, fresh: bool = False) -> dict:
    """Holder and allocation status for an ASN, and whether it is announced at all."""
    try:
        value = validate.normalise_asn(asn)
    except InputRefused as exc:
        return envelope.refused(
            tool="routing_as_overview", query={"asn": asn}, reason=str(exc)
        )
    return await routing.as_overview(value, fresh=fresh)


@mcp.tool()
async def routing_announced_prefixes(asn: str, fresh: bool = False) -> dict:
    """What prefixes does this AS announce, and how widely are they seen?

    Visibility is from RIPE's route collectors, NOT a global view. Low visibility
    has legitimate causes and is not evidence of a leak or hijack.
    """
    try:
        value = validate.normalise_asn(asn)
    except InputRefused as exc:
        return envelope.refused(
            tool="routing_announced_prefixes", query={"asn": asn}, reason=str(exc)
        )
    return await routing.announced_prefixes(value, fresh=fresh)


# ---------------------------------------------------------------------------
# Peering — 2 tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def peering_network(asn: str, fresh: bool = False) -> dict:
    """This AS's PeeringDB record: network type, traffic profile, peering policy.

    PeeringDB is SELF-REPORTED. No record means nobody published one — not that
    the network does not peer.
    """
    try:
        value = validate.normalise_asn(asn)
    except InputRefused as exc:
        return envelope.refused(tool="peering_network", query={"asn": asn}, reason=str(exc))
    return await peeringdb.network(value, fresh=fresh)


@mcp.tool()
async def peering_presence(asn: str, fresh: bool = False) -> dict:
    """Which IXPs and facilities does this AS report being present at?

    Self-reported; absence is not evidence of absence.
    """
    try:
        value = validate.normalise_asn(asn)
    except InputRefused as exc:
        return envelope.refused(tool="peering_presence", query={"asn": asn}, reason=str(exc))
    return await peeringdb.presence(value, fresh=fresh)


# ---------------------------------------------------------------------------
# Atlas — 2 tools, deliberately narrow
# ---------------------------------------------------------------------------

@mcp.tool()
async def atlas_anchors(country: str, fresh: bool = False) -> dict:
    """RIPE Atlas anchors in a country — stable, always-on measurement targets.

    For general probe availability by location, or to RUN a measurement, use the
    Globalping skill instead. This reports only what Globalping does not cover.
    """
    try:
        value = validate.parse_country(country)
    except InputRefused as exc:
        return envelope.refused(tool="atlas_anchors", query={"country": country}, reason=str(exc))
    return await atlas.anchors(value, fresh=fresh)


@mcp.tool()
async def atlas_probe_count(asn: str, fresh: bool = False) -> dict:
    """How many RIPE Atlas probes are inside this AS? Can it be measured from within?"""
    try:
        value = validate.normalise_asn(asn)
    except InputRefused as exc:
        return envelope.refused(tool="atlas_probe_count", query={"asn": asn}, reason=str(exc))
    return await atlas.probe_count(value, fresh=fresh)


# ---------------------------------------------------------------------------
# Composite — 1 tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def resource_report(resource: str, origin_asn: str = "") -> dict:
    """Everything known about an internet resource: registry, routing, peering, RPKI.

    Each section carries its own source. Supply origin_asn alongside a prefix to
    include RPKI validation.
    """
    tool = "resource_report"
    try:
        kind, value = validate.parse_resource(resource)
    except InputRefused as exc:
        return envelope.refused(tool=tool, query={"resource": resource}, reason=str(exc))

    sections: dict[str, Any] = {}

    # DELIBERATELY SERIAL — one await after another, never asyncio.gather.
    # FR-023a prohibits parallel fan-out against these free services, and this is
    # the tool most likely to attract a "make it faster" change. The rate limiter
    # in http_client would serialise per source anyway; this makes the intent
    # visible at the call site so nobody has to discover it.
    sections["registry"] = await rdap.lookup(kind, value, tool=tool)

    if kind == "asn":
        sections["routing"] = await routing.as_overview(value, fresh=False)
        sections["announcements"] = await routing.announced_prefixes(value, fresh=False)
        sections["peering"] = await peeringdb.network(value, fresh=False)
        sections["atlas"] = await atlas.probe_count(value, fresh=False)
    else:
        if origin_asn:
            try:
                asn = validate.normalise_asn(origin_asn)
                sections["rpki"] = await rpki.validate(value, asn, fresh=False)
            except InputRefused as exc:
                sections["rpki"] = envelope.refused(
                    tool=tool, query={"origin_asn": origin_asn}, reason=str(exc)
                )

    caveats = [
        "Each section carries its own source; do not attribute one section's data "
        "to another's origin.",
    ]
    if kind == "prefix" and not origin_asn:
        caveats.append(
            "RPKI validation was not performed because no origin_asn was supplied. "
            "Validation is always of a prefix AND origin-AS pair — this is NOT a "
            "'not-found' result."
        )

    # Report disagreement rather than resolving it (Edge Cases).
    reg = (sections.get("registry") or {}).get("data") or {}
    peer = (sections.get("peering") or {}).get("data") or {}
    holder, name = reg.get("holder"), peer.get("name")
    if holder and name and holder.strip().lower() != name.strip().lower():
        caveats.append(
            f"Registry holder ({holder!r}) and PeeringDB name ({name!r}) differ. "
            "Both are reported as-is; this is common and not necessarily a problem."
        )

    return envelope.merged(tool=tool, sections=sections,
                           query={"resource": resource, "origin_asn": origin_asn or None},
                           caveats=caveats)


if __name__ == "__main__":
    mcp.run(transport="stdio")
