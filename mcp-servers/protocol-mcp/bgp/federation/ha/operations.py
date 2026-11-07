"""Bounded quorum metadata. No raw provider/device output or secret replication."""
import copy
import re
import time
import uuid

from .. import protected_contract as c
from .config import HAError, check


def operation_key(operation_id):
    c.uuid_field(operation_id)
    return 'operations/' + operation_id


def member_key(binding):
    c.validate_binding(binding, 'member')
    return 'members/' + c.sha256({'installation_id': binding['installation_id'], 'member_id': binding['member_id']})


def reservation_keys(review):
    member = review['member']
    # The member-wide reservation deliberately covers different request IDs and
    # profile aliases on the same isolated executor, including unknown outcomes.
    return ['resources/' + c.sha256({'kind': 'member', 'installation': member['installation_id'],
                                    'member_id': member['member_id']}),
            'resources/' + c.sha256({'kind': 'runner', 'installation': member['installation_id'],
                                    'profile': review['model_profile']['profile_id']})]


def validate_admission(request):
    c.exact(request, 'cluster_id generation operation_id attempt_id approval_digest kind ordinal request_digest member_incarnation nonce')
    for key in ('cluster_id', 'generation', 'operation_id', 'attempt_id', 'member_incarnation'):
        c.uuid_field(request[key])
    for key in ('approval_digest', 'request_digest', 'nonce'):
        c.digest_field(request[key])
    check(request['kind'] in ('model', 'tool') and type(request['ordinal']) is int
          and request['ordinal'] in ((1, 2) if request['kind'] == 'model' else (1,)), 'invalid_admission')
    return 'claims/' + request['operation_id'] + '/' + request['kind'] + str(request['ordinal'])


class OperationLedger:
    def __init__(self, authority, *, clock_ms=None):
        self.authority = authority
        self.now = clock_ms or (lambda: int(time.time() * 1000))

    @staticmethod
    def _execution_capacity(rows):
        check(not rows['control'][0].get('recovery', {}).get('capacity_frozen', False),
              'recovery_fenced', 503)

    @staticmethod
    def _principal_keys(principal):
        return ['edge-principals/' + principal['subject']] if principal['issuer'] == 'device-key' else []

    def _principal_current(self, rows, principal):
        # The enrollment revision participates in the SAME quorum transaction
        # as the effect claim. A previously verified signature is not a grant
        # that survives device revocation between request and execution.
        for key in self._principal_keys(principal):
            record = rows[key][0]
            check(record is not None and record['state'] == 'active'
                  and record['principal'] == principal, 'device_authority_changed', 403)

    def _nonce(self, principal, nonce):
        c.validate_principal(principal); c.ident(nonce)
        return 'nonces/' + c.sha256({'principal': principal, 'nonce': nonce})

    def enroll_member(self, binding, certificate):
        key = member_key(binding)
        check(all(binding['installation_id'] != node['installation_id']
                  and binding['key_id'] != node['key_id']
                  for node in self.authority.manifest.nodes), 'member_border_identity_collision', 403)
        check(c.key_id(certificate) == binding['key_id'], 'member_key_mismatch', 403)
        from ..certs import time_valid
        check(time_valid(certificate), 'member_certificate_expired', 403)
        entry = {'binding': binding, 'certificate': certificate, 'state': 'active'}
        def transition(rows):
            old, _ = rows[key]
            check(old is None or old == entry, 'member_enrollment_conflict', 409)
            control = rows['control'][0]
            count = control.get('member_count', 0)
            check(old is not None or count < self.authority.manifest.limits['max_members'], 'state_capacity', 503)
            control['member_count'] = count + int(old is None)
            control['membership_revision'] += int(old is None)
            return [('control', control, None), (key, entry, None)], entry
        return self.authority.mutate('enroll_member', [key], transition)[0]

    def _member(self, rows, binding):
        entry = rows[member_key(binding)][0]
        check(entry is not None and entry['state'] == 'active' and entry['binding'] == binding,
              'member_not_enrolled', 403)
        return entry

    def lookup(self, *, operation_id=None, client_nonce=None, principal=None):
        if operation_id is None:
            index = self.authority.snapshot([self._nonce(principal, client_nonce)])[self._nonce(principal, client_nonce)][0]
            if index is None:
                return None
            operation_id = index['operation_id']
        key = operation_key(operation_id)
        row = self.authority.snapshot([key])[key][0]
        if row and principal is not None:
            check(row['review']['principal'] == principal, 'operation_not_found', 404)
        return row

    def prepare(self, client_nonce, candidate_digest, review):
        c.validate_review(review, cluster=True); c.digest_field(candidate_digest)
        old = self.lookup(client_nonce=client_nonce, principal=review['principal'])
        if old is not None:
            check(old['candidate_digest'] == candidate_digest and old['review'] == review, 'client_nonce_conflict', 409)
            return old
        op = str(uuid.uuid4()); key = operation_key(op)
        nonce_key, enrollment = self._nonce(review['principal'], client_nonce), member_key(review['member'])
        node = self.authority.manifest.node(self.authority.node_id)
        expected = {**self.authority.manifest.audience, 'manifest_revision': self.authority.manifest.revision,
                    'issuer_node_id': self.authority.node_id, 'authority_epoch': self.authority.epoch}
        check(review['cluster'] == expected, 'stale_review', 409)
        check(review['border'] == {'installation_id': node['installation_id'], 'identity': node['identity'],
              'key_id': node['key_id'], 'authority_generation': self.authority.manifest.generation}, 'review_issuer_mismatch', 403)
        row = {'operation_id': op, 'client_nonce': client_nonce, 'candidate_digest': candidate_digest,
               'review': copy.deepcopy(review), 'review_digest': c.sha256(review), 'state': 'review_pending',
               'revision': 1, 'approval': None, 'approval_id': None, 'approval_digest': None,
               'attempt_id': None, 'dispatch_leader': None, 'revoked': False, 'result_ref': None,
               'ack': None, 'member_incarnation': None}
        def transition(rows):
            check(rows[nonce_key][0] is None and rows[key][0] is None, 'client_nonce_conflict', 409)
            self._execution_capacity(rows)
            self._principal_current(rows, review['principal'])
            enrolled = self._member(rows, review['member'])
            row['trust_snapshot'] = {'member': enrolled['certificate'], 'border': node['certificate']}
            control = rows['control'][0]
            check(control['operation_count'] < self.authority.manifest.limits['max_operations'], 'state_capacity', 503)
            check(self.now() < review['limits']['expires_at_ms'], 'approval_expired', 403)
            control['operation_count'] += 1
            check(len(c.encode(row)) <= 65536, 'state_capacity', 503)
            return [(key, row, None), (nonce_key, {'operation_id': op, 'candidate_digest': candidate_digest}, None),
                    ('control', control, None)], row
        return self.authority.mutate('prepare', [key, nonce_key, enrollment, *self._principal_keys(review['principal'])], transition)[0]

    def approve(self, operation_id, envelope, *, revision, review_digest):
        key = operation_key(operation_id)
        node = self.authority.manifest.node(self.authority.node_id)
        payload = c.verify(envelope, node['certificate'], c.HA_APPROVAL)
        def transition(rows):
            row = rows[key][0]
            check(row is not None, 'operation_not_found', 404)
            self._execution_capacity(rows)
            self._principal_current(rows, row['review']['principal'])
            check(row['state'] == 'review_pending' and row['revision'] == revision and not row['revoked'], 'revision_conflict', 409)
            check(row['review_digest'] == review_digest and c.review_from_payload(payload) == row['review']
                  and payload['operation_id'] == operation_id, 'review_changed', 409)
            check(row['review']['cluster']['authority_epoch'] == self.authority.epoch
                  and row['review']['cluster']['issuer_node_id'] == self.authority.node_id, 'stale_review', 409)
            check(payload['issued_at_ms'] <= self.now() < payload['limits']['expires_at_ms'], 'approval_expired', 403)
            row.update(state='approved', revision=row['revision'] + 1, approval=envelope,
                       approval_id=payload['approval_id'], approval_digest=c.digest(c.HA_APPROVAL, payload))
            check(len(c.encode(row)) <= 65536, 'state_capacity', 503)
            return [(key, row, None)], row
        return self.authority.mutate('approve', [key, *self._principal_keys(payload['principal'])], transition)[0]

    def revoke(self, operation_id):
        key = operation_key(operation_id)
        def transition(rows):
            row = rows[key][0]; check(row is not None, 'operation_not_found', 404)
            row['revoked'] = True; row['revision'] += 1
            return [(key, row, None)], row
        return self.authority.mutate('revoke', [key], transition)[0]

    def deny(self, operation_id, *, revision, review_digest):
        key = operation_key(operation_id)
        original = self.lookup(operation_id=operation_id)
        check(original is not None, 'operation_not_found', 404)
        def transition(rows):
            row = rows[key][0]; check(row is not None, 'operation_not_found', 404)
            self._principal_current(rows, row['review']['principal'])
            check(row['review']['cluster']['authority_epoch'] == self.authority.epoch
                  and row['review']['cluster']['issuer_node_id'] == self.authority.node_id, 'stale_review', 409)
            check(row['state'] == 'review_pending' and row['revision'] == revision
                  and row['review_digest'] == review_digest, 'revision_conflict', 409)
            row.update(state='refused', revoked=True, revision=row['revision'] + 1, error_code='owner_denied')
            return [(key, row, None)], row
        return self.authority.mutate('deny', [key, *self._principal_keys(original['review']['principal'])], transition)[0]

    def mark_unknown(self, operation_id):
        key = operation_key(operation_id)
        def transition(rows):
            row = rows[key][0]; check(row is not None, 'operation_not_found', 404)
            if row['result_ref'] is None:
                row.update(state='outcome_unknown', revision=row['revision'] + 1, error_code='submit_outcome_unknown')
            return [(key, row, None)], row
        return self.authority.mutate('submit_unknown', [key], transition)[0]

    def acknowledge_delivery(self, operation_id, receipt_digest):
        key = operation_key(operation_id)
        def transition(rows):
            row = rows[key][0]; check(row is not None and row['ack'] is not None, 'ack_not_ready', 409)
            check(row['result_ref']['digest'] == receipt_digest, 'ack_binding_mismatch', 409)
            row.update(ack_delivered=True, revision=row['revision'] + 1)
            return [(key, row, None)], row
        return self.authority.mutate('ack_delivery', [key], transition)[0]

    def dispatch(self, operation_id):
        key = operation_key(operation_id)
        original = self.lookup(operation_id=operation_id)
        check(original is not None, 'operation_not_found', 404)
        resources = reservation_keys(original['review'])
        attempt = str(uuid.uuid4())
        enrollment = member_key(original['review']['member'])
        def transition(rows):
            row = rows[key][0]
            check(row['attempt_id'] is None, 'dispatch_already_claimed', 409)
            self._execution_capacity(rows)
            self._principal_current(rows, row['review']['principal'])
            check(row['state'] == 'approved' and not row['revoked'], 'operation_not_approved', 409)
            check(self.now() < row['review']['limits']['expires_at_ms'], 'approval_expired', 403)
            self._member(rows, row['review']['member'])
            for resource in resources:
                held = rows[resource][0]
                check(held is None or held['state'] == 'released', 'resource_recovery_required', 409)
            row.update(state='dispatch_claimed', attempt_id=attempt, revision=row['revision'] + 1,
                       dispatch_leader={'value': rows['leader'][0], 'epoch': rows['leader'][1]})
            reservation = {'operation_id': operation_id, 'attempt_id': attempt, 'state': 'reserved'}
            return [(key, row, None)] + [(k, reservation, None) for k in resources], row
        return self.authority.mutate('dispatch', [key, enrollment, *resources,
            *self._principal_keys(original['review']['principal'])], transition)[0]

    def _admission_binding(self, row, request, binding):
        check(row is not None and row['review']['member'] == binding, 'foreign_member', 403)
        check(request['attempt_id'] == row['attempt_id'] and request['approval_digest'] == row['approval_digest'],
              'admission_binding_mismatch', 403)
        check({k: request[k] for k in ('cluster_id', 'generation')} == self.authority.manifest.audience,
              'cluster_changed', 409)

    def admit(self, request, binding):
        claim_key = validate_admission(request)
        key, enrollment = operation_key(request['operation_id']), member_key(binding)
        original = self.lookup(operation_id=request['operation_id'])
        self._admission_binding(original, request, binding)
        resources = reservation_keys(original['review'])
        def transition(rows):
            row = rows[key][0]
            self._execution_capacity(rows)
            self._principal_current(rows, row['review']['principal'])
            self._admission_binding(row, request, binding)
            self._member(rows, binding)
            check(row['state'] in ('dispatch_claimed', 'member_admitted') and not row['revoked'], 'operation_revoked', 403)
            check(self.now() < row['review']['limits']['expires_at_ms'], 'approval_expired', 403)
            check(rows[claim_key][0] is None, 'admission_spent', 409)
            check(row['member_incarnation'] in (None, request['member_incarnation']), 'member_restarted', 409)
            for resource in resources:
                held = rows[resource][0]
                check(held and held['state'] == 'reserved' and held['operation_id'] == row['operation_id']
                      and held['attempt_id'] == row['attempt_id'], 'resource_recovery_required', 409)
            claim = {'request': request, 'member_sha256': c.sha256(binding), 'leader': rows['leader'][0],
                     'epoch': rows['leader'][1], 'state': 'committed'}
            check(len(c.encode(claim)) <= 4096, 'state_capacity', 503)
            row.update(state='member_admitted', member_incarnation=request['member_incarnation'], revision=row['revision'] + 1)
            return [(claim_key, claim, None), (key, row, None)], claim
        return self.authority.mutate('admit_' + request['kind'], [key, enrollment, claim_key, *resources,
            *self._principal_keys(original['review']['principal'])], transition)

    def admission_status(self, request, binding):
        claim_key = validate_admission(request)
        key, enrollment = operation_key(request['operation_id']), member_key(binding)
        rows = self.authority.snapshot([key, enrollment, claim_key])
        self._member(rows, binding)
        self._admission_binding(rows[key][0], request, binding)
        claim, revision = rows[claim_key]
        check(claim is not None and claim['request'] == request and claim['member_sha256'] == c.sha256(binding),
              'admission_not_found', 404)
        return claim, revision

    def accept_result(self, operation_id, envelope, *, private_key, audit_ref):
        """Commit a bounded reference and successor ACK; never redispatch work.

        Original evidence remains in the member's durable artifact store. Failure
        results do not automatically release resource fences: guard uncertainty
        needs a separate proven reconciliation, not a terminal UI label.
        """
        key = operation_key(operation_id)
        original = self.lookup(operation_id=operation_id)
        check(original is not None, 'operation_not_found', 404)
        payload = c.verify(envelope, original['trust_snapshot']['member'], c.HA_RESULT)
        review = original['review']
        check(payload['operation_id'] == operation_id and payload['approval_id'] == original['approval_id']
              and payload['attempt_id'] == original['attempt_id'] and payload['approval_sha256'] == original['approval_digest'],
              'result_binding_mismatch', 409)
        check(all(payload[k] == review[k] for k in ('principal', 'border', 'member', 'model_profile', 'cluster'))
              and payload['tool_call_sha256'] == c.sha256(review['tool_call']), 'result_binding_mismatch', 409)
        check(len(c.encode(payload['output'])) <= review['limits']['max_output_bytes'], 'output_too_large')
        result_digest = c.digest(c.HA_RESULT, payload)
        if original['result_ref'] is not None:
            check(original['result_ref']['digest'] == result_digest, 'receipt_conflict', 409)
            return original
        c.ident(audit_ref)
        node = self.authority.manifest.node(self.authority.node_id)
        binding = {'installation_id': node['installation_id'], 'identity': node['identity'],
                   'key_id': node['key_id'], 'authority_generation': self.authority.manifest.generation}
        ack = c.sign(c.HA_ACK, {
            'ack_id': str(uuid.uuid4()), 'operation_id': operation_id, 'approval_id': payload['approval_id'],
            'attempt_id': payload['attempt_id'], 'receipt_id': payload['receipt_id'], 'receipt_sha256': result_digest,
            'border': payload['border'], 'member': payload['member'], 'cluster': payload['cluster'],
            'accepted_at_ms': self.now(), 'audit_ref': audit_ref,
            'acceptance': {'node_id': self.authority.node_id, 'border': binding, 'authority_epoch': self.authority.epoch}}, private_key)
        c.verify(ack, node['certificate'], c.HA_ACK)
        resources = reservation_keys(review)
        def transition(rows):
            row = rows[key][0]
            check(row['approval_digest'] == original['approval_digest'] and row['attempt_id'] == original['attempt_id'],
                  'result_binding_mismatch', 409)
            if row['result_ref'] is not None:
                check(row['result_ref']['digest'] == result_digest, 'receipt_conflict', 409)
                # Concurrent identical collection retains the first ACK.
                return [(key, row, None)], row
            row.update(state={'succeeded': 'completed', 'failed': 'failed', 'refused': 'refused'}[payload['outcome']],
                result_ref={'digest': result_digest, 'receipt_id': payload['receipt_id'],
                            'artifact_id': operation_id, 'member': payload['member'], 'outcome': payload['outcome'],
                            'effect_status': payload['effect_status']}, ack=ack, revision=row['revision'] + 1)
            writes = [(key, row, None)]
            if payload['outcome'] == 'succeeded' and payload['effect_status'] == 'finished':
                for resource in resources:
                    held = rows[resource][0]
                    check(held is not None and held['operation_id'] == operation_id
                          and held['attempt_id'] == row['attempt_id'], 'resource_binding_conflict', 409)
                    held['state'] = 'released'
                    held['result_digest'] = result_digest
                    writes.append((resource, held, None))
            return writes, row
        return self.authority.mutate('accept_result', [key, *resources], transition)[0]
