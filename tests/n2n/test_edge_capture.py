"""Bidirectional capture tests (feature 068, US2/US3)."""

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
        self._next_id = 0
        self._pending: dict = {}
        self._task = asyncio.create_task(self._loop())

    async def _loop(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                if "method" in msg:
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

    async def close(self):
        self._task.cancel()


async def _serve(border):
    async def on_conn(ws):
        await border.accept_edge_ws(ws)
    server = await websockets.serve(on_conn, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def _enroll(border, port, member_id="risk/phone1", capture_handler=None):
    token = border.risk.issue_token(label="phone1")["token"]
    ws = await websockets.connect(f"ws://127.0.0.1:{port}")
    challenge = asyncio.get_event_loop().create_future()

    def _on_challenge(params):
        if not challenge.done():
            challenge.set_result(bytes.fromhex(params["nonce"]))
        return {}

    handlers = {"n2n/edge/challenge": _on_challenge, "n2n/edge/heartbeat": lambda p: {}}
    if capture_handler:
        handlers["n2n/edge/capture"] = capture_handler
    phone = _FakePhone(ws, handlers=handlers)
    nonce = await asyncio.wait_for(challenge, timeout=5.0)
    cert_pem, key_pem = certs.create_self_signed(member_id)
    signature = RiskManager.sign_challenge(key_pem, nonce).hex()
    resp = await phone.call("in2n/enroll", {
        "token": token, "member_id": member_id, "cert_pem": cert_pem,
        "signature": signature, "runtime_kind": "mobile"})
    assert resp["pinned"] is True
    return phone


async def _wait_for_terminal(border, task_id, timeout=5.0):
    async def _wait():
        while True:
            status = border.tasks.status(task_id)
            if status["state"] in ("completed", "failed", "cancelled"):
                return status
            await asyncio.sleep(0.02)
    return await asyncio.wait_for(_wait(), timeout=timeout)


def test_delegate_resolves_edge_node_and_calls_capture_not_tasks_submit(tmp_path):
    """Closes T020: n2n_delegate(target_name='camera.capture', ...) against a
    risk containing only an edge node with that capability resolves to the
    edge node (via the UNMODIFIED RiskRouter) and calls n2n/edge/capture
    over its edge channel, not n2n/tasks/submit."""
    asyncio.run(_delegate_resolves_edge_node(tmp_path))


async def _delegate_resolves_edge_node(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    called = []

    def _on_capture(params):
        called.append(params)
        return {"decision": "captured", "content_type": "image", "content": "ZmFrZQ=="}

    try:
        phone = await _enroll(border, port, capture_handler=_on_capture)
        border.risk.set_capture_capabilities("risk/phone1", ["camera.capture"])

        result = await border.route_and_delegate("camera.capture", "")
        assert result["member_id"] == "risk/phone1"
        task_id = result["task_id"]

        status = await _wait_for_terminal(border, task_id)
        assert status["state"] == "completed"
        assert called == [{"capability": "camera.capture"}]

        task_result = border.tasks.result(task_id)
        assert task_result["output_text"]["decision"] == "captured"
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_declined_capture_surfaces_as_explicit_failure(tmp_path):
    """Closes T021 (FR-009/SC-004): a declined capture flows back as an
    explicit failure (task state 'failed'), never 'completed' with an empty
    payload."""
    asyncio.run(_declined_capture_fails(tmp_path))


async def _declined_capture_fails(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)

    def _on_capture(params):
        return {"decision": "declined", "reason": "permission_denied"}

    try:
        phone = await _enroll(border, port, capture_handler=_on_capture)
        border.risk.set_capture_capabilities("risk/phone1", ["camera.capture"])

        result = await border.route_and_delegate("camera.capture", "")
        task_id = result["task_id"]

        status = await _wait_for_terminal(border, task_id)
        assert status["state"] == "failed"

        task_result = border.tasks.result(task_id)
        assert "permission_denied" in task_result["error"]
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_capability_only_on_disconnected_edge_fails_cleanly(tmp_path):
    """Closes T022: delegating to a capability only a DISCONNECTED edge node
    advertises fails cleanly (member_unreachable), consistent with how an
    unreachable agent member is already handled -- no cold-start attempted
    for a phone, so this fails fast, not hangs."""
    asyncio.run(_disconnected_edge_capability(tmp_path))


async def _disconnected_edge_capability(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        border.risk.set_capture_capabilities("risk/phone1", ["camera.capture"])
        await phone.close()
        border.edge_channels.pop("risk/phone1", None)  # simulate disconnect

        result = await asyncio.wait_for(
            border.route_and_delegate("camera.capture", ""), timeout=2.0)
        assert result.get("error") == "member_unreachable"
    finally:
        server.close()
    border.manager.close()


def test_disabled_capability_invisible_to_router(tmp_path):
    """Closes T023 (FR-007a/SC-008): a capability omitted from
    register_capabilities makes RiskRouter.candidates() NOT include the edge
    node at all -- inspecting scope directly, not just observing a request
    fail."""
    asyncio.run(_disabled_capability_invisible(tmp_path))


async def _disabled_capability_invisible(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        # Enable only camera.capture -- audio.record deliberately omitted.
        border.risk.set_capture_capabilities("risk/phone1", ["camera.capture"])

        cands_enabled = border.router.candidates("camera.capture")
        assert any(m["member_id"] == "risk/phone1" for m in cands_enabled)

        cands_disabled = border.router.candidates("audio.record")
        assert not any(m["member_id"] == "risk/phone1" for m in cands_disabled)

        mem = border.risk.get_member("risk/phone1")
        names = {e["name"] for e in json.loads(mem["scope"])}
        assert "audio.record" not in names
        assert "camera.capture" in names
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_set_capture_capabilities_rejects_unknown_name(tmp_path):
    asyncio.run(_rejects_unknown_name(tmp_path))


async def _rejects_unknown_name(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        with pytest.raises(ValueError):
            border.risk.set_capture_capabilities("risk/phone1", ["not.a.real.capability"])
        await phone.close()
    finally:
        server.close()
    border.manager.close()
