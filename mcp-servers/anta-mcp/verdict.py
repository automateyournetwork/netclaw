"""Verdict model for anta-mcp — five outcomes, and the reclassification that makes them honest.

ANTA's own enum is: unset, success, failure, error, skipped.

NetClaw reports FIVE outcomes, splitting one of ANTA's:

    pass            <- success
    fail            <- failure   (the expectation genuinely did not hold)
    not_applicable  <- failure   (RECLASSIFIED: the feature is not configured at all)
    skipped         <- skipped
    error           <- error     (device unreachable / run broke)

WHY THE RECLASSIFICATION EXISTS. Measured against clab-mandible-veos1 during spec 098's Phase 0:

    VerifyBGPPeerCount -> failure
      "'show bgp summary vrf all' failed on veos1: BGP inactive"

BGP is not configured on that device. The honest answer is "not applicable" -- nothing was tested.
Counting it as a failure reports a BGP fault on a device with NO BGP AT ALL.

That is the same defect class this repository keeps finding: spec 091's Suricata reporting 0 alerts
with 0 signatures loaded, spec 094's BMC timeout, spec 096's count capped at 10,000, spec 095's
sites_sle returning count:1 with no metrics. An absence rendered as a finding, where the wrong
reading is the natural one.

THE RULE IS DELIBERATELY NARROW. A reclassification that is too eager hides real failures, which is
worse than the problem it solves. Only messages that clearly indicate an inactive feature or an
unsupported command are reclassified, the original message is ALWAYS preserved, and anything
uncertain stays `fail`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

PASS = "pass"
FAIL = "fail"
NOT_APPLICABLE = "not_applicable"
SKIPPED = "skipped"
ERROR = "error"

OUTCOMES = (PASS, FAIL, NOT_APPLICABLE, SKIPPED, ERROR)

# Narrow by design. Each pattern means "the box does not run this", never "the box is broken".
# Anything not matched stays a failure -- a missed reclassification is a cosmetic problem, a
# wrong one hides a fault.
_NOT_APPLICABLE_PATTERNS = (
    re.compile(r"\b(?:is\s+)?(?:not\s+)?(?:inactive|not\s+configured|not\s+enabled)\b", re.I),
    re.compile(r"\binvalid input\b", re.I),
    re.compile(r"\bnot supported\b", re.I),
    re.compile(r"\bunsupported\b", re.I),
    re.compile(r"\bno such (?:command|feature)\b", re.I),
)


class VerdictError(RuntimeError):
    """Raised when a caller tries to emit a summary that merges distinct outcomes."""


def classify(anta_status: str, messages: list[str] | None) -> tuple[str, str | None]:
    """Map an ANTA status to a NetClaw outcome.

    Returns (outcome, note). `note` explains a reclassification and is None otherwise.
    """
    text = " ".join(messages or [])
    status = (anta_status or "").lower()

    if status == "success":
        return PASS, None
    if status == "skipped":
        return SKIPPED, None
    if status == "error":
        return ERROR, None
    if status == "failure":
        for pat in _NOT_APPLICABLE_PATTERNS:
            if pat.search(text):
                return (
                    NOT_APPLICABLE,
                    "feature not configured or command unsupported on this device - "
                    "nothing was tested",
                )
        return FAIL, None
    # 'unset' or anything unrecognised: do not guess a healthy answer.
    return ERROR, f"unrecognised ANTA status {anta_status!r}"


def summarise(results: list[dict]) -> dict:
    """Five separate counts. Never a percentage.

    A health percentage is refused rather than computed: passed/total is meaningless when
    not_applicable and skipped sit in the denominator. Forty tests of which thirty are not
    applicable is not "25% healthy" -- it is ten tests and thirty non-answers.
    """
    counts = {o: 0 for o in OUTCOMES}
    for r in results:
        v = r.get("verdict")
        if v not in counts:
            raise VerdictError(f"unknown verdict {v!r} - the outcome set is closed")
        counts[v] += 1

    return {
        "passed": counts[PASS],
        "failed": counts[FAIL],
        "not_applicable": counts[NOT_APPLICABLE],
        "skipped": counts[SKIPPED],
        "errored": counts[ERROR],
        "total": sum(counts.values()),
    }


def health_percentage(*_args, **_kwargs):
    """Deliberately unavailable.

    Kept as a raising stub so the refusal is discoverable at the call site rather than being an
    absence someone reimplements locally.
    """
    raise VerdictError(
        "a health percentage is not emitted: passed/total is meaningless with "
        "not_applicable and skipped in the denominator. Report the five counts."
    )


def envelope(device: str, results: list[dict], *, tls_verified: bool) -> dict:
    """Wrap results with attribution. There is no path that omits it (FR-012).

    tls_verified is always present. A silent TLS downgrade is unacceptable; a disclosed one is
    workable -- the same discipline spec 094 applied to BMC certificates.
    """
    if not device:
        raise VerdictError("a result must name the device that answered")
    return {
        "device": device,
        "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tls_verified": bool(tls_verified),
        "summary": summarise(results),
        "results": results,
    }


def unreachable(device: str, reason: str, *, tls_verified: bool) -> dict:
    """An unreachable device is an ERROR about the device -- never a set of failing tests.

    Spec 094's box-vs-network distinction in a new place: failing to reach a device establishes
    nothing about whether its state is correct.
    """
    return {
        "device": device,
        "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tls_verified": bool(tls_verified),
        "outcome": ERROR,
        "reason": reason,
        "results": [],
        "summary": summarise([]),
        "caveat": "NOT A TEST FAILURE - the device could not be reached, so nothing was tested. "
                  "This says nothing about whether its configuration is correct.",
    }


def no_tests_selected(selector: str) -> dict:
    """An empty selection is not a passing run (FR-006)."""
    return {
        "outcome": "no_tests_selected",
        "selector": selector,
        "results": [],
        "summary": summarise([]),
        "caveat": "NOT A PASS - no test matched the selection, so nothing was tested. "
                  "Use anta_list_tests to find valid test names or categories.",
    }
