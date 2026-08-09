"""Contract tests for the response envelope. Spec 080, SC-002a.

Runs with NO appliance. That is the point: the guarantees this feature makes are
structural, so they are testable without a FortiGate — which proved its worth on
2026-08-01, when the lab was unavailable all day and the foundation still shipped.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "fortinet-mcp"))

# Keep audit writes out of the real GAIT trail during tests.
_AUDIT = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
os.environ["FORTINET_AUDIT_LOG"] = _AUDIT.name

import envelope  # noqa: E402
from envelope import Outcome, Plane, emit, unreachable  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def test_every_response_carries_plane_and_scope() -> None:
    """FR-005/FR-009: attribution is structural, not a convention."""
    r = emit(Plane.MANAGER, source="fmg-01", scope={"adom": "root"}, data={"x": 1}, tool="t")
    check("manager response carries plane", r["plane"] == "manager", r.get("plane"))
    check("manager response carries adom", r["scope"].get("adom") == "root", r.get("scope"))
    check("response carries a timestamp", bool(r.get("retrieved_at")))
    check("response carries its source", r.get("source") == "fmg-01")


def test_missing_scope_is_an_error_not_an_unqualified_result() -> None:
    """FR-009. An unqualified result reads as authoritative while being ambiguous —
    the more dangerous of the two failure modes, so it is refused."""
    r = emit(Plane.MANAGER, source="fmg-01", scope={}, data={"x": 1}, tool="t")
    check(
        "manager without adom -> scope_indeterminate",
        r["outcome"] == Outcome.SCOPE_INDETERMINATE.value,
        r["outcome"],
    )
    check("indeterminate scope drops the data", r["data"] is None, repr(r["data"]))

    r2 = emit(Plane.DEVICE, source="fgt-01", scope={"device": "fgt-01"}, data={}, tool="t")
    check(
        "device without vdom -> scope_indeterminate",
        r2["outcome"] == Outcome.SCOPE_INDETERMINATE.value,
        r2["outcome"],
    )

    r3 = emit(Plane.ANALYZER, source="faz-01", scope={"window_start": "a"}, data={}, tool="t")
    check(
        "analyzer without a full window -> scope_indeterminate",
        r3["outcome"] == Outcome.SCOPE_INDETERMINATE.value,
        r3["outcome"],
    )


def test_each_plane_requires_its_own_scope() -> None:
    ok_device = emit(
        Plane.DEVICE, source="fgt", scope={"device": "fgt-01", "vdom": "root"}, tool="t"
    )
    check("device with device+vdom is ok", ok_device["outcome"] == "ok", ok_device["outcome"])

    ok_analyzer = emit(
        Plane.ANALYZER,
        source="faz",
        scope={"window_start": "2026-08-01T00:00:00Z", "window_end": "2026-08-01T23:59:59Z"},
        tool="t",
    )
    check("analyzer with a window is ok", ok_analyzer["outcome"] == "ok", ok_analyzer["outcome"])


def test_unreachable_plane_is_named_and_carries_no_data() -> None:
    """FR-007: answer from what responded, say which plane you could not consult.
    Never fill a silent gap with another plane's data."""
    r = unreachable(Plane.DEVICE, "fgt-01", "connection refused", tool="t")
    check("unreachable -> plane_unreachable", r["outcome"] == Outcome.PLANE_UNREACHABLE.value)
    check("unreachable names the plane", "device" in r["message"], r.get("message", ""))
    check("unreachable carries no data", r["data"] is None)
    check("unreachable leaves a note", bool(r["notes"]))


def test_the_two_write_gates_are_distinct_values() -> None:
    """FR-020a. A single 'not authorised' would reproduce the exact conflation
    /speckit.analyze caught in spec 076 — human approval and an approved change
    record are different gates and neither substitutes for the other."""
    check(
        "approval and change-record refusals differ",
        Outcome.REFUSED_NO_APPROVAL.value != Outcome.REFUSED_NO_CHANGE_RECORD.value,
    )
    check(
        "read-only refusal is distinct from both",
        len({
            Outcome.REFUSED_READ_ONLY.value,
            Outcome.REFUSED_NO_APPROVAL.value,
            Outcome.REFUSED_NO_CHANGE_RECORD.value,
        }) == 3,
    )


def test_no_logs_is_not_the_same_as_unused() -> None:
    """FR-018b, and the same error class as spec 078's 'no advisories != not
    vulnerable' and spec 079's 'no probes != outage'."""
    check(
        "no_logs_in_window is its own outcome",
        Outcome.NO_LOGS_IN_WINDOW.value not in (Outcome.EMPTY_RESULT.value, Outcome.OK.value),
    )


def test_plane_cannot_be_spoofed_by_a_caller() -> None:
    """FR-006: `plane` is set by the module that made the call. It is a positional
    argument of a typed enum, not a free-text field a caller can populate."""
    check("Plane is a closed enum", {p.value for p in Plane} == {"manager", "device", "analyzer"})


def main() -> int:
    print("envelope contract tests (no appliance required)")
    for fn in (
        test_every_response_carries_plane_and_scope,
        test_missing_scope_is_an_error_not_an_unqualified_result,
        test_each_plane_requires_its_own_scope,
        test_unreachable_plane_is_named_and_carries_no_data,
        test_the_two_write_gates_are_distinct_values,
        test_no_logs_is_not_the_same_as_unused,
        test_plane_cannot_be_spoofed_by_a_caller,
    ):
        print(f"\n{fn.__name__}")
        fn()

    os.unlink(_AUDIT.name)
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all envelope contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
