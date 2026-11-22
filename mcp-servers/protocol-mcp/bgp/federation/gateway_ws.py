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
import hashlib
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


class GatewayWsError(RuntimeError):
    """Raised when the gateway returns an error response or refuses handshake."""


class GatewayWsAuthError(GatewayWsError):
    """The gateway refused the connect handshake because of the auth token
    (e.g. AUTH_TOKEN_MISMATCH). The client is marked stale so the next
    get_gateway_ws_client() re-resolves the token instead of retrying the
    rejected one for the lifetime of the process."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


_AUTH_CODES = ("AUTH_TOKEN_MISMATCH", "AUTH_TOKEN_MISSING", "AUTH_TOKEN_INVALID",
               "AUTH_UNAUTHORIZED", "AUTH_REQUIRED")


def token_fingerprint(token) -> str:
    """Non-reversible identifier for logs: sha256(token)[:10]. Never log the
    token itself."""
    if not token:
        return "none"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:10]


def _auth_error_code(error):
    """Return the AUTH_* code from a handshake error payload, or None. The
    gateway nests the code under error.details (shape varies by version), so
    search the serialized payload rather than one fixed path."""
    try:
        blob = json.dumps(error, sort_keys=True, default=str)
    except (TypeError, ValueError):
        blob = str(error)
    for code in _AUTH_CODES:
        if code in blob:
            return code
    return None


def _resolve_token_ref(token, path):
    """gateway.auth.token may be a literal string or an OpenClaw SecretRef object
    (spec 167 F2). Only an `env` SecretRef is resolved here (from this process's
    environment); other sources (store/file/exec/...) are refused rather than read,
    and a dict is never returned as the token."""
    if not isinstance(token, dict):
        if token is not None and not isinstance(token, str):
            raise GatewayWsError(f"gateway.auth.token in {path} is not a string or SecretRef")
        return token
    source, ref_id = token.get("source"), token.get("id")
    if source == "env":
        if not isinstance(ref_id, str) or not ref_id:
            raise GatewayWsError(f"gateway.auth.token env SecretRef in {path} has no id")
        value = os.environ.get(ref_id)
        if not value:
            raise GatewayWsError(
                f"gateway.auth.token in {path} references env var {ref_id}, which is not set "
                f"(set {ref_id} or the {_ENV_TOKEN} override)")
        return value
    raise GatewayWsError(
        f"gateway.auth.token in {path} is a SecretRef with source {source!r}, which is not "
        f"supported here; set the {_ENV_TOKEN} override")


def resolve_gateway_ws_config(config_path: str = None) -> tuple:
    """Return (ws_url, token). See resolve_gateway_ws_config_with_source()."""
    url, token, _source = resolve_gateway_ws_config_with_source(config_path)
    return url, token


def resolve_gateway_ws_config_with_source(config_path: str = None) -> tuple:
    """Resolve (ws_url, token) the same way the `openclaw` CLI resolves gateway
    connection details today: from openclaw.json's gateway.port/bind/auth.token,
    with an env override for parity with gateway.py's OPENCLAW_BIN pattern.

    Only loopback/local mode is supported (matches the Border's own config and
    the trust boundary the CLI path already operates in -- see
    specs/116-border-turn-latency/contracts/gateway-ws-rpc.md).

    Returns (ws_url, token, token_source). token_source names where the token
    came from -- "env:OPENCLAW_GATEWAY_TOKEN", "config:<path>" (literal) or
    "secretref-env:<VAR>@<path>" -- and never contains the token value.
    """
    env_url = os.environ.get(_ENV_URL)
    env_token = os.environ.get(_ENV_TOKEN)
    if env_url and env_token:
        return env_url, env_token, f"env:{_ENV_TOKEN}"

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
    if env_token:
        # The env token wins over gateway.auth.token even without the URL
        # override, so a stale OPENCLAW_GATEWAY_TOKEN in the service env
        # shadows the config token. The logged source makes that visible.
        return url, env_token, f"env:{_ENV_TOKEN}"
    raw = (gw.get("auth", {}) or {}).get("token")
    token = _resolve_token_ref(raw, path)
    if not token:
        raise GatewayWsError(
            f"no gateway auth token found in {path} (gateway.auth.token) and "
            f"no {_ENV_TOKEN} override set")
    if isinstance(raw, dict):
        return url, token, f"secretref-env:{raw.get('id')}@{path}"
    return url, token, f"config:{path}"


class GatewayWsClient:
    """One persistent WS connection to the gateway, shared across agent turns.

    Not thread-safe across event loops; intended for use within a single
    asyncio event loop (the Border daemon's own loop).
    """

    def __init__(self, url: str, token: str, token_source: str = "unknown"):
        self.url = url
        self.token = token
        self.token_source = token_source
        # Set when the gateway rejects this client's token; the process-wide
        # singleton is then rebuilt from freshly resolved config.
        self.auth_failed = False
        self._ws = None
        self._lock = asyncio.Lock()
        self._pending = {}  # request id -> asyncio.Future
        self._reader_task = None
        self._run_observers = {}

    def watch_run(self, run_id, observer):
        if run_id in self._run_observers or len(self._run_observers) >= 64:
            raise GatewayWsError('gateway observation capacity unavailable')
        self._run_observers[run_id] = observer
        return lambda: self._run_observers.pop(run_id, None)

    async def _ensure_connected(self):
        async with self._lock:
            if self._ws is not None and self._ws.state == _WsState.OPEN:
                return
            # Retire the previous reader before replacing shared pending state.
            # Its finally block must never fail calls on the new connection.
            if self._reader_task is not None:
                self._reader_task.cancel()
                await asyncio.gather(self._reader_task, return_exceptions=True)
                self._reader_task = None
            self._ws = await websockets.connect(self.url, open_timeout=_CONNECT_TIMEOUT_S)
            try:
                await self._handshake()
            except GatewayWsAuthError as exc:
                self.auth_failed = True
                logger.warning(
                    "gateway rejected token: code=%s source=%s fp=%s url=%s "
                    "(client marked stale; next call re-resolves the token)",
                    exc.code, self.token_source, token_fingerprint(self.token), self.url)
                await self._ws.close()
                self._ws = None
                raise
            except BaseException:
                await self._ws.close()
                self._ws = None
                raise
            logger.info("gateway ws connected url=%s token_source=%s fp=%s",
                        self.url, self.token_source, token_fingerprint(self.token))
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
                "caps": ["tool-events"],
                "auth": {"token": self.token},
            },
        }
        await self._ws.send(json.dumps(connect_req))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=_CONNECT_TIMEOUT_S)
        resp = json.loads(raw)
        if resp.get("type") != "res" or resp.get("id") != req_id or not resp.get("ok"):
            code = _auth_error_code(resp.get("error"))
            if code:
                raise GatewayWsAuthError(f"gateway connect handshake failed: {code}", code)
            raise GatewayWsError(f"gateway connect handshake failed: {resp}")

    async def _read_loop(self):
        """Dispatch incoming frames: match `res` frames to pending calls by id,
        observe only locally bound native agent events for active runs.

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
                if not isinstance(frame, dict):
                    continue
                if frame.get('type') == 'event' and frame.get('event') == 'agent':
                    payload = frame.get('payload')
                    observer = self._run_observers.get(payload.get('runId')) if isinstance(payload, dict) and isinstance(payload.get('runId'), str) else None
                    if observer:
                        try:
                            observer(payload)
                        except Exception:
                            # Missing or malformed evidence never becomes a
                            # source claim, and never retries the agent call.
                            logger.warning('native external attribution unavailable')
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
        except Exception:
            # Bounded failure below: do not retain peer frame/token diagnostics.
            pass
        finally:
            # A clean WebSocket close also leaves outstanding calls uncertain.
            # Wake every waiter; a missing response is never execution failure
            # evidence and must not silently resubmit an agent turn.
            for fut, _ in self._pending.values():
                if not fut.done():
                    fut.set_exception(GatewayWsError('gateway connection closed before final response'))
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

        No call is retried after dispatch. A later explicit request reconnects
        independently; agent work with a lost response remains outcome unknown.
        """
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
        async with self._lock:
            if self._reader_task is not None:
                self._reader_task.cancel()
                await asyncio.gather(self._reader_task, return_exceptions=True)
                self._reader_task = None
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
        stale = _singleton
        if stale is not None and not stale.auth_failed:
            return stale
        url, token, source = resolve_gateway_ws_config_with_source()
        fp = token_fingerprint(token)
        if stale is None:
            logger.info("gateway ws token resolved: source=%s fp=%s url=%s", source, fp, url)
        else:
            # Drop the rejected client. Re-resolution only helps if the token
            # source changed; an env-sourced token is fixed for the process
            # lifetime, so say so rather than silently reusing it.
            await stale.close()
            old_fp = token_fingerprint(stale.token)
            if fp == old_fp:
                logger.warning(
                    "gateway ws token re-resolved after auth failure but is unchanged: "
                    "source=%s fp=%s; fix the token source%s", source, fp,
                    " and restart this process" if source.startswith("env:") else "")
            else:
                logger.info(
                    "gateway ws token re-resolved after auth failure: source=%s fp=%s "
                    "(was source=%s fp=%s)", source, fp, stale.token_source, old_fp)
        _singleton = GatewayWsClient(url, token, source)
        return _singleton
