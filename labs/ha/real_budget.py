"""One durable qualification budget shared by runner, HUD, Code and Mobile.

Reservations are cumulative. Even a failed approval consumes its full allowance;
an unknown sender keeps the single active slot until exact signed reconciliation.
No network or process action is performed by this module.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid

LIMITS = {'approved_operations': 10, 'inferences': 20, 'native_effects': 10,
          'concurrent_operations': 1, 'operation_seconds': 180, 'inference_seconds': 60}
SURFACES = ('runner', 'hud', 'vscode', 'mobile')


class RehearsalRefused(ValueError):
    pass


def need(value, code):
    if not value:
        raise RehearsalRefused(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def uuid_value(value):
    try:
        need(isinstance(value, str) and str(uuid.UUID(value)) == value, 'invalid_identity')
    except (ValueError, TypeError):
        raise RehearsalRefused('invalid_identity') from None


def sha_value(value):
    need(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value), 'invalid_digest')


def private_directory(root, *, create=False):
    root = Path(root).absolute()
    need(root == root.resolve(), 'private_path_required')
    if create:
        root.mkdir(mode=0o700, exist_ok=False)
    info = root.lstat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
         'private_directory_required')
    return root


def read_private(path, maximum=1024 * 1024):
    path = Path(path).absolute()
    need(path == path.resolve(), 'private_path_required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
             and info.st_size <= maximum, 'private_file_required')
        return stream.read(maximum + 1)


def write_new(path, value):
    path = Path(path).absolute()
    private_directory(path.parent)
    raw = value if isinstance(value, bytes) else canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_new(path, value):
    """Atomically publish a complete claim without replacing an existing file."""
    path = Path(path).absolute(); private_directory(path.parent)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    write_new(temporary, value)
    try:
        # link is an atomic no-replace publication on the same filesystem.
        os.link(temporary, path, follow_symlinks=False)
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        temporary.unlink()


def validate_claim(claim, *, operation_id, client_nonce, review_digest, surface, run_id=None):
    fields = {'schema_version', 'run_id', 'claim_id', 'operation_id', 'client_nonce', 'review_digest',
              'surface', 'limits', 'reserved_at_ms', 'claim_sha256'}
    need(isinstance(claim, dict) and set(claim) == fields and type(claim['schema_version']) is int
         and claim['schema_version'] == 1, 'invalid_budget_claim')
    for key in ('run_id', 'claim_id', 'operation_id'):
        uuid_value(claim[key])
    sha_value(claim['review_digest']); sha_value(claim['claim_sha256'])
    need(claim['operation_id'] == operation_id and claim['client_nonce'] == client_nonce
         and claim['review_digest'] == review_digest and claim['surface'] == surface
         and (run_id is None or claim['run_id'] == run_id), 'budget_claim_changed')
    need(surface in SURFACES and isinstance(client_nonce, str) and 1 <= len(client_nonce) <= 200
         and type(claim['reserved_at_ms']) is int and claim['reserved_at_ms'] > 0
         and claim['limits'] == {'inferences': 2, 'native_effects': 1,
                                 'operation_seconds': 180, 'inference_seconds': 60}, 'invalid_budget_claim')
    need(digest({k: v for k, v in claim.items() if k != 'claim_sha256'}) == claim['claim_sha256'],
         'budget_claim_changed')
    return claim


class Budget:
    def __init__(self, root, *, run_id=None, create=False, clock_ms=None):
        self.root = private_directory(root)
        self.path = self.root / 'real-budget.sqlite3'
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        if create:
            uuid_value(run_id)
            write_new(self.path, b'')
            with self.connection() as db:
                db.executescript('''CREATE TABLE budget (singleton INTEGER PRIMARY KEY CHECK(singleton=1), run_id TEXT NOT NULL, limits_json TEXT NOT NULL);
                  CREATE TABLE reservation (claim_id TEXT PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
                    client_nonce TEXT NOT NULL UNIQUE, claim_json TEXT NOT NULL, state TEXT NOT NULL,
                    sender TEXT, receipt_sha256 TEXT, actual_inferences INTEGER, actual_native_effects INTEGER);
                  CREATE TABLE event (id INTEGER PRIMARY KEY, claim_id TEXT NOT NULL, kind TEXT NOT NULL, at_ms INTEGER NOT NULL, detail TEXT NOT NULL);''')
                db.execute('INSERT INTO budget VALUES(1,?,?)', (run_id, canonical(LIMITS).decode()))
        else:
            read_private(self.path, 16 * 1024 * 1024)
        with self.connection() as db:
            row = db.execute('SELECT run_id,limits_json FROM budget WHERE singleton=1').fetchone()
            need(row and json.loads(row[1]) == LIMITS and (run_id is None or row[0] == run_id), 'budget_identity_changed')
            self.run_id = row[0]

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db, claim_id, kind, detail):
        db.execute('INSERT INTO event(claim_id,kind,at_ms,detail) VALUES(?,?,?,?)',
                   (claim_id, kind, self.clock_ms(), canonical(detail).decode()))

    def reserve(self, *, operation_id, client_nonce, review_digest, surface):
        uuid_value(operation_id); sha_value(review_digest)
        need(surface in SURFACES and isinstance(client_nonce, str) and 1 <= len(client_nonce) <= 200,
             'invalid_budget_request')
        claim = {'schema_version': 1, 'run_id': self.run_id, 'claim_id': str(uuid.uuid4()),
                 'operation_id': operation_id, 'client_nonce': client_nonce, 'review_digest': review_digest,
                 'surface': surface, 'limits': {'inferences': 2, 'native_effects': 1,
                 'operation_seconds': 180, 'inference_seconds': 60}, 'reserved_at_ms': self.clock_ms()}
        claim['claim_sha256'] = digest(claim)
        with self.connection() as db:
            need(db.execute('SELECT 1 FROM reservation WHERE operation_id=? OR client_nonce=?',
                            (operation_id, client_nonce)).fetchone() is None, 'operation_already_reserved')
            need(db.execute("SELECT 1 FROM reservation WHERE state!='settled'").fetchone() is None, 'unresolved_operation_retained')
            used = db.execute('SELECT count(*) FROM reservation').fetchone()[0]
            need(used < 10 and used * 2 + 2 <= 20, 'real_budget_exhausted')
            db.execute('INSERT INTO reservation(claim_id,operation_id,client_nonce,claim_json,state) VALUES(?,?,?,?,?)',
                       (claim['claim_id'], operation_id, client_nonce, canonical(claim).decode(), 'reserved'))
            self._event(db, claim['claim_id'], 'reserved', {'cumulative_operations': used + 1,
                                                        'cumulative_inferences': (used + 1) * 2,
                                                        'cumulative_native_effects': used + 1})
        return claim

    def claim_send(self, claim, *, surface):
        validate_claim(claim, operation_id=claim['operation_id'], client_nonce=claim['client_nonce'],
                       review_digest=claim['review_digest'], surface=surface, run_id=self.run_id)
        with self.connection() as db:
            row = db.execute('SELECT claim_json,state FROM reservation WHERE claim_id=?', (claim['claim_id'],)).fetchone()
            need(row and json.loads(row[0]) == claim and row[1] == 'reserved', 'approval_send_already_claimed')
            db.execute("UPDATE reservation SET state='send_claimed',sender=? WHERE claim_id=?", (surface, claim['claim_id']))
            self._event(db, claim['claim_id'], 'send_claimed', {'surface': surface})
        return claim

    def unknown(self, claim_id):
        uuid_value(claim_id)
        with self.connection() as db:
            row = db.execute('SELECT state FROM reservation WHERE claim_id=?', (claim_id,)).fetchone()
            need(row and row[0] in ('send_claimed', 'unknown'), 'invalid_budget_transition')
            db.execute("UPDATE reservation SET state='unknown' WHERE claim_id=?", (claim_id,))
            self._event(db, claim_id, 'unknown', {'slot_retained': True})

    def refused(self, claim, *, evidence_sha256):
        """Terminal state for a definitive pre-dispatch refusal proven by an independent
        status read. The reservation still counts in full; only the active slot is released.
        Callers must have verified review_pending, attempt_count 0 and may_have_executed false."""
        sha_value(evidence_sha256)
        with self.connection() as db:
            row = db.execute('SELECT claim_json,state FROM reservation WHERE claim_id=?', (claim['claim_id'],)).fetchone()
            need(row and json.loads(row[0]) == claim and row[1] == 'send_claimed', 'invalid_budget_transition')
            db.execute("UPDATE reservation SET state='settled',receipt_sha256=?,actual_inferences=0,actual_native_effects=0 WHERE claim_id=?",
                       (evidence_sha256, claim['claim_id']))
            self._event(db, claim['claim_id'], 'refused_pre_dispatch', {'evidence_sha256': evidence_sha256,
                                                                       'counted_in_full': True})

    def settle(self, claim, *, receipt_sha256, inferences, native_effects):
        """Called only after the runner verifies the original result+ACK packet."""
        sha_value(receipt_sha256)
        need(type(inferences) is int and 0 <= inferences <= 2 and type(native_effects) is int
             and 0 <= native_effects <= 1, 'observed_effect_bound_exceeded')
        with self.connection() as db:
            row = db.execute('SELECT claim_json,state FROM reservation WHERE claim_id=?', (claim['claim_id'],)).fetchone()
            need(row and json.loads(row[0]) == claim and row[1] in ('send_claimed', 'unknown'), 'invalid_budget_transition')
            db.execute("UPDATE reservation SET state='settled',receipt_sha256=?,actual_inferences=?,actual_native_effects=? WHERE claim_id=?",
                       (receipt_sha256, inferences, native_effects, claim['claim_id']))
            self._event(db, claim['claim_id'], 'settled', {'receipt_sha256': receipt_sha256,
                                                        'actual_inferences': inferences, 'actual_native_effects': native_effects})

    def snapshot(self):
        with self.connection() as db:
            rows = db.execute('SELECT claim_json,state,sender,receipt_sha256,actual_inferences,actual_native_effects FROM reservation ORDER BY rowid').fetchall()
        return {'schema_version': 1, 'run_id': self.run_id, 'limits': LIMITS,
                'reserved': {'operations': len(rows), 'inferences': len(rows) * 2, 'native_effects': len(rows)},
                'reservations': [{'claim': json.loads(r[0]), 'state': r[1], 'sender': r[2], 'receipt_sha256': r[3],
                                  'actual_inferences': r[4], 'actual_native_effects': r[5]} for r in rows]}
