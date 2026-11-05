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
    ports={'4000/tcp':[{'HostIp':'127.0.0.1','HostPort':'40099'}]}
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


def test_only_guard_loopback_port_is_published(tmp_path):
    selected,container,namespace,_=model_fixture(tmp_path)
    assert ollama.verify_confinement(selected,container,namespace,policy_sha256='d'*64)['guard_url']=='http://127.0.0.1:40099'


@pytest.mark.parametrize('mutate',[
    lambda c:c['Config'].update(User='0'),lambda c:c['Config'].update(Cmd=['serve','--another']),
    lambda c:c['Config']['Env'].append('ANTHROPIC_API_KEY=fixture-private'),
    lambda c:c['Config']['Env'].append('OLLAMA_HOST=0.0.0.0:11434'),
    lambda c:c['HostConfig'].update(ReadonlyRootfs=False),lambda c:c['HostConfig'].update(MemorySwap=-1),
    lambda c:c['HostConfig'].update(NetworkMode='host'),lambda c:c['HostConfig'].update(CapAdd=['NET_ADMIN']),
    lambda c:c['HostConfig']['PortBindings'].update({'11434/tcp':[{'HostIp':'127.0.0.1','HostPort':'11434'}]}),
    lambda c:c['NetworkSettings']['Ports']['4000/tcp'][0].update(HostIp='0.0.0.0'),
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
