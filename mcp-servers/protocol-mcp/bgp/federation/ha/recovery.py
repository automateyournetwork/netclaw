"""Fenced NCFED recovery. Old approvals/claims never become fresh capacity.

A snapshot is a quorum-consistent export, not proof that nothing happened later.
All restoration therefore retains a global execution-capacity fence. This module
has deliberately no boolean, timer or operator override that clears that fence.
"""
import base64
import copy
from dataclasses import dataclass, field
import re
import time

from .. import protected_contract as c
from ..certs import time_valid
from .config import HAError, check

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_SNAPSHOT_KEYS = 16384
MAX_RECEIPT_AGE_MS = 300000
_RECEIPT = object()
_DOMAIN = b'netclaw.ncfed.ha/owned-host-isolation/v1\0'


def now_ms():
    return int(time.time() * 1000)


def _key(key):
    check(isinstance(key, str) and len(key) <= 240 and re.fullmatch(
        r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', key), 'invalid_snapshot_key')


def snapshot_document(manifest, rows, revision, *, now_ms=None):
    check(type(revision) is int and 0 < revision <= 2**53 - 1, 'invalid_snapshot_revision')
    check(isinstance(rows, dict) and 1 <= len(rows) <= MAX_SNAPSHOT_KEYS, 'snapshot_capacity')
    records = {}
    for key, pair in rows.items():
        _key(key)
        check(isinstance(pair, (list, tuple)) and len(pair) == 2, 'invalid_snapshot_record')
        value, modified = pair
        check(type(modified) is int and 0 < modified <= revision, 'invalid_snapshot_revision')
        check(value is not None and len(c.encode(value)) <= 65536, 'snapshot_capacity')
        if key != 'leader':
            records[key] = {'value': copy.deepcopy(value), 'revision': modified}
    control = records.get('control', {}).get('value')
    check(isinstance(control, dict) and {k: control.get(k) for k in manifest.audience} == manifest.audience
          and control.get('manifest_sha256') == c.sha256(manifest.value)
          and control.get('manifest_revision') == manifest.revision, 'snapshot_identity_mismatch')
    created = globals()['now_ms']() if now_ms is None else now_ms
    check(type(created) is int and created > 0, 'invalid_snapshot_time')
    document = {'schema_version': 1, **manifest.audience, 'revision': revision,
                'created_at_ms': created, 'manifest_sha256': c.sha256(manifest.value), 'records': records}
    check(len(c.encode(document)) <= MAX_SNAPSHOT_BYTES, 'snapshot_capacity')
    return document


def validate_snapshot(snapshot, manifest):
    c.exact(snapshot, 'schema_version cluster_id generation revision created_at_ms manifest_sha256 records')
    check(snapshot['schema_version'] == 1 and {k: snapshot[k] for k in manifest.audience} == manifest.audience
          and snapshot['manifest_sha256'] == c.sha256(manifest.value), 'snapshot_identity_mismatch')
    rows = {}
    check(isinstance(snapshot['records'], dict), 'invalid_snapshot_record')
    for key, record in snapshot['records'].items():
        c.exact(record, 'value revision')
        check(key != 'leader', 'leased_authority_restore_refused')
        rows[key] = (record['value'], record['revision'])
    check(snapshot_document(manifest, rows, snapshot['revision'], now_ms=snapshot['created_at_ms']) == snapshot,
          'invalid_snapshot')
    return snapshot


def export_snapshot(store, manifest):
    """Single linearizable prefix read. Truncation/capacity errors fail closed.

    EtcdStore is used directly; members never receive its credentials. No paged
    read can silently mix revisions. Raw provider/device output is not exported.
    """
    prefix = store.prefix.encode()
    end = prefix[:-1] + bytes([prefix[-1] + 1])
    from .store import b64
    response = store._request('/v3/kv/range', {'key': b64(prefix), 'range_end': b64(end),
        'serializable': False, 'limit': MAX_SNAPSHOT_KEYS + 1}, read_only=True)
    try:
        check(not response.get('more', False), 'snapshot_capacity')
        rows = response.get('kvs', [])
        check(isinstance(rows, list) and 0 < len(rows) <= MAX_SNAPSHOT_KEYS, 'snapshot_capacity')
        result = {}
        for row in rows:
            key = base64.b64decode(row['key'], validate=True).decode()
            check(key.startswith(store.prefix), 'snapshot_scope_mismatch')
            key = key[len(store.prefix):]
            check(key not in result, 'duplicate_snapshot_key')
            result[key] = (c.decode(base64.b64decode(row['value'], validate=True), 65536), int(row['mod_revision']))
        return snapshot_document(manifest, result, int(response['header']['revision']))
    except HAError:
        raise
    except Exception:
        raise HAError('invalid_snapshot', 503) from None


def isolation_message(payload):
    raw = c.encode(payload)
    check(len(raw) <= 16384, 'isolation_receipt_capacity')
    return _DOMAIN + raw


@dataclass(frozen=True)
class IsolationReceipt:
    """In-process verified proof; unsigned caller dictionaries are never proofs."""
    _payload_bytes: bytes = field(repr=False)
    digest: str
    _proof: object = field(repr=False, compare=False)

    @property
    def payload(self):
        return c.decode(self._payload_bytes, 16384)


def _new_generation(old, new):
    check(new.cluster_id == old.cluster_id and new.generation != old.generation,
          'new_generation_required', 409)
    check(new.value['organization'] == old.value['organization'] and new.revision > old.revision
          and new.anchor_key_id == old.anchor_key_id, 'reenrollment_mismatch', 403)
    for name in ('node_id', 'installation_id', 'key_id'):
        check(not {n[name] for n in old.nodes} & {n[name] for n in new.nodes}, 'fresh_node_trust_required', 403)


def verify_isolation(proof, certificate, *, expected_key_id, old_manifest, new_manifest, snapshot, now_ms=None):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    try:
        validate_snapshot(snapshot, old_manifest); _new_generation(old_manifest, new_manifest)
        c.exact(proof, 'payload key_id signature')
        check(proof['key_id'] == expected_key_id == c.key_id(certificate)
              and time_valid(certificate), 'isolation_signer_mismatch', 403)
        check(isinstance(proof['signature'], str) and re.fullmatch('[A-Za-z0-9_-]{8,200}', proof['signature']),
              'invalid_isolation_signature', 403)
        raw = base64.urlsafe_b64decode(proof['signature'] + '=' * (-len(proof['signature']) % 4))
        check(base64.urlsafe_b64encode(raw).rstrip(b'=').decode() == proof['signature'], 'invalid_isolation_signature', 403)
        public = x509.load_pem_x509_certificate(certificate.encode()).public_key()
        check(isinstance(public, ec.EllipticCurvePublicKey) and isinstance(public.curve, ec.SECP256R1),
              'invalid_isolation_signature', 403)
        public.verify(raw, isolation_message(proof['payload']), ec.ECDSA(hashes.SHA256()))
        payload = proof['payload']
        c.exact(payload, 'schema_version receipt_id cluster_id generation new_generation snapshot_sha256 inventory_sha256 export_sha256 observed_at_ms method nodes voter_count executor_count observations_sha256')
        c.uuid_field(payload['receipt_id'])
        for name in ('snapshot_sha256', 'inventory_sha256', 'export_sha256', 'observations_sha256'):
            c.digest_field(payload[name])
        check(payload['schema_version'] == 1 and payload['method'] == 'owned-host-isolation-v1', 'invalid_isolation_method')
        check({k: payload[k] for k in old_manifest.audience} == old_manifest.audience
              and payload['new_generation'] == new_manifest.generation
              and payload['snapshot_sha256'] == c.sha256(snapshot), 'isolation_binding_mismatch', 403)
        enrolled_count = snapshot['records']['control']['value'].get('member_count', 0)
        check(type(enrolled_count) is int and type(payload['executor_count']) is int
              and enrolled_count <= payload['executor_count'], 'incomplete_isolation', 403)
        check(payload['nodes'] == sorted(n['node_id'] for n in old_manifest.nodes)
              and type(payload['voter_count']) is int and payload['voter_count'] == 3
              and type(payload['executor_count']) is int and 1 <= payload['executor_count'] <= 32,
              'incomplete_isolation', 403)
        receipt = IsolationReceipt(c.encode(payload), c.sha256(proof), _RECEIPT)
        _receipt(receipt, snapshot, old_manifest, new_manifest, now_ms)
        return receipt
    except HAError:
        raise
    except Exception:
        raise HAError('invalid_isolation_signature', 403) from None


def _receipt(receipt, snapshot, old, new, at):
    check(type(receipt) is IsolationReceipt and receipt._proof is _RECEIPT, 'trusted_isolation_required', 403)
    payload = receipt.payload
    at = now_ms() if at is None else at
    check(type(at) is int and type(payload['observed_at_ms']) is int
          and 0 <= at - payload['observed_at_ms'] <= MAX_RECEIPT_AGE_MS, 'isolation_receipt_expired', 403)
    check(payload['observed_at_ms'] >= snapshot['created_at_ms'], 'snapshot_after_isolation')
    check(payload['snapshot_sha256'] == c.sha256(snapshot)
          and {k: payload[k] for k in old.audience} == old.audience
          and payload['new_generation'] == new.generation, 'isolation_binding_mismatch', 403)


def restore_records(snapshot, old_manifest, new_manifest):
    validate_snapshot(snapshot, old_manifest); _new_generation(old_manifest, new_manifest)
    records = {k: copy.deepcopy(v['value']) for k, v in snapshot['records'].items()
               if k != 'recovery/install'}
    control = records['control']
    control.update(**new_manifest.audience, manifest_sha256=c.sha256(new_manifest.value),
                   manifest_revision=new_manifest.revision, active=False,
                   nodes={n['node_id']: {'state': 'active', 'key_id': n['key_id']} for n in new_manifest.nodes},
                   membership_revision=control['membership_revision'] + 1,
                   revocation_revision=control['revocation_revision'] + 1,
                   recovery={'capacity_frozen': True, 'reason': 'snapshot_evidence_gap',
                             'source_generation': old_manifest.generation,
                             'snapshot_sha256': c.sha256(snapshot), 'source_revision': snapshot['revision']})
    for key, row in records.items():
        if key.startswith('operations/') and row.get('state') not in ('completed', 'failed', 'refused'):
            row.update(state='outcome_unknown', revoked=True, revision=row['revision'] + 1,
                       error_code='recovery_evidence_required')
        if key.startswith('members/'):
            # Old member keys can retrieve preserved evidence, but re-enrollment
            # and execution must use the new generation's explicit trust flow.
            row['state'] = 'recovery_fenced'
    return records


def _commit(store, comparisons, writes, witness_key, witness):
    try:
        committed, revision = store.txn(comparisons, writes)
    except HAError as exc:
        if exc.code != 'commit_unknown':
            raise
        observed, revision = store.read(witness_key)
        check(observed == witness, 'commit_unknown', 503)
        committed = True
    check(committed, 'restore_state_changed', 409)
    return revision


def _require_empty_namespace(store):
    from .store import b64
    prefix = store.prefix.encode()
    end = prefix[:-1] + bytes([prefix[-1] + 1])
    result = store._request('/v3/kv/range', {'key': b64(prefix), 'range_end': b64(end),
        'serializable': False, 'limit': 1}, read_only=True)
    check(result.get('kvs', []) == [] and not result.get('more', False), 'restore_target_not_empty', 409)


def install_restored(store, snapshot, old_manifest, new_manifest, receipt, *, now_ms=None):
    """Install only into an unused generation; interrupted chunks remain fenced.

    A repeat reconciles/resumes this exact install digest. It never recampaigns,
    reissues claims, replaces another install, or overwrites an active cluster.
    """
    _receipt(receipt, snapshot, old_manifest, new_manifest, now_ms)
    records = restore_records(snapshot, old_manifest, new_manifest)
    used_key = 'recovery/used/' + receipt.payload['receipt_id']
    check(used_key not in records, 'isolation_receipt_spent', 409)
    ordered = sorted(k for k in records if k != 'control')
    expected = {'receipt_id': receipt.payload['receipt_id'], 'receipt_sha256': receipt.digest,
                'snapshot_sha256': c.sha256(snapshot), 'manifest_sha256': c.sha256(new_manifest.value),
                'records_sha256': c.sha256(records), 'next_index': 0, 'complete': False, 'activated': False}
    rows = store.read_many(['control', 'leader', 'recovery/install'])
    existing = rows['recovery/install'][0]
    if existing is None:
        check(rows['control'][0] is None and rows['leader'][0] is None, 'restore_target_not_empty', 409)
        _require_empty_namespace(store)
        _commit(store, [('control', 'revision', 0), ('leader', 'revision', 0), ('recovery/install', 'revision', 0),
                        (used_key, 'revision', 0)],
                [('control', records['control'], None), ('recovery/install', expected, None),
                 (used_key, {'receipt_sha256': receipt.digest, 'generation': new_manifest.generation}, None)],
                'recovery/install', expected)
    while True:
        rows = store.read_many(['control', 'leader', 'recovery/install'])
        control, control_revision = rows['control']; progress, progress_revision = rows['recovery/install']
        check(isinstance(progress, dict) and all(progress.get(k) == expected[k] for k in (
            'receipt_id', 'receipt_sha256', 'snapshot_sha256', 'manifest_sha256', 'records_sha256')),
            'restore_target_not_empty', 409)
        check(not progress['activated'], 'restore_already_activated', 409)
        check(control == records['control'] and rows['leader'][0] is None, 'restore_state_changed', 409)
        if progress['complete']:
            return progress
        index = progress['next_index']
        check(type(index) is int and 0 <= index <= len(ordered), 'invalid_restore_progress')
        chunk = ordered[index:index + 12]
        next_progress = dict(progress, next_index=index + len(chunk), complete=index + len(chunk) == len(ordered))
        comparisons = [('control', 'revision', control_revision), ('leader', 'revision', 0),
                       ('recovery/install', 'revision', progress_revision)] + [(key, 'revision', 0) for key in chunk]
        writes = [(key, records[key], None) for key in chunk] + [('recovery/install', next_progress, None)]
        _commit(store, comparisons, writes, 'recovery/install', next_progress)


def activate_restored(store, snapshot, old_manifest, new_manifest, receipt, *, now_ms=None):
    _receipt(receipt, snapshot, old_manifest, new_manifest, now_ms)
    _new_generation(old_manifest, new_manifest)
    rows = store.read_many(['control', 'leader', 'recovery/install'])
    control, revision = rows['control']; progress, progress_revision = rows['recovery/install']
    check(isinstance(progress, dict) and progress.get('receipt_sha256') == receipt.digest
          and progress.get('manifest_sha256') == c.sha256(new_manifest.value)
          and progress.get('snapshot_sha256') == c.sha256(snapshot), 'restore_binding_mismatch', 403)
    check(not progress['activated'], 'restore_already_activated', 409)
    check(progress['complete'] and rows['leader'][0] is None and control['active'] is False
          and control.get('recovery', {}).get('capacity_frozen') is True, 'restore_incomplete', 409)
    control = dict(control, active=True)
    progress = dict(progress, activated=True)
    _commit(store, [('control', 'revision', revision), ('leader', 'revision', 0),
                    ('recovery/install', 'revision', progress_revision)],
            [('control', control, None), ('recovery/install', progress, None)], 'recovery/install', progress)
    return {'active': True, 'capacity_frozen': True, 'receipt_id': progress['receipt_id']}
