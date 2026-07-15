"""iN2N Border cold-start-on-route for on-demand members (feature 056, hybrid runtime).

The Border spawns a sleeping on-demand member when routed to it, waits for it to
dial in + authenticate, then delegates. Remote members (no launch_cmd) can't be
cold-started. The subprocess spawn is stubbed (no real process in tests).
"""

import asyncio

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager


def _border(base):
    mgr = FederationManager(base_dir=str(base))
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    return svc


def test_cold_start_spawns_and_waits(tmp_path):
    asyncio.run(_cold_start(tmp_path))


async def _cold_start(tmp_path):
    svc = _border(tmp_path / "b")
    svc.risk.add_member("cml", specialty=[{"name": "cml-lab-lifecycle"}],
                        launch_cmd="true", on_demand=True)

    class _FakeChan:
        member_id = "risk/cml"

    real = asyncio.create_subprocess_shell
    async def fake_spawn(cmd, **kw):
        # simulate the member process dialing in + authenticating shortly after launch
        async def _appear():
            await asyncio.sleep(0.2)
            svc.member_channels["risk/cml"] = _FakeChan()
        asyncio.create_task(_appear())
        return await real("true", **kw)   # harmless real process for the return type

    asyncio.create_subprocess_shell = fake_spawn
    try:
        ch = await svc.ensure_member_up("risk/cml", wait_s=5)
        assert ch is not None                       # cold-started + came up
        assert "risk/cml" in svc.member_channels
    finally:
        asyncio.create_subprocess_shell = real
    svc.manager.close()


def test_remote_member_not_cold_started(tmp_path):
    asyncio.run(_remote(tmp_path))


async def _remote(tmp_path):
    svc = _border(tmp_path / "b")
    # a member with NO launch_cmd (e.g. lives on another host) — Border can't spawn it
    svc.risk.add_member("remote", specialty=[{"name": "x"}])
    ch = await svc.ensure_member_up("risk/remote", wait_s=1)
    assert ch is None
    # delegating to it reports unreachable rather than hanging
    out = await svc.delegate_to_member("risk/remote", "x", "do it")
    assert out["error"] == "member_unreachable"
    svc.manager.close()


def test_always_on_member_needs_no_spawn(tmp_path):
    asyncio.run(_always_on(tmp_path))


async def _always_on(tmp_path):
    svc = _border(tmp_path / "b")
    svc.risk.add_member("cml", specialty=[{"name": "cml-lab-lifecycle"}])

    class _FakeChan:
        member_id = "risk/cml"
    svc.member_channels["risk/cml"] = _FakeChan()     # already live (always-on)
    ch = await svc.ensure_member_up("risk/cml", wait_s=1)
    assert ch is svc.member_channels["risk/cml"]      # returned immediately, no spawn
    svc.manager.close()
