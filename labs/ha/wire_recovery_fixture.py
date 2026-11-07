#!/usr/bin/env python3
"""Coordinator-only FIXTURE: wire loss, paused leader and owned trust negatives.

No import starts a process. Effects are controlled callbacks, never model/MCP.
Production Border/Member operations, signed result/ACK persistence, actual TLS
and etcd stay on the exercised path. Each mutation is one-shot and journaled.
"""
import argparse
import asyncio
import base64
import hashlib
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import ssl
import stat
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    sys.path[:0] = [str(ROOT), str(ROOT/'mcp-servers/protocol-mcp'), str(ROOT/'scripts/lib')]
from labs.ha import process_fixture as base
from labs.ha.process_fixture import decode, digest, encode, need, owned_directory, private, read_private

EXTRA = {
    'owner-prepare': {'client_nonce'}, 'owner-decide': {'operation_id','revision','review_digest'},
    'owner-reconcile': {'operation_id'}, 'member-row': {'operation_id'},
    'arm-loss': {'operation_id','fault'}, 'capture': {'context','via_node_id'},
    'consume-held': set(), 'tls-rejections':set(), 'in2n-rejections':set(), 'member-health':set(), 'wire-role': {'via_node_id','method'},
}
MEMBER = {'member-row','arm-loss','capture','consume-held','wire-role'}
MUTATIONS = base.MUTATIONS | {'owner-prepare','owner-decide','owner-reconcile','arm-loss','capture','consume-held','wire-role'}


def validate_request(raw, config):
    value = decode(raw)
    if value.get('method') not in EXTRA: return base.validate_request(raw,config)
    # Reuse exact envelope/authentication validation without widening production
    # or the base worker's command surface.
    probe = dict(value,method='status',params={})
    base.validate_request(encode(probe),config)
    method,params = value['method'],value['params']
    need(isinstance(params,dict) and set(params)==EXTRA[method], 'control_fields')
    need((method in MEMBER) == (config['role']=='member'), 'control_role')
    if 'operation_id' in params: need(str(uuid.UUID(params['operation_id']))==params['operation_id'],'control_operation_id')
    if 'via_node_id' in params: need(str(uuid.UUID(params['via_node_id']))==params['via_node_id'],'control_ingress')
    if method=='owner-prepare': need(isinstance(params['client_nonce'],str) and 1<=len(params['client_nonce'])<=120,'control_nonce')
    if method=='owner-decide':
        need(type(params['revision']) is int and params['revision']>0,'control_revision')
        need(isinstance(params['review_digest'],str) and len(params['review_digest'])==64
             and all(c in '0123456789abcdef' for c in params['review_digest']),'control_digest')
    if method=='arm-loss': need(params['fault'] in ('result-reply','ack-delivery'),'control_fault')
    if method=='wire-role': need(params['method'] in ('n2n/cluster/status','n2n/tools/call','execution/admin'),'control_method')
    if method=='capture':
        # The original member admission validator supplies the full context check.
        altered=dict(value,method='admit',params=dict(params,kind='model',ordinal=1,mode='complete'))
        base.validate_request(encode(altered),config)
    return value


async def control(config,method,params=None):
    request={'schema_version':1,'run_id':config['run_id'],'request_id':str(uuid.uuid4()),
             'method':method,'params':params or {},'token':config['control_token']}
    validate_request(encode(request),config)
    reader,writer=await asyncio.wait_for(asyncio.open_unix_connection(config['control_socket'],limit=base.MAX_RESPONSE+1),2)
    try:
        writer.write(encode(request)+b'\n');await writer.drain()
        raw=await asyncio.wait_for(reader.readline(),24)
        need(raw.endswith(b'\n'),'control_reply_unknown');value=decode(raw,base.MAX_RESPONSE)
        need(value['request_id']==request['request_id'] and value['boot_id']==config['launch_id']
             and value['classification']=='FIXTURE','control_reply_identity')
        if not value['ok']: raise base.ControlError(value['error'])
        return value['result']
    finally: writer.close();await writer.wait_closed()


class Worker(base.Worker):
    def __init__(self,config):
        super().__init__(config)
        self.operations=None;self.loss=None;self.held=[];self.proof_observations=[];self.tls_context_original=None;self.tls_audit_failed=False;self.in2n_init_original=None;self.in2n_audit_failed=False
        for name in ('audit','wire-loss','tls-rejections','in2n-rejections'):
            (self.home/name).mkdir(mode=0o700,exist_ok=True);owned_directory(self.home/name)

    def audit(self,event,record):
        rows=list((self.home/'audit').iterdir());need(len(rows)<64,'fixture_audit_capacity')
        name=f'{len(rows):03d}-{event}.json'
        private(self.home/'audit'/name,{'class':'FIXTURE','event':event,'record':record})
        return 'controlled-wire-fixture/'+name

    def effect(self,operation_id,kind,ordinal):
        need(len(self.effects())<8,'fixture_effect_capacity')
        value={'class':'FIXTURE','operation_id':operation_id,'kind':kind,'ordinal':ordinal,
               'controlled_callback':True,'member_incarnation':self.journal.incarnation,
               'observed_monotonic_ns':time.monotonic_ns()}
        private(self.home/'effects'/f'{operation_id}-{kind}{ordinal}.json',value)
        return value

    async def start(self):
        if self.config['role']=='border':
            from bgp.federation import exporter_tls
            self.tls_context_original=exporter_tls._context
            exporter_tls._context=audited_tls_context(self.tls_context_original,self.home/'tls-rejections',
                lambda:setattr(self,'tls_audit_failed',True))
            from bgp.federation.ha.internal import AttachmentChannel
            self.in2n_init_original=AttachmentChannel.__init__
            AttachmentChannel.__init__=audited_attachment_init(self.in2n_init_original,self.home/'in2n-rejections',
                lambda:setattr(self,'in2n_audit_failed',True))
        await super().start()
        if self.config['role']=='border':
            from bgp.federation.ha.border import ClusterBorderOperations
            self.operations=ClusterBorderOperations(self.node,state_dir=self.home/'protected',
                member_channels=self.channels,audit_writer=self.audit)
            return
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.member import ClusterMemberOperations
        from bgp.federation.protected_docker import DockerExecutor
        worker=self
        class ControlledExecutor(DockerExecutor):
            def __init__(self): self.ollama={'controlled_fixture':True}
            async def run(self,approved,gate,*,ha_admission=None):
                async def effect(kind,ordinal): return worker.effect(approved['operation_id'],kind,ordinal)
                await ha_admission('model',1,'a'*64,lambda:effect('model',1))
                evidence=await gate(approved['tool_call'],lambda:ha_admission(
                    'tool',1,c.sha256(approved['tool_call']),lambda:effect('tool',1)))
                await ha_admission('model',2,'b'*64,lambda:effect('model',2))
                return {'output':{'class':'FIXTURE','controlled_result':approved['operation_id']},
                        'tool_evidence':evidence,'usage':{'available':False},'effective_model_profile':approved['model_profile']}
            def close(self): pass
        dummy=SimpleNamespace(node_id=self.manifest.nodes[0]['node_id'],authority=SimpleNamespace(epoch=1))
        review=base.fixture_review(self.manifest,dummy,self.member['binding'])
        catalog={'member':self.member['binding'],'model_profiles':[review['model_profile']],
            'tools':[dict(review['tool_call'],limits={k:v for k,v in review['limits'].items() if k!='expires_at_ms'})]}
        self.operations=ClusterMemberOperations(SimpleNamespace(db_path=self.home/'federation.db'),
            manifest=self.manifest,identity=self.member['binding'],certificate=self.member['certificate'],
            private_key=read_private(self.config['member_key_file']).decode(),attachments=self.attachments,
            journal=self.journal,catalog_provider=lambda:catalog,executor=ControlledExecutor(),audit_writer=self.audit)
        async def result(channel,params):
            envelope=await self.operations.member_result(channel,params)
            if self.loss=={'operation_id':params['operation_id'],'fault':'result-reply'}:
                self.drop(channel,params['operation_id'],'result-reply',digest(envelope))
                await channel.close();raise ConnectionError('controlled_result_reply_loss')
            return envelope
        async def ack(channel,params):
            if self.loss=={'operation_id':params['ack']['payload']['operation_id'],'fault':'ack-delivery'}:
                self.drop(channel,params['ack']['payload']['operation_id'],'ack-delivery',digest(params['ack']))
                await channel.close();raise ConnectionError('controlled_ack_delivery_loss')
            return await self.operations.acknowledge(channel,params)
        self.attachments.handlers.update({'execution/catalog':self.operations.member_catalog,
            'execution/submit':self.operations.submit,'execution/status':self.operations.member_status,
            'execution/result':result,'execution/ack':ack})
        original=self.attachments.send_admission
        async def observed(request):
            proof=await original(request);self.observe_proof(proof);return proof
        self.attachments.send_admission=observed

    def observe_proof(self,proof):
        need(len(self.proof_observations)<16,'fixture_proof_capacity')
        value=proof['payload']
        self.proof_observations.append({'epoch':value['claim']['epoch'],'leader':value['claim']['leader'],
            'commit_revision':value['commit_revision'],'request_sha256':digest(value['claim']['request']),
            'observed_monotonic_ns':time.monotonic_ns()})

    def drop(self,channel,operation_id,fault,envelope_sha256):
        need(channel.trusted and channel.strict and channel.attestation=='possession','loss_requires_authenticated_wire')
        self.loss=None
        private(self.home/'wire-loss'/f'{operation_id}-{fault}.json',{
            'class':'FIXTURE','operation_id':operation_id,'fault':fault,'envelope_sha256':envelope_sha256,
            'peer':channel.protected_peer_binding,'tls_profile':channel.writer.get_extra_info('tls_profile'),
            'observed_monotonic_ns':time.monotonic_ns(),'interception':
                'after production result lookup, before reply write' if fault=='result-reply' else
                'after authenticated RPC delivery, before production acknowledge/persistence',
            'automatic_retry':False})

    async def command(self,method,params):
        from bgp.federation import protected_contract as c
        if method=='status':
            value=await super().command(method,params)
            if self.attachments:
                value.update(proof_observations=self.proof_observations,held_proofs=len(self.held),
                    wire_losses=[decode(read_private(p)) for p in sorted((self.home/'wire-loss').glob('*.json'))],
                    has_consensus_credentials='store' in self.config,has_network_listener=self.listener is not None)
            return value
        if method=='tls-rejections':
            need(not self.tls_audit_failed,'tls_observer_failed')
            return [decode(read_private(p)) for p in sorted((self.home/'tls-rejections').glob('*.json'))]
        if method=='in2n-rejections':
            need(not self.in2n_audit_failed,'in2n_observer_failed')
            return [decode(read_private(p)) for p in sorted((self.home/'in2n-rejections').glob('*.json'))]
        if method=='member-health':
            value=await self.operations._send(self.member['binding'],'execution/catalog',{})
            need(value['member']==self.member['binding'],'member_health_binding_changed')
            return {'member':value['member'],'catalog_sha256':digest(value),'node_id':self.node.node_id,
                    'observed_monotonic_ns':time.monotonic_ns(),'authenticated_catalog_response':True}
        if method.startswith('owner-'):
            context={'access_mode':'open-lab','installation_id':self.operations.identity['installation_id'],**self.manifest.audience}
            if method=='owner-prepare':
                catalog=await self.operations.catalog({'auth_context':context});need(len(catalog['members'])==1,'one_fixture_member_required')
                member=catalog['members'][0]
                return await self.operations.prepare(dict(params,auth_context=context,catalog_revision=catalog['revision'],
                    member_id=member['member']['member_id'],model_profile_id=member['model_profiles'][0]['profile_id'],
                    tool=member['tools'][0]['tool'],arguments=member['tools'][0]['arguments']))
            if method=='owner-decide': return await self.operations.decision(dict(params,auth_context=context,decision='approve'))
            return await self.operations.reconcile(dict(params,auth_context=context))
        if method=='member-row':
            row=self.operations.store.get('member',params['operation_id'])
            return row
        if method=='arm-loss':
            need(self.loss is None and len(list((self.home/'wire-loss').iterdir()))<2,'fixture_loss_already_armed')
            row=self.operations.store.get('member',params['operation_id'])
            need(row is not None and row['receipt'] is not None and row['ack'] is None,'original_result_required')
            self.loss=dict(params);return {'armed':dict(params),'observed_monotonic_ns':time.monotonic_ns()}
        if method=='admit':
            need(params['mode']=='complete','wire_fixture_hold_refused')
            async def send(request):
                channel=self.attachments.channels[params['via_node_id']]
                proof=await channel.call('execution/admission',request,timeout=5)
                self.observe_proof(proof);return proof
            async def effect():return self.effect(params['context']['operation_id'],params['kind'],params['ordinal'])
            result=await self.journal.run(params['context'],params['kind'],params['ordinal'],
                c.sha256({'kind':params['kind'],'ordinal':params['ordinal']}),send,effect)
            return {'state':'finished','effect':result,'proof_observation':self.proof_observations[-1]}
        if method=='capture':
            need(not self.held,'held_proofs_already_exist')
            channel=self.attachments.channels[params['via_node_id']]
            for kind in ('model','tool'):
                request,started=self.journal.begin(params['context'],kind,1,c.sha256({'kind':kind,'ordinal':1}))
                proof=await channel.call('execution/admission',request,timeout=5)
                self.observe_proof(proof);self.held.append((request,proof,started))
            for _,_,started in self.held:self.journal.fresh(started)
            return {'held':[{'request':r,'proof':p,'started':s} for r,p,s in self.held],
                    'proof_observations':self.proof_observations,'member_incarnation':self.journal.incarnation}
        if method=='consume-held':
            from bgp.federation.ha.config import HAError
            need(len(self.held)==2,'held_proofs_required');before=self.effects();results=[]
            for request,proof,started in self.held:
                try:
                    self.journal.consume(request,proof,started)
                    raise AssertionError('paused_authority_proof_accepted')
                except HAError as exc:
                    need(exc.code=='admission_expired','wrong_paused_proof_refusal')
                    self.journal._terminal(request,'unknown')
                    results.append({'kind':request['kind'],'code':exc.code,'proof_epoch':proof['payload']['claim']['epoch'],
                        'elapsed_ms':(time.monotonic()-started[0])*1000,'observed_monotonic_ns':time.monotonic_ns()})
            need(self.effects()==before,'stale_proof_invoked_effect')
            return {'refusals':results,'proof_observations':self.proof_observations,'effects_before':before,'effects_after':self.effects()}
        if method=='wire-role':
            from bgp.federation.ha.internal import AttachmentChannel
            from bgp.federation.channel import RpcError
            channel=self.attachments.channels[params['via_node_id']]
            # Deliberately bypass only the caller's local allowlist. Actual TLS
            # request reaches the production receiver, whose allowlist must deny.
            try:
                await super(AttachmentChannel,channel).call(params['method'],{},timeout=3)
                raise AssertionError('wire_role_escalation_accepted')
            except RpcError as exc:
                need(exc.message=='attachment_method_refused','wrong_role_refusal')
                return {'method':params['method'],'code':exc.code,'message':exc.message,
                        'authenticated_node_id':params['via_node_id'],'receiver_refused':True}
        return await super().command(method,params)

    async def _serve_one(self,reader,writer):
        request=None
        try:
            raw=await asyncio.wait_for(reader.readline(),2);need(raw.endswith(b'\n'),'control_frame_required')
            request=validate_request(raw,self.config)
            if request['method'] in MUTATIONS:base.claim_command(self.home,request)
            result=await asyncio.wait_for(self.command(request['method'],request['params']),21)
            answer={'ok':True,'result':result}
        except BaseException as exc:
            if isinstance(exc,asyncio.CancelledError):raise
            answer={'ok':False,'error':getattr(exc,'code',type(exc).__name__)}
        answer.update(schema_version=1,request_id=request['request_id'] if request else None,
            boot_id=self.boot,pid=os.getpid(),classification='FIXTURE')
        raw=encode(answer);need(len(raw)<=base.MAX_RESPONSE,'control_response_bound')
        try:writer.write(raw+b'\n');await asyncio.wait_for(writer.drain(),2)
        finally:writer.close();await writer.wait_closed()

    async def close(self):
        if self.config['role']=='member' and self.operations:await self.operations.close()
        await super().close()
        if self.tls_context_original is not None:
            from bgp.federation import exporter_tls
            exporter_tls._context=self.tls_context_original
        if self.in2n_init_original is not None:
            from bgp.federation.ha.internal import AttachmentChannel
            AttachmentChannel.__init__=self.in2n_init_original


async def worker_main(config_file):
    os.umask(0o077);config=decode(read_private(config_file));worker=Worker(config)
    path=Path(config['control_socket']);owned_directory(path.parent)
    need(not path.exists() and len(str(path).encode())<100,'control_socket_in_use')
    for sig in (signal.SIGTERM,signal.SIGINT):asyncio.get_running_loop().add_signal_handler(sig,worker.stop.set)
    server=None
    async def watch():
        deadline=time.monotonic()+600
        while not worker.stop.is_set():
            if os.getppid()!=config['coordinator_pid'] or time.monotonic()>deadline:worker.stop.set();return
            await asyncio.sleep(1)
    task=asyncio.create_task(watch())
    try:
        await worker.start();server=await asyncio.start_unix_server(worker.serve,str(path),limit=base.MAX_REQUEST)
        path.chmod(0o600);await worker.stop.wait()
    finally:
        task.cancel();await asyncio.gather(task,return_exceptions=True)
        if server:server.close()
        await asyncio.wait_for(worker.close(),10)
        if server:await server.wait_closed()


class WireFixture(base.ProcessFixture):
    async def call(self,name,method,params=None):return await control(self.configs[name],method,params)
    async def start(self,name):
        need(name not in self.children or self.children[name].returncode is not None,'owned_process_running')
        need(base.source_identity()['sha256']==self.source['sha256'],'worker_source_changed')
        config=dict(self.configs[name],launch_id=str(uuid.uuid4()),control_token=secrets.token_hex(32))
        socket_path=Path(config['control_socket'])
        if socket_path.exists():
            info=socket_path.lstat(); old=self.records[name]
            need(stat.S_ISSOCK(info.st_mode) and info.st_uid==os.getuid() and (info.st_dev,info.st_ino)==tuple(old['socket_identity']), 'stale_socket_identity_changed')
            socket_path.unlink()
        self.boots[name]+=1; number=self.boots[name]; home=Path(config['home'])
        file=home/f'config-{number}.json';private(file,config);self.configs[name]=config
        command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'worker','--config',str(file)]
        private(home/f'launch-{number}.claim.json',{'command':command,'config_sha256':hashlib.sha256(read_private(file)).hexdigest(),
            'source_sha256':self.source['sha256'],'launch_id':config['launch_id']})
        out=os.open(home/f'worker-{number}.stdout',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        err=os.open(home/f'worker-{number}.stderr',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        try:
            process=await asyncio.create_subprocess_exec(*command,stdout=out,stderr=err,
                env={'PATH':os.defpath,'HOME':str(home)},cwd=str(home),start_new_session=True)
        finally:os.close(out);os.close(err)
        self.children[name]=process
        private(home/f'spawn-{number}.json',{'pid':process.pid,'command':command,'launch_id':config['launch_id'],
            'source_sha256':self.source['sha256'],'config_sha256':hashlib.sha256(read_private(file)).hexdigest(),
            'observed_at_ms':int(time.time()*1000)})
        async def ready():
            need(process.returncode is None,'worker_exited_during_start')
            return await control(config,'status')
        status=await base.eventually(ready)
        need(status['pid']==process.pid and status['boot_id']==config['launch_id'],'owned_pid_mismatch')
        command_line=subprocess.run(['ps','-p',str(process.pid),'-o','command='],capture_output=True,check=True,timeout=2).stdout.decode().strip()
        info=socket_path.lstat()
        record={'pid':process.pid,'command':command,'command_line':command_line,'source_sha256':self.source['sha256'],
            'boot_id':config['launch_id'],'socket_identity':[info.st_dev,info.st_ino],
            'python_sha256':hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
            **{key:status[key] for key in ('node_id','authority_incarnation','member_incarnation') if key in status}}
        private(home/f'owned-{number}.json',record);self.records[name]=record
        return status


    async def leader_excluding(self,excluded=(),minimum_epoch=0):
        async def find():
            for name,process in self.children.items():
                if name=='member' or name in excluded or process.returncode is not None:continue
                status=await self.call(name,'status')
                if status.get('local_leader') and status['epoch']>minimum_epoch:return name,status
        return await base.eventually(find,seconds=60)

    def observe_owned(self,name):
        from ha_cluster import process_observation
        process=self.children[name];record=self.records[name]
        need(process.pid==record['pid'] and process.returncode is None,'owned_process_not_running')
        observed=process_observation(process.pid)
        need(observed['present'] and observed['uid']==os.getuid(),'owned_process_missing')
        command_line=subprocess.run(['ps','-p',str(process.pid),'-o','command='],capture_output=True,check=True,timeout=2).stdout.decode().strip()
        need(command_line==record['command_line'],'owned_process_identity_changed')
        return observed

    async def pause(self,name):
        baseline=self.observe_owned(name);point=time.monotonic_ns()
        private(self.path/'leader-pause.claim.json',{'pid':self.children[name].pid,'baseline':baseline,
            'signal':'SIGSTOP','observed_monotonic_ns':point})
        os.kill(self.children[name].pid,signal.SIGSTOP);self.paused_name=name
        async def stopped():
            actual=self.observe_owned(name)
            need(actual['start_id']==baseline['start_id'] and actual['command_sha256']==baseline['command_sha256'],'owned_process_identity_changed')
            state=subprocess.run(['ps','-p',str(self.children[name].pid),'-o','state='],capture_output=True,check=True,timeout=2).stdout.decode().strip()
            return {'state':state,'identity':actual,'observed_monotonic_ns':time.monotonic_ns()} if 'T' in state else None
        actual=await base.eventually(stopped,seconds=5)
        private(self.path/'leader-pause.verified.json',actual)
        return point,actual

    async def resume(self,name):
        expected=decode(read_private(self.path/'leader-pause.claim.json'))['baseline']
        observed=self.observe_owned(name)
        need(all(observed[k]==expected[k] for k in ('start_id','command_sha256')),'owned_process_identity_changed')
        private(self.path/'leader-resume.claim.json',{'pid':self.children[name].pid,'signal':'SIGCONT',
            'observed_monotonic_ns':time.monotonic_ns()})
        os.kill(self.children[name].pid,signal.SIGCONT)
        async def resumed():
            state=subprocess.run(['ps','-p',str(self.children[name].pid),'-o','state='],capture_output=True,check=True,timeout=2).stdout.decode().strip()
            return {'state':state,'observed_monotonic_ns':time.monotonic_ns()} if 'T' not in state else None
        actual=await base.eventually(resumed,seconds=5);private(self.path/'leader-resume.verified.json',actual)
        self.paused_name=None
        return actual


def timings(fault,detected,replaced,recovered):
    need(0<fault<=detected<=replaced<=recovered,'invalid_fault_timeline')
    return {'fault_monotonic_ns':fault,'fault_observed_monotonic_ns':detected,
        'replacement_observed_monotonic_ns':replaced,'recovery_observed_monotonic_ns':recovered,
        'failure_to_detection_ms':(detected-fault)/1e6,'failure_to_new_authority_ms':(replaced-fault)/1e6,
        'failure_to_service_recovery_ms':(recovered-fault)/1e6,
        'observation_semantics':'coordinator monotonic observations; includes polling and control round trip'}


async def result_loss_row(fixture,fault):
    from bgp.federation import protected_contract as c
    label='lost-'+fault;leader,status=await fixture.leader();old_epoch=status['epoch']
    before=await fixture.call('member','status')
    row=await fixture.call(leader,'owner-prepare',{'client_nonce':label+'-'+str(uuid.uuid4())})
    original=await fixture.call(leader,'owner-decide',{key:row[key] for key in ('operation_id','revision','review_digest')})
    operation_id=original['operation_id']
    async def finished():
        member=await fixture.call('member','member-row',{'operation_id':operation_id})
        return member if member and member['receipt'] is not None else None
    member=await base.eventually(finished)
    receipt=member['receipt'];payload=c.verify(receipt,fixture.member_certificate,c.HA_RESULT)
    need(payload['outcome']=='succeeded' and member['ack'] is None,'controlled_result_missing')
    effects=(await fixture.call('member','status'))['effects'];need(len(effects)==len(before['effects'])+3,'controlled_callback_count')
    await fixture.call('member','arm-loss',{'operation_id':operation_id,'fault':fault})
    loss_started=time.monotonic_ns()
    await fixture.call(leader,'owner-reconcile',{'operation_id':operation_id})
    observed=await fixture.call('member','status');loss_detected=time.monotonic_ns()
    losses=[x for x in observed['wire_losses'] if x['operation_id']==operation_id and x['fault']==fault]
    need(len(losses)==1 and observed['effects']==effects,'wire_loss_not_observed')
    member_lost=await fixture.call('member','member-row',{'operation_id':operation_id})
    cluster_lost=await fixture.call(leader,'get',{'operation_id':operation_id})
    need(member_lost['receipt']==receipt and member_lost['ack'] is None,'wire_fault_did_not_leave_ack_pending')
    need((cluster_lost['ack'] is None)==(fault=='result-reply'),'wrong_wire_loss_boundary')
    if fault=='result-reply':need(cluster_lost['result_ref'] is None,'lost_result_was_accepted')
    else:need(cluster_lost['result_ref'] is not None and not cluster_lost.get('ack_delivered',False),'lost_ack_not_pending')
    private(fixture.path/(label+'-before-death.json'),{'original':original,'member':member_lost,
        'cluster':cluster_lost,'wire_loss':losses[0],'effects':effects})
    fault_at=time.monotonic_ns();await fixture.kill(leader,label+'-leader');detected=time.monotonic_ns()
    successor,current=await fixture.leader_excluding((leader,),old_epoch);replaced=time.monotonic_ns()
    await fixture.attached(2)
    recovered=await fixture.call(successor,'owner-reconcile',{'operation_id':operation_id});recovery_at=time.monotonic_ns()
    durable=await fixture.call('member','member-row',{'operation_id':operation_id})
    cluster=await fixture.call(successor,'get',{'operation_id':operation_id})
    need(durable['receipt']==receipt and durable['state']=='acknowledged' and durable['ack']==cluster['ack'],'original_result_ack_not_durable')
    ack=durable['ack'];acceptance=fixture.manifest.node(ack['payload']['acceptance']['node_id'])
    c.verify(ack,acceptance['certificate'],c.HA_ACK)
    need(cluster['ack_delivered'] is True and recovered['result']['verified'] is True,'successor_reconciliation_incomplete')
    if fault=='ack-delivery':need(ack==cluster_lost['ack'],'original_ack_changed')
    else:need(ack['payload']['acceptance']['node_id']==current['node_id'],'successor_ack_required')
    after=await fixture.call('member','status');need(after['effects']==effects,'recovery_replayed_effect')
    for key in ('operation_id','attempt_id','approval_digest'):need(durable[key]==member[key],'original_identity_changed')
    result={'class':'FIXTURE','passed':True,'case':label,'original_operation_id':operation_id,
        'actual_authenticated_in2n':True,'wire_loss':losses[0],'original_signed_result':receipt,'durable_member_ack':ack,
        'original_member_state':member['state'],'recovered_member_state':durable['state'],
        'effects_before_fault':effects,'effects_after_recovery':after['effects'],'model_calls':0,'native_tool_calls':0,
        'timing':timings(loss_started,loss_detected,replaced,recovery_at),
        'authority_loss_timing':timings(fault_at,detected,replaced,recovery_at),'old_epoch':old_epoch,'new_epoch':current['epoch'],
        'native_profile_qualified':False}
    private(fixture.path/(label+'.json'),result)
    await fixture.start(leader);await fixture.mesh(3);await fixture.attached(3)
    return result


async def paused_row(fixture):
    leader,status=await fixture.leader();epoch=status['epoch']
    row=await fixture.call(leader,'prepare',{'client_nonce':'paused-'+str(uuid.uuid4())})
    row=await fixture.call(leader,'dispatch',{'operation_id':row['operation_id']})
    context={k:row[k] for k in ('operation_id','attempt_id','approval_digest')}
    held=await fixture.call('member','capture',{'context':context,'via_node_id':status['node_id']})
    need(all(x['proof']['payload']['claim']['epoch']==epoch for x in held['held']),'captured_authority_changed')
    private(fixture.path/'paused-held-proofs.json',held)
    paused=False
    try:
        fault_at,observation=await fixture.pause(leader);paused=True
        successor,current=await fixture.leader_excluding((leader,),epoch);replaced=time.monotonic_ns()
        before=await fixture.call('member','status')
        need(before['proof_observations']==held['proof_observations'],'member_observed_new_authority_before_stale_gate')
        refused=await fixture.call('member','consume-held')
        need(refused['proof_observations']==held['proof_observations'],'member_observed_new_authority_at_stale_gate')
        await fixture.resume(leader);paused=False
        await fixture.mesh(3);await fixture.attached(3)
        fresh=await fixture.call('member','admit',{'context':context,'kind':'model','ordinal':2,'mode':'complete',
                                                  'via_node_id':current['node_id']})
        recovered=time.monotonic_ns();after=await fixture.call('member','status')
        need(fresh['proof_observation']['epoch']>epoch,'replacement_proof_epoch_required')
        need(len(after['effects'])==len(before['effects'])+1,'replacement_admission_failed')
        await fixture.call(successor,'unknown',{'operation_id':row['operation_id']})
        result={'class':'FIXTURE','passed':True,'case':'paused-leader-unaware-member','operation_id':row['operation_id'],
            'old_epoch':epoch,'new_epoch':current['epoch'],'paused_process':observation,
            'held_proof_refusals':refused,'replacement_admission':fresh,
            'member_authority_observations_unchanged_before_stale_gate':True,
            'timing':timings(fault_at,observation['observed_monotonic_ns'],replaced,recovered),
            'effects_before':before['effects'],'effects_after':after['effects'],
            'model_calls':0,'native_tool_calls':0,'native_profile_qualified':False}
        private(fixture.path/'paused-leader-unaware-member.json',result);return result
    finally:
        if getattr(fixture,'paused_name',None)==leader:await fixture.resume(leader)


async def bad_hello(manifest,endpoint,ca,binding,key,*,fault,old_proof=None):
    from bgp.federation import exporter_tls
    from bgp.federation.channel import RpcError
    from bgp.federation.internal_channel import read_border_preamble
    from bgp.federation.ha.internal import AttachmentChannel,transcript
    from bgp.federation.ha.signatures import sign,verify
    async def current(channel):pass
    reader,writer=await exporter_tls.open_connection(endpoint['host'],endpoint['port'],ca_file=ca,
                                                    server_hostname=endpoint['server_name'])
    channel=None
    try:
        nonce=await read_border_preamble(reader);need(nonce is not None,'test_listener_not_in2n')
        node=next(n for n in manifest.nodes if n['endpoints']['in2n']==endpoint)
        channel=AttachmentChannel(reader,writer,local_identity=binding['member_id'],member_id=binding['member_id'],
            is_border_side=False,nonce=nonce,handlers={},current=current)
        await channel.start();member_nonce=secrets.token_bytes(32)
        params={'binding_profile':'in2n-tls-exporter-v1','member_nonce':member_nonce.hex()}
        result=await channel.call('in2n/attest',params,timeout=4)
        expected=transcript(manifest,node['node_id'],channel,member_nonce)
        need(verify(result['cluster_attestation'],node['certificate'],'attachment-border')==expected,'test_attestation_invalid')
        proof=sign('attachment-member',dict(expected,member=binding,
            role='cluster-border' if fault=='wrong-role' else 'execution-member'),key)
        if fault=='capture':return proof
        sent=old_proof if fault=='replay' else proof
        try:
            await channel.call('in2n/hello',dict(params,member=binding,proof=sent),timeout=4)
            raise AssertionError('untrusted_hello_accepted')
        except (RpcError,ConnectionError) as exc:
            # The production receiver can close after sending its refusal. Its
            # exact observed auth error below is authoritative, not this closure.
            if isinstance(exc,ConnectionRefusedError):raise
            return {'fault':fault,'client_observation':type(exc).__name__,
                'client_code':getattr(exc,'code',None),'proof_sha256':digest(sent),
                'params_sha256':digest(dict(params,member=binding,proof=sent)),
                'tls_bound_transcript_sha256':digest(expected)}
    finally:
        if channel:await channel.close()
        else:writer.close();await writer.wait_closed()


HELLO_REFUSALS={'not-enrolled':'member_not_enrolled','wrong-role':'attachment_proof_mismatch',
                'replay':'attachment_proof_mismatch'}


def audited_attachment_init(original,directory,on_error):
    """Observe the exact production hello exception; always rethrow unchanged."""
    def initialize(channel,*args,**options):
        handlers=options.get('handlers',{})
        if options.get('is_border_side') and 'in2n/hello' in handlers:
            hello=handlers['in2n/hello']
            async def observed(ch,params):
                try:return await hello(ch,params)
                except Exception as exc:
                    try:
                        rows=list(directory.iterdir());need(len(rows)<64,'in2n_observation_capacity')
                        private(directory/f'{len(rows):03d}.json',{'class':'FIXTURE','method':'in2n/hello',
                            'params_sha256':digest(params),'proof_sha256':digest(params.get('proof')),
                            'error_code':getattr(exc,'code',None),'error_type':type(exc).__name__,
                            'trusted':ch.trusted,'tls_profile':ch.writer.get_extra_info('tls_profile'),
                            'observed_monotonic_ns':time.monotonic_ns()})
                    except BaseException:on_error();raise
                    raise
            options=dict(options,handlers=dict(handlers,**{'in2n/hello':observed}))
        original(channel,*args,**options)
    return initialize


def verify_hello_rejection(before,after,attempt):
    need(after[:len(before)]==before,'receiver_in2n_observation_changed')
    expected=HELLO_REFUSALS[attempt['fault']]
    matched=[row for row in after[len(before):] if row['method']=='in2n/hello'
        and row['params_sha256']==attempt['params_sha256'] and row['proof_sha256']==attempt['proof_sha256']
        and row['error_code']==expected and row['trusted'] is False
        and row['tls_profile']=='in2n-tls-exporter-v1']
    need(matched,'receiver_hello_rejection_not_observed')
    return matched


AUTH_TLS_ALERTS=frozenset({'TLSV1_ALERT_UNKNOWN_CA','TLSV1_ALERT_ACCESS_DENIED',
    'SSLV3_ALERT_BAD_CERTIFICATE','SSLV3_ALERT_UNSUPPORTED_CERTIFICATE',
    'TLSV1_ALERT_CERTIFICATE_UNKNOWN','TLSV13_ALERT_CERTIFICATE_REQUIRED'})
VERIFY_ERRORS=frozenset({18,19,20,21,27,28})  # OpenSSL untrusted/invalid issuer purpose.


def audited_tls_context(original,directory,on_error):
    """Observe production verification without changing its bool(ok) decision.

    The frozen exporter factory's callback is exactly bool(ok). We preserve its
    verification mode, CA set, certificates, protocol and the same return value.
    Only fresh failed leaf-verification observations are recorded. No success or
    failure is manufactured from an uninformative connection close.
    """
    def factory(**options):
        context=original(**options)
        if options.get('require_peer'):
            def verify(connection,certificate,error,depth,ok):
                if not ok and depth==0:
                    from OpenSSL import crypto
                    try:
                        rows=list(directory.iterdir());need(len(rows)<64,'tls_observation_capacity')
                        private(directory/f'{len(rows):03d}.json',{'class':'FIXTURE',
                            'certificate_sha256':hashlib.sha256(crypto.dump_certificate(crypto.FILETYPE_ASN1,certificate)).hexdigest(),
                            'verify_error':error,'depth':depth,'accepted':False,'observed_monotonic_ns':time.monotonic_ns()})
                    except BaseException:
                        on_error();raise
                return bool(ok)
            context.set_verify(context.get_verify_mode(),verify)
        return context
    return factory


def verify_receiver_rejection(before,after,certificate):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    expected=hashlib.sha256(x509.load_pem_x509_certificate(certificate.encode()).public_bytes(serialization.Encoding.DER)).hexdigest()
    need(after[:len(before)]==before,'receiver_tls_observation_changed')
    matched=[row for row in after[len(before):] if row['certificate_sha256']==expected
        and row['verify_error'] in VERIFY_ERRORS and row['accepted'] is False and row['depth']==0]
    need(matched,'receiver_certificate_rejection_not_observed')
    return matched


def peer_auth_alert(error):
    """Require an actual peer-auth TLS alert, never a connect/reset/timeout."""
    seen=set();pending=[error]
    while pending:
        value=pending.pop()
        if id(value) in seen:continue
        seen.add(id(value))
        if isinstance(value,ssl.SSLError) and getattr(value,'reason',None) in AUTH_TLS_ALERTS:
            return value.reason
        for nested in (getattr(value,'__cause__',None),getattr(value,'__context__',None),*getattr(value,'args',())):
            if isinstance(nested,BaseException):pending.append(nested)
    raise ValueError('credential_refusal_not_observed')


async def rejected_cluster_tls(endpoint,ca,certificate,key):
    from bgp.federation import exporter_tls
    writer=None
    try:
        reader,writer=await exporter_tls.open_connection(endpoint['host'],endpoint['port'],ca_file=ca,
            server_hostname=endpoint['server_name'],cert_file=certificate,key_file=key,handshake_timeout=4)
        value=await asyncio.wait_for(reader.read(1),4)
        need(not value,'untrusted_cluster_client_received_preamble')
        return {'client_observation':'connection_closed_before_cluster_preamble'}
    except (ConnectionRefusedError,TimeoutError):raise
    except (ssl.SSLError,ConnectionResetError,ConnectionError) as exc:
        # This is only the client-side observation. The caller MUST correlate
        # a new exact failed receiver certificate-verification event below.
        return {'client_observation':type(exc).__name__}
    finally:
        if writer:
            writer.close()
            try:await writer.wait_closed()
            except (ssl.SSLError,ConnectionError):pass


def etcd_denied(url,ca,certificate,key):
    import httpx
    context=ssl.create_default_context(cafile=ca);context.minimum_version=ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(certificate,key)
    try:
        with httpx.Client(verify=context,trust_env=False,timeout=4) as client:
            response=client.post(url+'/v3/kv/range',json={'key':base64.b64encode(b'/netclaw/ha/').decode()})
            need(response.status_code in (400,401,403) and len(response.content)<=4096,'untrusted_consensus_client_reached_read')
            body=response.json()
            expected={'etcdserver: user name is empty','etcdserver: authentication failed, invalid user ID or password',
                      'etcdserver: permission denied','etcdserver: invalid auth token'}
            need(isinstance(body,dict) and body.get('error') in expected
                 and body.get('code') in (3,7,16),'credential_refusal_not_observed')
            return {'refused':True,'observation':'etcd-auth-rejection','status':response.status_code,
                    'code':body['code'],'reason':body['error']}
    except (httpx.ConnectError,httpx.ReadError) as exc:
        return {'refused':True,'observation':'peer-tls-auth-alert','reason':peer_auth_alert(exc)}


async def positive_cluster(fixture,node):
    from bgp.federation import exporter_tls
    other=next(n for n in fixture.manifest.nodes if n['node_id']!=node['node_id'])
    index=next(i for i,n in enumerate(fixture.manifest.nodes) if n['node_id']==other['node_id'])
    endpoint=node['endpoints']['cluster']
    _,writer=await exporter_tls.open_connection(endpoint['host'],endpoint['port'],
        ca_file=fixture.configs['member']['transport_ca'],server_hostname=endpoint['server_name'],
        cert_file=str(fixture.lab.root/f'cluster-transport/node{index}.crt'),
        key_file=str(fixture.lab.root/f'cluster-transport/node{index}.key'),handshake_timeout=4)
    need(writer.get_extra_info('tls_profile')=='ncfed-cluster-mtls-v1','positive_cluster_tls_failed')
    writer.close();await writer.wait_closed()
    return {'surface':'cluster-mtls','node_id':node['node_id'],'valid_owned_certificate_handshake':True,
            'observed_monotonic_ns':time.monotonic_ns()}


async def positive_etcd(fixture,index,port):
    positive=fixture.lab.store(index)
    try:
        positive.endpoints=[f'https://127.0.0.1:{port}'];positive._index=0
        observed=await asyncio.to_thread(positive.read,'control')
        need(observed[0] is not None,'positive_consensus_control_missing')
        return {'surface':'private-etcd','port':port,'positive_control_revision':observed[1],
                'observed_monotonic_ns':time.monotonic_ns()}
    finally:positive.close()


async def topology_row(fixture):
    from bgp.federation.certs import create_self_signed
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.config import HAError
    path=fixture.path/'trust';path.mkdir(mode=0o700)
    member=decode(read_private(fixture.path/'member.json'));config=fixture.configs['member']
    certificate=member['certificate'];private(path/'member.crt',certificate.encode())
    identities=[('member',member['binding'],certificate,read_private(config['member_key_file']).decode(),
                  str(path/'member.crt'),config['member_key_file'])]
    for role in ('external','unenrolled'):
        certificate,key=create_self_signed('r08/'+role+'-negative',days=3)
        binding={'installation_id':str(uuid.uuid4()),'member_id':'r08/'+role+'-negative',
            'key_id':c.key_id(certificate),'enrollment_generation':str(uuid.uuid4())}
        private(path/(role+'.crt'),certificate.encode());private(path/(role+'.key'),key.encode())
        identities.append((role,binding,certificate,key,str(path/(role+'.crt')),str(path/(role+'.key'))))
    rows=[]
    controls=[]
    for node in fixture.manifest.nodes:
        controls.append(dict(await positive_cluster(fixture,node),phase='before'))
        target=next(name for name,record in fixture.records.items() if record.get('node_id')==node['node_id'])
        controls.append(dict(await fixture.call(target,'member-health'),surface='in2n-member',phase='before'))
        for role,binding,certificate,key,certificate_file,key_file in identities:
            before=await fixture.call(target,'tls-rejections')
            rejected=await rejected_cluster_tls(node['endpoints']['cluster'],config['transport_ca'],certificate_file,key_file)
            after=await fixture.call(target,'tls-rejections')
            proofs=verify_receiver_rejection(before,after,certificate)
            rows.append({'surface':'cluster-mtls','role':role,'node_id':node['node_id'],
                'receiver_refused':True,'receiver_verification':proofs,**rejected})
            if role!='member':
                before=await fixture.call(target,'in2n-rejections')
                result=await bad_hello(fixture.manifest,node['endpoints']['in2n'],config['transport_ca'],binding,key,fault='not-enrolled')
                after=await fixture.call(target,'in2n-rejections')
                proofs=verify_hello_rejection(before,after,result)
                rows.append({'surface':'in2n-membership','role':role,'node_id':node['node_id'],
                    'receiver_refused':True,'receiver_verification':proofs,**result})
        for method in ('n2n/cluster/status','n2n/tools/call','execution/admin'):
            result=await fixture.call('member','wire-role',{'via_node_id':node['node_id'],'method':method})
            rows.append({'surface':'in2n-method-role',**result})
        controls.append(dict(await positive_cluster(fixture,node),phase='after'))
        controls.append(dict(await fixture.call(target,'member-health'),surface='in2n-member',phase='after'))
    selected=fixture.manifest.nodes[0]['endpoints']['in2n'];role,binding,certificate,key,certificate_file,key_file=identities[0]
    target=next(name for name,record in fixture.records.items() if record.get('node_id')==fixture.manifest.nodes[0]['node_id'])
    for fault in ('wrong-role','replay'):
        before=await fixture.call(target,'in2n-rejections')
        prior=await bad_hello(fixture.manifest,selected,config['transport_ca'],binding,key,fault='capture') if fault=='replay' else None
        result=await bad_hello(fixture.manifest,selected,config['transport_ca'],binding,key,fault=fault,old_proof=prior)
        after=await fixture.call(target,'in2n-rejections')
        proofs=verify_hello_rejection(before,after,result)
        rows.append({'surface':'in2n-transcript','receiver_refused':True,'receiver_verification':proofs,**result})
    controls.append(dict(await fixture.call(target,'member-health'),surface='in2n-transcript',phase='after'))
    for index,port in enumerate(fixture.lab.document['ports']):
        controls.append(dict(await positive_etcd(fixture,index,port),phase='before'))
        for role,_,_,_,certificate_file,key_file in identities:
            result=await asyncio.to_thread(etcd_denied,f'https://127.0.0.1:{port}',str(fixture.lab.root/'pki/client-ca.crt'),certificate_file,key_file)
            rows.append({'surface':'private-etcd-mtls','role':role,'port':port,**result})
        controls.append(dict(await positive_etcd(fixture,index,port),phase='after'))
    store=fixture.lab.store(0)
    try:
        for surface,path_name,body in [('etcd-outside-prefix','/v3/kv/range',{'key':base64.b64encode(b'/unowned/').decode()}),
                                     ('etcd-administration','/v3/auth/role/list',{})]:
            try:
                await asyncio.to_thread(store._request,path_name,body,read_only=True)
                raise AssertionError('border_consensus_scope_escalation')
            except HAError as exc:
                need(exc.code in ('etcd_access_refused','etcd_request_refused'),'unobserved_rbac_refusal')
                rows.append({'surface':surface,'role':'scoped-border','receiver_refused':True,'code':exc.code})
    finally:store.close()
    await fixture.mesh(3);await fixture.attached(3)
    status=await fixture.call('member','status')
    need(len(status['attachments'])==3 and status['has_consensus_credentials'] is False
         and status['has_network_listener'] is False,'member_topology_changed')
    # Inspect actual member PID only. Its private AF_UNIX control socket is not a
    # network listener and cannot confer member-to-member transport authority.
    listeners=subprocess.run(['lsof','-nP','-a','-p',str(status['pid']),'-iTCP','-sTCP:LISTEN','-F','n'],capture_output=True,timeout=5)
    need(listeners.returncode==1 and not listeners.stdout and not listeners.stderr,'member_tcp_listener_present_or_inventory_failed')
    result={'class':'FIXTURE','passed':True,'case':'topology-trust','rows':rows,'positive_controls':controls,
        'member_pid':status['pid'],'actual_attachments':status['attachments'],'outbound_only_observed':True,
        'member_tcp_listener_inventory':{'returncode':listeners.returncode,'stdout_bytes':len(listeners.stdout)},
        'member_consensus_credentials':False,'model_calls':0,'native_tool_calls':0,
        'external_scope':'fresh independent-organization certificate; no eN2N grant or endpoint failover qualification',
        'native_profile_qualified':False}
    private(fixture.path/'topology-trust.json',result);return result


async def run(lab,evidence):
    from bgp.federation.ha.authority import Authority
    fixture=WireFixture(lab,evidence)
    fixture.member_certificate=decode(read_private(fixture.path/'member.json'))['certificate']
    completed=False
    try:
        from labs.ha.fenced_restore_fixture import live_voters
        live_voters(lab)  # Exact owned direct3 and global running voter cap.
        store=lab.store(0)
        try:
            need(store.read('control')[0] is None,'fresh_dedicated_fixture_required')
            Authority(store,fixture.manifest,fixture.manifest.nodes[0]['node_id']).bootstrap(create=True)
        finally:store.close()
        for name in ('border0','border1','border2'):await fixture.start(name)
        await fixture.mesh(3);leader,_=await fixture.leader();await fixture.call(leader,'enroll')
        await fixture.start('member');await fixture.attached(3)
        await topology_row(fixture)
        first=await result_loss_row(fixture,'result-reply')
        second=await result_loss_row(fixture,'ack-delivery')
        paused=await paused_row(fixture)
        status=await fixture.call('member','status');need(len(status['effects'])==7,'fixture_effect_budget_mismatch')
        private(fixture.path/'final-member.json',status)
        # Reopen the production SQLite store independently after all workers
        # exit; final ACK proof must be durable rather than an in-memory DTO.
        await fixture.close();completed=True
        database=Path(fixture.configs['member']['home'])/'federation.db'
        rows=[]
        with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as database_read:
            for row in (first,second):
                original=database_read.execute('SELECT state,receipt,ack FROM protected_operation WHERE side=? AND operation_id=?',
                    ('member',row['original_operation_id'])).fetchone()
                need(original is not None,'durable_ack_missing')
                state,receipt,ack=original[0],decode(original[1].encode(),base.MAX_RESPONSE),decode(original[2].encode(),base.MAX_RESPONSE)
                need(receipt==row['original_signed_result'] and ack==row['durable_member_ack']
                     and state=='acknowledged','durable_ack_restart_mismatch')
                rows.append({'operation_id':row['original_operation_id'],'receipt_sha256':digest(receipt),
                             'ack_sha256':digest(ack),'state':state})
        private(fixture.path/'reopened-member-ack-proof.json',rows)
        result={'class':'FIXTURE','passed':True,'source_sha256':fixture.source['sha256'],
            'rows':['topology-trust','lost-result-reply','lost-ack-delivery','paused-leader-unaware-member'],
            'controlled_callbacks':7,'model_calls':0,'native_tool_calls':0,'native_profile_qualified':False,
            'actual_os_processes':4,'member_enrollments':1,'owned_worker_cleanup_passed':True,
            'voters_retained_running':3,'voter_cleanup_pending':True}
        private(fixture.path/'complete.json',result);return result
    except BaseException as exc:
        private(fixture.path/'failed.json',{'class':'FIXTURE','type':type(exc).__name__,
            'code':getattr(exc,'code',None),'automatic_retry':False,'evidence_retained':True})
        raise
    finally:
        if not completed and not (fixture.path/'owned-process-cleanup.json').exists():await fixture.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('worker','run'))
    parser.add_argument('--config');parser.add_argument('--fixture');parser.add_argument('--evidence')
    args=parser.parse_args(argv);os.umask(0o077)
    if args.command=='worker':
        need(args.config and not args.fixture and not args.evidence,'worker_arguments');asyncio.run(worker_main(args.config));return 0
    need(args.fixture and args.evidence and not args.config,'coordinator_arguments')
    from labs.ha.etcd_lab import EtcdLab
    result=asyncio.run(asyncio.wait_for(run(EtcdLab(args.fixture).load(),args.evidence),480))
    print(encode(result).decode());return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except SystemExit:raise
    except BaseException as exc:
        print(encode({'class':'FIXTURE','failed':True,'type':type(exc).__name__,
                      'code':getattr(exc,'code',None),'automatic_retry':False}).decode(),file=sys.stderr)
        raise SystemExit(1)
