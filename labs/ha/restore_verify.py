"""Verify an actually installed fenced generation without performing an effect.

Run in the reviewed maintenance window before new Border services campaign. This
uses production Authority/OperationLedger gates, not a replacement guard. Native
model/MCP counter verification remains the coordinator's separate REAL evidence.
"""
import copy
import time
import uuid

from bgp.federation import protected_contract as c
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.config import HAError, check
from bgp.federation.ha.operations import OperationLedger
from bgp.federation.ha.recovery import restore_records


def verify_restore(store, snapshot, old_manifest, new_manifest, node_id):
    expected = restore_records(snapshot, old_manifest, new_manifest)
    authority = Authority(store, new_manifest, node_id)
    rows = authority.snapshot(['recovery/install'])
    control, control_revision = rows['control']; install = rows['recovery/install'][0]
    check(isinstance(install, dict) and install.get('complete') is True, 'restore_incomplete')
    check(control.get('recovery', {}).get('capacity_frozen') is True, 'restore_capacity_not_frozen')
    checked, preserved = [], {}
    for offset in range(0, len(expected), 12):
        names = list(expected)[offset:offset+12]
        values = store.read_many(names)
        for name in names:
            actual = values[name][0]
            anticipated = copy.deepcopy(expected[name])
            if name == 'control':
                anticipated['active'] = control['active']
            check(actual == anticipated, 'restored_record_changed')
            preserved[name] = c.sha256(actual)
            checked.append(name)
    if control['active'] is False:
        try:
            authority.campaign()
            raise AssertionError('fenced_generation_campaigned')
        except HAError as exc:
            if exc.code != 'recovery_fenced': raise
        return {'class': 'FIXTURE', 'real_profile_qualified': False, 'active': False,
                'capacity_frozen': True, 'checked_records': len(checked),
                'records_sha256': c.sha256(preserved), 'control_revision': control_revision,
                'gate_results': [{'gate': 'campaign', 'code': 'recovery_fenced'}]}
    check(rows['leader'][0] is None, 'maintenance_authority_busy', 409)
    check(authority.campaign(), 'maintenance_authority_busy', 409)
    try:
        ledger = OperationLedger(authority)
        pending = [value for key, value in expected.items() if key.startswith('operations/')
                   and value.get('attempt_id') and value.get('approval_digest')]
        check(pending, 'restore_admission_evidence_required')
        original = pending[0]
        review = copy.deepcopy(original['review'])
        node = new_manifest.node(node_id)
        review['cluster'] = {**new_manifest.audience, 'manifest_revision': new_manifest.revision,
                             'issuer_node_id': node_id, 'authority_epoch': authority.epoch}
        review['border'] = {'installation_id': node['installation_id'], 'identity': node['identity'],
                           'key_id': node['key_id'], 'authority_generation': new_manifest.generation}
        results = []
        def refused(gate, callback):
            try:
                callback()
                raise AssertionError('restored_capacity_was_usable')
            except HAError as exc:
                if exc.code != 'recovery_fenced': raise
                results.append({'gate': gate, 'code': exc.code})
        refused('fresh-prepare', lambda: ledger.prepare('restore-probe-' + uuid.uuid4().hex, 'a'*64, review))
        for kind in ('model', 'tool'):
            request = {**new_manifest.audience, 'operation_id': original['operation_id'],
                'attempt_id': original['attempt_id'], 'approval_digest': original['approval_digest'],
                'kind': kind, 'ordinal': 1, 'request_digest': 'b'*64,
                'member_incarnation': str(uuid.uuid4()), 'nonce': uuid.uuid4().hex + uuid.uuid4().hex}
            refused(kind + '-admission', lambda request=request: ledger.admit(request, original['review']['member']))
        after, _ = store.read('control')
        check(after == control, 'restore_probe_mutated_control')
        return {'class': 'FIXTURE', 'real_profile_qualified': False, 'active': True,
                'capacity_frozen': True, 'checked_records': len(checked),
                'records_sha256': c.sha256(preserved), 'control_revision': control_revision,
                'gate_results': results, 'operation_id': original['operation_id']}
    finally:
        if authority.lease_id: store.revoke_lease(authority.lease_id)
