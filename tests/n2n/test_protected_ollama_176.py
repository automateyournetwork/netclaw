"""Thermidor-derived R05 profile and unknown-latch cases; source tests, not live proof."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import uuid

import pytest
from protected_support_171 import module, runtime_module, file_module, SOURCE

ollama = module('protected_ollama')


def profile(tmp_path, family=4):
    arch='arm64' if family==4 else 'amd64'
    return {'schema_version':1,'family':family,'architecture':arch,'runner_version':ollama.RUNNER,'model':ollama.MODEL,
        'model_image':'sha256:'+'a'*64,'runner_manifest_sha256':ollama.RUNNER_MANIFESTS[arch],
        'manifest_sha256':ollama.MANIFEST,'layer_sha256s':list(ollama.LAYERS),
        'model_container':'netclaw-r05-model-fixture','model_container_id':'b'*64,
        'model_store':str(tmp_path/'models'),'guard_uid':501,'model_uid':10002,
        'confinement_file':str(tmp_path/'confinement.json'),'confinement_sha256':'c'*64}


def payload(family=4):
    return {'operation_id':str(uuid.uuid4()),'model_profile':{'provider':'ollama','model':ollama.MODEL,'profile_id':'ollama-cpu-ipv'+str(family)},
            'tool_call':{'tool':'subnet_calculator' if family==4 else 'subnet_calculator_v6',
                         'arguments':{'cidr':'192.0.2.0/26' if family==4 else '2001:db8:1234::/48'}},
            'limits':{'expires_at_ms':2000000000000,'inference_timeout_ms':60000}}


def request(approved):
    return {'model':ollama.MODEL,'messages':[{'role':'system','content':'harness scaffolding'}, {'role':'user','content':'untrusted task text'}],
        'tools':[{'type':'function','function':{'name':'approved__'+approved['tool_call']['tool'],
            'parameters':{'type':'object','properties':{'cidr':{'type':'string','title':'Cidr'}},'required':['cidr']}}}],
        'stream':True,'max_completion_tokens':1024}


def reply(approved, ordinal=1):
    message={'role':'assistant','content':None,'tool_calls':[{'id':'call-1','type':'function',
        'function':{'name':'approved__'+approved['tool_call']['tool'],'arguments':json.dumps(approved['tool_call']['arguments'])}}]}
    if ordinal==2:message={'role':'assistant','content':'The returned network has 64 addresses.'}
    return {'id':'completion-1','object':'chat.completion','created':1800000000,'model':ollama.MODEL,
        'choices':[{'index':0,'finish_reason':'tool_calls' if ordinal==1 else 'stop','message':message}],
        'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}}


@pytest.mark.parametrize('family',[4,6])
def test_final_profile_has_exact_proven_resource_limits(tmp_path,family):
    value=profile(tmp_path,family);ollama.validate_profile(value)
    bound=ollama.limits(value)
    assert bound['agent_memory_mib']==1536 and bound['model_memory_mib']==2048
    assert bound['max_turns']==2 and bound['max_tool_calls']==1 and bound['provider_charge_microusd']==0
    assert bound['call_timeout_seconds']==(60 if family==4 else 120)
    assert bound['keep_alive_seconds']==(30 if family==4 else 120)


@pytest.mark.parametrize('key,value',[('model','other:latest'),('runner_version','latest'),('architecture','amd64'),
    ('manifest_sha256','d'*64),('layer_sha256s',[]),('model_image','latest'),('guard_uid',0),('model_uid',501),
    ('model_container','unowned'),('confinement_sha256','bad')])
def test_profile_cannot_silently_widen_or_replace_model(tmp_path,key,value):
    selected=profile(tmp_path);selected[key]=value
    with pytest.raises(ollama.OllamaRefused):ollama.validate_profile(selected)


@pytest.mark.parametrize('name,accepted', [('netclaw-r08-owned-model',True),
    ('netclaw-r05-owned-model',True),('netclaw-r09-unqualified-model',False),
    ('netclaw-r08-',False),('foreign-r08-model',False)])
def test_r08_owned_namespace_is_explicit_and_narrow(tmp_path,name,accepted):
    selected=profile(tmp_path);selected['model_container']=name
    if accepted:assert ollama.validate_profile(selected)==selected
    else:
        with pytest.raises(ollama.OllamaRefused,match='ollama_container_unowned'):ollama.validate_profile(selected)


def test_runner_latch_blocks_new_operation_after_timeout_and_restart(tmp_path):
    path=tmp_path/'runner.sqlite';revision='a'*64
    latch=ollama.RunnerLatch(path,revision)
    old=str(uuid.uuid4());reservation=latch.begin(old,'b'*64);latch.uncertain(reservation);latch.close()
    restarted=ollama.RunnerLatch(path,revision)
    with pytest.raises(ollama.OllamaRefused,match='recovery_required'):restarted.begin(str(uuid.uuid4()),'c'*64)
    with pytest.raises(ollama.OllamaRefused,match='verified_recovery'):restarted.recover({'stopped':True},verify=lambda *_:False)
    assert restarted.snapshot()['state']=='uncertain'
    checksum=restarted.recover({'actual_stopped_container':'fixed-id','old_operation':old},verify=lambda receipt,state:state['operation_id']==old and receipt['old_operation']==old)
    assert restarted.snapshot()['recovery_sha256']==checksum
    restarted.begin(str(uuid.uuid4()),'d'*64)
    assert restarted.db.execute('SELECT COUNT(*) FROM runner_recovery').fetchone()[0]==1
    restarted.close()


def test_in_flight_crash_never_becomes_idle_or_rebinds(tmp_path):
    latch=ollama.RunnerLatch(tmp_path/'runner.sqlite','a'*64);latch.begin(str(uuid.uuid4()),'b'*64);latch.close()
    with pytest.raises(ollama.OllamaRefused,match='profile_changed'):ollama.RunnerLatch(tmp_path/'runner.sqlite','c'*64)
    restarted=ollama.RunnerLatch(tmp_path/'runner.sqlite','a'*64)
    with pytest.raises(ollama.OllamaRefused,match='recovery_required'):restarted.begin(str(uuid.uuid4()),'b'*64)
    restarted.close()


@pytest.mark.parametrize('family',[4,6])
def test_v4_uses_signed_call_and_preserves_real_second_turn(tmp_path,family):
    selected=profile(tmp_path,family);approved=payload(family);body=request(approved)
    first=ollama.calculator_request(body,approved,selected)
    assert first['reasoning_effort']=='none' and first['max_tokens']==1024 and first['stream'] is False
    assert approved['tool_call']['arguments']['cidr'] in first['messages'][1]['content']
    assert 'untrusted task' not in str(first['messages'])
    assistant=reply(approved)['choices'][0]['message'];tool={'role':'tool','tool_call_id':'call-1','content':'{"num_addresses":"64"}'}
    body['messages'] += [assistant,tool]
    second=ollama.calculator_request(body,approved,selected)
    assert second['messages'][-2:]==[assistant,tool]
    assert body['messages'][0]['content']=='harness scaffolding'


@pytest.mark.parametrize('change',[lambda b:b.update(reasoning_effort='none'),lambda b:b['tools'].append(copy.deepcopy(b['tools'][0])),
    lambda b:b['tools'][0]['function'].update(name='unapproved'),lambda b:b['tools'][0]['function']['parameters']['properties'].update(url={'type':'string'}),
    lambda b:b['messages'].append({'role':'user','content':'another task'}),lambda b:b['messages'].append({'role':'assistant','content':'pretend result'})])
def test_prompt_caller_cannot_choose_controls_or_fabricate_history(tmp_path,change):
    approved=payload();body=request(approved);change(body)
    with pytest.raises(ollama.OllamaRefused):ollama.calculator_request(body,approved,profile(tmp_path))


@pytest.mark.parametrize('mutation',[lambda r:r['choices'][0].update(finish_reason='stop'),
    lambda r:r['choices'][0]['message'].update(tool_calls=[]),lambda r:r['usage'].update(total_tokens=0),
    lambda r:r['choices'][0]['message']['tool_calls'][0]['function'].update(arguments='{"cidr":"192.0.2.64/26"}')])
def test_model_must_make_real_exact_tool_call_with_measured_usage(mutation):
    approved=payload();response=reply(approved);mutation(response)
    with pytest.raises(ollama.OllamaRefused):ollama.validate_response(response,1,approved)


def test_scoped_unknown_fences_the_next_operation_and_keeps_prior_claim(tmp_path):
    runtime=runtime_module();fence=runtime.InferenceFence(tmp_path/'inference.sqlite');latch=ollama.RunnerLatch(tmp_path/'runner.sqlite','a'*64)
    approved=payload();count=[]
    async def forward(_):count.append('dispatched');raise TimeoutError('fixture')
    scoped=runtime.ScopedInference(approved,'token',fence,forward,runner_latch=latch)
    async def scenario():
        with pytest.raises(runtime.RuntimeUnknown):await scoped.invoke('POST','/v1/chat/completions',{'authorization':'Bearer token'},request(approved))
        other=payload();fresh=runtime.ScopedInference(other,'token',fence,forward,runner_latch=latch)
        with pytest.raises(runtime.RuntimeRefused,match='recovery_required'):await fresh.invoke('POST','/v1/chat/completions',{'authorization':'Bearer token'},request(other))
    asyncio.run(scenario())
    assert count==['dispatched'] and fence.count(approved['operation_id'])==1 and latch.snapshot()['state']=='uncertain'
    fence.close();latch.close()


def test_two_admitted_turns_preserve_actual_native_result_and_measured_tokens(tmp_path):
    runtime=runtime_module();fence=runtime.InferenceFence(tmp_path/'inference.sqlite');latch=ollama.RunnerLatch(tmp_path/'runner.sqlite','a'*64)
    approved=payload();evidence=None;requests=[]
    def adapt(body):
        body=ollama.validate_history(body,fence.first_response(approved['operation_id']),evidence)
        return ollama.calculator_request(body,approved,profile(tmp_path))
    async def forward(body):
        requests.append(copy.deepcopy(body));response=reply(approved,len(requests))
        if len(requests)==1:response['choices'][0]['message']['tool_calls'][0]['id']='call_m9aee3p2'
        return response
    scoped=runtime.ScopedInference(approved,'token',fence,forward,request_adapter=adapt,
        response_validator=lambda result,ordinal:ollama.validate_response(result,ordinal,approved),
        runner_latch=latch,tool_finished=lambda:evidence is not None)
    async def scenario():
        nonlocal evidence
        body=request(approved);first=await scoped.invoke('POST','/v1/chat/completions',{'authorization':'Bearer token'},body)
        evidence={'output':{'num_addresses':'64'},'independent_verification':True,'mcp_calls':1,'native_result_sha256':'d'*64}
        assistant=copy.deepcopy(first['choices'][0]['message']);assistant['tool_calls'][0]['id']='callm9aee3p2'
        body['messages'] += [assistant,{'role':'tool','tool_call_id':'callm9aee3p2','content':ollama.canonical(evidence['output']).decode()}]
        await scoped.invoke('POST','/v1/chat/completions',{'authorization':'Bearer token'},body)
        with pytest.raises(runtime.RuntimeRefused):await scoped.invoke('POST','/v1/chat/completions',{'authorization':'Bearer token'},body)
    asyncio.run(scenario())
    assert len(requests)==2 and latch.snapshot()['state']=='idle'
    assert requests[1]['messages'][-2]['tool_calls'][0]['id']=='call_m9aee3p2'
    assert requests[1]['messages'][-1]['tool_call_id']=='call_m9aee3p2'
    assert fence.usage(approved['operation_id'])=={'prompt_tokens':200,'completion_tokens':40,'total_tokens':240}
    assert fence.final_answer(approved['operation_id'])=='The returned network has 64 addresses.'
    fence.close();latch.close()
