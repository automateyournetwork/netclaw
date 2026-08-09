"""Routing status from RIPEstat. Spec 081, FR-012..FR-014.

WHAT VISIBILITY IS NOT
----------------------
These figures come from **RIPE's route collectors**, not from a global view of the
internet. A prefix seen by few peers has entirely legitimate explanations:

  - a deliberately scoped announcement (no-export, a single upstream)
  - anycast, where different collectors see different origins
  - a very recent change that has not propagated to every collector

So this module reports counts and the collector basis, and **never** attaches the
words "leak" or "hijack" (FR-013, SC-009). Declaring a routing incident needs more
evidence than one collector network's view, and it is an operator judgement.

Three outcomes that look alike and are not (FR-014):
    ok + prefixes         the AS announces these
    no_record (empty)     the AS exists and announces nothing observed here
    source_unavailable    RIPEstat did not answer
"""

from __future__ import annotations

from typing import Any

import envelope
from http_client import CLIENT, RateLimited, SourceUnavailable
from outcomes import Outcome

SOURCE = "stat.ripe.net"
_OVERVIEW = "https://stat.ripe.net/data/as-overview/data.json"
_ANNOUNCED = "https://stat.ripe.net/data/announced-prefixes/data.json"
_ROUTING_STATUS = "https://stat.ripe.net/data/routing-status/data.json"

COLLECTOR_CAVEAT = (
    "Visibility is measured from RIPE NCC's route collectors, not from a global "
    "view of the internet. Low visibility has legitimate causes — scoped "
    "announcements, anycast, or recent changes — and is not by itself evidence of "
    "a route leak or hijack."
)

#: Announced-prefix lists can be very large for a transit AS. Bounded and stated,
#: never silently truncated.
MAX_PREFIXES = 200


async def as_overview(asn: str, *, fresh: bool = False) -> dict[str, Any]:
    """Holder and allocation status for an ASN — distinct from what it announces."""
    tool = "routing_as_overview"
    query = {"asn": asn}
    try:
        payload, cached, age = await CLIENT.get_json(
            "routing", _OVERVIEW, params={"resource": asn}, fresh=fresh
        )
    except RateLimited as exc:
        return envelope.emit(source=SOURCE, tool=tool, query=query,
                             outcome=Outcome.RATE_LIMITED, message=str(exc))
    except SourceUnavailable as exc:
        return envelope.unavailable(source=SOURCE, tool=tool, query=query, reason=str(exc))

    data = (payload or {}).get("data") or {}
    if not data or data.get("announced") is None and not data.get("holder"):
        return envelope.emit(
            source=SOURCE, tool=tool, query=query, outcome=Outcome.NO_RECORD,
            message=f"RIPEstat has no overview for {asn}.",
        )

    return envelope.emit(
        source=SOURCE, tool=tool, query=query, cached=cached, cache_age_seconds=age,
        data={
            "asn": asn,
            "holder": data.get("holder"),
            # `announced` is RIPEstat's own boolean for "is this AS visible at all".
            "currently_announced": data.get("announced"),
            "type": data.get("type"),
            "block": (data.get("block") or {}).get("desc"),
        },
        caveats=[
            "Holder is registry/allocation data. What the AS actually announces is "
            "a separate question — use routing_announced_prefixes."
        ],
    )


async def announced_prefixes(asn: str, *, fresh: bool = False) -> dict[str, Any]:
    """Prefixes observed as announced by this AS, with visibility."""
    tool = "routing_announced_prefixes"
    query = {"asn": asn}
    try:
        payload, cached, age = await CLIENT.get_json(
            "routing", _ANNOUNCED, params={"resource": asn}, fresh=fresh
        )
        status, _, _ = await CLIENT.get_json(
            "routing", _ROUTING_STATUS, params={"resource": asn}, fresh=fresh
        )
    except RateLimited as exc:
        return envelope.emit(source=SOURCE, tool=tool, query=query,
                             outcome=Outcome.RATE_LIMITED, message=str(exc))
    except SourceUnavailable as exc:
        return envelope.unavailable(source=SOURCE, tool=tool, query=query, reason=str(exc))

    data = (payload or {}).get("data") or {}
    raw = data.get("prefixes") or []
    sdata = (status or {}).get("data") or {}

    if not raw:
        # FR-014: "announces nothing observed" is a real finding, and is distinct
        # from "the AS does not exist" and from "the query failed".
        return envelope.emit(
            source=SOURCE, tool=tool, query=query, outcome=Outcome.NO_RECORD,
            message=(
                f"No announcements observed for {asn} by RIPE's collectors. This "
                "is distinct from the AS not existing, and from a failed query."
            ),
            caveats=[COLLECTOR_CAVEAT],
            data={"asn": asn, "prefixes": [], "count": 0},
        )

    truncated = len(raw) > MAX_PREFIXES
    prefixes = [
        {"prefix": p.get("prefix"), "timelines": len(p.get("timelines") or [])}
        for p in raw[:MAX_PREFIXES]
    ]
    caveats = [COLLECTOR_CAVEAT]
    if truncated:
        caveats.append(
            f"Showing {MAX_PREFIXES} of {len(raw)} prefixes. The list was bounded, "
            "not silently truncated."
        )

    return envelope.emit(
        source=SOURCE, tool=tool, query=query, cached=cached, cache_age_seconds=age,
        data={
            "asn": asn,
            "prefixes": prefixes,
            "count": len(prefixes),
            "total_available": len(raw),
            "truncated": truncated,
            "observed_neighbours": sdata.get("observed_neighbours"),
            "announced_space": sdata.get("announced_space"),
            "visibility": {
                "ris_peers_seeing": (sdata.get("visibility") or {}).get("v4", {}).get("ris_peers_seeing"),
                "total_ris_peers": (sdata.get("visibility") or {}).get("v4", {}).get("total_ris_peers"),
            },
            "collector_basis": "RIPE NCC RIS route collectors",
        },
        caveats=caveats,
    )
