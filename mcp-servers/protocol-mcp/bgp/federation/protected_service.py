"""Opt-in owner-approved operations over trusted iN2N; no legacy fallback."""
import asyncio
import inspect
import os
from pathlib import Path
import secrets
import time
import uuid
from .protected_contract import (APPROVAL, RESULT, ACK, MAX_OUTPUT, ProtectedError, ProtectedOutcomeUnknown, canonical_bytes,
    decode, digest, encode, exact, ident, key_id, require, review_from_payload, sha256,
    sign, validate_binding, validate_model, validate_review, validate_tool, verify, uuid_field, digest_field,
    validate_catalog_entry)
from .protected_store import ProtectedStore
from .protected_access import OpenLabAccess, validate_access
from .protected_owner import OwnerAuthority, private_file, write_private


async def maybe_await(value):
    return await value if inspect.isawaitable(value) else value


class ProtectedOperations:
    def __init__(self, manager, *, role, identity, signer, trust_resolver,
                 catalog_provider, owner=None, executor=None, audit_writer=None,
                 clock_ms=None, transport=None, channel_validator=None):
        require(role in ('border', 'member'), 'unsupported_role')
        validate_binding(identity, role)
        self.manager, self.role, self.identity = manager, role, identity
        self.signer, self.trust_resolver = signer, trust_resolver
        self.catalog_provider, self.owner, self.executor = catalog_provider, owner, executor
        self.now = clock_ms or (lambda: int(time.time() * 1000))
        self.transport, self.channel_validator = transport, channel_validator
        self.store = ProtectedStore(manager.db_path)
        self.audit_writer = audit_writer or self._audit_default
        self.workers = set()
        self.failure_recovery_lock = asyncio.Lock()
        self.bridge = None
        from .protected_calculator import CombinedCoordinator
        self.combined = CombinedCoordinator(self)

    def _audit_default(self, event, record):
        from .gait import emit_protected
        return emit_protected(event, record=record, gait_dir=Path(self.manager.base_dir) / 'gait')

    def _audit(self, event, row, **extra):
        review = row['review']
        record = {'principal': review['principal'], 'operation_id': row['operation_id'],
                  'approval_id': row.get('approval_id'), 'approval_digest': row.get('approval_digest'),
                  'attempt_id': row.get('attempt_id'), 'member': review['member'], **extra}
        result = self.audit_writer(event, record)
        require(isinstance(result, str) and 0 < len(result) <= 200, 'audit_unavailable', 503)
        return result

    def _owner(self, context):
        require(self.role == 'border' and self.owner is not None, 'owner_unavailable', 503)
        from .protected_device import DeviceAuthority
        if isinstance(context, DeviceAuthority):
            return context.authorize(self)
        return self.owner.authorize(context)

    @property
    def open_lab(self):
        return isinstance(self.owner, OpenLabAccess)

    def _owned(self, operation_id, principal, *, historical=False):
        row = self.store.get('border', operation_id)
        current = row is not None and (row['review']['principal'] == principal if self.open_lab
                                       else row['owner_subject'] == principal['subject'])
        require(row is not None and (current or
                historical and self.open_lab and principal['issuer'] != 'device-key'
                and row['review']['border'] == self.identity),
                'operation_not_found', 404)
        return row

    def _by_nonce(self, nonce, principal):
        if not self.open_lab or principal['issuer'] == 'device-key':
            return self.store.get('border', client_nonce=nonce, owner_subject=principal['subject'])
        # A nonce retained before the explicit lab cutover must not create a
        # second authority under the new audit principal. Ambiguity is refused.
        with self.store.connection() as conn:
            rows = conn.execute('SELECT * FROM protected_operation WHERE side=? AND client_nonce=?',
                                ('border', nonce)).fetchall()
        rows = [self.store.unpack(row) for row in rows]
        require(len(rows) <= 1, 'client_nonce_conflict', 409)
        if rows:
            return self._owned(rows[0]['operation_id'], principal, historical=True)
        return None

    def _view(self, row, principal):
        value = self._dto(row)
        if self.open_lab and row['review']['principal'] != principal:
            value['allowed_actions'] = ['reconcile']
        return value

    def _trust(self, binding):
        cert = self.trust_resolver(binding, historical=False)
        require(isinstance(cert, str) and key_id(cert) == binding['key_id'], 'authority_changed', 403)
        return cert

    def _channel(self, channel, binding):
        require(channel is not None and getattr(channel, 'strict', False) and getattr(channel, 'trusted', False), 'trusted_channel_required', 403)
        require(getattr(channel, 'attestation', None) == 'possession', 'possession_required', 403)
        current = getattr(channel, 'authority_current', None)
        if current is not None:
            require(current(), 'authority_revoked', 403)
        if self.channel_validator:
            require(self.channel_validator(channel, binding), 'foreign_channel', 403)
        else:
            require(getattr(channel, 'protected_peer_binding', None) == binding, 'foreign_channel', 403)
        self._trust(binding)

    async def _send(self, member_id, method, params):
        require(self.transport is not None, 'transport_unavailable', 503)
        return await self.transport(member_id, method, params)

    def _dto(self, row):
        receipt, ack = row.get('receipt'), row.get('ack')
        uncertain = row['state'] in ('reconciliation_required', 'outcome_unknown', 'audit_pending')
        approval = row.get('approval')
        return {'operation_id': row['operation_id'], 'client_nonce': row['client_nonce'],
                'revision': row['revision'], 'state': row['state'], 'review_digest': row['review_digest'],
                'review': row['review'], 'approval': None if not approval else {
                    'approval_id': row['approval_id'], 'digest': row['approval_digest'],
                    'expires_at_ms': approval['payload']['limits']['expires_at_ms']},
                'attempt_count': int(row['attempt_id'] is not None), 'reconciliation_required': uncertain,
                'may_have_executed': bool(row['attempt_id'] or row['effect_authorization'] or row['state'] in ('dispatch_pending', 'member_admitted', 'reconciliation_required')),
                'result': None if not receipt else {'verified': ack is not None, 'digest': row['receipt_digest'],
                    'durable_ack': ack is not None, 'ack_delivery_pending': bool(row['ack_pending']), 'evidence': receipt['payload']},
                'error_code': row['error_code'], 'allowed_actions':
                    (['approve', 'deny'] if row['state'] == 'review_pending' else ['reconcile']) + ([] if row['revoked'] else ['revoke'])}

    async def catalog(self, params):
        exact(params, 'auth_context')
        with self._owner(params['auth_context']): pass
        members = await maybe_await(self.catalog_provider())
        members = members if isinstance(members, list) else [members]
        for entry in members:
            validate_catalog_entry(entry)
            self._trust(entry['member'])
        require(len({entry['member']['member_id'] for entry in members}) == len(members), 'ambiguous_catalog')
        members.sort(key=lambda entry: entry['member']['member_id'])
        result = {'revision': sha256(members), 'members': members, 'capabilities': ['calculator_combined_v1']}
        with self._owner(params['auth_context']): return result

    async def combined_prepare(self, params):
        return await self.combined.prepare(params)

    async def combined_status(self, params):
        return await self.combined.status(params)

    async def combined_cancel(self, params):
        return await self.combined.cancel(params)

    async def prepare(self, params):
        exact(params, 'auth_context client_nonce catalog_revision member_id model_profile_id tool arguments')
        ident(params['client_nonce'])
        with self._owner(params['auth_context']) as principal:
            old = self._by_nonce(params['client_nonce'], principal)
        candidate = {key: params[key] for key in ('catalog_revision', 'member_id', 'model_profile_id', 'tool', 'arguments')}
        candidate_digest = sha256(candidate)
        if old:
            require(old['candidate_digest'] == candidate_digest, 'client_nonce_conflict', 409)
            return await self.status({'auth_context': params['auth_context'], 'operation_id': old['operation_id']})
        catalog = await self.catalog({'auth_context': params['auth_context']})
        require(params['catalog_revision'] == catalog['revision'], 'catalog_changed', 409)
        member = next((entry for entry in catalog['members'] if entry['member']['member_id'] == params['member_id']), None)
        require(member is not None, 'member_not_available', 409)
        model = next((item for item in member['model_profiles'] if item['profile_id'] == params['model_profile_id']), None)
        tool = next((item for item in member['tools'] if item['tool'] == params['tool'] and item['arguments'] == params['arguments']), None)
        require(model is not None and tool is not None, 'selection_not_supported', 403)
        limits = dict(tool['limits'], expires_at_ms=self.now() + 300000)
        tool_call = {key: value for key, value in tool.items() if key != 'limits'}
        with self._owner(params['auth_context']) as principal:
            review = {'principal': principal, 'border': self.identity, 'member': member['member'],
                      'model_profile': model, 'tool_call': tool_call, 'limits': limits, 'change_request_ref': None}
            validate_review(review)
            # Immutable snapshots are trusted locally, never from submitted certificates.
            snapshot = {'border': self._trust(self.identity), 'member': self._trust(member['member'])}
            old = self._by_nonce(params['client_nonce'], principal)
            if old:
                require(old['candidate_digest'] == candidate_digest, 'client_nonce_conflict', 409)
                return self._view(old, principal)
            row = self.store.create('border', str(uuid.uuid4()), owner_subject=principal['subject'], review=review,
                                    review_digest=sha256(review), trust_snapshot=snapshot,
                                    client_nonce=params['client_nonce'], candidate_digest=candidate_digest)
            return self._dto(row)

    async def decision(self, params):
        exact(params, 'auth_context operation_id revision review_digest decision')
        require(params['decision'] in ('approve', 'deny'))
        with self._owner(params['auth_context']) as principal:
            row = self._owned(params['operation_id'], principal)
            require(row['review_digest'] == params['review_digest'], 'review_changed', 409)
            if row['state'] != 'review_pending':
                require((params['decision'] == 'deny' and row['state'] == 'refused') or (params['decision'] == 'approve' and row['approval'] is not None), 'decision_conflict', 409)
                return self._dto(row)
            require(type(params['revision']) is int and row['revision'] == params['revision'], 'revision_conflict', 409)
        if params['decision'] == 'approve':
            require(self.now() < row['review']['limits']['expires_at_ms'], 'approval_expired', 403)
        if params['decision'] == 'approve' and self.store.combined_for_child(row['operation_id']):
            current = await self.catalog({'auth_context': params['auth_context']})
            member = next((m for m in current['members'] if m['member'] == row['review']['member']), None)
            expected = dict(row['review']['tool_call'], limits={k:v for k,v in row['review']['limits'].items() if k != 'expires_at_ms'})
            require(member is not None and row['review']['model_profile'] in member['model_profiles']
                    and expected in member['tools'], 'profile_changed', 403)
        draft = None
        audit_row = row
        if params['decision'] == 'approve':
            draft = dict(row['review'], approval_id=str(uuid.uuid4()), operation_id=row['operation_id'],
                         nonce=secrets.token_urlsafe(32), issued_at_ms=self.now(), review_sha256=row['review_digest'])
            audit_row = dict(row, approval_id=draft['approval_id'], approval_digest=digest(APPROVAL, draft))
        audit_ref = self._audit('protected_approval' if draft else 'protected_denial', audit_row)
        with self._owner(params['auth_context']) as principal:
            row = self._owned(params['operation_id'], principal)
            if row['state'] != 'review_pending':
                require((params['decision'] == 'approve' and row['approval'] is not None) or (params['decision'] == 'deny' and row['state'] == 'refused'), 'decision_conflict', 409)
                return self._dto(row)
            require(row['revision'] == params['revision'] and not row['revoked'], 'state_conflict', 409)
            if params['decision'] == 'deny':
                row = self.store.transition('border', row['operation_id'], 'review_pending', state='refused', error_code='owner_denied', audit_refs={'approval': audit_ref})
                return self._dto(row)
            require(self.now() < row['review']['limits']['expires_at_ms'], 'approval_expired', 403)
            self._trust(row['review']['member']); self._trust(self.identity)
            payload = draft
            require(payload['issued_at_ms'] <= self.now(), 'clock_rollback', 403)
            approval = self.signer(APPROVAL, payload)
            verify(approval, row['trust_snapshot']['border'], APPROVAL)
            row = self.store.transition('border', row['operation_id'], 'review_pending', state='approved',
                                       approval=approval, approval_digest=digest(APPROVAL, payload), approval_nonce=payload['nonce'],
                                       approval_id=payload['approval_id'], audit_refs={'approval': audit_ref})
        dispatch_ref = self._audit('protected_dispatch', row)
        with self._owner(params['auth_context']) as principal:
            row = self._owned(params['operation_id'], principal)
            require(not row['revoked'] and self.now() < row['review']['limits']['expires_at_ms'], 'operation_revoked', 403)
            self._trust(row['review']['member'])
            row = self.store.transition('border', row['operation_id'], 'approved', state='dispatch_pending', audit_refs=dict(row['audit_refs'], dispatch=dispatch_ref))
        try:
            response = await self._send(row['review']['member']['member_id'], 'execution/submit', {'approval': row['approval']})
            require(isinstance(response, dict) and response.get('operation_id') == row['operation_id'], 'invalid_submit_response')
            current = self.store.get('border', row['operation_id'])
            row = self.store.transition('border', row['operation_id'], current['state'], state='member_admitted', attempt_id=response.get('attempt_id'))
        except Exception:
            current = self.store.get('border', row['operation_id'])
            if current['state'] == 'dispatch_pending':
                row = self.store.transition('border', row['operation_id'], 'dispatch_pending', state='reconciliation_required', error_code='submit_outcome_unknown')
        # Never return private data to a session revoked while the submit was in flight.
        with self._owner(params['auth_context']) as principal:
            return self._dto(self._owned(row['operation_id'], principal))

    async def status(self, params):
        require(set(params) in ({'auth_context', 'operation_id'}, {'auth_context', 'client_nonce'}))
        with self._owner(params['auth_context']) as principal:
            if 'operation_id' in params:
                row = self._owned(params['operation_id'], principal, historical=True)
            else:
                row = self._by_nonce(params['client_nonce'], principal)
                require(row is not None, 'operation_not_found', 404)
            return self._view(row, principal)

    async def revoke(self, params):
        exact(params, 'auth_context operation_id')
        with self._owner(params['auth_context']) as principal:
            row = self._owned(params['operation_id'], principal)
        self._audit('protected_revocation', row)
        with self._owner(params['auth_context']) as principal:
            self._owned(params['operation_id'], principal)
            return self._dto(self.store.revoke('border', params['operation_id']))

    async def reconcile(self, params):
        exact(params, 'auth_context operation_id')
        with self._owner(params['auth_context']) as principal:
            row = self._owned(params['operation_id'], principal, historical=True)
        if row['approval'] is not None:
            try:
                member = row['review']['member']['member_id']
                response = await self._send(member, 'execution/status', {'operation_id': row['operation_id']})
                require(response.get('operation_id') == row['operation_id'], 'invalid_status_response')
                if response.get('receipt_ready') and row['ack'] is None:
                    receipt = await self._send(member, 'execution/result', {'operation_id': row['operation_id']})
                    row = self._accept_result(row, receipt)
                elif response.get('state') == 'outcome_unknown' and row['ack'] is None:
                    row = self.store.transition('border', row['operation_id'], row['state'], state='reconciliation_required', error_code='member_outcome_unknown', attempt_id=response.get('attempt_id'))
                if row['ack'] is not None:
                    await self._send(member, 'execution/ack', {'ack': row['ack']})
                    row = self.store.transition('border', row['operation_id'], row['state'], ack_pending=0)
            except ProtectedError as exc:
                if exc.code not in ('transport_unavailable', 'operation_not_found'):
                    raise
            except Exception:
                pass  # A failed read or ACK delivery creates no new execution authority.
        with self._owner(params['auth_context']) as principal:
            return self._view(self._owned(row['operation_id'], principal, historical=True), principal)

    def _accept_result(self, row, envelope):
        p = verify(envelope, row['trust_snapshot']['member'], RESULT)
        a = row['approval']['payload']
        require(all(p[k] == a[k] for k in ('operation_id', 'approval_id', 'principal', 'border', 'member', 'model_profile')), 'result_binding_mismatch', 409)
        require(p['approval_sha256'] == row['approval_digest'] and p['tool_call_sha256'] == sha256(a['tool_call']), 'result_binding_mismatch', 409)
        require(row['attempt_id'] in (None, p['attempt_id']), 'attempt_conflict', 409)
        require(len(encode(p['output'])) <= a['limits']['max_output_bytes'], 'output_too_large')
        rd = digest(RESULT, p)
        if row['receipt_digest'] is not None:
            require(row['receipt_digest'] == rd, 'receipt_conflict', 409)
            return row
        audit_ref = self._audit('protected_result_accepted', row, receipt_digest=rd, attempt_id=p['attempt_id'],
                                outcome=p['outcome'], effect_status=p['effect_status'], error_code=p['error_code'])
        ack_payload = {'ack_id': str(uuid.uuid4()), 'operation_id': p['operation_id'], 'approval_id': p['approval_id'],
                       'attempt_id': p['attempt_id'], 'receipt_id': p['receipt_id'], 'receipt_sha256': rd,
                       'border': p['border'], 'member': p['member'], 'accepted_at_ms': self.now(), 'audit_ref': audit_ref}
        ack = self.signer(ACK, ack_payload)
        verify(ack, row['trust_snapshot']['border'], ACK)
        state = {'succeeded': 'completed', 'failed': 'failed', 'refused': 'refused'}[p['outcome']]
        # Receipt and its ACK are one FULL synchronous transaction before completion.
        try:
            return self.store.transition('border', row['operation_id'], row['state'], state=state, receipt=envelope,
                                         receipt_digest=rd, ack=ack, ack_pending=1, attempt_id=p['attempt_id'], error_code=p['error_code'],
                                         audit_refs=dict(row['audit_refs'], accepted=audit_ref))
        except ProtectedError as exc:
            current = self.store.get('border', row['operation_id'])
            if exc.code not in ('state_conflict', 'immutable_evidence') or current['receipt_digest'] != rd or current['ack'] is None:
                raise
            return current

    async def member_catalog(self, channel, params):
        exact(params, '')
        require(self.role == 'member', 'wrong_role')
        binding = getattr(channel, 'protected_peer_binding', None)
        self._channel(channel, binding)
        result = await maybe_await(self.catalog_provider())
        validate_catalog_entry(result)
        require(result['member'] == self.identity, 'catalog_identity_mismatch')
        return result

    async def submit(self, channel, params):
        exact(params, 'approval')
        require(self.role == 'member', 'wrong_role')
        envelope = params['approval']
        require(isinstance(envelope, dict) and isinstance(envelope.get('payload'), dict))
        claimed = envelope['payload'].get('border')
        self._channel(channel, claimed)
        cert = self._trust(claimed)
        payload = verify(envelope, cert, APPROVAL)
        try:
            return await self._admit_payload(channel, envelope, payload, cert)
        except ProtectedError as exc:
            # Only a cryptographically verified payload can supply an audit principal.
            refused = {'operation_id': payload['operation_id'], 'review': review_from_payload(payload),
                       'approval_id': payload['approval_id'], 'approval_digest': digest(APPROVAL, payload)}
            self._audit('protected_admission_refused', refused, outcome='refused',
                        effect_status='not_started', error_code=exc.code)
            raise

    async def _admit_payload(self, channel, envelope, payload, cert):
        require(payload['member'] == self.identity, 'foreign_member', 403)
        approval_digest = digest(APPROVAL, payload)
        old = self.store.get('member', payload['operation_id'])
        if old:
            require(old['approval_digest'] == approval_digest, 'operation_conflict', 409)
            return self._member_dto(old)
        require(payload['issued_at_ms'] <= self.now() < payload['limits']['expires_at_ms'], 'approval_expired', 403)
        await self._check_catalog(payload)
        require(self.executor is not None, 'protected_runtime_unavailable', 503)
        review = review_from_payload(payload)
        try:
            row = self.store.create('member', payload['operation_id'], owner_subject=payload['principal']['subject'],
                                    review=review, review_digest=payload['review_sha256'], state='admitted', approval=envelope,
                                    trust_snapshot={'border': cert, 'member': self._trust(self.identity)})
        except ProtectedError as exc:
            old = self.store.get('member', payload['operation_id'])
            if exc.code != 'operation_conflict' or not old or old['approval_digest'] != approval_digest:
                raise
            return self._member_dto(old)
        task = asyncio.create_task(self._execute(row['operation_id'], channel))
        self.workers.add(task)
        task.add_done_callback(self.workers.discard)
        return self._member_dto(row)

    async def _check_catalog(self, payload):
        catalog = await maybe_await(self.catalog_provider())
        validate_catalog_entry(catalog)
        require(catalog['member'] == payload['member'] and payload['model_profile'] in catalog['model_profiles'], 'profile_changed', 403)
        expected = payload['tool_call']
        entry = next((item for item in catalog['tools'] if {key: value for key, value in item.items() if key != 'limits'} == expected), None)
        require(entry is not None, 'tool_profile_changed', 403)
        require(all(payload['limits'][key] == value for key, value in entry['limits'].items() if key != 'expires_at_ms'), 'limits_changed', 403)

    def _member_dto(self, row):
        return {'operation_id': row['operation_id'], 'state': row['state'], 'attempt_id': row['attempt_id'],
                'receipt_ready': row['receipt'] is not None, 'receipt_digest': row['receipt_digest'],
                'effect_claimed': bool(row['effect_claimed']), 'error_code': row['error_code']}

    def _member_lookup(self, channel, operation_id):
        row = self.store.get('member', operation_id)
        require(row is not None, 'operation_not_found', 404)
        self._channel(channel, row['review']['border'])
        return row

    async def member_status(self, channel, params):
        exact(params, 'operation_id')
        row = self._member_lookup(channel, params['operation_id'])
        if row['state'] == 'outcome_unknown' and not row['effect_finished'] and hasattr(self, 'config'):
            async with self.failure_recovery_lock:
                row = self._member_lookup(channel, params['operation_id'])
                if row['state'] == 'outcome_unknown' and not row['effect_finished'] and not any(not task.done() for task in self.workers):
                    from .protected_failure_recovery import verify_known_netbox_failure
                    try:
                        verified = await verify_known_netbox_failure(row, self.config)
                    except (ProtectedError, OSError, ValueError, KeyError, TypeError, asyncio.TimeoutError):
                        # An incomplete, conflicting or unsafe proof is still
                        # unknown. Never synthesize a refusal from missing data.
                        verified = None
                    if verified is not None:
                        self._channel(channel, row['review']['border'])
                        recovery_ref = self._audit('protected_failure_recovery', row,
                            failure_proof_digest=sha256(verified.proof), original_state=row['state'],
                            original_error_code=row['error_code'], outcome='failed', effect_status='finished',
                            http_status=verified.proof['http_status'])
                        row = self.store.complete_known_netbox_failure(verified, recovery_ref)
        if row['state'] == 'outcome_unknown' and row['effect_finished'] and row['executor_result'] is None:
            terminal = {'output': {'tool_evidence': row['tool_evidence']}, 'tool_evidence': row['tool_evidence'],
                        'usage': {'available': False}, 'effective_model_profile': row['review']['model_profile'],
                        'outcome': 'failed', 'effect_status': 'finished', 'error_code': 'interrupted_after_effect'}
            row = self.store.transition('member', row['operation_id'], 'outcome_unknown', state='audit_pending', executor_result=terminal)
        if row['state'] == 'audit_pending' and row['executor_result'] is not None:
            await self._finish(row, row['executor_result'])
            row = self.store.get('member', row['operation_id'])
        return self._member_dto(row)

    async def member_result(self, channel, params):
        exact(params, 'operation_id')
        row = self._member_lookup(channel, params['operation_id'])
        require(row['receipt'] is not None, 'result_not_ready', 409)
        return row['receipt']

    async def acknowledge(self, channel, params):
        exact(params, 'ack')
        envelope = params['ack']
        require(isinstance(envelope, dict) and isinstance(envelope.get('payload'), dict))
        row = self._member_lookup(channel, envelope['payload'].get('operation_id'))
        p = verify(envelope, row['trust_snapshot']['border'], ACK)
        require(row['receipt'] is not None, 'result_not_ready', 409)
        receipt = row['receipt']['payload']
        require(all(p[k] == receipt[k] for k in ('operation_id', 'approval_id', 'attempt_id', 'receipt_id', 'border', 'member')) and p['receipt_sha256'] == row['receipt_digest'], 'ack_binding_mismatch', 409)
        if row['ack']:
            require(digest(ACK, row['ack']['payload']) == digest(ACK, p), 'ack_conflict', 409)
        else:
            row = self.store.transition('member', row['operation_id'], 'result_ready', state='acknowledged', ack=envelope)
        return self._member_dto(row)

    async def effect_authorize(self, channel, params):
        exact(params, 'operation_id approval_digest attempt_id tool_call_digest')
        uuid_field(params['operation_id']); uuid_field(params['attempt_id'])
        digest_field(params['approval_digest']); digest_field(params['tool_call_digest'])
        require(self.role == 'border', 'wrong_role')
        row = self.store.get('border', params['operation_id'])
        require(row is not None, 'operation_not_found', 404)
        self._channel(channel, row['review']['member'])
        require(row['approval_digest'] == params['approval_digest'] and sha256(row['review']['tool_call']) == params['tool_call_digest'], 'effect_binding_mismatch', 409)
        require(row['attempt_id'] in (None, params['attempt_id']), 'attempt_conflict', 409)
        require(row['approval']['payload']['issued_at_ms'] <= self.now() < row['review']['limits']['expires_at_ms'], 'approval_expired', 403)
        # Revocation and authorization compete in the same SQLite transaction.
        authorization = self.store.authorize_effect(row['operation_id'], dict(params))
        return dict(authorization, authorized=True)

    async def _execute(self, operation_id, channel):
        row = self.store.get('member', operation_id)
        try:
            attempt_id = str(uuid.uuid4())
            dispatch = self._audit('protected_executor', dict(row, attempt_id=attempt_id))
            row = self.store.claim_executor(operation_id, self.now(), attempt_id=attempt_id)
            row = self.store.transition('member', operation_id, 'executor_claimed', audit_refs={'approval': row['approval_digest'], 'dispatch': dispatch})
            payload = row['approval']['payload']
            retained = {'called': False, 'finished': False, 'evidence': None}
            async def gate(proposed_tool_call, invoke_exact_effect):
                require(callable(invoke_exact_effect), 'invalid_effect_callback')
                require(proposed_tool_call == payload['tool_call'], 'tool_call_changed', 403)
                require(not retained['called'], 'effect_already_claimed', 409)
                retained['called'] = True
                self._channel(channel, payload['border'])
                await self._check_catalog(payload)
                require(payload['issued_at_ms'] <= self.now() < payload['limits']['expires_at_ms'], 'approval_expired', 403)
                binding = {'operation_id': operation_id, 'approval_digest': row['approval_digest'],
                           'attempt_id': row['attempt_id'], 'tool_call_digest': sha256(payload['tool_call'])}
                authorization = await channel.call('execution/effect-authorize', binding)
                require(authorization == dict(binding, authorized=True), 'effect_not_authorized', 403)
                self._channel(channel, payload['border'])
                require(self.now() < payload['limits']['expires_at_ms'], 'approval_expired', 403)
                effect_ref = self._audit('protected_effect', row)
                self.store.claim_effect(operation_id, authorization)
                self.store.transition('member', operation_id, 'effect_claimed', audit_refs=dict(row['audit_refs'], effect=effect_ref))
                # No asynchronous boundary between durable claim and invocation.
                evidence = await invoke_exact_effect()
                encode(evidence)  # Reject unrepresentable evidence; retain the spent fence.
                retained.update(finished=True, evidence=evidence)
                self.store.transition('member', operation_id, 'effect_claimed', tool_evidence=evidence, effect_finished=1)
                return evidence
            try:
                result = await self.executor.run(payload, gate)
                require(isinstance(result, dict) and set(result) == {'output', 'tool_evidence', 'usage', 'effective_model_profile'}, 'invalid_executor_result')
                require(result['effective_model_profile'] == payload['model_profile'], 'effective_profile_mismatch')
                require(result['tool_evidence'] == retained['evidence'], 'tool_evidence_mismatch')
                require(retained['finished'], 'no_tool_effect')
                terminal = dict(result, outcome='succeeded', effect_status='finished', error_code=None)
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)): raise
                current = self.store.get('member', operation_id)
                if not retained['finished'] and (current['effect_claimed'] or isinstance(exc, ProtectedOutcomeUnknown) or not isinstance(exc, ProtectedError)):
                    self.store.transition('member', operation_id, current['state'], state='outcome_unknown', error_code='effect_outcome_unknown')
                    return
                terminal = {'output': {'tool_evidence': retained['evidence']} if retained['finished'] else {},
                            'tool_evidence': retained['evidence'], 'usage': {'available': False},
                            'effective_model_profile': payload['model_profile'],
                            'outcome': 'failed' if retained['finished'] else 'refused',
                            'effect_status': 'finished' if retained['finished'] else 'not_started',
                            'error_code': getattr(exc, 'code', 'executor_failed')}
            row = self.store.get('member', operation_id)
            # Durable pending result survives post-effect GAIT/sign/storage failure.
            row = self.store.transition('member', operation_id, row['state'], state='audit_pending', executor_result=terminal)
            await self._finish(row, terminal)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)): raise
            current = self.store.get('member', operation_id)
            if current and current['state'] in ('admitted', 'executor_claimed', 'effect_claimed'):
                self.store.transition('member', operation_id, current['state'], state='outcome_unknown' if current['attempt_id'] else 'refused', error_code=getattr(exc, 'code', 'execution_unavailable'))

    async def _finish(self, row, terminal):
        if row['receipt'] is not None: return
        payload, output = row['approval']['payload'], terminal['output']
        error, outcome = terminal['error_code'], terminal['outcome']
        if len(encode(output)) > payload['limits']['max_output_bytes']:
            output = {'error': 'output_overflow', 'raw_evidence_sha256': sha256(terminal['output'])}
            error, outcome = 'output_overflow', 'failed'
        audit = self._audit('protected_result', row, output_digest=sha256(output), tool_evidence_digest=sha256(terminal['tool_evidence']),
                            outcome=outcome, effect_status=terminal['effect_status'], error_code=error)
        receipt = {'receipt_id': str(uuid.uuid4()), 'operation_id': row['operation_id'], 'approval_id': row['approval_id'],
                   'approval_sha256': row['approval_digest'], 'attempt_id': row['attempt_id'],
                   'principal': payload['principal'], 'border': payload['border'], 'member': payload['member'],
                   'model_profile': payload['model_profile'], 'tool_call_sha256': sha256(payload['tool_call']),
                   'started_at_ms': row['started_ms'], 'finished_at_ms': max(self.now(), row['started_ms']),
                   'outcome': outcome, 'effect_status': terminal['effect_status'], 'output': output,
                   'output_sha256': sha256(output), 'tool_evidence_sha256': sha256(terminal['tool_evidence']),
                   'usage': terminal['usage'], 'audit_refs': dict(row['audit_refs'], result=audit), 'error_code': error}
        envelope = self.signer(RESULT, receipt)
        verify(envelope, row['trust_snapshot']['member'], RESULT)
        try:
            self.store.transition('member', row['operation_id'], 'audit_pending', state='result_ready', receipt=envelope,
                                  receipt_digest=digest(RESULT, receipt), audit_refs=receipt['audit_refs'], error_code=error)
        except ProtectedError as exc:
            current = self.store.get('member', row['operation_id'])
            if exc.code != 'state_conflict' or current['receipt'] is None:
                raise
            # Another reconciler durably completed this same immutable attempt.
            require(current['executor_result'] == terminal, 'receipt_conflict', 409)

    async def start(self):
        self.store.recover()

    async def close(self):
        if self.bridge: await self.bridge.close()
        # Cancellation does not release any spent execution/effect claim.
        for worker in list(self.workers): worker.cancel()
        if self.workers: await asyncio.gather(*self.workers, return_exceptions=True)
        if self.executor and hasattr(self.executor, 'close'):
            await maybe_await(self.executor.close())


class OperatorBridge:
    """Fixed bounded local transport. Bearer is only in an owned environment file."""
    def __init__(self, service, state_dir, installation_id):
        self.service, self.state_dir, self.installation = service, Path(state_dir), installation_id
        self.server = None
        content = private_file(self.state_dir / 'protected-operator.env', 4096).decode('ascii')
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        require(len(lines) == 1 and lines[0].startswith('NETCLAW_PROTECTED_OPERATOR_TOKEN='), 'bridge_credential_invalid', 503)
        self.token = lines[0].split('=', 1)[1].strip().strip('"').strip("'")
        require(len(self.token) >= 43 and len(self.token) <= 200 and self.token.isascii() and '\n' not in self.token, 'bridge_credential_invalid', 503)
        self.generation = str(uuid.uuid4())

    async def start(self):
        self.server = await asyncio.start_server(self._handle, '127.0.0.1', 0, limit=16384)
        port = self.server.sockets[0].getsockname()[1]
        write_private(self.state_dir / 'protected-operator.json', {'schemaVersion': 1, 'installationId': self.installation,
                      'port': port, 'generation': self.generation, 'credentialVariable': 'NETCLAW_PROTECTED_OPERATOR_TOKEN'})
        return port

    async def close(self):
        if self.server:
            self.server.close(); await self.server.wait_closed()

    async def _handle(self, reader, writer):
        status, result = 200, None
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 5)
            require(len(header) <= 16384)
            lines = header.decode('ascii').split('\r\n')
            require(lines[0] == 'POST /operator HTTP/1.1', 'invalid_bridge_request')
            headers = {}
            for line in lines[1:]:
                if not line: continue
                require(':' in line)
                name, value = line.split(':', 1); name = name.lower()
                require(name not in headers)
                headers[name] = value.strip()
            require('transfer-encoding' not in headers and headers.get('content-type', '').split(';')[0] == 'application/json')
            require(secrets.compare_digest(headers.get('authorization', ''), 'Bearer ' + self.token), 'bridge_unauthorized', 401)
            require(headers.get('content-length', '').isdigit())
            length = int(headers['content-length']); require(0 < length <= 1024 * 1024)
            body = decode(await asyncio.wait_for(reader.readexactly(length), 10))
            exact(body, 'method params')
            method, params = body['method'], body['params']
            require(isinstance(params, dict))
            require(not self.service.open_lab or not method.startswith('owner.'), 'method_refused', 404)
            if method in ('mobile.enrollment.info', 'mobile.enrollment.issue', 'mobile.enrollment.status'):
                require(self.service.open_lab, 'owner_issuance_unqualified', 403)
                require('auth_context' in params, 'lab_context_refused', 403)
                with self.service._owner(params['auth_context']):
                    args = {key: value for key, value in params.items() if key != 'auth_context'}
                    issuer = self.service.mobile_enrollment
                    result = getattr(issuer, method.rsplit('.', 1)[1])(args)
            elif method == 'owner.login':
                exact(params, 'ticket'); result = self.service.owner.login(params['ticket'])
            elif method == 'owner.session':
                exact(params, 'cookie'); result = self.service.owner.session(params['cookie'])
            elif method == 'owner.logout':
                exact(params, 'cookie csrf_token'); result = self.service.owner.logout(params['cookie'], params['csrf_token'])
            else:
                require(method in ('catalog', 'prepare', 'decision', 'status', 'reconcile', 'revoke', 'combined_prepare', 'combined_status', 'combined_cancel'), 'method_refused', 403)
                result = await getattr(self.service, method)(params)
            response = {'ok': True, 'result': result}
        except ProtectedError as exc:
            status, response = exc.status, {'ok': False, 'error': {'code': exc.code}}
        except Exception:
            status, response = 503, {'ok': False, 'error': {'code': 'protected_service_unavailable'}}
        data = encode(response)
        writer.write(('HTTP/1.1 %d Response\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: %d\r\n\r\n' % (status, len(data))).encode() + data)
        try: await writer.drain()
        finally: writer.close(); await writer.wait_closed()


def validate_profile(config, *, role=None, identity=None):
    """A Border cannot silently ignore a supplied local executor/credential catalog."""
    require(isinstance(config, dict), 'protected_profile_invalid')
    selected_role = config.get('role')
    require(selected_role in ('border', 'member'), 'unsupported_role')
    exact(config, ('schemaVersion role identity' + (' access' if 'access' in config else '')) if selected_role == 'border'
          else 'schemaVersion role identity catalog runtime border')
    if 'access' in config:
        validate_access(config['access'])
    require(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'protected_profile_invalid')
    validate_binding(config['identity'], selected_role)
    if role is not None:
        require(selected_role == role and config['identity'] == identity, 'local_authority_changed', 403)
    return config


def from_service(service):
    """Production-only factory: fixed private configuration and enrolled trust."""
    runtime, risk = service.runtime, service.risk
    require(runtime.installation is not None, 'installation_uninitialized', 503)
    config = validate_profile(decode(private_file(runtime.state / 'protected-profile.json')))
    original_profile = encode(config)
    role = config.get('role'); require(role in ('border', 'member'), 'unsupported_role')
    require((role == 'border') == risk.is_border(), 'role_mismatch', 503)
    identity = config['identity']; validate_binding(identity, role)
    require(identity['installation_id'] == runtime.installation, 'installation_mismatch', 403)
    if role == 'border':
        own_cert, own_key = risk.hub_credential()
        require(identity['identity'] == (risk.get_risk() or {}).get('risk_name', '') + '/border', 'identity_mismatch', 403)
    else:
        own_cert = risk.self_cert_pem()
        own_key = (risk.keys_dir / 'self.key').read_text()
        enrollment = risk.protected_enrollment()
        require(enrollment is not None and enrollment['enrollment_generation'] == identity['enrollment_generation'] and enrollment['member_id'] == identity['member_id'] and enrollment['installation_id'] == runtime.installation, 'protected_enrollment_required', 503)
    require(key_id(own_cert) == identity['key_id'], 'identity_key_mismatch', 403)

    def current_profile():
        try:
            current = validate_profile(decode(private_file(runtime.state / 'protected-profile.json')),
                                       role=role, identity=identity)
            require(encode(current) == original_profile, 'local_profile_changed', 403)
            # Trust is rechecked after remote effect authorization awaits. Bind
            # that final reread too, so drift during the await cannot execute an
            # old child merely because role/identity still match.
            if role == 'member' and hasattr(executor, 'validate_catalog'):
                executor.validate_catalog(current['catalog'], runtime_config=current['runtime'])
            return current
        except Exception:
            if hasattr(executor, 'invalidate'):
                executor.invalidate()
            raise

    def trust(binding, historical=False):
        current_configuration = current_profile()
        require(not historical, 'recorded_snapshot_required')
        require(isinstance(binding, dict), 'missing_authority', 403)
        if binding == identity:
            if role == 'member':
                current = risk.protected_enrollment()
                require(current and current['enrollment_generation'] == binding['enrollment_generation'], 'authority_changed', 403)
            return own_cert
        if role == 'border':
            member = risk.get_member(binding.get('member_id')) or {}
            require(member.get('state') in ('enrolled', 'active', 'unreachable') and
                    member.get('key_fingerprint') == binding.get('key_id') and
                    member.get('enrollment_generation') == binding.get('enrollment_generation') and
                    member.get('installation_id') == binding.get('installation_id'), 'member_authority_changed', 403)
            return member['pinned_key']
        require(binding == current_configuration.get('border'), 'border_authority_changed', 403)
        channel = service.border_channel
        require(channel is not None and getattr(channel, 'protected_peer_binding', None) == binding and getattr(channel, 'protected_peer_certificate', None), 'border_unavailable', 503)
        return channel.protected_peer_certificate

    def validate_channel(channel, binding):
        if role == 'border':
            return (channel is service.member_channels.get(binding.get('member_id')) and
                    getattr(channel, 'member_id', None) == binding.get('member_id') and
                    getattr(channel, 'enrollment_generation', None) == binding.get('enrollment_generation'))
        return channel is service.border_channel and getattr(channel, 'protected_peer_binding', None) == binding

    async def transport(member_id, method, params):
        channel = service.member_channels.get(member_id)
        require(channel is not None and channel.strict and channel.trusted, 'transport_unavailable', 503)
        return await channel.call(method, params, timeout=15)

    async def catalog():
        if role == 'member':
            current = current_profile()
            data = current['catalog']
            if not hasattr(executor, 'validate_catalog'):
                validate_catalog_entry(data)
            require(data['member'] == identity, 'catalog_identity_mismatch')
            return data
        entries = []
        for member in risk.list_members():
            if not member.get('enrollment_generation') or not member.get('installation_id'):
                continue
            channel = service.member_channels.get(member['member_id'])
            if channel is None or not channel.strict or not channel.trusted:
                continue
            try:
                entry = await channel.call('execution/catalog', {}, timeout=10)
                trust(entry['member'])
                entries.append(entry)
            except Exception:
                continue
        return entries

    owner = (OpenLabAccess(runtime.installation) if 'access' in config else
             OwnerAuthority(runtime.state, runtime.installation)) if role == 'border' else None
    executor = None
    if role == 'member':
        from .protected_runtime import build_executor
        validate_catalog_entry(config['catalog'])
        require(config['catalog']['member'] == identity, 'catalog_identity_mismatch')
        executor = build_executor(config['runtime'], manager=service.manager)
        try:
            if hasattr(executor, 'validate_catalog'):
                executor.validate_catalog(config['catalog'], runtime_config=config['runtime'])
        except BaseException:
            executor.close()
            raise
    operations = ProtectedOperations(service.manager, role=role, identity=identity,
        signer=lambda schema, payload: sign(schema, payload, own_key), trust_resolver=trust,
        catalog_provider=catalog, owner=owner, executor=executor,
        audit_writer=service.audit.protected, transport=transport, channel_validator=validate_channel)
    operations.config = config
    operations.mobile_enrollment = getattr(service, 'mobile_enrollment', None)
    if role == 'border':
        # Check authority initialization at startup; never promote legacy cookies.
        if not operations.open_lab:
            with owner.locked() as connection: owner._meta(connection)
        operations.bridge = OperatorBridge(operations, runtime.state, runtime.installation)
    return operations
