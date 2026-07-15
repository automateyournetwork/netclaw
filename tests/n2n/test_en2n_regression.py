"""Frozen eN2N core is unchanged by iN2N (feature 056, US4).

Guards FR-014/FR-016/FR-018 and SC-009: a Member never runs the external stack,
a peer never sees member data, and the eN2N framing/handlers are untouched.
"""

import json

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp import constants


def _svc(base, name="claw"):
    mgr = FederationManager(base_dir=str(base))
    return FederationService(local_as=65001, router_id="4.4.4.4", display_name=name, manager=mgr)


def test_ncfed_framing_constants_unchanged():
    """iN2N must not have altered the frozen NCFED wire framing (FR-018)."""
    assert constants.NCFED_MAGIC == b"NCFED"
    assert constants.NCFED_FRAME_HEADER_SIZE == 5
    assert constants.NCFED_MAX_PAYLOAD == 65536
    # iN2N uses a DISTINCT magic so eN2N discrimination is unaffected.
    assert constants.IN2N_MAGIC != constants.NCFED_MAGIC


def test_en2n_handlers_present_alongside_in2n(tmp_path):
    """The eN2N handler set is intact even though iN2N handlers now exist."""
    svc = _svc(tmp_path / "a")
    for m in ("n2n/hello", "n2n/consent_state", "n2n/inventory", "n2n/tools/call",
              "n2n/tasks/submit", "n2n/chat/open"):
        assert m in svc.handlers, f"frozen eN2N handler {m} missing"
    svc.manager.close()


def test_member_refuses_outbound_en2n(tmp_path):
    """FR-014: a Member role does not open external channels."""
    import asyncio
    svc = _svc(tmp_path / "m")
    svc.risk.set_role("member", risk_name="r", border_endpoint="127.0.0.1:9",
                      self_member_id="r/cml")
    # lower AS would normally dial, but a member must not federate externally
    asyncio.run(svc.open_channel(65099, "9.9.9.9", "127.0.0.1", 1))
    assert svc.channels == {}
    assert not svc._en2n_allowed()
    svc.manager.close()


def test_border_and_standalone_allow_en2n(tmp_path):
    svc = _svc(tmp_path / "b")
    svc.risk.set_role("border", risk_name="r", enabled_stacks="both")
    assert svc._en2n_allowed()
    svc.risk.set_role("standalone")
    assert svc._en2n_allowed()
    svc.manager.close()


def test_peer_inventory_never_leaks_members(tmp_path):
    """FR-016/SC-005: the eN2N inventory a peer receives contains no member-level
    identities/topology — the risk presents only the Border identity."""
    svc = _svc(tmp_path / "border")
    # Isolate the Border's own skills so the aggregate is deterministic (the real
    # repo already ships a cml-lab-lifecycle skill).
    svc.inventory.skills_dir = tmp_path / "empty-skills"
    svc.risk.set_role("border", risk_name="johns-risk", enabled_stacks="both")
    # Provision members — their IDs must NOT appear, but their caps aggregate up.
    svc.risk.add_member("cml", profile=None, specialty=[{"name": "cml-lab-lifecycle"}])
    svc.risk.add_member("pyats", profile=None, specialty=[{"name": "pyats-run"}])
    inv = svc.inventory.build("as65007-7.7.7.7")   # what a peer would receive
    blob = json.dumps(inv)
    # member IDs / topology never leak (FR-016)
    assert "johns-risk/cml" not in blob
    assert "johns-risk/pyats" not in blob
    assert "member" not in {k.lower() for k in inv.keys()}
    # ...but the member SPECIALTY capabilities ARE advertised as risk-level caps,
    # attributed to the risk (aggregate under one identity — the chosen behavior).
    names = {s["name"] for s in inv["skills"]}
    assert "cml-lab-lifecycle" in names
    assert "pyats-run" in names
    agg = [s for s in inv["skills"] if s.get("risk_aggregate")]
    assert {"cml-lab-lifecycle", "pyats-run"} <= {s["name"] for s in agg}
    svc.manager.close()
