"""RPKI origin validation — the flagship capability. Spec 081, FR-001..FR-007c.

PRIMARY SOURCE: `rpki-validator.ripe.net/api/v1/validity/<asn>/<prefix>`

Chosen over RIPEstat's `rpki-validation` on three measured grounds (research R2):

  1. It reports RFC 6811 vocabulary natively — `not-found`, not `unknown`. The
     translation risk is removed at source rather than papered over downstream.
  2. `state` and `reason` are separate fields. RIPEstat fuses them into
     `invalid_asn` / `invalid_length`, forcing string parsing to recover a
     distinction FR-002 requires.
  3. It returns the VRPs that drove the verdict, which FR-005 requires so an
     operator can check the reasoning rather than trust a label.

FALLBACK: RIPEstat, with its vocabulary translated and the translation stated.

NOT CORROBORATION
-----------------
Both endpoints are RIPE NCC Routinator — same engine, same operator, same trust
anchors (research R3). The fallback is for *availability*, not agreement.
Comparing them would produce agreement that means nothing, so `corroborated` is
always False and every result says so.

An unreachable validator yields VALIDATION_UNAVAILABLE, never `not_found`
(FR-007c). Inferring "unsigned" from "could not ask" is the subtlest bug available
in this feature: it turns an outage into a confident, wrong, reassuring answer.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import envelope
import outcomes
from http_client import CLIENT, RateLimited, SourceUnavailable
from outcomes import Outcome

PRIMARY = "rpki-validator.ripe.net"
FALLBACK = "stat.ripe.net"

_PRIMARY_URL = "https://rpki-validator.ripe.net/api/v1/validity/{asn}/{prefix}"
_FALLBACK_URL = "https://stat.ripe.net/data/rpki-validation/data.json"

TOOL = "rpki_validate"


async def validate(prefix: str, origin_asn: str, *, fresh: bool = False) -> dict[str, Any]:
    """Validate a prefix + origin-AS **pair**.

    Validation is always of the pair — a prefix alone has no validity state, and a
    tool that accepted one would be answering a different question than the caller
    asked.
    """
    query = {"prefix": prefix, "origin_asn": origin_asn}

    # --- primary -----------------------------------------------------------
    url = _PRIMARY_URL.format(asn=quote(origin_asn, safe=""), prefix=quote(prefix, safe=""))
    try:
        payload, cached, age = await CLIENT.get_json("rpki", url, fresh=fresh)
        if payload is not None:
            result = outcomes.from_validator_json(payload, validator=PRIMARY)
            return _emit(result, query, cached, age, source=PRIMARY)
    except RateLimited as exc:
        return envelope.emit(
            source=PRIMARY, tool=TOOL, query=query,
            outcome=Outcome.RATE_LIMITED, message=str(exc),
            caveats=["No validation was performed; this is not a `not-found`."],
        )
    except (SourceUnavailable, ValueError):
        pass  # fall through to the fallback

    # --- fallback ----------------------------------------------------------
    try:
        payload, cached, age = await CLIENT.get_json(
            "rpki", _FALLBACK_URL,
            params={"resource": origin_asn, "prefix": prefix}, fresh=fresh,
        )
        if payload is not None:
            result = outcomes.from_ripestat_json(
                payload, prefix=prefix, origin_asn=origin_asn, validator=FALLBACK
            )
            return _emit(result, query, cached, age, source=FALLBACK)
    except RateLimited as exc:
        return envelope.emit(
            source=FALLBACK, tool=TOOL, query=query,
            outcome=Outcome.RATE_LIMITED, message=str(exc),
            caveats=["No validation was performed; this is not a `not-found`."],
        )
    except (SourceUnavailable, ValueError):
        pass

    # --- neither answered --------------------------------------------------
    # FR-007c. The distinction that matters most, one level down: we could not
    # ASK, which is not the same as being told there is no ROA.
    return envelope.emit(
        source=f"{PRIMARY} (and fallback {FALLBACK})",
        tool=TOOL,
        query=query,
        outcome=Outcome.VALIDATION_UNAVAILABLE,
        message=(
            "RPKI validation could not be performed: neither validator answered."
        ),
        caveats=[
            "This is NOT a 'not-found' result. 'not-found' means no ROA exists; "
            "this means the validator could not be reached, so the RPKI state of "
            "this announcement is genuinely unknown.",
            "NetClaw will not infer RPKI state from routing or registry data.",
        ],
    )


def _emit(
    result: outcomes.RpkiValidation,
    query: dict[str, Any],
    cached: bool,
    age: float | None,
    *,
    source: str,
) -> dict[str, Any]:
    """Wrap a validation in the provenance envelope.

    Note what is NOT here: no severity score, no "risk" field, no recommendation.
    FR-007 forbids this tool declaring a hijack, an attack or an incident. It
    reports state and the evidence behind it; escalation is the operator's call.
    """
    return envelope.emit(
        source=source,
        tool=TOOL,
        query=query,
        data=result.to_dict(),
        outcome=Outcome.OK,
        caveats=result.caveats(),
        cached=cached,
        cache_age_seconds=age,
    )
