"""iN2N Border routing: deterministic member selection (feature 056, US2).

Covers FR-011/FR-012/FR-021b. The async delegation over the channel is exercised
in test_member_delegation.py; here we assert the selection algorithm.
"""

import json

import pytest

from bgp.federation.risk import RiskManager, BASE_FLOOR
from bgp.federation.router import RiskRouter, NoCapableMember


@pytest.fixture
def border(manager):
    rm = RiskManager(manager, quarantine_threshold=5)
    rm.set_role("border", risk_name="risk", enabled_stacks="in2n",
                border_endpoint="10.0.0.1:1179")
    return rm


def _enroll(rm, name, specialty_names):
    """Provision + enroll a member scoped to base floor + given specialties."""
    scope = list(BASE_FLOOR) + [
        {"name": n, "type": "skill", "tier": "specialty"} for n in specialty_names]
    tok = rm.issue_token()["token"]
    cert, _ = RiskManager._generate_self_signed(name)
    rm.consume_token(tok, name, cert, scope=scope)
    return name


def test_single_match_routes_there(border):
    _enroll(border, "risk/cml", ["cml-lab-lifecycle"])
    r = RiskRouter(border)
    assert r.select_member("cml-lab-lifecycle")["member_id"] == "risk/cml"


def test_most_specific_specialist_wins(border):
    """A narrow specialist beats a broad claw that merely also lists the cap."""
    _enroll(border, "risk/cml", ["cml-lab-lifecycle"])                     # 1 specialty
    _enroll(border, "risk/generalist",
            ["cml-lab-lifecycle", "pyats-run", "meraki", "aci"])            # 4 specialties
    r = RiskRouter(border)
    assert r.select_member("cml-lab-lifecycle")["member_id"] == "risk/cml"


def test_tie_broken_lexicographically(border):
    """Equal specificity → smallest member_id (deterministic, repeatable)."""
    _enroll(border, "risk/bbb", ["shared-cap"])
    _enroll(border, "risk/aaa", ["shared-cap"])
    r = RiskRouter(border)
    assert r.select_member("shared-cap")["member_id"] == "risk/aaa"
    # repeatable
    assert r.select_member("shared-cap")["member_id"] == "risk/aaa"


def test_no_capable_member(border):
    _enroll(border, "risk/cml", ["cml-lab-lifecycle"])
    r = RiskRouter(border)
    with pytest.raises(NoCapableMember):
        r.select_member("nonexistent-cap")
    out = r.route("nonexistent-cap")
    assert out["error"] == "IN2N_ERR_NO_CAPABLE_MEMBER"


def test_quarantined_member_not_selected(border):
    _enroll(border, "risk/cml", ["cml-lab-lifecycle"])
    # quarantine it (threshold 5)
    for _ in range(5):
        border.record_auth_failure("risk/cml")
    r = RiskRouter(border)
    with pytest.raises(NoCapableMember):
        r.select_member("cml-lab-lifecycle")


def test_base_floor_capability_routes_but_specificity_excludes_it(border):
    """A base-floor capability is coverable; specificity still counts specialty only."""
    _enroll(border, "risk/cml", ["cml-lab-lifecycle"])
    r = RiskRouter(border)
    # self-status is base floor → covered
    assert r.select_member("self-status")["member_id"] == "risk/cml"
    # specialty count is 1, not 1+len(BASE_FLOOR)
    mem = border.get_member("risk/cml")
    assert border.specialty_count(mem["scope"]) == 1
