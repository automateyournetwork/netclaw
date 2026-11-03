"""Synthetic boundary tests; native MCP discovery is recorded separately."""
import asyncio
from contextlib import asynccontextmanager
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import threading
from types import SimpleNamespace

import pytest

from bgp.federation import protected_contract as contract
from bgp.federation import protected_mcp as integration
from bgp.federation import protected_runtime as runtime
from bgp.federation import protected_docker as docker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lib'))
import netbox_http

DEVICE = {'object_type':'dcim.device','object_id':42,'fields':contract.NETBOX_FIELDS['dcim.device'],'brief':False}
PREFIX = {'object_type':'ipam.prefix','object_id':17,'fields':contract.NETBOX_FIELDS['ipam.prefix'],'brief':False}
SUBNET = {'cidr':'192.0.2.0/26'}


@pytest.mark.parametrize('tool,args', [('netbox_get_object_by_id',DEVICE),('netbox_get_object_by_id',PREFIX),('subnet_calculator',SUBNET)])
def test_exact_native_arguments_supported(tool,args):
    contract.validate_tool_arguments(tool,args)


@pytest.mark.parametrize('args', [dict(DEVICE,object_type='dcim.devices'),dict(DEVICE,object_type='users.token'),
    dict(DEVICE,object_id=True),dict(DEVICE,object_id=0),dict(DEVICE,object_id=-1),dict(DEVICE,object_id='42'),
    dict(DEVICE,brief=True),dict(DEVICE,fields=['id']),dict(DEVICE,fields=list(reversed(DEVICE['fields']))),
    dict(DEVICE,url='https://other.invalid'),{k:v for k,v in DEVICE.items() if k!='brief'}])
def test_netbox_scope_refusals(args):
    with pytest.raises(contract.ProtectedError): contract.validate_tool_arguments('netbox_get_object_by_id',args)


@pytest.mark.parametrize('cidr',['0.0.0.0/24','255.255.255.0/24','192.0.2.1/24','192.0.2.0/23','192.0.2.0/31','192.0.2.1/32','::/64',None,24])
def test_subnet_bounds(cidr):
    with pytest.raises(contract.ProtectedError):contract.validate_tool_arguments('subnet_calculator',{'cidr':cidr})


@pytest.mark.parametrize('name',['netbox_create_object','netbox_search_objects','netbox_get_objects','subnet_calculator_v6','shell'])
def test_unknown_or_write_tools_refused(name):
    with pytest.raises(contract.ProtectedError):contract.validate_tool_arguments(name,DEVICE)


def test_auth_compatibility_and_secret_validation():
    assert netbox_http.auth_header('nbt_fixture.test')=='Bearer nbt_fixture.test'
    assert netbox_http.auth_header('legacyfixture')=='Token legacyfixture'
    for token in ('nbt_missing', 'fixture\nheader', 'fixture value',''):
        with pytest.raises(ValueError):netbox_http.auth_header(token)


@pytest.fixture
def http(monkeypatch):
    policy={'schemaVersion':1,'url':'https://fixture.invalid/api/dcim/devices/42/','params':{'fields':','.join(DEVICE['fields'])}}
    calls=[]
    response=SimpleNamespace(status_code=200,headers={'Content-Type':'application/json'},
        iter_content=lambda _:iter([b'{"id":42}']),close=lambda:None)
    def request(self,*args,**kwargs):calls.append((args,kwargs));return response
    monkeypatch.setattr(netbox_http.requests.Session,'request',request)
    session=netbox_http.ProtectedSession(policy,'nbt_fixture.secret')
    return session,policy,calls,response


def test_http_one_fixed_get_without_proxy_redirect_retry(http):
    session,policy,calls,_=http
    assert session.trust_env is False
    response=session.get(policy['url'],params=policy['params'],verify=True)
    assert response._content==b'{"id":42}'
    assert calls==[(('GET',policy['url']),{'params':policy['params'],'verify':True,'allow_redirects':False,'timeout':(10,30),'stream':True})]
    with pytest.raises(ValueError):session.get(policy['url'],params=policy['params'],verify=True)
    assert len(calls)==1


@pytest.mark.parametrize('changes',[{'method':'POST'},{'url':'https://other.invalid/api/dcim/devices/42/'},
    {'params':{'fields':'id,token'}},{'verify':False},{'proxies':{'https':'http://other.invalid'}},
    {'headers':{'Authorization':'Bearer attacker'}},{'timeout':999}])
def test_http_refuses_before_request(http,changes):
    session,policy,calls,_=http
    request={'method':'GET','url':policy['url'],'params':policy['params'],'verify':True};request.update(changes)
    with pytest.raises(ValueError):session.request(**request)
    assert calls==[]


@pytest.mark.parametrize('status,body,content_type',[(302,b'{}','application/json'),(401,b'{}','application/json'),
    (200,b'{"token":"nbt_fixture.secret"}','application/json'),(200,b'{"id":1,"id":2}','application/json'),
    (200,b'{"x":NaN}','application/json'),(200,b'[]','application/json'),(200,b'<html>','text/html'),
    (200,b'x'*(netbox_http.MAX_RESPONSE+1),'application/json')])
def test_http_bad_results_never_return_secret_or_retry(http,status,body,content_type):
    session,policy,calls,response=http
    response.status_code=status;response.headers['Content-Type']=content_type
    response.iter_content=lambda _:iter([body])
    with pytest.raises(ValueError,match='^netbox_read_failed_or_unknown$'):
        session.get(policy['url'],params=policy['params'],verify=True)
    assert len(calls)==1


def hashed(raw):return hashlib.sha256(raw).hexdigest()

def write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    path.write_bytes(raw);path.chmod(0o600)
    return hashed(raw)


@pytest.fixture
def mcp_config(tmp_path):
    root=tmp_path.resolve()
    python=root/'venv/bin/python'
    write(python,b'#!/bin/sh\nexit 1\n');python.chmod(0o700)
    write(root/'venv/pyvenv.cfg',b'include-system-site-packages = false\n')
    manifest={'files':{'bin/python':hashed(python.read_bytes()),'pyvenv.cfg':hashed((root/'venv/pyvenv.cfg').read_bytes())},
              'symlinks':{},'executable_sha256':hashed(python.read_bytes())}
    manifest_path=root/'python-manifest.json';manifest_hash=write(manifest_path,runtime.canonical(manifest))
    source=root/'source';sources={}
    for name in ('server.py','netbox_client.py','netclaw_http.py','netbox_types.py','config.py'):
        relative='src/netbox_mcp_server/'+name;sources[relative]=write(source/relative,('# fixture '+name).encode())
    skill=root/'skills/netbox-reconcile/SKILL.md';skill_hash=write(skill,b'Fixture reviewed NetBox skill')
    token=root/'netbox.env';write(token,b'NETBOX_TOKEN=nbt_fixture.secret\n')
    return {'kind':'netbox','tool':'netbox_get_object_by_id','python':str(python),'python_manifest':str(manifest_path),
        'python_manifest_sha256':manifest_hash,'source_root':str(source),'source_sha256':sources,
        'input_schema_sha256':runtime.sha({'type':'object'}),'origin':'https://fixture.invalid','credential_file':str(token),
        'endpoint_sha256':runtime.sha({'kind':'netbox','origin':'https://fixture.invalid'}),
        'selection_sha256':runtime.sha({'tool':'netbox_get_object_by_id','arguments':DEVICE}),
        'skill':{'path':str(skill),'sha256':skill_hash}}


@pytest.mark.parametrize('change',['source','skill','python','extra_source','endpoint','selection','credential_mode'])
def test_local_drift_refuses_before_child(mcp_config,change):
    cfg=mcp_config
    if change=='source':Path(cfg['source_root'],'src/netbox_mcp_server/server.py').write_text('changed')
    if change=='skill':Path(cfg['skill']['path']).write_text('changed')
    if change=='python':Path(cfg['python']).write_text('changed')
    if change=='extra_source':Path(cfg['source_root'],'evil.py').write_text('changed')
    if change=='endpoint':cfg['origin']='https://other.invalid'
    if change=='selection':cfg['selection_sha256']='0'*64
    if change=='credential_mode':Path(cfg['credential_file']).chmod(0o644)
    with pytest.raises(runtime.RuntimeRefused):integration.validate_binding(cfg,arguments=DEVICE)


def test_mcp_child_calls_existing_tool_with_frozen_scope_and_private_credentials(mcp_config,tmp_path,monkeypatch):
    observed=[]
    @asynccontextmanager
    async def child(params,**kwargs):
        observed.append(params)
        assert params.env['NETBOX_TOKEN']=='nbt_fixture.secret'
        assert params.env['PYTHON_DOTENV_DISABLED']=='1'
        assert not {'ANTHROPIC_API_KEY','HTTPS_PROXY','NETCLAW_R04_GUARD_TOKEN'} & set(params.env)
        assert params.args==['-B','-m','netbox_mcp_server.server','--transport','stdio']
        assert json.loads(Path(params.env['NETCLAW_NETBOX_POLICY']).read_text())['url'].endswith('/dcim/devices/42/')
        yield object(),object()
    class Session:
        def __init__(self,*args):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def initialize(self):pass
        async def list_tools(self):return SimpleNamespace(tools=[SimpleNamespace(name='netbox_get_object_by_id',input_schema={'type':'object'})])
        async def call_tool(self,name,args,**kwargs):
            assert name=='netbox_get_object_by_id' and args==DEVICE
            return SimpleNamespace(is_error=False,structured_content={'id':42,'name':'fixture','status':{'value':'active'},
                'site':{'id':1},'device_type':{'id':2},'last_updated':'2026-11-03T00:00:00Z'},content=[])
    import mcp,mcp.client.stdio
    monkeypatch.setattr(mcp,'ClientSession',Session);monkeypatch.setattr(mcp.client.stdio,'stdio_client',child)
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-never-forward');monkeypatch.setenv('HTTPS_PROXY','http://forbidden.invalid')
    result=asyncio.run(integration.invoke_mcp(mcp_config,DEVICE,tmp_path/'operation'))
    assert len(observed)==1 and result['output']['id']==42 and result['mcp_calls']==1
    assert result['skill_sha256']==mcp_config['skill']['sha256'] and result['captured_at_ms']>0
    assert 'nbt_fixture.secret' not in json.dumps(result)
    for p in (tmp_path/'operation').rglob('*'):
        if p.is_file():assert b'nbt_fixture.secret' not in p.read_bytes()


def test_openclaw_exposes_only_selected_native_tool():
    payload={'model_profile':{'model':'claude-sonnet-4-6'},'tool_call':{'tool':'netbox_get_object_by_id'}}
    cfg=docker.openclaw_config(payload,'relay')
    assert cfg['tools']['allow']==['approved__netbox_get_object_by_id']
    assert cfg['mcp']['servers']['approved']['toolFilter']['include']==['netbox_get_object_by_id']
    with pytest.raises(runtime.RuntimeRefused):docker.validate_raw_mcp_call({'method':'tools/call','params':{'name':'netbox_get_object_by_id','arguments':dict(DEVICE,object_id=43)}},DEVICE,'netbox_get_object_by_id')


def test_native_unix_http_connection_never_uses_tcp(tmp_path):
    name='r04_relay_test';spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/protected-inference.py')
    relay=importlib.util.module_from_spec(spec);spec.loader.exec_module(relay)
    import tempfile
    with tempfile.TemporaryDirectory(prefix='r04uds-',dir=str(Path('/tmp').resolve())) as directory:
        path=Path(directory)/'broker.sock';listener=socket.socket(socket.AF_UNIX);listener.bind(str(path));listener.listen(1)
        observed=[]
        def serve():
            conn,_=listener.accept()
            with conn:
                raw=b''
                while b'\r\n\r\n' not in raw: raw+=conn.recv(4096)
                head,body=raw.split(b'\r\n\r\n',1)
                while len(body)<2: body+=conn.recv(4096)
                observed.append(head+b'\r\n\r\n'+body);conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}')
        thread=threading.Thread(target=serve);thread.start()
        conn=relay.UnixHTTPConnection(str(path));conn.request('POST','/mcp',b'{}')
        assert conn.getresponse().read()==b'{}';conn.close();thread.join(timeout=2);listener.close()
        assert b'POST /mcp' in observed[0]


def test_readiness_is_an_explicit_single_record_list_policy(tmp_path):
    path=tmp_path/'policy.json'
    policy={'schemaVersion':2,'purpose':'readiness','url':'https://fixture.invalid/api/dcim/devices/',
            'params':{'fields':','.join(DEVICE['fields']),'limit':1,'offset':0,'ordering':'id'}}
    write(path,json.dumps(policy).encode())
    assert netbox_http.load_policy(str(path))==policy
    for params in (dict(policy['params'],limit=2),dict(policy['params'],offset=1),dict(policy['params'],q='anything')):
        write(path,json.dumps(dict(policy,params=params)).encode())
        with pytest.raises(ValueError):netbox_http.load_policy(str(path))


@pytest.mark.parametrize('tool,arguments',[('netbox_get_object_by_id',DEVICE),('netbox_get_object_by_id',PREFIX),('subnet_calculator',SUBNET)])
def test_mixed_tool_completed_claims_survive_lost_ack_and_restart(tmp_path,tool,arguments):
    from protected_support_171 import OperationPair
    async def scenario():
        pair=OperationPair(tmp_path)
        selected=dict(pair.template['tool_call'],tool=tool,arguments=arguments,arguments_sha256=runtime.sha(arguments))
        pair.template['tool_call']=selected
        pair.catalog_entry['tools']=[dict(selected,limits={k:v for k,v in pair.template['limits'].items() if k!='expires_at_ms'})]
        prepared=await pair.prepare();await pair.decide(prepared);await pair.drain()
        pair.drop_ack_reply=True
        await pair.reconcile(prepared['operation_id'])
        assert len(pair.effects)==1 and pair.executor_calls==1
        await pair.restart();pair.drop_ack_reply=False
        await pair.reconcile(prepared['operation_id'])
        assert len(pair.effects)==1 and pair.executor_calls==1
        await pair.border.close();await pair.member.close()
    asyncio.run(scenario())
