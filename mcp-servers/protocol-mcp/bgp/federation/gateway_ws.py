"""Persistent WebSocket JSON-RPC client to the local OpenClaw gateway.

Spec 116 root cause: dispatching an agent turn via the `openclaw agent` CLI
(gateway.py's prior approach) unconditionally sets `cleanupBundleMcpOnRunEnd:
true` in the CLI's own gateway dispatch path, which tears down the gateway's
session-scoped MCP tool runtime at the end of every single turn -- so the next
turn always rebuilds it from cold, even in the same session (measured: ~27s of
fixed cost on every turn, see specs/116-border-turn-latency/research.md).

OpenClaw's own internal `sessions_send` tool (runAgentStep in its bundled
source) calls the identical gateway `agent` RPC method WITHOUT that flag,
proving the runtime is meant to be reused across calls sharing a session key.
This module talks to the same `agent` RPC method the same way, over one
persistent connection per Border process (not one CLI subprocess per turn),
so the gateway's own reuse behavior actually gets to run.

Docs: gateway WS protocol handshake/framing is documented in the vendored
OpenClaw package's docs/gateway/protocol.md (connect handshake, req/res/event
framing). This module implements a minimal client against that protocol --
just enough to send `agent` requests and read matching responses.
"""

import asyncio
import json
import logging
import os
import uuid

import websockets
from websockets.protocol import State as _WsState

logger = logging.getLogger("n2n.gateway_ws")

# feature 057-style override convention (see gateway.py's OPENCLAW_BIN): allow
# the URL/token to be overridden without touching config, e.g. for tests or a
# non-default gateway port.
_ENV_URL = "OPENCLAW_GATEWAY_WS_URL"
_ENV_TOKEN = "OPENCLAW_GATEWAY_TOKEN"

_DEFAULT_OPENCLAW_CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")

_CONNECT_TIMEOUT_S = 10.0
_RECONNECT_BACKOFF_S = 1.0


class GatewayWsError(RuntimeError):
    """Raised when the gateway returns an error response or refuses handshake."""


def resolve_gateway_ws_config(config_path: str = None) -> tuple:
    """Resolve (ws_url, token) the same way the `openclaw` CLI resolves gateway
    connection details today: from openclaw.json's gateway.port/bind/auth.token,
    with an env override for parity with gateway.py's OPENCLAW_BIN pattern.

    Only loopback/local mode is supported (matches the Border's own config and
    the trust boundary the CLI path already operates in -- see
    specs/116-border-turn-latency/contracts/gateway-ws-rpc.md).
    """
    env_url = os.environ.get(_ENV_URL)
    env_token = os.environ.get(_ENV_TOKEN)
    if env_url and env_token:
        return env_url, env_token

    path = config_path or os.environ.get('OPENCLAW_CONFIG_PATH')
    if not path:
        from .runtime import selected
        runtime=selected()
        if runtime.kind!='openclaw':raise GatewayWsError('selected runtime is not OpenClaw')
        path=str(runtime.config)
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    gw = cfg.get("gateway", {})
    port = gw.get("port", 18789)
    url = env_url or f"ws://127.0.0.1:{port}"
    token = env_token or (gw.get("auth", {}) or {}).get("token")
    if not token:
        raise GatewayWsError(
            f"no gateway auth token found in {path} (gateway.auth.token) and "
            f"no {_ENV_TOKEN} override set")
    return url, token


class GatewayWsClient:
    """One persistent WS connection to the gateway, shared across agent turns.

    Not thread-safe across event loops; intended for use within a single
    asyncio event loop (the Border daemon's own loop).
    """

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self._ws = None
        self._lock = asyncio.Lock()
        self._pending = {}  # request id -> asyncio.Future
        self._reader_task = None

    async def _ensure_connected(self):
        async with self._lock:
            if self._ws is not None and self._ws.state == _WsState.OPEN:
                return
            self._ws = await websockets.connect(self.url, open_timeout=_CONNECT_TIMEOUT_S)
            await self._handshake()
            self._pending = {}
            self._reader_task = asyncio.ensure_future(self._read_loop())

    async def _handshake(self):
        # The gateway sends a pre-connect challenge event before any request is
        # sent (docs/gateway/protocol.md, "Handshake (connect)"). Token/password
        # auth on a trusted loopback backend client does not need to sign the
        # nonce (that's the device-identity auth path) -- just consume it.
        raw = await asyncio.wait_for(self._ws.recv(), timeout=_CONNECT_TIMEOUT_S)
        challenge = json.loads(raw)
        if challenge.get("type") != "event" or challenge.get("event") != "connect.challenge":
            raise GatewayWsError(f"expected connect.challenge, got: {challenge}")

        req_id = str(uuid.uuid4())
        connect_req = {
            "type": "req",
            "id": req_id,
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 4,
                "client": {
                    "id": "gateway-client",
                    "version": "116",
                    "platform": "linux",
                    "mode": "backend",
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write"],
                "auth": {"token": self.token},
            },
        }
        await self._ws.send(json.dumps(connect_req))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=_CONNECT_TIMEOUT_S)
        resp = json.loads(raw)
        if resp.get("type") != "res" or resp.get("id") != req_id or not resp.get("ok"):
            raise GatewayWsError(f"gateway connect handshake failed: {resp}")

    async def _read_loop(self):
        """Dispatch incoming frames: match `res` frames to pending calls by id,
        ignore `event` frames (this client does not subscribe to any).

        The gateway's `agent` method (and other long-running methods) reply
        with an intermediate `{ok: true, payload: {status: "accepted", ...}}`
        frame immediately, THEN the real final result frame later, both
        carrying the SAME request id (confirmed by reading OpenClaw's own
        GatewayClient.request()/expectFinal handling in its bundled source,
        client-C8-EgcVB.js). A pending call marked `expect_final` must skip
        the "accepted" frame and keep waiting for the real one -- otherwise
        the caller gets the acceptance ack back as if it were the answer.
        """
        try:
            async for raw in self._ws:
                try:
                    frame = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if frame.get("type") != "res":
                    continue
                pending = self._pending.get(frame.get("id"))
                if pending is None:
                    continue
                fut, expect_final = pending
                if fut.done():
                    continue
                if expect_final and (frame.get("payload") or {}).get("status") == "accepted":
                    continue  # not the real answer yet -- keep waiting
                self._pending.pop(frame.get("id"), None)
                fut.set_result(frame)
        except Exception as e:
            # Connection dropped mid-read. Fail every outstanding call so a
            # caller blocked in call() doesn't hang forever; call() itself
            # handles reconnect-and-retry.
            for fut, _ in self._pending.values():
                if not fut.done():
                    fut.set_exception(e)
            self._pending = {}

    async def call(self, method: str, params: dict, timeout_s: float | None,
                    expect_final: bool = True) -> dict:
        """Send one JSON-RPC request, await its matching (final) response,
        return the response frame's `payload`. Raises GatewayWsError on an
        `ok: false` response, TimeoutError if no response arrives within
        timeout_s. None delegates the response deadline to the caller.

        `expect_final=True` (default, matches how OpenClaw's own CLI dispatches
        `agent`): skip an intermediate "accepted" acknowledgement frame and
        wait for the real final result frame with the same request id.

        On a dropped connection mid-call, reconnects once and retries the call
        once before giving up (spec 116 Edge Case: a connection hiccup must not
        corrupt in-flight turn bookkeeping or silently hang).
        """
        try:
            return await self._call_once(method, params, timeout_s, expect_final)
        except (websockets.exceptions.ConnectionClosed, OSError):
            logger.warning("gateway_ws: connection dropped during %s call; reconnecting", method)
            self._ws = None
            await asyncio.sleep(_RECONNECT_BACKOFF_S)
            return await self._call_once(method, params, timeout_s, expect_final)

    async def _call_once(self, method: str, params: dict, timeout_s: float | None,
                          expect_final: bool) -> dict:
        await self._ensure_connected()
        req_id = str(uuid.uuid4())
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = (fut, expect_final)
        req = {"type": "req", "id": req_id, "method": method, "params": params}
        try:
            await self._ws.send(json.dumps(req))
            frame = await asyncio.wait_for(fut, timeout=timeout_s)
        finally:
            # Cancellation and send failures must release bookkeeping too.
            self._pending.pop(req_id, None)
            if not fut.done():
                fut.cancel()
        if not frame.get("ok"):
            raise GatewayWsError(f"gateway RPC '{method}' failed: {frame.get('error')}")
        return frame.get("payload", {})

    async def close(self):
        if self._reader_task is not None:
            self._reader_task.cancel()
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


_singleton = None
_singleton_lock = asyncio.Lock()


async def get_gateway_ws_client() -> GatewayWsClient:
    """Lazily construct and return the process-wide persistent client. One
    connection is reused by every run_agent_turn() call in this process -- the
    entire point of the fix (see module docstring)."""
    global _singleton
    async with _singleton_lock:
        if _singleton is None:
            url, token = resolve_gateway_ws_config()
            _singleton = GatewayWsClient(url, token)
        return _singleton
