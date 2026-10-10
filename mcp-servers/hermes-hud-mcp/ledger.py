"""Private durable admission/evidence. A lost POST is never safe to replay."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat as file_stat
import time
from contextlib import contextmanager

ACTIVE = ('submitting', 'queued', 'running', 'waiting_approval', 'stopping', 'unknown')
TERMINAL = ('completed', 'failed', 'cancelled', 'interrupted')

class HudError(ValueError):
    def __init__(self, code, message=None):
        self.code = code
        super().__init__(message or code.replace('_', ' '))

def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value):
        raise HudError('input_invalid')
    return value

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def private_dir(directory):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stat = directory.lstat()
    if directory.is_symlink() or not directory.is_dir() or stat.st_mode & 0o077 or stat.st_uid != os.getuid():
        raise HudError('configuration_missing', 'Owner-private state directory required')
    return directory

def private_db(file):
    file = Path(file)
    private_dir(file.parent)
    fd = os.open(file, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        stat = os.fstat(fd)
        if not file_stat.S_ISREG(stat.st_mode):raise HudError('configuration_missing')
        if stat.st_mode & 0o077 or stat.st_uid != os.getuid(): raise HudError('configuration_missing')
    finally: os.close(fd)
    return file

class Ledger:
    def __init__(self, file, installation):
        self.file = private_db(file)
        self.installation = identifier(installation)
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, session TEXT,
                seed TEXT NOT NULL, seed_digest TEXT NOT NULL, created REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, conversation TEXT NOT NULL,
                nonce TEXT NOT NULL, fingerprint TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL,
                run_id TEXT, result TEXT, deadline REAL NOT NULL, created REAL NOT NULL,
                UNIQUE(conversation,nonce), FOREIGN KEY(conversation) REFERENCES conversations(id));
              CREATE TABLE IF NOT EXISTS evidence (sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                request TEXT NOT NULL, call_id TEXT NOT NULL, tool TEXT NOT NULL, state TEXT NOT NULL,
                result_digest TEXT, summary TEXT, created REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS acknowledgments (request TEXT NOT NULL, conversation TEXT NOT NULL,
                created REAL NOT NULL, PRIMARY KEY(request,conversation));
              CREATE TABLE IF NOT EXISTS execution_scopes (request TEXT PRIMARY KEY,
                scope TEXT NOT NULL, FOREIGN KEY(request) REFERENCES requests(id) ON DELETE CASCADE);
            ''')
            row = db.execute('SELECT value FROM metadata WHERE key=?', ('installation',)).fetchone()
            if row and row[0] != installation: raise HudError('owner_invalid')
            db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)', ('installation', installation))
            # Only settled metadata ages out. Uncertainty survives ordinary retention.
            expired=[r[0] for r in db.execute('SELECT id FROM requests WHERE state IN (?,?,?,?) AND created<?',(*TERMINAL,time.time()-30*86400))]
            for request in expired:
                db.execute('DELETE FROM evidence WHERE request=?',(request,))
                db.execute('DELETE FROM acknowledgments WHERE request=?',(request,))
                db.execute('DELETE FROM requests WHERE id=?',(request,))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.file, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback(); raise
        finally: db.close()

    def scope(self, installation):
        if installation != self.installation: raise HudError('owner_invalid')

    def open(self, conversation, seed=None, acknowledgment=None):
        identifier(conversation); seed = seed or []
        if not isinstance(seed, list) or len(json.dumps(seed).encode()) > 1024*1024: raise HudError('input_invalid')
        if any(not isinstance(m, dict) or set(m) != {'role','content'} or m['role'] not in ('user','assistant') or not isinstance(m['content'], str) for m in seed): raise HudError('input_invalid')
        with self.db() as db:
            row = db.execute('SELECT * FROM conversations WHERE id=?', (conversation,)).fetchone()
            if row:
                if seed and digest(seed)!=row['seed_digest']:raise HudError('input_invalid','Conversation seed is immutable.')
                return dict(row)
            if acknowledgment:
                old = db.execute('SELECT state FROM requests WHERE id=?', (identifier(acknowledgment),)).fetchone()
                # Node already authorizes this exact owned request. A missing bridge
                # admission after transport/storage failure stays uncertain; the
                # acknowledgment is retained without inventing an old run or replay.
                if old and old[0] != 'unknown': raise HudError('input_invalid')
                db.execute('INSERT INTO acknowledgments VALUES (?,?,?)', (acknowledgment,conversation,time.time()))
            db.execute('INSERT INTO conversations VALUES (?,NULL,?,?,?)', (conversation,json.dumps(seed),digest(seed),time.time()))
        return self.conversation(conversation)

    def conversation(self, conversation):
        with self.db() as db: row = db.execute('SELECT * FROM conversations WHERE id=?', (identifier(conversation),)).fetchone()
        if not row: raise HudError('owner_invalid')
        return dict(row)

    def bind(self, conversation, session):
        with self.db() as db:
            db.execute('UPDATE conversations SET session=? WHERE id=? AND session IS NULL', (identifier(session),identifier(conversation)))
        return self.conversation(conversation)

    def admit(self, conversation, request, nonce, text, deadline_ms, execution_scope=None):
        identifier(request); identifier(nonce); self.conversation(conversation)
        if not isinstance(text,str) or not text.strip() or len(text.encode()) > 65536: raise HudError('input_invalid')
        if not isinstance(deadline_ms,int) or not 1000 <= deadline_ms <= 3600000: raise HudError('input_invalid')
        fingerprint = digest({'text':text,'conversation':conversation,**({'scope':execution_scope} if execution_scope is not None else {})})
        if execution_scope is not None:
            if not isinstance(execution_scope,dict) or execution_scope.get('installation')!=self.installation or execution_scope.get('request')!=request or execution_scope.get('conversation')!=conversation or execution_scope.get('body_digest')!=digest(text):
                raise HudError('owner_invalid')
            if not time.time()<execution_scope.get('deadline',0)<=time.time()+3601:raise HudError('input_invalid')
        with self.db() as db:
            old = db.execute('SELECT * FROM requests WHERE conversation=? AND nonce=?', (conversation,nonce)).fetchone()
            if old:
                if old['fingerprint'] != fingerprint: raise HudError('input_invalid', 'Retry nonce conflicts with original request')
                return dict(old), False
            if db.execute('SELECT 1 FROM requests WHERE conversation=? AND state IN (?,?,?,?,?,?)', (conversation,*ACTIVE)).fetchone(): raise HudError('conversation_busy')
            if db.execute('SELECT count(*) FROM requests WHERE state IN (?,?,?,?,?,?)', ACTIVE).fetchone()[0] >= 4: raise HudError('conversation_busy')
            now=time.time()
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,NULL,NULL,?,?)', (request,conversation,nonce,fingerprint,text,'submitting',now+deadline_ms/1000,now))
            if execution_scope is not None:
                db.execute('INSERT INTO execution_scopes VALUES (?,?)',(request,json.dumps(execution_scope,sort_keys=True)))
        return self.request(conversation,request), True

    def request(self, conversation, request):
        with self.db() as db: row=db.execute('SELECT * FROM requests WHERE id=? AND conversation=?', (identifier(request),identifier(conversation))).fetchone()
        if not row: raise HudError('owner_invalid')
        return dict(row)

    def update(self, conversation, request, state, run_id=None, result=None):
        self.request(conversation,request)
        if state not in (*ACTIVE,*TERMINAL): raise HudError('response_invalid')
        with self.db() as db:
            db.execute('UPDATE requests SET state=?,run_id=COALESCE(?,run_id),result=COALESCE(?,result) WHERE id=? AND conversation=? AND state NOT IN (?,?,?,?)', (state,run_id,json.dumps(result) if result is not None else None,request,conversation,*TERMINAL))
        return self.request(conversation,request)

    def record(self, request, call_id, tool, state, summary=None):
        identifier(request); identifier(call_id); identifier(tool)
        with self.db() as db:
            if not db.execute('SELECT 1 FROM requests WHERE id=?', (request,)).fetchone(): raise HudError('owner_invalid')
            db.execute('INSERT INTO evidence(request,call_id,tool,state,result_digest,summary,created) VALUES (?,?,?,?,?,?,?)',
                (request,call_id,tool,state,digest(summary) if summary is not None else None,summary[:4096] if summary else None,time.time()))

    def events(self, conversation, request, cursor=0):
        self.request(conversation,request)
        if not isinstance(cursor,int) or not 0<=cursor<=2147483647:raise HudError('input_invalid')
        with self.db() as db:
            rows=db.execute('SELECT sequence,call_id,tool,state,result_digest,summary,created FROM evidence WHERE request=? AND sequence>? ORDER BY sequence LIMIT 20', (request,int(cursor))).fetchall()
        return [dict(row) for row in rows]
