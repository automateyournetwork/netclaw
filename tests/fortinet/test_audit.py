"""Contract tests for the GAIT audit trail. Spec 080, FR-023, SC-011.

Principle IV is NON-NEGOTIABLE: "No operation MAY execute silently — all actions
MUST produce an audit record."

These tests exist because `/speckit.analyze` found FR-023 with a *verification*
task and no *implementation* task — the identical defect it caught in spec 076,
where Principle III was recorded as "inherited from the existing approval path"
with nothing behind it. Verifying an unimplemented guarantee passes by accident.

Runs with NO appliance.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "fortinet-mcp"))

_AUDIT = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
os.environ["FORTINET_AUDIT_LOG"] = _AUDIT.name

from envelope import Outcome, Plane, emit, unreachable  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def read_records() -> list[dict]:
    with open(_AUDIT.name, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def reset() -> None:
    open(_AUDIT.name, "w").close()


def test_every_response_emits_exactly_one_record() -> None:
    reset()
    emit(Plane.MANAGER, source="fmg", scope={"adom": "root"}, data={"a": 1}, tool="fmg_list_adoms")
    records = read_records()
    check("one response -> one record", len(records) == 1, f"got {len(records)}")
    if records:
        r = records[0]
        check("record names the tool", r.get("tool") == "fmg_list_adoms", r.get("tool"))
        check("record names the plane", r.get("plane") == "manager", r.get("plane"))
        check("record carries the outcome", r.get("outcome") == "ok", r.get("outcome"))
        check("record carries a timestamp", bool(r.get("ts")))
        check("record identifies the component", r.get("component") == "fortinet-mcp")


def test_refusals_are_audited_too() -> None:
    """The case most likely to be missed. A refused write is an operation that
    happened and must leave a trail — arguably more important than a successful
    read, since it records an attempt."""
    reset()
    emit(
        Plane.MANAGER,
        source="fmg",
        scope={"adom": "root"},
        outcome=Outcome.REFUSED_NO_CHANGE_RECORD,
        message="no approved change record",
        tool="fmg_install_package",
    )
    emit(
        Plane.MANAGER,
        source="fmg",
        scope={"adom": "root"},
        outcome=Outcome.REFUSED_NO_APPROVAL,
        message="no human approval",
        tool="fmg_install_package",
    )
    records = read_records()
    check("both refusals audited", len(records) == 2, f"got {len(records)}")
    outcomes = {r.get("outcome") for r in records}
    check(
        "refusal outcomes recorded distinctly",
        outcomes == {"refused_no_change_record", "refused_no_approval"},
        str(outcomes),
    )


def test_unreachable_plane_is_audited() -> None:
    reset()
    unreachable(Plane.DEVICE, "fgt-01", "connection refused", tool="fgt_system_status")
    records = read_records()
    check("unreachable audited", len(records) == 1, f"got {len(records)}")
    if records:
        check("outcome recorded", records[0].get("outcome") == "plane_unreachable")


def test_no_credential_reaches_the_audit_trail() -> None:
    """FR-023 with FR-029. The audit trail is a disclosure surface too."""
    reset()
    emit(
        Plane.DEVICE,
        source="fgt",
        scope={"device": "fgt-01", "vdom": "root", "api_token": "SUPERSECRET123"},
        data={"password": "hunter2"},
        tool="fgt_system_status",
    )
    raw = open(_AUDIT.name, encoding="utf-8").read()
    check("token value absent from trail", "SUPERSECRET123" not in raw)
    check("scope secret redacted", "<redacted>" in raw, raw[:200])
    check(
        "payload not written to the trail at all",
        "hunter2" not in raw,
        "an audit trail records the shape of an operation, not its data",
    )


def test_scope_and_source_are_recorded() -> None:
    reset()
    emit(
        Plane.ANALYZER,
        source="faz-01",
        scope={"window_start": "2026-08-01T00:00:00Z", "window_end": "2026-08-01T12:00:00Z"},
        outcome=Outcome.NO_LOGS_IN_WINDOW,
        message="no logs matched",
        tool="faz_policy_activity",
    )
    records = read_records()
    if check("record written", bool(records)) is None and records:
        r = records[0]
        check("source recorded", r.get("source") == "faz-01", r.get("source"))
        check("window recorded in scope", "window_start" in (r.get("scope") or {}), str(r.get("scope")))
        check(
            "no_logs_in_window preserved, not flattened to ok",
            r.get("outcome") == "no_logs_in_window",
            r.get("outcome"),
        )


def main() -> int:
    print("GAIT audit contract tests (no appliance required)")
    for fn in (
        test_every_response_emits_exactly_one_record,
        test_refusals_are_audited_too,
        test_unreachable_plane_is_audited,
        test_no_credential_reaches_the_audit_trail,
        test_scope_and_source_are_recorded,
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
    print("all audit contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
