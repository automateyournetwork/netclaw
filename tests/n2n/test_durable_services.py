"""iN2N durable runtime: service generator + single-owner reconciliation (US5).

FR-013/014/015. The generator emits valid systemd unit text for the mesh daemon
and one unit per always-on member; the Border's cold-start path defers to a
service-managed member's unit instead of shell-spawning it (no double-launch).
systemctl is stubbed — we test the unit TEXT + the single-owner routing logic.
"""

import asyncio
import importlib.util
import os
import sys

import pytest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager


def _load_services_module():
    path = os.path.join(REPO, "scripts", "in2n-services.py")
    spec = importlib.util.spec_from_file_location("in2n_services", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mesh_unit_text_is_valid(monkeypatch):
    svc = _load_services_module()
    text = svc._mesh_unit_text()
    assert "[Unit]" in text and "[Service]" in text and "[Install]" in text
    assert "Restart=always" in text
    assert "WantedBy=default.target" in text
    assert "@REPO@" not in text and "@HOME@" not in text   # substituted
    assert "bgp-daemon-v2.py" in text


def test_member_unit_text_binds_env_and_restart():
    svc = _load_services_module()
    text = svc._member_unit_text("johns-risk/cml", "bash /home/x/.openclaw-cml/run.sh")
    assert "netclaw-mesh.service" in text          # ordered after the daemon
    assert "Restart=always" in text
    assert "ExecStart=" in text
    # `bash` resolved to an absolute path for systemd
    assert "ExecStart=/" in text
    assert "run.sh" in text


def test_unit_naming():
    svc = _load_services_module()
    assert svc._unit_name("johns-risk/ipfabric") == "netclaw-member-johns-risk-ipfabric.service"


def test_single_owner_service_member_not_shell_spawned(tmp_path, monkeypatch):
    # FR-014: a member bound to a durable service is brought up via its unit,
    # NEVER shell-spawned by the cold-start path (no double-launch).
    asyncio.run(_single_owner(tmp_path, monkeypatch))


async def _single_owner(tmp_path, monkeypatch):
    mgr = FederationManager(base_dir=str(tmp_path / "b"))
    svc = FederationService(local_as=65001, router_id="4.4.4.4",
                            display_name="Border", manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    # Provision a member and bind it to a durable service.
    svc.risk.add_member("cml", profile="cml", launch_cmd="bash /x/run.sh", on_demand=False)
    svc.risk.set_managed_by("risk/cml", "service", service_unit="netclaw-member-risk-cml.service")

    spawned = {"shell": False}
    async def _no_shell(*a, **k):
        spawned["shell"] = True
        class _P:  # pragma: no cover
            pass
        return _P()
    monkeypatch.setattr(asyncio, "create_subprocess_shell", _no_shell)

    ensured = {"unit": None}
    async def _fake_unit(unit):
        ensured["unit"] = unit
        return True
    svc._ensure_unit_active = _fake_unit
    # It will wait for a dial that never comes; short-circuit the wait.
    async def _no_wait(member_id, wait_s=30.0):
        return None
    svc._wait_for_dial = _no_wait

    await svc.ensure_member_up("risk/cml")
    assert spawned["shell"] is False                      # never shell-spawned
    assert ensured["unit"] == "netclaw-member-risk-cml.service"
    mgr.close()
