"""iN2N production posture matrix + delegation preflight (feature 057, US1).

FR-001/002/003a, FR-019/020, SC-001/SC-008. The control probes are stubbed so we
test the posture aggregation + per-control degraded policy deterministically,
without a live OpenShell/DefenseClaw/GAIT.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "mcp-servers", "protocol-mcp"))

from bgp.federation import posture, controls


def _stub_controls(monkeypatch, *, sandbox, guard, audit, production=True, strict=False):
    async def _os_avail():
        return (sandbox, "" if sandbox else "sandbox down")
    async def _dc_avail():
        return (guard, "" if guard else "guard down")
    def _gait():
        return (audit, "" if audit else "gait down")
    monkeypatch.setattr(controls, "sandbox_available", _os_avail)
    monkeypatch.setattr(controls, "defenseclaw_available", _dc_avail)
    monkeypatch.setattr(controls, "gait_recording", _gait)
    monkeypatch.setattr(controls, "is_production", lambda: production)
    monkeypatch.setattr(controls, "strict_all", lambda: strict)


def test_all_controls_up_is_enforced(monkeypatch):
    _stub_controls(monkeypatch, sandbox=True, guard=True, audit=True)
    p = asyncio.run(posture.compute_posture())
    assert p["state"] == "enforced"
    assert p["missing"] == []
    assert p["summary"] == "production — enforced"


def test_testing_mode_never_claims_production(monkeypatch):
    # Even with all controls down, testing mode reports 'testing', never a false claim.
    _stub_controls(monkeypatch, sandbox=False, guard=False, audit=False, production=False)
    p = asyncio.run(posture.compute_posture())
    assert p["state"] == "testing"
    assert p["mode"] == "testing"
    assert "production" not in p["summary"]


@pytest.mark.parametrize("missing_name,flags", [
    ("sandbox", dict(sandbox=False, guard=True, audit=True)),
    ("model-guard", dict(sandbox=True, guard=False, audit=True)),
    ("audit", dict(sandbox=True, guard=True, audit=False)),
])
def test_single_control_missing_is_degraded_and_named(monkeypatch, missing_name, flags):
    # SC-001: any one control down in production → degraded naming it, never enforced.
    _stub_controls(monkeypatch, **flags)
    p = asyncio.run(posture.compute_posture())
    assert p["state"] == "degraded"
    assert p["missing"] == [missing_name]
    assert missing_name in p["summary"]
    assert "enforced" not in p["summary"]


def test_preflight_containment_gap_refuses(monkeypatch):
    # FR-019: sandbox (containment) missing → delegation refused (fail-closed).
    _stub_controls(monkeypatch, sandbox=False, guard=True, audit=True)
    p = asyncio.run(posture.compute_posture())
    d = posture.posture_ok_for_delegation(p)
    assert d["allow"] is False
    assert d["enforcement"] == "refused:sandbox"
    assert d["refused_control"] == "sandbox"


def test_preflight_model_guard_gap_refuses(monkeypatch):
    # FR-019 + SC-003: model-guard missing → refused, never runs unguarded.
    _stub_controls(monkeypatch, sandbox=True, guard=False, audit=True)
    p = asyncio.run(posture.compute_posture())
    d = posture.posture_ok_for_delegation(p)
    assert d["allow"] is False
    assert d["enforcement"] == "refused:model-guard"


def test_preflight_audit_only_gap_runs_flagged(monkeypatch):
    # FR-019/SC-008: audit-only gap → runs but flagged audit-degraded.
    _stub_controls(monkeypatch, sandbox=True, guard=True, audit=False)
    p = asyncio.run(posture.compute_posture())
    d = posture.posture_ok_for_delegation(p)
    assert d["allow"] is True
    assert d["enforcement"] == "audit-degraded"


def test_preflight_strict_all_refuses_on_audit_gap(monkeypatch):
    # SC-008: strict-all override → refuse on ANY gap, including audit.
    _stub_controls(monkeypatch, sandbox=True, guard=True, audit=False, strict=True)
    p = asyncio.run(posture.compute_posture())
    d = posture.posture_ok_for_delegation(p, strict_all=True)
    assert d["allow"] is False
    assert d["enforcement"] == "refused:audit"


def test_preflight_enforced_when_all_up(monkeypatch):
    _stub_controls(monkeypatch, sandbox=True, guard=True, audit=True)
    p = asyncio.run(posture.compute_posture())
    d = posture.posture_ok_for_delegation(p)
    assert d["allow"] is True
    assert d["enforcement"] == "enforced"


def test_preflight_testing_allows(monkeypatch):
    _stub_controls(monkeypatch, sandbox=False, guard=False, audit=False, production=False)
    p = asyncio.run(posture.compute_posture())
    d = posture.posture_ok_for_delegation(p)
    assert d["allow"] is True
    assert d["enforcement"] == "testing"
