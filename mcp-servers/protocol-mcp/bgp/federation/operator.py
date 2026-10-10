"""Narrow local operator bridge. No peer can mint an operator scope."""
import json
import secrets
import sqlite3
import time
from .execution import ExecutionScope, Refused, digest


class OperatorBridge:
    def __init__(self,service,broker):
        self.service=service;self.broker=broker;self.tokens={}

    def request(self,conversation,request):
        file=self.service.runtime.home/'netclaw-hud/ledger.db'
        if file.is_symlink() or not file.is_file() or file.stat().st_mode&0o077:raise Refused('private operator ledger required')
        with sqlite3.connect('file:'+str(file)+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            identity=db.execute("SELECT value FROM metadata WHERE key='installation'").fetchone()
            row=db.execute('SELECT * FROM requests WHERE id=? AND conversation=?',(request,conversation)).fetchone()
        if not identity or identity[0]!=self.service.runtime.installation or not row:raise Refused('foreign operator request')
        if row['state'] not in ('submitting','queued','running') or time.time()>=row['deadline']:raise Refused('operator request is no longer active')
        return dict(row)

    async def __call__(self,body):
        # The private HUD companion supplies these identifiers from its immutable
        # constructor snapshot, never from model-generated tool arguments.
        conversation=body.get('conversation');request=body.get('request')
        row=self.request(conversation,request)
        operation=body.get('tool');arguments=body.get('arguments')
        from .operator_policy import wire_operation
        wire=wire_operation(operation,arguments)
        if request not in self.tokens:
            scope=ExecutionScope(self.service.runtime.installation,'local-operator','operator',request,conversation,
                'operator','federation',digest(row['body']),row['deadline'],'operator')
            def current(_):
                try:self.request(conversation,request);return True
                except Exception:return False
            self.tokens[request]=self.broker.issue(scope,current)
        await self.broker.check(self.tokens[request],request)
        return self.permit(body,self.tokens[request],row['deadline'],wire)

    async def scoped(self,token,body):
        scope=await self.broker.check(token,body.get('request'))
        if scope.origin!='operator' or scope.profile!='operator' or scope.target_type!='edge_ask':raise Refused('mobile operator scope required')
        if body.get('conversation')!=scope.conversation:raise Refused('foreign operator conversation')
        from .operator_policy import wire_operation
        wire=wire_operation(body.get('tool'),body.get('arguments'))
        return self.permit(body,token,scope.deadline,wire)

    def permit(self,body,token,deadline,wire):
        permit=secrets.token_urlsafe(48)
        self.broker.effects[digest(permit)]={'expires':min(time.time()+30,deadline),'scope_token':token,
            'request':body['request'],'call_id':body.get('call_id'),'operation':body.get('tool'),'arguments':body.get('arguments'),'wire':wire,'invoke':self.invoke}
        return {'permit':permit,'url':f'http://127.0.0.1:{self.broker.port}'}

    async def invoke(self,scope,operation,arguments):
        service=self.service
        if operation=='n2n_status':
            return {'identity':service.local_identity,'harness':service.inventory._harness_card(),
                    'peers':[{'identity':p['identity'],'state':p['state']} for p in service.manager.list_peers()]}
        if operation=='n2n_risk_status':
            row=service.manager._conn.execute('SELECT risk_name,role FROM risk WHERE id=1').fetchone()
            return dict(row) if row else {'role':'standalone'}
        if operation in ('n2n_member_list','n2n_member_health'):
            from .member_inventory import stored_inventory
            return {'members':[{'member_id':m['member_id'],'state':m['state'],'profile':m['profile'],'inventory':stored_inventory(m),**service.member_liveness(m)}
                for m in service.risk.list_members() if not arguments.get('member_id') or arguments['member_id']==m['member_id']]}
        if operation=='n2n_peer_capabilities':
            peer=arguments['peer']
            if service.is_member_task(peer):
                from .member_inventory import stored_inventory
                member=service.risk.get_member(peer)
                return {'source':peer,'inventory':stored_inventory(member) if member else None}
            return {'source':peer,**(service.inventory.load_remote(peer) or {'inventory':None})}
        if operation in ('n2n_invoke','n2n_delegate'):
            peer=arguments['peer'];target=arguments['target_name'];kind=arguments.get('target_type','skill')
            if kind=='tool':
                tool_args=json.loads(arguments.get('arguments') or '{}')
                return await service.invoker.invoke_remote_tool(peer,target,tool_args)
            if service.is_member_task(peer):result=await service.delegate_to_member(peer,target,arguments.get('input_text') or '',execution_scope=scope)
            else:result=await service.invoker.submit_remote_skill(peer,target,arguments.get('input_text') or '',execution_scope=scope)
        elif operation=='n2n_route':
            result=await service.route_and_delegate(arguments['target_hint'],arguments['request_text'],execution_scope=scope)
            peer=result.get('member_id')
        elif operation=='n2n_chat':
            peer=arguments['peer'];session=arguments.get('session_id')
            if session and self.broker.owner(scope,'chat',session)!=peer:raise Refused('foreign chat session')
            result=await service.chat.open_and_send(peer,arguments['message'],session)
            if result.get('session_id'):self.broker.own(scope,'chat',result['session_id'],peer)
            return result
        elif operation in ('n2n_task_status','n2n_task_result'):
            task=arguments['task_id'];peer=self.broker.owner(scope,'task',task)
            if service.is_member_task(peer):return await service.poll_member_task(peer,task,'result' if operation.endswith('result') else 'status')
            return await service.invoker.poll_remote_task(peer,task,'result' if operation.endswith('result') else 'status')
        else:raise Refused('unqualified operator operation')
        if result.get('task_id'):
            if not peer:raise Refused('delegated task owner unavailable')
            self.broker.own(scope,'task',result['task_id'],peer)
        return result
