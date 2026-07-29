"""Phone-to-Border command channel tests (feature 067, US1/US2/US3)."""

import asyncio
import json
import os

import pytest
import websockets

from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService
from bgp.federation.risk import RiskManager
from bgp.federation import certs, gateway


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
                    if msg.get("id") is None:
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


def test_edge_ask_creates_task_and_returns_immediately(tmp_path, monkeypatch):
    """Closes T008: n2n/edge/ask creates a delegated_task (target_type=
    'edge_ask') and returns a task_id immediately -- run_agent_turn is
    mocked so this test needs no real `openclaw agent` binary."""
    asyncio.run(_edge_ask_creates_task(tmp_path, monkeypatch))


async def _edge_ask_creates_task(tmp_path, monkeypatch):
    async def _fake_run_agent_turn(prompt, session_key="n2n", **kwargs):
        assert kwargs.get("untrusted") is False or "untrusted" not in kwargs
        return f"Answer to: {prompt}", 123
    monkeypatch.setattr(gateway, "run_agent_turn", _fake_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        resp = await phone.call("n2n/edge/ask", {"text": "check BGP on core routers"})
        assert "task_id" in resp
        task_id = resp["task_id"]

        row = border.manager._conn.execute(
            "SELECT * FROM delegated_task WHERE task_id=?", (task_id,)).fetchone()
        assert row is not None
        assert row["target_type"] == "edge_ask"
        assert row["peer_identity"] == "risk/phone1"
        assert row["input_text"] == "check BGP on core routers"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_result_pushed_to_connected_phone(tmp_path, monkeypatch):
    """Closes T009: the completed task's answer is pushed via
    n2n/edge/ask_result to the connected phone."""
    asyncio.run(_edge_ask_result_pushed(tmp_path, monkeypatch))


async def _edge_ask_result_pushed(tmp_path, monkeypatch):
    async def _fake_run_agent_turn(prompt, session_key="n2n", **kwargs):
        return "Checked all 4 core routers -- all healthy.", 55
    monkeypatch.setattr(gateway, "run_agent_turn", _fake_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        resp = await phone.call("n2n/edge/ask", {"text": "check BGP"})
        task_id = resp["task_id"]

        result = await phone.wait_for_notification("n2n/edge/ask_result")
        assert result["task_id"] == task_id
        assert result["state"] == "completed"
        assert "all healthy" in result["output_text"]
        assert result["tokens_used"] == 55
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_failure_surfaces_not_hangs(tmp_path, monkeypatch):
    """Closes T010 (FR-010): a failing agent turn surfaces as a failed task
    via n2n/edge/ask_result, never a silent hang."""
    asyncio.run(_edge_ask_failure_surfaces(tmp_path, monkeypatch))


async def _edge_ask_failure_surfaces(tmp_path, monkeypatch):
    async def _fake_run_agent_turn(prompt, session_key="n2n", **kwargs):
        raise RuntimeError("no authorization for that action")
    monkeypatch.setattr(gateway, "run_agent_turn", _fake_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        resp = await phone.call("n2n/edge/ask", {"text": "do something unauthorized"})
        task_id = resp["task_id"]

        result = await asyncio.wait_for(
            phone.wait_for_notification("n2n/edge/ask_result"), timeout=5.0)
        assert result["task_id"] == task_id
        assert result["state"] == "failed"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_task_cancellable_via_existing_mechanism(tmp_path, monkeypatch):
    """Closes T013 (FR-012): an edge-ask task_id is cancellable via
    n2n/tasks/cancel -- the SAME Invoker.handle_task_cancel member-delegation
    already uses, registered under the edge channel too."""
    asyncio.run(_edge_ask_task_cancellable(tmp_path, monkeypatch))


async def _edge_ask_task_cancellable(tmp_path, monkeypatch):
    started = asyncio.Event()

    async def _slow_run_agent_turn(prompt, session_key="n2n", **kwargs):
        started.set()
        await asyncio.sleep(30)
        return "too slow", 0
    monkeypatch.setattr(gateway, "run_agent_turn", _slow_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        resp = await phone.call("n2n/edge/ask", {"text": "slow request"})
        task_id = resp["task_id"]
        await asyncio.wait_for(started.wait(), timeout=5.0)

        cancel_resp = await phone.call("n2n/tasks/cancel", {"task_id": task_id})
        assert cancel_resp["cancelled"] is True

        result = await asyncio.wait_for(
            phone.wait_for_notification("n2n/edge/ask_result"), timeout=5.0)
        assert result["state"] == "cancelled"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_cancel_after_completion_is_a_noop(tmp_path, monkeypatch):
    """Closes T014: cancelling a task that already completed never flips a
    completed result back to cancelled (the race edge case from spec.md)."""
    asyncio.run(_edge_ask_cancel_after_completion(tmp_path, monkeypatch))


async def _edge_ask_cancel_after_completion(tmp_path, monkeypatch):
    async def _fast_run_agent_turn(prompt, session_key="n2n", **kwargs):
        return "done already", 1
    monkeypatch.setattr(gateway, "run_agent_turn", _fast_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        resp = await phone.call("n2n/edge/ask", {"text": "fast request"})
        task_id = resp["task_id"]
        await phone.wait_for_notification("n2n/edge/ask_result")

        cancel_resp = await phone.call("n2n/tasks/cancel", {"task_id": task_id})
        assert cancel_resp["cancelled"] is False  # worker already finished

        status = await phone.call("n2n/tasks/status", {"task_id": task_id})
        assert status["state"] == "completed"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_task_owner_bound_to_submitting_device(tmp_path, monkeypatch):
    """Closes T016's underlying premise (FR-004/NCFED -00 SS9.2/SS14.6):
    task retrieval is owner-bound to the submitting edge node exactly as it
    already is for a member -- no edge-specific authorization branch exists
    to accidentally special-case a phone (the absence of special-casing IS
    the point of research D3/FR-004)."""
    asyncio.run(_edge_ask_task_owner_bound(tmp_path, monkeypatch))


async def _edge_ask_task_owner_bound(tmp_path, monkeypatch):
    async def _fake_run_agent_turn(prompt, session_key="n2n", **kwargs):
        await asyncio.sleep(10)
        return "unused", 0
    monkeypatch.setattr(gateway, "run_agent_turn", _fake_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone1 = await _enroll(border, port, member_id="risk/phone1")
        resp = await phone1.call("n2n/edge/ask", {"text": "phone1's question"})
        task_id = resp["task_id"]

        phone2 = await _enroll(border, port, member_id="risk/phone2")
        status = await phone2.call("n2n/tasks/status", {"task_id": task_id})
        assert status["state"] == "unknown"  # not phone2's task -- invisible to it

        own_status = await phone1.call("n2n/tasks/status", {"task_id": task_id})
        assert own_status["state"] in ("working", "submitted")
        await phone1.close()
        await phone2.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_bare_attachment_still_reaches_agent_turn(tmp_path, monkeypatch):
    """Closes T016 (feature 068, US2/FR-005): n2n/edge/ask with only an
    attachment and empty text still reaches run_agent_turn() with a
    non-empty prompt (folds the attachment in, per the message_file path) --
    a bare capture with no accompanying text is a valid request."""
    asyncio.run(_edge_ask_bare_attachment(tmp_path, monkeypatch))


async def _edge_ask_bare_attachment(tmp_path, monkeypatch):
    calls = []

    async def _fake_run_agent_turn(prompt, session_key="n2n", **kwargs):
        calls.append((prompt, kwargs.get("message_file")))
        return "I see a rack with a red fault LED.", 42
    monkeypatch.setattr(gateway, "run_agent_turn", _fake_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        resp = await phone.call("n2n/edge/ask", {
            "attachment": {"content_type": "image", "content": "ZmFrZSBpbWFnZSBieXRlcw=="}
        })
        task_id = resp["task_id"]
        result = await phone.wait_for_notification("n2n/edge/ask_result")
        assert result["task_id"] == task_id
        assert result["state"] == "completed"

        assert len(calls) == 1
        prompt, message_file = calls[0]
        assert prompt  # non-empty even though text was never provided
        assert message_file is not None  # folded via --message-file, not a raw CLI arg
        assert not os.path.exists(message_file)  # cleaned up after the turn
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_neither_text_nor_attachment_refused(tmp_path):
    asyncio.run(_edge_ask_neither(tmp_path))


async def _edge_ask_neither(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        with pytest.raises(RuntimeError):
            await phone.call("n2n/edge/ask", {})
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_edge_ask_session_key_never_contains_a_slash(tmp_path, monkeypatch):
    """Every edge member_id is risk-scoped ("risk/<label>") and openclaw
    agent's --session-id/--session-key rejects a value containing "/" with
    "Invalid session ID" -- confirmed via a real device against a real
    Border (068 polish). session_key must be sanitized before reaching
    run_agent_turn(), not just prefixed."""
    asyncio.run(_edge_ask_session_key_sanitized(tmp_path, monkeypatch))


async def _edge_ask_session_key_sanitized(tmp_path, monkeypatch):
    seen_session_keys = []

    async def _fake_run_agent_turn(prompt, session_key="n2n", **kwargs):
        seen_session_keys.append(session_key)
        return "ok", 0

    monkeypatch.setattr(gateway, "run_agent_turn", _fake_run_agent_turn)

    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port, member_id="risk/has-a-slash")
        resp = await phone.call("n2n/edge/ask", {"text": "hello"})
        result = await phone.wait_for_notification("n2n/edge/ask_result")
        assert result["task_id"] == resp["task_id"]
        await phone.close()
    finally:
        server.close()
    border.manager.close()

    assert seen_session_keys, "run_agent_turn was never called"
    assert "/" not in seen_session_keys[0], seen_session_keys[0]
    assert seen_session_keys[0] == "n2n-edge-risk_has-a-slash"
