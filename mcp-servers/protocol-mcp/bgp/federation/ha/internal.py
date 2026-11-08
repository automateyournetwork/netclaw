"""NCFED/iN2N member-initiated multiattachment with separate enrolled roles."""
import asyncio
import secrets

from .. import exporter_tls
from ..certs import time_valid
from ..channel import RpcError
from ..internal_channel import InternalChannel, read_border_preamble, send_border_preamble
from ..internal_security import channel_binding
from ..protected_contract import decode, encode, exact, key_id, sha256, validate_binding
from .config import HAError, check
from .signatures import sign, verify

HANDSHAKE = frozenset({'in2n/attest', 'in2n/hello'})
EXECUTION = frozenset({'execution/catalog', 'execution/submit', 'execution/status',
                       'execution/result', 'execution/ack', 'execution/admission',
                       'execution/admission-status'})
MAX_MESSAGE = 1024 * 1024 + 65536


def border_binding(manifest, node_id):
    node = manifest.node(node_id)
    return {'installation_id': node['installation_id'], 'identity': node['identity'],
            'key_id': node['key_id'], 'authority_generation': manifest.generation}


def transcript(manifest, node_id, channel, member_nonce):
    return {**manifest.audience, 'manifest_sha256': sha256(manifest.value),
            'node_id': node_id, 'border': border_binding(manifest, node_id),
            'border_nonce': channel.nonce.hex(), 'member_nonce': member_nonce.hex(),
            'tls_binding': channel_binding(channel.writer, strict=True).hex()}


class AttachmentChannel(InternalChannel):
    def __init__(self, *args, current, **kwargs):
        super().__init__(*args, **kwargs)
        self.strict = True
        self.current_async = current

    async def _check_current_authority(self):
        await super()._check_current_authority()
        if self.trusted:
            try:
                await self.current_async(self)
            except BaseException:
                await self.close()
                raise

    async def call(self, method, params, timeout=30):
        check(method in EXECUTION or (method in HANDSHAKE and not self.trusted),
              'attachment_method_refused', 403)
        return await super().call(method, params, timeout=timeout)

    async def notify(self, method, params):
        raise HAError('attachment_notification_refused', 403)

    async def _handle_request(self, msg):
        if msg.get('method') not in EXECUTION | HANDSHAKE:
            await self._send_frames(self._err(msg['id'], -32023, 'attachment_method_refused'))
            return
        await self._check_current_authority()
        await super()._handle_request(msg)

    async def _dispatch(self, raw):
        try:
            message = decode(raw, MAX_MESSAGE)
            check(isinstance(message, dict) and message.get('jsonrpc') == '2.0'
                  and isinstance(message.get('id'), str) and 0 < len(message['id']) <= 256)
            if 'method' in message:
                exact(message, 'jsonrpc id method params')
                await self._handle_request(message)
            else:
                exact(message, 'jsonrpc id error' if 'error' in message else 'jsonrpc id result')
                future = self._pending.pop(message['id'], None)
                if future and not future.done(): future.set_result(message)
        except Exception:
            await self.close()

    async def _send_frames(self, message):
        check(len(encode(message)) <= MAX_MESSAGE, 'attachment_message_capacity')
        await super()._send_frames(message)


async def accept_member(node, reader, writer, *, handlers, on_authenticated):
    """A pre-enrolled member proves its own key; cluster peer keys do not suffice."""
    check(set(handlers) <= EXECUTION, 'attachment_method_refused')
    channel = None
    try:
        channel_binding(writer, strict=True)
        nonce = await send_border_preamble(writer)
        async def current(ch):
            await node.member_current(ch.protected_peer_binding)
        async def attest(ch, params):
            exact(params, 'binding_profile member_nonce')
            check(params['binding_profile'] == 'in2n-tls-exporter-v1', 'attachment_profile_refused', 403)
            check(isinstance(params['member_nonce'], str) and len(params['member_nonce']) == 64)
            member_nonce = bytes.fromhex(params['member_nonce'])
            await node.current(node.node_id)
            ch.member_challenge = member_nonce
            return {'cluster_attestation': sign('attachment-border',
                    transcript(node.manifest, node.node_id, ch, member_nonce), node.private_key)}
        async def hello(ch, params):
            exact(params, 'binding_profile member_nonce member proof')
            check(params['binding_profile'] == 'in2n-tls-exporter-v1', 'attachment_profile_refused', 403)
            binding = params['member']; validate_binding(binding, 'member')
            entry = await node.member_current(binding)
            proof = verify(params['proof'], entry['certificate'], 'attachment-member')
            expected = dict(transcript(node.manifest, node.node_id, ch, ch.member_challenge),
                            member=binding, role='execution-member')
            check(proof == expected, 'attachment_proof_mismatch', 403)
            ch.member_id = binding['member_id']; ch.peer_identity = binding['member_id']
            ch.protected_peer_binding, ch.protected_peer_certificate = binding, entry['certificate']
            ch.enrollment_generation = binding['enrollment_generation']
            ch.trusted, ch.attestation = True, 'possession'
            on_authenticated(ch)
            return {'accepted': True, 'cluster': node.manifest.audience,
                    'border': border_binding(node.manifest, node.node_id)}
        channel = AttachmentChannel(reader, writer, local_identity=node.manifest.node(node.node_id)['identity'],
            member_id=None, is_border_side=True, nonce=nonce, current=current,
            handlers={**handlers, 'in2n/attest': attest, 'in2n/hello': hello})
        async def deadline():
            await asyncio.sleep(10)
            if not channel.trusted: await channel.close()
        channel.admission_deadline = asyncio.create_task(deadline())
        await channel.start()
        return channel
    except BaseException:
        if channel: await channel.close()
        else: writer.close()
        raise


class MemberAttachments:
    def __init__(self, manifest, member, private_key, *, ca_file, handlers, current):
        check(manifest.anchor_key_id is not None, 'unverified_cluster_manifest', 403)
        validate_binding(member, 'member')
        check(set(handlers) <= EXECUTION and callable(current), 'attachment_method_refused')
        self.manifest, self.member, self.private_key = manifest, dict(member), private_key
        self.ca_file, self.handlers, self.current = ca_file, dict(handlers), current
        self.channels, self.tasks, self.closing = {}, set(), False
        self._connecting = set()

    async def connect(self, node_id):
        check(not self.closing and node_id not in self._connecting, 'attachment_busy', 409)
        check(node_id not in self.channels or self.channels[node_id]._closed, 'attachment_exists', 409)
        self._connecting.add(node_id)
        node = self.manifest.node(node_id); address = node['endpoints']['in2n']
        writer, channel = None, None
        try:
            await self.current()
            reader, writer = await exporter_tls.open_connection(address['host'], address['port'],
                ca_file=self.ca_file, server_hostname=address['server_name'])
            nonce = await read_border_preamble(reader)
            check(nonce is not None, 'attachment_preamble_refused', 403)
            async def current(ch):
                await self.current()
                check(time_valid(node['certificate']), 'node_certificate_expired', 403)
                check(self.channels.get(node_id) in (None, ch), 'attachment_replaced', 409)
            channel = AttachmentChannel(reader, writer, local_identity=self.member['member_id'],
                member_id=self.member['member_id'], is_border_side=False,
                nonce=nonce, handlers=self.handlers, current=current)
            await channel.start()
            member_nonce = secrets.token_bytes(32)
            params = {'binding_profile': 'in2n-tls-exporter-v1', 'member_nonce': member_nonce.hex()}
            attested = await channel.call('in2n/attest', params, timeout=10)
            exact(attested, 'cluster_attestation')
            proof = verify(attested['cluster_attestation'], node['certificate'], 'attachment-border')
            expected = transcript(self.manifest, node_id, channel, member_nonce)
            check(proof == expected, 'attachment_proof_mismatch', 403)
            member_proof = sign('attachment-member', dict(expected, member=self.member, role='execution-member'), self.private_key)
            answer = await channel.call('in2n/hello', dict(params, member=self.member, proof=member_proof), timeout=10)
            check(answer == {'accepted': True, 'cluster': self.manifest.audience,
                            'border': border_binding(self.manifest, node_id)}, 'attachment_hello_refused', 403)
            channel.protected_peer_binding = border_binding(self.manifest, node_id)
            channel.protected_peer_certificate = node['certificate']
            channel.cluster_node_id = node_id
            channel.trusted, channel.attestation = True, 'possession'
            self.channels[node_id] = channel
            def closed(ch):
                if self.channels.get(node_id) is ch: self.channels.pop(node_id, None)
            channel.on_close = closed
            return channel
        except BaseException:
            if channel: await channel.close()
            elif writer: writer.close()
            raise
        finally:
            self._connecting.discard(node_id)

    async def start(self):
        check(not self.tasks and not self.closing, 'attachments_already_started', 409)
        async def maintain(node_id):
            while not self.closing:
                if node_id not in self.channels:
                    try: await self.connect(node_id)
                    except asyncio.CancelledError: raise
                    except Exception: pass
                await asyncio.sleep(1)
        for node in self.manifest.nodes:
            task = asyncio.create_task(maintain(node['node_id']))
            self.tasks.add(task); task.add_done_callback(self.tasks.discard)

    async def close(self):
        self.closing = True
        tasks = list(self.tasks)
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)
        for channel in list(self.channels.values()): await channel.close()

    async def send_admission(self, request):
        # Pick one authenticated connection. A failure is an unknown request;
        # reconnection or another available Border never triggers a second send.
        available = [ch for _, ch in sorted(self.channels.items()) if ch.trusted and not ch._closed]
        check(available, 'border_transport_unavailable', 503)
        return await available[0].call('execution/admission', request, timeout=5)
