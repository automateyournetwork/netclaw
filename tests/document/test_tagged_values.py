"""The typed vocabulary. Spec 082, FR-001/002/005c/007, SC-002/003.

These are the guarantees the feature exists to make. They are structural, so they are
provable without writing a file — but note that three of the checks below assert on
RENDERED TEXT, because "a missing value must not read as data" is a claim about wording,
and only a text assertion catches a wording bug. Spec 081 learned that the same way.
"""

from __future__ import annotations

from _harness import FAILURES, check, run  # noqa: F401

from outcomes import (  # noqa: E402
    Outcome,
    ValueRefused,
    find_disagreements,
    parse_tagged,
    render_as_of,
    render_source,
    render_tagged,
)


def _refusal(raw, path="field"):
    try:
        parse_tagged(raw, path)
    except ValueRefused as exc:
        return exc
    return None


def test_value_requires_a_source():
    exc = _refusal({"v": 5})
    check("a value without 'src' is refused", exc is not None, "it was accepted")
    if exc:
        check(
            "the refusal is typed as refused_unattributed",
            exc.outcome is Outcome.REFUSED_UNATTRIBUTED,
            f"got {exc.outcome}",
        )
        check("the message names the field path", "field" in str(exc), str(exc)[:80])
    check("an empty src is refused", _refusal({"v": 5, "src": "   "}) is not None, "accepted")
    ok = parse_tagged({"v": 5, "src": "fgt_x"}, "field")
    check("a value with a src is accepted", ok.kind == "value" and ok.value == 5)


def test_bare_scalars_are_refused():
    for raw in (5, "up", True, None, ["a"]):
        exc = _refusal(raw)
        check(
            f"bare {type(raw).__name__} {raw!r} is refused",
            exc is not None and exc.outcome is Outcome.REFUSED_UNTYPED,
            "accepted — a caller could express missing data as a blank",
        )
    exc = _refusal(5)
    if exc:
        check("the refusal shows the accepted shapes", "unavailable" in str(exc), str(exc)[:80])


def test_exactly_one_discriminator():
    check("no discriminator is refused", _refusal({"src": "x"}) is not None, "accepted")
    check(
        "two discriminators are refused",
        _refusal({"v": 1, "src": "x", "unavailable": "y"}) is not None,
        "accepted",
    )


def test_gaps_require_a_reason():
    for tag in ("unavailable", "failed"):
        check(
            f"'{tag}' with an empty reason is refused",
            _refusal({tag: "   "}) is not None,
            "accepted — an unavailable with no reason is a blank wearing a label",
        )
        ok = parse_tagged({tag: "device did not answer"}, "f")
        check(f"'{tag}' with a reason is accepted", ok.kind == tag and ok.is_gap)


def test_as_of_must_be_iso():
    check("non-ISO as_of is refused", _refusal({"v": 1, "src": "x", "as_of": "yesterday"}) is not None)
    for good in ("2026-08-03", "2026-08-03T14:02:00Z", "2026-08-03T14:02:00+02:00"):
        check(f"ISO as_of {good!r} is accepted", _refusal({"v": 1, "src": "x", "as_of": good}) is None)


def test_the_three_shapes_render_differently():
    """SC-002 / SC-003. Asserted on the RENDERED TEXT, not on the type."""
    empty = render_tagged(parse_tagged({"v": "", "src": "x"}, "f"))
    unav = render_tagged(parse_tagged({"unavailable": "device did not answer"}, "f"))
    fail = render_tagged(parse_tagged({"failed": "connection refused"}, "f"))

    check("three shapes render to three distinct strings", len({empty, unav, fail}) == 3,
          f"{empty!r} {unav!r} {fail!r}")
    check("empty-value says the source was consulted", empty == "(empty)", empty)
    check("unavailable is labelled NOT AVAILABLE", unav.startswith("NOT AVAILABLE"), unav)
    check("failed is labelled RETRIEVAL FAILED", fail.startswith("RETRIEVAL FAILED"), fail)
    check("unavailable carries its reason", "did not answer" in unav, unav)
    check("failed carries its reason", "connection refused" in fail, fail)

    forbidden = {"", " ", "-", "--", "n/a", "na", "none", "null", "0", "tbd", "unknown"}
    for label, text in (("unavailable", unav), ("failed", fail), ("empty", empty)):
        check(
            f"{label} does not render as a plausible blank",
            text.strip().lower() not in forbidden,
            f"rendered as {text!r}, which reads as data",
        )


def test_null_is_not_missing():
    """A source reporting null is a fact; a field with no source is not."""
    got = render_tagged(parse_tagged({"v": None, "src": "x"}, "f"))
    check("an explicit null renders as (null), not as blank", got == "(null)", got)
    check("(null) differs from NOT AVAILABLE", got != render_tagged(parse_tagged({"unavailable": "r"}, "f")))


def test_source_and_as_of_render_visibly():
    tv = parse_tagged({"v": 1, "src": "fgt_list_interfaces", "device": "fgt-01",
                       "as_of": "2026-08-03T14:02:00Z"}, "f")
    src = render_source(tv)
    check("source names the tool", "fgt_list_interfaces" in src, src)
    check("source names the device", "fgt-01" in src, src)
    check("as_of is the SOURCE's time", render_as_of(tv) == "2026-08-03T14:02:00Z", render_as_of(tv))
    no_age = parse_tagged({"v": 1, "src": "x"}, "f")
    check(
        "a source with no as_of says so rather than borrowing the generation time",
        render_as_of(no_age) == "(not stated by source)",
        render_as_of(no_age),
    )


def test_disagreement_detection():
    a = parse_tagged({"v": "fgt-01", "src": "fgt_system_status"}, "f")
    b = parse_tagged({"v": "fgt-01-alt", "src": "netbox_get_device"}, "f")
    same = parse_tagged({"v": "fgt-01", "src": "netbox_get_device"}, "f")

    found = find_disagreements([("Hostname", a), ("Hostname", b)])
    check("differing values from two sources are flagged", len(found) == 1, str(found))
    if found:
        cav = found[0].caveat()
        check("the caveat names both sources", "fgt_system_status" in cav and "netbox_get_device" in cav, cav)
        check("the caveat says NetClaw did not reconcile", "not reconciled" in cav, cav)

    check("agreeing sources are not flagged", find_disagreements([("Hostname", a), ("Hostname", same)]) == [])
    check("one source alone is not a disagreement", find_disagreements([("Hostname", a)]) == [])


TESTS = [
    test_value_requires_a_source,
    test_bare_scalars_are_refused,
    test_exactly_one_discriminator,
    test_gaps_require_a_reason,
    test_as_of_must_be_iso,
    test_the_three_shapes_render_differently,
    test_null_is_not_missing,
    test_source_and_as_of_render_visibly,
    test_disagreement_detection,
]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "tagged value"))
