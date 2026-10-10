"""Bounded authenticated client for the private, qualified Hermes companion."""
import json
import os
from pathlib import Path
import re
import time
import httpx
from ledger import Ledger, HudError, identifier, TERMINAL, digest

def sanitize(value):
    if isinstance(value, dict):
        return {k:sanitize(v) for k,v in value.items() if (k.endswith('_tokens') and isinstance(v,(int,float))) or not re.search(r'key|token|password|secret|authorization|reasoning|thinking',k,re.I)}
    if isinstance(value,list): return [sanitize(v) for v in value]
    if isinstance(value,str):
        for key,secret in os.environ.items():
            if re.search(r'KEY|TOKEN|PASSWORD|SECRET',key) and len(secret)>8: value=value.replace(secret,'[redacted]')
        value=re.sub(r'(?is)<(?:think|thinking|reasoning)>.*?</(?:think|thinking|reasoning)>','',value)
        return re.sub(r'(?i)Bearer\s+\S+', 'Bearer [redacted]', value)[:65536]
    return value

class Bridge:
    def __init__(self, home, installation, *, port=None, key=None, client=None, namespace='hud'):
        self.home=Path(home);self.installation=installation
        if namespace not in ('hud','federation'):raise HudError('configuration_missing')
        self.namespace=namespace
        self.ledger=Ledger(self.home/('netclaw-'+namespace)/'ledger.db',installation)
        port=int(port or os.environ.get('NETCLAW_HERMES_'+namespace.upper()+'_PORT',8643))
        if not 1024<=port<=65535:raise HudError('configuration_missing')
        self.key=key or os.environ.get('NETCLAW_HERMES_'+namespace.upper()+'_API_KEY','')
        self.client=client or httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=5,follow_redirects=False,trust_env=False)

    def http(self, method, route, body=None, timeout=5, request=None, permit=None):
        if len(self.key)<32:raise HudError('configuration_missing','Run netclaw hud select and launch the private companion.')
        headers={'Authorization':'Bearer '+self.key}
        if request: headers.update({'Idempotency-Key':request,'X-NetClaw-Request-ID':request})
        if permit:headers['X-NetClaw-Execution-Permit']=permit
        try:
            with self.client.stream(method,route,json=body,headers=headers,timeout=timeout) as response:
                if response.status_code in (401,403):raise HudError('authentication_failed')
                if response.status_code==409:raise HudError('conversation_busy')
                if response.status_code>=400:raise HudError('upstream_failed',f'Hermes rejected the request (HTTP {response.status_code}).')
                if response.is_redirect:raise HudError('response_invalid')
                data=bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data)>4*1024*1024:raise HudError('response_invalid')
                return json.loads(data)
        except httpx.ConnectError as exc:raise HudError('runtime_stopped') from exc
        except httpx.TimeoutException as exc:raise HudError('deadline_exceeded') from exc
        except (httpx.HTTPError,ValueError) as exc:
            if isinstance(exc,HudError):raise
            raise HudError('response_invalid') from exc

    def status(self):
        return sanitize(self.http('GET','/health/detailed'))

    def open(self, conversation, seed=None, acknowledgment=None):
        row=self.ledger.open(conversation,seed,acknowledgment)
        if not row['session']:
            data=self.http('POST','/api/sessions',{'title':'NetClaw HUD '+conversation})
            session=data.get('session',{}).get('id')
            self.ledger.bind(conversation,identifier(session))
        return {'conversationId':conversation,'state':'open'}

    def submit(self, conversation, request, nonce, text, deadline_ms=900000, execution_scope=None, permit=None):
        if self.namespace=='federation' and (execution_scope is None or not permit):raise HudError('owner_invalid')
        row,created=self.ledger.admit(conversation,request,nonce,text,deadline_ms,execution_scope)
        if not created:return self.project(row)
        conv=self.ledger.conversation(conversation)
        if not conv['session']:
            self.ledger.update(conversation,request,'failed',result={'code':'configuration_missing'})
            raise HudError('configuration_missing')
        body={'input':text,'session_id':conv['session']}
        with self.ledger.db() as db:
            count=db.execute('SELECT count(*) FROM requests WHERE conversation=?',(conversation,)).fetchone()[0]
        if count==1 and json.loads(conv['seed']):body['conversation_history']=json.loads(conv['seed'])
        try:
            options={'permit':permit} if permit else {}
            data=self.http('POST','/v1/runs',body,timeout=min(10,deadline_ms/1000),request=request,**options)
            native=data.get('id') or data.get('run_id')
            if not isinstance(native,str):raise HudError('response_invalid')
            row=self.ledger.update(conversation,request,'queued',run_id=identifier(native))
        except Exception:
            # Even a malformed/error response may follow admission. Never infer nonexecution.
            row=self.ledger.update(conversation,request,'unknown',result={'code':'outcome_unknown','recovery':'Check owned history/status; do not resend this operation.'})
        return self.project(row)

    def request_status(self, conversation, request):
        row=self.ledger.request(conversation,request)
        if row['state'] not in TERMINAL and row['run_id']:
            try:
                data=self.http('GET',f"/v1/runs/{identifier(row['run_id'])}")
                state=data.get('status')
                if state=='awaiting_approval':state='waiting_approval'
                if state not in ('queued','running','waiting_approval','stopping',*TERMINAL):raise HudError('response_invalid')
                if ((self.namespace=='federation' and row['state']=='unknown') or time.time()>row['deadline']) and state not in TERMINAL:state='unknown'
                result={'output':sanitize(data.get('output') or ''),'runtime':sanitize(data.get('runtime') or {}),
                        'usage':sanitize(data.get('usage')) if data.get('usage') else None,
                        'approval':sanitize(data.get('approval') or data.get('pending_approval')),
                        'code':'outcome_unknown' if state=='unknown' else None}
                row=self.ledger.update(conversation,request,state,result=result)
            except HudError:
                if time.time()>row['deadline']:row=self.ledger.update(conversation,request,'unknown',result={'code':'outcome_unknown'})
        elif row['state']=='submitting':
            row=self.ledger.update(conversation,request,'unknown',result={'code':'outcome_unknown'})
        return self.project(row)

    def project(self,row):
        result=json.loads(row['result']) if row['result'] else {}
        return {'requestId':row['id'],'conversationId':row['conversation'],'state':row['state'],**result,
                'runtimeKind':'hermes','mayHaveExecuted':True}

    def history(self, conversation, cursor=0, limit=200):
        conv=self.ledger.conversation(conversation)
        if not conv['session']:return {'messages':[],'hasMore':False}
        if not 1<=limit<=200 or not 0<=int(cursor)<=1000000:raise HudError('input_invalid')
        data=self.http('GET',f"/api/sessions/{identifier(conv['session'])}/messages?limit={limit}&offset={int(cursor)}&order=latest&include_compacted=true")
        rows=data.get('messages',data.get('data',[]))
        messages=[]
        for row in rows:
            if row.get('role') not in ('user','assistant'):continue
            content=row.get('content')
            if isinstance(content,list):content='\n'.join(p.get('text','') for p in content if p.get('type')=='text')
            if isinstance(content,str) and content.strip():messages.append({'role':row['role'],'content':sanitize(content)})
        return {'messages':messages,'hasMore':bool(data.get('has_more')) or len(rows)==limit,'nextCursor':int(cursor)+len(rows)}

    def approval(self,conversation,request,approval_id,choice):
        if choice not in ('once','deny'):raise HudError('input_invalid')
        row=self.ledger.request(conversation,request)
        current=self.request_status(conversation,request)
        approval=current.get('approval') or {}
        if (approval.get('request_id') or approval.get('id')) != approval_id:raise HudError('input_invalid','Approval is no longer pending.')
        self.http('POST',f"/v1/runs/{identifier(row['run_id'])}/approval",{'request_id':identifier(approval_id),'choice':choice})
        return self.request_status(conversation,request)

    def stop(self,conversation,request):
        row=self.ledger.request(conversation,request)
        if not row['run_id']:return self.project(row)
        self.http('POST',f"/v1/runs/{identifier(row['run_id'])}/stop",{})
        if row['state'] not in TERMINAL:row=self.ledger.update(conversation,request,'stopping')
        return self.project(row)
