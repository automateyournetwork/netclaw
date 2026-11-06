"""Actual SDK shape plus adversarial inspection fixtures; no deployment claim."""
import asyncio
import copy
import hashlib
import json
import pytest
from protected_support_171 import docker_module
from test_protected_ollama_176 import ollama, profile, payload, request, reply


def model_fixture(tmp_path):
    selected=profile(tmp_path);namespace='net:[4026532000]'
    receipt={'schema_version':1,'container_id':selected['model_container_id'],'image':selected['model_image'],
        'network_namespace_inode':namespace,'guard_uid':501,'model_uid':10002,'model_api':'127.0.0.1:11434',
        'worker_range':[32768,65535],'excluded_ports':[4000,4001,11434,49171],
        'policy_sha256':'d'*64,'positive_control':True,'denied_callers':['agent','broker','border','sibling','external']}
    write_receipt(selected,receipt)
    ports={}
    container={'Id':selected['model_container_id'],'Name':'/'+selected['model_container'],'Image':selected['model_image'],
        'State':{'Running':True,'OOMKilled':False},'Config':{'User':'10002','Entrypoint':['/usr/local/bin/ollama'],'Cmd':['serve'],
            'Env':[k+'='+v for k,v in ollama.model_environment(selected).items()]},
        'HostConfig':{'ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],'CapAdd':[],
            'SecurityOpt':['no-new-privileges'],'Devices':[],'PidMode':'','IpcMode':'private',
            'NetworkMode':'netclaw-r05-owned','Memory':2048*1024**2,'MemorySwap':2048*1024**2,
            'NanoCpus':2*10**9,'PidsLimit':256,'PortBindings':copy.deepcopy(ports)},
        'NetworkSettings':{'Networks':{'netclaw-r05-owned':{}},'Ports':ports},
        'Mounts':[{'Type':'bind','Source':selected['model_store'],'Destination':'/models','RW':False}]}
    return selected,container,namespace,receipt


def write_receipt(selected,receipt):
    from pathlib import Path
    raw=ollama.canonical(receipt);p=Path(selected['confinement_file']);p.write_bytes(raw);p.chmod(0o600)
    selected['confinement_sha256']=hashlib.sha256(raw).hexdigest()


def test_neither_model_nor_guard_has_published_port(tmp_path):
    selected,container,namespace,_=model_fixture(tmp_path)
    assert ollama.verify_confinement(selected,container,namespace,policy_sha256='d'*64)['guard_url']=='docker-exec://'+'b'*64+'/127.0.0.1:4000'


@pytest.mark.parametrize('mutate',[
    lambda c:c['Config'].update(User='0'),lambda c:c['Config'].update(Cmd=['serve','--another']),
    lambda c:c['Config']['Env'].append('ANTHROPIC_API_KEY=fixture-private'),
    lambda c:c['Config']['Env'].append('OLLAMA_HOST=0.0.0.0:11434'),
    lambda c:c['HostConfig'].update(ReadonlyRootfs=False),lambda c:c['HostConfig'].update(MemorySwap=-1),
    lambda c:c['HostConfig'].update(NetworkMode='host'),lambda c:c['HostConfig'].update(CapAdd=['NET_ADMIN']),
    lambda c:c['HostConfig']['PortBindings'].update({'11434/tcp':[{'HostIp':'127.0.0.1','HostPort':'11434'}]}),
    lambda c:c['NetworkSettings']['Ports'].update({'4000/tcp':[{'HostIp':'127.0.0.1','HostPort':'40099'}]}),
    lambda c:c['NetworkSettings']['Networks'].update(other={}),lambda c:c['Mounts'][0].update(RW=True),
    lambda c:c['Mounts'].append({'Type':'bind','Source':'/var/run/docker.sock','Destination':'/var/run/docker.sock','RW':False}),
    lambda c:c['State'].update(OOMKilled=True),lambda c:c.update(Id='e'*64),
])
def test_container_changes_fail_closed(tmp_path,mutate):
    selected,container,namespace,_=model_fixture(tmp_path);mutate(container)
    with pytest.raises(ollama.OllamaRefused):ollama.verify_confinement(selected,container,namespace,policy_sha256='d'*64)


@pytest.mark.parametrize('mutate',[lambda r:r.update(positive_control=False),lambda r:r.update(denied_callers=['agent']),
    lambda r:r.update(network_namespace_inode='net:[123]'),lambda r:r.update(excluded_ports=[4000]),
    lambda r:r.update(worker_range=[1024,65535])])
def test_measured_receipt_requires_live_identity_positive_and_all_negative_controls(tmp_path,mutate):
    selected,container,namespace,receipt=model_fixture(tmp_path);mutate(receipt);write_receipt(selected,receipt)
    with pytest.raises(ollama.OllamaRefused):ollama.verify_confinement(selected,container,namespace,policy_sha256='d'*64)


@pytest.mark.parametrize('family',[4,6])
def test_real_mcp_sdk_encodes_one_compact_text_result_without_structured_copy(family):
    from mcp.server.mcpserver import MCPServer
    expected={'network_address':'192.0.2.0' if family==4 else '2001:db8::','num_addresses':'64' if family==4 else '1208925819614629174706176'}
    called=[]
    class Broker:
        async def call(self,tool,args):
            called.append((tool,args));return {'output':expected,'independent_verification':True,'mcp_calls':1,'native_result_sha256':'f'*64}
    tool='subnet_calculator' if family==4 else 'subnet_calculator_v6';server=MCPServer('R05 wire fixture')
    server.add_tool(docker_module().compact_summary_tool(Broker(),tool))
    result=asyncio.run(server.call_tool(tool,{'cidr':'192.0.2.0/26' if family==4 else '2001:db8::/48'}))
    wire=result.model_dump(mode='json',exclude_none=True)
    assert 'structuredContent' not in wire and len(wire['content'])==1
    assert wire['content'][0]['type']=='text' and wire['content'][0]['text']==ollama.canonical(expected).decode()
    assert len(called)==1


def test_second_turn_cannot_invent_tool_output_or_assistant_call():
    approved=payload();first=reply(approved);body=request(approved);evidence={'output':{'num_addresses':'64'},'independent_verification':True,'mcp_calls':1,'native_result_sha256':'f'*64}
    body['messages'] += [copy.deepcopy(first['choices'][0]['message']),{'role':'tool','tool_call_id':'call-1','content':ollama.canonical(evidence['output']).decode()}]
    ollama.validate_history(body,first,evidence)
    forged=copy.deepcopy(body);forged['messages'][-1]['content']='{"num_addresses":"65"}'
    with pytest.raises(ollama.OllamaRefused,match='invented_tool'):ollama.validate_history(forged,first,evidence)
    forged=copy.deepcopy(body);forged['messages'][-2]['tool_calls'][0]['id']='invented'
    with pytest.raises(ollama.OllamaRefused,match='invented_assistant'):ollama.validate_history(forged,first,evidence)
    with pytest.raises(ollama.OllamaRefused):ollama.validate_history(body,None,evidence)


def test_firewall_digest_ignores_counters_and_handles_but_not_rules(tmp_path):
    original={'nftables':[{'metainfo':{'version':'fixture'}},{'chain':{'family':'inet','name':'output','handle':1}},
        {'rule':{'chain':'output','handle':2,'expr':[{'counter':{'packets':1,'bytes':60}},{'drop':None}]}}]}
    changed=copy.deepcopy(original);changed['nftables'][-1]['rule']['expr'][0]['counter']['bytes']=600
    changed['nftables'][-1]['rule']['handle']=99
    assert ollama.nft_policy_digest(changed)==ollama.nft_policy_digest(original)
    changed['nftables'][-1]['rule']['expr'][-1]={'accept':None}
    assert ollama.nft_policy_digest(changed)!=ollama.nft_policy_digest(original)
    selected,container,namespace,_=model_fixture(tmp_path)
    with pytest.raises(ollama.OllamaRefused,match='firewall_changed'):
        ollama.verify_confinement(selected,container,namespace,policy_sha256='e'*64)


def test_base_image_environment_is_not_a_routing_override_allowlist(tmp_path):
    selected,container,namespace,_=model_fixture(tmp_path);container['Config']['Env'].append('LD_LIBRARY_PATH=/tmp/injected')
    with pytest.raises(ollama.OllamaRefused):
        ollama.verify_confinement(selected,container,namespace,policy_sha256='d'*64,image_environment=['LD_LIBRARY_PATH=/usr/local/lib/ollama'])


def test_local_forward_uses_fixed_namespace_helper_and_stdin_only_capability(tmp_path,monkeypatch):
    import time
    docker=docker_module();selected=profile(tmp_path);approved=payload();approved['limits']['expires_at_ms']=int(time.time()*1000)+30000
    executor=object.__new__(docker.DockerExecutor);executor.config={};executor.ollama=selected
    marker='docker-exec://'+selected['model_container_id']+'/127.0.0.1:4000'
    executor.guards={approved['operation_id']:marker};executor.guard_token='fixture-private-guard-token';calls=[]
    async def inspect():return {'guard_url':marker}
    async def command(*args,**kwargs):calls.append((args,kwargs));return ollama.canonical(reply(approved))
    executor.inspect_model=inspect;executor.command=command;monkeypatch.setattr(docker,'validate_execution_bindings',lambda *_:None)
    result=asyncio.run(executor.forward(approved,request(approved)))
    assert result==reply(approved) and len(calls)==1
    args,kwargs=calls[0]
    assert args[:5]==('exec','--interactive','--user','501',selected['model_container_id'])
    assert executor.guard_token not in str(args) and 'input_data' in kwargs
    sent=json.loads(kwargs['input_data']);assert sent['guard_token']==executor.guard_token and sent['request']==request(approved)
    assert "http://127.0.0.1:4000/v1/chat/completions" in args[-1] and 'NoRedirect' in args[-1]
    assert 'X-DC-Target-URL' in args[-1] and 'http://127.0.0.1:11434' in args[-1]


from test_protected_revision_bindings import bound

def test_real_subprocess_pipe_carries_request_without_capability_in_argv_or_env(bound):
    import sys
    from pathlib import Path
    from types import SimpleNamespace
    docker=docker_module();config,_,_=bound
    Path(config['docker']).write_text('#!'+sys.executable+'\nimport hashlib,json,os,sys\nraw=sys.stdin.buffer.read()\nprint(json.dumps({"argv":sys.argv[1:],"env":dict(os.environ),"stdin_sha256":hashlib.sha256(raw).hexdigest()}))\n')
    executor=docker.DockerExecutor(config,manager=SimpleNamespace());secret='fixture-pipe-only-capability';body=ollama.canonical({'guard_token':secret,'request':{'model':ollama.MODEL}})
    try:
        observed=json.loads(asyncio.run(executor.command('exec','--interactive','fixture-container',input_data=body)))
        assert observed['stdin_sha256']==hashlib.sha256(body).hexdigest()
        assert secret not in str(observed['argv'])+str(observed['env'])
    finally:executor.fence.close()


def native_history():
    approved=payload();first=reply(approved);body=request(approved)
    evidence={'output':{'address_count':'64'},'independent_verification':True,'mcp_calls':1,'native_result_sha256':'f'*64}
    body['messages'] += [copy.deepcopy(first['choices'][0]['message']),{'role':'tool','tool_call_id':'call-1','content':ollama.canonical(evidence['output']).decode()}]
    return first,body,evidence


def test_native_argument_json_reserialization_preserves_actual_call():
    first,body,evidence=native_history();body['messages'][-2]['tool_calls'][0]['function']['arguments']='{\n "cidr"  : "192.0.2.0/26"\n}'
    ollama.validate_history(body,first,evidence)
    assert body['messages'][-2]['tool_calls'][0]['function']['arguments'].startswith('{\n')


@pytest.mark.parametrize('raw',['{"cidr":"wrong","cidr":"192.0.2.0/26"}','{"cidr":NaN}','{"cidr":Infinity}',
    '{"cidr":-Infinity}','{"cidr":1e9999}','{"cidr":"192.0.2.64/26"}','{"cidr":"192.0.2.0/26","extra":false}'])
def test_native_history_refuses_duplicate_nonfinite_or_changed_argument(raw):
    first,body,evidence=native_history();body['messages'][-2]['tool_calls'][0]['function']['arguments']=raw
    with pytest.raises(ollama.OllamaRefused):ollama.validate_history(body,first,evidence)
    response=reply(payload());response['choices'][0]['message']['tool_calls'][0]['function']['arguments']=raw
    with pytest.raises(ollama.OllamaRefused):ollama.validate_response(response,1,payload())


@pytest.mark.parametrize('field,value',[('id','made-up'),('type','other')])
def test_native_history_never_normalizes_changed_call_identity(field,value):
    first,body,evidence=native_history();body['messages'][-2]['tool_calls'][0][field]=value
    with pytest.raises(ollama.OllamaRefused):ollama.validate_history(body,first,evidence)


@pytest.mark.parametrize('actual',['call_m9aee3p2','call_'+'a'*80])
def test_pinned_openclaw_strict_alias_restores_retained_provider_id(tmp_path,actual):
    # Actual pinned OpenClaw 2026.7.1-2 offline wire fixture exposed strict IDs;
    # the generated alias is derived from the admitted response, not user input.
    first,body,evidence=native_history();first['choices'][0]['message']['tool_calls'][0]['id']=actual
    native=actual.replace('_','')[:40]
    body['messages'][-2]['tool_calls'][0]['id']=native
    body['messages'][-1]['tool_call_id']=native
    original=copy.deepcopy(body)
    restored=ollama.validate_history(body,first,evidence)
    adapted=ollama.calculator_request(restored,payload(),profile(tmp_path))
    assert adapted['messages'][-2]['tool_calls'][0]['id']==actual
    assert adapted['messages'][-1]['tool_call_id']==actual
    assert body==original and first['choices'][0]['message']['tool_calls'][0]['id']==actual


@pytest.mark.parametrize('assistant_id,tool_id',[
    ('callm9aee3p2','call_m9aee3p2'),('call_m9aee3p2','callm9aee3p2'),
    ('callmadeup','callmadeup'),('callM9aee3p2','callM9aee3p2'),
    ('callm9aee3p2x2','callm9aee3p2x2'),('m9aee3p2','m9aee3p2')])
def test_native_alias_never_allows_invented_or_mismatched_ids(assistant_id,tool_id):
    first,body,evidence=native_history();first['choices'][0]['message']['tool_calls'][0]['id']='call_m9aee3p2'
    body['messages'][-2]['tool_calls'][0]['id']=assistant_id;body['messages'][-1]['tool_call_id']=tool_id
    with pytest.raises(ollama.OllamaRefused):ollama.validate_history(body,first,evidence)


@pytest.mark.parametrize('extra',['assistant','tool','text'])
def test_native_history_has_no_extra_content_fields(extra):
    first,body,evidence=native_history()
    if extra=='assistant':body['messages'][-2]['invented']='extra'
    elif extra=='tool':body['messages'][-1]['invented']='extra'
    else:body['messages'][-1]['content']=[{'type':'text','text':body['messages'][-1]['content'],'invented':'extra'}]
    with pytest.raises(ollama.OllamaRefused):ollama.validate_history(body,first,evidence)


def test_native_tool_output_can_only_use_one_exact_text_content():
    first,body,evidence=native_history();text=body['messages'][-1]['content']
    body['messages'][-1]['content']=[{'type':'text','text':text}]
    ollama.validate_history(body,first,evidence)
    body['messages'][-1]['content'].append({'type':'text','text':'extra'})
    with pytest.raises(ollama.OllamaRefused):ollama.validate_history(body,first,evidence)


@pytest.mark.parametrize('code,expected',[
    ('ollama_invented_assistant_history','ollama_invented_assistant_history'),
    ('SECRET arbitrary exception/body','inference_refused'),
    ('secret_looking_valid_code','inference_refused')])
def test_private_refusal_diagnostic_is_fixed_bounded_and_preserves_first(tmp_path,code,expected):
    module=docker_module();module.record_inference_refusal(tmp_path,code)
    receipt=tmp_path/'inference-refusal.json';before=receipt.read_bytes()
    assert json.loads(before)=={'schema_version':1,'code':expected}
    assert receipt.stat().st_mode&0o777==0o600
    module.record_inference_refusal(tmp_path,'ollama_tool_history_changed')
    assert receipt.read_bytes()==before


@pytest.mark.parametrize('local,port',[(True,18970),(False,4001)])
def test_native_guard_readiness_uses_the_frozen_profile_management_port(tmp_path,monkeypatch,local,port,capsys):
    import io
    import urllib.request
    seen=[]
    def urlopen(url,*,timeout):
        seen.append((url,timeout))
        return io.BytesIO(json.dumps({'guardrail':{'state':'running','details':{'mode':'action'}},
            'provenance':{'binary_version':'1.0.4'}}).encode())
    monkeypatch.setattr(urllib.request,'urlopen',urlopen)
    exec(docker_module().guard_health_probe(profile(tmp_path) if local else None),{})
    assert seen==[('http://127.0.0.1:'+str(port)+'/health',2)]
    assert json.loads(capsys.readouterr().out)['version']=='1.0.4'
