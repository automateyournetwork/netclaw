"""Border-to-phone push channel tests (feature 066, US2)."""

import asyncio

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
    """Mirrors the one in test_edge_enrollment.py — a minimal WS client
    standing in for the Dart app."""

    def __init__(self, ws, handlers=None):
        self.ws = ws
        self.handlers = handlers or {}
        self.received = []
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

    received = []

    def _on_message(params):
        received.append(params)
        return {"received": True}

    phone = _FakePhone(ws, handlers={
        "n2n/edge/challenge": _on_challenge,
        "n2n/edge/heartbeat": lambda p: {},
        "n2n/edge/message": _on_message,
    })
    phone.received = received
    nonce = await asyncio.wait_for(challenge, timeout=5.0)
    cert_pem, key_pem = certs.create_self_signed(member_id)
    signature = RiskManager.sign_challenge(key_pem, nonce).hex()
    resp = await phone.call("in2n/enroll", {
        "token": token, "member_id": member_id, "cert_pem": cert_pem,
        "signature": signature, "runtime_kind": "mobile"})
    assert resp["pinned"] is True
    return phone


def test_push_to_edge_delivers_explicit_message_only(tmp_path):
    asyncio.run(_push_to_edge_delivers_explicit_message_only(tmp_path))


async def _push_to_edge_delivers_explicit_message_only(tmp_path):
    """Closes FR-008: push_to_edge is the ONLY path that ever calls
    n2n/edge/message — a message pushed via it reaches the phone; nothing
    else in the codebase triggers that method (grep-verified, not just
    behaviorally: the Border's own edge handler map has no server-side
    handler for it at all, since it is Border-initiated only)."""
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        result = await border.push_to_edge("risk/phone1", {
            "content_type": "text",
            "content": "Toronto branch WAN outage detected — 14 locations affected.",
            "designated_by": "agent",
            "pushed_at": "2026-07-22T21:40:00Z",
        })
        assert result == {"received": True}
        assert len(phone.received) == 1
        assert phone.received[0]["content"] == (
            "Toronto branch WAN outage detected — 14 locations affected.")

        # Not connected: push_to_edge on a never-enrolled member fails cleanly.
        with pytest.raises(ValueError):
            await border.push_to_edge("risk/nobody", {"content_type": "text", "content": "x"})

        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_all_content_types_round_trip(tmp_path):
    asyncio.run(_all_content_types_round_trip(tmp_path))


async def _all_content_types_round_trip(tmp_path):
    """Closes T028: text/voice/image all round-trip through
    push_to_edge/n2n/edge/message unmodified."""
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        cases = [
            {"content_type": "text", "content": "hello"},
            {"content_type": "voice", "content": "ZmFrZSB2b2ljZSBieXRlcw=="},
            {"content_type": "image", "content": "ZmFrZSBpbWFnZSBieXRlcw=="},
        ]
        for case in cases:
            payload = dict(case, designated_by="agent", pushed_at="2026-07-22T21:40:00Z")
            result = await border.push_to_edge("risk/phone1", payload)
            assert result == {"received": True}
        assert len(phone.received) == len(cases)
        for expected, actual in zip(cases, phone.received):
            assert actual["content_type"] == expected["content_type"]
            assert actual["content"] == expected["content"]
        await phone.close()
    finally:
        server.close()
    border.manager.close()


def test_push_to_edge_on_disconnected_member_fails_cleanly_not_hangs(tmp_path):
    """Closes T033: push_to_edge() against a member_id with no entry in
    edge_channels raises promptly (never attempts n2n/edge/message and never
    hangs) — the daemon's POST /n2n/edge/push route is what then falls back
    to the push-notification path (push_notify.send_push_notification),
    keeping push_to_edge single-purpose like delegate_to_member()."""
    asyncio.run(_push_to_edge_on_disconnected_member_fails_cleanly(tmp_path))


async def _push_to_edge_on_disconnected_member_fails_cleanly(tmp_path):
    border = _border(tmp_path / "border")
    server, port = await _serve(border)
    try:
        phone = await _enroll(border, port)
        await phone.close()
        border.edge_channels.pop("risk/phone1", None)  # simulate disconnect

        async def _call():
            return await border.push_to_edge("risk/phone1", {"content_type": "text", "content": "x"})

        with pytest.raises(ValueError):
            await asyncio.wait_for(_call(), timeout=2.0)
    finally:
        server.close()
    border.manager.close()


def test_send_push_notification_dispatches_to_registered_platform(tmp_path, monkeypatch):
    """push_notify.send_push_notification routes to FCM or APNs based on the
    member's registered push_platform, and raises cleanly when nothing is
    registered — mocked at the HTTP layer since no real Firebase/Apple
    credentials exist in this environment (unverified against a real
    delivery; see push_notify.py's module docstring)."""
    asyncio.run(_send_push_notification_dispatches(tmp_path, monkeypatch))


async def _send_push_notification_dispatches(tmp_path, monkeypatch):
    from bgp.federation import push_notify

    async def _fake_send_fcm(token, content):
        return {"via": "fcm", "token": token}

    monkeypatch.setattr(push_notify, "send_fcm", _fake_send_fcm)
    # No send_apns to patch: spec 103 consolidated iOS onto the FCM path, since
    # the client registers an FCM registration token rather than the raw APNs
    # device token api.push.apple.com requires. This test had kept patching a
    # send_apns that no longer exists and had been failing on main ever since;
    # it now asserts the consolidation instead of the removed function.
    fcm_member = {"member_id": "risk/phone1", "push_platform": "fcm", "push_token": "tok-fcm"}
    apns_member = {"member_id": "risk/phone2", "push_platform": "apns", "push_token": "tok-apns"}
    unregistered = {"member_id": "risk/phone3", "push_platform": None, "push_token": None}

    assert (await push_notify.send_push_notification(fcm_member, {"content_type": "text"}))["via"] == "fcm"
    # platform='apns' still routes through FCM — accepted so devices enrolled
    # before that decision keep working without re-registering.
    assert (await push_notify.send_push_notification(apns_member, {"content_type": "text"}))["via"] == "fcm"
    with pytest.raises(RuntimeError):
        await push_notify.send_push_notification(unregistered, {"content_type": "text"})
    # A genuinely raw APNs device token must be rejected loudly rather than sent
    # to FCM, where it would fail as an opaque vendor error.
    with pytest.raises(RuntimeError, match="raw APNs"):
        await push_notify.send_push_notification(
            {"member_id": "risk/phone4", "push_platform": "apns", "push_token": "a" * 64},
            {"content_type": "text"})


def test_n2n_edge_message_has_no_inbound_handler(tmp_path):
    """Structural proof backing FR-008's directionality: the Border's edge
    handler map (_edge_border_handlers) never registers n2n/edge/message —
    it is Border-initiated only, so a phone can never push content INTO the
    Border via this method."""
    border = _border(tmp_path / "border")
    assert "n2n/edge/message" not in border._edge_border_handlers
    border.manager.close()
