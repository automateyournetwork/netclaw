import copy
import uuid

import pytest

from bgp.federation import certs, protected_contract as c
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.config import Manifest, HAError
from bgp.federation.ha.operations import OperationLedger, reservation_keys
from test_ha_operations_179 import prepared, dispatch_fixture


def result_case():
    store, nodes, ledger, row, member = prepared()
    row = dispatch_fixture(store, nodes, ledger, row)
    # Introduce a successor key before constructing the isolated state machine;
    # no runtime manifest or live authority is rewritten by this fixture.
    value = nodes[0].manifest.value
    certificate, private = certs.create_self_signed(value['nodes'][1]['identity'])
    value['nodes'][1].update(certificate=certificate, key_id=c.key_id(certificate))
    manifest = Manifest(value)
    control, revision = store.read('control')
    control['manifest_sha256'] = c.sha256(manifest.value)
    control['nodes'][value['nodes'][1]['node_id']]['key_id'] = c.key_id(certificate)
    store.txn([('control', 'revision', revision)], [('control', control, None)])
    store.revoke_lease('123')
    authority = Authority(store, manifest, value['nodes'][1]['node_id'])
    authority.campaign()
    successor = OperationLedger(authority, clock_ms=ledger.now)
    review = row['review']
    payload = {'receipt_id': str(uuid.uuid4()), 'operation_id': row['operation_id'],
        'approval_id': row['approval_id'], 'approval_sha256': row['approval_digest'], 'attempt_id': row['attempt_id'],
        **{k:review[k] for k in ('principal','border','member','model_profile','cluster')},
        'tool_call_sha256': c.sha256(review['tool_call']), 'started_at_ms': ledger.now(), 'finished_at_ms': ledger.now(),
        'outcome': 'succeeded', 'effect_status': 'finished', 'output': {'private_result': 'original value'},
        'output_sha256': c.sha256({'private_result': 'original value'}), 'tool_evidence_sha256': 'f'*64,
        'usage': {'available': True}, 'audit_refs': {'result': 'controlled-audit'}, 'error_code': None}
    envelope = c.sign(c.HA_RESULT, payload, member['key_pem'])
    return store, successor, row, envelope, private, certificate


def test_successor_commits_original_result_reference_and_own_ack_without_raw_output():
    store, ledger, row, envelope, private, certificate = result_case()
    accepted = ledger.accept_result(row['operation_id'], envelope, private_key=private, audit_ref='fixture-audit')
    assert accepted['state'] == 'completed'
    assert accepted['result_ref']['digest'] == c.digest(c.HA_RESULT, envelope['payload'])
    ack = c.verify(accepted['ack'], certificate, c.HA_ACK)
    assert ack['border'] == row['review']['border']
    assert ack['acceptance']['node_id'] == ledger.authority.node_id
    assert ack['acceptance']['border'] != ack['border']
    assert 'private_result' not in c.encode({key: value for key, (value, _) in store.rows.items()}).decode()
    for resource in reservation_keys(row['review']):
        assert store.read(resource)[0]['state'] == 'released'
    before = store.mutations
    assert ledger.accept_result(row['operation_id'], envelope, private_key=private, audit_ref='fixture-audit') == accepted
    assert store.mutations == before


def test_result_mismatch_cannot_release_original_reservation():
    store, ledger, row, envelope, private, certificate = result_case()
    changed = copy.deepcopy(envelope)
    changed['payload']['attempt_id'] = str(uuid.uuid4())
    with pytest.raises(c.ProtectedError):
        ledger.accept_result(row['operation_id'], changed, private_key=private, audit_ref='fixture-audit')
    assert ledger.lookup(operation_id=row['operation_id'])['result_ref'] is None
    for resource in reservation_keys(row['review']):
        assert store.read(resource)[0]['state'] == 'reserved'
