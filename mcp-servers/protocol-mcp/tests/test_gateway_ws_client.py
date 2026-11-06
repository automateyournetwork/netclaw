"""Unit tests for GatewayWsClient against a minimal fake gateway server.

No live OpenClaw gateway required -- these spin up a local `websockets.serve`
server that speaks just enough of the connect handshake + req/res framing
(docs/gateway/protocol.md) to exercise GatewayWsClient in isolation.
"""

import asyncio
import json

import pytest
import websockets

from bgp.federation.gateway_ws import GatewayWsClient, GatewayWsError

pytestmark = pytest.mark.asyncio


async def _fake_gateway_handler(fail_first_agent_call=False, drop_after_connect=False):
    """Returns a handler coroutine for websockets.serve implementing: send the
    pre-connect challenge event, accept connect handshake (ok:true), then for
    method 'agent' send the real gateway's two-frame sequence (an immediate
    "accepted" ack, THEN the real final result, both with the same request
    id -- matching OpenClaw's own expectFinal behavior confirmed by reading
    its bundled client-C8-EgcVB.js), or simulate a drop, depending on flags."""

    state = {"agent_calls": 0}

    async def handler(ws):
        await ws.send(json.dumps({
            "type": "event", "event": "connect.challenge",
            "payload": {"nonce": "test-nonce", "ts": 0},
        }))
        async for raw in ws:
            frame = json.loads(raw)
            if frame["method"] == "connect":
                await ws.send(json.dumps({
                    "type": "res", "id": frame["id"], "ok": True,
                    "payload": {"type": "hello-ok", "protocol": 4},
                }))
                if drop_after_connect:
                    await ws.close()
                    return
                continue
            if frame["method"] == "agent":
                state["agent_calls"] += 1
                if fail_first_agent_call and state["agent_calls"] == 1:
                    await ws.close()
                    return
                await ws.send(json.dumps({
                    "type": "res", "id": frame["id"], "ok": True,
                    "payload": {"status": "accepted"},
                }))
                await ws.send(json.dumps({
                    "type": "res", "id": frame["id"], "ok": True,
                    "payload": {"result": {"payloads": [{"text": "OK"}]}},
                }))
                continue
            if frame["method"] == "never-responds":
                continue  # deliberately do not respond, for timeout test

    return handler


async def test_connect_handshake_succeeds():
    handler = await _fake_gateway_handler()
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", "test-token")
        await client._ensure_connected()
        assert client._ws is not None
        await client.close()


async def test_request_response_round_trip():
    handler = await _fake_gateway_handler()
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", "test-token")
        payload = await client.call("agent", {"message": "hi"}, timeout_s=5)
        assert payload["result"]["payloads"][0]["text"] == "OK"
        await client.close()


async def test_accepted_ack_is_not_mistaken_for_final_result():
    """The single most important correctness property discovered against the
    live gateway: an intermediate {status: "accepted"} frame must be skipped,
    not returned as if it were the answer. Reproduces a real bug found while
    validating spec 116's fix live (the client returned "(no reply text in
    agent response)" after 0.1s -- it had resolved on the accepted ack)."""
    handler = await _fake_gateway_handler()
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", "test-token")
        payload = await client.call("agent", {"message": "hi"}, timeout_s=5)
        assert "status" not in payload or payload.get("status") != "accepted"
        assert payload["result"]["payloads"][0]["text"] == "OK"
        await client.close()


async def test_reconnect_after_drop():
    handler = await _fake_gateway_handler(fail_first_agent_call=True)
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", "test-token")
        # Spec177 supersedes transparent retry: the first request may already
        # have executed. A distinct later request may reconnect normally.
        with pytest.raises(GatewayWsError, match='before final response'):
            await client.call("agent", {"message": "hi"}, timeout_s=5)
        payload = await client.call("agent", {"message": "distinct request"}, timeout_s=5)
        assert payload["result"]["payloads"][0]["text"] == "OK"
        await client.close()


async def test_timeout_when_no_response():
    handler = await _fake_gateway_handler()
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", "test-token")
        with pytest.raises(asyncio.TimeoutError):
            await client.call("never-responds", {}, timeout_s=0.5)
        await client.close()


async def test_ok_false_response_raises_gateway_ws_error():
    async def handler(ws):
        await ws.send(json.dumps({
            "type": "event", "event": "connect.challenge",
            "payload": {"nonce": "test-nonce", "ts": 0},
        }))
        async for raw in ws:
            frame = json.loads(raw)
            if frame["method"] == "connect":
                await ws.send(json.dumps({"type": "res", "id": frame["id"], "ok": True, "payload": {}}))
                continue
            await ws.send(json.dumps({
                "type": "res", "id": frame["id"], "ok": False,
                "error": {"message": "boom"},
            }))

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", "test-token")
        with pytest.raises(GatewayWsError):
            await client.call("agent", {}, timeout_s=5)
        await client.close()
