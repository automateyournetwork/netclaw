"""Operation-bound Anthropic forwarding with durable retry suppression.

The production upstream is fixed HTTPS. The optional callable is a qualification
seam for loopback fixtures, never selected by environment or an HTTP request.
"""
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import http.client
import inspect
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import ssl
import stat
import time
import uuid

MODEL = 'claude-sonnet-4-6'
MAX_REQUEST = 1024 * 1024
MAX_RESPONSE = 2 * 1024 * 1024
UPSTREAM_TIMEOUT = 90
ALLOWED_REQUEST_FIELDS = frozenset(('model','max_tokens','messages','system','tools','tool_choice',
    'temperature','top_p','top_k','stop_sequences','stream','metadata','thinking','output_config','service_tier'))


class ProviderRefused(ValueError):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def require(condition, code='invalid_request', status=400):
    if not condition: raise ProviderRefused(code, status)


def _valid_json(value, depth=0):
    require(depth <= 32, 'request_nesting_limit')
    if value is None or type(value) is bool: return
    if type(value) is int:
        require(abs(value) <= 2**53-1, 'invalid_json_number')
    elif type(value) is float:
        require(math.isfinite(value), 'invalid_json_number')
    elif isinstance(value,str):
        try:value.encode('utf-8','strict')
        except UnicodeError:raise ProviderRefused('invalid_unicode') from None
    elif isinstance(value,list):
        require(len(value)<=10000,'request_collection_limit')
        for child in value:_valid_json(child,depth+1)
    elif isinstance(value,dict):
        require(len(value)<=10000,'request_collection_limit')
        for key,child in value.items():
            require(isinstance(key,str),'invalid_json_key');_valid_json(key,depth+1);_valid_json(child,depth+1)
    else:raise ProviderRefused('invalid_json_type')


def canonical(value):
    _valid_json(value)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def strict_json(raw):
    require(isinstance(raw,bytes) and 0<len(raw)<=MAX_REQUEST,'request_size_limit',413)
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate_json_key');result[key]=value
        return result
    try:
        result=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=pairs,
                          parse_constant=lambda _:(_ for _ in ()).throw(ProviderRefused('invalid_json_number')))
    except (UnicodeError,ValueError) as exc:
        if isinstance(exc,ProviderRefused):raise
        raise ProviderRefused('invalid_json') from None
    _valid_json(result)
    return result


def private_directory(path):
    path=Path(path).absolute()
    require(path==path.resolve(),'symlink_private_directory',503)
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077,'unsafe_private_directory',503)
    return path


def private_read(path,maximum=MAX_RESPONSE):
    path=Path(path).absolute()
    require(path==path.resolve(),'symlink_private_file',503)
    private_directory(path.parent)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077 and info.st_size<=maximum,'unsafe_private_file',503)
        return stream.read()


def private_write(path,value):
    path=Path(path)
    private_directory(path.parent)
    if path.exists() or path.is_symlink():private_read(path,64*1024*1024)
    temporary=path.with_name(path.name+'.'+str(uuid.uuid4())+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(value if isinstance(value,bytes) else canonical(value));stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if temporary.exists():temporary.unlink()


@dataclass(frozen=True)
class ProviderResponse:
    status: int
    body: bytes
    headers: dict = field(default_factory=lambda:{'content-type':'application/json'})


def refusal(code,status=409):
    # Deliberately fixed codes: never include request bodies, credentials or exceptions.
    return ProviderResponse(status,canonical({'error':{'type':'netclaw_protected_upstream','code':code}}))


SCHEMA='''
CREATE TABLE IF NOT EXISTS provider_meta (
 id INTEGER PRIMARY KEY CHECK(id=1), operation_id TEXT NOT NULL, model TEXT NOT NULL,
 expires_at_ms INTEGER NOT NULL, maximum_calls INTEGER NOT NULL, max_seen_ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS provider_request (
 request_digest TEXT PRIMARY KEY, ordinal INTEGER NOT NULL UNIQUE,
 canonical_request BLOB NOT NULL, state TEXT NOT NULL CHECK(state IN ('claimed','finished','unknown')),
 upstream_attempt_count INTEGER NOT NULL CHECK(upstream_attempt_count=1),
 claimed_ms INTEGER NOT NULL, finished_ms INTEGER,
 upstream_status INTEGER, response_status INTEGER, response_headers TEXT,
 response_body BLOB, response_digest TEXT, upstream_body_digest TEXT, error_code TEXT
);
'''


class ProviderFence:
    """A dispatch claim is never released, including after restart or a timeout."""
    def __init__(self,path,*,operation_id,expires_at_ms,model=MODEL,maximum_calls=2,clock_ms=None):
        try:require(str(uuid.UUID(operation_id))==operation_id,'invalid_operation')
        except (ValueError,TypeError,AttributeError):raise ProviderRefused('invalid_operation') from None
        require(model==MODEL,'model_not_qualified')
        require(type(maximum_calls) is int and maximum_calls==2,'invalid_call_limit')
        require(type(expires_at_ms) is int and 0<expires_at_ms<2**53,'invalid_expiry')
        self.path=Path(path).absolute();private_directory(self.path.parent)
        self.operation_id,self.expires_at_ms,self.model,self.maximum_calls=operation_id,expires_at_ms,model,maximum_calls
        self.now=clock_ms or (lambda:int(time.time()*1000))
        if self.path.exists() or self.path.is_symlink():private_read(self.path,64*1024*1024)
        else:
            try:
                fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
            except FileExistsError:private_read(self.path,64*1024*1024)
        with self.connection() as conn:conn.executescript(SCHEMA)
        with self.transaction() as conn:
            meta=conn.execute('SELECT * FROM provider_meta WHERE id=1').fetchone()
            if meta is None:
                conn.execute('INSERT INTO provider_meta VALUES(1,?,?,?,?,?)',(operation_id,model,expires_at_ms,maximum_calls,self.now()))
            else:
                require((meta['operation_id'],meta['model'],meta['expires_at_ms'],meta['maximum_calls'])==(operation_id,model,expires_at_ms,maximum_calls),'foreign_or_changed_operation',403)

    @contextmanager
    def connection(self):
        info=self.path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077,'unsafe_provider_ledger',503)
        conn=sqlite3.connect(str(self.path),isolation_level=None,timeout=10)
        conn.row_factory=sqlite3.Row;conn.execute('PRAGMA synchronous=FULL');conn.execute('PRAGMA busy_timeout=10000')
        try:yield conn
        finally:conn.close()

    @contextmanager
    def transaction(self):
        with self.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:yield conn;conn.commit()
            except BaseException:conn.rollback();raise

    def claim(self,request):
        require(isinstance(request,dict) and set(request)<=ALLOWED_REQUEST_FIELDS,'request_fields_refused')
        require(request.get('model')==self.model,'model_substitution',403)
        require(type(request.get('max_tokens')) is int and 0<request['max_tokens']<=4096,'token_limit_refused',403)
        require(isinstance(request.get('messages'),list) and 0<len(request['messages'])<=256,'messages_required')
        require('stream' not in request or type(request['stream']) is bool,'invalid_stream_flag')
        raw=canonical(request);require(len(raw)<=MAX_REQUEST,'request_size_limit',413)
        hashed=hashlib.sha256(raw).hexdigest()
        with self.transaction() as conn:
            existing=conn.execute('SELECT * FROM provider_request WHERE request_digest=?',(hashed,)).fetchone()
            if existing is not None:
                require(bytes(existing['canonical_request'])==raw,'request_digest_conflict',409)
                result=dict(existing);result['new_claim']=False;return result
            meta=conn.execute('SELECT * FROM provider_meta WHERE id=1').fetchone()
            now=self.now()
            require(now>=meta['max_seen_ms'],'clock_rollback',403)
            require(now<self.expires_at_ms,'operation_expired',403)
            rows=conn.execute('SELECT ordinal,state FROM provider_request ORDER BY ordinal').fetchall()
            require(len(rows)<self.maximum_calls,'provider_call_limit',429)
            # An uncertain first call cannot be disguised as a distinct second call.
            require(all(row['state']=='finished' for row in rows),'prior_upstream_outcome_unknown',409)
            conn.execute('UPDATE provider_meta SET max_seen_ms=? WHERE id=1',(now,))
            conn.execute("INSERT INTO provider_request(request_digest,ordinal,canonical_request,state,upstream_attempt_count,claimed_ms) VALUES(?,?,?,'claimed',1,?)",(hashed,len(rows)+1,raw,now))
            result=dict(conn.execute('SELECT * FROM provider_request WHERE request_digest=?',(hashed,)).fetchone())
            result['new_claim']=True;return result

    def finish(self,request_digest,response,*,upstream_status=None,upstream_body_digest=None,error_code=None):
        require(type(response.status) is int and 200<=response.status<=599,'invalid_upstream_status')
        require(isinstance(response.body,bytes) and len(response.body)<=MAX_RESPONSE,'response_size_limit',502)
        headers=_safe_response_headers(response.headers)
        with self.transaction() as conn:
            changed=conn.execute("UPDATE provider_request SET state='finished',finished_ms=?,upstream_status=?,response_status=?,response_headers=?,response_body=?,response_digest=?,upstream_body_digest=?,error_code=? WHERE request_digest=? AND state='claimed'",
                (self.now(),upstream_status if upstream_status is not None else response.status,response.status,
                 canonical(headers).decode(),response.body,hashlib.sha256(response.body).hexdigest(),
                 upstream_body_digest or hashlib.sha256(response.body).hexdigest(),error_code,request_digest)).rowcount
            require(changed==1,'provider_result_conflict',409)

    def unknown(self,request_digest,code='upstream_outcome_unknown'):
        with self.transaction() as conn:
            conn.execute("UPDATE provider_request SET state='unknown',error_code=? WHERE request_digest=? AND state='claimed'",(code,request_digest))

    def snapshot(self):
        with self.connection() as conn:
            meta=dict(conn.execute('SELECT * FROM provider_meta WHERE id=1').fetchone())
            rows=[dict(row) for row in conn.execute('SELECT request_digest,ordinal,state,upstream_attempt_count,claimed_ms,finished_ms,upstream_status,response_status,response_digest,upstream_body_digest,error_code FROM provider_request ORDER BY ordinal')]
        return {'schemaVersion':1,'operation_id':meta['operation_id'],'model':meta['model'],
                'expires_at_ms':meta['expires_at_ms'],'maximum_calls':meta['maximum_calls'],
                'upstream_attempt_count':sum(row['upstream_attempt_count'] for row in rows),
                'count_semantics':'durable dispatch claims; uncertain claims may or may not have reached the provider',
                'requests':rows}


def _safe_response_headers(headers):
    require(isinstance(headers,dict),'invalid_upstream_headers',502)
    result={}
    for name,value in headers.items():
        if not isinstance(name,str) or name.lower() not in ('content-type','request-id','anthropic-request-id'):continue
        require(isinstance(value,str) and value.isascii() and len(value)<=200 and '\r' not in value and '\n' not in value,'invalid_upstream_headers',502)
        result[name.lower()]=value
    result.setdefault('content-type','application/json')
    return result


def _fixed_anthropic(request,api_key,timeout=UPSTREAM_TIMEOUT):
    """No proxy settings, URL parameters, custom auth headers or redirects."""
    deadline=time.monotonic()+timeout
    connection=http.client.HTTPSConnection('api.anthropic.com',443,timeout=min(10,timeout),context=ssl.create_default_context())
    try:
        connection.connect()
        sock=connection.sock
        def remaining():
            seconds=deadline-time.monotonic()
            if seconds<=0:raise TimeoutError()
            sock.settimeout(seconds)
        remaining()
        connection.request('POST','/v1/messages',body=canonical(request),headers={
            'Content-Type':'application/json','Anthropic-Version':'2023-06-01',
            'x-api-key':api_key,'User-Agent':'netclaw-protected-provider/1','Connection':'close'})
        remaining();response=connection.getresponse()
        raw=bytearray()
        while True:
            remaining();chunk=response.read1(min(65536,MAX_RESPONSE+1-len(raw)))
            if not chunk:break
            raw.extend(chunk)
            if len(raw)>MAX_RESPONSE:raise ProviderRefused('response_size_limit',502)
        return ProviderResponse(response.status,bytes(raw),dict(response.getheaders()))
    finally:connection.close()


class ProviderProxy:
    def __init__(self,fence,api_key,*,upstream=None,timeout=UPSTREAM_TIMEOUT):
        require(isinstance(api_key,str) and 1<=len(api_key)<=4096 and api_key.isascii() and '\n' not in api_key and '\r' not in api_key,'provider_key_unavailable',503)
        require(type(timeout) in (int,float) and 0<timeout<=UPSTREAM_TIMEOUT,'invalid_upstream_timeout')
        self.fence,self._api_key,self.upstream,self.timeout=fence,api_key,upstream,timeout
        self.server=None;self.active=set();self.semaphore=asyncio.Semaphore(16)

    async def process(self,raw_body):
        try:
            request=strict_json(raw_body)
            row=self.fence.claim(request)
        except ProviderRefused as exc:return refusal(exc.code,exc.status)
        if not row['new_claim']:
            if row['state']=='finished':
                body=bytes(row['response_body'])
                if hashlib.sha256(body).hexdigest()!=row['response_digest']:return refusal('cached_response_corrupt',503)
                return ProviderResponse(row['response_status'],body,json.loads(row['response_headers']))
            return refusal('upstream_in_flight_or_unknown')
        try:
            if self.upstream is None:
                result=await asyncio.wait_for(asyncio.to_thread(_fixed_anthropic,request,self._api_key,self.timeout),self.timeout)
            else:
                async def call_fixture():
                    if inspect.iscoroutinefunction(self.upstream):return await self.upstream(request)
                    result=await asyncio.to_thread(self.upstream,request)
                    return await result if inspect.isawaitable(result) else result
                result=await asyncio.wait_for(call_fixture(),self.timeout)
            require(isinstance(result,ProviderResponse),'invalid_upstream_response',502)
            require(isinstance(result.body,bytes) and len(result.body)<=MAX_RESPONSE,'response_size_limit',502)
            require(type(result.status) is int and 200<=result.status<=599,'invalid_upstream_status',502)
            original_status=result.status;original_digest=hashlib.sha256(result.body).hexdigest();code=None
            if self._api_key.encode() in result.body or any(self._api_key in value for value in result.headers.values() if isinstance(value,str)):
                result=refusal('provider_credential_echo_refused',502);code='provider_credential_echo_refused'
            elif 300<=result.status<400:
                result=refusal('upstream_redirect_refused',502);code='upstream_redirect_refused'
            result=ProviderResponse(result.status,result.body,_safe_response_headers(result.headers))
            self.fence.finish(row['request_digest'],result,upstream_status=original_status,upstream_body_digest=original_digest,error_code=code)
            return result
        except BaseException as exc:
            # A cancelled thread can still finish its one network request. Its claim
            # remains spent; a later request never launches another network attempt.
            self.fence.unknown(row['request_digest'])
            if isinstance(exc,(asyncio.CancelledError,KeyboardInterrupt,SystemExit)):raise
            return refusal('upstream_outcome_unknown')

    async def start(self,host='127.0.0.1',port=18888):
        require(host=='127.0.0.1' and type(port) is int and 0<=port<=65535,'loopback_listener_required')
        self.server=await asyncio.start_server(self._handle,host,port,limit=16384)
        return self.server.sockets[0].getsockname()[1]

    async def close(self):
        if self.server:self.server.close();await self.server.wait_closed()
        tasks=list(self.active)
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)

    async def async_send_response(self,writer,response):
        headers=_safe_response_headers(response.headers)
        start=f'HTTP/1.1 {response.status} Response\r\nContent-Length: {len(response.body)}\r\nConnection: close\r\nCache-Control: no-store\r\n'
        for key,value in headers.items():start+=key+': '+value+'\r\n'
        writer.write(start.encode('ascii')+b'\r\n'+response.body)
        await writer.drain()

    async def _handle(self,reader,writer):
        task=asyncio.current_task();self.active.add(task)
        try:
            async with self.semaphore:
                try:
                    raw=await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),5)
                    require(len(raw)<=16384,'header_size_limit',413)
                    lines=raw.decode('ascii').split('\r\n')
                    require(lines[0]=='POST /v1/messages HTTP/1.1','route_refused',404)
                    headers={}
                    for line in lines[1:]:
                        if not line:continue
                        require(':' in line,'invalid_header')
                        name,value=line.split(':',1);name=name.lower()
                        require(name not in headers,'duplicate_header')
                        headers[name]=value.strip()
                    require('transfer-encoding' not in headers,'chunked_request_refused')
                    require(headers.get('content-type','').split(';')[0]=='application/json','content_type_refused',415)
                    require(headers.get('content-length','').isdigit(),'content_length_required',411)
                    length=int(headers['content-length']);require(0<length<=MAX_REQUEST,'request_size_limit',413)
                    body=await asyncio.wait_for(reader.readexactly(length),10)
                    response=await self.process(body)
                except ProviderRefused as exc:response=refusal(exc.code,exc.status)
                except Exception:response=refusal('invalid_request',400)
                await self.async_send_response(writer,response)
        except (ConnectionError,asyncio.IncompleteReadError):pass
        finally:
            self.active.discard(task);writer.close()
            try:await writer.wait_closed()
            except Exception:pass
