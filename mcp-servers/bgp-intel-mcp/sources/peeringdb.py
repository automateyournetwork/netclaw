"""PeeringDB — interconnection data. Spec 081, FR-015/FR-016.

THE ONE THING TO GET RIGHT
--------------------------
**PeeringDB is self-reported.** Operators maintain their own records. So an absent
record means *nobody filled in the form* — not that the network does not peer.

Reporting "no PeeringDB record" as "this AS does not peer" would be the same
absence-of-evidence error as RPKI `not-found` meaning "invalid", and it would be
wrong about a large number of networks that peer extensively and simply do not
publish.
"""

from __future__ import annotations

from typing import Any

import envelope
from http_client import CLIENT, RateLimited, SourceUnavailable
from outcomes import Outcome

SOURCE = "peeringdb.com"
_NET = "https://www.peeringdb.com/api/net"
_NETIXLAN = "https://www.peeringdb.com/api/netixlan"
_NETFAC = "https://www.peeringdb.com/api/netfac"

SELF_REPORTED_CAVEAT = (
    "PeeringDB is self-reported: operators maintain their own records. Absence of "
    "a record, an IXP, or a facility means nobody published it — NOT that the "
    "network does not peer there."
)


async def _net_id(asn: str, *, fresh: bool = False) -> tuple[int | None, dict[str, Any] | None, bool, float | None]:
    number = int(asn.removeprefix("AS"))
    payload, cached, age = await CLIENT.get_json(
        "peeringdb", _NET, params={"asn": number}, fresh=fresh
    )
    records = (payload or {}).get("data") or []
    if not records:
        return None, None, cached, age
    return records[0].get("id"), records[0], cached, age


async def network(asn: str, *, fresh: bool = False) -> dict[str, Any]:
    """The AS's PeeringDB network record: type, traffic profile, policy, contacts."""
    tool = "peering_network"
    query = {"asn": asn}
    try:
        _, rec, cached, age = await _net_id(asn, fresh=fresh)
    except RateLimited as exc:
        return envelope.emit(source=SOURCE, tool=tool, query=query,
                             outcome=Outcome.RATE_LIMITED, message=str(exc))
    except SourceUnavailable as exc:
        return envelope.unavailable(source=SOURCE, tool=tool, query=query, reason=str(exc))

    if rec is None:
        # FR-016. The wording here is the requirement.
        return envelope.emit(
            source=SOURCE, tool=tool, query=query, outcome=Outcome.NO_RECORD,
            message=(
                f"{asn} has no self-reported PeeringDB record. This is NOT evidence "
                "that the network does not peer."
            ),
            caveats=[SELF_REPORTED_CAVEAT],
        )

    return envelope.emit(
        source=SOURCE, tool=tool, query=query, cached=cached, cache_age_seconds=age,
        data={
            "asn": asn,
            "name": rec.get("name"),
            "aka": rec.get("aka") or None,
            "network_type": rec.get("info_type"),
            "traffic_estimate": rec.get("info_traffic"),
            "traffic_ratio": rec.get("info_ratio"),
            "scope": rec.get("info_scope"),
            "policy_general": rec.get("policy_general"),
            "policy_url": rec.get("policy_url") or None,
            "irr_as_set": rec.get("irr_as_set") or None,
            "website": rec.get("website") or None,
            "ix_count": rec.get("ix_count"),
            "fac_count": rec.get("fac_count"),
        },
        caveats=[SELF_REPORTED_CAVEAT],
    )


async def presence(asn: str, *, fresh: bool = False) -> dict[str, Any]:
    """IXPs and facilities this AS reports being present at."""
    tool = "peering_presence"
    query = {"asn": asn}
    try:
        net_id, rec, cached, age = await _net_id(asn, fresh=fresh)
        if net_id is None:
            return envelope.emit(
                source=SOURCE, tool=tool, query=query, outcome=Outcome.NO_RECORD,
                message=(
                    f"{asn} has no self-reported PeeringDB record, so no IXP or "
                    "facility presence is published. This is NOT evidence that the "
                    "network does not peer."
                ),
                caveats=[SELF_REPORTED_CAVEAT],
            )
        ixlans, _, _ = await CLIENT.get_json(
            "peeringdb", _NETIXLAN, params={"net_id": net_id}, fresh=fresh
        )
        facs, _, _ = await CLIENT.get_json(
            "peeringdb", _NETFAC, params={"net_id": net_id}, fresh=fresh
        )
    except RateLimited as exc:
        return envelope.emit(source=SOURCE, tool=tool, query=query,
                             outcome=Outcome.RATE_LIMITED, message=str(exc))
    except SourceUnavailable as exc:
        return envelope.unavailable(source=SOURCE, tool=tool, query=query, reason=str(exc))

    ix = [
        {
            "ix_name": r.get("name"),
            "speed_mbps": r.get("speed"),
            "ipaddr4": r.get("ipaddr4"),
            "ipaddr6": r.get("ipaddr6"),
            "operational": r.get("operational"),
            "is_rs_peer": r.get("is_rs_peer"),
        }
        for r in ((ixlans or {}).get("data") or [])
    ]
    fac = [
        {"name": r.get("name"), "city": r.get("city"), "country": r.get("country")}
        for r in ((facs or {}).get("data") or [])
    ]

    return envelope.emit(
        source=SOURCE, tool=tool, query=query, cached=cached, cache_age_seconds=age,
        data={
            "asn": asn,
            "name": (rec or {}).get("name"),
            "ixps": ix,
            "ixp_count": len(ix),
            "facilities": fac,
            "facility_count": len(fac),
        },
        caveats=[SELF_REPORTED_CAVEAT],
    )
