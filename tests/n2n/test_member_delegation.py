"""iN2N Border→Member delegation + scope enforcement (feature 056, US2/US5).

Routes a capability to the owning member and delegates it as an async task over
the internal channel, reusing the 053 TaskManager. The gateway executor is
stubbed (no live gateway in tests) so we validate the delegation PLUMBING and
scope refusal (FR-009/010/023, SC-006/SC-007).
"""

import asyncio

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.risk import BASE_FLOOR


def _service(base, name):
    mgr = FederationManager(base_dir=str(base))
    return FederationService(local_as=65001, router_id="4.4.4.4", display_name=name, manager=mgr)


async def _stand_up_risk(tmp_path, member_scope):
    border = _service(tmp_path / "border", "Border")
    member = _service(tmp_path / "member", "Member")
    border.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    member.risk.set_role("member", risk_name="risk", self_member_id="risk/cml")
    member.member_scope = set(member_scope)
    # A member now executes via OpenClaw EMBEDDED mode (gateway.run_agent_turn
    # local=True). Stub that module fn (no live OpenClaw in tests) — the worker
    # imports it at call time, so patching the module attribute takes effect.
    import bgp.federation.gateway as gw
    async def _fake_run(prompt, session_key="in2n", timeout_s=600, local=False, model=None):
        return (f"embedded run ok :: {prompt}", 42)
    gw.run_agent_turn = _fake_run

    # Enroll the member with a scope that covers its specialty so the Border can route.
    scope = list(BASE_FLOOR) + [
        {"name": c, "type": "skill", "tier": "specialty"} for c in member_scope]
    tok = border.risk.issue_token()["token"]

    async def on_conn(reader, writer):
        await border.accept_internal(reader, writer)
    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    # dial + enroll; then patch the pinned member's scope on the Border side
    await member.dial_border("127.0.0.1", port, enrollment_token=tok)
    await asyncio.sleep(0.2)
    # Border stores scope from enrollment params; ensure the specialty is recorded
    border.risk._conn.execute(
        "UPDATE member SET scope=? WHERE member_id=?",
        (__import__("json").dumps(scope), "risk/cml"))
    border.risk._conn.commit()
    return border, member, server


def test_route_and_delegate_completes(tmp_path):
    asyncio.run(_route_and_delegate(tmp_path))


async def _route_and_delegate(tmp_path):
    border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"])
    async with server:
        # Operator asks the Border; it routes to risk/cml and delegates.
        out = await border.route_and_delegate("cml-lab-lifecycle", "build my lab")
        assert out["member_id"] == "risk/cml"
        task_id = out["task_id"]
        assert out["state"] == "submitted"
        # The task runs on the MEMBER side; poll it to completion.
        for _ in range(50):
            st = member.tasks.status(task_id)
            if st["state"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.05)
        res = member.tasks.result(task_id)
        assert res["state"] == "completed"
        assert "cml-lab-lifecycle" in res["output_text"]   # embedded run saw the skill
        # Border-side retrieval must work over the iN2N member channel (regression:
        # the operator poll used to go down the eN2N path and stall at 'submitted').
        assert border.is_member_task("risk/cml")
        polled = await border.poll_member_task("risk/cml", task_id, kind="result")
        assert polled["state"] == "completed"
        assert "cml-lab-lifecycle" in polled["output_text"]
    border.manager.close(); member.manager.close()


def test_no_capable_member(tmp_path):
    asyncio.run(_no_capable(tmp_path))


async def _no_capable(tmp_path):
    border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"])
    async with server:
        out = await border.route_and_delegate("something-nobody-has", "x")
        assert out["error"] == "IN2N_ERR_NO_CAPABLE_MEMBER"
    border.manager.close(); member.manager.close()


def test_out_of_scope_refused(tmp_path):
    asyncio.run(_out_of_scope(tmp_path))


async def _out_of_scope(tmp_path):
    # Member is enrolled with cml scope, but we ask it (directly) for a capability
    # its runtime scope does not allow → ERR_OUT_OF_SCOPE (FR-023/SC-007).
    border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"])
    async with server:
        # Force-route a capability the member is NOT scoped to run.
        out = await border.delegate_to_member("risk/cml", "dangerous-config-push", "x")
        assert out["error"] == "out_of_scope"
        assert out["code"] == -32031
    border.manager.close(); member.manager.close()


def test_internal_delegation_audited_and_linkable(tmp_path):
    """FR-024/FR-025: internal delegations are audited channel_kind=in2n, and an
    external request satisfied internally can link the two records."""
    from bgp.federation.manager import FederationManager
    from bgp.federation.audit import Auditor
    mgr = FederationManager(base_dir=str(tmp_path / "audit"))
    audit = Auditor(mgr)
    # An external (eN2N) request arrives...
    ext = audit.record(direction="inbound", peer_identity="as65007-7.7.7.7",
                       target_type="skill", target_name="cml-lab-lifecycle",
                       decision="allowlisted", outcome="pending", channel_kind="en2n")
    # ...and the Border satisfies it by delegating internally, linking back.
    intn = audit.record(direction="outbound", peer_identity="risk/cml",
                        target_type="skill", target_name="cml-lab-lifecycle",
                        decision="requested", outcome="submitted",
                        channel_kind="in2n", linked_record_id=ext)
    rows = {r["id"]: r for r in audit.recent(limit=10)}
    assert rows[ext]["channel_kind"] == "en2n"
    assert rows[intn]["channel_kind"] == "in2n"
    assert rows[intn]["linked_record_id"] == ext      # the two tiers are joined
    mgr.close()
