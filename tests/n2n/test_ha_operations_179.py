"""Quorum metadata transitions, independent of provider/runtime behavior."""
import copy
import secrets
import uuid

import pytest

from bgp.federation.ha.config import HAError
from bgp.federation.ha.operations import OperationLedger
from bgp.federation import protected_contract as c
from test_ha_authority_179 import cluster
from test_ha_execution_contract_179 import ha_approval


def prepared():
    store, nodes = cluster()
    authority = nodes[0]
    authority.campaign()
    border, member, payload = ha_approval()
    node = authority.manifest.node(authority.node_id)
    # This test uses the manifest's public key for the Border binding. Signing
    # is covered separately; approve validates the supplied signed envelope.
    payload['border'] = {'installation_id': node['installation_id'], 'identity': node['identity'],
                         'key_id': node['key_id'], 'authority_generation': authority.manifest.generation}
    payload['cluster'] = {**authority.manifest.audience, 'manifest_revision': authority.manifest.revision,
                          'issuer_node_id': authority.node_id, 'authority_epoch': authority.epoch}
    payload['principal']['subject'] = str(uuid.uuid5(uuid.UUID(authority.manifest.cluster_id), 'netclaw.open-lab.operator'))
    review = c.review_from_payload(payload)
    ledger = OperationLedger(authority, clock_ms=lambda: payload['issued_at_ms'])
    ledger.enroll_member(review['member'], member['cert_pem'])
    row = ledger.prepare('nonce-one', 'a'*64, review)
    return store, nodes, ledger, row, member


def dispatch_fixture(store, nodes, ledger, row):
    # Seed a previously verified approval only for admission state-machine
    # tests; this is not a wire/authentication or actual execution claim.
    value, revision = store.read('operations/' + row['operation_id'])
    value.update(state='approved', approval_digest='b'*64, approval_id=str(uuid.uuid4()))
    store.txn([('operations/' + row['operation_id'], 'revision', revision)],
              [('operations/' + row['operation_id'], value, None)])
    return ledger.dispatch(row['operation_id'])


def request(ledger, row, *, nonce=None):
    return {**ledger.authority.manifest.audience, 'operation_id': row['operation_id'],
            'attempt_id': row['attempt_id'], 'approval_digest': row['approval_digest'],
            'kind': 'model', 'ordinal': 1, 'request_digest': 'c'*64,
            'member_incarnation': str(uuid.uuid4()), 'nonce': nonce or secrets.token_hex(32)}


def test_nonce_is_cluster_wide_and_exact():
    store, nodes, ledger, row, member = prepared()
    assert ledger.prepare('nonce-one', 'a'*64, row['review']) == row
    with pytest.raises(HAError, match='client_nonce_conflict'):
        ledger.prepare('nonce-one', 'd'*64, row['review'])
    store.revoke_lease('123'); nodes[1].campaign()
    follower = OperationLedger(nodes[1], clock_ms=ledger.now)
    assert follower.lookup(client_nonce='nonce-one', principal=row['review']['principal']) == row


@pytest.mark.parametrize('field', ['installation_id', 'key_id'])
def test_member_cannot_enroll_using_border_identity(field):
    store, nodes, ledger, row, member = prepared()
    binding = dict(row['review']['member'])
    binding[field] = nodes[0].manifest.nodes[0][field]
    before = copy.deepcopy(store.rows)
    with pytest.raises(HAError, match='member_border_identity_collision'):
        ledger.enroll_member(binding, member['cert_pem'])
    assert store.rows == before


def test_dispatch_and_admission_never_repeat_after_leader_change():
    store, nodes, ledger, row, member = prepared()
    row = dispatch_fixture(store, nodes, ledger, row)
    req = request(ledger, row)
    claim, revision = ledger.admit(req, row['review']['member'])
    assert revision > nodes[0].epoch and claim['request'] == req
    store.revoke_lease('123'); nodes[1].campaign()
    successor = OperationLedger(nodes[1], clock_ms=ledger.now)
    assert successor.admission_status(req, row['review']['member'])[0] == claim
    with pytest.raises(HAError, match='dispatch_already_claimed'):
        successor.dispatch(row['operation_id'])
    with pytest.raises(HAError, match='admission_spent'):
        successor.admit(request(successor, row), row['review']['member'])


def test_unknown_reserves_member_across_new_ids_and_leaders():
    store, nodes, ledger, row, member = prepared()
    dispatch_fixture(store, nodes, ledger, row)
    second = ledger.prepare('nonce-two', 'a'*64, row['review'])
    with pytest.raises(HAError, match='resource_recovery_required'):
        dispatch_fixture(store, nodes, ledger, second)


@pytest.mark.parametrize('fault', ['revoked', 'no_quorum', 'wrong_member', 'wrong_generation', 'wrong_attempt'])
def test_admission_refusal_preserves_empty_claim(fault):
    store, nodes, ledger, row, member = prepared()
    row = dispatch_fixture(store, nodes, ledger, row)
    req, binding = request(ledger, row), copy.deepcopy(row['review']['member'])
    if fault == 'revoked': ledger.revoke(row['operation_id'])
    if fault == 'no_quorum': store.available = False
    if fault == 'wrong_member': binding['key_id'] = 'f'*64
    if fault == 'wrong_generation': req['generation'] = str(uuid.uuid4())
    if fault == 'wrong_attempt': req['attempt_id'] = str(uuid.uuid4())
    with pytest.raises(HAError):
        ledger.admit(req, binding)
    store.available = True
    assert not any(key.startswith('claims/') for key in store.rows)


def test_capacity_fails_without_purging_nonce_or_claims():
    store, nodes, ledger, row, member = prepared()
    control, revision = store.read('control')
    control['operation_count'] = nodes[0].manifest.limits['max_operations']
    store.txn([('control', 'revision', revision)], [('control', control, None)])
    with pytest.raises(HAError, match='state_capacity'):
        ledger.prepare('nonce-two', 'a'*64, row['review'])
    assert ledger.lookup(operation_id=row['operation_id']) == row


def device_operation():
    store, nodes, ledger, old, member = prepared()
    review = copy.deepcopy(old['review'])
    principal = {'issuer': 'device-key', 'subject': str(uuid.uuid4()),
                 'display_name': 'Enrolled mobile device', 'roles': ['device-operator']}
    review['principal'] = principal
    key = 'edge-principals/' + principal['subject']
    record = {'principal': principal, 'state': 'active'}
    with pytest.raises(HAError, match='device_authority_changed'):
        ledger.prepare('device-nonce', 'a'*64, review)
    store.txn([(key, 'revision', 0)], [(key, record, None)])
    row = ledger.prepare('device-nonce', 'a'*64, review)
    return store, nodes, ledger, row, key


@pytest.mark.parametrize('boundary', ['dispatch', 'admit', 'admit_race'])
def test_device_revocation_is_in_the_execution_transaction(boundary):
    store, nodes, ledger, row, key = device_operation()
    if boundary != 'dispatch': row = dispatch_fixture(store, nodes, ledger, row)
    def revoke():
        record, revision = store.read(key)
        record['state'] = 'revoked'
        original_txn([(key, 'revision', revision)], [(key, record, None)])
    original_txn = store.txn
    if boundary == 'admit_race':
        fired = []
        def racing_txn(comparisons, writes):
            if not fired and any(k.startswith('claims/') for k, _, _ in writes):
                fired.append(True); revoke()
            return original_txn(comparisons, writes)
        store.txn = racing_txn
    else: revoke()
    with pytest.raises(HAError, match='device_authority_changed'):
        if boundary == 'dispatch': dispatch_fixture(store, nodes, ledger, row)
        else: ledger.admit(request(ledger, row), row['review']['member'])
    assert not any(k.startswith('claims/') for k in store.rows)
    if boundary == 'dispatch':
        assert ledger.lookup(operation_id=row['operation_id'])['attempt_id'] is None


def test_restore_capacity_fence_blocks_new_device_and_owner_execution():
    store, nodes, ledger, row, _ = prepared()
    row = dispatch_fixture(store, nodes, ledger, row)
    control, revision = store.read('control')
    control['recovery'] = {'capacity_frozen': True}
    store.txn([('control', 'revision', revision)], [('control', control, None)])
    with pytest.raises(HAError, match='recovery_fenced'):
        ledger.admit(request(ledger, row), row['review']['member'])
    assert not any(k.startswith('claims/') for k in store.rows)


def test_pending_review_cannot_be_denied_by_a_different_authority():
    store, nodes, ledger, row, _ = prepared()
    store.revoke_lease('123'); nodes[1].campaign()
    successor = OperationLedger(nodes[1], clock_ms=ledger.now)
    with pytest.raises(HAError, match='stale_review'):
        successor.deny(row['operation_id'], revision=row['revision'], review_digest=row['review_digest'])
    assert successor.lookup(operation_id=row['operation_id'])['state'] == 'review_pending'
