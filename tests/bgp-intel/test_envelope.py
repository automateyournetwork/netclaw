"""Provenance and audit at the chokepoint. Spec 081, SC-012/SC-013/SC-014, FR-022.

No network. These assert the two guarantees that make merged multi-source answers
usable at all: every result names its source, and every operation leaves a trail.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "bgp-intel-mcp"))

_AUDIT = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
os.environ["BGP_INTEL_AUDIT_LOG"] = _AUDIT.name

import envelope  # noqa: E402
from envelope import ProvenanceError  # noqa: E402
from outcomes import Outcome  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def records() -> list[dict]:
    with open(_AUDIT.name, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def reset() -> None:
    open(_AUDIT.name, "w").close()


def test_every_response_names_its_source() -> None:
    """FR-019/SC-012. 'The registry says' is not attributable — RIRs differ in
    freshness and completeness, PeeringDB is self-reported, RIPEstat sees only its
    own collectors."""
    r = envelope.emit(source="rdap.db.ripe.net", tool="t", data={"x": 1})
    check("source present", r["source"] == "rdap.db.ripe.net")
    check("retrieved_at present", bool(r["retrieved_at"]))
    check("outcome present", r["outcome"] == "ok")
    check("caveats is a list", isinstance(r["caveats"], list))


def test_sourceless_response_is_an_error() -> None:
    """FR-019. An unattributed answer is not a weaker answer; it is unusable."""
    for bad in ("", "   ", None):
        try:
            envelope.emit(source=bad, tool="t", data={})  # type: ignore[arg-type]
            check(f"source={bad!r} rejected", False, "no exception raised")
        except ProvenanceError:
            check(f"source={bad!r} rejected", True)


def test_merged_answers_carry_per_element_provenance() -> None:
    """FR-021/SC-013. One collective citation across a merged answer is not
    attribution — a reader cannot tell which part came from where."""
    reset()
    a = envelope.emit(source="rdap.db.ripe.net", tool="t", data={"holder": "X"})
    b = envelope.emit(source="peeringdb.com", tool="t", data={"name": "Y"})
    m = envelope.merged(tool="resource_report", sections={"registry": a, "peering": b})
    check("each section keeps its own source",
          m["sections"]["registry"]["source"] != m["sections"]["peering"]["source"])
    check("sources_consulted lists both",
          set(m["sources_consulted"]) == {"rdap.db.ripe.net", "peeringdb.com"},
          str(m["sources_consulted"]))


def test_failed_section_is_named_inside_the_report() -> None:
    """FR-011. A failure inside a composite is reported as a failure, and the
    report does not fail wholesale."""
    dead = envelope.unavailable(source="stat.ripe.net", tool="t", query={},
                                reason="timeout")
    ok = envelope.emit(source="peeringdb.com", tool="t", data={})
    m = envelope.merged(tool="resource_report", sections={"routing": dead, "peering": ok})
    joined = " ".join(m["caveats"]).lower()
    check("failed section named in caveats", "routing" in joined, joined[:120])
    check("caveat says failure not absence", "not as absence" in joined, joined[:160])


def test_source_failure_never_reads_as_no_record() -> None:
    """FR-011. A dead API must not look like an empty registry."""
    r = envelope.unavailable(source="rdap.arin.net", tool="t", query={}, reason="reset")
    check("outcome is a failure", r["outcome"] == Outcome.SOURCE_UNAVAILABLE.value)
    check("failure names the source", "rdap.arin.net" in r["message"])
    joined = " ".join(r["caveats"]).lower()
    check("caveat distinguishes failure from absence",
          "not evidence that no record exists" in joined, joined[:140])


def test_local_refusal_makes_no_request() -> None:
    """FR-028. Refusing locally is a disclosure control — the source is this
    server precisely because nothing left the machine."""
    r = envelope.refused(tool="registry_lookup", query={"resource": "10.0.0.1"},
                         reason="RFC1918")
    check("outcome is input_refused", r["outcome"] == Outcome.INPUT_REFUSED.value)
    check("source is local", "local" in r["source"])
    check("caveat says no request was made",
          any("no request" in c.lower() for c in r["caveats"]))


def test_cache_reports_age() -> None:
    """FR-026b. An operator chasing a fast-moving RPKI change must be able to tell
    whether they are looking at a fresh answer."""
    r = envelope.emit(source="s", tool="t", data={}, cached=True, cache_age_seconds=42.44)
    check("cached flag set", r["cached"] is True)
    check("age reported and rounded", r["cache_age_seconds"] == 42.4, str(r["cache_age_seconds"]))
    fresh = envelope.emit(source="s", tool="t", data={})
    check("uncached reports no age", fresh["cache_age_seconds"] is None)


def test_every_operation_is_audited() -> None:
    """FR-022/SC-014, Principle IV. Including refusals and failures."""
    reset()
    envelope.emit(source="s1", tool="rpki_validate", data={})
    envelope.refused(tool="registry_lookup", query={"resource": "127.0.0.1"}, reason="loopback")
    envelope.unavailable(source="s2", tool="peering_network", query={}, reason="timeout")
    rs = records()
    check("three operations -> three records", len(rs) == 3, f"got {len(rs)}")
    outs = {r["outcome"] for r in rs}
    check("refusal and failure both audited",
          {"input_refused", "source_unavailable"} <= outs, str(outs))
    check("records name the component",
          all(r["component"] == "bgp-intel-mcp" for r in rs))
    check("records carry cached flag", all("cached" in r for r in rs))


def main() -> int:
    print("envelope + audit contract tests (no network required)")
    for fn in (
        test_every_response_names_its_source,
        test_sourceless_response_is_an_error,
        test_merged_answers_carry_per_element_provenance,
        test_failed_section_is_named_inside_the_report,
        test_source_failure_never_reads_as_no_record,
        test_local_refusal_makes_no_request,
        test_cache_reports_age,
        test_every_operation_is_audited,
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
