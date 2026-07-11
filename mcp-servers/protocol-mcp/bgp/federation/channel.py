"""NCFED channel: framing, handshake, and JSON-RPC 2.0 dispatch.

Framing (contracts/n2n-wire-protocol.md):
    [4-byte big-endian length][1-byte flags][UTF-8 JSON-RPC 2.0 payload]
    flags bit0 = continuation (chunk of a larger message)

The channel is a single TCP connection multiplexed on the mesh port via the
NCFED discrimination magic. It carries JSON-RPC 2.0 requests/responses and
notifications. Methods are registered by the manager/inventory/invocation/chat
modules; everything except n2n/hello is rejected until the peer is federated.
"""

import asyncio
import json
import logging
import struct
from typing import Awaitable, Callable, Optional

from ..constants import (
    NCFED_MAGIC, NCFED_MAX_PAYLOAD, NCFED_FLAG_CONTINUATION,
    NCFED_HEARTBEAT_INTERVAL, NCFED_HEARTBEAT_MISS_LIMIT,
)

logger = logging.getLogger("n2n.channel")

# JSON-RPC reserved error codes (contracts/n2n-wire-protocol.md)
ERR_NOT_ALLOWLISTED = -32001
ERR_APPROVAL_PENDING = -32002
ERR_APPROVAL_EXPIRED = -32003
ERR_BUDGET_EXHAUSTED = -32004
ERR_RATE_LIMITED = -32005
ERR_EXECUTION_TIMEOUT = -32006
ERR_SEVERED = -32007
ERR_GUARDRAIL_BLOCKED = -32008
ERR_NOT_FEDERATED = -32010
ERR_METHOD_NOT_FOUND = -32601

Handler = Callable[["FederationChannel", dict], Awaitable[Optional[dict]]]


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def encode_frames(message: dict) -> list:
    """Encode a JSON-RPC message into one or more wire frames (chunked >64 KB)."""
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    frames = []
    if not payload:
        return [struct.pack("!IB", 0, 0)]
    offset = 0
    while offset < len(payload):
        chunk = payload[offset:offset + NCFED_MAX_PAYLOAD]
        offset += len(chunk)
        more = offset < len(payload)
        flags = NCFED_FLAG_CONTINUATION if more else 0
        frames.append(struct.pack("!IB", len(chunk), flags) + chunk)
    return frames


class FederationChannel:
    """One NCFED connection to one peer. Registered method handlers dispatch
    inbound requests; outbound requests await correlated responses."""

    def __init__(self, reader, writer, *, local_identity: str, peer_as: int,
                 peer_router_id: str, manager, is_initiator: bool, handlers: dict = None):
        self.reader = reader
        self.writer = writer
        self.local_identity = local_identity
        self.peer_as = peer_as
        self.peer_router_id = peer_router_id
        self.peer_identity = f"as{peer_as}-{peer_router_id}"
        self.manager = manager
        self.is_initiator = is_initiator
        self.logger = logging.getLogger(f"n2n.channel[{self.peer_identity}]")
        self._next_id = 0
        self._pending: dict = {}       # request_id -> Future
        self._recv_buf = b""           # reassembly across continuation frames
        self._closed = False
        self._read_task: Optional[asyncio.Task] = None
        self._hb_task: Optional[asyncio.Task] = None
        self.display_name: Optional[str] = None
        # Per-channel handler map (owned by the FederationService that created
        # this channel) — NOT class-level, so multiple services in one process
        # (e.g. tests) don't clobber each other's handlers.
        self.handlers: dict = dict(handlers or {})

    def register(self, method: str, handler: Handler):
        self.handlers[method] = handler

    # ---- lifecycle ----------------------------------------------------

    async def start(self):
        self._misses = 0
        self._read_task = asyncio.create_task(self._read_loop())
        self._hb_task = asyncio.create_task(self._heartbeat_loop())

    async def close(self):
        if self._closed:
            return
        self._closed = True
        for t in (self._read_task, self._hb_task):
            if t:
                t.cancel()
        try:
            self.writer.close()
        except Exception:
            pass
        # Notify the owner (service) so a dead channel is deregistered and the
        # reconnect supervisor can re-dial (US2). Never let a hook error mask close.
        cb = getattr(self, "on_close", None)
        if cb:
            try:
                cb(self)
            except Exception:
                pass

    # ---- framing I/O --------------------------------------------------

    async def _send_frames(self, message: dict):
        for frame in encode_frames(message):
            self.writer.write(frame)
        await self.writer.drain()

    async def _read_loop(self):
        try:
            while not self._closed:
                header = await self.reader.readexactly(5)
                self._misses = 0  # any inbound frame (incl. heartbeat) proves liveness
                length, flags = struct.unpack("!IB", header)
                if length > NCFED_MAX_PAYLOAD:
                    self.logger.warning("Oversized frame %d — closing", length)
                    break
                chunk = await self.reader.readexactly(length) if length else b""
                if flags & NCFED_FLAG_CONTINUATION:
                    self._recv_buf += chunk
                    continue
                full = self._recv_buf + chunk
                self._recv_buf = b""
                if not full:
                    continue  # heartbeat
                await self._dispatch(full)
        except (asyncio.IncompleteReadError, ConnectionError):
            self.logger.info("Channel closed by peer")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error("Channel read error: %s", e)
        finally:
            await self.close()

    async def _heartbeat_loop(self):
        # Send a heartbeat each interval AND track liveness: a failed send or
        # NCFED_HEARTBEAT_MISS_LIMIT intervals with no inbound frame closes the
        # channel (which fires on_close → deregister → reconnect). (US2, FR-006)
        try:
            while not self._closed:
                await asyncio.sleep(NCFED_HEARTBEAT_INTERVAL)
                self._misses += 1
                if self._misses >= NCFED_HEARTBEAT_MISS_LIMIT:
                    self.logger.warning("Channel to %s: %d missed heartbeats — closing",
                                        self.peer_identity, self._misses)
                    break
                try:
                    self.writer.write(struct.pack("!IB", 0, 0))
                    await self.writer.drain()
                except (ConnectionError, OSError) as e:
                    self.logger.warning("Channel to %s: heartbeat send failed (%s) — closing",
                                        self.peer_identity, e)
                    break
        except asyncio.CancelledError:
            return
        except Exception:
            pass
        await self.close()

    # ---- dispatch -----------------------------------------------------

    async def _dispatch(self, raw: bytes):
        try:
            msg = json.loads(raw.decode("utf-8"))
        except Exception as e:
            self.logger.warning("Bad JSON on channel: %s", e)
            return

        if "method" in msg:                      # request or notification
            await self._handle_request(msg)
        elif "id" in msg:                        # response to our request
            fut = self._pending.pop(msg["id"], None)
            if fut and not fut.done():
                fut.set_result(msg)

    async def _handle_request(self, msg: dict):
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}

        # Only n2n/hello is allowed before federation is established.
        if method != "n2n/hello" and not self.manager.is_federated(self.peer_identity):
            if req_id is not None:
                await self._send_frames(self._err(req_id, ERR_NOT_FEDERATED, "peer not federated"))
            return

        handler = self.handlers.get(method)
        if not handler:
            if req_id is not None:
                await self._send_frames(self._err(req_id, ERR_METHOD_NOT_FOUND, f"unknown method {method}"))
            return
        try:
            result = await handler(self, params)
            if req_id is not None:
                await self._send_frames({"jsonrpc": "2.0", "id": req_id, "result": result or {}})
        except RpcError as e:
            if req_id is not None:
                await self._send_frames(self._err(req_id, e.code, e.message))
        except Exception as e:
            self.logger.error("Handler %s failed: %s", method, e)
            if req_id is not None:
                await self._send_frames(self._err(req_id, -32000, str(e)))

    def _err(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    # ---- outbound requests --------------------------------------------

    async def call(self, method: str, params: dict, timeout: float = 30.0) -> dict:
        self._next_id += 1
        req_id = f"{self.local_identity}:{self._next_id}"
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self._send_frames({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        try:
            resp = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise RpcError(ERR_EXECUTION_TIMEOUT, f"{method} timed out")
        if "error" in resp:
            raise RpcError(resp["error"]["code"], resp["error"]["message"])
        return resp.get("result", {})

    async def notify(self, method: str, params: dict):
        await self._send_frames({"jsonrpc": "2.0", "method": method, "params": params})


async def read_handshake(reader) -> Optional[tuple]:
    """Read the 8 bytes following the already-consumed 'NCFED' magic:
    4-byte AS + 4-byte IPv4-encoded router-id. Returns (peer_as, router_id)."""
    import ipaddress
    try:
        rest = await asyncio.wait_for(reader.readexactly(8), timeout=10.0)
    except Exception:
        return None
    peer_as = struct.unpack("!I", rest[:4])[0]
    router_id = str(ipaddress.IPv4Address(rest[4:8]))
    return peer_as, router_id


def build_handshake(local_as: int, router_id: str) -> bytes:
    """NCFED magic + AS + router-id, mirroring the NCTUN handshake."""
    import ipaddress
    return NCFED_MAGIC + struct.pack("!I", local_as) + ipaddress.IPv4Address(router_id).packed
