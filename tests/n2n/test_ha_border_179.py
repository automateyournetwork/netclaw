import uuid
from types import SimpleNamespace

import pytest

from bgp.federation import protected_contract as c
from bgp.federation.ha.border import ClusterBorderOperations
from bgp.federation.ha.node import ClusterNode
from bgp.federation.ha.config import HAError
from ha_support_179 import cluster_with_keys
from test_ha_execution_contract_179 import ha_approval


@pytest.mark.asyncio
async def test_exact_review_survives_lost_submit_without_second_dispatch(tmp_path):
    store, manifest, authorities, keys = cluster_with_keys()
    _, member, payload = ha_approval()
    catalog = {'member': payload['member'], 'model_profiles': [payload['model_profile']],
        'tools': [dict(payload['tool_call'], limits={k:v for k,v in payload['limits'].items() if k != 'expires_at_ms'})]}
    submissions = []
    class Channel:
        strict = trusted = True
        _closed = False
        protected_peer_binding = payload['member']
        async def call(self, method, params, timeout):
            if method == 'execution/catalog': return catalog
            if method == 'execution/submit':
                submissions.append(params)
                raise ConnectionError('controlled lost submit acknowledgement')
            return {'operation_id': params['operation_id'], 'receipt_ready': False, 'state': 'outcome_unknown'}
    node = ClusterNode(authorities[0], private_key=keys[0], ca_file='unused', cert_file='unused', key_file='unused')
    node.ledger.enroll_member(payload['member'], member['cert_pem'])
    operations = ClusterBorderOperations(node, state_dir=tmp_path/'private',
        member_channels={payload['member']['member_id']: Channel()}, audit_writer=lambda *args: 'controlled-audit')
    context = {'access_mode': 'open-lab', 'installation_id': operations.identity['installation_id'], **manifest.audience}
    cat = await operations.catalog({'auth_context': context})
    prepared = await operations.prepare({'auth_context': context, 'client_nonce': 'nonce-fixture',
        'catalog_revision': cat['revision'], 'member_id': payload['member']['member_id'],
        'model_profile_id': payload['model_profile']['profile_id'], 'tool': payload['tool_call']['tool'],
        'arguments': payload['tool_call']['arguments']})
    decision = {'auth_context': context, 'operation_id': prepared['operation_id'], 'revision': prepared['revision'],
                'review_digest': prepared['review_digest'], 'decision': 'approve'}
    unknown = await operations.decision(decision)
    assert unknown['state'] == 'outcome_unknown' and unknown['may_have_executed']
    assert len(submissions) == 1
    assert submissions[0]['approval']['schema'] == c.HA_APPROVAL
    assert submissions[0]['dispatch']['payload']['attempt_id']
    again = await operations.decision(decision)
    assert again['operation_id'] == unknown['operation_id'] and len(submissions) == 1
    await operations.reconcile({'auth_context': context, 'operation_id': unknown['operation_id']})
    assert len(submissions) == 1
    foreign = dict(context, cluster_id=str(uuid.uuid4()))
    with pytest.raises(HAError, match='cluster_context_refused'):
        await operations.status({'auth_context': foreign, 'operation_id': unknown['operation_id']})
