"""Native-owned single-owner tickets and sessions; no browser-selected identity."""
from contextlib import contextmanager
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import threading
import time
import uuid
from .protected_contract import ProtectedError, decode, encode, exact, require, validate_principal

SCHEMA = '''
CREATE TABLE IF NOT EXISTS owner_meta(id INTEGER PRIMARY KEY CHECK(id=1),installation_id TEXT NOT NULL,generation INTEGER NOT NULL,principal_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS owner_ticket(ticket_hash TEXT PRIMARY KEY,generation INTEGER NOT NULL,expires_ms INTEGER NOT NULL,consumed_ms INTEGER);
CREATE TABLE IF NOT EXISTS owner_session(session_hash TEXT PRIMARY KEY,generation INTEGER NOT NULL,csrf_token TEXT NOT NULL,created_ms INTEGER NOT NULL,expires_ms INTEGER NOT NULL,last_seen_ms INTEGER NOT NULL,revoked_ms INTEGER);
'''


def private_directory(path, create=False):
    path = Path(path)
    if create:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'unsafe_private_directory', 503)
    return path


def private_file(path, max_bytes=1024 * 1024):
    path = Path(path)
    private_directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077 and info.st_size <= max_bytes, 'unsafe_private_file', 503)
        return stream.read()


def write_private(path, value):
    path = Path(path)
    private_directory(path.parent, True)
    if path.exists() or path.is_symlink():
        private_file(path)
    temporary = path.with_name(path.name + '.' + str(uuid.uuid4()) + '.tmp')
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(value if isinstance(value, bytes) else encode(value))
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if temporary.exists(): temporary.unlink()


def token_hash(token):
    require(isinstance(token, str) and len(token) == 43 and all(c.isalnum() or c in '-_' for c in token) and token.isascii(), 'invalid_session', 401)
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class OwnerAuthority:
    def __init__(self, state_dir, installation_id, *, clock_ms=None):
        self.directory = Path(state_dir)
        self.installation_id = installation_id
        self.db_path = self.directory / 'protected-owner.sqlite'
        self.lock_path = self.directory / 'protected-owner.lock'
        self.now = clock_ms or (lambda: int(time.time() * 1000))
        self._thread_lock = threading.RLock()

    @contextmanager
    def locked(self, *, initialize=False):
        private_directory(self.directory, initialize)
        with self._thread_lock:
            fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'unsafe_owner_lock', 503)
                fcntl.flock(fd, fcntl.LOCK_EX)
                if not self.db_path.exists() and initialize:
                    database_fd = os.open(self.db_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    os.close(database_fd)
                private_file(self.db_path, 64 * 1024 * 1024)
                conn = sqlite3.connect(self.db_path, isolation_level=None, timeout=15)
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA synchronous=FULL')
                if initialize: conn.executescript(SCHEMA)
                try:
                    yield conn
                finally:
                    conn.close()
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)

    def _meta(self, conn):
        row = conn.execute('SELECT * FROM owner_meta WHERE id=1').fetchone()
        require(row is not None and row['installation_id'] == self.installation_id, 'owner_uninitialized', 503)
        return row

    def init(self, display_name, *, subject=None):
        principal = {'issuer': 'local', 'subject': subject or str(uuid.uuid4()), 'display_name': display_name, 'roles': ['owner']}
        validate_principal(principal)
        with self.locked(initialize=True) as conn:
            row = conn.execute('SELECT * FROM owner_meta WHERE id=1').fetchone()
            if row:
                require(row['installation_id'] == self.installation_id, 'foreign_owner', 403)
                return decode(row['principal_json'])
            conn.execute('INSERT INTO owner_meta VALUES(1,?,?,?)', (self.installation_id, 1, encode(principal).decode()))
        return principal

    def ticket(self, *, ttl_ms=600000):
        require(type(ttl_ms) is int and 0 < ttl_ms <= 600000)
        raw = secrets.token_urlsafe(32)
        with self.locked() as conn:
            meta = self._meta(conn)
            conn.execute('INSERT INTO owner_ticket VALUES(?,?,?,NULL)', (token_hash(raw), meta['generation'], self.now() + ttl_ms))
        return raw

    def revoke(self):
        with self.locked() as conn:
            meta = self._meta(conn)
            conn.execute('BEGIN IMMEDIATE')
            try:
                conn.execute('UPDATE owner_meta SET generation=generation+1 WHERE id=1')
                conn.execute('UPDATE owner_session SET revoked_ms=? WHERE revoked_ms IS NULL', (self.now(),))
                conn.commit()
            except BaseException:
                conn.rollback(); raise
            return {'revoked': True, 'auth_generation': meta['generation'] + 1}

    def _projection(self, meta, row):
        return {'principal': decode(meta['principal_json']), 'auth_generation': meta['generation'],
                'session_hash': row['session_hash'], 'csrf_token': row['csrf_token'],
                'expires_ms': row['expires_ms'], 'installation_id': self.installation_id}

    def login(self, ticket):
        hashed = token_hash(ticket)
        with self.locked() as conn:
            meta, now = self._meta(conn), self.now()
            conn.execute('BEGIN IMMEDIATE')
            try:
                ticket_row = conn.execute('SELECT * FROM owner_ticket WHERE ticket_hash=?', (hashed,)).fetchone()
                require(ticket_row is not None and ticket_row['generation'] == meta['generation'] and ticket_row['consumed_ms'] is None and now < ticket_row['expires_ms'] and now >= ticket_row['expires_ms'] - 600000, 'invalid_ticket', 401)
                conn.execute('UPDATE owner_ticket SET consumed_ms=? WHERE ticket_hash=? AND consumed_ms IS NULL', (now, hashed))
                cookie, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                session_hash = token_hash(cookie)
                conn.execute('INSERT INTO owner_session VALUES(?,?,?,?,?,?,NULL)', (session_hash, meta['generation'], csrf, now, now + 8 * 60 * 60 * 1000, now))
                row = conn.execute('SELECT * FROM owner_session WHERE session_hash=?', (session_hash,)).fetchone()
                conn.commit()
            except BaseException:
                conn.rollback(); raise
            return dict(self._projection(meta, row), cookie=cookie)

    def _active(self, conn, session_hash, *, refresh=True):
        meta, now = self._meta(conn), self.now()
        row = conn.execute('SELECT * FROM owner_session WHERE session_hash=?', (session_hash,)).fetchone()
        require(row is not None and row['generation'] == meta['generation'] and row['revoked_ms'] is None and row['created_ms'] <= row['last_seen_ms'] <= now < row['expires_ms'] and now - row['last_seen_ms'] < 30 * 60 * 1000, 'invalid_session', 401)
        if refresh:
            conn.execute('UPDATE owner_session SET last_seen_ms=? WHERE session_hash=?', (now, session_hash))
        return self._projection(meta, row)

    def session(self, cookie):
        with self.locked() as conn:
            return self._active(conn, token_hash(cookie))

    def logout(self, cookie, csrf_token):
        with self.locked() as conn:
            current = self._active(conn, token_hash(cookie), refresh=False)
            require(isinstance(csrf_token, str) and hmac.compare_digest(current['csrf_token'], csrf_token), 'csrf_refused', 403)
            conn.execute('UPDATE owner_session SET revoked_ms=? WHERE session_hash=?', (self.now(), current['session_hash']))
        return {'revoked': True}

    def authority_expiry(self, context):
        """Read the server-owned hard session deadline for clipped child plans."""
        exact(context, 'principal auth_generation session_hash')
        with self.locked() as conn:
            active = self._active(conn, context['session_hash'])
            require(active['principal'] == context['principal'] and active['auth_generation'] == context['auth_generation'], 'foreign_owner_context', 403)
            return active['expires_ms']

    @contextmanager
    def authorize(self, context):
        exact(context, 'principal auth_generation session_hash')
        with self.locked() as conn:
            active = self._active(conn, context['session_hash'])
            require(active['principal'] == context['principal'] and active['auth_generation'] == context['auth_generation'], 'foreign_owner_context', 403)
            yield active['principal']
