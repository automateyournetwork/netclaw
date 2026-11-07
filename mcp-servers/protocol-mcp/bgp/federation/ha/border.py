"""Owner review, single dispatch and original-result collection for an HA Border."""
import asyncio
from contextlib import contextmanager
import secrets
import time
import uuid

from .. import protected_contract as c
from ..protected_access import lab_principal
from ..protected_runtime import private_directory, private_write
from .config import check, HAError, read_private
from .internal import border_binding
from .node import FORWARDED
from .signatures import sign
from .edge import VerifiedClusterDevice


class ClusterBorderOperations:
    """Explicit open-lab cluster scope and signed enrolled-device requests.

    The bridge remains private. Routing cannot import cookies or turn a supplied
    principal into authenticated owner/device authority.
    """
    role, open_lab = 'border', True

    def __init__(self, node, *, state_dir, member_channels, audit_writer, current=None):
        self.node, self.manifest, self.ledger = node, node.manifest, node.ledger
        self.identity = border_binding(self.manifest, node.node_id)
        self.member_channels, self.audit_writer, self.current = member_channels, audit_writer, current
        self.state = private_directory(state_dir)
        self.results = private_directory(self.state / 'ha-results')
        self.observations = private_directory(self.state / 'ha-observations')
        self.principal = lab_principal(self.manifest.cluster_id)
        self.bridge, self.mobile_enrollment = None, None
        node.dispatch = self._local

    @contextmanager
    def _owner(self, context):
        if self.current: self.current()
        if isinstance(context, VerifiedClusterDevice):
            yield context.principal()
            return
        c.exact(context, 'access_mode installation_id cluster_id generation')
        check(context['access_mode'] == 'open-lab' and
              {key: context[key] for key in ('cluster_id', 'generation')} == self.manifest.audience
              and context['installation_id'] in {n['installation_id'] for n in self.manifest.nodes},
              'cluster_context_refused', 403)
        yield dict(self.principal, roles=list(self.principal['roles']))

    def _audit(self, event, row):
        record = {'principal': row['review']['principal'], 'operation_id': row['operation_id'],
                  'approval_id': row.get('approval_id'), 'approval_digest': row.get('approval_digest'),
                  'attempt_id': row.get('attempt_id'), 'member': row['review']['member'],
                  'cluster': self.manifest.audience}
        reference = self.audit_writer(event, record)
        check(isinstance(reference, str) and 0 < len(reference) <= 200, 'audit_unavailable', 503)
        return reference

    async def _route(self, action, params):
        check(isinstance(params, dict) and 'auth_context' in params, 'cluster_context_refused', 403)
        await self._authenticate(action, params, self.node.node_id)
        try:
            result = await self.node.route('n2n/cluster/forward', {'action': action, 'params': params})
            if isinstance(result, dict) and 'operation_id' in result:
                self._retain(result)
            return result
        except HAError as exc:
            if action != 'status' or exc.code not in ('no_quorum', 'authority_unavailable', 'leader_transport_unavailable'):
                raise
            return self._retained_status(params, exc.code)

    def _retain(self, dto):
        # A private immutable-at-observation DTO is useful during quorum loss.
        # It is never supplied to the ledger or used as execution authority.
        c.uuid_field(dto['operation_id'])
        cached = {'dto': dto, 'observed_at_ms': int(time.time()*1000)}
        private_write(self.observations / (dto['operation_id'] + '.json'), c.encode(cached))
        index = c.sha256({'principal': dto['review']['principal'], 'nonce': dto['client_nonce']})
        private_write(self.observations / ('nonce-' + index + '.json'), c.encode({'operation_id': dto['operation_id']}))

    def _retained_status(self, params, reason):
        c.exact(params, 'auth_context operation_id' if 'operation_id' in params else 'auth_context client_nonce')
        # This historical fallback is scoped to the explicit open-lab audience.
        # Devices continue to require current quorum revocation checks.
        with self._owner(params['auth_context']) as principal: pass
        check(principal['issuer'] == 'open-lab', 'device_authority_unavailable', 503)
        identifier = params.get('operation_id')
        if identifier is None:
            index = c.sha256({'principal': principal, 'nonce': params['client_nonce']})
            path = self.observations / ('nonce-' + index + '.json')
            check(path.exists(), 'no_retained_observation', 503)
            identifier = c.decode(read_private(path))['operation_id']
        c.uuid_field(identifier)
        path = self.observations / (identifier + '.json')
        check(path.exists(), 'no_retained_observation', 503)
        cached = c.decode(read_private(path, c.MAX_ENVELOPE + 65536))
        dto = cached['dto']
        check(dto['operation_id'] == identifier and dto['review']['principal'] == principal
              and {k:dto['review']['cluster'][k] for k in self.manifest.audience} == self.manifest.audience,
              'retained_observation_mismatch', 403)
        return dict(dto, allowed_actions=[], observation={'kind': 'retained',
            'observed_at_ms': cached['observed_at_ms'], 'reason': reason})

    async def _authenticate(self, action, params, ingress_node_id):
        context = params.get('auth_context')
        if isinstance(context, dict) and context.get('access_mode') == 'cluster-device-proof':
            c.exact(context, 'access_mode proof params')
            original = context['params']
            check(isinstance(original, dict) and original.get('installation_id') ==
                  self.manifest.node(ingress_node_id)['installation_id'], 'device_ingress_mismatch', 403)
            check({k:v for k,v in original.items() if k != 'installation_id'} ==
                  {k:v for k,v in params.items() if k != 'auth_context'}, 'device_proof_invalid', 403)
            registry = getattr(self, 'edge_registry', None)
            check(registry is not None, 'cluster_device_authority_unavailable', 503)
            return await asyncio.to_thread(registry.verify_request, context['proof'],
                'n2n/edge/operations/' + action, original)
        with self._owner(context): pass
        return context

    async def _local(self, action, params, *, ingress_node_id=None):
        check(action in FORWARDED, 'cluster_method_refused', 403)
        ingress_node_id = ingress_node_id or self.node.node_id
        context = await self._authenticate(action, params, ingress_node_id)
        result = await getattr(self, '_local_' + action)(dict(params, auth_context=context))
        await self._authenticate(action, params, ingress_node_id)
        return result

    async def catalog(self, params): return await self._route('catalog', params)
    async def prepare(self, params): return await self._route('prepare', params)
    async def decision(self, params): return await self._route('decision', params)
    async def status(self, params): return await self._route('status', params)
    async def reconcile(self, params): return await self._route('reconcile', params)
    async def revoke(self, params): return await self._route('revoke', params)

    async def _row(self, operation_id, context):
        with self._owner(context) as principal:
            row = await asyncio.to_thread(self.ledger.lookup, operation_id=operation_id, principal=principal)
        check(row is not None, 'operation_not_found', 404)
        return row

    def _result(self, row):
        reference = row['result_ref']
        if not reference: return None
        path = self.results / (row['operation_id'] + '.json')
        if not path.exists(): return None
        envelope = c.decode(read_private(path, c.MAX_ENVELOPE))
        payload = c.verify(envelope, row['trust_snapshot']['member'], c.HA_RESULT)
        check(c.digest(c.HA_RESULT, payload) == reference['digest'], 'receipt_conflict', 409)
        return {'verified': row['ack'] is not None, 'digest': reference['digest'],
                'durable_ack': row['ack'] is not None, 'ack_delivery_pending': not row.get('ack_delivered', False),
                'evidence': payload}

    def _dto(self, row):
        uncertain = row['state'] in ('dispatch_claimed', 'outcome_unknown')
        approval = row['approval']
        return {'operation_id': row['operation_id'], 'client_nonce': row['client_nonce'],
            'revision': row['revision'], 'state': row['state'], 'review_digest': row['review_digest'], 'review': row['review'],
            'approval': None if approval is None else {'approval_id': row['approval_id'], 'digest': row['approval_digest'],
                'expires_at_ms': row['review']['limits']['expires_at_ms']},
            'attempt_count': int(row['attempt_id'] is not None), 'reconciliation_required': uncertain,
            'may_have_executed': row['attempt_id'] is not None, 'result': self._result(row),
            'result_reference': row['result_ref'], 'error_code': row.get('error_code'),
            'allowed_actions': (['approve','deny'] if row['state'] == 'review_pending' and not row['revoked'] else ['reconcile'])
                               + ([] if row['revoked'] else ['revoke']),
            'authority': {'mode': 'cluster', **self.manifest.audience, 'served_by': self.node.node_id,
                          'epoch': self.node.authority.epoch, 'observation_only': True}}

    async def _send(self, member, method, params):
        channel = self.member_channels.get(member['member_id'])
        check(channel is not None and channel.strict and channel.trusted and not channel._closed
              and channel.protected_peer_binding == member, 'member_transport_unavailable', 503)
        await self.node.member_current(member)
        response = await channel.call(method, params, timeout=15)
        await self.node.member_current(member)
        return response

    async def _local_catalog(self, params):
        c.exact(params, 'auth_context')
        entries = []
        for channel in list(self.member_channels.values()):
            binding = getattr(channel, 'protected_peer_binding', None)
            if binding is None: continue
            try:
                entry = await self._send(binding, 'execution/catalog', {})
                c.validate_catalog_entry(entry)
                check(entry['member'] == binding, 'catalog_identity_mismatch', 403)
                entries.append(entry)
            except Exception:
                continue
        entries.sort(key=lambda e: e['member']['member_id'])
        check(len({e['member']['member_id'] for e in entries}) == len(entries), 'ambiguous_catalog', 409)
        return {'revision': c.sha256(entries), 'members': entries, 'capabilities': ['cluster_execution_v2'],
                'cluster': self.manifest.audience}

    async def _local_prepare(self, params):
        c.exact(params, 'auth_context client_nonce catalog_revision member_id model_profile_id tool arguments')
        candidate = {key: params[key] for key in ('catalog_revision','member_id','model_profile_id','tool','arguments')}
        with self._owner(params['auth_context']) as principal: pass
        old = await asyncio.to_thread(self.ledger.lookup, client_nonce=params['client_nonce'], principal=principal)
        if old:
            check(old['candidate_digest'] == c.sha256(candidate), 'client_nonce_conflict', 409)
            return self._dto(old)
        catalog = await self._local_catalog({'auth_context': params['auth_context']})
        check(catalog['revision'] == params['catalog_revision'], 'catalog_changed', 409)
        entry = next((e for e in catalog['members'] if e['member']['member_id'] == params['member_id']), None)
        check(entry is not None, 'member_not_available', 409)
        model = next((m for m in entry['model_profiles'] if m['profile_id'] == params['model_profile_id']), None)
        tool = next((t for t in entry['tools'] if t['tool'] == params['tool'] and t['arguments'] == params['arguments']), None)
        check(model is not None and tool is not None, 'selection_not_supported', 403)
        review = {'principal': principal, 'border': self.identity, 'member': entry['member'],
            'model_profile': model, 'tool_call': {k:v for k,v in tool.items() if k != 'limits'},
            'limits': dict(tool['limits'], expires_at_ms=int(time.time()*1000) + 180000), 'change_request_ref': None,
            'cluster': {**self.manifest.audience, 'manifest_revision': self.manifest.revision,
                        'issuer_node_id': self.node.node_id, 'authority_epoch': self.node.authority.epoch}}
        row = await asyncio.to_thread(self.ledger.prepare, params['client_nonce'], c.sha256(candidate), review)
        return self._dto(row)

    async def _local_decision(self, params):
        c.exact(params, 'auth_context operation_id revision review_digest decision')
        check(params['decision'] in ('approve','deny'), 'invalid_decision')
        row = await self._row(params['operation_id'], params['auth_context'])
        check(row['review_digest'] == params['review_digest'], 'review_changed', 409)
        if row['state'] != 'review_pending':
            check((params['decision'] == 'approve' and row['approval'] is not None) or
                  (params['decision'] == 'deny' and row.get('error_code') == 'owner_denied'), 'decision_conflict', 409)
            return self._dto(row)
        self._audit('protected_approval' if params['decision'] == 'approve' else 'protected_denial', row)
        if params['decision'] == 'deny':
            return self._dto(await asyncio.to_thread(self.ledger.deny, row['operation_id'],
                revision=params['revision'], review_digest=params['review_digest']))
        payload = dict(row['review'], approval_id=str(uuid.uuid4()), operation_id=row['operation_id'],
                       nonce=secrets.token_urlsafe(32), issued_at_ms=int(time.time()*1000), review_sha256=row['review_digest'])
        approval = c.sign(c.HA_APPROVAL, payload, self.node.private_key)
        row = await asyncio.to_thread(self.ledger.approve, row['operation_id'], approval,
                                      revision=params['revision'], review_digest=params['review_digest'])
        self._audit('protected_dispatch', row)
        row = await asyncio.to_thread(self.ledger.dispatch, row['operation_id'])
        dispatch = sign('dispatch', {**self.manifest.audience, 'operation_id': row['operation_id'],
            'attempt_id': row['attempt_id'], 'approval_digest': row['approval_digest'],
            'issuer_node_id': self.node.node_id, 'authority_epoch': row['dispatch_leader']['epoch']}, self.node.private_key)
        try:
            response = await self._send(row['review']['member'], 'execution/submit', {'approval': approval, 'dispatch': dispatch})
            check(response.get('operation_id') == row['operation_id'] and response.get('attempt_id') == row['attempt_id'],
                  'invalid_submit_response')
        except Exception:
            # Marking uncertainty is a separate state transition, never a repeat
            # of the submit/dispatch. If quorum is gone, retain dispatch_claimed.
            try: row = await asyncio.to_thread(self.ledger.mark_unknown, row['operation_id'])
            except Exception: pass
        return self._dto(row)

    async def _local_status(self, params):
        check(set(params) in ({'auth_context','operation_id'}, {'auth_context','client_nonce'}))
        with self._owner(params['auth_context']) as principal: pass
        row = await self._row(params['operation_id'], params['auth_context']) if 'operation_id' in params else (
            await asyncio.to_thread(self.ledger.lookup, client_nonce=params['client_nonce'], principal=principal))
        check(row is not None, 'operation_not_found', 404)
        return self._dto(row)

    async def _local_revoke(self, params):
        c.exact(params, 'auth_context operation_id')
        row = await self._row(params['operation_id'], params['auth_context'])
        self._audit('protected_revocation', row)
        return self._dto(await asyncio.to_thread(self.ledger.revoke, row['operation_id']))

    async def _local_reconcile(self, params):
        c.exact(params, 'auth_context operation_id')
        row = await self._row(params['operation_id'], params['auth_context'])
        if row['attempt_id'] is None: return self._dto(row)
        try:
            member = row['review']['member']
            status = await self._send(member, 'execution/status', {'operation_id': row['operation_id']})
            check(status.get('operation_id') == row['operation_id'], 'invalid_status_response')
            if status.get('receipt_ready'):
                receipt = await self._send(member, 'execution/result', {'operation_id': row['operation_id']})
                audit = self._audit('protected_result_accepted', row)
                row = await asyncio.to_thread(self.ledger.accept_result, row['operation_id'], receipt,
                                              private_key=self.node.private_key, audit_ref=audit)
                path = self.results / (row['operation_id'] + '.json')
                if not path.exists(): private_write(path, c.encode(receipt))
                self._result(row)  # Verify original immutable local artifact.
                response = await self._send(member, 'execution/ack', {'ack': row['ack']})
                check(response.get('state') == 'acknowledged' and response.get('operation_id') == row['operation_id'], 'ack_delivery_unknown')
                row = await asyncio.to_thread(self.ledger.acknowledge_delivery, row['operation_id'], row['result_ref']['digest'])
        except HAError as exc:
            if exc.code not in ('member_transport_unavailable', 'operation_not_found', 'ack_delivery_unknown'): raise
        except (ConnectionError, asyncio.TimeoutError):
            pass
        return self._dto(row)

    async def start(self):
        await self.node.start()
        if self.bridge: await self.bridge.start()

    async def close(self):
        if self.bridge: await self.bridge.close()
        await self.node.close()
