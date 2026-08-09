"""Feature 100 (T026): outbound calls must reach a terminal audit state.

The defect: all three outbound paths wrote one row with `outcome="pending"` and then
never wrote again. A success, a refusal by the peer, and a timeout were
indistinguishable in the audit trail, and every outbound row sat pending forever
(FR-034). A refusal in particular was discarded rather than kept as evidence (FR-036).

FR-035 is the one that makes the trail reconcilable across a federation boundary: the
terminal row must carry the SAME request_id as the pending row, so the caller's pair
joins to the callee's inbound row.
"""

import asyncio

import pytest

from bgp.federation.channel import ERR_EXECUTION_TIMEOUT, ERR_NOT_ALLOWLISTED, RpcError
from bgp.federation.invocation import Invoker


class _FakeChannel:
    """Stands in for a live FederationChannel, raising or returning as directed."""

    def __init__(self, raise_exc=None, result=None):
        self._raise = raise_exc
        self._result = result if result is not None else {"ok": True}
        self.calls = []

    async def call(self, method, params, timeout=None):
        self.calls.append((method, params, timeout))
        if self._raise is not None:
            raise self._raise
        return self._result


class _FakeService:
    def __init__(self, manager, auditor):
        self.manager = manager
        self.audit = auditor
        self.authz = None
        self.local_identity = "as65001-4.4.4.4"


@pytest.fixture
def invoker(manager):
    from bgp.federation.audit import Auditor
    manager.upsert_peer(65006, "6.6.6.6", display_name="Nate")
    auditor = Auditor(manager)
    inv = Invoker.__new__(Invoker)          # bypass __init__'s service wiring
    inv.service = _FakeService(manager, auditor)
    inv.manager = manager
    inv.audit = auditor
    inv.tool_timeout = 120
    inv.skill_timeout = 600
    return inv


IDENT = "as65006-6.6.6.6"


def _outcomes(invoker, request_id):
    return [r["outcome"] for r in invoker.audit.recent(limit=50)
            if r["request_id"] == request_id]


# ── Terminal outcomes per class (FR-034/036/037) ──────────────────────────────

def test_success_records_a_terminal_row(invoker):
    ch = _FakeChannel(result={"stdout": "ok"})
    asyncio.run(invoker._outbound_call(
        ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
        target_name="show_version", req_id="req-success", timeout=5))
    assert _outcomes(invoker, "req-success") == ["success"]


def test_remote_refusal_records_denied_and_reraises(invoker):
    """FR-036: a refusal is auditable evidence, not a transient response."""
    ch = _FakeChannel(raise_exc=RpcError(ERR_NOT_ALLOWLISTED, "not allowlisted"))
    with pytest.raises(RpcError):
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="rm_rf", req_id="req-denied", timeout=5))
    assert _outcomes(invoker, "req-denied") == ["denied"]


def test_remote_timeout_records_timeout_not_denied(invoker):
    """FR-037: a timeout is its own terminal state — flattening it into a denial would
    misattribute an infrastructure failure to a policy refusal."""
    ch = _FakeChannel(raise_exc=RpcError(ERR_EXECUTION_TIMEOUT, "timed out"))
    with pytest.raises(RpcError):
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="slow", req_id="req-timeout", timeout=5))
    assert _outcomes(invoker, "req-timeout") == ["timeout"]


def test_local_asyncio_timeout_records_timeout(invoker):
    ch = _FakeChannel(raise_exc=asyncio.TimeoutError())
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="slow", req_id="req-localto", timeout=5))
    assert _outcomes(invoker, "req-localto") == ["timeout"]


def test_dropped_channel_still_reaches_terminal_state(invoker):
    """FR-037: 'or whose channel drops before a response MUST reach a terminal
    recorded state rather than remaining pending'."""
    ch = _FakeChannel(raise_exc=ConnectionResetError("channel dropped"))
    with pytest.raises(ConnectionResetError):
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="show_version", req_id="req-dropped", timeout=5))
    assert _outcomes(invoker, "req-dropped") == ["error"]


@pytest.mark.parametrize("exc", [
    RpcError(ERR_NOT_ALLOWLISTED, "no"),
    RpcError(ERR_EXECUTION_TIMEOUT, "slow"),
    asyncio.TimeoutError(),
    ConnectionResetError("gone"),
    RuntimeError("unexpected"),
])
def test_no_failure_mode_leaves_the_row_pending(invoker, exc):
    """The headline requirement (FR-034): whatever happens, `pending` is not final."""
    ch = _FakeChannel(raise_exc=exc)
    with pytest.raises(Exception):
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="t", req_id="req-nopend", timeout=5))
    outcomes = _outcomes(invoker, "req-nopend")
    assert outcomes, "a terminal row must exist"
    assert "pending" not in outcomes


def test_exceptions_still_propagate(invoker):
    """Recording an outcome must not swallow the error — callers depend on it raising."""
    ch = _FakeChannel(raise_exc=RpcError(ERR_NOT_ALLOWLISTED, "denied by peer"))
    with pytest.raises(RpcError) as ei:
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="t", req_id="req-prop", timeout=5))
    assert ei.value.code == ERR_NOT_ALLOWLISTED


# ── FR-035: correlation by one identifier ─────────────────────────────────────

def test_terminal_row_reuses_the_initiating_request_id(invoker):
    ch = _FakeChannel()
    asyncio.run(invoker._outbound_call(
        ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
        target_name="show_version", req_id="shared-id-42", timeout=5))
    rows = [r for r in invoker.audit.recent(limit=50)
            if r["request_id"] == "shared-id-42"]
    assert rows, "FR-035: terminal row must be joinable by request_id"
    assert all(r["direction"] == "outbound" for r in rows)


def test_terminal_row_preserves_target_identity(invoker):
    ch = _FakeChannel()
    asyncio.run(invoker._outbound_call(
        ch, "n2n/knowledge/query", {}, ident=IDENT, target_type="knowledge",
        target_name="runbooks", req_id="req-target", timeout=5))
    row = [r for r in invoker.audit.recent(limit=50)
           if r["request_id"] == "req-target"][0]
    assert row["target_type"] == "knowledge"
    assert row["target_name"] == "runbooks"
    assert row["peer_identity"] == IDENT


def test_decision_stays_requested_on_outbound(invoker):
    """On an outbound call WE make no authorization decision — we asked. Only the
    outcome varies, which keeps `decision` meaning the same thing in both directions."""
    ch = _FakeChannel(raise_exc=RpcError(ERR_NOT_ALLOWLISTED, "no"))
    with pytest.raises(RpcError):
        asyncio.run(invoker._outbound_call(
            ch, "n2n/tools/call", {}, ident=IDENT, target_type="tool",
            target_name="t", req_id="req-dec", timeout=5))
    row = [r for r in invoker.audit.recent(limit=50)
           if r["request_id"] == "req-dec"][0]
    assert row["decision"] == "requested"


# ── The wrapper is actually wired into the outbound paths ─────────────────────

def test_outbound_paths_route_through_the_helper():
    """A regression guard with teeth: if someone reverts one of the three call sites to
    a bare `ch.call(...)`, its rows silently go back to pending forever."""
    import inspect

    from bgp.federation import invocation

    for name in ("invoke_remote_tool", "query_remote_knowledge",
                 "fetch_replicate_manifest"):
        src = inspect.getsource(getattr(invocation.Invoker, name))
        assert "_outbound_call" in src, (
            f"{name} must route through _outbound_call or its audit row stays pending")


def test_call_is_forwarded_verbatim(invoker):
    """The helper must not alter method, params, or timeout (FR-029: no wire change)."""
    ch = _FakeChannel()
    params = {"tool": "show_version", "request_id": "x"}
    asyncio.run(invoker._outbound_call(
        ch, "n2n/tools/call", params, ident=IDENT, target_type="tool",
        target_name="show_version", req_id="x", timeout=99))
    assert ch.calls == [("n2n/tools/call", params, 99)]
