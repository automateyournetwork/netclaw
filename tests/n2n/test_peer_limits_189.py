"""Spec 189: max-prefix-style peer limit semantics (issue #343).

Covers: counted vs uncounted operations (FR-001), backward-compatible defaults
(FR-002/005/010/013), warn / teardown actions and persisted hold-down (FR-005..007),
edge-triggered warning (FR-008), global cap (FR-004), status/reset/audit (FR-009/011/012),
policy validation, and iN2N (already_trusted) never being torn down.
"""
import asyncio
import inspect
from types import SimpleNamespace

import pytest

from bgp.federation import authorization, invocation
from bgp.federation.authorization import Authorizer
from bgp.federation.channel import RpcError, ERR_RATE_LIMITED, ERR_BUDGET_EXHAUSTED, ERR_SEVERED
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.service import FederationService

TOOL = ("tool", "cml-mcp/list_labs")


def _federated(manager, asn=65007, rid="7.7.7.7"):
    manager.local_consent(asn, rid)
    manager.remote_consent(asn, rid)
    return peer_identity(asn, rid)


@pytest.fixture
def authz(manager):
    a = Authorizer(manager)
    a.audit = _Audit()
    return a


class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)
        return len(self.rows)

    def decisions(self):
        return [r["decision"] for r in self.rows]


def _call(authz, ident, allow_trusted=False):
    """One full admission: authorize then admit (what every handler does)."""
    d = authz.authorize(ident, *TOOL, already_trusted=allow_trusted)
    if not d.allowed:
        return d
    return authz.admit(ident, *TOOL, d, already_trusted=allow_trusted)


# ---------------------------------------------------------------- defaults (SC-001)

def test_defaults_are_unchanged(authz, manager):
    ident = _federated(manager)
    p = authz.get_policy(ident)
    assert (p["rate_per_min"], p["daily_requests"], p["daily_tokens"]) == (10, 200, 500000)
    assert p["action"] == "refuse" and p["warn_threshold"] == 0.8 and p["restart_timer_s"] == 300
    assert authz.global_caps() == {"daily_requests": None, "daily_tokens": None}


def test_default_refuse_keeps_channel_and_codes(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.daily_requests = 2
    authz.rate_per_min = 100
    hooks = []
    authz.teardown_hook = lambda *a: hooks.append(a)
    assert _call(authz, ident).allowed and _call(authz, ident).allowed
    d = _call(authz, ident)
    assert not d.allowed and d.code == "budget_exhausted" and not d.teardown
    assert hooks == [] and authz.hold_down_remaining(ident) == 0
    # refusals are free: usage did not move past the limit
    assert authz.budget_status(ident)["requests_used"] == 2
    assert [x for x in authz.audit.decisions() if x.startswith("limit_") and x != "limit_warning"] == []


def test_default_rate_refusal(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.rate_per_min = 2
    assert authz.authorize(ident, *TOOL).allowed and authz.authorize(ident, *TOOL).allowed
    d = authz.authorize(ident, *TOOL)
    assert d.code == "rate_limited" and not d.teardown


# ---------------------------------------------------------------- warn

def test_warn_allows_and_counts(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.rate_per_min = 100
    authz.set_policy(ident, action="warn", daily_requests=2)
    results = [_call(authz, ident) for _ in range(4)]
    assert all(r.allowed for r in results)
    assert authz.budget_status(ident)["requests_used"] == 4  # usage stays truthful
    assert "limit_exceeded_warned" in authz.audit.decisions()


def test_warn_rate_is_not_enforced(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.set_policy(ident, action="warn", rate_per_min=1)
    assert all(authz.authorize(ident, *TOOL).allowed for _ in range(3))
    assert "limit_exceeded_warned" in authz.audit.decisions()


# ---------------------------------------------------------------- teardown / hold-down

def test_teardown_hold_down_and_recovery(authz, manager, monkeypatch):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.rate_per_min = 100
    authz.set_policy(ident, action="teardown", daily_requests=1, restart_timer_s=60)
    hooks = []
    authz.teardown_hook = lambda peer, reason: hooks.append((peer, reason))
    assert _call(authz, ident).allowed
    d = _call(authz, ident)
    assert not d.allowed and d.code == "budget_exhausted" and d.teardown
    assert hooks == [(ident, "limit:requests")]
    assert 0 < authz.hold_down_remaining(ident) <= 60
    held = authz.authorize(ident, *TOOL)
    assert held.code == "severed" and "hold-down" in held.reason
    assert "limit_teardown" in authz.audit.decisions()
    assert "limit_hold_down_refused" in authz.audit.decisions()
    # timer expiry
    real = authorization.time.time
    monkeypatch.setattr(authorization.time, "time", lambda: real() + 61)
    assert authz.hold_down_remaining(ident) == 0
    monkeypatch.undo()


def test_hold_down_survives_manager_restart(fed_base):
    m1 = FederationManager(base_dir=fed_base)
    ident = _federated(m1)
    a1 = Authorizer(m1)
    a1.grant(ident, *TOOL)
    a1.set_policy(ident, action="teardown", daily_requests=0, restart_timer_s=300)
    assert a1.authorize(ident, *TOOL).teardown
    m1.close()
    m2 = FederationManager(base_dir=fed_base)
    try:
        a2 = Authorizer(m2)
        assert a2.hold_down_remaining(ident) > 0
        assert a2.get_policy(ident)["action"] == "teardown"  # overrides persisted too
    finally:
        m2.close()


def test_clear_hold_down_keeps_counters(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.set_policy(ident, action="teardown", daily_requests=1, restart_timer_s=300)
    authz.rate_per_min = 100
    _call(authz, ident)
    _call(authz, ident)
    authz.clear_hold_down(ident, actor="ops")
    assert authz.hold_down_remaining(ident) == 0
    assert authz.budget_status(ident)["requests_used"] == 1
    assert authz.authorize(ident, *TOOL).code == "budget_exhausted"  # counters not reset


def test_rate_exceed_triggers_teardown(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.set_policy(ident, action="teardown", rate_per_min=1, restart_timer_s=30)
    assert authz.authorize(ident, *TOOL).allowed
    d = authz.authorize(ident, *TOOL)
    assert d.code == "rate_limited" and d.teardown and authz.hold_down_remaining(ident) > 0


def test_internal_channel_is_never_torn_down(authz, manager):
    """C1: iN2N (already_trusted) keeps refuse semantics even under action=teardown."""
    me = "johns-risk/viz"
    authz.grant(me, *TOOL)
    authz.rate_per_min = 100
    authz.set_policy(me, action="teardown", daily_requests=1)
    hooks = []
    authz.teardown_hook = lambda *a: hooks.append(a)
    assert _call(authz, me, allow_trusted=True).allowed
    d = _call(authz, me, allow_trusted=True)
    assert d.code == "budget_exhausted" and not d.teardown
    assert hooks == [] and authz.hold_down_remaining(me) == 0


# ---------------------------------------------------------------- warning (parametrized, C6)

@pytest.mark.parametrize("limit_name,field,per_call", [("requests", "daily_requests", (1, 0)),
                                                       ("tokens", "daily_tokens", (0, 40))])
def test_warning_once_per_day_and_rearms(authz, manager, monkeypatch, limit_name, field, per_call):
    ident = _federated(manager)
    authz.rate_per_min = 1000
    authz.set_policy(ident, warn_threshold=0.8, **{field: 100 if limit_name == "tokens" else 10})
    reqs, toks = per_call

    def warnings():
        return [r for r in authz.audit.rows if r["decision"] == "limit_warning"
                and r["target_name"].startswith(limit_name + ":")]
    if limit_name == "requests":
        for _ in range(7):
            authz.debit(ident, requests=1)
        assert warnings() == []
        for _ in range(3):
            authz.debit(ident, requests=1)
    else:
        authz.debit(ident, requests=0, tokens=40)
        authz.debit(ident, requests=0, tokens=30)
        assert warnings() == []
        authz.debit(ident, requests=0, tokens=20)
    assert len(warnings()) == 1
    authz.debit(ident, requests=0 if limit_name == "tokens" else 1, tokens=1)
    assert len(warnings()) == 1  # edge triggered
    monkeypatch.setattr(authorization, "_today", lambda: "2099-01-01")
    authz.debit(ident, requests=10 if limit_name == "requests" else 0,
                tokens=100 if limit_name == "tokens" else 0)
    assert len(warnings()) == 2  # re-armed on next UTC day


# ---------------------------------------------------------------- global cap

def test_global_cap_unset_is_off(authz, manager):
    a, b = _federated(manager), _federated(manager, 65008, "8.8.8.8")
    for i in (a, b):
        authz.grant(i, *TOOL)
    authz.rate_per_min = 1000
    for _ in range(30):
        assert _call(authz, a).allowed and _call(authz, b).allowed


def test_global_cap_across_peers_and_teardown_is_local(authz, manager):
    a, b = _federated(manager), _federated(manager, 65008, "8.8.8.8")
    for i in (a, b):
        authz.grant(i, *TOOL)
    authz.rate_per_min = 1000
    authz.set_policy("*", daily_requests=5)
    authz.set_policy(a, action="teardown", restart_timer_s=10)
    hooks = []
    authz.teardown_hook = lambda peer, r: hooks.append(peer)
    for _ in range(3):
        assert _call(authz, a).allowed
    for _ in range(2):
        assert _call(authz, b).allowed
    d = _call(authz, a)
    assert d.code == "budget_exhausted" and "global" in d.reason and d.teardown
    assert hooks == [a] and authz.hold_down_remaining(b) == 0
    d_b = _call(authz, b)   # b is under action=refuse: refused, channel kept
    assert d_b.code == "budget_exhausted" and not d_b.teardown and hooks == [a]
    assert authz.limit_status(a)["global"]["requests_used"] == 5


def test_global_cap_from_env(manager, monkeypatch):
    monkeypatch.setenv("N2N_GLOBAL_DAILY_REQUESTS", "1")
    a = Authorizer(manager)
    assert a.global_caps()["daily_requests"] == 1
    a.set_policy("*", daily_requests=9)   # '*' row takes precedence over env (C4)
    assert a.global_caps()["daily_requests"] == 9


# ---------------------------------------------------------------- status / reset / validation

def test_status_and_reset(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.rate_per_min = 100
    authz.set_policy(ident, action="teardown", daily_requests=2, restart_timer_s=100, warn_threshold=0.5)
    _call(authz, ident)
    st = authz.limit_status(ident)
    assert st["requests_used"] == 1 and st["policy"]["action"] == "teardown"
    assert st["has_override"] and st["warned"] == ["requests"] and st["hold_down_remaining_s"] == 0
    _call(authz, ident)
    assert _call(authz, ident).teardown
    assert authz.limit_status(ident)["hold_down_remaining_s"] > 0
    authz.reset_limits(ident, actor="ops")
    st = authz.limit_status(ident)
    assert st["requests_used"] == 0 and st["warned"] == [] and st["hold_down_remaining_s"] == 0
    assert st["rate_used"] == 0
    assert "limit_reset" in authz.audit.decisions()
    assert _call(authz, ident).allowed


@pytest.mark.parametrize("bad", [{"daily_requests": -1}, {"rate_per_min": "x"}, {"action": "drop"},
                                 {"warn_threshold": 0}, {"warn_threshold": 1.5},
                                 {"restart_timer_s": -5}, {"bogus": 1}, {"daily_tokens": True}])
def test_invalid_policy_rejected_and_unchanged(authz, manager, bad):
    ident = _federated(manager)
    authz.set_policy(ident, daily_requests=7)
    with pytest.raises(ValueError):
        authz.set_policy(ident, **bad)
    assert authz.get_policy(ident)["daily_requests"] == 7


def test_zero_limit_denies_all_and_none_inherits(authz, manager):
    ident = _federated(manager)
    authz.grant(ident, *TOOL)
    authz.set_policy(ident, daily_requests=0)
    assert authz.authorize(ident, *TOOL).code == "budget_exhausted"
    authz.set_policy(ident, daily_requests=None)
    assert authz.get_policy(ident)["daily_requests"] == 200


def test_node_wide_action_default(authz, manager):
    ident = _federated(manager)
    authz.set_policy("*", action="warn")
    assert authz.get_policy(ident)["action"] == "warn"
    authz.set_policy(ident, action="refuse")
    assert authz.get_policy(ident)["action"] == "refuse"


# ---------------------------------------------------------------- what counts (FR-001, C3)

def _svc(tmp_path, monkeypatch):
    monkeypatch.setattr(invocation, "_security_mode", lambda: "hobby")
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="fixture",
                            manager=FederationManager(base_dir=str(tmp_path)))
    ident = _federated(svc.manager)
    svc.manager.set_chat_enabled(ident, True)
    svc.authz.rate_per_min = 1000
    return svc, SimpleNamespace(peer_identity=ident, attestation="possession")


def test_counted_operations_debit_exactly_one(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    ident = ch.peer_identity
    used = lambda: svc.authz.budget_status(ident)["requests_used"]

    async def tool(*a, **k):
        return {}

    async def skill(*a, **k):
        return "out", 1

    async def chat(*a, **k):
        return "reply", 1
    svc.invoker._exec_tool_stdio = tool
    svc.invoker._exec_skill_gateway = skill
    svc.chat._ask_gateway = chat
    svc.authz.grant(ident, "tool", "fixture/t")
    svc.authz.grant(ident, "skill", "fixture-skill")

    async def run():
        await svc.invoker.handle_tools_call(ch, {"tool": "fixture/t"})
        assert used() == 1
        sub = await svc.invoker.handle_task_submit(ch, {"skill": "fixture-skill"})
        await asyncio.gather(*list(svc.tasks._workers.values()))
        assert used() == 2
        # uncounted: status / result / cancel
        await svc.invoker.handle_task_status(ch, {"task_id": sub["task_id"]})
        await svc.invoker.handle_task_result(ch, {"task_id": sub["task_id"]})
        assert used() == 2
        # chat: open/close uncounted, message counted
        await svc.chat.handle_chat_open(ch, {"session_id": "s1"})
        assert used() == 2
        await svc.chat.handle_chat_message(ch, {"session_id": "s1", "text": "hi"})
        assert used() == 3
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()


def test_knowledge_and_replication_targets_share_the_admission_path():
    """knowledge query and replication manifest/batch each run authorize+admit.
    Batch pages are NOT exempt in the reference implementation (documented in spec FR-001)."""
    src = inspect.getsource(invocation.Invoker)
    assert 'self.authz.authorize(peer, "knowledge", collection_id)' in src
    assert 'self.authz.authorize(peer, "knowledge_replica", collection_id)' in src
    assert '_replicate_gate(channel, params, "replicate_manifest")' in src
    assert '_replicate_gate(channel, params, "replicate_batch")' in src


def test_chat_admission_goes_through_one_entry_point(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    svc.authz.set_policy(ch.peer_identity, action="teardown", rate_per_min=1, restart_timer_s=30)
    hooks = []
    svc.authz.teardown_hook = lambda p, r: hooks.append(p)

    async def chat(*a, **k):
        return "r", 1
    svc.chat._ask_gateway = chat

    async def run():
        await svc.chat.handle_chat_open(ch, {"session_id": "s"})
        await svc.chat.handle_chat_message(ch, {"session_id": "s", "text": "1"})
        with pytest.raises(RpcError) as e:
            await svc.chat.handle_chat_message(ch, {"session_id": "s", "text": "2"})
        assert e.value.code == ERR_RATE_LIMITED
        with pytest.raises(RpcError) as e2:
            await svc.chat.handle_chat_message(ch, {"session_id": "s", "text": "3"})
        assert e2.value.code == ERR_SEVERED     # hold-down
    try:
        asyncio.run(run())
        assert hooks == [ch.peer_identity]
    finally:
        svc.manager.close()


# ---------------------------------------------------------------- service wiring

def test_service_teardown_closes_channel_and_blocks_reinbound(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    ident = ch.peer_identity
    closed = []

    class Chan:
        is_initiator = False
        attestation = "possession"

        async def close(self):
            closed.append(ident)
    chan = Chan()
    svc.channels[ident] = chan
    svc.authz.set_policy(ident, action="teardown", daily_requests=0, restart_timer_s=30)
    svc.authz.grant(ident, "tool", "fixture/t")

    async def run():
        with pytest.raises(RpcError) as e:
            await svc.invoker.handle_tools_call(ch, {"tool": "fixture/t"})
        assert e.value.code == ERR_BUDGET_EXHAUSTED
        await asyncio.sleep(0.4)
        assert closed == [ident] and ident not in svc.channels
        assert svc.manager.is_federated(ident)      # consent NOT revoked
        assert svc._register_channel(ident, Chan()) is False   # hold-down blocks re-inbound
        svc.authz.clear_hold_down(ident)
        assert svc._register_channel(ident, Chan()) is True
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()


# ---------------------------------------------------------------- daemon operator surface

def test_daemon_config_status_and_reset_routes(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "mcp-servers/protocol-mcp/bgp-daemon-v2.py"
    spec = importlib.util.spec_from_file_location("limits_daemon_189", path)
    daemon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daemon)
    svc, ch = _svc(tmp_path, monkeypatch)
    ident = ch.peer_identity
    daemon._federation = svc

    async def run():
        code, out = await daemon.handle_n2n("POST", "/n2n/config", {
            "peer": ident, "limit_action": "teardown", "daily_requests": 5,
            "warn_threshold": 0.5, "restart_timer_s": 20})
        assert code == 200 and out["limits"]["policy"]["action"] == "teardown"
        assert out["limits"]["policy"]["daily_requests"] == 5
        code, out = await daemon.handle_n2n("POST", "/n2n/config", {"peer": ident, "limit_action": "drop"})
        assert code == 400 and "action" in out["error"]
        assert svc.authz.get_policy(ident)["action"] == "teardown"   # unchanged by the bad request
        code, out = await daemon.handle_n2n("GET", "/n2n/status", {})
        entry = [p for p in out["peers"] if p["identity"] == ident][0]
        assert entry["limits"]["action"] == "teardown" and entry["limits"]["requests_limit"] == 5
        code, out = await daemon.handle_n2n("GET", f"/n2n/peers/{ident}", {})
        assert out["limits"]["policy"]["restart_timer_s"] == 20
        svc.authz.debit(ident, requests=3)
        code, out = await daemon.handle_n2n("POST", "/n2n/config", {"peer": ident, "reset_limits": True})
        assert out["limits"]["requests_used"] == 0
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()
