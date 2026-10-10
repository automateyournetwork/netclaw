"""Trusted receiver scopes and private, fail-closed execution broker.

The model never receives a token or chooses its origin. Ingress creates a scope
after channel authorization; every effect checks that authorization again.
"""
import asyncio
from dataclasses import dataclass
import hashlib
import inspect
import json
import secrets
import time
import uuid

from .runtime import private_dir, write_private


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


class Refused(ValueError): pass
class OutcomeUnknown(RuntimeError):
    """A dispatch may have executed; never silently resubmit."""


@dataclass(frozen=True)
class ExecutionScope:
    installation: str
    requester: str
    origin: str
    request: str
    conversation: str
    target_type: str
    target: str
    body_digest: str
    deadline: float
    profile: str
    grant: str | None = None
    approval: str | None = None
    parent: str | None = None
    presentation_origin: str | None = None

    def __post_init__(self):
        if self.origin not in ('operator','internal','external') or self.profile not in ('operator','chat','subnet'):
            raise Refused('invalid execution origin/profile')
        if self.origin != 'operator' and self.profile == 'operator': raise Refused('receiver cannot become operator')
        if self.presentation_origin not in (None,'voice'):raise Refused('invalid presentation origin')
        for value in (self.installation,self.requester,self.request,self.conversation,self.target_type,self.target):
            if not isinstance(value,str) or not 1<=len(value)<=200 or any(ord(c)<32 for c in value):raise Refused('invalid execution scope')
        if len(self.body_digest)!=64 or any(c not in '0123456789abcdef' for c in self.body_digest):raise Refused('invalid body digest')
        if not isinstance(self.deadline,(float,int)) or not time.time()<self.deadline<=time.time()+3601:raise Refused('invalid deadline')
        if self.profile == 'subnet' and (self.target_type,self.target) not in (('skill','subnet-calculator'),('tool','subnet-calc-mcp/subnet_calculator')):
            raise Refused('unqualified receiver target')

    def as_dict(self): return dict(self.__dict__)


def conversation_id(installation, requester, session):
    return 'n2n-'+digest([installation,requester,session])[:48]


class ExecutionBroker:
    def __init__(self, manager, runtime, operator=None):
        self.manager=manager;self.runtime=runtime;self.operator=operator
        self.key=secrets.token_urlsafe(48);self.permits={};self.effects={};self.server=None;self.port=None
        self.db=manager._conn
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS execution_scope(request TEXT PRIMARY KEY, installation TEXT NOT NULL,
            body_digest TEXT NOT NULL, scope TEXT NOT NULL, permit_hash TEXT NOT NULL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS execution_effect(effect_key TEXT PRIMARY KEY, installation TEXT NOT NULL,
            conversation TEXT NOT NULL, request TEXT NOT NULL, call_id TEXT NOT NULL, body_digest TEXT NOT NULL,
            state TEXT NOT NULL, result TEXT, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS execution_handle(installation TEXT NOT NULL, conversation TEXT NOT NULL,
            kind TEXT NOT NULL, handle TEXT NOT NULL, peer TEXT NOT NULL,
            PRIMARY KEY(installation,conversation,kind,handle));
        ''')
        self.db.commit()

    def issue(self, scope, authorize):
        if scope.installation!=self.runtime.installation:raise Refused('foreign installation')
        if not callable(authorize):raise Refused('live authorization required')
        token=secrets.token_urlsafe(48);hashed=digest(token)
        existing=self.db.execute('SELECT * FROM execution_scope WHERE request=?',(scope.request,)).fetchone()
        if existing:raise Refused('request already admitted; reconcile without replay')
        self.db.execute('INSERT INTO execution_scope VALUES (?,?,?,?,?,?)',
                        (scope.request,scope.installation,scope.body_digest,json.dumps(scope.as_dict()),hashed,time.time()))
        self.db.commit()
        self.permits[hashed]=(scope,authorize)
        return token

    async def check(self, token, request, tool=None, arguments=None):
        entry=self.permits.get(digest(token))
        if not entry:raise Refused('invalid or restarted execution permit')
        scope,authorize=entry
        if scope.request!=request or scope.installation!=self.runtime.installation or time.time()>=scope.deadline:
            raise Refused('expired or foreign execution permit')
        allowed=authorize(scope)
        if inspect.isawaitable(allowed):allowed=await allowed
        if not allowed:raise Refused('authorization revoked')
        if tool is not None:
            if scope.profile=='chat':raise Refused('chat cannot invoke tools')
            if scope.profile=='subnet' and tool!='mcp__subnet_calc_mcp__subnet_calculator':raise Refused('outside receiver profile')
            if scope.profile=='subnet':
                import ipaddress
                if not isinstance(arguments,dict) or set(arguments)!={'cidr'}:raise Refused('invalid arguments')
                try:network=ipaddress.IPv4Network(arguments['cidr'],strict=False)
                except (ValueError,TypeError):raise Refused('invalid subnet') from None
                if not 24<=network.prefixlen<=30:raise Refused('unqualified subnet size')
        return scope

    async def effect(self, token, request, call_id, operation, arguments, invoke):
        scope=await self.check(token,request)
        if scope.profile!='operator':raise Refused('receiver cannot orchestrate federation')
        if not isinstance(call_id,str) or not 1<=len(call_id)<=128:raise Refused('invalid call id')
        key=digest([scope.installation,scope.conversation,request,call_id])
        body=digest([operation,arguments])
        row=self.db.execute('SELECT * FROM execution_effect WHERE effect_key=?',(key,)).fetchone()
        if row:
            if row['body_digest']!=body:raise Refused('conflicting repeated effect')
            if row['state']=='completed':return json.loads(row['result'])
            raise OutcomeUnknown('previous effect may have executed; do not replay')
        # Durable intent precedes any send, including a read that can allocate a
        # chat/task remotely. A lost result never restores dispatch permission.
        self.db.execute('INSERT INTO execution_effect VALUES (?,?,?,?,?,?,?,NULL,?)',
                        (key,scope.installation,scope.conversation,request,call_id,body,'dispatching',time.time()))
        self.db.commit()
        try:
            result=await asyncio.wait_for(invoke(scope,operation,arguments),max(.001,scope.deadline-time.time()))
            await self.check(token,request)
            encoded=json.dumps(result)
            if len(encoded.encode())>1048576:raise OutcomeUnknown('effect result exceeds the supported response bound')
            self.db.execute("UPDATE execution_effect SET state='completed',result=? WHERE effect_key=?",(encoded,key))
            self.db.commit()
            return result
        except BaseException:
            self.db.execute("UPDATE execution_effect SET state='outcome_unknown' WHERE effect_key=?",(key,));self.db.commit()
            raise

    def own(self, scope, kind, handle, peer):
        self.db.execute('INSERT OR IGNORE INTO execution_handle VALUES (?,?,?,?,?)',
                        (scope.installation,scope.conversation,kind,handle,peer));self.db.commit()

    def owner(self, scope, kind, handle):
        row=self.db.execute('SELECT peer FROM execution_handle WHERE installation=? AND conversation=? AND kind=? AND handle=?',
                            (scope.installation,scope.conversation,kind,handle)).fetchone()
        if not row:raise Refused('unknown owned handle')
        return row['peer']

    async def start(self):
        if self.server:return
        self.runtime.fence(initialize=True)
        self.server=await asyncio.start_server(self._client,'127.0.0.1',0,limit=65536+8192)
        self.port=self.server.sockets[0].getsockname()[1]
        write_private(self.runtime.state/'broker.json',{'schemaVersion':1,'installationId':self.runtime.installation,
                      'port':self.port,'key':self.key})

    async def close(self):
        self.permits.clear()
        if self.server:
            self.server.close();await self.server.wait_closed();self.server=None

    async def _client(self, reader, writer):
        code=403;result={'error':'execution refused'}
        try:
            header=await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),5)
            if len(header)>8192:raise Refused('oversized headers')
            lines=header.decode('ascii').split('\r\n');method,route,version=lines[0].split(' ')
            headers={}
            for line in lines[1:]:
                if not line:continue
                name,value=line.split(':',1);name=name.lower()
                if name in headers:raise Refused('duplicate header')
                headers[name]=value.strip()
            if method!='POST' or 'transfer-encoding' in headers:raise Refused('unsupported request')
            size=int(headers.get('content-length','0'))
            if not 0<size<=65536:raise Refused('invalid body size')
            body=json.loads(await asyncio.wait_for(reader.readexactly(size),5))
            bearer=headers.get('authorization','').removeprefix('Bearer ')
            if route=='/check':
                scope=await self.check(bearer,body['request'],body.get('tool'),body.get('arguments'))
                result={'allowed':True,'installationId':scope.installation,'scope':scope.as_dict()}
            elif route=='/operator' and secrets.compare_digest(bearer,self.key) and self.operator:
                result=await self.operator(body)
            elif route=='/operator/scoped' and self.operator:
                result=await self.operator.scoped(bearer,body)
            elif route=='/effect' and self.operator:
                effect=self.effects.pop(digest(bearer),None)
                if not effect or time.time()>=effect['expires']:raise Refused('expired or used effect permit')
                if body!=effect['wire']:raise Refused('effect body differs from permit')
                result=await self.effect(effect['scope_token'],effect['request'],effect['call_id'],effect['operation'],effect['arguments'],effect['invoke'])
            else:raise Refused('unknown operation')
            code=200
        except OutcomeUnknown:
            code=409;result={'error':'outcome_unknown'}
        except (Exception,asyncio.CancelledError):pass
        try:
            data=json.dumps(result).encode()
            writer.write(f'HTTP/1.1 {code} Result\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\nConnection: close\r\n\r\n'.encode()+data)
            await writer.drain()
        finally:
            writer.close();await writer.wait_closed()
