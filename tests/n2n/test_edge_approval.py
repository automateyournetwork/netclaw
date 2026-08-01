"""Biometric-gated approval resolution tests (feature 068, US1)."""

import asyncio
import json

import pytest
import websockets

from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService
from bgp.federation.risk import RiskManager
from bgp.federation import certs


def _border(base):
    mgr = FederationManager(base_dir=str(base))
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="Border",
                            manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    return svc


class _FakePhone:
    def __init__(self, ws, handlers=None):
        self.ws = ws
        self.handlers = handlers or {}
        self.notifications = []
        self._next_id = 0
        self._pending: dict = {}
        self._task = asyncio.create_task(self._loop())

    async def _loop(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                if "method" in msg:
                    self.notifications.append((msg["method"], msg.get("params") or {}))
                    handler = self.handlers.get(msg["method"])
                    result = handler(msg.get("params") or {}) if handler else {}
                    if msg.get("id") is not None:
                        await self.ws.send(json.dumps(
                            {"jsonrpc": "2.0", "id": msg["id"], "result": result}))
                elif "id" in msg:
                    fut = self._pending.pop(msg["id"], None)
                    if fut and not fut.done():
                        fut.set_result(msg)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def call(self, method, params, timeout=5.0):
        self._next_id += 1
        req_id = f"phone:{self._next_id}"
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self.ws.send(json.dumps(
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}))
        msg = await asyncio.wait_for(fut, timeout=timeout)
        if "error" in msg:
            raise RuntimeError(msg["error"])
        return msg.get("result", {})

    async def wait_for_notification(self, method, timeout=5.0):
        async def _wait():
            while True:
                for m, params in self.notifications:
                    if m == method:
                        return params
                await asyncio.sleep(0.02)
        return await asyncio.wait_for(_wait(), timeout=timeout)

    async def close(self):
        self._task.cancel()


async def _serve(border):
    async def on_conn(ws):
        await border.accept_edge_ws(ws)
    server = await websockets.serve(on_conn, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def _enroll(border, port, member_id="risk/phone1"):
    token = border.risk.issue_token(label="phone1")["token"]
    ws = await websockets.connect(f"ws://127.0.0.1:{port}")
    challenge = asyncio.get_event_loop().create_future()

    def _on_challenge(params):
        if not challenge.done():
            challenge.set_result(bytes.fromhex(params["nonce"]))
        return {}

    phone = _FakePhone(ws, handlers={
        "n2n/edge/challenge": _on_challenge,
        "n2n/edge/heartbeat": lambda p: {},
    })
    nonce = await asyncio.wait_for(challenge, timeout=5.0)
    cert_pem, key_pem = certs.create_self_signed(member_id)
    signature = RiskManager.sign_challenge(key_pem, nonce).hex()
    resp = await phone.call("in2n/enroll", {
        "token": token, "member_id": member_id, "cert_pem": cert_pem,
        "signature": signature, "runtime_kind": "mobile"})
    assert resp["pinned"] is True
    return phone


def _make_pending_approval(border, peer="risk/somepeer"):
    inv_id = border.manager._conn.execute(
        "INSERT INTO remote_invocation_record (direction, peer_identity, target_type, "
        "target_name, decision, outcome) VALUES ('inbound', ?, 'skill', 'reboot-router', "
        "'approval_required', 'pending')", (peer,)).lastrowid
    border.manager._conn.commit()
    appr = border.authz.create_approval(inv_id)
    return inv_id, appr["approval_id"]


def test_notify_approval_pushes_to_connected_edge_channels(tmp_path):
    """Closes T011 (FR-001): notify_approval() pushes to every connected edge
    channel with content_type='approval' and the expected fields — the
    first real delivery mechanism behind this hook."""
    asyncio.run(_notify_approval_pushes(tmp_path))


async def _notify_approval_pushes(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        inv_id, approval_id = _make_pending_approval(border, peer="risk/somepeer")

        border.notify_approval(inv_id, "risk/somepeer", "skill", "reboot-router")

        params = await phone.wait_for_notification("n2n/edge/message")
        assert params["content_type"] == "approval"
        assert params["approval_id"] == approval_id
        assert params["target_type"] == "skill"
        assert params["target_name"] == "reboot-router"
        assert params["requesting_agent"] == "risk/somepeer"
        assert params["risk_name"] == "risk"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_notify_approval_no_connected_edges_is_a_noop(tmp_path):
    """No connected edge nodes -> notify_approval() must not raise or hang."""
    asyncio.run(_notify_approval_noop(tmp_path))


async def _notify_approval_noop(tmp_path):
    border = _border(tmp_path / "border")
    inv_id, _ = _make_pending_approval(border)
    border.notify_approval(inv_id, "risk/somepeer", "skill", "reboot-router")  # must not raise
    await asyncio.sleep(0.05)
    border.manager.close()


def test_edge_approval_resolve_calls_existing_resolve_approval_unchanged(tmp_path):
    """Closes T012 (FR-004): n2n/edge/approval_resolve calls the EXISTING
    Authorizer.resolve_approval(..., via='biometric') unchanged -- confirm
    resolved_via='biometric' in the DB row."""
    asyncio.run(_edge_approval_resolve(tmp_path))


async def _edge_approval_resolve(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        _, approval_id = _make_pending_approval(border)

        resp = await phone.call("n2n/edge/approval_resolve",
                                {"approval_id": approval_id, "action": "approve"})
        assert resp["resolved"] is True

        row = border.manager._conn.execute(
            "SELECT status, resolved_via FROM approval_request WHERE id=?",
            (approval_id,)).fetchone()
        assert row["status"] == "approved"
        assert row["resolved_via"] == "biometric"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_approval_resolve_confirmation_method_passthrough(tmp_path):
    """Feature 072, research D4: an explicit confirmation_method (e.g. an
    Apple Watch relaying through the phone) is recorded as-is, never coerced
    to 'biometric' -- the whole point of this field is that the Border's own
    audit record must not claim a biometric confirmation that never happened."""
    asyncio.run(_edge_approval_resolve_confirmation_method(tmp_path))


async def _edge_approval_resolve_confirmation_method(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        _, approval_id = _make_pending_approval(border)

        resp = await phone.call("n2n/edge/approval_resolve",
                                {"approval_id": approval_id, "action": "approve",
                                 "confirmation_method": "watch_passcode"})
        assert resp["resolved"] is True

        row = border.manager._conn.execute(
            "SELECT status, resolved_via FROM approval_request WHERE id=?",
            (approval_id,)).fetchone()
        assert row["status"] == "approved"
        assert row["resolved_via"] == "watch_passcode"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_first_resolution_wins_cli_then_phone(tmp_path):
    """Closes T012's second half: if the CLI/HTTP path (n2n_approve) resolves
    an approval first, a subsequent phone resolution attempt on the SAME
    approval is a no-op -- the existing 'first resolution wins' behavior
    (resolve_approval's WHERE status='pending' clause), not new logic."""
    asyncio.run(_first_resolution_wins(tmp_path))


async def _first_resolution_wins(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        _, approval_id = _make_pending_approval(border)

        # CLI/HTTP path resolves it first (denies).
        border.authz.resolve_approval(approval_id, "deny", via="cli")

        # Phone attempts to approve the SAME (already-resolved) approval.
        resp = await phone.call("n2n/edge/approval_resolve",
                                {"approval_id": approval_id, "action": "approve"})
        assert resp["resolved"] is True  # existing resolve_approval() always reports True...
        # ...but 073/FR-005/research D6 distinguishes this no-op from a real
        # first-time resolve, so a notification action (or the watch/phone
        # UI) can show "already resolved" instead of a false success.
        assert resp["already_resolved"] is True

        row = border.manager._conn.execute(
            "SELECT status, resolved_via FROM approval_request WHERE id=?",
            (approval_id,)).fetchone()
        # ...but the row itself was never double-applied: still denied via cli.
        assert row["status"] == "denied"
        assert row["resolved_via"] == "cli"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_approval_resolve_already_resolved_false_on_first_resolution(tmp_path):
    """073/FR-005, research D6: a resolution that actually transitions a
    still-pending approval reports already_resolved=False -- the counterpart
    to test_first_resolution_wins_cli_then_phone's True case above."""
    asyncio.run(_edge_approval_resolve_first_time(tmp_path))


async def _edge_approval_resolve_first_time(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        _, approval_id = _make_pending_approval(border)

        resp = await phone.call("n2n/edge/approval_resolve",
                                {"approval_id": approval_id, "action": "approve"})
        assert resp["resolved"] is True
        assert resp["already_resolved"] is False
        await phone.close()
    finally:
        server.close()
    border.manager.close()
