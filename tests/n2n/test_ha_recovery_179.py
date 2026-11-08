"""Controlled lifecycle/recovery state-machine tests, never REAL qualification."""
import copy
import time
import uuid

import pytest

from bgp.federation import certs, protected_contract as c
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.config import HAError, Manifest
from bgp.federation.ha.lifecycle import Lifecycle, VoterChanges
from bgp.federation.ha.recovery import (
    snapshot_document, restore_records, install_restored, activate_restored,
    verify_isolation, isolation_message,
)
from test_ha_authority_179 import cluster, MemoryStore as StateStore


class MemoryStore(StateStore):
    prefix = "/netclaw/ha/fixture/generation/"

    def _request(self, path, body, *, read_only=False):
        assert path == "/v3/kv/range" and read_only and body["limit"] == 1
        return {"kvs": [{}] if self.rows else []}

from test_ha_contract_179 import manifest_fixture


def recovery_case():
    store, nodes = cluster()
    old = nodes[0].manifest
    source = snapshot_document(old, {k: v for k, v in store.rows.items()}, store.revision, now_ms=1000)
    value, _, _ = manifest_fixture()
    value.update(cluster_id=old.cluster_id, generation=str(uuid.uuid4()),
                 organization=old.value['organization'], revision=old.revision + 1)
    new = Manifest(value)
    certificate, key = certs.create_self_signed('recovery-host')
    body = {'schema_version': 1, 'receipt_id': str(uuid.uuid4()), **old.audience,
            'new_generation': new.generation, 'snapshot_sha256': c.sha256(source),
            'inventory_sha256': 'a' * 64, 'export_sha256': 'b' * 64,
            'observed_at_ms': 2000, 'method': 'owned-host-isolation-v1',
            'nodes': sorted(n['node_id'] for n in old.nodes),
            'voter_count': 3, 'executor_count': 1, 'observations_sha256': 'c' * 64}
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    import base64
    signer = serialization.load_pem_private_key(key.encode(), password=None)
    def proof(payload=body):
        signature = signer.sign(isolation_message(payload), ec.ECDSA(hashes.SHA256()))
        return {'payload': copy.deepcopy(payload), 'key_id': c.key_id(certificate),
                'signature': base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}
    receipt = verify_isolation(proof(), certificate, expected_key_id=c.key_id(certificate),
                               old_manifest=old, new_manifest=new, snapshot=source, now_ms=2001)
    return store, nodes, old, source, new, certificate, proof, receipt


def test_drain_retire_majority_and_same_generation_reentry_denied():
    store, nodes = cluster(); nodes[0].campaign()
    lifecycle = Lifecycle(nodes[0])
    result = lifecycle.drain(nodes[1].node_id)
    assert result['state'] == 'drained'
    assert store.read('control')[0]['membership_revision'] == 2
    with pytest.raises(HAError, match='node_drained'):
        nodes[1].campaign()
    lifecycle.retire(nodes[1].node_id)
    with pytest.raises(HAError, match='node_retired'):
        lifecycle.resume(nodes[1].node_id)
    with pytest.raises(HAError, match='node_retired'):
        nodes[1].bootstrap(create=True)


def test_lifecycle_denies_without_quorum_and_requires_drain_before_retirement():
    store, nodes = cluster(); nodes[0].campaign()
    lifecycle = Lifecycle(nodes[0])
    with pytest.raises(HAError, match='drain_required'):
        lifecycle.retire(nodes[1].node_id)
    before = copy.deepcopy(store.rows)
    store.available = False
    with pytest.raises(HAError, match='no_quorum'):
        lifecycle.drain(nodes[1].node_id)
    assert store.rows == before


def test_drain_last_active_node_refused_and_self_drain_commits_first():
    store, nodes = cluster(); nodes[0].campaign()
    lifecycle = Lifecycle(nodes[0])
    lifecycle.drain(nodes[1].node_id); lifecycle.drain(nodes[2].node_id)
    with pytest.raises(HAError, match='last_active_border'):
        lifecycle.drain(nodes[0].node_id)
    lifecycle.resume(nodes[1].node_id)
    lifecycle.drain(nodes[0].node_id)
    assert store.read('control')[0]['nodes'][nodes[0].node_id]['state'] == 'drained'
    with pytest.raises(HAError, match='node_drained'):
        nodes[0].mutate('bad', ['x'], lambda rows: ([('x', {}, None)], {}))


def test_snapshot_rejects_bad_audience_revision_capacity_and_leader_is_excluded():
    store, nodes = cluster(); nodes[0].campaign()
    snap = snapshot_document(nodes[0].manifest, store.rows, store.revision, now_ms=1000)
    assert 'leader' not in snap['records']
    wrong = copy.deepcopy(store.rows)
    wrong['control'][0]['generation'] = str(uuid.uuid4())
    with pytest.raises(HAError, match='snapshot_identity_mismatch'):
        snapshot_document(nodes[0].manifest, wrong, store.revision, now_ms=1000)
    with pytest.raises(HAError, match='invalid_snapshot_revision'):
        snapshot_document(nodes[0].manifest, store.rows, 0, now_ms=1000)


@pytest.mark.parametrize('fault', ['stale', 'future', 'forged', 'other_snapshot', 'same_generation', 'missing_node', 'boolean'])
def test_isolation_receipt_rejects_untrusted_or_mismatched_observation(fault):
    _, _, old, snap, new, certificate, proof, receipt = recovery_case()
    packet = proof(); now = 2001
    if fault == 'stale': now = 302001
    if fault == 'future': now = 1000
    if fault == 'forged': packet['payload']['export_sha256'] = 'd' * 64
    if fault == 'other_snapshot': snap = dict(snap, created_at_ms=1001)
    if fault == 'same_generation': new = old
    if fault == 'missing_node':
        body = packet['payload']; body['nodes'].pop(); packet = proof(body)
    if fault == 'boolean': packet = {'isolated': True}
    with pytest.raises(HAError):
        verify_isolation(packet, certificate, expected_key_id=c.key_id(certificate),
                         old_manifest=old, new_manifest=new, snapshot=snap, now_ms=now)


def test_restore_requires_fresh_identity_and_preserves_spent_unknown_records():
    store, nodes, old, snap, new, certificate, proof, receipt = recovery_case()
    snap['records']['claims/operation/model1'] = {'value': {'state': 'committed'}, 'revision': 1}
    snap['records']['resources/runner'] = {'value': {'state': 'reserved'}, 'revision': 1}
    snap['records']['operations/one'] = {'value': {'state': 'member_admitted', 'revision': 2,
        'result_ref': None, 'attempt_id': str(uuid.uuid4())}, 'revision': 1}
    records = restore_records(snap, old, new)
    assert records['control']['active'] is False
    assert records['control']['recovery']['capacity_frozen'] is True
    assert records['claims/operation/model1'] == {'state': 'committed'}
    assert records['resources/runner']['state'] == 'reserved'
    assert records['operations/one']['state'] == 'outcome_unknown'
    with pytest.raises(HAError, match='new_generation_required'):
        restore_records(snap, old, old)
    replacement = new.value
    replacement['nodes'] = old.nodes
    with pytest.raises(HAError, match='fresh_node_trust_required'):
        restore_records(snap, old, Manifest(replacement))


def test_restore_is_fenced_one_use_and_never_overwrites_existing_control():
    _, _, old, snap, new, certificate, proof, receipt = recovery_case()
    target = MemoryStore()
    result = install_restored(target, snap, old, new, receipt, now_ms=2001)
    assert result['complete'] and not result['activated']
    authority = Authority(target, new, new.nodes[0]['node_id'])
    with pytest.raises(HAError, match='recovery_fenced'):
        authority.campaign()
    activate_restored(target, snap, old, new, receipt, now_ms=2002)
    assert target.read('control')[0]['active']
    assert target.read('control')[0]['recovery']['capacity_frozen']
    assert authority.campaign()
    with pytest.raises(HAError, match='restore_already_activated'):
        activate_restored(target, snap, old, new, receipt, now_ms=2003)
    other, nodes = cluster()
    before = copy.deepcopy(other.rows)
    with pytest.raises(HAError, match='restore_target_not_empty'):
        install_restored(other, snap, old, new, receipt, now_ms=2001)
    assert other.rows == before


def test_opaque_receipt_cannot_be_replaced_by_unsigned_mapping_or_stale_proof():
    _, _, old, snap, new, _, _, receipt = recovery_case()
    with pytest.raises(HAError, match='trusted_isolation_required'):
        install_restored(MemoryStore(), snap, old, new, {'verified': True}, now_ms=2001)
    with pytest.raises(HAError, match='isolation_receipt_expired'):
        install_restored(MemoryStore(), snap, old, new, receipt, now_ms=302001)


def test_restore_recovers_exact_lost_ack_and_chunked_install_without_replay():
    _, _, old, snap, new, certificate, proof, receipt = recovery_case()
    target = MemoryStore(); target.lose_reply = True
    result = install_restored(target, snap, old, new, receipt, now_ms=2001)
    assert result['complete']
    before = target.mutations
    assert install_restored(target, snap, old, new, receipt, now_ms=2002) == result
    assert target.mutations == before


class MembershipFixture:
    def __init__(self):
        self.rows = [{'id': str(i + 1), 'learner': False, 'peer_urls': [f'https://v{i}:2380']} for i in range(3)]
        self.calls, self.lose_reply = 0, False

    def members(self):
        return copy.deepcopy(self.rows)

    def change(self, action, target):
        self.calls += 1
        if action == 'remove': self.rows = [r for r in self.rows if r['id'] != target]
        if action == 'add_learner': self.rows.append({'id': '4', 'learner': True, 'peer_urls': [target]})
        if action == 'promote':
            for row in self.rows:
                if row['id'] == target: row['learner'] = False
        if self.lose_reply:
            self.lose_reply = False
            raise HAError('commit_unknown', 503)


def test_voter_replacement_is_serialized_learner_first_and_never_repeats_unknown():
    store, nodes = cluster(); nodes[0].campaign()
    admin = MembershipFixture(); changes = VoterChanges(nodes[0], admin)
    plan = changes.prepare('add_learner', 'https://v3:2380')
    with pytest.raises(HAError, match='voter_change_in_progress'):
        changes.prepare('remove', '3')
    admin.lose_reply = True
    with pytest.raises(HAError, match='commit_unknown'):
        changes.apply(plan['change_id'])
    with pytest.raises(HAError, match='voter_change_outcome_unknown'):
        changes.apply(plan['change_id'])
    assert admin.calls == 1
    assert changes.reconcile(plan['change_id'])['state'] == 'completed'
    with pytest.raises(HAError, match='unsafe_voter_change'):
        changes.prepare('promote', '4')
    removal = changes.prepare('remove', '3'); changes.apply(removal['change_id'])
    with pytest.raises(HAError, match='unsafe_voter_change'):
        changes.prepare('remove', '2')
    promotion = changes.prepare('promote', '4'); changes.apply(promotion['change_id'])
    assert len(admin.rows) == 3 and all(not row['learner'] for row in admin.rows)


def test_voter_loss_of_quorum_or_changed_inventory_does_not_call_admin():
    store, nodes = cluster(); nodes[0].campaign()
    admin = MembershipFixture(); changes = VoterChanges(nodes[0], admin)
    plan = changes.prepare('remove', '3')
    store.available = False
    with pytest.raises(HAError): changes.apply(plan['change_id'])
    store.available = True
    admin.rows[0]['peer_urls'] = ['https://different:2380']
    with pytest.raises(HAError, match='voter_inventory_changed'):
        changes.apply(plan['change_id'])
    assert admin.calls == 0


def test_receipt_payload_mutation_cannot_refresh_proof_and_orphan_namespace_is_refused():
    _, _, old, snap, new, _, _, receipt = recovery_case()
    receipt.payload['observed_at_ms'] = 500000
    assert receipt.payload['observed_at_ms'] == 2000
    target = MemoryStore()
    target.rows['claims/orphan/model1'] = ({'state': 'committed'}, 1)
    with pytest.raises(HAError, match='restore_target_not_empty'):
        install_restored(target, snap, old, new, receipt, now_ms=2001)
    assert 'control' not in target.rows


def test_chunked_restore_preserves_all_decisions_and_completion_receipts():
    _, _, old, snap, new, certificate, proof, _ = recovery_case()
    for index in range(30):
        snap['records'][f'claims/work{index}/model1'] = {'value': {'state': 'committed'}, 'revision': 1}
    terminal = {'state': 'completed', 'revision': 3, 'result_ref': {'digest': 'a' * 64}, 'ack': {'original': True}}
    snap['records']['operations/completed'] = {'value': terminal, 'revision': 1}
    body = proof()['payload']; body['snapshot_sha256'] = c.sha256(snap)
    receipt = verify_isolation(proof(body), certificate, expected_key_id=c.key_id(certificate),
        old_manifest=old, new_manifest=new, snapshot=snap, now_ms=2001)
    target = MemoryStore()
    installed = install_restored(target, snap, old, new, receipt, now_ms=2001)
    assert installed['complete'] and installed['next_index'] == 31
    assert target.read('operations/completed')[0] == terminal
    assert len([key for key in target.rows if key.startswith('claims/')]) == 30
    assert target.mutations == 4


def test_export_uses_one_linearizable_bounded_prefix_read_and_refuses_truncation():
    import base64
    from bgp.federation.ha.recovery import export_snapshot
    store, nodes = cluster()
    class ExportFixture:
        prefix = f'/netclaw/ha/{nodes[0].manifest.cluster_id}/{nodes[0].manifest.generation}/'
        calls = 0
        truncated = False
        def _request(self, path, body, *, read_only):
            self.calls += 1
            assert path == '/v3/kv/range' and read_only and body['serializable'] is False
            assert base64.b64decode(body['key']).decode() == self.prefix
            return {'more': self.truncated, 'header': {'revision': str(store.revision)}, 'kvs': [
                {'key': base64.b64encode((self.prefix + key).encode()).decode(),
                 'value': base64.b64encode(c.encode(value)).decode(), 'mod_revision': str(revision)}
                for key, (value, revision) in store.rows.items()]}
    transport = ExportFixture()
    snapshot = export_snapshot(transport, nodes[0].manifest)
    assert snapshot['revision'] == store.revision and transport.calls == 1
    transport.truncated = True
    with pytest.raises(HAError, match='snapshot_capacity'):
        export_snapshot(transport, nodes[0].manifest)
