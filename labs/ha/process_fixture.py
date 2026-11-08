"""Coordinator-only OS-process fixture for production NCFED/iN2N admission.

Three real ClusterNode processes and a separate MemberAdmission process use the
existing owned voters. Only the effect callback is controlled. No product MCP
server, model/native invocation, general command endpoint or automatic replay.
Importing this module starts nothing. Actual runs belong to the coordinator.
"""
import argparse
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
MAX_REQUEST, MAX_RESPONSE = 65536, 4 * 1024 * 1024
MUTATIONS = frozenset(('enroll', 'prepare', 'dispatch', 'unknown', 'admit', 'accept-fixture-result'))
PARAMETERS = {'status': set(), 'enroll': set(), 'prepare': {'client_nonce'},
    'dispatch': {'operation_id'}, 'unknown': {'operation_id'}, 'get': {'operation_id'},
    'snapshot': set(), 'admit': {'context', 'kind', 'ordinal', 'mode', 'via_node_id'},
    'accept-fixture-result': {'operation_id', 'envelope'}}


def need(condition, code):
    if not condition: raise ValueError(code)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value): return hashlib.sha256(encode(value)).hexdigest()


def decode(raw, maximum=MAX_REQUEST):
    need(isinstance(raw, bytes) and len(raw) <= maximum, 'control_frame_bound')
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate_control_key'); result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_control_value')))


def owned_directory(path):
    path = Path(path); info = path.lstat()
    need(path.is_absolute() and path.resolve() == path and stat.S_ISDIR(info.st_mode)
         and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'unsafe_control_directory')
    return path


def read_private(path, maximum=MAX_RESPONSE):
    path = Path(path); info = path.lstat()
    need(path.is_absolute() and path.resolve() == path and stat.S_ISREG(info.st_mode)
         and info.st_uid == os.getuid() and not info.st_mode & 0o077 and info.st_size <= maximum,
         'unsafe_control_file')
    return path.read_bytes()


def private(path, value):
    path = Path(path); owned_directory(path.parent)
    raw = value if isinstance(value, bytes) else encode(value)
    need(len(raw) <= MAX_RESPONSE, 'artifact_bound')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def source_identity():
    files = sorted((ROOT/'mcp-servers/protocol-mcp/bgp/federation').rglob('*.py'))
    files += sorted((ROOT/'labs/ha').glob('*.py'))
    entries = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return {'sha256': digest(entries), 'files': entries}


def validate_request(raw, config):
    value = decode(raw)
    need(isinstance(value, dict) and set(value) == {'schema_version', 'run_id', 'request_id', 'method', 'params', 'token'}, 'control_fields')
    need(value['schema_version'] == 1 and value['run_id'] == config['run_id'], 'control_audience')
    need(isinstance(value['token'], str) and hmac.compare_digest(value['token'], config['control_token']), 'control_auth')
    need(isinstance(value['request_id'], str) and str(uuid.UUID(value['request_id'])) == value['request_id'], 'control_request_id')
    method, params = value['method'], value['params']
    allowed = {'status', 'admit'} if config['role'] == 'member' else set(PARAMETERS)-{'admit'}
    need(method in allowed and isinstance(params, dict) and set(params) == PARAMETERS[method], 'control_method_refused')
    if 'operation_id' in params: need(str(uuid.UUID(params['operation_id'])) == params['operation_id'], 'control_operation_id')
    if method == 'prepare': need(isinstance(params['client_nonce'], str) and 1 <= len(params['client_nonce']) <= 120, 'control_nonce')
    if method == 'accept-fixture-result':
        need(isinstance(params['envelope'], dict), 'controlled_result_required')
        payload = params['envelope'].get('payload', {})
        need(isinstance(payload, dict) and payload.get('output') == {
            'class': 'FIXTURE', 'controlled_process_result': params['operation_id']}, 'controlled_result_required')
    if method == 'admit':
        need(str(uuid.UUID(params['via_node_id'])) == params['via_node_id'], 'control_ingress')
        need(params['mode'] in ('complete', 'hold') and params['kind'] in ('model', 'tool')
             and type(params['ordinal']) is int and params['ordinal'] in ((1, 2) if params['kind'] == 'model' else (1,)), 'control_admission')
        need(isinstance(params['context'], dict) and set(params['context']) == {'operation_id', 'attempt_id', 'approval_digest'}, 'control_context')
        for key in ('operation_id', 'attempt_id'): need(str(uuid.UUID(params['context'][key])) == params['context'][key], 'control_context')
        need(isinstance(params['context']['approval_digest'], str) and len(params['context']['approval_digest']) == 64
             and all(ch in '0123456789abcdef' for ch in params['context']['approval_digest']), 'control_context')
    return value


def claim_command(home, request):
    directory = owned_directory(Path(home)/'commands')
    need(len(list(directory.iterdir())) < 32, 'control_command_capacity')
    private(directory/(request['request_id']+'.json'), {'schema_version': 1, 'method': request['method'],
        'request_id': request['request_id'], 'params_sha256': digest(request['params']), 'state': 'sent_or_unknown'})


def fixture_review(manifest, node, member):
    from bgp.federation import protected_contract as c
    from bgp.federation.protected_access import lab_principal
    from bgp.federation.ha.internal import border_binding
    return {'principal': lab_principal(manifest.cluster_id), 'border': border_binding(manifest, node.node_id),
        'cluster': {**manifest.audience, 'manifest_revision': manifest.revision, 'issuer_node_id': node.node_id,
                    'authority_epoch': node.authority.epoch}, 'member': member,
        'model_profile': {'profile_id': 'controlled-process-fixture', 'profile_revision': '1', 'runtime_kind': 'controlled',
            'runtime_version': 'fixture', 'provider': 'controlled', 'model': 'fixture', 'guard_policy_sha256': 'a'*64},
        'tool_call': {'tool': 'subnet_calculator', 'tool_schema_sha256': 'b'*64, 'arguments': {'cidr': '192.0.2.0/26'},
            'arguments_sha256': c.sha256({'cidr': '192.0.2.0/26'}), 'device_ref': 'documentation-subnet',
            'inventory_revision': 'fixture', 'endpoint_sha256': 'c'*64},
        'limits': {'expires_at_ms': int(time.time()*1000)+180000, 'inference_timeout_ms': 60000,
            'tool_timeout_ms': 60000, 'max_inference_calls': 2, 'max_tool_calls': 1, 'max_output_bytes': 65536},
        'change_request_ref': None}


class Worker:
    def __init__(self, config):
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.config import verify_manifest
        need(config['schema_version'] == 1 and config['class'] == 'FIXTURE'
             and config['source_root'] == str(ROOT) and config['source_sha256'] == source_identity()['sha256'], 'worker_source_changed')
        self.config, self.home = config, owned_directory(Path(config['home']))
        raw = read_private(config['manifest_file']); need(hashlib.sha256(raw).hexdigest() == config['manifest_file_sha256'], 'worker_manifest_changed')
        anchor = read_private(config['anchor_file']).decode()
        self.manifest = verify_manifest(raw, anchor, expected_key_id=config['anchor_key_id'])
        need(c.sha256(self.manifest.value) == config['manifest_sha256'], 'worker_manifest_changed')
        self.member = decode(read_private(config['member_file']))
        self.boot, self.stop = config['launch_id'], asyncio.Event()
        self.node = self.store = self.attachments = self.journal = self.listener = None
        self.channels, self.tasks, self.control_tasks = {}, set(), set()

    async def start(self):
        from bgp.federation import exporter_tls
        from bgp.federation.ha.internal import MemberAttachments, accept_member
        if self.config['role'] == 'member':
            from bgp.federation.ha.admission import MemberAdmission
            self.journal = MemberAdmission(self.home/'journal', self.manifest, self.member['binding'])
            async def current():
                need(hashlib.sha256(read_private(self.config['manifest_file'])).hexdigest() == self.config['manifest_file_sha256'], 'worker_manifest_changed')
            self.attachments = MemberAttachments(self.manifest, self.member['binding'], read_private(self.config['member_key_file']).decode(),
                ca_file=self.config['transport_ca'], handlers={}, current=current)
            await self.attachments.start()
            return
        from bgp.federation.ha.authority import Authority
        from bgp.federation.ha.node import ClusterNode
        from bgp.federation.ha.store import EtcdStore
        value = self.config['store']
        self.store = EtcdStore(value['endpoints'], prefix=value['prefix'], ca=value['ca'],
            certificate=value['certificate'], private_key=value['private_key'], username=value['username'],
            password=read_private(value['password_file']).decode())
        self.node = ClusterNode(Authority(self.store, self.manifest, self.manifest.nodes[self.config['index']]['node_id']),
            private_key=read_private(self.config['node_key_file']).decode(), ca_file=self.config['transport_ca'],
            cert_file=self.config['transport_certificate'], key_file=self.config['transport_key'])
        await self.node.start()
        async def admission(channel, request): return await self.node.admit_member(channel, request)
        async def incoming(reader, writer):
            try:
                await accept_member(self.node, reader, writer, handlers={'execution/admission': admission},
                    on_authenticated=lambda channel: self.channels.update({channel.member_id: channel}))
            except Exception:
                writer.close()
        endpoint = self.manifest.node(self.node.node_id)['endpoints']['in2n']
        self.listener = await exporter_tls.start_server(incoming, endpoint['host'], endpoint['port'],
            cert_file=self.config['transport_certificate'], key_file=self.config['transport_key'], close_clients=True)

    def journal_summary(self):
        with self.journal._connection() as conn:
            rows = conn.execute('SELECT operation_id,attempt_id,kind,ordinal,incarnation,state,proof_hash,request FROM ha_admission ORDER BY operation_id,kind,ordinal').fetchall()
        return [{'operation_id':r[0], 'attempt_id':r[1], 'kind':r[2], 'ordinal':r[3], 'incarnation':r[4],
                 'state':r[5], 'proof_hash':r[6], 'request_sha256':hashlib.sha256(r[7].encode()).hexdigest()} for r in rows]

    def effects(self):
        files = sorted((self.home/'effects').glob('*.json')); need(len(files) <= 8, 'fixture_effect_capacity')
        return [decode(read_private(file)) for file in files]

    async def command(self, method, params):
        from bgp.federation import protected_contract as c
        if method == 'status':
            result = {'pid':os.getpid(), 'boot_id':self.boot, 'source_sha256':self.config['source_sha256'],
                'class':'FIXTURE', 'model_calls':0, 'native_tool_calls':0}
            if self.attachments:
                return dict(result, member_incarnation=self.journal.incarnation,
                    attachments=sorted(self.attachments.channels), journal=self.journal_summary(), effects=self.effects())
            try:
                leader, epoch = await asyncio.to_thread(self.node.authority.current)
                result.update(leader=leader['node_id'], epoch=epoch,
                    local_leader=self.node.authority.leader == leader and self.node.authority.epoch == epoch)
            except Exception as exc: result.update(leader=None, epoch=None, error=getattr(exc,'code',type(exc).__name__))
            return dict(result, node_id=self.node.node_id, authority_incarnation=self.node.authority.incarnation, peers=sorted(self.node.channels),
                        members=sorted(k for k,ch in self.channels.items() if ch.trusted and not ch._closed))
        if method == 'enroll':
            return await asyncio.to_thread(self.node.ledger.enroll_member, self.member['binding'], self.member['certificate'])
        if method == 'prepare':
            review = fixture_review(self.manifest, self.node, self.member['binding'])
            row = await asyncio.to_thread(self.node.ledger.prepare, params['client_nonce'], 'd'*64, review)
            payload = dict(review, approval_id=str(uuid.uuid4()), operation_id=row['operation_id'], nonce=secrets.token_urlsafe(32),
                issued_at_ms=int(time.time()*1000), review_sha256=row['review_digest'])
            approval = c.sign(c.HA_APPROVAL, payload, self.node.private_key)
            return await asyncio.to_thread(self.node.ledger.approve, row['operation_id'], approval,
                revision=row['revision'], review_digest=row['review_digest'])
        if method == 'dispatch': return await asyncio.to_thread(self.node.ledger.dispatch, params['operation_id'])
        if method == 'unknown': return await asyncio.to_thread(self.node.ledger.mark_unknown, params['operation_id'])
        if method == 'get': return await asyncio.to_thread(self.node.ledger.lookup, operation_id=params['operation_id'])
        if method == 'accept-fixture-result':
            row = await asyncio.to_thread(self.node.ledger.lookup, operation_id=params['operation_id'])
            need(row is not None and row['review']['model_profile']['profile_id'] == 'controlled-process-fixture',
                 'controlled_result_required')
            # Real production signature/binding/ACK validation; only this private
            # fixture protocol can submit an explicitly controlled result.
            return await asyncio.to_thread(self.node.ledger.accept_result, params['operation_id'], params['envelope'],
                private_key=self.node.private_key, audit_ref='controlled-process-fixture-audit')
        if method == 'snapshot':
            from bgp.federation.ha.recovery import export_snapshot
            return await asyncio.to_thread(export_snapshot, self.store, self.manifest)
        if method == 'admit':
            self.manifest.node(params['via_node_id'])
            entered = asyncio.get_running_loop().create_future()
            async def send(request):
                channel=self.attachments.channels.get(params['via_node_id'])
                need(channel is not None and channel.trusted and not channel._closed, 'controlled_ingress_unavailable')
                # One chosen authenticated ingress; no replacement on unknown.
                return await channel.call('execution/admission',request,timeout=5)
            async def effect():
                need(len(self.effects()) < 8, 'fixture_effect_capacity')
                value = {'class':'FIXTURE', 'operation_id':params['context']['operation_id'], 'kind':params['kind'],
                    'ordinal':params['ordinal'], 'member_incarnation':self.journal.incarnation, 'controlled_callback':True}
                private(self.home/'effects'/(value['operation_id']+'-'+value['kind']+str(value['ordinal'])+'.json'), value)
                if params['mode'] == 'hold':
                    entered.set_result({'state':'controlled_effect_entered', 'effect':value})
                    await asyncio.wait_for(asyncio.Event().wait(), 120)
                return value
            async def execute():
                try:
                    result = await self.journal.run(params['context'], params['kind'], params['ordinal'],
                        c.sha256({'kind':params['kind'], 'ordinal':params['ordinal']}), send, effect)
                    if not entered.done(): entered.set_result({'state':'finished', 'effect':result})
                except BaseException as exc:
                    if not entered.done(): entered.set_exception(exc)
            task = asyncio.create_task(execute()); self.tasks.add(task); task.add_done_callback(self.tasks.discard)
            return await asyncio.wait_for(entered, 12)
        raise ValueError('control_method_refused')

    async def serve(self, reader, writer):
        if len(self.control_tasks)>=4:
            writer.close();await writer.wait_closed();return
        task=asyncio.current_task();self.control_tasks.add(task)
        try:await self._serve_one(reader,writer)
        finally:
            self.control_tasks.discard(task)
            writer.close()

    async def _serve_one(self, reader, writer):
        request = None
        try:
            raw = await asyncio.wait_for(reader.readline(), 2)
            need(raw.endswith(b'\n'), 'control_frame_required')
            request = validate_request(raw, self.config)
            if request['method'] in MUTATIONS: claim_command(self.home, request)
            result = await asyncio.wait_for(self.command(request['method'], request['params']), 15)
            answer = {'ok':True, 'result':result}
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError): raise
            answer = {'ok':False, 'error':getattr(exc,'code',type(exc).__name__)}
        answer.update(schema_version=1, request_id=request['request_id'] if request else None,
                      boot_id=self.boot, pid=os.getpid(), classification='FIXTURE')
        raw = encode(answer); need(len(raw) <= MAX_RESPONSE, 'control_response_bound')
        try: writer.write(raw+b'\n'); await asyncio.wait_for(writer.drain(), 2)
        finally: writer.close(); await writer.wait_closed()

    async def close(self):
        if self.listener: self.listener.close()
        for task in list(self.control_tasks):task.cancel()
        if self.control_tasks:await asyncio.gather(*self.control_tasks,return_exceptions=True)
        for task in list(self.tasks): task.cancel()
        if self.tasks: await asyncio.gather(*self.tasks, return_exceptions=True)
        if self.attachments: await self.attachments.close()
        for channel in list(self.channels.values()): await channel.close()
        if self.node: await self.node.close()
        if self.listener: await self.listener.wait_closed()
        if self.store: self.store.close()


async def worker_main(config_file):
    os.umask(0o077)
    config = decode(read_private(config_file)); worker = Worker(config)
    socket_path = Path(config['control_socket']); owned_directory(socket_path.parent)
    need(not socket_path.exists() and len(str(socket_path).encode()) < 100, 'control_socket_in_use')
    for sig in (signal.SIGTERM, signal.SIGINT): asyncio.get_running_loop().add_signal_handler(sig, worker.stop.set)
    server = None
    async def watchdog():
        deadline=time.monotonic()+600
        while not worker.stop.is_set():
            if os.getppid()!=config['coordinator_pid'] or time.monotonic()>=deadline:
                worker.stop.set();return
            await asyncio.sleep(1)
    watch=asyncio.create_task(watchdog())
    try:
        await worker.start()
        server = await asyncio.start_unix_server(worker.serve, str(socket_path), limit=MAX_REQUEST)
        socket_path.chmod(0o600)
        await worker.stop.wait()
    finally:
        watch.cancel();await asyncio.gather(watch,return_exceptions=True)
        if server: server.close()
        await asyncio.wait_for(worker.close(), 10)
        if server: await server.wait_closed()


class ControlError(RuntimeError):
    def __init__(self, code): self.code=code; super().__init__(code)


async def control(config, method, params=None, *, request_id=None):
    request = {'schema_version':1, 'run_id':config['run_id'], 'request_id':request_id or str(uuid.uuid4()),
               'method':method, 'params':params or {}, 'token':config['control_token']}
    validate_request(encode(request), config)
    reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(config['control_socket'], limit=MAX_RESPONSE+1), 2)
    try:
        writer.write(encode(request)+b'\n'); await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), 18)
        need(raw.endswith(b'\n'), 'control_reply_unknown'); value = decode(raw, MAX_RESPONSE)
        need(value['request_id'] == request['request_id'] and value['boot_id'] == config['launch_id']
             and value['classification'] == 'FIXTURE', 'control_reply_identity')
        if not value['ok']: raise ControlError(value['error'])
        return value['result']
    finally: writer.close(); await writer.wait_closed()


async def eventually(function, seconds=45):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            value=await function()
            if value:return value
        except (OSError, asyncio.TimeoutError, ControlError): pass
        await asyncio.sleep(.2)
    raise RuntimeError('process_fixture_condition_timeout')


class ProcessFixture:
    def __init__(self, lab, evidence):
        from bgp.federation import protected_contract as c
        from bgp.federation.certs import create_self_signed
        from bgp.federation.ha.config import verify_manifest
        self.lab, self.path = lab, Path(evidence)
        need(self.path.is_absolute() and self.path.resolve()==self.path,'absolute_private_evidence_required')
        self.path.mkdir(mode=0o700, exist_ok=False); owned_directory(self.path)
        self.run_id, self.source = str(uuid.uuid4()), source_identity()
        private(self.path/'source.json', self.source)
        self.control_root=Path(tempfile.mkdtemp(prefix='nc179-',dir='/tmp')).resolve(); self.control_root.chmod(0o700)
        identity, transport = lab.root/'cluster-identity', lab.root/'cluster-transport'
        raw=(identity/'manifest.json').read_bytes(); anchor=(identity/'root.crt').read_text()
        self.manifest=verify_manifest(raw,anchor,expected_key_id=c.key_id(anchor))
        private(self.path/'manifest.json',raw); private(self.path/'anchor.crt',anchor.encode())
        certificate,key=create_self_signed('r08/controlled-process-member',days=3)
        binding={'installation_id':str(uuid.uuid4()),'member_id':'r08/process-'+uuid.uuid4().hex[:12],
                 'key_id':c.key_id(certificate),'enrollment_generation':str(uuid.uuid4())}
        private(self.path/'member.json',{'binding':binding,'certificate':certificate})
        self.base={'schema_version':1,'class':'FIXTURE','run_id':self.run_id,'coordinator_pid':os.getpid(),'source_root':str(ROOT),
            'source_sha256':self.source['sha256'],'manifest_file':str(self.path/'manifest.json'),
            'manifest_file_sha256':hashlib.sha256(raw).hexdigest(),'manifest_sha256':c.sha256(self.manifest.value),
            'anchor_file':str(self.path/'anchor.crt'),'anchor_key_id':c.key_id(anchor),
            'member_file':str(self.path/'member.json'),'transport_ca':str(transport/'transport-ca.crt')}
        self.children, self.configs, self.records, self.boots, self.rows = {}, {}, {}, {}, []
        self.intentional_kills=set()
        credentials=decode(read_private(lab.root/'credentials.json'))
        for name in ('border0','border1','border2','member'):
            home=self.path/name; home.mkdir(mode=0o700)
            for child in ('commands','effects'): (home/child).mkdir(mode=0o700)
            config=dict(self.base,role='member' if name=='member' else 'border',home=str(home),control_socket=str(self.control_root/(name+'.sock')))
            if name=='member':
                private(home/'member.key',key.encode());config['member_key_file']=str(home/'member.key')
            else:
                index=int(name[-1]);private(home/'etcd.password',credentials[name].encode())
                config.update(index=index,node_key_file=str(identity/f'node{index}.key'),
                    transport_certificate=str(transport/f'node{index}.crt'),transport_key=str(transport/f'node{index}.key'),
                    store={'endpoints':[f'https://127.0.0.1:{lab.document["ports"][(index+j)%3]}' for j in range(3)],
                    'prefix':lab.document['prefix'],'ca':str(lab.root/'pki/client-ca.crt'),
                    'certificate':str(lab.root/f'pki/border{index}.crt'),'private_key':str(lab.root/f'pki/border{index}.key'),
                    'username':name,'password_file':str(home/'etcd.password')})
            self.configs[name]=config; self.boots[name]=0
        private(self.path/'scope.json',{'class':'FIXTURE','run_id':self.run_id,'source_sha256':self.source['sha256'],
            'manifest_sha256':c.sha256(self.manifest.value),'actual_ncfed_cluster':True,'actual_in2n_member':True,
            'processes':4,'maximum_controlled_callbacks':8,'model_calls':0,'native_tool_calls':0,
            'control_directory':str(self.control_root),'native_profile_qualified':False})

    async def start(self,name):
        need(name not in self.children or self.children[name].returncode is not None,'owned_process_running')
        need(source_identity()['sha256']==self.source['sha256'],'worker_source_changed')
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
        status=await eventually(ready)
        need(status['pid']==process.pid and status['boot_id']==config['launch_id'],'owned_pid_mismatch')
        command_line=subprocess.run(['ps','-p',str(process.pid),'-o','command='],capture_output=True,check=True,timeout=2).stdout.decode().strip()
        info=socket_path.lstat()
        record={'pid':process.pid,'command':command,'command_line':command_line,'source_sha256':self.source['sha256'],
            'boot_id':config['launch_id'],'socket_identity':[info.st_dev,info.st_ino],
            'python_sha256':hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
            **{key:status[key] for key in ('node_id','authority_incarnation','member_incarnation') if key in status}}
        private(home/f'owned-{number}.json',record);self.records[name]=record
        return status

    async def call(self,name,method,params=None): return await control(self.configs[name],method,params)

    async def leader(self):
        async def find():
            for name, process in self.children.items():
                if name=='member' or process.returncode is not None:continue
                status=await self.call(name,'status')
                if status.get('local_leader'):return name,status
        return await eventually(find)

    async def attached(self,count):
        async def check():
            status=await self.call('member','status')
            return status if len(status['attachments'])==count else None
        return await eventually(check)

    async def mesh(self,count):
        async def check():
            statuses=[await self.call(name,'status') for name,process in self.children.items()
                      if name!='member' and process.returncode is None]
            active={row['node_id'] for row in statuses}
            return statuses if len(statuses)==count and all(set(row['peers'])==active-{row['node_id']} for row in statuses) else None
        return await eventually(check)

    async def admit(self,context,kind,ordinal,mode):
        leader,current=await self.leader()
        statuses=await self.mesh(sum(name!='member' and process.returncode is None for name,process in self.children.items()))
        ingress=next((row for row in statuses if row['node_id']!=current['node_id']),current)
        result=await self.call('member','admit',{'context':context,'kind':kind,'ordinal':ordinal,'mode':mode,
                                               'via_node_id':ingress['node_id']})
        return {'ingress_node_id':ingress['node_id'],'leader_node_id':current['node_id'],
                'forwarded_over_cluster':ingress['node_id']!=current['node_id'],'result':result}

    async def kill(self,name,label):
        process=self.children[name];need(process.returncode is None,'owned_process_not_running')
        need(source_identity()['sha256']==self.source['sha256'],'worker_source_changed')
        record=self.records[name]
        observed=subprocess.run(['ps','-p',str(process.pid),'-o','command='],capture_output=True,check=True,timeout=2).stdout.decode().strip()
        need(observed==record['command_line'] and process.pid==record['pid'],'owned_process_identity_changed')
        private(self.path/(label+'.claim.json'),{'fault':'SIGKILL','name':name,**record,'observed_command_line':observed})
        os.kill(process.pid,signal.SIGKILL)
        code=await asyncio.wait_for(process.wait(),5);need(code==-signal.SIGKILL,'owned_kill_not_observed')
        self.intentional_kills.add(process.pid)
        private(self.path/(label+'.verified.json'),{'name':name,'pid':process.pid,'returncode':code,'boot_id':record['boot_id']})
        return record

    async def close(self):
        results=[]
        for name,process in self.children.items():
            if process.returncode is None:
                process.send_signal(signal.SIGTERM)
                try:await asyncio.wait_for(process.wait(),12)
                except asyncio.TimeoutError:
                    process.kill();await asyncio.wait_for(process.wait(),5)
            socket_path=Path(self.configs[name]['control_socket']); removed=False
            if socket_path.exists() and name in self.records:
                info=socket_path.lstat()
                need(stat.S_ISSOCK(info.st_mode) and info.st_uid==os.getuid()
                     and (info.st_dev,info.st_ino)==tuple(self.records[name]['socket_identity']), 'cleanup_socket_identity_changed')
                socket_path.unlink(); removed=True
            expected=-signal.SIGKILL if process.pid in self.intentional_kills else 0
            results.append({'name':name,'pid':process.pid,'returncode':process.returncode,'expected_returncode':expected,
                            'passed':process.returncode==expected,'owned_socket_removed':removed})
        passed=all(row['passed'] for row in results)
        private(self.path/'owned-process-cleanup.json',{'passed':passed,'processes':results,'voters_untouched_by_cleanup':True})
        if not list(self.control_root.iterdir()):self.control_root.rmdir()
        need(passed,'owned_process_cleanup_failed')


async def _run(lab,evidence,*,restart_voters=False):
    from bgp.federation.ha.authority import Authority
    lab.inspect_owned()
    fixture=ProcessFixture(lab,evidence); original=None
    try:
        store=lab.store(0)
        try:
            existing,_=store.read('control')
            Authority(store,fixture.manifest,fixture.manifest.nodes[0]['node_id']).bootstrap(create=existing is None)
        finally:store.close()
        for name in ('border0','border1','border2'):await fixture.start(name)
        peers=await fixture.mesh(3)
        leader,status=await fixture.leader();await fixture.call(leader,'enroll')
        await fixture.start('member');baseline=await fixture.attached(3)
        original=await fixture.call(leader,'prepare',{'client_nonce':'process-'+str(uuid.uuid4())})
        original=await fixture.call(leader,'dispatch',{'operation_id':original['operation_id']})
        context={key:original[key] for key in ('operation_id','attempt_id','approval_digest')}
        private(fixture.path/'original.json',{'row':original,'context':context,'initial_member':baseline,'cluster_mesh':peers})
        admitted=await fixture.admit(context,'model',1,'complete')
        need(admitted['forwarded_over_cluster'],'initial_admission_must_forward_over_ncfed')
        private(fixture.path/'initial-follower-admission.json',admitted)
        killed=[]
        for step in range(2):
            leader,status=await fixture.leader();killed.append(await fixture.kill(leader,f'leader-{step+1}'))
            successor,observed=await fixture.leader();need(observed['node_id']!=status['node_id'],'old_leader_survived')
            await fixture.attached(2-step)
            kind,ordinal,mode=('model',2,'complete') if step==0 else ('tool',1,'hold')
            result=await fixture.admit(context,kind,ordinal,mode)
            private(fixture.path/f'leader-{step+1}.recovered.json',{'old':status,'new':observed,'original_context':context,'result':result})
        before=await fixture.call('member','status');need(len(before['effects'])==3,'fixture_effect_count')
        await fixture.kill('member','member-consumed-unknown')
        leader,status=await fixture.leader()
        unknown=await fixture.call(leader,'unknown',{'operation_id':original['operation_id']})
        snapshot=await fixture.call(leader,'snapshot');private(fixture.path/'restart-snapshot.json',snapshot)
        killed.append(await fixture.kill(leader,'leader-3'))
        need(len({item['pid'] for item in killed})==3,'distinct_border_processes_required')
        voter_evidence=None
        if restart_voters:
            from labs.ha.owned_restart import OwnedVoterRestart
            from labs.ha.faults import owned_call
            directory=fixture.path/'voter-restart';directory.mkdir(mode=0o700)
            voter_evidence=await owned_call(OwnedVoterRestart(lab,directory,fixture.path/'restart-snapshot.json').execute)
        private(fixture.path/'full-restart.claim.json',{'original_context':context,'journal_sha256':digest(before['journal']),
            'effects_sha256':digest(before['effects']),'actual_voter_restart':bool(voter_evidence)})
        for name in ('border0','border1','border2'):await fixture.start(name)
        await fixture.mesh(3)
        for old in killed:
            new=next(record for name,record in fixture.records.items() if name!='member' and record['node_id']==old['node_id'])
            need(new['pid']!=old['pid'] and new['boot_id']!=old['boot_id']
                 and new['authority_incarnation']!=old['authority_incarnation'],'border_process_not_restarted')
        leader,status=await fixture.leader();await fixture.start('member');after=await fixture.attached(3)
        need(after['member_incarnation']!=before['member_incarnation'] and after['pid']!=before['pid'],'member_process_not_restarted')
        need(after['journal']==before['journal'] and after['effects']==before['effects'],'durable_member_state_changed')
        retained=await fixture.call(leader,'get',{'operation_id':original['operation_id']})
        for key in ('operation_id','attempt_id','approval_digest','review_digest','result_ref','state'):
            need(retained[key]==unknown[key],'original_operation_changed')
        refusals=[]
        try:await fixture.admit(context,'tool',1,'complete')
        except ControlError as exc:need(exc.code=='admission_spent','wrong_replay_refusal');refusals.append(exc.code)
        else:raise AssertionError('consumed_admission_replayed')
        replacement=await fixture.call(leader,'prepare',{'client_nonce':'fenced-'+str(uuid.uuid4())})
        try:await fixture.call(leader,'dispatch',{'operation_id':replacement['operation_id']})
        except ControlError as exc:need(exc.code=='resource_recovery_required','wrong_resource_refusal');refusals.append(exc.code)
        else:raise AssertionError('new_id_bypassed_unknown_fence')
        final=await fixture.call('member','status');need(final['effects']==before['effects'],'restart_replayed_callback')
        result={'class':'FIXTURE','passed':True,'actual_os_processes':4,'actual_ncfed_cluster':True,'actual_in2n_member':True,
            'leader_kills':killed,'restarted_borders':[record for name,record in fixture.records.items() if name!='member'],
            'original_context':context,'before_restart':before,'after_restart':after,
            'retained_operation':retained,'refusals':refusals,'controlled_callbacks':3,'model_calls':0,'native_tool_calls':0,
            'actual_voter_restart':voter_evidence,'full_voter_restart_qualified':bool(voter_evidence),
            'native_profile_qualified':False,'signed_result_recovery_qualified':False}
    except BaseException as exc:
        private(fixture.path/'failure.json',{'class':'FIXTURE','type':type(exc).__name__,'code':getattr(exc,'code',None),
            'original_operation_id':original and original['operation_id'],'automatic_retry':False})
        raise
    finally:await fixture.close()
    private(fixture.path/'complete.json',result);return result


async def run(lab,evidence,*,restart_voters=False):
    async with asyncio.timeout(480):
        return await _run(lab,evidence,restart_voters=restart_voters)


def main():
    sys.path[:0]=[str(ROOT),str(ROOT/'mcp-servers/protocol-mcp')]
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    worker=sub.add_parser('worker');worker.add_argument('--config',type=Path,required=True)
    coordinator=sub.add_parser('run');coordinator.add_argument('--fixture',type=Path,required=True)
    coordinator.add_argument('--evidence',type=Path,required=True)
    coordinator.add_argument('--allow-owned-voter-restart',action='store_true')
    args=parser.parse_args()
    if args.command=='worker':asyncio.run(worker_main(args.config));return
    from labs.ha.etcd_lab import EtcdLab
    result=asyncio.run(run(EtcdLab(args.fixture).load(),args.evidence,restart_voters=args.allow_owned_voter_restart))
    print(json.dumps({'class':'FIXTURE','passed':result['passed'],'full_voter_restart_qualified':result['full_voter_restart_qualified']}))


if __name__=='__main__':
    try:main()
    except SystemExit:raise
    except BaseException as exc:
        print(json.dumps({'class':'FIXTURE','failed':True,'type':type(exc).__name__,'code':getattr(exc,'code',None)}),file=sys.stderr)
        raise SystemExit(1)
