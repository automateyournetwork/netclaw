"""Enrolled Border cluster role on the frozen NCFED wire, never an etcd proxy."""
import asyncio
import secrets
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from ..channel import FederationChannel, build_handshake
from ..certs import time_valid
from ..protected_contract import decode, encode, exact, key_id, sha256, uuid_field
from .config import HAError, check
from .signatures import sign, verify

HELLO = 'n2n/cluster/hello'
METHODS = frozenset({'n2n/cluster/status', 'n2n/cluster/forward',
                     'n2n/cluster/admission', 'n2n/cluster/admission-status', 'n2n/cluster/edge'})
PREAMBLE = build_handshake(0, '0.0.0.0')
MAX_MESSAGE = 1024 * 1024 + 65536


class ClusterChannel(FederationChannel):
    def __init__(self, reader, writer, *, manifest, node_id, peer_node_id, private_key,
                 current, local_nonce, peer_nonce, is_initiator, handlers=None):
        check(manifest.anchor_key_id is not None, 'unverified_cluster_manifest', 403)
        node, peer = manifest.node(node_id), manifest.node(peer_node_id)
        check(node_id != peer_node_id and callable(current), 'invalid_cluster_peer')
        check(writer.get_extra_info('tls_profile') == 'ncfed-cluster-mtls-v1'
              and writer.get_extra_info('tls_version') == 'TLSv1.3', 'cluster_mtls_required', 403)
        exporter = writer.get_extra_info('tls_exporter')
        check(isinstance(exporter, bytes) and len(exporter) == 32, 'cluster_exporter_required', 403)
        try:
            tls_cert = x509.load_der_x509_certificate(writer.get_extra_info('tls_peer_certificate'))
            tls_pem = tls_cert.public_bytes(serialization.Encoding.PEM).decode()
            check(key_id(tls_pem) == peer['key_id'], 'cluster_tls_peer_mismatch', 403)
        except HAError:
            raise
        except Exception:
            raise HAError('cluster_tls_peer_mismatch', 403) from None
        check(set(handlers or {}) <= METHODS, 'cluster_method_refused')
        super().__init__(reader, writer, local_identity=node['identity'], peer_as=0,
            peer_router_id='0.0.0.0', manager=None, is_initiator=is_initiator, handlers=handlers)
        self.manifest, self.node, self.peer = manifest, node, peer
        self.peer_identity = peer_node_id
        self.current, self.private_key = current, private_key
        self.local_nonce, self.peer_nonce, self.exporter = local_nonce, peer_nonce, exporter
        self.incarnation = str(uuid.uuid4())
        self.peer_incarnation = None
        self.hello_received = False
        self.hello_sent = False
        self._auth_timer = None
        self._peer_verified = asyncio.Event()
        self._ready = asyncio.Event()

    def _transcript(self, node, peer, incarnation, nonce, challenge):
        return {**self.manifest.audience, 'manifest_sha256': sha256(self.manifest.value),
                'node_id': node['node_id'], 'installation_id': node['installation_id'],
                'peer_node_id': peer['node_id'], 'role': 'cluster-border',
                'incarnation': incarnation, 'nonce': nonce.hex(), 'challenge': challenge.hex(),
                'tls_exporter': self.exporter.hex()}

    async def start(self):
        await self.current(self.peer['node_id'])
        self._auth_timer = asyncio.get_running_loop().call_later(10, self.writer.abort)
        await super().start()
        proof = sign('hello', self._transcript(self.node, self.peer, self.incarnation,
                                              self.local_nonce, self.peer_nonce), self.private_key)
        self.hello_sent = True
        result = await super().call(HELLO, proof, timeout=10)
        await asyncio.wait_for(self._peer_verified.wait(), 10)
        check(result == {'accepted': True} and not self._closed, 'cluster_authentication_failed', 403)
        self.authenticated = True
        self._ready.set()
        self._auth_timer.cancel()

    async def _current(self):
        if not self.authenticated and not self._closed:
            await asyncio.wait_for(self._ready.wait(), 10)
        check(self.authenticated and not self._closed, 'cluster_not_authenticated', 403)
        try:
            check(time_valid(self.peer['certificate']), 'node_certificate_expired', 403)
            await self.current(self.peer['node_id'])
        except BaseException:
            await self.close()
            raise

    async def call(self, method, params, timeout=30):
        check(method in METHODS, 'cluster_method_refused', 403)
        await self._current()
        try:
            return await super().call(method, params, timeout=timeout)
        finally:
            await self._current()

    async def notify(self, method, params):
        raise HAError('cluster_notification_refused', 403)

    async def _send_frames(self, message):
        check(len(encode(message)) <= MAX_MESSAGE, 'cluster_message_capacity')
        if self.authenticated:
            await self._current()
        await super()._send_frames(message)

    async def _dispatch(self, raw):
        try:
            msg = decode(raw, MAX_MESSAGE)
            check(isinstance(msg, dict) and msg.get('jsonrpc') == '2.0')
            check(isinstance(msg.get('id'), str) and 0 < len(msg['id']) <= 256)
            if 'method' in msg:
                exact(msg, 'jsonrpc id method params')
                await self._handle_request(msg)
            else:
                exact(msg, 'jsonrpc id error' if 'error' in msg else 'jsonrpc id result')
                future = self._pending.pop(msg['id'], None)
                if future and not future.done():
                    future.set_result(msg)
        except Exception:
            await self.close()

    async def _handle_request(self, msg):
        method, params, req_id = msg['method'], msg['params'], msg['id']
        try:
            if method == HELLO:
                check(not self.hello_received and self.hello_sent, 'cluster_authentication_failed', 403)
                # Mark before any await; a replay cannot race a second proof.
                self.hello_received = True
                payload = verify(params, self.peer['certificate'], 'hello')
                uuid_field(payload.get('incarnation'))
                expected = self._transcript(self.peer, self.node, payload['incarnation'],
                                            self.peer_nonce, self.local_nonce)
                check(payload == expected, 'cluster_transcript_mismatch', 403)
                await self.current(self.peer['node_id'])
                self.peer_incarnation = payload['incarnation']
                self._peer_verified.set()
                result = {'accepted': True}
            else:
                check(method in METHODS and method in self.handlers, 'cluster_method_refused', 403)
                await self._current()
                check(isinstance(params, dict), 'invalid_cluster_params')
                result = await self.handlers[method](self, params)
                await self._current()
            await self._send_frames({'jsonrpc': '2.0', 'id': req_id, 'result': result})
        except HAError as exc:
            await super()._send_frames(self._err(req_id, -32050, exc.code))
            if method == HELLO:
                await self.close()
        except Exception:
            await super()._send_frames(self._err(req_id, -32050, 'cluster_request_unknown'))
            if method == HELLO:
                await self.close()

    async def close(self):
        if self._auth_timer:
            self._auth_timer.cancel()
        await super().close()


async def attach(reader, writer, **options):
    """Separate cluster listener; standard NCFED discrimination followed by nonce."""
    channel = None
    try:
        local_nonce = secrets.token_bytes(32)
        writer.write(PREAMBLE + local_nonce)
        await writer.drain()
        raw = await asyncio.wait_for(reader.readexactly(len(PREAMBLE) + 32), 10)
        check(raw[:len(PREAMBLE)] == PREAMBLE, 'cluster_preamble_refused', 403)
        channel = ClusterChannel(reader, writer, local_nonce=local_nonce,
                                  peer_nonce=raw[len(PREAMBLE):], **options)
        await channel.start()
        return channel
    except BaseException:
        if channel:
            await channel.close()
        else:
            writer.close()
        raise
