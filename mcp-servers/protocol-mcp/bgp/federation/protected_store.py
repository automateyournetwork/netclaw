"""Additive, durable execution claims in the installation federation database."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid
from .protected_contract import ProtectedError, encode, require

SCHEMA = '''
CREATE TABLE IF NOT EXISTS protected_operation (
 side TEXT NOT NULL, operation_id TEXT NOT NULL, client_nonce TEXT,
 owner_subject TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 review TEXT NOT NULL, review_digest TEXT NOT NULL, candidate_digest TEXT,
 approval TEXT, approval_digest TEXT, approval_nonce TEXT, approval_id TEXT,
 attempt_id TEXT, receipt TEXT, receipt_digest TEXT, ack TEXT,
 effect_authorization TEXT, tool_evidence TEXT, executor_result TEXT,
 trust_snapshot TEXT NOT NULL, audit_refs TEXT NOT NULL DEFAULT '{}',
 revoked INTEGER NOT NULL DEFAULT 0, effect_claimed INTEGER NOT NULL DEFAULT 0, effect_finished INTEGER NOT NULL DEFAULT 0,
 ack_pending INTEGER NOT NULL DEFAULT 0, error_code TEXT, started_ms INTEGER,
 PRIMARY KEY(side, operation_id), UNIQUE(side, client_nonce, owner_subject),
 UNIQUE(side, approval_nonce), UNIQUE(side, approval_id), UNIQUE(side, attempt_id)
);
CREATE TABLE IF NOT EXISTS protected_combined (
 parent_id TEXT PRIMARY KEY,client_nonce TEXT NOT NULL,owner_subject TEXT NOT NULL,
 principal TEXT NOT NULL,border TEXT NOT NULL,request_digest TEXT NOT NULL,
 created_at_ms INTEGER NOT NULL,expires_at_ms INTEGER NOT NULL,cancelled INTEGER NOT NULL DEFAULT 0,
 UNIQUE(owner_subject,client_nonce)
);
CREATE TABLE IF NOT EXISTS protected_combined_child (
 parent_id TEXT NOT NULL,child_index INTEGER NOT NULL CHECK(child_index IN (0,1)),
 family INTEGER NOT NULL CHECK(family IN (4,6)),operation_id TEXT NOT NULL UNIQUE,
 PRIMARY KEY(parent_id,child_index),UNIQUE(parent_id,family)
);
CREATE TABLE IF NOT EXISTS protected_model_call (
 operation_id TEXT NOT NULL, ordinal INTEGER NOT NULL, claimed_ms INTEGER NOT NULL,
 PRIMARY KEY(operation_id, ordinal)
);
'''
JSON_FIELDS = frozenset('review approval receipt ack effect_authorization tool_evidence executor_result trust_snapshot audit_refs'.split())
FIELDS = frozenset('state review review_digest candidate_digest approval approval_digest approval_nonce approval_id attempt_id receipt receipt_digest ack effect_authorization tool_evidence executor_result trust_snapshot audit_refs revoked effect_claimed effect_finished ack_pending error_code started_ms'.split())


class ProtectedStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        path = Path(db_path)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink():
            raise ProtectedError('unsafe_store')
        if path.exists():
            require(path.is_file() and path.stat().st_uid == os.getuid(), 'unsafe_store')
        else:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        # The federation DB may predate the protected profile; restrict its mode.
        os.chmod(path, 0o600)
        with self.connection() as conn:
            conn.executescript(SCHEMA)
            columns = {row[1] for row in conn.execute('PRAGMA table_info(protected_operation)')}
            if 'effect_finished' not in columns:
                conn.execute('ALTER TABLE protected_operation ADD COLUMN effect_finished INTEGER NOT NULL DEFAULT 0')

    @contextmanager
    def connection(self):
        info = os.lstat(self.db_path)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'unsafe_store')
        conn = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA synchronous=FULL')
        conn.execute('PRAGMA busy_timeout=15000')
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        with self.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    @staticmethod
    def unpack(row):
        if row is None:
            return None
        result = dict(row)
        for key in JSON_FIELDS:
            if result.get(key) is not None:
                result[key] = json.loads(result[key])
        return result

    def get(self, side, operation_id=None, *, client_nonce=None, owner_subject=None):
        with self.connection() as conn:
            if operation_id:
                row = conn.execute('SELECT * FROM protected_operation WHERE side=? AND operation_id=?', (side, operation_id)).fetchone()
            else:
                row = conn.execute('SELECT * FROM protected_operation WHERE side=? AND client_nonce=? AND owner_subject=?', (side, client_nonce, owner_subject)).fetchone()
            return self.unpack(row)

    def create(self, side, operation_id, *, owner_subject, review, review_digest, trust_snapshot,
               state='review_pending', client_nonce=None, candidate_digest=None, approval=None):
        values = dict(side=side, operation_id=operation_id, owner_subject=owner_subject, review=review,
                      review_digest=review_digest, trust_snapshot=trust_snapshot, state=state,
                      client_nonce=client_nonce, candidate_digest=candidate_digest)
        if approval:
            from .protected_contract import digest
            p = approval['payload']
            values.update(approval=approval, approval_digest=digest(approval['schema'], p), approval_nonce=p['nonce'], approval_id=p['approval_id'])
        serialized = {key: encode(value).decode() if key in JSON_FIELDS else value for key, value in values.items()}
        try:
            with self.transaction() as conn:
                conn.execute('INSERT INTO protected_operation (' + ','.join(serialized) + ') VALUES (' + ','.join('?' for _ in serialized) + ')', tuple(serialized.values()))
        except sqlite3.IntegrityError:
            raise ProtectedError('operation_conflict', 409) from None
        return self.get(side, operation_id)

    @staticmethod
    def _combined(conn, *, parent_id=None, client_nonce=None, owner_subject=None):
        if parent_id:
            row = conn.execute('SELECT * FROM protected_combined WHERE parent_id=?', (parent_id,)).fetchone()
        else:
            row = conn.execute('SELECT * FROM protected_combined WHERE client_nonce=? AND owner_subject=?',
                               (client_nonce, owner_subject)).fetchone()
        if row is None:
            return None
        value = dict(row)
        value['principal'], value['border'] = json.loads(value['principal']), json.loads(value['border'])
        value['children'] = [dict(r) for r in conn.execute(
            'SELECT operation_id,family FROM protected_combined_child WHERE parent_id=? ORDER BY child_index',
            (value['parent_id'],))]
        require(len(value['children']) == 2, 'combined_store_corrupt', 503)
        return value

    def get_combined(self, **selector):
        with self.connection() as conn:
            return self._combined(conn, **selector)

    def combined_for_child(self, operation_id):
        with self.connection() as conn:
            row = conn.execute('SELECT parent_id FROM protected_combined_child WHERE operation_id=?',
                               (operation_id,)).fetchone()
            return self._combined(conn, parent_id=row['parent_id']) if row else None

    def create_combined(self, parent, rows):
        require(len(rows) == len(parent['children']) == 2, 'combined_children_required')
        with self.transaction() as conn:
            old = self._combined(conn, client_nonce=parent['client_nonce'], owner_subject=parent['principal']['subject'])
            if old:
                require(old['principal'] == parent['principal'] and old['border'] == parent['border']
                        and old['request_digest'] == parent['request_digest'], 'client_nonce_conflict', 409)
                return old
            conn.execute('INSERT INTO protected_combined VALUES(?,?,?,?,?,?,?,?,?)',
                         (parent['parent_id'], parent['client_nonce'], parent['principal']['subject'],
                          encode(parent['principal']).decode(), encode(parent['border']).decode(),
                          parent['request_digest'], parent['created_at_ms'], parent['expires_at_ms'], 0))
            for index, row in enumerate(rows):
                serialized = {k: encode(v).decode() if k in JSON_FIELDS else v for k, v in row.items()}
                conn.execute('INSERT INTO protected_operation (' + ','.join(serialized) + ') VALUES ('
                             + ','.join('?' for _ in serialized) + ')', tuple(serialized.values()))
                conn.execute('INSERT INTO protected_combined_child VALUES(?,?,?,?)',
                             (parent['parent_id'], index, parent['children'][index]['family'], row['operation_id']))
            return self._combined(conn, parent_id=parent['parent_id'])

    @staticmethod
    def _combined_transition(conn, operation_id, state, now_ms=None):
        row = conn.execute('SELECT p.*,c.child_index FROM protected_combined p JOIN protected_combined_child c '
                           'ON p.parent_id=c.parent_id WHERE c.operation_id=?', (operation_id,)).fetchone()
        if row is None:
            return
        require(not row['cancelled'], 'combined_cancelled', 409)
        if now_ms is not None:
            require(row['created_at_ms'] <= now_ms < row['expires_at_ms'], 'combined_expired', 403)
        if state in ('approved', 'refused') and row['child_index']:
            previous = conn.execute("SELECT o.state FROM protected_combined_child c JOIN protected_operation o "
                                    "ON o.operation_id=c.operation_id AND o.side='border' "
                                    "WHERE c.parent_id=? AND c.child_index=0", (row['parent_id'],)).fetchone()
            require(previous is not None and previous['state'] != 'review_pending', 'combined_previous_decision_pending', 409)

    def cancel_combined(self, parent_id, principal):
        with self.transaction() as conn:
            parent = self._combined(conn, parent_id=parent_id)
            require(parent is not None and parent['principal'] == principal, 'combined_not_found', 404)
            conn.execute('UPDATE protected_combined SET cancelled=1 WHERE parent_id=?', (parent_id,))
            for child in parent['children']:
                conn.execute("UPDATE protected_operation SET revoked=1,revision=revision+1 WHERE side='border' "
                             "AND operation_id=? AND revoked=0", (child['operation_id'],))
            return self._combined(conn, parent_id=parent_id)

    def transition(self, side, operation_id, expected, **changes):
        require(set(changes) <= FIELDS, 'invalid_transition')
        states = [expected] if isinstance(expected, str) else list(expected)
        require(bool(states))
        values = {key: encode(value).decode() if key in JSON_FIELDS and value is not None else value for key, value in changes.items()}
        sets = ','.join(key + '=?' for key in values) + ',revision=revision+1'
        with self.transaction() as conn:
            prior = self.unpack(conn.execute('SELECT * FROM protected_operation WHERE side=? AND operation_id=?', (side, operation_id)).fetchone())
            require(prior is not None and prior['state'] in states, 'state_conflict', 409)
            allowed = {
                'border': {'review_pending': {'approved','refused'}, 'approved': {'dispatch_pending','refused','reconciliation_required'},
                           'dispatch_pending': {'member_admitted','reconciliation_required','completed','refused','failed'},
                           'member_admitted': {'result_pending','reconciliation_required','completed','refused','failed'},
                           'result_pending': {'reconciliation_required','completed','refused','failed'},
                           'reconciliation_required': {'member_admitted','completed','refused','failed'},
                           'completed': set(), 'failed': set(), 'refused': set()},
                'member': {'admitted': {'refused','outcome_unknown'}, 'executor_claimed': {'audit_pending','outcome_unknown'},
                           'effect_claimed': {'audit_pending','outcome_unknown'}, 'audit_pending': {'result_ready'},
                           'result_ready': {'acknowledged'}, 'acknowledged': set(), 'outcome_unknown': set(), 'refused': set()}}
            next_state = changes.get('state', prior['state'])
            if side == 'border' and ((prior['state'] == 'review_pending' and next_state in ('approved','refused'))
                    or (prior['state'] == 'approved' and next_state == 'dispatch_pending')):
                now = (changes.get('approval') or {}).get('payload', {}).get('issued_at_ms')
                self._combined_transition(conn, operation_id, next_state, now)

            proven_recovery = side == 'member' and prior['state'] == 'outcome_unknown' and prior['effect_finished'] == 1 and next_state == 'audit_pending'
            require(proven_recovery or next_state == prior['state'] or next_state in allowed[side].get(prior['state'], set()), 'irreversible_state', 409)
            for field in ('attempt_id','approval','approval_digest','approval_nonce','approval_id','receipt','receipt_digest','ack',
                          'effect_authorization','tool_evidence','executor_result'):
                if prior[field] is not None and field in changes:
                    require(changes[field] == prior[field], 'immutable_evidence', 409)
            for field in ('review','review_digest','trust_snapshot','candidate_digest'):
                if field in changes: require(changes[field] == prior[field], 'immutable_review', 409)
            for field in ('effect_claimed','effect_finished','revoked'):
                if field in changes: require(type(changes[field]) is int and changes[field] in (0,1) and changes[field] >= prior[field], 'spent_authority', 409)
            try:
                cur = conn.execute('UPDATE protected_operation SET ' + sets + ' WHERE side=? AND operation_id=? AND state IN (' + ','.join('?' for _ in states) + ')', tuple(values.values()) + (side, operation_id, *states))
            except sqlite3.IntegrityError:
                raise ProtectedError('operation_conflict', 409) from None
            require(cur.rowcount == 1, 'state_conflict', 409)
        return self.get(side, operation_id)

    def complete_known_netbox_failure(self, verified, audit_ref):
        """One atomic native recovery; no caller-supplied terminal or new claim."""
        from .protected_failure_recovery import VerifiedFailure, authority_digest
        require(isinstance(verified, VerifiedFailure) and isinstance(verified.proof, dict), 'failure_proof_required')
        proof = verified.proof
        require(proof.get('kind') == 'native_netbox_http_authorization_response'
                and type(proof.get('http_status')) is int and proof['http_status'] in (401, 403)
                and proof.get('http_requests') == proof.get('mcp_calls') == 1
                and isinstance(audit_ref, str) and 0 < len(audit_ref) <= 200, 'failure_proof_required')
        with self.transaction() as conn:
            row = self.unpack(conn.execute("SELECT * FROM protected_operation WHERE side='member' AND operation_id=?",
                                           (proof['operation_id'],)).fetchone())
            require(row is not None and row['state'] == 'outcome_unknown'
                    and row['revision'] == proof['original_revision']
                    and row['attempt_id'] == proof['attempt_id'] and row['approval_digest'] == proof['approval_sha256']
                    and row['review_digest'] == proof['review_sha256'] and authority_digest(row) == proof['authority_sha256']
                    and row['error_code'] == proof['original_error_code']
                    and row['effect_claimed'] == 1 and row['effect_finished'] == 0
                    and all(row[key] is None for key in ('receipt', 'receipt_digest', 'ack', 'tool_evidence', 'executor_result')),
                    'failure_state_conflict', 409)
            verified.recheck()
            terminal = {'output': {}, 'tool_evidence': None, 'usage': {'available': False},
                        'effective_model_profile': row['review']['model_profile'],
                        'outcome': 'failed', 'effect_status': 'finished',
                        'error_code': 'native_netbox_http_' + str(proof['http_status']),
                        'failure_recovery': proof}
            audit_refs = dict(row['audit_refs'], failure_recovery=audit_ref)
            # Finished means this denied read attempt has a definite terminal
            # response. It does not fabricate successful MCP/object evidence.
            changed = conn.execute("UPDATE protected_operation SET state='audit_pending',effect_finished=1,"
                "executor_result=?,audit_refs=?,revision=revision+1 WHERE side='member' AND operation_id=? "
                "AND state='outcome_unknown' AND revision=?",
                (encode(terminal).decode(), encode(audit_refs).decode(), proof['operation_id'], proof['original_revision']))
            require(changed.rowcount == 1, 'failure_state_conflict', 409)
        return self.get('member', proof['operation_id'])

    def claim_executor(self, operation_id, now_ms, *, attempt_id=None):
        from .protected_contract import uuid_field
        attempt = attempt_id or str(uuid.uuid4())
        uuid_field(attempt)
        with self.transaction() as conn:
            cur = conn.execute("UPDATE protected_operation SET state='executor_claimed',attempt_id=?,started_ms=?,revision=revision+1 WHERE side='member' AND operation_id=? AND state='admitted' AND revoked=0 AND attempt_id IS NULL", (attempt, now_ms, operation_id))
            require(cur.rowcount == 1, 'executor_already_claimed', 409)
        return self.get('member', operation_id)

    def claim_effect(self, operation_id, authorization):
        with self.transaction() as conn:
            cur = conn.execute("UPDATE protected_operation SET state='effect_claimed',effect_claimed=1,effect_authorization=?,revision=revision+1 WHERE side='member' AND operation_id=? AND state='executor_claimed' AND revoked=0 AND effect_claimed=0", (encode(authorization).decode(), operation_id))
            require(cur.rowcount == 1, 'effect_already_claimed', 409)
        return self.get('member', operation_id)

    def authorize_effect(self, operation_id, binding):
        with self.transaction() as conn:
            row = self.unpack(conn.execute("SELECT * FROM protected_operation WHERE side='border' AND operation_id=?", (operation_id,)).fetchone())
            require(row is not None, 'operation_not_found', 404)
            if row['effect_authorization'] is not None:
                require(row['effect_authorization'] == binding, 'effect_binding_conflict', 409)
                return row['effect_authorization']
            require(not row['revoked'] and row['state'] in ('dispatch_pending', 'member_admitted', 'result_pending', 'reconciliation_required'), 'operation_revoked', 403)
            conn.execute("UPDATE protected_operation SET effect_authorization=?,revision=revision+1 WHERE side='border' AND operation_id=?", (encode(binding).decode(), operation_id))
        return binding

    def revoke(self, side, operation_id):
        with self.transaction() as conn:
            conn.execute('UPDATE protected_operation SET revoked=1,revision=revision+1 WHERE side=? AND operation_id=?', (side, operation_id))
        return self.get(side, operation_id)

    def claim_model_call(self, operation_id, now_ms, maximum=2):
        require(maximum == 2)
        with self.transaction() as conn:
            row = conn.execute("SELECT state,revoked FROM protected_operation WHERE side='member' AND operation_id=?", (operation_id,)).fetchone()
            require(row is not None and row['state'] in ('executor_claimed', 'effect_claimed') and not row['revoked'], 'model_call_refused', 403)
            count = conn.execute('SELECT count(*) FROM protected_model_call WHERE operation_id=?', (operation_id,)).fetchone()[0]
            require(count < maximum, 'model_call_limit', 403)
            conn.execute('INSERT INTO protected_model_call VALUES(?,?,?)', (operation_id, count + 1, now_ms))
        return count + 1

    def recover(self):
        with self.transaction() as conn:
            # Claims are tombstones. Never restart a provider or integration worker.
            conn.execute("UPDATE protected_operation SET state='outcome_unknown',error_code='interrupted',revision=revision+1 WHERE side='member' AND state IN ('executor_claimed','effect_claimed') AND receipt IS NULL")
            conn.execute("UPDATE protected_operation SET state='reconciliation_required',error_code='dispatch_interrupted',revision=revision+1 WHERE side='border' AND state IN ('approved','dispatch_pending','member_admitted','result_pending') AND ack IS NULL")
