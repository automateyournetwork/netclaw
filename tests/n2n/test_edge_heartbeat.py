"""Edge node heartbeat / BASE_FLOOR-equivalent health tests (feature 066, US3)."""

import asyncio

import websockets

from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService
from bgp.federation.risk import RiskManager, BASE_FLOOR
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
        import json
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
        import json
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


def test_disconnected_edge_node_reflects_unreachable(tmp_path):
    """Closes T035: a disconnected edge node's state (the health-tracking
    mechanism BASE_FLOOR's guarantee reduces to) reflects unreachable
    promptly — via WS close detection, not by waiting through a real
    heartbeat-miss window (which is a slower backup path for a socket that
    doesn't cleanly report its own closure)."""
    asyncio.run(_disconnected_edge_node_reflects_unreachable(tmp_path))


async def _disconnected_edge_node_reflects_unreachable(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        assert border.risk.get_member("risk/phone1")["state"] == "active"

        await phone.close()
        await border.edge_channels["risk/phone1"].close()
        await asyncio.sleep(0.05)

        assert "risk/phone1" not in border.edge_channels
        assert border.risk.get_member("risk/phone1")["state"] == "unreachable"
    finally:
        server.close()
    border.manager.close()


def test_connected_heartbeating_edge_node_with_zero_skills_passes_base_floor(tmp_path):
    """Closes T036 (the positive case complementing T035/G4): a connected,
    heartbeating node_type='edge' member with zero skills in scope
    (floor_scope('edge') == [], D5/T010) still gets the same
    health-monitoring guarantee BASE_FLOOR exists for — proven by directly
    exercising the same heartbeat check the periodic loop runs
    (_edge_heartbeat_once) and confirming it updates health and keeps the
    member in a healthy/active state, with no skill ever delivered."""
    asyncio.run(_connected_heartbeating_edge_node_passes_base_floor(tmp_path))


async def _connected_heartbeating_edge_node_passes_base_floor(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        mem = border.risk.get_member("risk/phone1")
        assert mem["scope"] == "[]"  # zero skills, unlike BASE_FLOOR
        for base in BASE_FLOOR:
            assert base["name"] not in mem["scope"]

        ch = border.edge_channels["risk/phone1"]
        ok = await border._edge_heartbeat_once("risk/phone1", ch)
        assert ok is True

        mem = border.risk.get_member("risk/phone1")
        assert mem["state"] == "active"  # still healthy — never delivered a skill
        import json
        health = json.loads(mem["health"] or "{}")
        assert "last_heartbeat" in health

        await phone.close()
    finally:
        server.close()
    border.manager.close()
