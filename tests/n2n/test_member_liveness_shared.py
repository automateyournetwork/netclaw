"""One definition of member liveness, used by every reporting call site.

Three call sites each computed liveness inline and drifted into checking only
`member_channels` — the AGENT-member registry — so every connected PHONE was
reported down (an edge member's channel lives in `edge_channels`). Two were
fixed in ec7acdd, a third in the health_report() fix. This pins the shared
helper so there is never a fourth.

`heartbeat_age_s` is part of the contract because `state` alone misleads on a
phone: it is written on connect/disconnect, and a phone reconnects constantly
(82 deregistrations and 94 dial-ins in one day on the live Border), so two reads
seconds apart can honestly disagree. Reported as "endpoints contradicting each
other" in a defect report; the heartbeat age is what actually distinguishes
"briefly between sockets" from "gone".
"""
import json
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "mcp-servers", "protocol-mcp"))


def _svc(member_channels=(), edge_channels=()):
    from bgp.federation.service import FederationService
    s = object.__new__(FederationService)
    s.member_channels = {k: object() for k in member_channels}
    s.edge_channels = {k: object() for k in edge_channels}
    return s


def _member(member_id, health=None):
    return {"member_id": member_id,
            "health": json.dumps(health) if health is not None else None}


def test_a_connected_phone_is_live():
    """The original bug: an edge channel lives in edge_channels, so a phone
    checked against member_channels alone read as down while connected."""
    s = _svc(edge_channels=["risk/phone"])
    assert s.member_liveness(_member("risk/phone"))["live"] is True


def test_a_connected_agent_member_is_live():
    s = _svc(member_channels=["johns-risk/pyats"])
    assert s.member_liveness(_member("johns-risk/pyats"))["live"] is True


def test_a_member_in_neither_registry_is_not_live():
    s = _svc()
    assert s.member_liveness(_member("risk/phone"))["live"] is False


def test_edge_and_agent_registries_are_both_consulted():
    """A regression that dropped either registry would pass a test that only
    covered the other."""
    s = _svc(member_channels=["a"], edge_channels=["b"])
    assert s.member_liveness(_member("a"))["live"] is True
    assert s.member_liveness(_member("b"))["live"] is True


def test_heartbeat_age_is_reported():
    s = _svc(edge_channels=["risk/phone"])
    out = s.member_liveness(_member("risk/phone",
                                    {"last_heartbeat": time.time() - 42}))
    assert out["heartbeat_age_s"] == pytest.approx(42, abs=2)


def test_a_stale_heartbeat_on_a_live_channel_is_visible():
    """This combination is exactly what looked like a lie to an operator:
    state/live say one thing, the heartbeat is minutes old."""
    s = _svc(edge_channels=["risk/phone"])
    out = s.member_liveness(_member("risk/phone",
                                    {"last_heartbeat": time.time() - 600}))
    assert out["live"] is True
    assert out["heartbeat_age_s"] > 500, "staleness must be visible, not hidden"


def test_missing_or_malformed_health_does_not_raise():
    s = _svc(edge_channels=["risk/phone"])
    for health in (None, {}, {"last_heartbeat": None}, {"last_heartbeat": "nonsense"}):
        out = s.member_liveness(_member("risk/phone", health))
        assert out["heartbeat_age_s"] is None
        assert out["live"] is True, "a bad health blob must not affect liveness"


def test_health_that_is_not_json_does_not_raise():
    s = _svc(edge_channels=["risk/phone"])
    out = s.member_liveness({"member_id": "risk/phone", "health": "{not json"})
    assert out["heartbeat_age_s"] is None


def test_heartbeat_age_is_never_negative():
    """Clock skew must not produce a negative age an operator has to interpret."""
    s = _svc(edge_channels=["risk/phone"])
    out = s.member_liveness(_member("risk/phone",
                                    {"last_heartbeat": time.time() + 120}))
    assert out["heartbeat_age_s"] >= 0


def test_no_reporting_call_site_computes_liveness_inline():
    """Guard against a fourth divergent copy appearing."""
    root = os.path.join(os.path.dirname(__file__), "..", "..",
                        "mcp-servers", "protocol-mcp")
    inline = "in fed.member_channels"
    with open(os.path.join(root, "bgp-daemon-v2.py")) as f:
        daemon = f.read()
    assert inline not in daemon, (
        "a daemon endpoint is computing liveness inline again — use "
        "FederationService.member_liveness() so the endpoints cannot drift")

    with open(os.path.join(root, "bgp", "federation", "service.py")) as f:
        svc = f.read()
    # Exactly one occurrence: the definition inside member_liveness itself.
    assert svc.count("in self.member_channels or mid in self.edge_channels") == 1
