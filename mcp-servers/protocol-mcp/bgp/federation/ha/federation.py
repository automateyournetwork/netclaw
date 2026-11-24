"""Cross-group protected federation: any Border of one HA group to any member of another (spec 198, contract
`specs/198-azure-multicloud-ha/contracts/cross-cloud-federation.md`).

Each group keeps its own manifest, etcd, authority epoch and operation ledger. Nothing here shares authority:

* A pinned, mutually authenticated NCFED channel (`PeerChannel`) joins Borders of DIFFERENT groups. Peers are pinned by
  the peer group's offline-anchor-signed manifest, never by trust-on-first-use.
* The ingress Border signs a send-once, short-lived delegation envelope (`peer-relay`). It never carries owner
  credentials; only the open-lab principal of the ORIGIN group (the owner's own scope there) can cross.
* The RECEIVING group re-authorizes in its OWN ledger: new operation id, its own review, approval, dispatch, lease,
  admission and durable ACK. The origin is recorded on the row. A peer can only touch operations it originated.
* A peer can do only what its explicit grant table allows (action x member x tool). Default is nothing.
* No write is retried. A lost reply leaves the remote operation observable by `status`, exactly like `node.route`.
"""
import asyncio
import copy
import hashlib
import ipaddress
import secrets
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .. import exporter_tls, protected_contract as c
from ..certs import time_valid
from ..channel import FederationChannel, build_handshake
from ..protected_runtime import private_directory, private_write
from .config import HAError, check, read_private, verify_manifest
from .signatures import sign, verify

HELLO = 'n2n/peer/hello'
RELAY = 'n2n/peer/relay'
CATALOG = 'n2n/peer/catalog'
METHODS = frozenset({RELAY, CATALOG})
RELAY_ACTIONS = ('prepare', 'decision', 'status', 'reconcile', 'revoke')
ACTIONS = ('catalog',) + RELAY_ACTIONS
OPERATION_ACTIONS = ('decision', 'status', 'reconcile', 'revoke')
KIND_ACTIONS = {'peer-relay': frozenset(RELAY_ACTIONS), 'peer-catalog': frozenset({'catalog'})}
PREAMBLE = build_handshake(0, '0.0.0.0')
MAX_MESSAGE = 1024 * 1024 + 65536
ENVELOPE_TTL_MS = 30000
CLOCK_SKEW_MS = 5000
CATALOG_TTL_S = 15
MAX_PEERS = 4
MAX_NONCES = 4096
RELAY_TIMEOUT_S = 30
PARAM_FIELDS = {
    'prepare': 'client_nonce catalog_revision member_id model_profile_id tool arguments',
    'decision': 'operation_id revision review_digest decision',
    'status': 'operation_id', 'reconcile': 'operation_id', 'revoke': 'operation_id', 'catalog': '',
}


# ---------------------------------------------------------------------------------------------- configuration

def _ident_list(value, *, allow_star=True):
    check(isinstance(value, list) and 1 <= len(value) <= 64, 'invalid_peer_grant')
    for item in value:
        c.ident(item)
    check(len(set(value)) == len(value), 'invalid_peer_grant')
    check(not ('*' in value and len(value) > 1) and (allow_star or '*' not in value), 'invalid_peer_grant')
    return value


def validate_grant(grant):
    c.exact(grant, 'actions members tools')
    actions = _ident_list(grant['actions'], allow_star=False)
    check(set(actions) <= set(ACTIONS), 'invalid_peer_grant')
    _ident_list(grant['members']); _ident_list(grant['tools'])
    return grant


def validate_peer_config(value):
    """Exact private peer file. Grants are inbound: what that peer may do on THIS group's members."""
    fields = 'schema_version listen dial_port transport_certificate_file private_key_file peer_ca_bundle_file peers'
    c.exact(value, fields + (' revoked' if 'revoked' in value else ''))
    check(type(value['schema_version']) is int and value['schema_version'] == 1, 'invalid_peer_config')
    c.exact(value['listen'], 'host port')
    try:
        ipaddress.ip_address(value['listen']['host'])
    except ValueError:
        raise HAError('invalid_peer_config') from None
    check(type(value['listen']['port']) is int and 1 <= value['listen']['port'] <= 65535
          and type(value['dial_port']) is int and 1 <= value['dial_port'] <= 65535, 'invalid_peer_config')
    for key in ('transport_certificate_file', 'private_key_file', 'peer_ca_bundle_file'):
        check(isinstance(value[key], str) and value[key].startswith('/') and '\x00' not in value[key], 'invalid_peer_config')
    check(isinstance(value['peers'], list) and 1 <= len(value['peers']) <= MAX_PEERS, 'invalid_peer_config')
    seen = set()
    for peer in value['peers']:
        c.exact(peer, 'label cluster_id generation manifest_file anchor_certificate_file anchor_key_id transport_ca_file grant')
        c.ident(peer['label']); c.uuid_field(peer['cluster_id']); c.uuid_field(peer['generation'])
        c.digest_field(peer['anchor_key_id'])
        for key in ('manifest_file', 'anchor_certificate_file', 'transport_ca_file'):
            check(isinstance(peer[key], str) and peer[key].startswith('/') and '\x00' not in peer[key], 'invalid_peer_config')
        validate_grant(peer['grant'])
        check(peer['cluster_id'] not in seen, 'duplicate_peer')
        seen.add(peer['cluster_id'])
    for item in value.get('revoked', []):
        c.uuid_field(item)
    return value


class Peer:
    def __init__(self, label, manifest, grant, ca_file):
        self.label, self.manifest, self.grant, self.ca_file = label, manifest, grant, ca_file
        self.revoked = False

    @property
    def cluster_id(self):
        return self.manifest.cluster_id

    @property
    def audience(self):
        return self.manifest.audience


class PeerRegistry:
    """Pinned peer groups. A peer exists only if its offline-anchor-signed manifest verified."""
    def __init__(self, local_manifest, peers):
        check(local_manifest.anchor_key_id is not None, 'unverified_cluster_manifest', 403)
        self.local = local_manifest
        self.peers = {}
        for peer in peers:
            check(peer.cluster_id != local_manifest.cluster_id and peer.manifest.generation != local_manifest.generation,
                  'peer_is_local_cluster')
            check(peer.cluster_id not in self.peers, 'duplicate_peer')
            keys = {n['key_id'] for n in peer.manifest.nodes}
            check(not keys & {n['key_id'] for n in local_manifest.nodes}, 'peer_key_collision')
            self.peers[peer.cluster_id] = peer

    def peer(self, cluster_id):
        peer = self.peers.get(cluster_id)
        check(peer is not None, 'peer_unpinned', 403)
        check(not peer.revoked, 'peer_revoked', 403)
        return peer

    def revoke(self, cluster_id):
        self.peers[cluster_id].revoked = True

    def by_key(self, key_id):
        found = [(p, n) for p in self.peers.values() for n in p.manifest.nodes if n['key_id'] == key_id]
        check(len(found) == 1, 'peer_unpinned', 403)
        return found[0]


def load_peer_config(path, local_manifest, *, reader=read_private):
    """(config, registry, files). `files` are every private file the Border must re-hash on each current() check."""
    config = validate_peer_config(c.decode(reader(path)))
    peers, files = [], {str(path)}
    for item in config['peers']:
        envelope = c.decode(reader(item['manifest_file']))
        anchor = reader(item['anchor_certificate_file']).decode()
        manifest = verify_manifest(envelope, anchor, expected_key_id=item['anchor_key_id'])
        check(manifest.cluster_id == item['cluster_id'] and manifest.generation == item['generation'], 'peer_audience_mismatch', 403)
        reader(item['transport_ca_file'])
        peers.append(Peer(item['label'], manifest, item['grant'], item['transport_ca_file']))
        files.update((item['manifest_file'], item['anchor_certificate_file'], item['transport_ca_file']))
    for key in ('transport_certificate_file', 'private_key_file', 'peer_ca_bundle_file'):
        reader(config[key])
        files.add(config[key])
    registry = PeerRegistry(local_manifest, peers)
    for cluster_id in config.get('revoked', []):
        if cluster_id in registry.peers:
            registry.revoke(cluster_id)
    return config, registry, sorted(files)


# ---------------------------------------------------------------------------------------------- envelopes

def open_lab_subject(cluster_id):
    return str(uuid.uuid5(uuid.UUID(cluster_id), 'netclaw.open-lab.operator'))


def grant_allows(grant, action, params):
    """Inbound grant check. The member/tool restrictions bind at prepare; later actions are bound to the origin row."""
    if action not in grant['actions']:
        return False
    if action != 'prepare':
        return True
    members, tools = grant['members'], grant['tools']
    return (members == ['*'] or params.get('member_id') in members) and (tools == ['*'] or params.get('tool') in tools)


class PeerGuard:
    """Verifies every inbound delegation. Raises a fixed code and never returns a partially trusted value."""
    def __init__(self, registry, *, clock_ms=None):
        self.registry = registry
        self.now = clock_ms or (lambda: int(time.time() * 1000))
        self.nonces = {}      # origin cluster -> OrderedDict nonce -> expiry
        self.epochs = {}      # origin cluster -> highest origin epoch accepted

    def _remember(self, cluster_id, nonce, expires):
        bucket = self.nonces.setdefault(cluster_id, OrderedDict())
        now = self.now()
        for key in [k for k, v in bucket.items() if v < now]:
            del bucket[key]
        check(len(bucket) < MAX_NONCES, 'peer_capacity', 503)
        bucket[nonce] = expires

    def verify(self, envelope, *, kind, channel_peer=None, consume=True):
        check(kind in KIND_ACTIONS and isinstance(envelope, dict) and isinstance(envelope.get('payload'), dict), 'invalid_peer_envelope')
        payload = envelope['payload']
        c.exact(payload, 'origin target action params params_sha256 principal origin_epoch nonce issued_at_ms expires_at_ms')
        origin = payload['origin']
        c.exact(origin, 'cluster_id generation manifest_revision node_id installation_id')
        for key in ('cluster_id', 'generation', 'node_id', 'installation_id'):
            c.uuid_field(origin[key])
        peer = self.registry.peer(origin['cluster_id'])
        check(origin['generation'] == peer.manifest.generation and origin['manifest_revision'] == peer.manifest.revision,
              'peer_audience_mismatch', 403)
        try:
            node = peer.manifest.node(origin['node_id'])
        except HAError:
            raise HAError('peer_unpinned', 403) from None
        check(node['installation_id'] == origin['installation_id'] and envelope.get('key_id') == node['key_id'], 'peer_unpinned', 403)
        verify(envelope, node['certificate'], kind)       # fixed code invalid_ha_proof on any signature failure
        check(time_valid(node['certificate']), 'node_certificate_expired', 403)
        if channel_peer is not None:
            check(channel_peer == (origin['cluster_id'], origin['node_id']), 'peer_channel_mismatch', 403)
        check(payload['target'] == self.registry.local.audience, 'peer_audience_mismatch', 403)
        action, params = payload['action'], payload['params']
        check(action in KIND_ACTIONS[kind], 'peer_action_refused', 403)
        check(isinstance(params, dict) and set(params) == set(PARAM_FIELDS[action].split()), 'invalid_peer_envelope')
        check(c.sha256(params) == payload['params_sha256'], 'peer_digest_mismatch', 403)
        c.validate_principal(payload['principal'])
        check(payload['principal']['issuer'] == 'open-lab'
              and payload['principal']['subject'] == open_lab_subject(origin['cluster_id']), 'peer_principal_refused', 403)
        issued, expires, now = payload['issued_at_ms'], payload['expires_at_ms'], self.now()
        c.timestamp(issued); c.timestamp(expires)
        check(issued <= now + CLOCK_SKEW_MS and now < expires and 0 < expires - issued <= ENVELOPE_TTL_MS,
              'peer_envelope_expired', 403)
        epoch = payload['origin_epoch']
        check(type(epoch) is int and 0 < epoch <= 2**53 - 1, 'invalid_peer_envelope')
        check(epoch >= self.epochs.get(origin['cluster_id'], 0), 'stale_origin_epoch', 409)
        c.ident(payload['nonce'])
        bucket = self.nonces.get(origin['cluster_id'], {})
        check(payload['nonce'] not in bucket, 'peer_replay', 409)
        check(grant_allows(peer.grant, action, params), 'peer_grant_denied', 403)
        if consume:
            self._remember(origin['cluster_id'], payload['nonce'], expires + CLOCK_SKEW_MS)
            self.epochs[origin['cluster_id']] = max(epoch, self.epochs.get(origin['cluster_id'], 0))
        return payload, peer


# ---------------------------------------------------------------------------------------------- transport

def _binding(manifest, node_id):
    node = manifest.node(node_id)
    return {'cluster_id': manifest.cluster_id, 'generation': manifest.generation,
            'manifest_sha256': c.sha256(manifest.value), 'node_id': node_id, 'installation_id': node['installation_id']}


class PeerChannel(FederationChannel):
    """Mutual proof between Borders of different groups over the existing NCFED framing and pinned mTLS."""
    def __init__(self, reader, writer, *, local_manifest, local_node_id, peer, peer_node_id, private_key,
                 current, local_nonce, peer_nonce, is_initiator, handlers=None):
        check(local_manifest.anchor_key_id is not None and callable(current), 'unverified_cluster_manifest', 403)
        node, peer_node = local_manifest.node(local_node_id), peer.manifest.node(peer_node_id)
        check(writer.get_extra_info('tls_profile') == 'ncfed-cluster-mtls-v1'
              and writer.get_extra_info('tls_version') == 'TLSv1.3', 'peer_mtls_required', 403)
        exporter = writer.get_extra_info('tls_exporter')
        check(isinstance(exporter, bytes) and len(exporter) == 32, 'peer_exporter_required', 403)
        try:
            tls = x509.load_der_x509_certificate(writer.get_extra_info('tls_peer_certificate'))
            check(c.key_id(tls.public_bytes(serialization.Encoding.PEM).decode()) == peer_node['key_id'], 'peer_tls_mismatch', 403)
        except HAError:
            raise
        except Exception:
            raise HAError('peer_tls_mismatch', 403) from None
        check(set(handlers or {}) <= METHODS, 'peer_method_refused')
        super().__init__(reader, writer, local_identity=node['identity'], peer_as=0, peer_router_id='0.0.0.0',
                         manager=None, is_initiator=is_initiator, handlers=handlers)
        self.local_manifest, self.node, self.peer, self.peer_node = local_manifest, node, peer, peer_node
        self.peer_cluster_id, self.peer_node_id = peer.cluster_id, peer_node_id
        self.peer_identity = peer_node_id
        self.current, self.private_key = current, private_key
        self.local_nonce, self.peer_nonce, self.exporter = local_nonce, peer_nonce, exporter
        self.incarnation = str(uuid.uuid4())
        self.hello_received = self.hello_sent = False
        self._auth_timer = None
        self._peer_verified = asyncio.Event()
        self._ready = asyncio.Event()

    def _transcript(self, local, remote, incarnation, nonce, challenge):
        return {'local': local, 'peer': remote, 'role': 'peer-border', 'incarnation': incarnation,
                'nonce': nonce.hex(), 'challenge': challenge.hex(), 'tls_exporter': self.exporter.hex()}

    def _bindings(self):
        return (_binding(self.local_manifest, self.node['node_id']), _binding(self.peer.manifest, self.peer_node_id))

    async def start(self):
        await self.current(self.peer.cluster_id, self.peer_node_id)
        self._auth_timer = asyncio.get_running_loop().call_later(10, self.writer.abort)
        await super().start()
        local, remote = self._bindings()
        proof = sign('peer-hello', self._transcript(local, remote, self.incarnation, self.local_nonce, self.peer_nonce), self.private_key)
        self.hello_sent = True
        result = await super().call(HELLO, proof, timeout=10)
        await asyncio.wait_for(self._peer_verified.wait(), 10)
        check(result == {'accepted': True} and not self._closed, 'peer_authentication_failed', 403)
        self.authenticated = True
        self._ready.set()
        self._auth_timer.cancel()

    async def _current(self):
        if not self.authenticated and not self._closed:
            await asyncio.wait_for(self._ready.wait(), 10)
        check(self.authenticated and not self._closed, 'peer_not_authenticated', 403)
        try:
            check(time_valid(self.peer_node['certificate']), 'node_certificate_expired', 403)
            await self.current(self.peer.cluster_id, self.peer_node_id)
        except BaseException:
            await self.close()
            raise

    async def call(self, method, params, timeout=30):
        check(method in METHODS, 'peer_method_refused', 403)
        await self._current()
        try:
            return await super().call(method, params, timeout=timeout)
        finally:
            await self._current()

    async def notify(self, method, params):
        raise HAError('peer_notification_refused', 403)

    async def _send_frames(self, message):
        check(len(c.encode(message)) <= MAX_MESSAGE, 'peer_message_capacity')
        if self.authenticated:
            await self._current()
        await super()._send_frames(message)

    async def _dispatch(self, raw):
        try:
            msg = c.decode(raw, MAX_MESSAGE)
            check(isinstance(msg, dict) and msg.get('jsonrpc') == '2.0' and isinstance(msg.get('id'), str)
                  and 0 < len(msg['id']) <= 256)
            if 'method' in msg:
                c.exact(msg, 'jsonrpc id method params')
                await self._handle_request(msg)
            else:
                c.exact(msg, 'jsonrpc id error' if 'error' in msg else 'jsonrpc id result')
                future = self._pending.pop(msg['id'], None)
                if future and not future.done():
                    future.set_result(msg)
        except Exception:
            await self.close()

    async def _handle_request(self, msg):
        method, params, req_id = msg['method'], msg['params'], msg['id']
        try:
            if method == HELLO:
                check(not self.hello_received and self.hello_sent, 'peer_authentication_failed', 403)
                self.hello_received = True
                payload = verify(params, self.peer_node['certificate'], 'peer-hello')
                c.uuid_field(payload.get('incarnation'))
                local, remote = self._bindings()
                check(payload == self._transcript(remote, local, payload['incarnation'], self.peer_nonce, self.local_nonce),
                      'peer_transcript_mismatch', 403)
                await self.current(self.peer.cluster_id, self.peer_node_id)
                self._peer_verified.set()
                result = {'accepted': True}
            else:
                check(method in METHODS and method in self.handlers, 'peer_method_refused', 403)
                await self._current()
                check(isinstance(params, dict), 'invalid_peer_params')
                result = await self.handlers[method](self, params)
                await self._current()
            await self._send_frames({'jsonrpc': '2.0', 'id': req_id, 'result': result})
        except HAError as exc:
            await super()._send_frames(self._err(req_id, -32051, exc.code))
            if method == HELLO:
                await self.close()
        except Exception:
            await super()._send_frames(self._err(req_id, -32051, 'peer_request_unknown'))
            if method == HELLO:
                await self.close()

    async def close(self):
        if self._auth_timer:
            self._auth_timer.cancel()
        await super().close()


async def attach_peer(reader, writer, **options):
    channel = None
    try:
        local_nonce = secrets.token_bytes(32)
        writer.write(PREAMBLE + local_nonce)
        await writer.drain()
        raw = await asyncio.wait_for(reader.readexactly(len(PREAMBLE) + 32), 10)
        check(raw[:len(PREAMBLE)] == PREAMBLE, 'peer_preamble_refused', 403)
        channel = PeerChannel(reader, writer, local_nonce=local_nonce, peer_nonce=raw[len(PREAMBLE):], **options)
        await channel.start()
        return channel
    except BaseException:
        if channel:
            await channel.close()
        else:
            writer.close()
        raise


# ---------------------------------------------------------------------------------------------- federation

class PeerFederation:
    """Per-Border federation role: serves signed read-only catalogs and delegated operations, and sends them."""
    def __init__(self, ops, registry, config, *, state_dir, clock_ms=None):
        self.ops, self.registry, self.config = ops, registry, config
        self.now = clock_ms or (lambda: int(time.time() * 1000))
        self.guard = PeerGuard(registry, clock_ms=self.now)
        self.state = private_directory(Path(state_dir) / 'peer-ops')
        self.channels, self.tasks, self.server, self.closing = {}, set(), None, False
        self._catalog = {}     # cluster_id -> (fetched_at, response)
        self.links = None      # injected transport for tests: async (cluster_id, method, params) -> result

    # --- identity helpers --------------------------------------------------------------------------------------
    @property
    def node(self):
        return self.ops.node

    def _context(self):
        return {'access_mode': 'open-lab', 'installation_id': self.ops.identity['installation_id'], **self.ops.manifest.audience}

    def _origin(self):
        node = self.ops.manifest.node(self.node.node_id)
        return {'cluster_id': self.ops.manifest.cluster_id, 'generation': self.ops.manifest.generation,
                'manifest_revision': self.ops.manifest.revision, 'node_id': self.node.node_id,
                'installation_id': node['installation_id']}

    async def _current(self, cluster_id, node_id):
        peer = self.registry.peer(cluster_id)
        check(time_valid(peer.manifest.node(node_id)['certificate']), 'node_certificate_expired', 403)
        await self.node.current(self.node.node_id)

    # --- sender ------------------------------------------------------------------------------------------------
    async def _epoch(self):
        """The QUORUM's current authority epoch. `authority.epoch` is only set on the node holding the lease, so a follower
        Border that used it would sign a null epoch (found live in run r10g/r10h: ew1/ase1 ingress failed, nne1 worked)."""
        authority = self.node.authority
        if not hasattr(authority, 'current'):
            return authority.epoch
        _, epoch = await asyncio.to_thread(authority.current)
        return epoch

    def _envelope(self, kind, peer, action, params, principal, epoch):
        check(type(epoch) is int and epoch >= 0, 'authority_unavailable', 503)
        issued = self.now()
        payload = {'origin': self._origin(), 'target': peer.audience, 'action': action, 'params': params,
                   'params_sha256': c.sha256(params), 'principal': principal, 'origin_epoch': epoch,
                   'nonce': secrets.token_urlsafe(32), 'issued_at_ms': issued, 'expires_at_ms': issued + ENVELOPE_TTL_MS}
        return sign(kind, payload, self.node.private_key)

    async def _call(self, cluster_id, method, params, timeout):
        """Send exactly once on one authenticated channel. A failure is an unknown outcome, never a retry."""
        if self.links is not None:
            return await self.links(cluster_id, method, params)
        available = [ch for _, ch in sorted(self.channels.items()) if ch.peer_cluster_id == cluster_id
                     and ch.authenticated and not ch._closed]
        check(available, 'peer_transport_unavailable', 503)
        return await available[0].call(method, params, timeout=timeout)

    def _verify_response(self, peer, reply, nonce, *, kind, extra=None):
        c.exact(reply, 'result proof')
        proof = reply['proof']
        node_id = proof['payload'].get('served_by') if isinstance(proof, dict) and isinstance(proof.get('payload'), dict) else None
        check(isinstance(node_id, str), 'peer_response_invalid', 403)
        try:
            node = peer.manifest.node(node_id)
        except HAError:
            raise HAError('peer_unpinned', 403) from None
        payload = verify(proof, node['certificate'], kind)
        check(payload['nonce'] == nonce and payload['target'] == self.ops.manifest.audience
              and payload['cluster'] == peer.audience and payload['result_sha256'] == c.sha256(reply['result']),
              'peer_response_invalid', 403)
        return payload

    def _audit(self, event, principal, operation_id, peer, action, extra):
        record = dict({'principal': principal, 'operation_id': operation_id, 'approval_id': None, 'action': action,
                       'peer_cluster': peer.audience, 'peer_label': peer.label, 'cluster': self.ops.manifest.audience}, **extra)
        reference = self.ops.audit_writer(event, record)
        check(isinstance(reference, str) and 0 < len(reference) <= 200, 'audit_unavailable', 503)
        return reference

    async def fetch_catalog(self, cluster_id, principal, *, force=False):
        """Signed read-only catalog of one peer. Unavailable peers contribute no entries; stale data is never served."""
        peer = self.registry.peer(cluster_id)
        cached = self._catalog.get(cluster_id)
        if cached and not force and time.monotonic() - cached[0] < CATALOG_TTL_S:
            return cached[1]
        await self.node.current(self.node.node_id)
        envelope = self._envelope('peer-catalog', peer, 'catalog', {}, principal, await self._epoch())
        reply = await self._call(cluster_id, CATALOG, {'relay': envelope}, 20)
        payload = self._verify_response(peer, reply, envelope['payload']['nonce'], kind='peer-catalog-response')
        result = reply['result']
        c.exact(result, 'revision members')
        local_ids = {m['member_id'] for m in self._local_member_ids()}
        entries, seen = [], set()
        for entry in result['members']:
            c.validate_catalog_entry(entry)
            ident = entry['member']['member_id']
            check(ident not in seen and ident not in local_ids, 'ambiguous_catalog', 409)
            seen.add(ident)
            entries.append(entry)
        info = {'cluster': peer.audience, 'label': peer.label, 'revision': result['revision'], 'members': entries,
                'served_by': payload['served_by']}
        self._catalog[cluster_id] = (time.monotonic(), info)
        return info

    def _local_member_ids(self):
        return [dict(channel.protected_peer_binding) for channel in list(self.ops.member_channels.values())
                if getattr(channel, 'protected_peer_binding', None)]

    def _tag(self, info):
        remote = {'cluster_id': info['cluster']['cluster_id'], 'generation': info['cluster']['generation'], 'label': info['label']}
        return [dict(entry, remote=remote) for entry in info['members']]

    async def route(self, ops, action, params):
        """Ingress interposition. Local behaviour is unchanged unless the member/operation is remote."""
        check(isinstance(params, dict) and 'auth_context' in params, 'cluster_context_refused', 403)
        await ops._authenticate(action, params, ops.node.node_id)
        principal = None
        with ops._owner(params['auth_context']) as principal:
            pass
        remote_capable = principal['issuer'] == 'open-lab'      # device principals never cross groups
        if action == 'catalog':
            result = await ops._route_core(action, params)
            if not remote_capable:
                return result
            peers = []
            members = list(result['members'])
            for cluster_id in sorted(self.registry.peers):
                peer = self.registry.peers[cluster_id]
                try:
                    info = await self.fetch_catalog(cluster_id, principal)
                    members += self._tag(info)
                    peers.append({'label': peer.label, 'cluster_id': cluster_id, 'status': 'ok', 'members': len(info['members'])})
                except Exception as exc:
                    peers.append({'label': peer.label, 'cluster_id': cluster_id, 'status': 'unavailable',
                                  'error': exc.code if isinstance(exc, HAError) else 'peer_error', 'members': 0})
            members.sort(key=lambda e: e['member']['member_id'])
            return dict(result, members=members, federation={'peers': peers})
        if not remote_capable:
            return await ops._route_core(action, params)
        if action == 'prepare':
            c.exact(params, 'auth_context client_nonce catalog_revision member_id model_profile_id tool arguments')
            for cluster_id in sorted(self.registry.peers):
                cached = self._catalog.get(cluster_id)
                info = cached[1] if cached and time.monotonic() - cached[0] < CATALOG_TTL_S else None
                if info is None:
                    try: info = await self.fetch_catalog(cluster_id, principal)
                    except Exception: continue
                entry = next((e for e in info['members'] if e['member']['member_id'] == params['member_id']), None)
                if entry is not None:
                    return await self._relay_prepare(info, entry, params, principal)
            return await ops._route_core(action, params)
        if action in OPERATION_ACTIONS:
            return await self._route_operation(ops, action, params, principal)
        return await ops._route_core(action, params)

    async def _relay_prepare(self, info, entry, params, principal):
        model = next((m for m in entry['model_profiles'] if m['profile_id'] == params['model_profile_id']), None)
        tool = next((t for t in entry['tools'] if t['tool'] == params['tool'] and t['arguments'] == params['arguments']), None)
        check(model is not None and tool is not None, 'selection_not_supported', 403)
        relay = {k: params[k] for k in PARAM_FIELDS['prepare'].split()}
        relay['catalog_revision'] = info['revision']
        dto = await self._send_relay(info['cluster']['cluster_id'], 'prepare', relay, principal, original_nonce=params['client_nonce'])
        self._index(dto['operation_id'], info['cluster']['cluster_id'], principal, params['client_nonce'])
        return dto

    def _index(self, operation_id, cluster_id, principal, client_nonce=None):
        c.uuid_field(operation_id)
        private_write(self.state / (operation_id + '.json'), c.encode({'cluster_id': cluster_id, 'subject': principal['subject']}))
        if client_nonce is not None:
            key = c.sha256({'principal': principal, 'nonce': client_nonce})
            private_write(self.state / ('nonce-' + key + '.json'), c.encode({'operation_id': operation_id, 'cluster_id': cluster_id}))

    def _indexed(self, params, principal):
        try:
            if 'operation_id' in params:
                c.uuid_field(params['operation_id'])
                path = self.state / (params['operation_id'] + '.json')
            else:
                path = self.state / ('nonce-' + c.sha256({'principal': principal, 'nonce': params['client_nonce']}) + '.json')
            if not path.exists():
                return None
            value = c.decode(read_private(path))
            return value['cluster_id'], value.get('operation_id') or params.get('operation_id')
        except Exception:
            return None

    async def _route_operation(self, ops, action, params, principal):
        if action == 'status' and 'client_nonce' in params:
            hit = self._indexed(params, principal)
            if hit:
                return await self._send_relay(hit[0], 'status', {'operation_id': hit[1]}, principal)
            return await ops._route_core(action, params)
        hit = self._indexed(params, principal)
        body = {k: v for k, v in params.items() if k != 'auth_context'}
        if hit:
            return await self._send_relay(hit[0], action, body, principal)
        try:
            return await ops._route_core(action, params)
        except HAError as exc:
            if exc.code != 'operation_not_found':
                raise
            error = exc
        # Not ours: ask each pinned peer. The peer answers only for operations that peer-origin recorded.
        for cluster_id in sorted(self.registry.peers):
            try:
                dto = await self._send_relay(cluster_id, action, body, principal)
            except HAError as exc:
                if exc.code in ('operation_not_found', 'peer_transport_unavailable', 'peer_revoked', 'peer_grant_denied'):
                    continue
                raise
            self._index(dto['operation_id'], cluster_id, principal)
            return dto
        raise error

    async def _send_relay(self, cluster_id, action, params, principal, *, original_nonce=None):
        peer = self.registry.peer(cluster_id)
        await self.node.current(self.node.node_id)
        epoch_now = await self._epoch()
        envelope = self._envelope('peer-relay', peer, action, params, principal, epoch_now)
        nonce = envelope['payload']['nonce']
        pending_id = params.get('operation_id') or str(uuid.uuid4())
        self._audit('protected_peer_relay_sent', principal, pending_id, peer, action,
                    {'relay_nonce_sha256': hashlib.sha256(nonce.encode()).hexdigest(), 'relay_sha256': c.sha256(envelope['payload']),
                     'origin_epoch': envelope['payload']['origin_epoch']})
        reply = await self._call(cluster_id, RELAY, {'relay': envelope}, RELAY_TIMEOUT_S)
        proof = self._verify_response(peer, reply, nonce, kind='peer-relay-response')
        dto = copy.deepcopy(reply['result'])
        check(isinstance(dto, dict) and 'operation_id' in dto, 'peer_response_invalid', 403)
        remote_authority = dto.get('authority')
        dto['authority'] = {'mode': 'cluster', **self.ops.manifest.audience, 'served_by': self.node.node_id,
                            'epoch': epoch_now, 'observation_only': True}
        dto['remote'] = {'cluster': peer.audience, 'label': peer.label, 'authority': remote_authority,
                         'served_by': proof['served_by'], 'response_sha256': proof['result_sha256']}
        # Keep the caller's original reference on every response, including a
        # status read through an ingress without an operation index. The receiving
        # ledger keeps its separate namespaced nonce and signed origin metadata.
        client_nonce = (dto.get('origin') or {}).get('client_nonce', original_nonce)
        if client_nonce is not None:
            dto['client_nonce'] = client_nonce
        enrollment = peer.manifest.public_enrollment
        binding = {'origin': {**self.ops.manifest.audience, 'node_id': self.node.node_id},
                   'principal': principal, 'peer_anchor_key_id': peer.manifest.anchor_key_id,
                   'peer_manifest_sha256': c.sha256(enrollment['manifest']),
                   'operation_sha256': c.sha256(dto)}
        # Clients trust their pinned local node's explicit endorsement of this
        # configured peer and exact DTO. This is evidence, never an execution permit.
        dto['remote']['client_binding'] = {**enrollment,
                                          'endorsement': sign('peer-client', binding, self.node.private_key)}
        self._audit('protected_peer_relay_result', principal, dto['operation_id'], peer, action,
                    {'state': dto.get('state'), 'remote_operation_id': dto['operation_id'],
                     'response_sha256': proof['result_sha256'], 'remote_epoch': (remote_authority or {}).get('epoch')})
        return dto

    # --- receiver ---------------------------------------------------------------------------------------------
    def _sign_response(self, kind, payload, result, epoch):
        body = {'nonce': payload['nonce'], 'origin_cluster': payload['origin']['cluster_id'], 'target': payload['origin'] and
                {'cluster_id': payload['origin']['cluster_id'], 'generation': payload['origin']['generation']},
                'cluster': self.ops.manifest.audience, 'served_by': self.node.node_id, 'epoch': epoch,
                'result_sha256': c.sha256(result), 'issued_at_ms': self.now()}
        return {'result': result, 'proof': sign(kind + '-response', body, self.node.private_key)}

    async def handle_relay(self, channel, params):
        c.exact(params, 'relay')
        payload, peer = self.guard.verify(params['relay'], kind='peer-relay',
                                          channel_peer=(channel.peer_cluster_id, channel.peer_node_id), consume=False)
        forwarded = {'action': 'peer_relay', 'params': {'auth_context': self._context(), 'relay': params['relay']}}
        result = await self.node.route('n2n/cluster/forward', forwarded)
        return self._sign_response('peer-relay', payload, result, await self._epoch())

    async def handle_catalog(self, channel, params):
        c.exact(params, 'relay')
        payload, peer = self.guard.verify(params['relay'], kind='peer-catalog',
                                          channel_peer=(channel.peer_cluster_id, channel.peer_node_id), consume=True)
        await self.node.current(self.node.node_id)
        catalog = await self.ops._local_catalog({'auth_context': self._context()})
        grant = peer.grant
        members = []
        for entry in catalog['members']:
            if grant['members'] != ['*'] and entry['member']['member_id'] not in grant['members']:
                continue
            tools = [t for t in entry['tools'] if grant['tools'] == ['*'] or t['tool'] in grant['tools']]
            if tools:
                members.append(dict(entry, tools=tools))
        return self._sign_response('peer-catalog', payload, {'revision': catalog['revision'], 'members': members}, await self._epoch())

    async def execute_relay(self, ops, params):
        """Runs on the LEADER of the receiving group: re-verify, re-authorize in this group's own ledger."""
        check(set(params) == {'auth_context', 'relay'}, 'invalid_peer_envelope')
        payload, peer = self.guard.verify(params['relay'], kind='peer-relay', consume=True)
        action, body, ctx, origin = payload['action'], payload['params'], params['auth_context'], payload['origin']
        recorded = {'cluster_id': origin['cluster_id'], 'generation': origin['generation'], 'node_id': origin['node_id'],
                    'principal_subject': payload['principal']['subject'],
                    'relay_sha256': c.sha256(payload), 'origin_epoch': payload['origin_epoch']}
        if action == 'prepare':
            recorded['client_nonce'] = body['client_nonce']
            nonce = 'peer-' + c.sha256({'origin': origin['cluster_id'], 'nonce': body['client_nonce']})[:40]
            return await ops._local_prepare(dict(body, client_nonce=nonce, auth_context=ctx), origin=recorded)
        c.uuid_field(body['operation_id'])
        row = await asyncio.to_thread(ops.ledger.lookup, operation_id=body['operation_id'], principal=ops.principal)
        mine = row is not None and (row.get('origin') or {}).get('cluster_id') == origin['cluster_id'] \
            and row['origin'].get('principal_subject') == payload['principal']['subject']
        check(mine, 'operation_not_found', 404)           # native operations and other peers' operations are invisible
        return await getattr(ops, '_local_' + action)(dict(body, auth_context=ctx))

    # --- lifecycle --------------------------------------------------------------------------------------------
    async def _accept(self, reader, writer):
        channel = None
        try:
            der = writer.get_extra_info('tls_peer_certificate')
            pem = x509.load_der_x509_certificate(der).public_bytes(serialization.Encoding.PEM).decode()
            peer, node = self.registry.by_key(c.key_id(pem))
            self.registry.peer(peer.cluster_id)
            check(peer.cluster_id < self.ops.manifest.cluster_id, 'peer_direction', 403)
            channel = await attach_peer(reader, writer, local_manifest=self.ops.manifest, local_node_id=self.node.node_id,
                peer=peer, peer_node_id=node['node_id'], private_key=self.node.private_key, current=self._current,
                handlers={RELAY: self.handle_relay, CATALOG: self.handle_catalog}, is_initiator=False)
            self._register(channel)
        except BaseException:
            if channel:
                await channel.close()
            writer.close()
            raise

    def _register(self, channel):
        key = (channel.peer_cluster_id, channel.peer_node_id)
        old = self.channels.get(key)
        check(old is None or old._closed, 'peer_duplicate_channel', 409)
        self.channels[key] = channel
        def closed(current):
            if self.channels.get(key) is current:
                self.channels.pop(key, None)
        channel.on_close = closed

    async def _dial(self, peer, node):
        address = node['endpoints']['in2n']
        key = (peer.cluster_id, node['node_id'])
        while not self.closing:
            channel = self.channels.get(key)
            if channel is None or channel._closed:
                writer = None
                try:
                    self.registry.peer(peer.cluster_id)
                    # The dial name is the node's DNS name (the sandbox policy admits names, not IP literals).
                    reader, writer = await exporter_tls.open_connection(address['server_name'], self.config['dial_port'],
                        ca_file=peer.ca_file, server_hostname=address['server_name'],
                        cert_file=self.config['transport_certificate_file'], key_file=self.config['private_key_file'])
                    channel = await attach_peer(reader, writer, local_manifest=self.ops.manifest, local_node_id=self.node.node_id,
                        peer=peer, peer_node_id=node['node_id'], private_key=self.node.private_key, current=self._current,
                        handlers={RELAY: self.handle_relay, CATALOG: self.handle_catalog}, is_initiator=True)
                    self._register(channel)
                except asyncio.CancelledError:
                    if writer: writer.close()
                    raise
                except Exception:
                    if writer: writer.close()
            await asyncio.sleep(2)

    async def start(self):
        check(self.server is None and not self.closing, 'peer_already_started', 409)
        listen = self.config['listen']
        self.server = await exporter_tls.start_server(self._accept, listen['host'], listen['port'],
            cert_file=self.config['transport_certificate_file'], key_file=self.config['private_key_file'],
            peer_ca_file=self.config['peer_ca_bundle_file'], close_clients=True)
        for peer in self.registry.peers.values():
            if self.ops.manifest.cluster_id < peer.cluster_id:        # one dial direction per pair
                for node in peer.manifest.nodes:
                    task = asyncio.create_task(self._dial(peer, node))
                    self.tasks.add(task); task.add_done_callback(self.tasks.discard)

    async def close(self):
        self.closing = True
        if self.server:
            self.server.close()
        for task in list(self.tasks): task.cancel()
        if self.tasks: await asyncio.gather(*list(self.tasks), return_exceptions=True)
        for channel in list(self.channels.values()): await channel.close()
        if self.server: await self.server.wait_closed()
