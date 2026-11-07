"""NCFED cluster lifecycle and narrow leader forwarding, with no write retries."""
import asyncio

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .. import exporter_tls
from ..protected_contract import key_id, exact
from .channel import attach
from .config import check, HAError
from .operations import OperationLedger, member_key
from .signatures import sign

FORWARDED = frozenset({'catalog', 'prepare', 'decision', 'status', 'reconcile', 'revoke'})


class ClusterNode:
    def __init__(self, authority, *, private_key, ca_file, cert_file, key_file, dispatch=None):
        check(authority.manifest.anchor_key_id is not None, 'unverified_cluster_manifest', 403)
        self.authority, self.manifest = authority, authority.manifest
        self.node_id, self.private_key = authority.node_id, private_key
        self.ca_file, self.cert_file, self.key_file = ca_file, cert_file, key_file
        self.dispatch, self.edge_dispatch = dispatch, None
        self.local_current = None
        self.ledger = OperationLedger(authority)
        self.channels, self.tasks, self.server = {}, set(), None
        self.closing = False
        self.handlers = {'n2n/cluster/status': self._status, 'n2n/cluster/forward': self._forward,
                         'n2n/cluster/admission': self._admission,
                         'n2n/cluster/admission-status': self._admission_status,
                         'n2n/cluster/edge': self._edge}

    async def current(self, peer_id):
        if self.local_current: self.local_current()
        rows = await asyncio.to_thread(self.authority.snapshot)
        for identifier in (peer_id, self.node_id):
            enrolled = rows['control'][0]['nodes'].get(identifier)
            check(enrolled is not None and enrolled['state'] == 'active'
                  and enrolled['key_id'] == self.manifest.node(identifier)['key_id'], 'node_retired', 403)
        check(rows['control'][0]['active'], 'recovery_fenced', 503)

    async def member_current(self, binding):
        if self.local_current: self.local_current()
        key = member_key(binding)
        rows = await asyncio.to_thread(self.authority.snapshot, [key])
        self.ledger._member(rows, binding)
        check(rows['control'][0]['active'], 'recovery_fenced', 503)
        check(rows['control'][0]['nodes'][self.node_id]['state'] in ('active', 'drained'), 'node_retired', 403)
        return rows[key][0]

    def _register(self, channel):
        peer = channel.peer['node_id']
        old = self.channels.get(peer)
        check(old is None or old._closed, 'cluster_duplicate_channel', 409)
        self.channels[peer] = channel
        def closed(current):
            if self.channels.get(peer) is current:
                self.channels.pop(peer, None)
        channel.on_close = closed

    async def _accept(self, reader, writer):
        channel = None
        try:
            certificate = x509.load_der_x509_certificate(writer.get_extra_info('tls_peer_certificate'))
            fingerprint = key_id(certificate.public_bytes(serialization.Encoding.PEM).decode())
            peers = [node for node in self.manifest.nodes if node['key_id'] == fingerprint]
            check(len(peers) == 1 and peers[0]['node_id'] < self.node_id, 'cluster_peer_direction', 403)
            channel = await attach(reader, writer, manifest=self.manifest, node_id=self.node_id,
                peer_node_id=peers[0]['node_id'], private_key=self.private_key,
                current=self.current, handlers=self.handlers, is_initiator=False)
            self._register(channel)
        except BaseException:
            if channel:
                await channel.close()
            writer.close()
            raise

    async def _dial(self, peer):
        address = peer['endpoints']['cluster']
        while not self.closing:
            channel = self.channels.get(peer['node_id'])
            if channel is None or channel._closed:
                writer = None
                try:
                    reader, writer = await exporter_tls.open_connection(address['host'], address['port'],
                        ca_file=self.ca_file, server_hostname=address['server_name'],
                        cert_file=self.cert_file, key_file=self.key_file)
                    channel = await attach(reader, writer, manifest=self.manifest, node_id=self.node_id,
                        peer_node_id=peer['node_id'], private_key=self.private_key,
                        current=self.current, handlers=self.handlers, is_initiator=True)
                    self._register(channel)
                except asyncio.CancelledError:
                    if writer: writer.close()
                    raise
                except Exception:
                    if writer: writer.close()
            # Reconnection establishes transport only; it never repeats an RPC.
            await asyncio.sleep(1)

    async def start(self):
        check(self.server is None and not self.closing, 'cluster_already_started', 409)
        await asyncio.to_thread(self.authority.bootstrap)
        address = self.manifest.node(self.node_id)['endpoints']['cluster']
        self.server = await exporter_tls.start_server(self._accept, address['host'], address['port'],
            cert_file=self.cert_file, key_file=self.key_file, peer_ca_file=self.ca_file)
        await self.authority.start_renewal()
        for peer in self.manifest.nodes:
            if self.node_id < peer['node_id']:
                task = asyncio.create_task(self._dial(peer))
                self.tasks.add(task); task.add_done_callback(self.tasks.discard)

    async def close(self):
        self.closing = True
        if self.server:
            self.server.close(); await self.server.wait_closed()
        tasks = list(self.tasks)
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)
        for channel in list(self.channels.values()): await channel.close()
        await self.authority.stop_renewal()

    async def _status(self, channel, params):
        exact(params, '')
        leader, epoch = await asyncio.to_thread(self.authority.current)
        return {**self.manifest.audience, 'node_id': self.node_id, 'leader': leader,
                'epoch': epoch, 'observation_only': True}

    async def route(self, method, params):
        """Resolve once, send once. Lost replies never select a second leader."""
        await self.current(self.node_id)
        leader, _ = await asyncio.to_thread(self.authority.current)
        if leader['node_id'] == self.node_id:
            return await self.handlers[method](None, params)
        channel = self.channels.get(leader['node_id'])
        check(channel is not None and channel.authenticated, 'leader_transport_unavailable', 503)
        return await channel.call(method, params, timeout=5)

    async def _forward(self, channel, params):
        exact(params, 'action params')
        check(params['action'] in FORWARDED and callable(self.dispatch), 'cluster_method_refused', 403)
        leader, _ = await asyncio.to_thread(self.authority.current)
        check(leader['node_id'] == self.node_id, 'stale_authority', 409)
        # dispatch independently authenticates original context/device proof;
        # a serialized principal alone is never accepted as authorization.
        ingress = channel.peer['node_id'] if channel is not None else self.node_id
        return await self.dispatch(params['action'], params['params'], ingress_node_id=ingress)

    async def _edge(self, channel, params):
        exact(params, 'action params')
        check(callable(self.edge_dispatch), 'cluster_method_refused', 403)
        leader, _ = await asyncio.to_thread(self.authority.current)
        check(leader['node_id'] == self.node_id, 'stale_authority', 409)
        ingress = channel.peer['node_id'] if channel is not None else self.node_id
        return await self.edge_dispatch(params['action'], params['params'], ingress_node_id=ingress)

    async def _admission(self, channel, params):
        exact(params, 'request member')
        claim, revision = await asyncio.to_thread(self.ledger.admit, params['request'], params['member'])
        return sign('admission', {'claim': claim, 'commit_revision': revision}, self.private_key)

    async def _admission_status(self, channel, params):
        exact(params, 'request member')
        claim, revision = await asyncio.to_thread(self.ledger.admission_status, params['request'], params['member'])
        # Original-issuer evidence is retrieved as metadata only. A successor
        # must not sign an old claim as if it had issued a fresh admission.
        return {'claim': claim, 'commit_revision': revision, 'observation_only': True}

    async def admit_member(self, channel, request):
        binding = getattr(channel, 'protected_peer_binding', None)
        check(getattr(channel, 'trusted', False) and getattr(channel, 'strict', False)
              and getattr(channel, 'is_border_side', False), 'trusted_member_channel_required', 403)
        await self.member_current(binding)
        return await self.route('n2n/cluster/admission', {'request': request, 'member': binding})
