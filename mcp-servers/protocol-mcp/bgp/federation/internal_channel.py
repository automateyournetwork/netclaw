"""iN2N internal transport: member-initiated dial, NCFED framing reuse.

Reuses the FROZEN NCFED wire framing (encode_frames + the read/heartbeat/dispatch
loops of FederationChannel) over a member-initiated outbound connection, adding
the iN2N trust model: a member is authenticated by proving possession of the
self-signed key the Border pinned at enrollment (signed nonce), NOT by BGP
identity or mutual consent. Hub-and-spoke: members only ever connect to the
Border (FR-007/FR-007a). No change to eN2N (052/053).

Transport handshake (contracts/in2n-internal-transport.md):
    Border → member : IN2N_MAGIC (5B) + nonce (32B)
    member → Border : in2n/hello | in2n/enroll  (JSON-RPC, signing the nonce)
Then the standard NCFED JSON-RPC channel runs. An optional TLS wrapper encrypts
the socket for distributed members; the auth guarantee is the signed-nonce check.
"""

import asyncio
import logging
import os
import struct
from typing import Optional

from ..constants import IN2N_MAGIC, IN2N_NONCE_SIZE, IN2N_METHOD_HELLO, IN2N_METHOD_ENROLL
from .channel import FederationChannel, ERR_METHOD_NOT_FOUND, RpcError

logger = logging.getLogger("n2n.internal_channel")

# iN2N JSON-RPC error codes surfaced on the channel.
_ERR_NOT_TRUSTED = -32023
_ERR_NOT_A_BORDER = -32024

# Methods allowed before a member is trusted (the handshake itself).
_PRE_TRUST_METHODS = (IN2N_METHOD_HELLO, IN2N_METHOD_ENROLL)


class InternalChannel(FederationChannel):
    """One iN2N connection between a Border and a Member.

    Subclasses FederationChannel to reuse its proven framing/heartbeat/dispatch,
    but replaces eN2N's `is_federated` gate with iN2N trust (pinned-key auth) and
    identifies the peer by risk-local `member_id` rather than an AS.
    """

    def __init__(self, reader, writer, *, local_identity: str, member_id: Optional[str],
                 is_border_side: bool, handlers: dict = None, nonce: bytes = b""):
        # Base __init__ wants peer_as/peer_router_id/manager; iN2N doesn't use
        # BGP identity, so pass neutral values and never call manager.is_federated
        # (we override _handle_request, the only place the base used it).
        super().__init__(reader, writer, local_identity=local_identity,
                         peer_as=0, peer_router_id="0.0.0.0", manager=None,
                         is_initiator=not is_border_side, handlers=handlers)
        self.member_id = member_id
        self.peer_identity = member_id or "<unauthenticated-member>"
        self.is_border_side = is_border_side
        self.trusted = False          # set True once the member authenticates
        self.nonce = nonce            # Border-issued challenge (border side)
        self.logger = logging.getLogger(f"n2n.in2n[{self.peer_identity}]")

    async def _handle_request(self, msg: dict):
        """iN2N dispatch: only the handshake methods are allowed before the
        member is trusted; everything else requires a verified pinned-key auth."""
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}

        if not self.trusted and method not in _PRE_TRUST_METHODS:
            if req_id is not None:
                await self._send_frames(self._err(req_id, _ERR_NOT_TRUSTED,
                                                   "member not authenticated"))
            return
        handler = self.handlers.get(method)
        if not handler:
            if req_id is not None:
                await self._send_frames(self._err(req_id, ERR_METHOD_NOT_FOUND,
                                                   f"unknown method {method}"))
            return
        try:
            result = await handler(self, params)
            if req_id is not None:
                await self._send_frames({"jsonrpc": "2.0", "id": req_id, "result": result or {}})
        except RpcError as e:
            if req_id is not None:
                await self._send_frames(self._err(req_id, e.code, e.message))
        except Exception as e:
            self.logger.error("iN2N handler %s failed: %s", method, e)
            if req_id is not None:
                await self._send_frames(self._err(req_id, -32000, str(e)))


# ── transport preamble helpers (byte-level, before the JSON-RPC channel) ──

async def send_border_preamble(writer) -> bytes:
    """Border side: emit IN2N magic + a fresh nonce; return the nonce so the
    accept path can verify the member's signature over it."""
    nonce = os.urandom(IN2N_NONCE_SIZE)
    writer.write(IN2N_MAGIC + nonce)
    await writer.drain()
    return nonce


async def read_border_preamble(reader) -> Optional[bytes]:
    """Member side: read IN2N magic + nonce. Returns the nonce, or None on bad magic."""
    try:
        magic = await asyncio.wait_for(reader.readexactly(len(IN2N_MAGIC)), timeout=10.0)
        if magic != IN2N_MAGIC:
            logger.warning("Bad iN2N preamble magic: %r", magic)
            return None
        nonce = await asyncio.wait_for(reader.readexactly(IN2N_NONCE_SIZE), timeout=10.0)
        return nonce
    except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError):
        return None


def build_ssl_contexts(cert_path: str, key_path: str):
    """Optional TLS for distributed members (encryption). Returns (server_ctx,
    client_ctx) using this claw's self-signed cert. Auth is still the app-layer
    signed-nonce check; TLS only encrypts the socket. Best-effort — callers may
    run plaintext over a trusted loopback/private transport."""
    import ssl
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_ctx.check_hostname = False
    client_ctx.verify_mode = ssl.CERT_NONE   # pinning happens at the app layer
    return server_ctx, client_ctx
