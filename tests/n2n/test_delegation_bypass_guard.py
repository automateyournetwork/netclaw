"""Regression tests for the 2026-07-14 eN2N skill-delegation bypass review.

Locks in the three remediations:
  * run_agent_turn refuses embedded (--local) execution of untrusted eN2N input
    unless production containment verifies (fail-closed).
  * A gateway-held scope approval surfaces through the n2n approval notifier and
    the task's progress state ("awaiting gateway approval"), with the approval
    window added to the wait instead of a blind hard timeout.
  * Timed-out / failed delegated skill runs land in the audit table (and thus
    the GAIT trail) — the pre-fix path recorded nothing on failure.
"""

import asyncio

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager


@pytest.fixture(autouse=True)
def _prime_descriptor():
    """Pre-fill the cached CLI capability descriptor so run_agent_turn never
    probes `openclaw agent --help` against this file's fake PATH binaries."""
    import bgp.federation.negotiate as neg
    prev = neg._local_descriptor
    neg._local_descriptor = {"proto_version": "053", "features": [],
                             "agent_invoke": "session-id",
                             "reply_shapes": ["payloads"]}
    yield
    neg._local_descriptor = prev


def _svc(base):
    return FederationService(local_as=65007, router_id="7.7.7.7", display_name="Nick",
                             manager=FederationManager(base_dir=str(base)))


PEER = "as65001-4.4.4.4"


class _Chan:
    peer_identity = PEER
    attestation = "possession"   # post-possession session (reconciled eN2N auth)


# ---- fail-closed: untrusted eN2N input may not run embedded ----------------

def test_untrusted_local_refused_outside_production(monkeypatch):
    from bgp.federation.gateway import run_agent_turn, EnforcementRefused
    monkeypatch.delenv("N2N_RISK_MODE", raising=False)
    with pytest.raises(EnforcementRefused):
        asyncio.run(run_agent_turn("peer text", local=True, untrusted=True))


def test_untrusted_local_refused_in_production_without_sandbox(monkeypatch):
    from bgp.federation import controls
    from bgp.federation.gateway import run_agent_turn, EnforcementRefused
    monkeypatch.setenv("N2N_RISK_MODE", "production")

    async def _no_sandbox():
        return False, "systemd --user manager unavailable"
    monkeypatch.setattr(controls, "sandbox_available", _no_sandbox)
    with pytest.raises(EnforcementRefused):
        asyncio.run(run_agent_turn("peer text", local=True, untrusted=True))


def test_trusted_member_local_path_unaffected(monkeypatch, tmp_path):
    """iN2N members (untrusted=False) keep their embedded testing-mode path."""
    import bgp.federation.gateway as gw
    monkeypatch.delenv("N2N_RISK_MODE", raising=False)

    fake = tmp_path / "openclaw"
    fake.write_text("#!/bin/sh\necho '{\"result\":{\"payloads\":[{\"text\":\"member-ok\"}]}}'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:" + __import__("os").environ["PATH"])
    reply, _ = asyncio.run(gw.run_agent_turn("hi", local=True, untrusted=False, timeout_s=15))
    assert reply == "member-ok"


# ---- stall bridge: gateway approval hold → notifier + progress + extension --

def test_gateway_stall_extends_window_and_completes(monkeypatch, tmp_path):
    """A turn silent past stall_after_s gets the on_stall extension and can
    still complete (previously it died on the hard timeout)."""
    import bgp.federation.gateway as gw

    fake = tmp_path / "openclaw"
    fake.write_text("#!/bin/sh\nsleep 3\n"
                    "echo '{\"result\":{\"payloads\":[{\"text\":\"late-ok\"}]}}'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:" + __import__("os").environ["PATH"])

    stalls = []

    def on_stall(waited):
        stalls.append(waited)
        return 10  # operator approval window

    reply, _ = asyncio.run(gw.run_agent_turn(
        "hi", timeout_s=2, on_stall=on_stall, stall_after_s=1))
    assert reply == "late-ok"
    assert stalls == [1]


def test_gateway_stall_timeout_without_extension(monkeypatch, tmp_path):
    import bgp.federation.gateway as gw

    fake = tmp_path / "openclaw"
    fake.write_text("#!/bin/sh\nsleep 30\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:" + __import__("os").environ["PATH"])

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(gw.run_agent_turn("hi", timeout_s=1, stall_after_s=5))


def test_exec_skill_stall_bridges_approval_notification(tmp_path):
    """_exec_skill_gateway wires on_stall → progress('awaiting gateway approval')
    + service.notify_approval, and asks for the approval window as extension."""
    svc = _svc(tmp_path / "n2n")
    try:
        notified = []
        svc.approval_notifier = lambda *a: notified.append(a)
        progressed = []

        import bgp.federation.gateway as gw
        orig = gw.run_agent_turn

        async def fake_run(prompt, session_key="n2n", timeout_s=300, local=False,
                           model=None, untrusted=False, on_stall=None, stall_after_s=120):
            assert untrusted, "eN2N skill input must be marked untrusted"
            ext = on_stall(stall_after_s)
            assert ext == svc.authz.approval_window_s
            return "ok", 7

        gw.run_agent_turn = fake_run
        try:
            out, tokens = asyncio.run(svc.invoker._exec_skill_gateway(
                "pyats-health-check", "check", progress=progressed.append, peer=PEER))
        finally:
            gw.run_agent_turn = orig
        assert (out, tokens) == ("ok", 7)
        assert progressed == ["awaiting gateway approval"]
        assert notified == [(None, PEER, "gateway-scope", "n2n-skill-pyats-health-check")]
    finally:
        svc.manager.close()


# ---- failures land in audit (and thus GAIT) ---------------------------------

def test_timeout_recorded_in_audit(tmp_path):
    svc = _svc(tmp_path / "n2n")
    try:
        svc.manager.local_consent(65001, "4.4.4.4")
        svc.manager.remote_consent(65001, "4.4.4.4")
        svc.authz.grant(PEER, "skill", "pyats-health-check")

        import bgp.federation.gateway as gw
        orig = gw.run_agent_turn

        async def fake_run(*a, **kw):
            raise asyncio.TimeoutError()

        gw.run_agent_turn = fake_run

        async def _run():
            sub = await svc.invoker.handle_task_submit(
                _Chan(), {"skill": "pyats-health-check", "input_text": "check"})
            for _ in range(100):
                if svc.tasks.status(sub["task_id"])["state"] == "failed":
                    return sub["task_id"]
                await asyncio.sleep(0.05)
            raise AssertionError("task never reached failed state")

        try:
            task_id = asyncio.run(_run())
        finally:
            gw.run_agent_turn = orig

        rows = svc.audit.recent(peer_identity=PEER)
        timeouts = [r for r in rows if r["outcome"] == "timeout"
                    and r["request_id"] == task_id]
        assert timeouts, f"no timeout audit row; rows={rows}"
    finally:
        svc.manager.close()
