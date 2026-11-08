"""Explicit HA member adapter using the existing protected executor/result ledger."""
import asyncio

from .. import protected_contract as c
from ..certs import time_valid
from ..protected_docker import DockerExecutor
from ..protected_service import ProtectedOperations
from .config import check
from .internal import border_binding
from .signatures import verify


class ClusterMemberOperations(ProtectedOperations):
    def __init__(self, manager, *, manifest, identity, certificate, private_key,
                 attachments, journal, catalog_provider, executor, audit_writer,
                 clock_ms=None, current=None):
        check(manifest.anchor_key_id is not None, 'unverified_cluster_manifest', 403)
        check(isinstance(executor, DockerExecutor) and executor.ollama, 'ha_runtime_unqualified', 503)
        check(c.key_id(certificate) == identity['key_id'], 'member_key_mismatch', 403)
        self.manifest, self.attachments, self.journal = manifest, attachments, journal
        self.current = current
        def trust(binding, historical=False):
            if self.current: self.current()
            if binding == identity: return certificate
            matches = [n for n in manifest.nodes if border_binding(manifest, n['node_id']) == binding]
            check(len(matches) == 1, 'border_authority_changed', 403)
            return matches[0]['certificate']
        super().__init__(manager, role='member', identity=identity,
            signer=lambda schema, payload: c.sign(schema, payload, private_key), trust_resolver=trust,
            catalog_provider=catalog_provider, executor=executor, audit_writer=audit_writer, clock_ms=clock_ms)
        self.approval_schema, self.result_schema, self.ack_schema = c.HA_APPROVAL, c.HA_RESULT, c.HA_ACK

    def _channel(self, channel, binding):
        if self.current: self.current()
        check(channel is not None and getattr(channel, 'strict', False) and getattr(channel, 'trusted', False)
              and getattr(channel, 'attestation', None) == 'possession' and not getattr(channel, '_closed', True),
              'trusted_channel_required', 403)
        node_id = getattr(channel, 'cluster_node_id', None)
        check(self.attachments.channels.get(node_id) is channel, 'foreign_channel', 403)
        node = self.manifest.node(node_id)
        check(channel.protected_peer_binding == border_binding(self.manifest, node_id)
              and time_valid(node['certificate']), 'border_authority_changed', 403)
        # Historical issuer and currently serving node are intentionally distinct.
        self._trust(binding)

    def _execution_channel(self, channel):
        available = [ch for _, ch in sorted(self.attachments.channels.items())
                     if ch.trusted and not ch._closed]
        check(available, 'border_transport_unavailable', 503)
        return available[0]

    def _execution_attempt(self, row):
        value = row['trust_snapshot']['dispatch']['attempt_id']
        c.uuid_field(value)
        return value

    async def _authorize_native(self, channel, binding):
        # This is only the local single-use tool claim. It grants no permission
        # to invoke: DockerExecutor performs the fresh quorum admission inside
        # its exact native callback, after local catalog/audit/claim work.
        check(isinstance(self.executor, DockerExecutor) and self.executor.ollama, 'ha_runtime_unqualified', 503)
        return dict(binding, ha_admission_required=True)

    async def _run_guarded(self, row, payload, gate):
        context = {key: row[key] for key in ('operation_id', 'attempt_id', 'approval_digest')}
        async def admission(kind, ordinal, request_digest, invoke):
            if self.current: self.current()
            return await self.journal.run(context, kind, ordinal, request_digest,
                                          self.attachments.send_admission, invoke)
        return await self.executor.run(payload, gate, ha_admission=admission)

    async def submit(self, channel, params):
        c.exact(params, 'approval dispatch')
        envelope, dispatch = params['approval'], params['dispatch']
        check(isinstance(envelope, dict) and isinstance(envelope.get('payload'), dict), 'invalid_contract')
        claimed = envelope['payload'].get('border')
        self._channel(channel, claimed)
        payload = c.verify(envelope, self._trust(claimed), c.HA_APPROVAL)
        cluster = payload['cluster']
        check({k: cluster[k] for k in ('cluster_id', 'generation')} == self.manifest.audience
              and cluster['manifest_revision'] == self.manifest.revision
              and claimed == border_binding(self.manifest, cluster['issuer_node_id']), 'cluster_changed', 409)
        check(payload['member'] == self.identity, 'foreign_member', 403)
        check(isinstance(dispatch, dict) and isinstance(dispatch.get('payload'), dict), 'invalid_dispatch')
        node_id = dispatch['payload'].get('issuer_node_id')
        proof = verify(dispatch, self.manifest.node(node_id)['certificate'], 'dispatch')
        c.exact(proof, 'cluster_id generation operation_id attempt_id approval_digest issuer_node_id authority_epoch')
        c.uuid_field(proof['attempt_id'])
        approval_digest = c.digest(c.HA_APPROVAL, payload)
        check({k: proof[k] for k in ('cluster_id', 'generation')} == self.manifest.audience
              and proof['operation_id'] == payload['operation_id'] and proof['approval_digest'] == approval_digest
              and type(proof['authority_epoch']) is int and cluster['authority_epoch'] <= proof['authority_epoch'] <= 2**53-1,
              'dispatch_binding_mismatch', 403)
        old = self.store.get('member', payload['operation_id'])
        if old:
            check(old['approval_digest'] == approval_digest and old['trust_snapshot'].get('dispatch') == proof,
                  'operation_conflict', 409)
            return dict(self._member_dto(old), attempt_id=proof['attempt_id'])
        check(payload['issued_at_ms'] <= self.now() < payload['limits']['expires_at_ms'], 'approval_expired', 403)
        await self._check_catalog(payload)
        self._channel(channel, claimed)
        row = self.store.create('member', payload['operation_id'], owner_subject=payload['principal']['subject'],
            review=c.review_from_payload(payload), review_digest=payload['review_sha256'], state='admitted', approval=envelope,
            trust_snapshot={'border': self._trust(claimed), 'member': self._trust(self.identity), 'dispatch': proof})
        task = asyncio.create_task(self._execute(row['operation_id'], channel))
        self.workers.add(task); task.add_done_callback(self.workers.discard)
        return dict(self._member_dto(row), attempt_id=proof['attempt_id'])

    async def acknowledge(self, channel, params):
        c.exact(params, 'ack')
        envelope = params['ack']
        check(isinstance(envelope, dict) and isinstance(envelope.get('payload'), dict), 'invalid_ack')
        claimed = envelope['payload']
        check(isinstance(claimed.get('acceptance'), dict), 'invalid_ack')
        node_id = claimed['acceptance'].get('node_id')
        node = self.manifest.node(node_id)
        payload = c.verify(envelope, node['certificate'], c.HA_ACK)
        check(payload['acceptance']['border'] == border_binding(self.manifest, node_id), 'ack_issuer_mismatch', 403)
        row = self._member_lookup(channel, payload['operation_id'])
        check(row['receipt'] is not None, 'result_not_ready', 409)
        receipt = row['receipt']['payload']
        check(all(payload[k] == receipt[k] for k in ('operation_id', 'approval_id', 'attempt_id',
                    'receipt_id', 'border', 'member', 'cluster')) and payload['receipt_sha256'] == row['receipt_digest'],
              'ack_binding_mismatch', 409)
        if row['ack']:
            check(c.digest(c.HA_ACK, row['ack']['payload']) == c.digest(c.HA_ACK, payload), 'ack_conflict', 409)
        else:
            row = self.store.transition('member', row['operation_id'], 'result_ready', state='acknowledged', ack=envelope)
        return self._member_dto(row)
