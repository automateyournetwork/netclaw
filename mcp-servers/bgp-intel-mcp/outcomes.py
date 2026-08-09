"""The typed distinctions this feature exists to protect. Spec 081, FR-002/003/004/007c/011.

THE ONE THAT MATTERS MOST
-------------------------
**RPKI `not_found` is not `invalid`.**

Most of the internet has no ROA. Unsigned address space is the overwhelmingly
common case, not an anomaly. An operator told that unsigned space is "invalid",
"unverified in a bad way", or a security finding will be handed false incidents at
a scale that destroys trust in the tool within a day.

    valid                  a ROA exists and authorises this origin      not a finding
    invalid + reason=as    a ROA exists, a DIFFERENT AS is authorised    ACTIONABLE
    invalid + reason=length a ROA exists, prefix is too specific         ACTIONABLE
    not_found              NO ROA EXISTS                                 not a finding

This is the same error class as spec 078's "no advisories != not vulnerable",
spec 079's "no probes found != outage" and spec 080's "no logs != rule unused".
Each shipped with the distinction named explicitly and enforced structurally.

SPELLING — three variants, all deliberate
-----------------------------------------
    RFC 6811 and the validator's JSON   ->  "not-found"   (hyphen: wire format)
    this module, enum members           ->  "not_found"   (underscore: identifier)
    RIPEstat fallback only              ->  "unknown"     (a different vocabulary)

Normalising these would either produce an invalid Python identifier or silently
break the wire mapping. A future maintainer tidying this "inconsistency" is a
realistic hazard, so it is written down rather than left to be inferred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    """What happened. Several of these look alike and mean very different things."""

    OK = "ok"

    #: The source answered and there is no record for this resource.
    #: MUST NOT be produced when the source failed — see SOURCE_UNAVAILABLE.
    NO_RECORD = "no_record"

    #: The source did not answer. A dead API must never look like an empty
    #: registry (FR-011).
    SOURCE_UNAVAILABLE = "source_unavailable"

    #: The source actively rejected us — e.g. ARIN's RDAP connection reset.
    SOURCE_REFUSED = "source_refused"

    #: Refused locally, before any request left the machine (FR-028). Sending a
    #: private address to a public registry is a disclosure even if it then fails.
    INPUT_REFUSED = "input_refused"

    #: Throttled. Backed off and reported rather than retried (FR-027).
    RATE_LIMITED = "rate_limited"

    #: RPKI-specific: the validator could not be reached.
    #: **This is not `not_found`.** An unreachable validator does not mean the
    #: space is unsigned (FR-007c). The subtlest bug available in this feature.
    VALIDATION_UNAVAILABLE = "validation_unavailable"


class RpkiState(str, Enum):
    """RFC 6811 origin validation states, in the standard's own vocabulary."""

    VALID = "valid"
    INVALID = "invalid"
    NOT_FOUND = "not_found"


class RpkiReason(str, Enum):
    """Why an announcement is invalid. RFC 6811 collapses both into "Invalid";
    the validator is more granular and flattening it destroys the difference
    between "someone else is announcing your space" and "you announced a /24
    under a /22 ROA" — different severity, different remediation (FR-002)."""

    AS = "as"
    LENGTH = "length"


#: Wire spelling -> internal state. The validator returns RFC 6811's hyphenated
#: form; `not-found` is not a valid Python identifier, hence the mapping.
WIRE_TO_STATE = {
    "valid": RpkiState.VALID,
    "invalid": RpkiState.INVALID,
    "not-found": RpkiState.NOT_FOUND,
    "notfound": RpkiState.NOT_FOUND,
}

#: RIPEstat fallback vocabulary -> (state, reason). RIPEstat diverges from the
#: standard twice: it says `unknown` for NotFound, and it FUSES state and reason
#: into one string. Both must be translated, and the translation stated (FR-004).
RIPESTAT_TO_STATE: dict[str, tuple[RpkiState, RpkiReason | None]] = {
    "valid": (RpkiState.VALID, None),
    "invalid_asn": (RpkiState.INVALID, RpkiReason.AS),
    "invalid_length": (RpkiState.INVALID, RpkiReason.LENGTH),
    "unknown": (RpkiState.NOT_FOUND, None),
}

#: Verbatim caveat attached to every `not_found`. The single most important string
#: in this codebase (FR-003). Deliberately contains none of the words
#: "invalid", "suspicious" or "unverified" — SC-004 asserts their absence.
NOT_FOUND_CAVEAT = (
    "No ROA exists for this prefix. This is the normal state for most address "
    "space on the internet and is NOT a finding — it means the holder has not "
    "published a Route Origin Authorisation, not that anything is wrong. "
    "RFC 6811 calls this state NotFound."
)

#: FR-007b — the error asymmetry, attached to every RPKI result. A wrong `valid`
#: says an announcement is authorised when it is not; a wrong `invalid` sends
#: someone chasing a hijack that is not happening.
VALID_CAVEAT = (
    "This reflects one validator's current view. It means a ROA authorises this "
    "origin — not that the announcement is legitimate in any broader sense."
)
INVALID_CAVEAT = (
    "A ROA covers this prefix and does not authorise this origin. Before treating "
    "this as an incident, confirm the origin AS is what you think it is and that "
    "the ROA is current — RPKI state changes when holders publish or withdraw."
)


@dataclass
class RpkiValidation:
    """One origin-validation result. Validation is always of the *pair*."""

    prefix: str
    origin_asn: str
    state: RpkiState
    validator: str
    reason: RpkiReason | None = None
    description: str | None = None
    vrps_matched: list[dict[str, Any]] = field(default_factory=list)
    vrps_unmatched_as: list[dict[str, Any]] = field(default_factory=list)
    vrps_unmatched_length: list[dict[str, Any]] = field(default_factory=list)
    #: Always False. Both reachable validators are RIPE NCC Routinator — same
    #: engine, same operator — so agreement between them would be theatre.
    #: Present rather than omitted so the absence of corroboration is explicit.
    corroborated: bool = False
    #: Set when the RIPEstat fallback was used and its vocabulary translated.
    translated_from: str | None = None

    @property
    def is_finding(self) -> bool:
        """True only for `invalid`. FR-003/FR-009.

        `valid` is healthy and `not_found` is the common case; neither is
        something to escalate.
        """
        return self.state is RpkiState.INVALID

    def authorised_origins(self) -> list[str]:
        """What the ROA *does* permit — this is what makes an `invalid` actionable
        rather than merely alarming (FR-006)."""
        out = []
        for vrp in self.vrps_unmatched_as + self.vrps_unmatched_length:
            asn = vrp.get("asn") or vrp.get("origin")
            if asn and asn not in out:
                out.append(str(asn))
        return out

    def max_lengths(self) -> list[int]:
        """maxLength values from covering ROAs — the other half of FR-006."""
        out = []
        for vrp in self.vrps_unmatched_length + self.vrps_unmatched_as:
            ml = vrp.get("max_length") or vrp.get("maxLength")
            if ml is not None:
                try:
                    v = int(ml)
                except (TypeError, ValueError):
                    continue
                if v not in out:
                    out.append(v)
        return out

    def caveats(self) -> list[str]:
        """The statements that must survive a model summarising the payload."""
        out: list[str] = []
        if self.state is RpkiState.NOT_FOUND:
            out.append(NOT_FOUND_CAVEAT)
        elif self.state is RpkiState.VALID:
            out.append(VALID_CAVEAT)
        elif self.state is RpkiState.INVALID:
            out.append(INVALID_CAVEAT)
            if self.reason is RpkiReason.AS:
                permitted = ", ".join(self.authorised_origins()) or "an unlisted AS"
                out.append(
                    f"The covering ROA authorises {permitted}, not {self.origin_asn}."
                )
            elif self.reason is RpkiReason.LENGTH:
                mls = ", ".join(str(m) for m in self.max_lengths()) or "a shorter length"
                out.append(
                    f"The origin AS is authorised, but the ROA permits a maximum "
                    f"prefix length of {mls}. This is usually a local "
                    f"misconfiguration rather than a third party announcing your space."
                )
        # FR-007a — never imply corroboration that does not exist.
        out.append(
            f"Single-validator result from {self.validator}; not corroborated by an "
            "independent validator."
        )
        if self.translated_from:
            out.append(
                f"State was translated from the {self.translated_from} vocabulary "
                f"to RFC 6811 terms."
            )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "prefix": self.prefix,
            "origin_asn": self.origin_asn,
            "state": self.state.value,
            "reason": self.reason.value if self.reason else None,
            # RFC 6811's own spelling, for readers who know the standard.
            "rfc6811_state": "NotFound" if self.state is RpkiState.NOT_FOUND
            else self.state.value.capitalize(),
            "is_finding": self.is_finding,
            "description": self.description,
            "validator": self.validator,
            "corroborated": self.corroborated,
            "vrps_matched": self.vrps_matched,
            "vrps_unmatched_as": self.vrps_unmatched_as,
            "vrps_unmatched_length": self.vrps_unmatched_length,
            "authorised_origins": self.authorised_origins(),
        }


def from_validator_json(payload: dict[str, Any], *, validator: str) -> RpkiValidation:
    """Parse `rpki-validator.ripe.net/api/v1/validity/` — the primary source.

    Shape measured live 2026-08-03 (research R2/R9):
        {"validated_route": {"route": {"origin_asn","prefix"},
          "validity": {"state","reason","description",
                       "VRPs": {"matched","unmatched_as","unmatched_length"}}}}
    """
    route = (payload.get("validated_route") or {}).get("route") or {}
    validity = (payload.get("validated_route") or {}).get("validity") or {}
    vrps = validity.get("VRPs") or {}

    raw_state = str(validity.get("state", "")).strip().lower()
    state = WIRE_TO_STATE.get(raw_state)
    if state is None:
        raise ValueError(f"unrecognised RPKI state from {validator}: {raw_state!r}")

    raw_reason = validity.get("reason")
    reason = None
    if state is RpkiState.INVALID and raw_reason:
        try:
            reason = RpkiReason(str(raw_reason).strip().lower())
        except ValueError:
            reason = None

    return RpkiValidation(
        prefix=route.get("prefix", ""),
        origin_asn=route.get("origin_asn", ""),
        state=state,
        reason=reason,
        description=validity.get("description"),
        vrps_matched=list(vrps.get("matched") or []),
        vrps_unmatched_as=list(vrps.get("unmatched_as") or []),
        vrps_unmatched_length=list(vrps.get("unmatched_length") or []),
        validator=validator,
    )


def from_ripestat_json(
    payload: dict[str, Any], *, prefix: str, origin_asn: str, validator: str
) -> RpkiValidation:
    """Parse the RIPEstat fallback and translate its vocabulary. FR-004.

    RIPEstat says `unknown` for RFC 6811's NotFound and fuses state with reason
    into `invalid_asn` / `invalid_length`. Both are translated here, and
    `translated_from` records that it happened so the response can say so.
    """
    data = payload.get("data") or {}
    raw = str(data.get("status", "")).strip().lower()
    mapped = RIPESTAT_TO_STATE.get(raw)
    if mapped is None:
        raise ValueError(f"unrecognised RIPEstat RPKI status: {raw!r}")
    state, reason = mapped

    roas = list(data.get("validating_roas") or [])
    matched = [r for r in roas if str(r.get("validity", "")).lower() == "valid"]
    unmatched_as = [r for r in roas if "asn" in str(r.get("validity", "")).lower()]
    unmatched_len = [r for r in roas if "length" in str(r.get("validity", "")).lower()]

    return RpkiValidation(
        prefix=prefix,
        origin_asn=origin_asn,
        state=state,
        reason=reason,
        description=None,
        vrps_matched=matched,
        vrps_unmatched_as=unmatched_as,
        vrps_unmatched_length=unmatched_len,
        validator=validator,
        translated_from="RIPEstat",
    )
