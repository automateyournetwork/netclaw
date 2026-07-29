"""NCFED edge channel: WebSocket transport for NetClaw Mobile "edge" nodes
(feature 066). Reuses the existing iN2N trust model (RiskManager: enrollment
tokens, pinned-key possession proof, per-member row) over a new
WebSocket-over-TLS transport instead of raw TCP — mobile platforms and their
networking stacks are built around WebSocket, not a bespoke framed TCP
protocol on an arbitrary port (research D2).

Unlike FederationChannel/InternalChannel (channel.py/internal_channel.py),
this transport does not reuse the raw NCFED byte framing
([4-byte length][1-byte flags][JSON]) — a WebSocket connection already frames
each message, so EdgeChannel sends/receives whole JSON-RPC 2.0 messages
directly over `.send()`/`recv()`. It exposes the same external
call()/notify()/handler-dispatch shape FederationChannel already has so it
plugs into FederationService's existing bidirectional call-out pattern
(mirroring delegate_to_member's shape) without any special-casing at call
sites (D8).

Hub-and-spoke only, like iN2N: an edge node always dials the Border. There is
no member-side (phone) implementation here — that side is the Dart client
under mobile/netclaw-mobile/.
"""

import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

logger = logging.getLogger("n2n.edge")

ERR_METHOD_NOT_FOUND = -32601
ERR_EXECUTION_TIMEOUT = -32006
ERR_NOT_TRUSTED = -32023

Handler = Callable[["EdgeChannel", dict], Awaitable[Optional[dict]]]

# The complete set of methods an edge channel will ever dispatch (FR-012):
# enrollment/reconnect handshake + the two built-in health methods + the
# Border-to-phone push method. Deliberately excludes every BGP, eN2N, and
# iN2N-inventory method name — an edge node can never reach the mesh's
# routing/inventory surface, even if a caller tried to register a handler
# for one of those methods on an EdgeChannel by mistake.
EDGE_METHODS = (
    "in2n/enroll",
    "in2n/hello",
    "n2n/edge/heartbeat",
    "n2n/edge/self_status",
    "n2n/edge/message",
    "n2n/edge/register_push",
    # feature 067: phone-to-Border command channel. n2n/edge/ask is
    # phone-initiated (mirrors chat.py's peer-chat pattern via
    # gateway.run_agent_turn); n2n/edge/ask_result is the Border's
    # best-effort push of the finished answer. n2n/tasks/* are the SAME
    # method names (and the SAME handler functions) the existing iN2N
    # member-facing task surface already uses (Invoker.handle_task_status/
    # result/cancel) -- reused as-is, not reimplemented, per research D4.
    "n2n/edge/ask",
    "n2n/edge/ask_result",
    # Border-initiated, best-effort, fire-and-forget: a turn that is still
    # alive at the stall checkpoint says so rather than leaving the phone on a
    # silent spinner for the whole (now much longer) budget. An app build with
    # no handler for it drops the notification silently on both sides, so this
    # is safe against version skew in either direction.
    "n2n/edge/task_progress",
    "n2n/tasks/status",
    "n2n/tasks/result",
    "n2n/tasks/cancel",
    # feature 068: biometric-gated approvals + bidirectional capture.
    # n2n/edge/register_capabilities is phone-initiated (declares which
    # capture types are currently enabled); n2n/edge/capture is
    # Border-initiated (mirrors push_to_edge's call-out shape, contract §2);
    # n2n/edge/approval_resolve is phone-initiated, calling the EXISTING
    # Authorizer.resolve_approval(..., via="biometric") unchanged.
    "n2n/edge/register_capabilities",
    "n2n/edge/capture",
    "n2n/edge/approval_resolve",
)

# Methods reachable before the channel has authenticated (the handshake itself).
_PRE_TRUST_METHODS = ("in2n/enroll", "in2n/hello")


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class EdgeChannel:
    """One WebSocket connection to one enrolled NetClaw Mobile device."""

    def __init__(self, ws, *, local_identity: str, handlers: dict = None):
        self.ws = ws
        self.local_identity = local_identity
        self.member_id: Optional[str] = None
        self.peer_identity = "<unauthenticated-edge>"
        self.trusted = False
        self.nonce = b""
        self.display_name: Optional[str] = None
        self.logger = logging.getLogger("n2n.edge[unauthenticated]")
        self._next_id = 0
        self._pending: dict = {}
        self._closed = False
        self._read_task: Optional[asyncio.Task] = None
        self.on_close = None
        # Restricted to EDGE_METHODS regardless of what's passed in (FR-012).
        self.handlers: dict = {k: v for k, v in dict(handlers or {}).items()
                               if k in EDGE_METHODS}

    def register(self, method: str, handler: Handler):
        if method not in EDGE_METHODS:
            raise ValueError(f"{method} is not an edge-channel method (FR-012)")
        self.handlers[method] = handler

    # ---- lifecycle ------------------------------------------------------

    async def start(self):
        self._read_task = asyncio.create_task(self._read_loop())

    async def close(self):
        if self._closed:
            return
        self._closed = True
        if self._read_task:
            self._read_task.cancel()
        try:
            await self.ws.close()
        except Exception:
            pass
        for _, fut in list(self._pending.items()):
            if not fut.done():
                fut.cancel()
        self._pending.clear()
        cb = self.on_close
        if cb:
            try:
                cb(self)
            except Exception:
                pass

    # ---- framing I/O (WebSocket already frames messages) -----------------

    async def _read_loop(self):
        try:
            async for raw in self.ws:
                await self._dispatch(raw)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.info("Edge channel closed: %s", e)
        finally:
            await self.close()

    async def _send(self, message: dict):
        await self.ws.send(json.dumps(message, separators=(",", ":")))

    # ---- dispatch ---------------------------------------------------------

    async def _dispatch(self, raw):
        try:
            msg = json.loads(raw)
        except Exception as e:
            self.logger.warning("Bad JSON on edge channel: %s", e)
            return
        if "method" in msg:
            await self._handle_request(msg)
        elif "id" in msg:
            fut = self._pending.pop(msg["id"], None)
            if fut and not fut.done():
                fut.set_result(msg)

    async def _handle_request(self, msg: dict):
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}
        if not self.trusted and method not in _PRE_TRUST_METHODS:
            if req_id is not None:
                await self._send(self._err(req_id, ERR_NOT_TRUSTED, "edge node not authenticated"))
            return
        handler = self.handlers.get(method)
        if not handler:
            if req_id is not None:
                await self._send(self._err(req_id, ERR_METHOD_NOT_FOUND, f"unknown method {method}"))
            return
        try:
            result = await handler(self, params)
            if req_id is not None:
                await self._send({"jsonrpc": "2.0", "id": req_id, "result": result or {}})
        except RpcError as e:
            if req_id is not None:
                await self._send(self._err(req_id, e.code, e.message))
        except Exception as e:
            self.logger.error("Edge handler %s failed: %s", method, e)
            if req_id is not None:
                await self._send(self._err(req_id, -32000, str(e)))

    def _err(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    # ---- outbound requests (Border → phone, mirrors delegate_to_member) --

    async def call(self, method: str, params: dict, timeout: float = 30.0) -> dict:
        self._next_id += 1
        req_id = f"{self.local_identity}:{self._next_id}"
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        try:
            resp = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise RpcError(ERR_EXECUTION_TIMEOUT, f"{method} timed out")
        if "error" in resp:
            raise RpcError(resp["error"]["code"], resp["error"]["message"])
        return resp.get("result", {})

    async def notify(self, method: str, params: dict):
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})
