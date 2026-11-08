"""Member-owned, durable and fresh single-use model/tool admission boundary."""
from contextlib import contextmanager
import os
import secrets
import sqlite3
import stat
import time
import uuid

from .. import protected_contract as c
from ..protected_runtime import private_directory, private_write
from .config import check, HAError
from .operations import validate_admission
from .signatures import verify
from .effect import CURRENT, EffectScope


class MemberAdmission:
    def __init__(self, home, manifest, member, *, monotonic=time.monotonic, wall=time.time):
        check(manifest.anchor_key_id is not None, 'unverified_cluster_manifest', 403)
        c.validate_binding(member, 'member')
        self.home = private_directory(home)
        self.path = self.home / 'ha-admission.sqlite3'
        self.manifest, self.member = manifest, dict(member)
        self.monotonic, self.wall = monotonic, wall
        self.incarnation = str(uuid.uuid4())
        if not self.path.exists() and not self.path.is_symlink():
            private_write(self.path, b'')
        with self._connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS ha_identity (id INTEGER PRIMARY KEY CHECK(id=1), binding TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ha_admission (
                  nonce TEXT PRIMARY KEY, operation_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                  kind TEXT NOT NULL, ordinal INTEGER NOT NULL, incarnation TEXT NOT NULL,
                  request TEXT NOT NULL, state TEXT NOT NULL, proof_hash TEXT,
                  UNIQUE(operation_id, kind, ordinal));
            ''')
            binding = c.encode({'audience': manifest.audience, 'member': self.member}).decode()
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT binding FROM ha_identity WHERE id=1').fetchone()
            if row is None:
                conn.execute('INSERT INTO ha_identity VALUES(1,?)', (binding,))
            else:
                check(row[0] == binding, 'member_journal_binding_changed', 409)
            conn.commit()

    @contextmanager
    def _connection(self):
        info = self.path.lstat()
        check(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
              'unsafe_member_journal', 503)
        conn = sqlite3.connect(str(self.path), timeout=1, isolation_level=None)
        try:
            conn.execute('PRAGMA synchronous=FULL')
            yield conn
        finally:
            conn.close()

    def begin(self, context, kind, ordinal, request_digest):
        c.exact(context, 'operation_id attempt_id approval_digest')
        request = {**self.manifest.audience, **context, 'kind': kind, 'ordinal': ordinal,
                   'request_digest': request_digest, 'member_incarnation': self.incarnation,
                   'nonce': secrets.token_hex(32)}
        validate_admission(request)
        # Challenge timing includes synchronous journal I/O and the network trip.
        started = (self.monotonic(), self.wall())
        try:
            with self._connection() as conn:
                conn.execute('BEGIN IMMEDIATE')
                count = conn.execute('SELECT COUNT(*) FROM ha_admission').fetchone()[0]
                check(count < self.manifest.limits['max_operations'] * 3, 'state_capacity', 503)
                conn.execute('INSERT INTO ha_admission VALUES(?,?,?,?,?,?,?,?,NULL)',
                    (request['nonce'], request['operation_id'], request['attempt_id'], kind, ordinal,
                     self.incarnation, c.encode(request).decode(), 'pending'))
                conn.commit()
        except sqlite3.IntegrityError:
            raise HAError('admission_spent', 409) from None
        return request, started

    def fresh(self, started):
        elapsed = self.monotonic() - started[0]
        wall_elapsed = self.wall() - started[1]
        check(0 <= elapsed * 1000 <= self.manifest.limits['admission_ms'], 'admission_expired', 409)
        check(abs(wall_elapsed - elapsed) * 1000 <= self.manifest.limits['clock_uncertainty_ms'],
              'clock_uncertain', 409)
        return int(self.manifest.limits['admission_ms'] - elapsed * 1000)

    def consume(self, request, proof, started):
        self.fresh(started)
        try:
            node = self.manifest.node(proof['payload']['claim']['leader']['node_id'])
            payload = verify(proof, node['certificate'], 'admission')
            c.exact(payload, 'claim commit_revision')
            claim = payload['claim']
            c.exact(claim, 'request member_sha256 leader epoch state')
            c.exact(claim['leader'], 'node_id incarnation generation election_nonce')
            c.uuid_field(claim['leader']['incarnation']); c.digest_field(claim['leader']['election_nonce'])
            check(claim['leader']['generation'] == self.manifest.generation
                  and claim['member_sha256'] == c.sha256(self.member)
                  and claim['request'] == request and claim['state'] == 'committed'
                  and request['member_incarnation'] == self.incarnation, 'admission_binding_mismatch', 403)
            check(type(claim['epoch']) is int and type(payload['commit_revision']) is int
                  and 0 < claim['epoch'] < payload['commit_revision'] <= 2**53 - 1,
                  'admission_revision_mismatch', 403)
        except HAError:
            raise
        except Exception:
            raise HAError('invalid_admission_receipt', 403) from None
        with self._connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            result = conn.execute('''UPDATE ha_admission SET state='consumed',proof_hash=?
                WHERE nonce=? AND incarnation=? AND request=? AND state='pending' ''',
                (c.sha256(proof), request['nonce'], self.incarnation, c.encode(request).decode()))
            check(result.rowcount == 1, 'admission_spent', 409)
            conn.commit()
        self.fresh(started)

    def _terminal(self, request, state):
        with self._connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute("UPDATE ha_admission SET state=? WHERE nonce=? AND state IN ('pending','consumed')",
                         (state, request['nonce']))
            conn.commit()

    async def run(self, context, kind, ordinal, request_digest, send, invoke):
        """Single attempt. A failed or lost claim is never replaced or retried."""
        check(callable(send) and callable(invoke), 'ha_runtime_unqualified', 503)
        request, started = self.begin(context, kind, ordinal, request_digest)
        try:
            proof = await send(request)
            self.consume(request, proof, started)
            # No intervening await between this check and entering the exact
            # trusted effect callback. A process pause is measured at this gate.
            self.fresh(started)
            scope = EffectScope(kind, lambda: self.fresh(started))
            token = CURRENT.set(scope)
            try:
                result = await invoke()
            finally:
                scope.active = False
                CURRENT.reset(token)
            self._terminal(request, 'finished')
            return result
        except BaseException:
            # An unavailable journal remains spent/pending, never reset. Preserve
            # the original failure while still trying to record uncertainty.
            try:
                self._terminal(request, 'unknown')
            except Exception:
                pass
            raise
