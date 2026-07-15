"""iN2N production containment controls fail-closed (feature 057, US2 + US3).

FR-004/005 (sandbox = host-level systemd confinement), FR-007/008/009 (DefenseClaw
guard + component scan), SC-002/SC-003. External CLIs are stubbed, so we verify the
enforcement LOGIC deterministically: production refuses when a containment control
is unavailable, and never runs unguarded.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "mcp-servers", "protocol-mcp"))

from bgp.federation import controls, gateway


# ---- US2: member confinement is applied at LAUNCH (systemd unit), so the model
# turn itself is not command-wrapped. The gateway guard leaves cmd unchanged. -----

def test_testing_mode_runs_unwrapped(monkeypatch):
    monkeypatch.setattr(controls, "is_production", lambda: False)
    base = ["openclaw", "agent", "--local", "-m", "hi"]
    out = asyncio.run(gateway._apply_production_controls(list(base), "hi"))
    assert out == base   # testing: no guard, unchanged


def test_production_guarded_cmd_unchanged(monkeypatch):
    # In production the model I/O is guarded but the command is unchanged
    # (confinement is applied out-of-band by the member's systemd unit).
    monkeypatch.setattr(controls, "is_production", lambda: True)
    async def _guard_ok():
        return (True, "")
    monkeypatch.setattr(controls, "defenseclaw_available", _guard_ok)
    base = ["openclaw", "agent", "--local", "-m", "hi"]
    out = asyncio.run(gateway._apply_production_controls(list(base), "hi"))
    assert out == base


def test_confined_cold_start_uses_systemd_run(monkeypatch):
    # FR-005: cold-started members in production launch inside a transient confined
    # systemd unit (NoNewPrivileges + read-only system + hidden master secrets).
    monkeypatch.setattr(controls.shutil, "which", lambda _: "/usr/bin/systemd-run")
    argv = controls.confined_cold_start("bash /x/run.sh", "risk/cml")
    assert argv[0] == "systemd-run" and "--user" in argv
    assert "NoNewPrivileges=yes" in argv and "ProtectSystem=strict" in argv
    assert "InaccessiblePaths=-%h/.openclaw/.env" in argv
    assert argv[-3:] == ["/bin/sh", "-c", "bash /x/run.sh"]


# ---- US3: DefenseClaw model-guard fail-closed (gateway) --------------------

def test_production_guard_unavailable_fails_closed(monkeypatch):
    # SC-003: defenseclaw down in production → refused BEFORE any sandbox/exec,
    # never routes to an unguarded provider.
    monkeypatch.setattr(controls, "is_production", lambda: True)
    async def _guard_down():
        return (False, "security.mode is not 'defenseclaw'")
    monkeypatch.setattr(controls, "defenseclaw_available", _guard_down)
    with pytest.raises(gateway.EnforcementRefused, match="model-guard unavailable"):
        asyncio.run(gateway._apply_production_controls(
            ["openclaw", "agent", "--local"], "hi"))


# ---- US3: component scan blocks a flagged member ---------------------------

def test_component_scan_pass(monkeypatch):
    async def _run_ok(cmd, timeout_s=60.0):
        return (0, "scan clean")
    monkeypatch.setattr(controls, "_run", _run_ok)
    monkeypatch.setattr(controls.shutil, "which", lambda _: "/usr/bin/defenseclaw")
    ok, verdict = asyncio.run(controls.component_scan(["cml-lab-lifecycle"]))
    assert ok is True and verdict == "pass"


def test_component_scan_flags_member(monkeypatch):
    # FR-008: a flagged component → blocked, named.
    async def _run_flag(cmd, timeout_s=60.0):
        return (1, "CRITICAL: dangerous eval detected")
    monkeypatch.setattr(controls, "_run", _run_flag)
    monkeypatch.setattr(controls.shutil, "which", lambda _: "/usr/bin/defenseclaw")
    ok, verdict = asyncio.run(controls.component_scan(["evil-skill"]))
    assert ok is False and verdict == "flagged:evil-skill"


def test_component_scan_empty_passes():
    ok, verdict = asyncio.run(controls.component_scan([]))
    assert ok is True and verdict == "pass"
