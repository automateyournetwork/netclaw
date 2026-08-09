"""RIPE Atlas — deliberately narrow. Spec 081, FR-017/FR-017a/FR-018.

Clarification Q1 narrowed this to the **two things Globalping does not provide**:

  anchors          stable, always-on measurement targets. Globalping has no
                   equivalent concept.
  per-AS probe      "can this network be measured from *inside* it?" — which
  counts            registry and routing data cannot answer.

General probe-availability-by-location is **NOT implemented here**. Globalping's
`locations` already owns it (spec 079), and duplicating it would breach Principle
VII. `routed_to_globalping()` exists to say so explicitly rather than returning a
subtly different answer to the same question.

Measurement *execution* is also Globalping's (FR-018). Atlas measurement creation
needs an API key and credits; only the read-only inventory half is in scope.
"""

from __future__ import annotations

from typing import Any

import envelope
from http_client import CLIENT, RateLimited, SourceUnavailable
from outcomes import Outcome

SOURCE = "atlas.ripe.net"
_ANCHORS = "https://atlas.ripe.net/api/v2/anchors/"
_PROBES = "https://atlas.ripe.net/api/v2/probes/"

MAX_ANCHORS = 100


async def anchors(country: str, *, fresh: bool = False) -> dict[str, Any]:
    """Atlas anchors in a country — stable reference targets."""
    tool = "atlas_anchors"
    query = {"country": country}
    try:
        payload, cached, age = await CLIENT.get_json(
            "atlas", _ANCHORS,
            params={"country": country, "page_size": MAX_ANCHORS}, fresh=fresh,
        )
    except RateLimited as exc:
        return envelope.emit(source=SOURCE, tool=tool, query=query,
                             outcome=Outcome.RATE_LIMITED, message=str(exc))
    except SourceUnavailable as exc:
        return envelope.unavailable(source=SOURCE, tool=tool, query=query, reason=str(exc))

    results = (payload or {}).get("results") or []
    if not results:
        return envelope.emit(
            source=SOURCE, tool=tool, query=query, outcome=Outcome.NO_RECORD,
            message=f"No Atlas anchors are listed in {country}.",
            data={"country": country, "anchors": [], "count": 0},
        )

    return envelope.emit(
        source=SOURCE, tool=tool, query=query, cached=cached, cache_age_seconds=age,
        data={
            "country": country,
            "anchors": [
                {
                    "id": a.get("id"),
                    "fqdn": a.get("fqdn"),
                    "city": a.get("city"),
                    "asn_v4": a.get("as_v4"),
                    "asn_v6": a.get("as_v6"),
                    "is_disabled": a.get("is_disabled"),
                }
                for a in results
            ],
            "count": len(results),
            "total_available": (payload or {}).get("count"),
        },
        caveats=[
            "Anchors are stable, always-on Atlas measurement targets. To actually "
            "run a measurement, use the Globalping skill — this tool only reports "
            "what infrastructure exists."
        ],
    )


async def probe_count(asn: str, *, fresh: bool = False) -> dict[str, Any]:
    """How many Atlas probes sit inside a given AS.

    Answers "is this network observable from within?" — useful before concluding
    anything from an absence of measurement data.
    """
    tool = "atlas_probe_count"
    query = {"asn": asn}
    number = int(asn.removeprefix("AS"))
    try:
        payload, cached, age = await CLIENT.get_json(
            "atlas", _PROBES,
            # page_size=1: we want the count, not the probe list. Fetching
            # thousands of probe records to count them would be rude.
            params={"asn": number, "page_size": 1}, fresh=fresh,
        )
    except RateLimited as exc:
        return envelope.emit(source=SOURCE, tool=tool, query=query,
                             outcome=Outcome.RATE_LIMITED, message=str(exc))
    except SourceUnavailable as exc:
        return envelope.unavailable(source=SOURCE, tool=tool, query=query, reason=str(exc))

    total = (payload or {}).get("count", 0)
    connected = sum(
        1 for p in ((payload or {}).get("results") or []) if p.get("status_name") == "Connected"
    )
    return envelope.emit(
        source=SOURCE, tool=tool, query=query, cached=cached, cache_age_seconds=age,
        data={
            "asn": asn,
            "probe_count": total,
            "sampled_connected": connected,
        },
        caveats=[
            "A probe count of zero means this AS cannot be measured from within by "
            "Atlas. It says nothing about the network's health or reachability.",
        ],
    )


def routed_to_globalping(what: str) -> dict[str, Any]:
    """Refuse a request that belongs to Globalping, and name it. FR-017a/FR-018.

    Returning a subtly different answer to the same question would be worse than
    refusing: the caller would not know they had asked the wrong tool.
    """
    return envelope.emit(
        source="bgp-intel-mcp (local)",
        tool="atlas_routed",
        query={"requested": what},
        outcome=Outcome.INPUT_REFUSED,
        message=(
            f"{what} belongs to the Globalping skill (spec 079), not this feature. "
            "Globalping measures from probes and reports general probe availability "
            "by location; this feature only reports Atlas anchors and per-AS probe "
            "density, which Globalping does not cover."
        ),
        caveats=["No request was made. Use globalping-external-checks instead."],
    )
