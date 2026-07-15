"""iN2N truthful fault isolation (feature 057, US6, FR-017/018, SC-006).

Induces each fault class and asserts the Border's health_report attributes the
correct, distinct cause with precedence daemon > member > backend > none. This is
the fix for the 056 misdiagnosis (a poll bug reported as a "member flap").
"""

import json
import os
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager


def _border(tmp_path):
    mgr = FederationManager(base_dir=str(tmp_path))
    svc = FederationService(local_as=65001, router_id="4.4.4.4",
                            display_name="Border", manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    return mgr, svc


def _add_active_member(svc, name="cml"):
    svc.risk.add_member(name, profile=name, launch_cmd="bash /x/run.sh", on_demand=True)
    mid = f"risk/{name}"
    # simulate enrollment → active
    svc.risk._conn.execute("UPDATE member SET state='active' WHERE member_id=?", (mid,))
    svc.risk._conn.commit()
    return mid


def test_daemon_down_masks_members(tmp_path):
    mgr, svc = _border(tmp_path)
    _add_active_member(svc)
    svc._in2n_server = None            # listener not bound → daemon/federation fault
    rep = svc.health_report()
    assert rep["daemon"] == "down"
    assert rep["fault_class"] == "daemon"      # masks member/backend
    mgr.close()


def test_member_down_reported_when_daemon_up(tmp_path):
    mgr, svc = _border(tmp_path)
    mid = _add_active_member(svc)
    svc._in2n_server = object()        # listener bound → daemon up
    # member is 'active' in the registry but has NO live channel → member-down
    assert mid not in svc.member_channels
    rep = svc.health_report()
    assert rep["daemon"] == "up"
    assert rep["fault_class"] == "member"
    assert rep["members"][mid]["state"] == "down"
    assert rep["members"][mid]["will_cold_start"] is True   # on_demand + launch_cmd
    mgr.close()


def test_backend_unreachable_not_a_federation_fault(tmp_path):
    mgr, svc = _border(tmp_path)
    mid = _add_active_member(svc)
    svc._in2n_server = object()                 # daemon up
    svc.member_channels[mid] = object()         # member up (live channel)
    # member reports its backend (device/API) unreachable in its health JSON
    svc.risk.update_health(mid, backend="unreachable")
    rep = svc.health_report()
    assert rep["daemon"] == "up"
    assert rep["members"][mid]["state"] == "up"
    assert rep["backends"][mid] == "unreachable"
    assert rep["fault_class"] == "backend"      # NOT daemon/member
    mgr.close()


def test_all_healthy_is_none(tmp_path):
    mgr, svc = _border(tmp_path)
    mid = _add_active_member(svc)
    svc._in2n_server = object()
    svc.member_channels[mid] = object()
    svc.risk.update_health(mid, backend="reachable")
    rep = svc.health_report()
    assert rep["fault_class"] == "none"
    mgr.close()
