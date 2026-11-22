"""Spec 198 cross-group protected federation: guard, grants, delegation, receiving-ledger authority, real mTLS channel."""
import asyncio
import copy
import types
import uuid

import pytest

from bgp.federation import certs, exporter_tls, protected_contract as c
from bgp.federation.ha import federation as fed
from bgp.federation.ha.border import ClusterBorderOperations
from bgp.federation.ha.config import HAError, sign_manifest, verify_manifest
from bgp.federation.ha.node import ClusterNode
from bgp.federation.ha.signatures import sign
from ha_support_179 import cluster_with_keys
from test_ha_contract_179 import manifest_fixture
from test_ha_execution_contract_179 import ha_approval

OPEN = ['*']
FULL = {'actions': list(fed.ACTIONS), 'members': OPEN, 'tools': OPEN}


def lab(manifest):
    ctx = {'access_mode': 'open-lab', **manifest.audience}
    return ctx


class MemberStub:
    """A member attached to the receiving group's Border: returns a member-signed result for the exact dispatched approval."""
    strict = trusted = True
    _closed = False

    def __init__(self, binding, key_pem):
        self.protected_peer_binding, self.key_pem = binding, key_pem
        self.approval = self.dispatch = None
        self.submissions = 0

    async def call(self, method, params, timeout):
        if method == 'execution/catalog':
            return self.catalog
        if method == 'execution/submit':
            self.submissions += 1
            self.approval, self.dispatch = params['approval']['payload'], params['dispatch']['payload']
            return {'operation_id': self.approval['operation_id'], 'attempt_id': self.dispatch['attempt_id']}
        if method == 'execution/status':
            return {'operation_id': params['operation_id'], 'receipt_ready': self.approval is not None, 'state': 'result_ready'}
        if method == 'execution/result':
            p, review = self.approval, self.approval
            payload = {'receipt_id': str(uuid.uuid4()), 'operation_id': p['operation_id'], 'approval_id': p['approval_id'],
                'approval_sha256': c.digest(c.HA_APPROVAL, p), 'attempt_id': self.dispatch['attempt_id'],
                **{k: review[k] for k in ('principal', 'border', 'member', 'model_profile', 'cluster')},
                'tool_call_sha256': c.sha256(review['tool_call']), 'started_at_ms': 1, 'finished_at_ms': 2,
                'outcome': 'succeeded', 'effect_status': 'finished', 'output': {'ok': True},
                'output_sha256': c.sha256({'ok': True}), 'tool_evidence_sha256': 'f' * 64,
                'usage': {'available': True}, 'audit_refs': {'result': 'controlled-audit'}, 'error_code': None}
            return c.sign(c.HA_RESULT, payload, self.key_pem)
        if method == 'execution/ack':
            return {'operation_id': self.approval['operation_id'], 'state': 'acknowledged'}
        raise AssertionError(method)


def group(tmp_path, tag, *, with_member):
    store, manifest, authorities, keys = cluster_with_keys()
    node = ClusterNode(authorities[0], private_key=keys[0], ca_file='unused', cert_file='unused', key_file='unused')
    audit, channels, stub = [], {}, None
    if with_member:
        _, member, payload = ha_approval()
        node.ledger.enroll_member(payload['member'], member['cert_pem'])
        stub = MemberStub(payload['member'], member['key_pem'])
        stub.catalog = {'member': payload['member'], 'model_profiles': [payload['model_profile']],
            'tools': [dict(payload['tool_call'], limits={k: v for k, v in payload['limits'].items() if k != 'expires_at_ms'})]}
        stub.payload = payload
        channels[payload['member']['member_id']] = stub
    def writer(event, record):
        audit.append((event, record)); return 'audit-%s-%d' % (tag, len(audit))
    ops = ClusterBorderOperations(node, state_dir=tmp_path / tag, member_channels=channels, audit_writer=writer)
    ops.context = dict(lab(manifest), installation_id=ops.identity['installation_id'])
    return types.SimpleNamespace(store=store, manifest=manifest, authorities=authorities, keys=keys, node=node,
                                 ops=ops, audit=audit, stub=stub)


def link(a, b, fed_b):
    """In-process transport that still exercises both guards and both signature checks."""
    async def send(cluster_id, method, params):
        assert cluster_id == b.manifest.cluster_id
        channel = types.SimpleNamespace(peer_cluster_id=a.manifest.cluster_id, peer_node_id=a.node.node_id)
        handler = fed_b.handle_relay if method == fed.RELAY else fed_b.handle_catalog
        return await handler(channel, params)
    return send


def world(tmp_path, *, grant_on_b=FULL, grant_on_a=FULL):
    a, b = group(tmp_path, 'a', with_member=False), group(tmp_path, 'b', with_member=True)
    peer_b = fed.Peer('azure', b.manifest, grant_on_a, 'unused')
    peer_a = fed.Peer('gcp', a.manifest, grant_on_b, 'unused')
    fa = fed.PeerFederation(a.ops, fed.PeerRegistry(a.manifest, [peer_b]), {}, state_dir=tmp_path / 'a')
    fb = fed.PeerFederation(b.ops, fed.PeerRegistry(b.manifest, [peer_a]), {}, state_dir=tmp_path / 'b')
    a.ops.federation, b.ops.federation = fa, fb
    fa.links, fb.links = link(a, b, fb), link(b, a, fa)
    return a, b, fa, fb


async def prepare_remote(a, b):
    cat = await a.ops.catalog({'auth_context': a.ops.context})
    entry = next(e for e in cat['members'] if e.get('remote'))
    return cat, entry, await a.ops.prepare({'auth_context': a.ops.context, 'client_nonce': 'nonce-' + str(uuid.uuid4()),
        'catalog_revision': cat['revision'], 'member_id': entry['member']['member_id'],
        'model_profile_id': entry['model_profiles'][0]['profile_id'], 'tool': entry['tools'][0]['tool'],
        'arguments': entry['tools'][0]['arguments']})


def relay(fa, fb_cluster, action, params, **override):
    peer = fa.registry.peers[fb_cluster]
    envelope = fa._envelope('peer-relay', peer, action, params, {'issuer': 'open-lab', 'display_name': 'Unauthenticated lab operator',
        'roles': ['lab-operator'], 'subject': fed.open_lab_subject(fa.ops.manifest.cluster_id)}, fa.node.authority.epoch)
    return envelope


async def deliver(fa, fb, envelope, a):
    channel = types.SimpleNamespace(peer_cluster_id=a.manifest.cluster_id, peer_node_id=a.node.node_id)
    return await fb.handle_relay(channel, {'relay': envelope})


# ------------------------------------------------------------------------------------------------ end to end

@pytest.mark.asyncio
async def test_union_catalog_tags_remote_member_and_keeps_local_revision(tmp_path):
    a, b, fa, fb = world(tmp_path)
    local = await a.ops._route_core('catalog', {'auth_context': a.ops.context})
    union = await a.ops.catalog({'auth_context': a.ops.context})
    remote = [e for e in union['members'] if e.get('remote')]
    assert [e['member'] for e in remote] == [b.stub.catalog['member']]
    assert remote[0]['remote']['cluster_id'] == b.manifest.cluster_id and remote[0]['remote']['label'] == 'azure'
    assert union['revision'] == local['revision'] and local['members'] == []
    assert union['federation']['peers'][0]['status'] == 'ok'


@pytest.mark.asyncio
async def test_cross_group_operation_is_authorized_in_the_receiving_ledger_and_audited_in_both(tmp_path):
    a, b, fa, fb = world(tmp_path)
    cat, entry, dto = await prepare_remote(a, b)
    assert dto['state'] == 'review_pending' and dto['remote']['cluster'] == b.manifest.audience
    assert dto['authority']['cluster_id'] == a.manifest.cluster_id          # the owner's HUD keeps its own group's identity
    assert dto['origin']['cluster_id'] == a.manifest.cluster_id and dto['review']['cluster']['cluster_id'] == b.manifest.cluster_id
    assert a.ops.ledger.lookup(operation_id=dto['operation_id']) is None     # nothing about it in the delegating ledger
    row = b.ops.ledger.lookup(operation_id=dto['operation_id'])
    assert row['origin']['cluster_id'] == a.manifest.cluster_id and row['origin']['origin_epoch'] >= 1
    decided = await a.ops.decision({'auth_context': a.ops.context, 'operation_id': dto['operation_id'],
        'revision': dto['revision'], 'review_digest': dto['review_digest'], 'decision': 'approve'})
    print('DECIDED', decided['state'], decided['attempt_count'])
    assert decided['attempt_count'] == 1 and decided['state'] in ('dispatch_claimed', 'member_admitted')
    assert b.stub.submissions == 1
    done = await a.ops.reconcile({'auth_context': a.ops.context, 'operation_id': dto['operation_id']})
    assert done['state'] == 'completed' and done['result']['durable_ack'] is True
    # B's own authority, epoch and ACK decided it; A's status served from the origin index sees the same operation.
    status = await a.ops.status({'auth_context': a.ops.context, 'operation_id': dto['operation_id']})
    assert status['state'] == 'completed' and status['remote']['cluster'] == b.manifest.audience
    assert b.stub.submissions == 1                                              # no second dispatch from any status/reconcile
    events_a = [e for e, _ in a.audit]
    assert 'protected_peer_relay_sent' in events_a and 'protected_peer_relay_result' in events_a
    assert any(record.get('origin', {}).get('cluster_id') == a.manifest.cluster_id for _, record in b.audit)


@pytest.mark.asyncio
async def test_status_for_unindexed_operation_finds_it_through_the_peer_but_native_operations_stay_invisible(tmp_path):
    a, b, fa, fb = world(tmp_path)
    _, _, dto = await prepare_remote(a, b)
    for path in fa.state.iterdir(): path.unlink()                               # another A Border has no index
    found = await a.ops.status({'auth_context': a.ops.context, 'operation_id': dto['operation_id']})
    assert found['operation_id'] == dto['operation_id'] and found['remote']['label'] == 'azure'
    # A native operation of B can never be read, decided or revoked through the peer.
    cat = await b.ops.catalog({'auth_context': b.ops.context})
    native = await b.ops.prepare({'auth_context': b.ops.context, 'client_nonce': 'native-1', 'catalog_revision': cat['revision'],
        'member_id': cat['members'][0]['member']['member_id'], 'model_profile_id': cat['members'][0]['model_profiles'][0]['profile_id'],
        'tool': cat['members'][0]['tools'][0]['tool'], 'arguments': cat['members'][0]['tools'][0]['arguments']})
    for action in ('status', 'revoke', 'reconcile'):
        envelope = relay(fa, b.manifest.cluster_id, action, {'operation_id': native['operation_id']})
        with pytest.raises(HAError, match='operation_not_found'):
            await deliver(fa, fb, envelope, a)
    assert b.ops.ledger.lookup(operation_id=native['operation_id'])['revoked'] is False


@pytest.mark.asyncio
async def test_local_member_flow_is_unchanged_by_federation(tmp_path):
    a, b, fa, fb = world(tmp_path)
    cat = await b.ops.catalog({'auth_context': b.ops.context})
    assert cat['members'] and all('remote' not in e for e in cat['members'])
    entry = next(e for e in cat['members'] if not e.get('remote'))
    prepared = await b.ops.prepare({'auth_context': b.ops.context, 'client_nonce': 'local-1', 'catalog_revision': cat['revision'],
        'member_id': entry['member']['member_id'], 'model_profile_id': entry['model_profiles'][0]['profile_id'],
        'tool': entry['tools'][0]['tool'], 'arguments': entry['tools'][0]['arguments']})
    assert 'origin' not in prepared and 'remote' not in prepared
    assert 'origin' not in b.ops.ledger.lookup(operation_id=prepared['operation_id'])


# ------------------------------------------------------------------------------------------------ negative cases

PREPARE = {'client_nonce': 'n-1', 'catalog_revision': 'x', 'member_id': 'm', 'model_profile_id': 'p', 'tool': 't', 'arguments': {}}


@pytest.mark.asyncio
async def test_no_grant_for_the_action_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path, grant_on_b={'actions': ['status'], 'members': OPEN, 'tools': OPEN})
    with pytest.raises(HAError, match='peer_grant_denied'):
        await deliver(fa, fb, relay(fa, b.manifest.cluster_id, 'prepare', PREPARE), a)
    union = await a.ops.catalog({'auth_context': a.ops.context})     # without a catalog grant nothing is even listed
    assert not [e for e in union['members'] if e.get('remote')]
    assert union['federation']['peers'][0] == {'label': 'azure', 'cluster_id': b.manifest.cluster_id, 'status': 'unavailable',
                                               'error': 'peer_grant_denied', 'members': 0}


@pytest.mark.asyncio
async def test_wrong_target_member_or_tool_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path, grant_on_b={'actions': ['prepare', 'status'], 'members': [str(uuid.uuid4())], 'tools': OPEN})
    with pytest.raises(HAError, match='peer_grant_denied'):
        await deliver(fa, fb, relay(fa, b.manifest.cluster_id, 'prepare', PREPARE), a)
    a, b, fa, fb = world(tmp_path / 'again', grant_on_b={'actions': ['prepare', 'catalog'], 'members': OPEN, 'tools': ['some-other-tool']})
    with pytest.raises(HAError, match='peer_grant_denied'):
        await deliver(fa, fb, relay(fa, b.manifest.cluster_id, 'prepare', PREPARE), a)
    cat = await fb.handle_catalog(types.SimpleNamespace(peer_cluster_id=a.manifest.cluster_id, peer_node_id=a.node.node_id),
        {'relay': fa._envelope('peer-catalog', fa.registry.peers[b.manifest.cluster_id], 'catalog', {}, lab_principal(a), fa.node.authority.epoch)})
    assert cat['result']['members'] == []                                       # an ungranted tool is not even advertised


def lab_principal(a):
    return {'issuer': 'open-lab', 'display_name': 'Unauthenticated lab operator', 'roles': ['lab-operator'],
            'subject': fed.open_lab_subject(a.manifest.cluster_id)}


@pytest.mark.asyncio
async def test_stale_origin_epoch_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    fb.guard.epochs[a.manifest.cluster_id] = a.node.authority.epoch + 5
    with pytest.raises(HAError, match='stale_origin_epoch'):
        await deliver(fa, fb, relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())}), a)


@pytest.mark.asyncio
async def test_replayed_nonce_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    cat, entry, dto = await prepare_remote(a, b)
    envelope = relay(fa, b.manifest.cluster_id, 'status', {'operation_id': dto['operation_id']})
    first = await deliver(fa, fb, envelope, a)
    assert first['result']['operation_id'] == dto['operation_id']
    with pytest.raises(HAError, match='peer_replay'):
        await deliver(fa, fb, envelope, a)


@pytest.mark.asyncio
async def test_expired_or_future_envelope_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    envelope = relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())})
    now = envelope['payload']['issued_at_ms']
    fb.guard.now = lambda: now + fed.ENVELOPE_TTL_MS + 1
    with pytest.raises(HAError, match='peer_envelope_expired'):
        await deliver(fa, fb, envelope, a)
    fb.guard.now = lambda: now - fed.CLOCK_SKEW_MS - 10
    with pytest.raises(HAError, match='peer_envelope_expired'):
        await deliver(fa, fb, envelope, a)


@pytest.mark.asyncio
async def test_unpinned_peer_key_or_cluster_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    envelope = relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())})
    _, rogue_key = certs.create_self_signed('rogue')
    forged = sign('peer-relay', envelope['payload'], rogue_key)
    with pytest.raises(HAError, match='peer_unpinned'):
        await deliver(fa, fb, forged, a)
    stranger = copy.deepcopy(envelope['payload'])
    stranger['origin']['cluster_id'] = str(uuid.uuid4())
    with pytest.raises(HAError, match='peer_unpinned'):
        await deliver(fa, fb, sign('peer-relay', stranger, a.keys[0]), a)
    # the right key under another node identity of the same group is refused as a channel mismatch
    other = types.SimpleNamespace(peer_cluster_id=a.manifest.cluster_id, peer_node_id=a.manifest.nodes[1]['node_id'])
    with pytest.raises(HAError, match='peer_channel_mismatch'):
        await fb.handle_relay(other, {'relay': envelope})


@pytest.mark.asyncio
async def test_revoked_peer_is_refused_on_every_path(tmp_path):
    a, b, fa, fb = world(tmp_path)
    envelope = relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())})
    fb.registry.revoke(a.manifest.cluster_id)
    with pytest.raises(HAError, match='peer_revoked'):
        await deliver(fa, fb, envelope, a)
    fa.registry.revoke(b.manifest.cluster_id)
    union = await a.ops.catalog({'auth_context': a.ops.context})
    assert union['federation']['peers'][0]['error'] == 'peer_revoked' and not [e for e in union['members'] if e.get('remote')]


@pytest.mark.asyncio
async def test_wrong_audience_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    third = types.SimpleNamespace(audience={'cluster_id': str(uuid.uuid4()), 'generation': str(uuid.uuid4())})
    envelope = fa._envelope('peer-relay', third, 'status', {'operation_id': str(uuid.uuid4())}, lab_principal(a), fa.node.authority.epoch)
    with pytest.raises(HAError, match='peer_audience_mismatch'):
        await deliver(fa, fb, envelope, a)
    stale = copy.deepcopy(relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())})['payload'])
    stale['origin']['generation'] = str(uuid.uuid4())
    with pytest.raises(HAError, match='peer_audience_mismatch'):
        await deliver(fa, fb, sign('peer-relay', stale, a.keys[0]), a)


@pytest.mark.asyncio
async def test_tampered_params_or_digest_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    envelope = relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())})
    tampered = copy.deepcopy(envelope)
    tampered['payload']['params'] = {'operation_id': str(uuid.uuid4())}
    with pytest.raises(HAError, match='invalid_ha_proof'):
        await deliver(fa, fb, tampered, a)
    # a correctly signed envelope whose params_sha256 does not match its params
    wrong = copy.deepcopy(envelope['payload'])
    wrong['params_sha256'] = '0' * 64
    with pytest.raises(HAError, match='peer_digest_mismatch'):
        await deliver(fa, fb, sign('peer-relay', wrong, a.keys[0]), a)
    extra = copy.deepcopy(envelope['payload'])
    extra['params'] = dict(extra['params'], injected='x')
    extra['params_sha256'] = c.sha256(extra['params'])
    with pytest.raises(HAError, match='invalid_peer_envelope'):
        await deliver(fa, fb, sign('peer-relay', extra, a.keys[0]), a)


@pytest.mark.asyncio
async def test_only_the_origin_groups_open_lab_principal_can_cross(tmp_path):
    a, b, fa, fb = world(tmp_path)
    for principal in (dict(lab_principal(a), subject=str(uuid.uuid4())),
                      {'issuer': 'device-key', 'display_name': 'Enrolled mobile device', 'roles': ['device-operator'],
                       'subject': str(uuid.uuid4())}):
        payload = copy.deepcopy(relay(fa, b.manifest.cluster_id, 'status', {'operation_id': str(uuid.uuid4())})['payload'])
        payload['principal'] = principal
        with pytest.raises((HAError, c.ProtectedError)):
            await deliver(fa, fb, sign('peer-relay', payload, a.keys[0]), a)
    # a device principal on the ingress never crosses: the local flow answers, no relay is attempted
    sent = []
    async def spy(cluster_id, method, params): sent.append(method); raise AssertionError('relay attempted')
    fa.links = spy
    device = {'access_mode': 'cluster-device-proof', 'proof': {}, 'params': {}}
    with pytest.raises(HAError):
        await a.ops.catalog({'auth_context': device})
    assert not sent


@pytest.mark.asyncio
async def test_peer_response_that_does_not_match_its_proof_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    honest = fa.links
    async def tamper(cluster_id, method, params):
        reply = await honest(cluster_id, method, params)
        reply = copy.deepcopy(reply)
        if method == fed.RELAY:
            reply['result']['state'] = 'completed'
        return reply
    fa.links = tamper
    cat, entry, _ = None, None, None
    with pytest.raises(HAError, match='peer_response_invalid'):
        await prepare_remote(a, b)


@pytest.mark.asyncio
async def test_lost_reply_is_never_retried(tmp_path):
    a, b, fa, fb = world(tmp_path)
    honest, calls = fa.links, []
    async def lose(cluster_id, method, params):
        calls.append(method)
        result = await honest(cluster_id, method, params)
        if method == fed.RELAY:
            raise ConnectionError('reply lost after the remote group acted')
        return result
    fa.links = lose
    with pytest.raises(ConnectionError):
        await prepare_remote(a, b)
    assert calls.count(fed.RELAY) == 1
    assert [row for row in b.store.rows if str(row).startswith('operations/')]   # the remote op exists once, recoverable


@pytest.mark.asyncio
async def test_catalog_member_id_collision_is_refused(tmp_path):
    a, b, fa, fb = world(tmp_path)
    a.ops.member_channels[b.stub.catalog['member']['member_id']] = b.stub       # A attaches a member with the same id
    union = await a.ops.catalog({'auth_context': a.ops.context})
    assert union['federation']['peers'][0]['status'] == 'unavailable'
    assert union['federation']['peers'][0]['error'] == 'ambiguous_catalog'


# ------------------------------------------------------------------------------------------------ configuration

def write(path, value):
    path.write_bytes(c.encode(value)); path.chmod(0o600)
    return str(path)


def peer_item(tmp_path, other, anchor, anchor_key, grant=FULL, **change):
    root = tmp_path / 'peer'; root.mkdir(exist_ok=True)
    item = {'label': 'azure', 'cluster_id': other.cluster_id, 'generation': other.generation,
            'manifest_file': write(root / 'manifest.json', sign_manifest(other.value, anchor_key)),
            'anchor_certificate_file': str(root / 'root.crt'), 'anchor_key_id': c.key_id(anchor),
            'transport_ca_file': str(root / 'ca.crt'), 'grant': grant}
    (root / 'root.crt').write_text(anchor); (root / 'root.crt').chmod(0o600)
    (root / 'ca.crt').write_text('ca'); (root / 'ca.crt').chmod(0o600)
    item.update(change)
    return item


def config(tmp_path, peers, **change):
    for name in ('transport.crt', 'transport.key', 'peers.pem'):
        (tmp_path / name).write_text('x'); (tmp_path / name).chmod(0o600)
    value = {'schema_version': 1, 'listen': {'host': '127.0.0.1', 'port': 7445}, 'dial_port': 7445,
             'transport_certificate_file': str(tmp_path / 'transport.crt'), 'private_key_file': str(tmp_path / 'transport.key'),
             'peer_ca_bundle_file': str(tmp_path / 'peers.pem'), 'peers': peers}
    value.update(change)
    return write(tmp_path / 'peer-federation.json', value)


def two_manifests():
    value_a, root_a, key_a = manifest_fixture()
    value_b, root_b, key_b = manifest_fixture()
    ma = verify_manifest(sign_manifest(value_a, key_a), root_a, expected_key_id=c.key_id(root_a))
    mb = verify_manifest(sign_manifest(value_b, key_b), root_b, expected_key_id=c.key_id(root_b))
    return ma, mb, root_b, key_b


def test_peer_file_loads_only_when_the_peer_manifest_verifies_against_its_pinned_anchor(tmp_path):
    ma, mb, root_b, key_b = two_manifests()
    path = config(tmp_path, [peer_item(tmp_path, mb, root_b, key_b)])
    cfg, registry, files = fed.load_peer_config(path, ma)
    assert list(registry.peers) == [mb.cluster_id] and str(path) in files
    wrong_anchor, _ = certs.create_self_signed('other-anchor')
    bad = config(tmp_path, [peer_item(tmp_path, mb, wrong_anchor, key_b)])
    with pytest.raises(HAError):
        fed.load_peer_config(bad, ma)
    swapped = config(tmp_path, [peer_item(tmp_path, mb, root_b, key_b, cluster_id=str(uuid.uuid4()))])
    with pytest.raises(HAError, match='peer_audience_mismatch'):
        fed.load_peer_config(swapped, ma)
    with pytest.raises(HAError, match='peer_is_local_cluster'):
        fed.load_peer_config(config(tmp_path, [peer_item(tmp_path, ma, root_b, key_b, cluster_id=ma.cluster_id, generation=ma.generation)]), ma)


@pytest.mark.parametrize('grant', [
    {'actions': [], 'members': OPEN, 'tools': OPEN},
    {'actions': ['prepare'], 'members': ['*', 'm'], 'tools': OPEN},
    {'actions': ['*'], 'members': OPEN, 'tools': OPEN},
    {'actions': ['prepare', 'deploy'], 'members': OPEN, 'tools': OPEN},
    {'actions': ['prepare'], 'members': OPEN},
])
def test_malformed_or_wildcard_action_grants_are_refused(tmp_path, grant):
    ma, mb, root_b, key_b = two_manifests()
    with pytest.raises((HAError, c.ProtectedError)):
        fed.load_peer_config(config(tmp_path, [peer_item(tmp_path, mb, root_b, key_b, grant=grant)]), ma)


def test_peer_file_rejects_unknown_fields_and_bad_listen(tmp_path):
    ma, mb, root_b, key_b = two_manifests()
    item = peer_item(tmp_path, mb, root_b, key_b)
    for change in ({'extra': 1}, {'listen': {'host': 'peer.example', 'port': 7445}}, {'dial_port': 0}):
        with pytest.raises((HAError, c.ProtectedError)):
            fed.load_peer_config(config(tmp_path, [item], **change), ma)
    value = c.decode((tmp_path / 'peer-federation.json').read_bytes())
    assert value['schema_version'] == 1


# ------------------------------------------------------------------------------------------------ real mTLS channel

def signed_cluster(tmp_path, tag):
    value, root, root_key = manifest_fixture()
    ca, ca_key = certs.create_risk_ca('peer-' + tag)
    keys = []
    for node in value['nodes']:
        node['certificate'], key = certs.issue_cert(ca, ca_key, node['identity'], san=tag + '.peer.test')
        node['key_id'] = c.key_id(node['certificate'])
        keys.append(key)
    manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=c.key_id(root))
    files = {}
    for name, text in [('ca', ca)] + [('cert%d' % i, n['certificate']) for i, n in enumerate(value['nodes'])] + [('key%d' % i, k) for i, k in enumerate(keys)]:
        path = tmp_path / (tag + '-' + name)
        path.write_text(text); path.chmod(0o600)
        files[name] = str(path)
    return manifest, keys, files


async def mtls_pair(tmp_path, *, initiator_node=0):
    ma, keys_a, fa = signed_cluster(tmp_path, 'a')
    mb, keys_b, fb = signed_cluster(tmp_path, 'b')
    ids_a, ids_b = [n['node_id'] for n in ma.nodes], [n['node_id'] for n in mb.nodes]
    received = asyncio.Queue()
    async def current(cluster_id, node_id): return None
    async def catalog(channel, params): return {'echo': params, 'peer': channel.peer_cluster_id}
    async def accept(reader, writer):
        try:
            ch = await fed.attach_peer(reader, writer, local_manifest=ma, local_node_id=ids_a[0], peer=fed.Peer('b', mb, FULL, fb['ca']),
                peer_node_id=ids_b[initiator_node], private_key=keys_a[0], current=current,
                handlers={fed.CATALOG: catalog}, is_initiator=False)
            await received.put(ch)
        except Exception as exc:
            await received.put(exc)
    server = await exporter_tls.start_server(accept, '127.0.0.1', 0, cert_file=fa['cert0'], key_file=fa['key0'], peer_ca_file=fb['ca'])
    try:
        reader, writer = await exporter_tls.open_connection('127.0.0.1', server.sockets[0].getsockname()[1], ca_file=fa['ca'],
            server_hostname='a.peer.test', cert_file=fb['cert%d' % initiator_node], key_file=fb['key%d' % initiator_node])
        return ma, mb, ids_a, ids_b, keys_b, fb, received, server, reader, writer, current, catalog
    except BaseException:
        server.close(); await server.wait_closed(); raise


@pytest.mark.asyncio
async def test_pinned_mutual_peer_channel_authenticates_and_carries_only_federation_methods(tmp_path):
    ma, mb, ids_a, ids_b, keys_b, fb, received, server, reader, writer, current, catalog = await mtls_pair(tmp_path)
    try:
        client = await fed.attach_peer(reader, writer, local_manifest=mb, local_node_id=ids_b[0], peer=fed.Peer('a', ma, FULL, 'x'),
            peer_node_id=ids_a[0], private_key=keys_b[0], current=current, handlers={fed.CATALOG: catalog}, is_initiator=True)
        peer = await asyncio.wait_for(received.get(), 3)
        assert not isinstance(peer, Exception)
        assert client.authenticated and peer.authenticated and peer.peer_cluster_id == mb.cluster_id
        assert await client.call(fed.CATALOG, {'x': 1}) == {'echo': {'x': 1}, 'peer': mb.cluster_id}   # the handler runs on the acceptor, whose peer is B
        with pytest.raises(HAError, match='peer_method_refused'):
            await client.call('n2n/cluster/forward', {})
        with pytest.raises(HAError, match='peer_notification_refused'):
            await client.notify(fed.CATALOG, {})
        await client.close(); await peer.close()
    finally:
        server.close(); await server.wait_closed()


@pytest.mark.asyncio
async def test_peer_channel_refuses_a_certificate_that_is_not_the_pinned_node_key(tmp_path):
    ma, mb, ids_a, ids_b, keys_b, fb, received, server, reader, writer, current, catalog = await mtls_pair(tmp_path, initiator_node=1)
    try:
        # node 1 holds a valid certificate but the dialer claims to be node 0: the pinned manifest key disagrees.
        with pytest.raises(HAError, match='peer_tls_mismatch'):
            await fed.attach_peer(reader, writer, local_manifest=mb, local_node_id=ids_b[1], peer=fed.Peer('a', ma, FULL, 'x'),
                peer_node_id=ids_a[1], private_key=keys_b[1], current=current, handlers={}, is_initiator=True)
    except HAError:
        raise
    finally:
        server.close(); await server.wait_closed()


@pytest.mark.asyncio
async def test_revocation_closes_an_established_peer_channel(tmp_path):
    ma, mb, ids_a, ids_b, keys_b, fb, received, server, reader, writer, current, catalog = await mtls_pair(tmp_path)
    live = {'ok': True}
    async def gate(cluster_id, node_id):
        if not live['ok']: raise HAError('peer_revoked', 403)
    try:
        client = await fed.attach_peer(reader, writer, local_manifest=mb, local_node_id=ids_b[0], peer=fed.Peer('a', ma, FULL, 'x'),
            peer_node_id=ids_a[0], private_key=keys_b[0], current=gate, handlers={}, is_initiator=True)
        await asyncio.wait_for(received.get(), 3)
        live['ok'] = False
        with pytest.raises(HAError, match='peer_revoked'):
            await client.call(fed.CATALOG, {})
        assert client._closed
    finally:
        server.close(); await server.wait_closed()


def test_generated_peer_config_is_accepted_by_the_loader_byte_for_byte(tmp_path):
    import json, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'labs' / 'ha'))
    import r10_group
    ma, mb, root_b, key_b = two_manifests()
    peer_root, local_root, state = tmp_path / 'b', tmp_path / 'a', tmp_path / 'state'
    for root in (peer_root, local_root):
        (root / 'identity').mkdir(parents=True); (root / 'transport').mkdir()
    for root, manifest in ((peer_root, mb), (local_root, ma)):
        (root / 'summary.json').write_text(json.dumps({'cluster_id': manifest.cluster_id, 'generation': manifest.generation,
                                                       'anchor_key_id': c.key_id(root_b)}))
    (peer_root / 'identity/manifest.json').write_bytes(c.encode(sign_manifest(mb.value, key_b)))
    (peer_root / 'identity/root.crt').write_text(root_b)
    (peer_root / 'transport/transport-ca.crt').write_text('ca')
    config, files = r10_group.peer_config(local_root, peer_root, 'gcp', members=['*'], tools=['*'], state=str(state))
    for name, raw in dict(files, **{'peer-federation.json': c.encode(config)}).items():
        target = state / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw); target.chmod(0o600)
    for name in ('transport/node.crt', 'transport/node.key'):
        target = state / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('x'); target.chmod(0o600)
    loaded, registry, listed = fed.load_peer_config(state / 'peer-federation.json', ma)
    assert list(registry.peers) == [mb.cluster_id]
    assert registry.peers[mb.cluster_id].grant['actions'] == list(fed.ACTIONS)


@pytest.mark.asyncio
async def test_follower_uses_quorum_epoch_not_its_own_null_epoch():
    """Live finding (r10g/r10h): authority.epoch is None on a follower; the envelope must carry the quorum epoch."""
    class Follower:
        epoch = None
        def current(self): return {'node_id': 'leader'}, 41
    fa = types.SimpleNamespace(node=types.SimpleNamespace(authority=Follower()))
    assert await fed.PeerFederation._epoch(fa) == 41
    peer = types.SimpleNamespace(audience={'cluster_id': 'c', 'generation': 'g'})
    def build(epoch):
        return fed.PeerFederation._envelope(types.SimpleNamespace(_origin=lambda: {}, now=lambda: 1,
            node=types.SimpleNamespace(private_key=None)), 'peer-catalog', peer, 'catalog', {}, {}, epoch)
    with pytest.raises(HAError, match='authority_unavailable'):
        build(None)                                   # a null epoch is refused at the sender, never signed
