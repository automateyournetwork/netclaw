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
Then the standard NCFED JSON-RPC channel runs. Distributed members require verified TLS. Possession and hub attestation proofs
include a TLS channel binding; plaintext is restricted to loopback.
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
_PRE_TRUST_METHODS = (IN2N_METHOD_HELLO, IN2N_METHOD_ENROLL, 'in2n/attest')


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
        self.strict = False
        self.auth_attempted = False
        self.attest_attempted = False
        self.member_challenge = None
        self.authority_current = None
        self.on_security_refusal = None
        self._refusal_recorded = False
        self.admission_deadline = None
        self.nonce = nonce            # Border-issued challenge (border side)
        self.logger = logging.getLogger(f"n2n.in2n[{self.peer_identity}]")

    async def refuse(self, reason):
        """Record one fixed reason per channel, then close even if audit fails."""
        if reason not in ('authentication_refused', 'current_authority_refused', 'admission_timeout'):
            raise ValueError('invalid strict refusal reason')
        try:
            if not self._refusal_recorded:
                self._refusal_recorded = True
                if self.on_security_refusal:
                    self.on_security_refusal(reason)
        finally:
            await self.close()

    def _authority_valid(self):
        if not (self.strict and self.trusted and self.authority_current):
            return True
        try:
            return bool(self.authority_current())
        except Exception:
            return False

    async def _check_current_authority(self):
        if not self._authority_valid():
            await self.refuse('current_authority_refused')
            raise RpcError(_ERR_NOT_TRUSTED, 'current authority refused')

    async def _send_frames(self, message):
        # Errors can contain private data too. Gate every outbound response, not
        # only the successful handler path, after any awaited work.
        await self._check_current_authority()
        if self._closed:
            raise ConnectionError('Channel closed; operation outcome may be unknown')
        await super()._send_frames(message)

    async def call(self, method: str, params: dict, timeout: float = 30.0) -> dict:
        await self._check_current_authority()
        try:
            return await super().call(method, params, timeout=timeout)
        finally:
            # Revocation may commit while the remote handler is running. Its
            # earlier effect is not undone, but its response grants no authority.
            await self._check_current_authority()

    async def notify(self, method: str, params: dict):
        await self._check_current_authority()
        await super().notify(method, params)

    async def _handle_request(self, msg: dict):
        """iN2N dispatch: only the handshake methods are allowed before the
        member is trusted; everything else requires a verified pinned-key auth."""
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}

        if self.strict:
            denied = (self.trusted and method in _PRE_TRUST_METHODS)
            reason = 'authentication_refused'
            if not self._authority_valid():
                denied = True
                reason = 'current_authority_refused'
            if method == 'in2n/attest':
                denied = denied or self.attest_attempted or self.auth_attempted
                self.attest_attempted = True
            elif method in (IN2N_METHOD_HELLO, IN2N_METHOD_ENROLL):
                denied = denied or self.auth_attempted or self.member_challenge is None
                self.auth_attempted = True
                denied = denied or params.get('binding_profile') != 'in2n-tls-exporter-v1'
                denied = denied or params.get('member_nonce') != (self.member_challenge or b'').hex()
            if denied:
                try:
                    if req_id is not None:
                        await self._send_frames(self._err(req_id, _ERR_NOT_TRUSTED, 'authentication or current authority refused'))
                finally:
                    await self.refuse(reason)
                return

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
            # A successful entry check does not survive an awaited handler.
            await self._check_current_authority()
            if self.trusted and self.admission_deadline:
                self.admission_deadline.cancel()
            if req_id is not None:
                await self._send_frames({"jsonrpc": "2.0", "id": req_id, "result": result or {}})
        except RpcError as e:
            try:
                if req_id is not None and not self._closed:
                    await self._send_frames(self._err(req_id, e.code, e.message))
            finally:
                if self.strict and method in _PRE_TRUST_METHODS:
                    await self.refuse('authentication_refused')
        except Exception as e:
            if self.strict:
                self.logger.error('strict iN2N handler failed')
            else:
                self.logger.error("iN2N handler %s failed: %s", method, e)
            try:
                if req_id is not None and not self._closed:
                    await self._send_frames(self._err(req_id, -32000, 'strict admission failed' if self.strict else str(e)))
            finally:
                if self.strict and method in _PRE_TRUST_METHODS:
                    await self.refuse('authentication_refused')

    async def close(self):
        if self.admission_deadline and self.admission_deadline is not asyncio.current_task():
            self.admission_deadline.cancel()
        await super().close()


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
    """Legacy explicit-cert helper: trust the supplied certificate and verify
    hostname. Distributed daemon setup uses internal_security contexts."""
    import ssl
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    client_ctx = ssl.create_default_context(cafile=cert_path)
    return server_ctx, client_ctx
