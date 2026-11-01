"""Exact-request disclosure grants and durable single-attempt submission state."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from artifacts import Artifacts, MAX_BYTES, Refused, absolute, directory, identity, publish_file, read_file

API_URL = 'https://api.netconverter.ai/external/v1'
MCP_URL = 'https://api.netconverter.ai/mcp/v1/'
JOB_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    installation: str
    mode: str
    state_dir: Path
    workspace: Path | None
    executable: Path | None
    key: str
    account: str

    def __post_init__(self):
        identity(self.installation)
        if self.mode not in ('hosted-readonly','local-terminal'): raise Refused('invalid_mode')
        absolute(self.state_dir)
        if not isinstance(self.account,str) or not 1 <= len(self.account) <= 128 or any(ord(x)<32 for x in self.account):
            raise Refused('invalid_account_reference')
        if re.search(r'nck_(?:live|test)_',self.account): raise Refused('credential_in_account_reference')
        if not isinstance(self.key,str) or any(ord(x)<32 for x in self.key): raise Refused('invalid_credential')
        if self.mode=='local-terminal':
            if not self.workspace or not self.executable: raise Refused('terminal_and_workspace_required')
            absolute(self.workspace); absolute(self.executable)

    @classmethod
    def from_env(cls, env=None):
        env=os.environ if env is None else env
        return cls(env.get('NETCONVERTER_INSTALLATION_ID',''), env.get('NETCONVERTER_MODE','hosted-readonly'),
                   Path(env.get('NETCONVERTER_DATA_DIR','')),
                   Path(env['NETCONVERTER_WORKSPACE']) if env.get('NETCONVERTER_WORKSPACE') else None,
                   Path(env['NETCONVERTER_EXECUTABLE']) if env.get('NETCONVERTER_EXECUTABLE') else None,
                   env.get('NETCONVERTER_API_KEY',''),env.get('NETCONVERTER_ACCOUNT_REF',''))

    def binding(self, salt):
        executable=None
        if self.executable:
            data,info=read_file(self.executable,limit=MAX_BYTES)
            if not os.access(self.executable,os.X_OK): raise Refused('terminal_not_executable')
            executable={'path':str(self.executable),'sha256':hashlib.sha256(data).hexdigest(),'identity':info}
        return digest({'installation':self.installation,'mode':self.mode,'workspace':str(self.workspace),
                       'executable':executable,'account':self.account,'api':API_URL,'mcp':MCP_URL,
                       'credential':hmac.new(salt,self.key.encode(),'sha256').hexdigest()})


def qualify(source,target,operation,options,capabilities):
    if operation not in ('convert','validate','optimize'): raise Refused('unsupported_operation')
    selection={'source':source,'target':target,'job_type':operation}
    matches=[p for p in capabilities.get('paths',[]) if all(p.get(k)==v for k,v in selection.items())]
    if len(matches)!=1:
        raise Refused('unsupported_migration_path')
    if not isinstance(options,dict) or len(canonical(options)) > 8192:
        raise Refused('invalid_options')
    # Model options never contain inline configuration/decisions documents.
    allowed={'selected_device_groups','optimization_options','file_name','zone_mapping',
             'remove_unused_objects','enable_appid','app_id_implementation','add_security_profiles',
             'log_all_rules','implicit_deny','panos_target_version','routing_engine',
             'default_profile_group','panorama_device_group','panorama_template','pipeline_mode'}
    if set(options)-allowed: raise Refused('unsupported_options')
    from jsonschema import Draft202012Validator
    schema=capabilities.get('options_schema',{})
    if not schema or '$ref' in canonical(schema): raise Refused('options_schema_unavailable')
    if not Draft202012Validator(schema).is_valid(options): raise Refused('invalid_options')
    return matches[0]


class Ledger:
    def __init__(self, config):
        self.config=config
        with directory(config.state_dir,create=True,private=True): pass
        salt_path=config.state_dir/'binding.key'
        try: publish_file(salt_path,secrets.token_bytes(32))
        except Refused:
            if not salt_path.exists(): raise
        self.salt,_=read_file(salt_path,limit=32)
        if len(self.salt)!=32: raise Refused('invalid_binding_key')
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS requests (
                  id TEXT PRIMARY KEY, body TEXT NOT NULL, digest TEXT NOT NULL,
                  binding TEXT NOT NULL, state TEXT NOT NULL, expires REAL,
                  attempt TEXT UNIQUE, job_ref TEXT UNIQUE, job_id TEXT, error TEXT);
                CREATE TABLE IF NOT EXISTS events (
                  seq INTEGER PRIMARY KEY, request_id TEXT NOT NULL, at REAL NOT NULL,
                  event TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS imported_jobs (
                  ref TEXT PRIMARY KEY, job_id TEXT NOT NULL, binding TEXT NOT NULL,
                  UNIQUE(job_id,binding));
                CREATE TABLE IF NOT EXISTS polling (
                  ref TEXT PRIMARY KEY, reserved_seconds INTEGER NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        path=self.config.state_dir/'ledger.sqlite3'
        with directory(self.config.state_dir,private=True):
            # The private parent is the trust boundary, not a same-user sandbox.
            if path.exists() or path.is_symlink():
                read_file(path,limit=64*1024*1024)
            else:
                try: publish_file(path,b'')
                except Refused:
                    if not path.exists(): raise
        db=sqlite3.connect(path,timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('BEGIN IMMEDIATE')
            yield db
            if db.in_transaction: db.commit()
        except BaseException:
            if db.in_transaction: db.rollback()
            raise
        finally: db.close()

    def event(self,db,request_id,event):
        db.execute('INSERT INTO events(request_id,at,event) VALUES(?,?,?)',(request_id,time.time(),event))

    def artifacts(self):
        if self.config.mode!='local-terminal' or not self.config.workspace: raise Refused('local_terminal_required')
        return Artifacts(self.config.workspace,self.config.installation)

    def prepare(self,path,source,target,operation,options,capabilities):
        artifacts=self.artifacts()
        if not self.config.key: raise Refused('credential_required')
        path_context=qualify(source,target,operation,options,capabilities)
        max_bytes=capabilities.get('max_bytes')
        if type(max_bytes) is not int or not 0<max_bytes<=MAX_BYTES: raise Refused('artifact_limit_unavailable')
        metadata,frozen=artifacts.capture(path,limit=max_bytes)
        content=artifacts.verify(frozen)
        try: text=content.decode('utf8')
        except UnicodeError: raise Refused('supported_text_source_required') from None
        if not text.strip() or '\x00' in text: raise Refused('supported_text_source_required')
        request_id=uuid.uuid4().hex; binding=self.config.binding(self.salt)
        body={'request_id':request_id,'installation':self.config.installation,'source':metadata,'frozen':frozen,
              'source_vendor':source,'target_vendor':target,'job_type':operation,'options':options,
              'path_context':path_context,
              'account_reference':self.config.account,'destination':API_URL,'mcp_destination':MCP_URL,
              'workspace':str(self.config.workspace),'executable':str(self.config.executable),
              'binding':binding,'capabilities_digest':digest(capabilities),'created_at':time.time()}
        review_digest=digest(body)
        with self.connection() as db:
            db.execute('INSERT INTO requests(id,body,digest,binding,state) VALUES(?,?,?,?,?)',
                       (request_id,canonical(body),review_digest,binding,'prepared'))
            self.event(db,request_id,'prepared')
        return self.status(request_id)

    def row(self,db,request_id):
        identity(request_id)
        row=db.execute('SELECT * FROM requests WHERE id=?',(request_id,)).fetchone()
        if not row: raise Refused('request_not_found')
        if digest(json.loads(row['body']))!=row['digest']: raise Refused('request_integrity_failure')
        return row

    def request(self,request_id):
        with self.connection() as db: return json.loads(self.row(db,request_id)['body'])

    def status(self,request_id):
        with self.connection() as db:
            row=self.row(db,request_id); body=json.loads(row['body'])
            state='unknown' if row['state']=='attempting' else row['state']
            if state=='approved' and (row['expires'] is None or row['expires']<=time.time()): state='expired'
            return {**body,'review_digest':row['digest'],'state':state,
                    'expires_at':row['expires'],'job_ref':row['job_ref'],'error':row['error'],
                    'approval_origin':'native-operator-cli','account_identity_verified':False}

    def approve(self,request_id,review_digest,ttl=300):
        if type(ttl) is not int or not 1<=ttl<=3600: raise Refused('invalid_approval_lifetime')
        with self.connection() as db:
            row=self.row(db,request_id)
            if row['state']!='prepared': raise Refused('request_not_approvable')
            if not hmac.compare_digest(row['digest'],review_digest): raise Refused('review_digest_mismatch')
            body=json.loads(row['body']); self.check_binding(row,body)
            db.execute('UPDATE requests SET state=?,expires=? WHERE id=?',('approved',time.time()+ttl,request_id))
            self.event(db,request_id,'operator_approved')
        return self.status(request_id)

    def check_binding(self,row,body):
        if row['binding']!=self.config.binding(self.salt): raise Refused('connection_changed')
        artifacts=self.artifacts(); artifacts.verify_source(body['source']); artifacts.verify(body['frozen'])

    def claim(self,request_id,capabilities):
        with self.connection() as db:
            row=self.row(db,request_id); body=json.loads(row['body'])
            if row['state']=='prepared': raise Refused('approval_required')
            if row['state']!='approved': raise Refused('approval_consumed_or_request_terminal')
            if row['expires'] is None or row['expires']<time.time(): raise Refused('approval_expired')
            self.check_binding(row,body)
            if body['capabilities_digest']!=digest(capabilities): raise Refused('capabilities_changed')
            qualify(body['source_vendor'],body['target_vendor'],body['job_type'],body['options'],capabilities)
            attempt=uuid.uuid4().hex
            db.execute('UPDATE requests SET state=?,attempt=? WHERE id=?',('attempting',attempt,request_id))
            self.event(db,request_id,'attempt_reserved')
        return {**body,'attempt_id':attempt}

    def finish(self,request_id,attempt_id,receipt):
        with self.connection() as db:
            row=self.row(db,request_id); body=json.loads(row['body'])
            if row['state']!='attempting' or row['attempt']!=attempt_id: raise Refused('attempt_mismatch')
            valid=(isinstance(receipt,dict) and isinstance(receipt.get('job_id'),str) and
                   JOB_ID.fullmatch(receipt['job_id']) and receipt.get('sha256')==body['source']['sha256'] and
                   type(receipt.get('bytes')) is int and receipt['bytes']==body['source']['bytes'])
            if valid:
                db.execute('UPDATE requests SET state=?,job_ref=?,job_id=? WHERE id=?',
                           ('submitted',uuid.uuid4().hex,receipt['job_id'],request_id))
            else:
                db.execute('UPDATE requests SET state=?,error=? WHERE id=?',
                           ('unknown','submission_outcome_unknown_do_not_resubmit',request_id))
            self.event(db,request_id,'submitted' if valid else 'unknown')
        return self.status(request_id)

    def job(self,job_ref):
        identity(job_ref)
        with self.connection() as db:
            row=db.execute('SELECT * FROM requests WHERE job_ref=?',(job_ref,)).fetchone()
            if not row:
                row=db.execute('SELECT ref AS id,job_id,binding FROM imported_jobs WHERE ref=?',(job_ref,)).fetchone()
            if not row or row['binding']!=self.config.binding(self.salt): raise Refused('job_not_bound_to_connection')
            return {'job_ref':job_ref,'job_id':row['job_id'],'request_id':row['id']}

    def associate(self,job_id):
        """Called only after a schema-qualified successful job read on this binding."""
        if not isinstance(job_id,str) or not JOB_ID.fullmatch(job_id): raise Refused('invalid_job_id')
        binding=self.config.binding(self.salt)
        with self.connection() as db:
            ref=uuid.uuid4().hex
            db.execute('INSERT OR IGNORE INTO imported_jobs VALUES(?,?,?)',(ref,job_id,binding))
            row=db.execute('SELECT ref FROM imported_jobs WHERE job_id=? AND binding=?',(job_id,binding)).fetchone()
            return row['ref']

    def reserve_poll(self,job_ref,seconds):
        self.job(job_ref)
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO polling VALUES(?,0)',(job_ref,))
            used=db.execute('SELECT reserved_seconds FROM polling WHERE ref=?',(job_ref,)).fetchone()[0]
            if used+seconds>300: raise Refused('job_wait_budget_exhausted_use_explicit_status')
            db.execute('UPDATE polling SET reserved_seconds=? WHERE ref=?',(used+seconds,job_ref))
