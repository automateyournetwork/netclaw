"""Token-source logging and re-resolve-after-AUTH_TOKEN_MISMATCH behaviour of
gateway_ws (production incident 2026-11-22: a stale OPENCLAW_GATEWAY_TOKEN
in the service env shadowed the config token, and the cached singleton kept
presenting the rejected token for the life of the process)."""

import hashlib
import json
import logging

import pytest
import websockets

from bgp.federation import gateway_ws
from bgp.federation.gateway_ws import (
    GatewayWsAuthError, GatewayWsClient, GatewayWsError, token_fingerprint)

GOOD = "good-token-value"
STALE = "stale-token-value"


def _gateway(accepted_token):
    async def handler(ws):
        await ws.send(json.dumps({"type": "event", "event": "connect.challenge",
                                  "payload": {"nonce": "n", "ts": 0}}))
        async for raw in ws:
            frame = json.loads(raw)
            if frame["method"] == "connect":
                if frame["params"]["auth"]["token"] != accepted_token:
                    await ws.send(json.dumps({
                        "type": "res", "id": frame["id"], "ok": False,
                        "error": {"code": "INVALID_REQUEST", "message": "unauthorized",
                                  "details": {"code": "AUTH_TOKEN_MISMATCH"}}}))
                    await ws.close()
                    return
                await ws.send(json.dumps({"type": "res", "id": frame["id"], "ok": True,
                                          "payload": {"type": "hello-ok"}}))
                continue
            await ws.send(json.dumps({"type": "res", "id": frame["id"], "ok": True,
                                      "payload": {"echo": frame["method"]}}))
    return handler


def _config(tmp_path, token, port=18789):
    path = tmp_path / "openclaw.json"
    path.write_text(json.dumps({"gateway": {"port": port, "auth": {"token": token}}}))
    return str(path)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for var in ("OPENCLAW_GATEWAY_WS_URL", "OPENCLAW_GATEWAY_TOKEN", "OPENCLAW_CONFIG_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(gateway_ws, "_singleton", None)
    yield


def test_fingerprint_is_sha256_prefix():
    assert token_fingerprint("abc") == hashlib.sha256(b"abc").hexdigest()[:10]
    assert token_fingerprint("") == "none"


def test_source_reported_for_each_origin(tmp_path, monkeypatch):
    path = _config(tmp_path, GOOD)
    assert gateway_ws.resolve_gateway_ws_config_with_source(path)[2] == f"config:{path}"

    ref_path = _config(tmp_path, {"source": "env", "id": "MY_GW_TOKEN"})
    monkeypatch.setenv("MY_GW_TOKEN", GOOD)
    url, token, source = gateway_ws.resolve_gateway_ws_config_with_source(ref_path)
    assert (token, source) == (GOOD, f"secretref-env:MY_GW_TOKEN@{ref_path}")

    # Env token alone shadows the config token -- the incident's root cause.
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", STALE)
    url, token, source = gateway_ws.resolve_gateway_ws_config_with_source(path)
    assert (token, source) == (STALE, "env:OPENCLAW_GATEWAY_TOKEN")
    # The two-tuple API is unchanged.
    assert gateway_ws.resolve_gateway_ws_config(path) == ("ws://127.0.0.1:18789", STALE)


async def test_auth_mismatch_raises_auth_error_and_marks_stale(caplog):
    async with websockets.serve(_gateway(GOOD), "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", STALE, "config:/x")
        with caplog.at_level(logging.INFO, logger="n2n.gateway_ws"):
            with pytest.raises(GatewayWsAuthError) as exc:
                await client.call("ping", {}, timeout_s=5)
        assert isinstance(exc.value, GatewayWsError)
        assert exc.value.code == "AUTH_TOKEN_MISMATCH"
        assert client.auth_failed
        assert token_fingerprint(STALE) in caplog.text
        assert STALE not in caplog.text and STALE not in str(exc.value)
        await client.close()


async def test_singleton_reresolves_token_after_auth_failure(tmp_path, monkeypatch, caplog):
    async with websockets.serve(_gateway(GOOD), "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        monkeypatch.setenv("OPENCLAW_CONFIG_PATH", _config(tmp_path, STALE, port))
        caplog.set_level(logging.INFO, logger="n2n.gateway_ws")

        first = await gateway_ws.get_gateway_ws_client()
        assert first is await gateway_ws.get_gateway_ws_client()  # cached
        with pytest.raises(GatewayWsAuthError):
            await first.call("ping", {}, timeout_s=5)

        # Operator fixes the token source; no process restart.
        _config(tmp_path, GOOD, port)
        second = await gateway_ws.get_gateway_ws_client()
        assert second is not first
        assert await second.call("ping", {}, timeout_s=5) == {"echo": "ping"}
        assert await gateway_ws.get_gateway_ws_client() is second

        text = caplog.text
        assert f"fp={token_fingerprint(STALE)}" in text
        assert f"fp={token_fingerprint(GOOD)}" in text
        assert "re-resolved after auth failure" in text
        assert STALE not in text and GOOD not in text
        await second.close()


async def test_unchanged_env_token_warns_restart_needed(tmp_path, monkeypatch, caplog):
    async with websockets.serve(_gateway(GOOD), "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        monkeypatch.setenv("OPENCLAW_GATEWAY_WS_URL", f"ws://127.0.0.1:{port}")
        monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", STALE)
        caplog.set_level(logging.INFO, logger="n2n.gateway_ws")

        first = await gateway_ws.get_gateway_ws_client()
        with pytest.raises(GatewayWsAuthError):
            await first.call("ping", {}, timeout_s=5)
        second = await gateway_ws.get_gateway_ws_client()
        assert second is not first and second.token_source == "env:OPENCLAW_GATEWAY_TOKEN"
        assert "unchanged" in caplog.text and "restart this process" in caplog.text
        assert STALE not in caplog.text
        await second.close()


async def test_non_auth_handshake_failure_does_not_mark_stale():
    async def handler(ws):
        await ws.send(json.dumps({"type": "event", "event": "connect.challenge", "payload": {}}))
        async for raw in ws:
            frame = json.loads(raw)
            await ws.send(json.dumps({"type": "res", "id": frame["id"], "ok": False,
                                      "error": {"code": "PROTOCOL_MISMATCH"}}))
            return

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = GatewayWsClient(f"ws://127.0.0.1:{port}", GOOD)
        with pytest.raises(GatewayWsError) as exc:
            await client.call("ping", {}, timeout_s=5)
        assert not isinstance(exc.value, GatewayWsAuthError)
        assert not client.auth_failed
        await client.close()
