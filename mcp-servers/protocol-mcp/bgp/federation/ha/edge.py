"""Quorum-owned mobile identity; callers forward proofs, never principals.

This registry deliberately has no Risk/SQLite fallback. Every challenge is
single-use, every enrollment token is durably consumed, and revocation is
observed by every Border. Methods are synchronous: wire handlers run them in
to_thread and forward mutations once to the current leader.
"""
import hashlib
import json
import re
import secrets
import time
import uuid

from ..certs import time_valid
from ..protected_contract import encode, exact, ident, key_id, uuid_field
from ..risk import RiskManager
from .config import check

PREFIX = b'netclaw.ncfed.ha/device-proof/v1\0'
REQUEST_PREFIX = b'netclaw.ncfed.ha/device-request/v1\0'
META = 'edge/index'
MAX_OFFERS = 128
MAX_CHALLENGES = 64
CHALLENGE_MS = 30_000
OFFER_MS = 120_000


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def proof_bytes(challenge, member_id, purpose, token=None):
    return PREFIX + encode({'challenge': challenge, 'member_id': member_id,
                           'purpose': purpose,
                           'token_sha256': digest(token) if token else None})


def principal(manifest, record):
    subject = str(uuid.uuid5(uuid.UUID(manifest.cluster_id),
        'netclaw.mobile.cluster-device:' + json.dumps([
            manifest.generation, record['member_id'], record['key_fingerprint'],
            record['enrollment_generation']], separators=(',', ':'))))
    return {'issuer': 'device-key', 'subject': subject,
            'display_name': 'Enrolled mobile device', 'roles': ['device-operator']}


class VerifiedClusterDevice:
    """Local verification result. Never reconstructed from caller principal JSON."""
    def __init__(self, binding, key, revision):
        self.binding, self.key, self.revision = binding, key, revision

    def principal(self):
        return dict(self.binding['principal'])


class ClusterEdgeRegistry:
    def __init__(self, authority, *, clock_ms=None):
        self.authority = authority
        self.manifest = authority.manifest
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    @staticmethod
    def _index(rows):
        return rows[META][0] or {'devices': [], 'offers': [], 'challenges': {}}

    def _node(self, rows, node_id):
        node = self.manifest.node(node_id)
        control = rows['control'][0]
        check(control['active'], 'recovery_fenced', 503)
        check(control['nodes'].get(node_id, {}).get('state') == 'active', 'node_retired', 403)
        check(control['nodes'][node_id]['key_id'] == node['key_id'], 'node_key_changed', 403)
        return node

    def challenge(self, node_id):
        now = self.clock_ms()
        node = self.manifest.node(node_id)
        challenge = {'schema_version': 1, **self.manifest.audience,
                     'node_id': node_id, 'installation_id': node['installation_id'],
                     'nonce': secrets.token_hex(32), 'expires_at_ms': now + CHALLENGE_MS}
        def transition(rows):
            self._node(rows, node_id)
            index = self._index(rows)
            index['challenges'] = {k: v for k, v in index['challenges'].items() if v['expires_at_ms'] > now}
            check(len(index['challenges']) < MAX_CHALLENGES, 'device_challenge_capacity', 503)
            index['challenges'][digest(challenge['nonce'])] = challenge
            return [(META, index, None)], challenge
        return self.authority.mutate('edge.challenge', [META], transition)[0]

    def _consume_challenge(self, rows, index, challenge):
        exact(challenge, 'schema_version cluster_id generation node_id installation_id nonce expires_at_ms')
        check(type(challenge['schema_version']) is int and challenge['schema_version'] == 1)
        check({k: challenge[k] for k in self.manifest.audience} == self.manifest.audience,
              'cluster_changed', 403)
        node = self._node(rows, challenge['node_id'])
        check(node['installation_id'] == challenge['installation_id'], 'node_changed', 403)
        check(isinstance(challenge['nonce'], str) and re.fullmatch('[a-f0-9]{64}', challenge['nonce']))
        key = digest(challenge['nonce'])
        check(index['challenges'].get(key) == challenge, 'device_challenge_spent', 403)
        check(type(challenge['expires_at_ms']) is int and self.clock_ms() < challenge['expires_at_ms'],
              'device_challenge_expired', 403)
        del index['challenges'][key]

    def issue(self, node_id, client_nonce, replace_client_nonce=None):
        uuid_field(client_nonce)
        if replace_client_nonce is not None:
            uuid_field(replace_client_nonce)
        node = self.manifest.node(node_id)
        offer_key = 'edge/offers/' + client_nonce
        replace_key = 'edge/offers/' + replace_client_nonce if replace_client_nonce else None
        check(replace_key != offer_key, 'invalid_replacement')
        token = 'in2n_' + secrets.token_urlsafe(24)
        now = self.clock_ms()
        offer = {'client_nonce': client_nonce, 'node_id': node_id,
                 'installation_id': node['installation_id'], 'token_sha256': digest(token),
                 'issued_at_ms': now, 'expires_at_ms': now + OFFER_MS, 'state': 'issued'}
        keys = [META, offer_key] + ([replace_key] if replace_key else [])
        def transition(rows):
            self._node(rows, node_id)
            index = self._index(rows)
            check(rows[offer_key][0] is None, 'offer_already_issued', 409)
            check(len(index['offers']) < MAX_OFFERS, 'device_offer_capacity', 503)
            writes = []
            if replace_key:
                old = rows[replace_key][0]
                check(old and old['state'] == 'issued', 'offer_not_replaceable', 409)
                old['state'] = 'replaced'
                writes.append((replace_key, old, None))
            index['offers'].append(client_nonce)
            writes.extend([(META, index, None), (offer_key, offer, None)])
            # Raw token is returned by this stack only; never in a decision receipt.
            return writes, self._public_offer(offer)
        result, _ = self.authority.mutate('edge.offer', keys, transition)
        return {**result, 'enrollment_token': token}

    def _public_offer(self, offer):
        state = offer['state']
        if state == 'issued' and self.clock_ms() >= offer['expires_at_ms']:
            state = 'expired'
        return {k: v for k, v in offer.items() if k != 'token_sha256'} | {'state': state}

    def status(self, client_nonce):
        uuid_field(client_nonce)
        key = 'edge/offers/' + client_nonce
        rows = self.authority.snapshot([key])
        check(rows['control'][0]['active'], 'recovery_fenced', 503)
        offer = rows[key][0]
        return self._public_offer(offer) if offer else {'client_nonce': client_nonce, 'state': 'absent'}

    @staticmethod
    def _proof(certificate, challenge, member_id, purpose, signature, token=None):
        ident(member_id)
        check(isinstance(certificate, str) and len(certificate) <= 8192 and time_valid(certificate),
              'device_certificate_invalid', 403)
        check(isinstance(signature, str) and re.fullmatch('[a-f0-9]{16,400}', signature), 'device_proof_invalid', 403)
        check(RiskManager.verify_possession(certificate, proof_bytes(challenge, member_id, purpose, token),
                                            bytes.fromhex(signature)), 'device_proof_invalid', 403)
        return key_id(certificate)

    def enroll(self, *, client_nonce, token, member_id, certificate, challenge, signature):
        uuid_field(client_nonce)
        check(isinstance(token, str) and re.fullmatch(r'in2n_[A-Za-z0-9_-]{32}', token), 'invalid_token', 403)
        fingerprint = self._proof(certificate, challenge, member_id, 'enroll', signature, token)
        offer_key, device_key = 'edge/offers/' + client_nonce, 'edge/devices/' + digest(member_id)
        enrollment_generation = str(uuid.uuid4())
        record = {'member_id': member_id, 'certificate': certificate, 'key_fingerprint': fingerprint,
                  'enrollment_generation': enrollment_generation, 'state': 'active'}
        principal_key = 'edge-principals/' + principal(self.manifest, record)['subject']
        def transition(rows):
            index = self._index(rows)
            self._consume_challenge(rows, index, challenge)
            offer = rows[offer_key][0]
            check(offer and offer['state'] == 'issued' and offer['token_sha256'] == digest(token)
                  and offer['expires_at_ms'] > self.clock_ms(), 'invalid_token', 403)
            check(offer['node_id'] == challenge['node_id'], 'enrollment_endpoint_changed', 403)
            check(rows[device_key][0] is None, 'device_already_enrolled', 409)
            check(len(index['devices']) < self.manifest.limits['max_members'], 'device_capacity', 503)
            index['devices'].append(member_id)
            offer['state'] = 'consumed'
            offer['member_id'] = member_id
            check(rows[principal_key][0] is None, 'device_principal_exists', 409)
            return [(META, index, None), (offer_key, offer, None), (device_key, record, None),
                    (principal_key, self._principal_record(record), None)], record
        record = self.authority.mutate('edge.enroll', [META, offer_key, device_key, principal_key], transition)[0]
        return self._binding(record)

    def hello(self, *, member_id, key_fingerprint, challenge, signature):
        ident(member_id)
        key = 'edge/devices/' + digest(member_id)
        def transition(rows):
            record = rows[key][0]
            check(record and record['state'] == 'active' and record['key_fingerprint'] == key_fingerprint,
                  'device_authority_changed', 403)
            self._proof(record['certificate'], challenge, member_id, 'hello', signature)
            index = self._index(rows)
            self._consume_challenge(rows, index, challenge)
            return [(META, index, None)], self._binding(record)
        return self.authority.mutate('edge.hello', [META, key], transition)[0]

    def _binding(self, record):
        return {**record, **self.manifest.audience, 'principal': principal(self.manifest, record)}

    def _principal_record(self, record):
        return {k: v for k, v in self._binding(record).items() if k in
                ('principal', 'member_id', 'key_fingerprint', 'enrollment_generation', 'state')}

    def verify_request(self, proof, method, params):
        exact(proof, 'schema_version cluster_id generation member_id enrollment_generation request_id method params_sha256 signature')
        check(type(proof['schema_version']) is int and proof['schema_version'] == 1)
        uuid_field(proof['request_id']); uuid_field(proof['enrollment_generation'])
        check({k: proof[k] for k in self.manifest.audience} == self.manifest.audience, 'cluster_changed', 403)
        check(method in tuple('n2n/edge/operations/' + action for action in
                              ('catalog', 'prepare', 'status', 'decision', 'reconcile'))
              and proof['method'] == method, 'device_proof_invalid', 403)
        check(isinstance(params, dict) and 'device_proof' not in params and len(encode(params)) <= 64 * 1024
              and proof['params_sha256'] == hashlib.sha256(encode(params)).hexdigest(), 'device_proof_invalid', 403)
        binding = self.binding(proof['member_id'])
        check(binding['enrollment_generation'] == proof['enrollment_generation'], 'device_authority_changed', 403)
        signature = proof['signature']
        check(isinstance(signature, str) and re.fullmatch('[a-f0-9]{16,400}', signature), 'device_proof_invalid', 403)
        body = {k: v for k, v in proof.items() if k != 'signature'}
        check(RiskManager.verify_possession(binding['certificate'], REQUEST_PREFIX + encode(body),
                                            bytes.fromhex(signature)), 'device_proof_invalid', 403)
        key = 'edge-principals/' + binding['principal']['subject']
        record, revision = self.authority.snapshot([key])[key]
        check(record == self._principal_record(binding) and record['state'] == 'active',
              'device_authority_changed', 403)
        return VerifiedClusterDevice(binding, key, revision)

    def binding(self, member_id):
        ident(member_id)
        key = 'edge/devices/' + digest(member_id)
        rows = self.authority.snapshot([key])
        check(rows['control'][0]['active'], 'recovery_fenced', 503)
        record = rows[key][0]
        check(record and record['state'] == 'active' and time_valid(record['certificate']),
              'device_authority_changed', 403)
        return self._binding(record)

    def revoke(self, member_id):
        ident(member_id)
        key = 'edge/devices/' + digest(member_id)
        # Never derive a subject from untrusted caller input.
        record = self.authority.snapshot([key])[key][0]
        check(record is not None, 'device_not_found', 404)
        principal_key = 'edge-principals/' + principal(self.manifest, record)['subject']
        def transition(rows):
            record = rows[key][0]
            check(record is not None, 'device_not_found', 404)
            record['state'] = 'revoked'
            control = rows['control'][0]
            control['revocation_revision'] += 1
            return [(key, record, None), (principal_key, self._principal_record(record), None),
                    ('control', control, None)], {'member_id': member_id, 'state': 'revoked'}
        return self.authority.mutate('edge.revoke', [key, principal_key], transition)[0]
