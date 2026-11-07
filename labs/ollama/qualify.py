#!/usr/bin/env python3
"""Prepare one fresh NetClaw model namespace and record measured confinement.

No inference, enrollment, existing runtime replacement or public deployment. The
peer and UID probes are explicit role stand-ins, not real Border/mobile/external
vantage qualification. Actual client acceptance remains a separate evidence gate.
"""
import argparse
import hashlib
import ipaddress
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('netclaw_ollama_qualification_profile',
    ROOT/'mcp-servers/protocol-mcp/bgp/federation/protected_ollama.py')
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

SERVICE_PORTS = [4000, 4001, 11434, 18970, 49171]
LABEL = 'netclaw.spec=176'


def owner_spec(args):
    value = getattr(args, 'owner_spec', 176)
    need(type(value) is int and value in (176, 179), 'owner_spec_refused')
    return value


def owner_labels(args):
    spec = owner_spec(args)
    name = getattr(args, 'owner_name', None)
    need(name is None or isinstance(name, str) and re.fullmatch(r'netclaw-r08-[a-z0-9_.-]+', name), 'owner_name_refused')
    need(spec != 179 or name is not None, 'owner_name_required')
    return ['--label', 'netclaw.spec=' + str(spec)] + (['--label', 'netclaw.owner=' + name] if name else [])


class QualificationRefused(ValueError): pass


def need(value, code):
    if not value: raise QualificationRefused(code)


def write(path, value):
    raw = value if isinstance(value, bytes) else model.canonical(value)
    path = Path(path); temporary = path.with_name(path.name+'.new')
    fd = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def nft_rules(guard_uid, model_uid):
    need(type(guard_uid) is int and type(model_uid) is int and 0 < guard_uid < 2**31
         and 0 < model_uid < 2**31 and guard_uid != model_uid, 'role_uid_invalid')
    excluded = ', '.join(map(str, SERVICE_PORTS))
    return f'''table inet netclaw_r05 {{
  chain output {{
    type filter hook output priority -50; policy drop;
    ct state established,related accept
    oifname "lo" ip daddr 127.0.0.1 meta skuid {guard_uid} tcp dport {{ 4000, 4001, 11434, 18970 }} accept
    oifname "lo" ip daddr 127.0.0.1 meta skuid {model_uid} tcp dport 32768-65535 tcp dport != {{ {excluded} }} accept
  }}
  chain input {{
    type filter hook input priority -50; policy drop;
    ct state established,related accept
    iifname "lo" accept
    tcp dport 4000 accept
  }}
}}
'''


def selected_profile(args):
    arch = 'arm64' if args.family == 4 else 'amd64'
    return {'schema_version':1, 'family':args.family, 'architecture':arch,
        'runner_version':model.RUNNER, 'model':model.MODEL, 'model_image':args.image,
        'runner_manifest_sha256':model.RUNNER_MANIFESTS[arch], 'manifest_sha256':model.MANIFEST,
        'layer_sha256s':list(model.LAYERS), 'model_container':args.name, 'model_container_id':'0'*64,
        'model_store':str(Path(args.model_store).absolute()), 'guard_uid':args.guard_uid, 'model_uid':args.model_uid,
        'confinement_file':str(Path(args.state_dir).absolute()/'confinement.json'), 'confinement_sha256':'0'*64}


def create_model_args(profile, network, *, owner=176, owner_name=None):
    need(type(owner) is int and owner in (176, 179), 'owner_spec_refused')
    bound = model.limits(profile)
    return ['create', '--name', profile['model_container'], '--network', network, '--read-only',
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', str(profile['model_uid']),
        '--pids-limit', '256', '--memory', '2048m', '--memory-swap', '2048m',
        '--cpus', str(bound['model_cpu_millicores']//1000), '--label', 'netclaw.spec='+str(owner),
        *(['--label', 'netclaw.owner='+owner_name] if owner_name else []),
        *(['--log-driver', 'json-file', '--log-opt', 'max-size=-1'] if owner == 179 else []),
        '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m',
        '--mount', 'type=bind,src='+profile['model_store']+',dst=/models,readonly',
        *[item for key,value in model.model_environment(profile).items() for item in ('--env', key+'='+value)],
        '--entrypoint', '/usr/local/bin/ollama', profile['model_image'], 'serve']


class Docker:
    def __init__(self, args, state, *, fresh=False):
        source = Path(args.docker)
        need(source.is_absolute(), 'absolute_docker_required')
        executable = source.resolve(strict=True); info = executable.stat()
        need(stat.S_ISREG(info.st_mode) and info.st_uid in (0,os.getuid()) and not info.st_mode&0o022
             and os.access(executable,os.X_OK), 'docker_binary_untrusted')
        need(isinstance(args.docker_host,str) and args.docker_host.startswith('unix:///'), 'local_docker_required')
        sock = Path(args.docker_host[7:]); sock_info = sock.lstat()
        need(sock == sock.resolve() and stat.S_ISSOCK(sock_info.st_mode) and sock_info.st_uid in (0,os.getuid()), 'docker_socket_untrusted')
        self.executable=str(executable); self.host=args.docker_host; self.state=state
        self.config=state/'docker-cli'
        if fresh:
            self.config.mkdir(mode=0o700); write(self.config/'config.json',b'{}')
        model.private_path(self.config,directory=True); model.private_path(self.config/'config.json')
        need((self.config/'config.json').read_bytes()==b'{}','docker_configuration_changed')

    def call(self, *args, data=None, timeout=30):
        try:
            result=subprocess.run([self.executable,'--host',self.host,'--config',str(self.config),*args],input=data,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False,
                env={'PATH':'/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(self.config)})
        except (OSError,subprocess.TimeoutExpired): raise QualificationRefused('docker_outcome_unknown') from None
        need(len(result.stdout)<=4*1024*1024 and len(result.stderr)<=1024*1024,'docker_output_bound')
        need(result.returncode==0,'docker_operation_failed')
        return result.stdout

    def inspect(self, name):
        rows=json.loads(self.call('inspect',name));need(isinstance(rows,list) and len(rows)==1,'docker_inspection_invalid')
        return rows[0]

    def python(self, container, uid, code, *args):
        return json.loads(self.call('exec','--user',str(uid),container,'python3','-c',code,*map(str,args),timeout=8))


API_PROBE = '''import json,urllib.request
with urllib.request.urlopen('http://127.0.0.1:11434/api/version',timeout=1) as response:
 print(json.dumps({'status':response.status,'version':json.load(response)['version']}))
'''
DENIED_PROBE = '''import json,socket
try:
 s=socket.create_connection(('127.0.0.1',11434),timeout=0.5);s.close();denied=False
except OSError:denied=True
print(json.dumps({'denied':denied}))
'''
PEER_PROBE = '''import json,socket,sys,urllib.request
host,nonce=sys.argv[1:]
with urllib.request.urlopen('http://'+host+':4000/',timeout=2) as reply: control=reply.read(256).decode()==nonce
try:
 s=socket.create_connection((host,11434),timeout=0.5);s.close();denied=False
except OSError:denied=True
print(json.dumps({'positive_control':control,'model_api_denied':denied}))
'''
LISTENER = '''import http.server,signal,sys
nonce=sys.argv[1]
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(nonce.encode())
 def log_message(self,*args):pass
signal.signal(signal.SIGALRM,lambda *_:sys.exit(2));signal.alarm(20)
with http.server.HTTPServer(('0.0.0.0',4000),Handler) as server:
 server.handle_request();server.handle_request()
'''


def owned_container(inspected, image, name, identity=None, *, owner=176, owner_name=None):
    need(inspected.get('Name')=='/'+name and inspected.get('Image')==image
         and inspected.get('Config',{}).get('Labels',{}).get('netclaw.spec')==str(owner)
         and (owner_name is None or inspected.get('Config',{}).get('Labels',{}).get('netclaw.owner')==owner_name)
         and (identity is None or inspected.get('Id')==identity), 'owned_container_changed')
    return inspected['Id']


def prepare(args):
    os.umask(0o077)
    profile=selected_profile(args);model.validate_profile(profile)
    spec=owner_spec(args); labels=owner_labels(args)
    need(re.fullmatch('netclaw-r'+('08' if spec==179 else '05')+'-[a-z0-9_.-]+',args.name),'owned_name_refused')
    need(args.guard_uid==os.getuid(),'guard_uid_must_be_operator')
    model.verify_store(profile)
    state=Path(args.state_dir).absolute();need(state==state.resolve() and state.parent.is_dir(),'state_path_invalid')
    state.mkdir(mode=0o700,exist_ok=False)
    docker=Docker(args,state,fresh=True);network=args.name+'-net'
    manifest={'schema_version':1,'owner_spec':spec,'owner_name':getattr(args,'owner_name',None),'image':args.image,'model_name':args.name,'model_id':None,
        'network_name':network,'network_id':None,'probe_name':args.name+'-peer','probe_id':None,'state':'preparing'}
    write(state/'owned.json',manifest)
    try:
        # Name uniqueness is enforced by Docker; no existing object is changed.
        subnet='198.19.'+str(int(hashlib.sha256(args.name.encode()).hexdigest()[:2],16))+'.0/28'
        network_id=docker.call('network','create','--internal','--subnet',subnet,*labels,network).decode().strip()
        need(re.fullmatch('[a-f0-9]{64}',network_id),'network_identity_unknown')
        manifest['network_id']=network_id;write(state/'owned.json',manifest)
        container_id=docker.call(*create_model_args(profile,network,owner=spec,owner_name=manifest['owner_name'])).decode().strip()
        need(re.fullmatch('[a-f0-9]{64}',container_id),'container_identity_unknown')
        manifest['model_id']=profile['model_container_id']=container_id;write(state/'owned.json',manifest)
        docker.call('start',container_id)
        # No model API request has occurred. Install before admitting any caller.
        rules=nft_rules(args.guard_uid,args.model_uid).encode();write(state/'policy.nft',rules)
        docker.call('exec','--privileged','--user','0','-i',container_id,'nft','-f','-',data=rules)
        raw_rules=json.loads(docker.call('exec','--privileged','--user','0',container_id,'nft','-j','list','ruleset'))
        policy_sha256=model.nft_policy_digest(raw_rules);write(state/'kernel-policy.json',raw_rules)
        positive=None
        for _ in range(30):
            try:positive=docker.python(container_id,args.guard_uid,API_PROBE)
            except QualificationRefused:time.sleep(.2);continue
            if positive=={'status':200,'version':model.RUNNER}:break
            raise QualificationRefused('runner_version_unqualified')
        need(positive=={'status':200,'version':model.RUNNER},'guard_api_positive_control_failed')
        same_namespace={};reserved={args.guard_uid,args.model_uid};candidate=21001
        for role in ('agent','broker','border','sibling'):
            while candidate in reserved:candidate+=1
            uid=candidate;reserved.add(uid);candidate+=1
            result=docker.python(container_id,uid,DENIED_PROBE)
            need(result=={'denied':True},'model_api_uid_confinement_failed')
            same_namespace[role]={'uid':uid,'probe':result,'scope':'role stand-in UID in the owned model namespace'}
        own_denied=docker.python(container_id,args.model_uid,DENIED_PROBE)
        need(own_denied=={'denied':True},'model_uid_api_bypass')
        inspected=docker.inspect(container_id);owned_container(inspected,args.image,args.name,container_id,owner=spec,owner_name=manifest['owner_name'])
        need(not inspected['HostConfig'].get('PortBindings') and not any(inspected['NetworkSettings'].get('Ports',{}).values()),'model_or_guard_port_published')
        address=inspected['NetworkSettings']['Networks'][network]['IPAddress'];ipaddress.IPv4Address(address)
        nonce=secrets.token_hex(16)
        docker.call('exec','--detach','--user',str(args.guard_uid),container_id,'python3','-c',LISTENER,nonce)
        control=False
        local_probe = "import json,sys,urllib.request; print(json.dumps({'positive_control':urllib.request.urlopen('http://127.0.0.1:4000/',timeout=1).read(256).decode()==sys.argv[1]}))"
        for _ in range(20):
            try:control=docker.python(container_id,args.guard_uid,local_probe,nonce)=={'positive_control':True};break
            except QualificationRefused:time.sleep(.1)
        need(control,'guard_namespace_positive_control_failed')
        peer_id=docker.call('create','--name',manifest['probe_name'],'--network',network,'--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(candidate),
            '--pids-limit','32','--memory','64m','--memory-swap','64m','--cpus','0.5',*labels,
            '--entrypoint','python3',args.image,'-c',PEER_PROBE,address,nonce).decode().strip()
        need(re.fullmatch('[a-f0-9]{64}',peer_id),'peer_identity_unknown')
        manifest['probe_id']=peer_id;write(state/'owned.json',manifest)
        docker.call('start',peer_id);need(docker.call('wait',peer_id).strip()==b'0','peer_probe_failed')
        peer=json.loads(docker.call('logs',peer_id));need(peer=={'positive_control':True,'model_api_denied':True},'peer_model_api_bypass')
        # Listener must have consumed exactly the two nonce reads and exited.
        guard_listener=docker.python(container_id,args.guard_uid,
            DENIED_PROBE.replace("('127.0.0.1',11434)","('127.0.0.1',4000)"))
        need(guard_listener=={'denied':True},'temporary_guard_probe_still_running')
        positive_after=docker.python(container_id,args.guard_uid,API_PROBE)
        need(positive_after==positive,'guard_api_positive_control_changed')
        namespace=docker.call('exec',container_id,'readlink','/proc/self/ns/net').decode().strip()
        receipt={'schema_version':1,'container_id':container_id,'image':args.image,'network_namespace_inode':namespace,
            'guard_uid':args.guard_uid,'model_uid':args.model_uid,'model_api':'127.0.0.1:11434',
            'worker_range':[32768,65535],'excluded_ports':SERVICE_PORTS,'policy_sha256':policy_sha256,
            'positive_control':True,'denied_callers':['agent','broker','border','sibling','external']}
        write(state/'confinement.json',receipt);profile['confinement_sha256']=hashlib.sha256((state/'confinement.json').read_bytes()).hexdigest()
        image_config=json.loads(docker.call('image','inspect',args.image))[0]
        model.verify_confinement(profile,docker.inspect(container_id),namespace,
            image_environment=image_config['Config'].get('Env',[]),policy_sha256=policy_sha256)
        evidence={'schema_version':1,'scope':'local owned namespace and role stand-ins; no inference or actual client qualification',
            'guard_api_positive_before':positive,'guard_api_positive_after':positive_after,'role_uid_negatives':same_namespace,
            'model_uid_api_negative':own_denied,'guard_uid_namespace_port_positive':control,'published_ports':[],'peer_probe':peer,
            'external_scope':'fresh peer container on the owned internal Docker bridge; not public Internet or deployed Border',
            'actual_external_vantage_qualified':False,'model_requests':0,'policy_sha256':policy_sha256}
        write(state/'qualification-evidence.json',evidence);write(state/'profile.json',profile)
        manifest['state']='prepared';write(state/'owned.json',manifest)
        return {'state':'prepared','profile_file':str(state/'profile.json'),'evidence_file':str(state/'qualification-evidence.json')}
    except BaseException:
        manifest['state']='failed_or_unknown';write(state/'owned.json',manifest)
        raise


def inspect(args):
    state=model.private_path(args.state_dir,directory=True);docker=Docker(args,state)
    profile=json.loads(model.private_path(state/'profile.json').read_bytes());model.verify_store(profile)
    manifest=json.loads(model.private_path(state/'owned.json').read_bytes())
    need(manifest.get('owner_spec',176)==owner_spec(args) and manifest.get('owner_name')==getattr(args,'owner_name',None),'owned_spec_changed')
    owner_labels(args)
    container=docker.inspect(profile['model_container_id'])
    owned_container(container,profile['model_image'],profile['model_container'],profile['model_container_id'],owner=owner_spec(args),owner_name=manifest.get('owner_name'))
    if owner_spec(args) == 179:
        need(container['HostConfig'].get('LogConfig') == {'Type':'json-file', 'Config':{'max-size':'-1'}},
             'owned_log_rotation_unqualified')
    networks=container['NetworkSettings']['Networks'];need(len(networks)==1,'model_network_changed')
    network=json.loads(docker.call('network','inspect',next(iter(networks))))[0]
    need(network.get('Internal') is True and not network.get('EnableIPv6'),'model_network_not_internal')
    namespace=docker.call('exec',profile['model_container_id'],'readlink','/proc/self/ns/net').decode().strip()
    rules=json.loads(docker.call('exec','--privileged','--user','0',profile['model_container_id'],'nft','-j','list','ruleset'))
    image=json.loads(docker.call('image','inspect',profile['model_image']))[0]
    return model.verify_confinement(profile,container,namespace,image_environment=image['Config'].get('Env',[]),
        policy_sha256=model.nft_policy_digest(rules))


def stop(args):
    state=model.private_path(args.state_dir,directory=True);docker=Docker(args,state)
    path=model.private_path(state/'owned.json');manifest=json.loads(path.read_bytes())
    spec=owner_spec(args);owner_labels(args)
    need(manifest.get('schema_version')==1 and manifest.get('owner_spec',176)==spec and manifest.get('owner_name')==getattr(args,'owner_name',None) and
         re.fullmatch('netclaw-r'+('08' if spec==179 else '05')+'-[a-z0-9_.-]+',manifest.get('model_name','')),'owned_manifest_invalid')
    stopped=[]
    for name_key,id_key in (('probe_name','probe_id'),('model_name','model_id')):
        identity=manifest.get(id_key)
        if identity is None:continue
        inspected=docker.inspect(identity);owned_container(inspected,manifest['image'],manifest[name_key],identity,owner=spec,owner_name=manifest.get('owner_name'))
        if inspected['State'].get('Running'):docker.call('stop','--time','8',identity,timeout=15)
        need(docker.inspect(identity)['State'].get('Running') is False,'owned_stop_unknown');stopped.append(identity)
    receipt={'schema_version':1,'stopped_container_ids':stopped,'network_retained':manifest.get('network_id'),
        'objects_and_evidence_preserved':True,'recorded_at_ms':int(time.time()*1000)}
    write(state/'stop-receipt.json',receipt);return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='action',required=True)
    for action in ('prepare','inspect','stop'):
        sub=commands.add_parser(action);sub.add_argument('--docker',required=True);sub.add_argument('--docker-host',required=True);sub.add_argument('--state-dir',required=True)
        sub.add_argument('--owner-spec',type=int,choices=(176,179),default=176)
        sub.add_argument('--owner-name')
        if action=='prepare':
            sub.add_argument('--image',required=True);sub.add_argument('--model-store',required=True);sub.add_argument('--name',required=True)
            sub.add_argument('--family',type=int,choices=(4,6),required=True);sub.add_argument('--guard-uid',type=int,required=True);sub.add_argument('--model-uid',type=int,required=True)
    args=parser.parse_args(argv)
    try:print(json.dumps({'prepare':prepare,'inspect':inspect,'stop':stop}[args.action](args),sort_keys=True));return 0
    except (ValueError,OSError,KeyError,TypeError):print('ollama_qualification: failed_or_unknown; retain owned.json and inspect before recovery',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
