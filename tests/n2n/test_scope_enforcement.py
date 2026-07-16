"""iN2N member scope enforcement + base-floor rules (feature 056, US5).

Covers FR-021a/FR-021b/FR-023/FR-027 and SC-007.
"""

import json

import pytest

from bgp.federation.risk import RiskManager, BASE_FLOOR


@pytest.fixture
def border(manager):
    rm = RiskManager(manager, quarantine_threshold=5)
    rm.set_role("border", risk_name="risk", enabled_stacks="in2n")
    return rm


def test_base_floor_present_and_nonremovable(border):
    """Every member carries the base floor regardless of profile (FR-021a)."""
    out = border.add_member("cml", specialty=[{"name": "cml-lab-lifecycle"}])
    names = {e["name"] for e in out["scope"]}
    for base in BASE_FLOOR:
        assert base["name"] in names
    # Custom member with NO specialty still has the full base floor.
    out2 = border.add_member("bare")
    names2 = {e["name"] for e in out2["scope"]}
    for base in BASE_FLOOR:
        assert base["name"] in names2


def test_advertised_equals_allowed(border):
    """A member's scope is both what it advertises and its execution ceiling."""
    out = border.add_member("cml", specialty=[{"name": "cml-lab-lifecycle"}])
    mem = border.get_member("risk/cml")
    # Everything advertised is in-scope; nothing outside is.
    for e in out["scope"]:
        assert border.covers(mem, e["name"])
    assert not border.covers(mem, "pyats-run")


def test_base_floor_excluded_from_specificity(border):
    """Base floor must not distort the routing specialist tie-break (FR-021b)."""
    out = border.add_member("cml", specialty=[{"name": "cml-lab-lifecycle"}])
    # 4 base entries + 1 specialty in scope, but specialty_count == 1
    assert len(out["scope"]) == len(BASE_FLOOR) + 1
    assert border.specialty_count(out["scope"]) == 1
    out2 = border.add_member("broad", specialty=["a", "b", "c"])
    assert border.specialty_count(out2["scope"]) == 3   # base still excluded


def test_out_of_scope_refused_at_service(tmp_path):
    """FR-023/SC-007: a scoped member refuses out-of-scope work over the channel."""
    import asyncio
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager

    async def _run():
        mgr = FederationManager(base_dir=str(tmp_path / "m"))
        member = FederationService(local_as=65001, router_id="4.4.4.4", manager=mgr)
        member.risk.set_role("member", risk_name="risk", self_member_id="risk/cml")
        member.member_scope = {"cml-lab-lifecycle"}

        class _Chan:
            member_id = "risk/border"
        # in-scope → accepted (returns a task_id); out-of-scope → RpcError -32031
        from bgp.federation.channel import RpcError
        # stub the executor so no live gateway is needed
        async def _fake(skill, text, progress=None, peer=None): return ("ok", 1)
        member.invoker._exec_skill_gateway = _fake
        ok = await member._in2n_member_submit(_Chan(), {"skill": "cml-lab-lifecycle", "input_text": "x"})
        assert ok["state"] == "submitted"
        with pytest.raises(RpcError) as ei:
            await member._in2n_member_submit(_Chan(), {"skill": "not-my-job", "input_text": "x"})
        assert ei.value.code == -32031
        mgr.close()

    asyncio.run(_run())
