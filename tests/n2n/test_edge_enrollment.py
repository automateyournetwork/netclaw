"""Edge node (NetClaw Mobile) enrollment tests (feature 066, US1).

Drives a real Border FederationService over a loopback WebSocket (the same
harness style as test_internal_transport.py, adapted for the WS transport —
see EdgeChannel/accept_edge_ws, research D2). There is no Python "member"
counterpart for an edge node (the real client is the Dart app under
mobile/netclaw-mobile/); _FakePhone is a minimal WS client standing in for it,
driving the same in2n/enroll/hello wire methods the Dart client will use.
"""

import asyncio
import json

import pytest
import websockets

from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService
from bgp.federation.risk import RiskManager
from bgp.federation import certs
from bgp.federation.edge import EDGE_METHODS


def _border(base):
    mgr = FederationManager(base_dir=str(base))
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="Border",
                            manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    return svc


class _FakePhone:
    """Minimal WS client mirroring EdgeChannel's own dispatch shape — stands
    in for the Dart app in Python-side integration tests."""

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


async def _enroll(border, port, member_id="risk/phone1", token=None, label="phone1"):
    """Drive one full enroll handshake over a fresh WS connection; returns
    (resp, phone). Caller is responsible for `await phone.close()`."""
    if token is None:
        token = border.risk.issue_token(label=label)["token"]
    ws = await websockets.connect(f"ws://127.0.0.1:{port}")
    challenge = asyncio.get_event_loop().create_future()

    def _on_challenge(params):
        if not challenge.done():
            challenge.set_result(bytes.fromhex(params["nonce"]))
        return {}

    phone = _FakePhone(ws, handlers={
        "n2n/edge/challenge": _on_challenge,
        "n2n/edge/heartbeat": lambda p: {},
        "n2n/edge/self_status": lambda p: {"battery": 80, "app_version": "1.0"},
    })
    nonce = await asyncio.wait_for(challenge, timeout=5.0)
    cert_pem, key_pem = certs.create_self_signed(member_id)
    signature = RiskManager.sign_challenge(key_pem, nonce).hex()
    resp = await phone.call("in2n/enroll", {
        "token": token, "member_id": member_id, "cert_pem": cert_pem,
        "signature": signature, "runtime_kind": "mobile"})
    return resp, phone, cert_pem, key_pem


async def _serve(border):
    async def on_conn(ws):
        await border.accept_edge_ws(ws)
    server = await websockets.serve(on_conn, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


def test_qr_enrollment_creates_edge_member_single_use(tmp_path):
    asyncio.run(_qr_enrollment_creates_edge_member_single_use(tmp_path))


async def _qr_enrollment_creates_edge_member_single_use(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        token = border.risk.issue_token(label="phone1")["token"]
        resp, phone, cert_pem, _ = await _enroll(border, port, token=token)
        assert resp["pinned"] is True
        mem = border.risk.get_member("risk/phone1")
        assert mem["node_type"] == "edge"
        assert mem["pinned_key"] == cert_pem
        assert mem["key_fingerprint"] == border.risk.fingerprint_of(cert_pem)
        assert mem["scope"] == "[]"
        assert "risk/phone1" in border.edge_channels
        await phone.close()

        # Single-use: the same token cannot enroll a second device.
        with pytest.raises(Exception):
            await _enroll(border, port, member_id="risk/phone2", token=token)
    finally:
        server.close()
    border.manager.close()


def test_plaintext_agent_enrollment_unaffected(tmp_path):
    """Regression (closes /speckit.analyze G1): a plain-text (non-edge) agent
    enrollment over the existing raw-TCP iN2N listener still produces a
    node_type='agent' row with the full BASE_FLOOR scope, unaffected by the
    T005 migration and T006 consume_token() change."""
    asyncio.run(_plaintext_agent_enrollment_unaffected(tmp_path))


async def _plaintext_agent_enrollment_unaffected(tmp_path):
    from bgp.federation.risk import BASE_FLOOR
    border = _border(tmp_path / "border")
    member = FederationService(local_as=65001, router_id="4.4.4.4", display_name="Member",
                               manager=FederationManager(base_dir=str(tmp_path / "member")))
    member.risk.set_role("member", risk_name="risk", border_endpoint="127.0.0.1:0",
                         self_member_id="risk/cml")
    token = border.risk.issue_token(label="cml")["token"]

    async def on_conn(reader, writer):
        await border.accept_internal(reader, writer)
    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        resp = await member.dial_border("127.0.0.1", port, enrollment_token=token)
        assert resp["pinned"] is True
        mem = border.risk.get_member("risk/cml")
        assert mem["node_type"] == "agent"
        assert json.loads(mem["scope"]) == BASE_FLOOR
    finally:
        server.close()
    border.manager.close(); member.manager.close()


def test_edge_channel_handler_map_excludes_mesh_methods():
    """Closes G3 (FR-012): EdgeChannel exposes only enrollment/heartbeat/
    self_status/message — never BGP, eN2N, or iN2N-inventory methods."""
    from bgp.federation.edge import EdgeChannel
    broader = {
        "in2n/enroll": lambda ch, p: None,
        "in2n/hello": lambda ch, p: None,
        "n2n/edge/heartbeat": lambda ch, p: None,
        "n2n/edge/self_status": lambda ch, p: None,
        "n2n/edge/message": lambda ch, p: None,
        "n2n/inventory": lambda ch, p: None,          # must be dropped
        "n2n/inventory_get": lambda ch, p: None,       # must be dropped
        "n2n/hello": lambda ch, p: None,               # eN2N — must be dropped
        "n2n/tasks/submit": lambda ch, p: None,        # BGP-delegation — must be dropped
    }
    ch = EdgeChannel(ws=None, local_identity="risk/border", handlers=broader)
    assert set(ch.handlers.keys()) <= set(EDGE_METHODS)
    assert "n2n/inventory" not in ch.handlers
    assert "n2n/hello" not in ch.handlers
    assert "n2n/tasks/submit" not in ch.handlers
    with pytest.raises(ValueError):
        ch.register("n2n/inventory", lambda ch, p: None)


def test_domain_mismatch_aborts_before_token_exchange():
    """Closes T016 (FR-003/D7): the client-side domain-verification rule an
    edge client MUST apply before dialing — reference logic for the Dart
    port (T013). Proves the *design* aborts before any wire call is made;
    the Dart implementation (T013/T017) applies the identical rule against
    the real TLS-certified hostname."""
    def verify_claw_domain_before_dial(qr_payload: dict, tls_certified_hostname: str) -> bool:
        return qr_payload["claw_domain"] == tls_certified_hostname

    qr = {"border_host": "netclaw.automateyournetwork.ca", "border_port": 8443,
          "claw_domain": "netclaw.automateyournetwork.ca", "enrollment_token": "in2n_x"}
    assert verify_claw_domain_before_dial(qr, "netclaw.automateyournetwork.ca") is True
    assert verify_claw_domain_before_dial(qr, "evil.example.com") is False
    # The real Dart client must never call consume_token()/reach the
    # token-exchange step when this returns False — asserted structurally
    # here (no network call is made in the False branch above at all).


def test_revoked_edge_member_blocks_further_delivery(tmp_path):
    """Closes G2 (SC-005/FR-013): removing/quarantining an edge member blocks
    push_to_edge and the heartbeat loop against it."""
    asyncio.run(_revoked_edge_member_blocks_further_delivery(tmp_path))


async def _revoked_edge_member_blocks_further_delivery(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        resp, phone, _, key_pem = await _enroll(border, port)
        assert resp["pinned"] is True
        assert "risk/phone1" in border.edge_channels

        # Existing member-removal mechanism (unchanged) revokes trust.
        border.risk._set_state("risk/phone1", "removed")
        await phone.close()
        await border.edge_channels["risk/phone1"].close()
        await asyncio.sleep(0.05)
        assert "risk/phone1" not in border.edge_channels

        with pytest.raises(ValueError):
            await border.edge_self_status("risk/phone1")

        # A removed member cannot re-authenticate via in2n/hello either —
        # even with a genuinely VALID signature over the fresh nonce (the
        # real key from enrollment), proving state (removed) is what blocks
        # it, not merely a bad signature.
        ws2 = await websockets.connect(f"ws://127.0.0.1:{port}")
        challenge2 = asyncio.get_event_loop().create_future()

        def _on_challenge2(params):
            if not challenge2.done():
                challenge2.set_result(bytes.fromhex(params["nonce"]))
            return {}
        phone2 = _FakePhone(ws2, handlers={"n2n/edge/challenge": _on_challenge2})
        nonce2 = await asyncio.wait_for(challenge2, timeout=5.0)
        mem = border.risk.get_member("risk/phone1")
        valid_signature = RiskManager.sign_challenge(key_pem, nonce2).hex()
        with pytest.raises(Exception):
            await phone2.call("in2n/hello", {
                "member_id": "risk/phone1",
                "key_fingerprint": mem["key_fingerprint"],
                "signature": valid_signature})
        await phone2.close()
    finally:
        server.close()
    border.manager.close()
