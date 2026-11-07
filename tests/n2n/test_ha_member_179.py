import asyncio
import secrets
import uuid
from types import SimpleNamespace

import pytest

from bgp.federation import protected_contract as c
from bgp.federation.ha.admission import MemberAdmission
from bgp.federation.ha.member import ClusterMemberOperations
from bgp.federation.ha.operations import OperationLedger
from bgp.federation.ha.signatures import sign
from bgp.federation.ha.internal import border_binding
from bgp.federation.protected_docker import DockerExecutor
from ha_support_179 import cluster_with_keys
from test_ha_execution_contract_179 import ha_approval


@pytest.mark.asyncio
async def test_member_uses_quorum_attempt_and_all_three_admission_boundaries(tmp_path):
    store, manifest, nodes, keys = cluster_with_keys()
    _, member, payload = ha_approval()
    payload['cluster'] = {**manifest.audience, 'manifest_revision': manifest.revision,
                          'issuer_node_id': nodes[0].node_id, 'authority_epoch': nodes[0].epoch}
    payload['border'] = border_binding(manifest, nodes[0].node_id)
    payload['principal']['subject'] = str(uuid.uuid5(uuid.UUID(manifest.cluster_id), 'netclaw.open-lab.operator'))
    ledger = OperationLedger(nodes[0], clock_ms=lambda: payload['issued_at_ms'])
    ledger.enroll_member(payload['member'], member['cert_pem'])
    row = ledger.prepare('controlled-member', 'e'*64, c.review_from_payload(payload))
    payload.update(operation_id=row['operation_id'], review_sha256=row['review_digest'])
    envelope = c.sign(c.HA_APPROVAL, payload, keys[0])
    ledger.approve(row['operation_id'], envelope, revision=1, review_digest=row['review_digest'])
    row = ledger.dispatch(row['operation_id'])
    dispatch = sign('dispatch', {**manifest.audience, 'operation_id': row['operation_id'],
        'attempt_id': row['attempt_id'], 'approval_digest': row['approval_digest'],
        'issuer_node_id': nodes[0].node_id, 'authority_epoch': nodes[0].epoch}, keys[0])
    effects = []
    class ControlledDocker(DockerExecutor):
        def __init__(self): self.ollama = {'controlled': True}
        async def run(self, approved, gate, *, ha_admission=None):
            async def model(): effects.append('controlled-model'); return {}
            async def native(): effects.append('controlled-tool'); return {'fixture': True}
            await ha_admission('model', 1, 'a'*64, model)
            evidence = await gate(approved['tool_call'],
                lambda: ha_admission('tool', 1, c.sha256(approved['tool_call']), native))
            await ha_admission('model', 2, 'b'*64, model)
            return {'output': evidence, 'tool_evidence': evidence, 'usage': {},
                    'effective_model_profile': approved['model_profile']}
        def close(self): pass
    class Attachments:
        channels = {}
        async def send_admission(self, request):
            claim, revision = ledger.admit(request, payload['member'])
            return sign('admission', {'claim': claim, 'commit_revision': revision}, keys[0])
    attachments = Attachments()
    channel = SimpleNamespace(strict=True, trusted=True, attestation='possession', _closed=False,
        protected_peer_binding=payload['border'], cluster_node_id=nodes[0].node_id)
    attachments.channels = {nodes[0].node_id: channel}
    catalog = {'member': payload['member'], 'model_profiles': [payload['model_profile']],
               'tools': [dict(payload['tool_call'], limits={k:v for k,v in payload['limits'].items() if k != 'expires_at_ms'})]}
    journal = MemberAdmission(tmp_path/'journal', manifest, payload['member'])
    operations = ClusterMemberOperations(SimpleNamespace(db_path=tmp_path/'private/federation.db'),
        manifest=manifest, identity=payload['member'], certificate=member['cert_pem'], private_key=member['key_pem'],
        attachments=attachments, journal=journal, catalog_provider=lambda: catalog,
        executor=ControlledDocker(), audit_writer=lambda *args: 'controlled-audit', clock_ms=ledger.now)
    try:
        submitted = await operations.submit(channel, {'approval': envelope, 'dispatch': dispatch})
        assert submitted['attempt_id'] == row['attempt_id']
        await asyncio.gather(*operations.workers)
        receipt = await operations.member_result(channel, {'operation_id': row['operation_id']})
        assert c.verify(receipt, member['cert_pem'], c.HA_RESULT)['attempt_id'] == row['attempt_id']
        assert effects == ['controlled-model','controlled-tool','controlled-model']
        assert len([k for k in store.rows if k.startswith('claims/')]) == 3
        await operations.submit(channel, {'approval': envelope, 'dispatch': dispatch})
        assert len(effects) == 3
        legacy = dict(envelope, schema=c.APPROVAL)
        with pytest.raises(c.ProtectedError):
            await operations.submit(channel, {'approval': legacy, 'dispatch': dispatch})
    finally:
        await operations.close()
