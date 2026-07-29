"""Regression: `health_report()` (the /n2n/faults source) computed member
liveness only from `fed.member_channels`, the agent-member registry. An edge
(phone) member's channel lives in `fed.edge_channels` instead, so a connected
phone was reported `state: down` — and because the DB row is `active` while
`live` was False, it also tripped `member_fault`, making the WHOLE risk report
`fault_class: "member"` when nothing was wrong.

This is the same bug class already fixed in commit ec7acdd for GET /n2n/members
and GET /n2n/members/health (see test_members_endpoint_edge_liveness.py); the
third call site, health_report(), was missed. Observed live on the production
Border 2026-07-25: member_health reported the node active/live with a
heartbeat seconds old while n2n_faults simultaneously reported it down.
"""

import asyncio
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(REPO, "mcp-servers", "protocol-mcp")


def _service(tmp_path):
    sys.path.insert(0, PROTO)
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager
    svc = FederationService(local_as=65001, router_id="4.4.4.4",
                            manager=FederationManager(base_dir=str(tmp_path)))
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    # health_report() gates daemon_up on the iN2N listener being bound.
    svc._in2n_server = object()
    return svc


def _activate(svc, member_id):
    """Drive the real lifecycle to STATE_ACTIVE: enrollment pins the key
    (state=enrolled), then authentication marks it active -- which is the
    state a live production phone actually sits in."""
    fp = svc.risk.get_member(member_id)["key_fingerprint"]
    assert svc.risk.verify_member(member_id, fp)
    assert svc.risk.get_member(member_id)["state"] == "active"


def _enroll_edge(svc, member_id="risk/phone1"):
    from bgp.federation import certs
    cert_pem, _ = certs.create_self_signed(member_id)
    token = svc.risk.issue_token(label="phone1")["token"]
    svc.risk.consume_token(token, member_id, cert_pem, scope=[],
                           transport_binding="edge-ws", node_type="edge")
    _activate(svc, member_id)
    return member_id


def test_connected_edge_node_is_not_a_member_fault(tmp_path):
    asyncio.run(_connected_edge_node_is_not_a_member_fault(tmp_path))


async def _connected_edge_node_is_not_a_member_fault(tmp_path):
    svc = _service(tmp_path)
    member_id = _enroll_edge(svc)

    # Disconnected edge node: down, and a genuine member fault (DB says
    # active, no channel) -- this half already behaved correctly.
    rep = svc.health_report()
    assert rep["members"][member_id]["state"] == "down"
    assert rep["fault_class"] == "member"

    # Now the phone is connected. Its channel lives in edge_channels --
    # never member_channels. This is the exact distinction the bug missed.
    svc.edge_channels[member_id] = object()

    rep = svc.health_report()
    assert rep["members"][member_id]["state"] == "up", (
        "connected edge node reported down -- health_report() is reading only "
        "member_channels and ignoring edge_channels")
    assert rep["fault_class"] == "none", (
        "a healthy connected phone tripped fault_class=%r for the whole risk"
        % rep["fault_class"])


def test_agent_member_liveness_unchanged(tmp_path):
    asyncio.run(_agent_member_liveness_unchanged(tmp_path))


async def _agent_member_liveness_unchanged(tmp_path):
    """Guard the fix against over-reach: an agent member must still be judged
    by member_channels alone, so a real agent-member outage is still reported."""
    svc = _service(tmp_path)
    from bgp.federation import certs
    member_id = "risk/cml"
    cert_pem, _ = certs.create_self_signed(member_id)
    token = svc.risk.issue_token(label="cml")["token"]
    svc.risk.consume_token(token, member_id, cert_pem, scope=[],
                           transport_binding="distributed")
    _activate(svc, member_id)

    rep = svc.health_report()
    assert rep["members"][member_id]["state"] == "down"
    assert rep["fault_class"] == "member"

    svc.member_channels[member_id] = object()
    rep = svc.health_report()
    assert rep["members"][member_id]["state"] == "up"
    assert rep["fault_class"] == "none"
