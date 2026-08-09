"""The distinctions, tested. Spec 081, SC-004/SC-005/SC-005a/SC-005b.

Runs with NO network. These are the guarantees the feature exists to make, and they
are structural, so they are provable without touching a public API.

Spec 080 shipped a null-fields bug past 24 passing tests because its tests asserted
on the envelope and not on content. Two of the tests here assert on **rendered
text** for exactly that reason: "the word 'invalid' must not appear in a not-found
result" is a claim about wording, and only a text assertion catches it.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "bgp-intel-mcp"))

import outcomes  # noqa: E402
from outcomes import Outcome, RpkiReason, RpkiState, RpkiValidation  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def make(state: RpkiState, reason: RpkiReason | None = None, **kw) -> RpkiValidation:
    return RpkiValidation(
        prefix=kw.pop("prefix", "192.0.66.0/24"),
        origin_asn=kw.pop("origin_asn", "AS64500"),
        state=state,
        reason=reason,
        validator="rpki-validator.ripe.net",
        **kw,
    )


def test_four_states_are_distinct() -> None:
    """FR-002. RFC 6811 has three states; the validator gives four outcomes because
    it separates the two reasons for invalidity. Collapsing them is prohibited."""
    combos = {
        (RpkiState.VALID, None),
        (RpkiState.INVALID, RpkiReason.AS),
        (RpkiState.INVALID, RpkiReason.LENGTH),
        (RpkiState.NOT_FOUND, None),
    }
    check("four distinct (state, reason) combinations exist", len(combos) == 4)
    check("invalid/as != invalid/length", RpkiReason.AS.value != RpkiReason.LENGTH.value)


def test_only_invalid_is_a_finding() -> None:
    """FR-003/FR-009. The heart of the feature."""
    check("valid is not a finding", make(RpkiState.VALID).is_finding is False)
    check("not_found is NOT a finding", make(RpkiState.NOT_FOUND).is_finding is False)
    check("invalid/as IS a finding", make(RpkiState.INVALID, RpkiReason.AS).is_finding is True)
    check("invalid/length IS a finding", make(RpkiState.INVALID, RpkiReason.LENGTH).is_finding is True)


def test_not_found_never_reads_as_a_problem() -> None:
    """SC-004 — the feature's central promise, asserted as text.

    Most of the internet has no ROA. If this result ever reads as a problem, the
    tool manufactures false incidents at scale."""
    blob = json.dumps(
        {"data": make(RpkiState.NOT_FOUND).to_dict(),
         "caveats": make(RpkiState.NOT_FOUND).caveats()}
    ).lower()
    for word in ("invalid", "suspicious", "unverified"):
        check(f"not_found output omits {word!r}", word not in blob,
              f"found {word!r} in a not_found result")
    check("not_found says it is normal", "normal" in blob)
    check("not_found says it is not a finding", "not a finding" in blob)


def test_rfc6811_vocabulary_is_reported() -> None:
    """FR-004/SC-005. A reader who knows RFC 6811 must not be misled by a source's
    private vocabulary."""
    d = make(RpkiState.NOT_FOUND).to_dict()
    check("not_found reports RFC 6811 'NotFound'", d["rfc6811_state"] == "NotFound", d["rfc6811_state"])
    check("valid reports 'Valid'", make(RpkiState.VALID).to_dict()["rfc6811_state"] == "Valid")


def test_corroboration_is_never_implied() -> None:
    """SC-005a/FR-007a. Both reachable validators are RIPE NCC Routinator, so
    claiming corroboration would be false."""
    v = make(RpkiState.VALID)
    blob = json.dumps({"data": v.to_dict(), "caveats": v.caveats()}).lower()
    check("corroborated is literally False", v.to_dict()["corroborated"] is False)
    for word in ("confirmed", "cross-checked", "independently verified"):
        check(f"output omits {word!r}", word not in blob, f"found {word!r}")
    check("output says 'not corroborated'", "not corroborated" in blob)
    check("output names the validator", "rpki-validator.ripe.net" in blob)


def test_validation_unavailable_is_not_not_found() -> None:
    """FR-007c/SC-005b. The core distinction, one level down — and the subtlest bug
    available here. 'Could not ask' is not 'there is no ROA'."""
    check("distinct outcome values",
          Outcome.VALIDATION_UNAVAILABLE.value != "not_found")
    check("VALIDATION_UNAVAILABLE is not an RpkiState",
          Outcome.VALIDATION_UNAVAILABLE.value not in {s.value for s in RpkiState})


def test_source_failure_is_not_no_record() -> None:
    """FR-011. A dead API must never look like an empty registry."""
    vals = {Outcome.NO_RECORD.value, Outcome.SOURCE_UNAVAILABLE.value,
            Outcome.SOURCE_REFUSED.value, Outcome.INPUT_REFUSED.value}
    check("four failure-ish outcomes remain distinct", len(vals) == 4, str(vals))


def test_invalid_names_what_the_roa_authorises() -> None:
    """FR-006. What makes an invalid actionable rather than merely alarming."""
    v = make(RpkiState.INVALID, RpkiReason.AS,
             vrps_unmatched_as=[{"asn": "AS15169", "prefix": "8.8.8.0/24", "max_length": "24"}])
    check("authorised origin extracted", v.authorised_origins() == ["AS15169"], str(v.authorised_origins()))
    check("caveat names the permitted AS", any("AS15169" in c for c in v.caveats()))
    ml = make(RpkiState.INVALID, RpkiReason.LENGTH,
              vrps_unmatched_length=[{"asn": "AS15169", "max_length": 24}])
    check("maxLength extracted", ml.max_lengths() == [24], str(ml.max_lengths()))
    check("length caveat mentions misconfiguration",
          any("misconfiguration" in c for c in ml.caveats()))


def test_ripestat_vocabulary_translation() -> None:
    """FR-004. RIPEstat says `unknown` for NotFound and fuses state with reason."""
    payload = {"data": {"status": "unknown", "validating_roas": []}}
    v = outcomes.from_ripestat_json(payload, prefix="4.0.0.0/9", origin_asn="AS3356",
                                   validator="stat.ripe.net")
    check("unknown -> not_found", v.state is RpkiState.NOT_FOUND, v.state.value)
    check("translation is recorded", v.translated_from == "RIPEstat", str(v.translated_from))
    check("translation is stated in caveats", any("translated" in c.lower() for c in v.caveats()))

    fused = {"data": {"status": "invalid_asn", "validating_roas": []}}
    v2 = outcomes.from_ripestat_json(fused, prefix="8.8.8.0/24", origin_asn="AS13335",
                                     validator="stat.ripe.net")
    check("invalid_asn -> (invalid, as)",
          v2.state is RpkiState.INVALID and v2.reason is RpkiReason.AS,
          f"{v2.state}/{v2.reason}")


def test_wire_spelling_is_accepted() -> None:
    """The deliberate hyphen/underscore split: the wire says `not-found`, the code
    says `not_found`. Normalising either would break something."""
    payload = {"validated_route": {"route": {"prefix": "4.0.0.0/9", "origin_asn": "AS3356"},
                                   "validity": {"state": "not-found", "VRPs": {}}}}
    v = outcomes.from_validator_json(payload, validator="rpki-validator.ripe.net")
    check("hyphenated wire form maps to NOT_FOUND", v.state is RpkiState.NOT_FOUND)
    check("enum member uses the underscore", RpkiState.NOT_FOUND.value == "not_found")


def main() -> int:
    print("RPKI distinction contract tests (no network required)")
    for fn in (
        test_four_states_are_distinct,
        test_only_invalid_is_a_finding,
        test_not_found_never_reads_as_a_problem,
        test_rfc6811_vocabulary_is_reported,
        test_corroboration_is_never_implied,
        test_validation_unavailable_is_not_not_found,
        test_source_failure_is_not_no_record,
        test_invalid_names_what_the_roa_authorises,
        test_ripestat_vocabulary_translation,
        test_wire_spelling_is_accepted,
    ):
        print(f"\n{fn.__name__}")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all outcome contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
