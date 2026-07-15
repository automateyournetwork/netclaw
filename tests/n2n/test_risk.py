"""iN2N risk role model + provisioning (feature 056, US1/US3).

Covers FR-002/003/004/005(role flag)/019/020/021/021a/021b/022.
"""

import json

import pytest

from bgp.federation.risk import RiskManager, BASE_FLOOR, STATE_PROVISIONED


@pytest.fixture
def rm(manager):
    return RiskManager(manager, quarantine_threshold=5)


# ---- role model (FR-002/003/004) --------------------------------------

def test_default_is_standalone(rm):
    """A fresh claw is standalone — a 'risk of one', behaves as pre-056 (FR-004)."""
    assert rm.is_standalone()
    assert rm.role() == "standalone"
    assert rm.get_risk()["risk_name"] is None


def test_set_border_and_member_roles(rm):
    rm.set_role("border", risk_name="johns-risk", description="lab fleet",
                enabled_stacks="both")
    r = rm.get_risk()
    assert r["role"] == "border" and r["risk_name"] == "johns-risk"
    assert rm.is_border()


def test_invalid_role_rejected(rm):
    with pytest.raises(ValueError):
        rm.set_role("overlord", risk_name="x")


def test_single_border_enforcement(rm):
    """FR-003: a claw cannot be Border of two different risks."""
    rm.set_role("border", risk_name="johns-risk", enabled_stacks="both")
    with pytest.raises(ValueError):
        rm.set_role("border", risk_name="a-different-risk", enabled_stacks="both")
    # Re-affirming the SAME risk is idempotent, not an error.
    rm.set_role("border", risk_name="johns-risk", enabled_stacks="in2n")
    assert rm.get_risk()["enabled_stacks"] == "in2n"


def test_member_role_gates_external_stack(rm):
    """FR-005/014: a Member never runs eN2N; standalone still does."""
    rm.set_role("member", risk_name="johns-risk", border_endpoint="127.0.0.1:9",
                self_member_id="johns-risk/cml")
    assert not rm.stack_enabled("en2n")
    assert not rm.is_border()
    # Standalone remains eN2N-capable as before (backwards compat).
    rm2 = RiskManager(rm.m)
    rm.set_role("standalone")
    assert rm.stack_enabled("en2n")


def test_border_stack_gating(rm):
    rm.set_role("border", risk_name="johns-risk", enabled_stacks="in2n")
    assert rm.stack_enabled("in2n")
    assert not rm.stack_enabled("en2n")
    rm.set_role("border", risk_name="johns-risk", enabled_stacks="both")
    assert rm.stack_enabled("en2n") and rm.stack_enabled("in2n")


# ---- provisioning + base floor (FR-019/020/021/021a/021b/022) ---------

def test_profile_provisions_scoped_member_with_base_floor(rm):
    rm.set_role("border", risk_name="johns-risk", enabled_stacks="in2n",
                border_endpoint="10.0.0.1:1179")
    out = rm.add_member("cml", profile="cml",
                        specialty=[{"name": "cml-lab-lifecycle", "type": "skill"}])
    assert out["member_id"] == "johns-risk/cml"
    names = {e["name"] for e in out["scope"]}
    # specialty present
    assert "cml-lab-lifecycle" in names
    # base floor present and non-removable
    for base in BASE_FLOOR:
        assert base["name"] in names
    # a single-use token + join instructions returned (member is a separate install)
    assert out["enrollment_token"].startswith("in2n_")
    assert out["join"]["N2N_ROLE"] == "member"
    # row provisioned, not yet pinned
    mem = rm.get_member("johns-risk/cml")
    assert mem["state"] == STATE_PROVISIONED and mem["pinned_key"] is None


def test_custom_member_arbitrary_subset(rm):
    rm.set_role("border", risk_name="r", enabled_stacks="in2n")
    out = rm.add_member("mix", specialty=["skill-a", "skill-b"])
    names = {e["name"] for e in out["scope"] if e["tier"] == "specialty"}
    assert names == {"skill-a", "skill-b"}


def test_specialty_count_excludes_base_floor(rm):
    """FR-021b: base floor must NOT count toward routing specificity."""
    rm.set_role("border", risk_name="r", enabled_stacks="in2n")
    out = rm.add_member("cml", profile="cml", specialty=[{"name": "cml-lab-lifecycle"}])
    assert rm.specialty_count(out["scope"]) == 1        # only the specialty entry
    assert len(out["scope"]) == len(BASE_FLOOR) + 1     # base floor is in the scope
    # a broader claw with more specialties is "less specific"
    out2 = rm.add_member("broad", specialty=["a", "b", "c", "cml-lab-lifecycle"])
    assert rm.specialty_count(out2["scope"]) == 4


def test_covers_and_in_scope(rm):
    rm.set_role("border", risk_name="r", enabled_stacks="in2n")
    rm.add_member("cml", profile="cml", specialty=[{"name": "cml-lab-lifecycle"}])
    mem = rm.get_member("r/cml")
    assert rm.covers(mem, "cml-lab-lifecycle")
    assert rm.covers(mem, "self-status")          # base floor is in scope
    assert not rm.covers(mem, "pyats-run")


def test_add_member_requires_border(rm):
    rm.set_role("member", risk_name="r", border_endpoint="127.0.0.1:9")
    with pytest.raises(ValueError):
        rm.add_member("x", profile="cml")
