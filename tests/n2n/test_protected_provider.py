"""No provider calls: durable provider retry fence, real loopback and process faults."""
import asyncio
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lib'))
import protected_provider as provider

KEY='sk-ant-private-fixture-never-a-real-provider-key'
NOW=1800000000000

def request(text='fixture'):
    return {'model':'claude-sonnet-4-6','max_tokens':64,'messages':[{'role':'user','content':[{'type':'text','text':text}]}]}

def fence_at(tmp_path,**kwargs):
    return provider.ProviderFence(tmp_path/'owned/provider.sqlite',operation_id=str(uuid.uuid4()),expires_at_ms=NOW+300000,clock_ms=lambda:NOW,**kwargs)

async def post(port,body,extra='',path='/v1/messages'):
    reader,writer=await asyncio.open_connection('127.0.0.1',port)
    writer.write((f'POST {path} HTTP/1.1\r\nHost: attacker.invalid\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n'+extra+'\r\n').encode()+body)
    await writer.drain();raw=await reader.read();writer.close();await writer.wait_closed()
    if not raw:return None
    headers,data=raw.split(b'\r\n\r\n',1)
    return int(headers.split()[1]),data


def test_four_retry_requests_reuse_one_cached_response(tmp_path):
    async def run():
        fence=fence_at(tmp_path);seen=[]
        async def upstream(value):seen.append(value);return provider.ProviderResponse(200,b'{"fixture":"answer"}')
        proxy=provider.ProviderProxy(fence,KEY,upstream=upstream)
        responses=[await proxy.process(provider.canonical(request())) for _ in range(4)]
        assert len(seen)==1 and all(response.status==200 and response.body==responses[0].body for response in responses)
        assert fence.snapshot()['upstream_attempt_count']==1
    asyncio.run(run())


def test_actual_http_three_lost_responses_then_cache(tmp_path):
    async def run():
        fence=fence_at(tmp_path);seen=[]
        async def upstream(value):seen.append(value);return provider.ProviderResponse(200,b'{"fixture":true}')
        class DropResponses(provider.ProviderProxy):
            count=0
            async def async_send_response(self,writer,response):
                self.count+=1
                if self.count<=3:writer.transport.abort();return
                await super().async_send_response(writer,response)
        proxy=DropResponses(fence,KEY,upstream=upstream);port=await proxy.start(port=0)
        try:
            answers=[await post(port,provider.canonical(request())) for _ in range(4)]
            assert answers[:3]==[None,None,None] and answers[3]==(200,b'{"fixture":true}')
            assert proxy.count==4 and len(seen)==1
        finally:await proxy.close()
    asyncio.run(run())


def test_concurrent_duplicates_forward_only_one_inflight_request(tmp_path):
    async def run():
        fence=fence_at(tmp_path);seen=[];entered=asyncio.Event();release=asyncio.Event()
        async def upstream(value):seen.append(value);entered.set();await release.wait();return provider.ProviderResponse(200,b'{}')
        proxy=provider.ProviderProxy(fence,KEY,upstream=upstream);port=await proxy.start(port=0)
        try:
            original=asyncio.create_task(post(port,provider.canonical(request())))
            await entered.wait()
            duplicates=await asyncio.gather(*(post(port,provider.canonical(request())) for _ in range(8)))
            assert all(result[0]==409 for result in duplicates)
            release.set();assert (await original)[0]==200
            assert (await post(port,provider.canonical(request())))[0]==200
            assert len(seen)==1 and fence.snapshot()['upstream_attempt_count']==1
        finally:release.set();await proxy.close()
    asyncio.run(run())


def test_accepted_upstream_eof_then_restart_never_forwards_again(tmp_path):
    async def run():
        fence=fence_at(tmp_path);seen=[]
        async def unknown(value):seen.append(value);raise ConnectionError('fixture accepted request then EOF')
        proxy=provider.ProviderProxy(fence,KEY,upstream=unknown)
        for _ in range(4):assert (await proxy.process(provider.canonical(request()))).status==409
        restarted=provider.ProviderFence(fence.path,operation_id=fence.operation_id,expires_at_ms=fence.expires_at_ms,clock_ms=lambda:NOW)
        proxy=provider.ProviderProxy(restarted,KEY,upstream=unknown)
        for _ in range(4):assert (await proxy.process(provider.canonical(request()))).status==409
        assert (await proxy.process(provider.canonical(request('changed after unknown')))).status==409
        assert len(seen)==1 and restarted.snapshot()['requests'][0]['state']=='unknown'
    asyncio.run(run())


def test_timeout_and_cancellation_keep_spent_claim(tmp_path):
    async def run():
        fence=fence_at(tmp_path);seen=[]
        async def stalled(value):seen.append(value);await asyncio.sleep(10)
        proxy=provider.ProviderProxy(fence,KEY,upstream=stalled,timeout=.02)
        assert (await proxy.process(provider.canonical(request()))).status==409
        assert (await proxy.process(provider.canonical(request()))).status==409
        assert len(seen)==1
        other=fence_at(tmp_path/'other');entered=asyncio.Event()
        async def cancel(value):entered.set();await asyncio.sleep(10)
        proxy=provider.ProviderProxy(other,KEY,upstream=cancel)
        task=asyncio.create_task(proxy.process(provider.canonical(request())))
        await entered.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert other.snapshot()['requests'][0]['state']=='unknown'
        assert (await proxy.process(provider.canonical(request()))).status==409
    asyncio.run(run())


def test_two_distinct_requests_limit_and_canonical_replay(tmp_path):
    async def run():
        fence=fence_at(tmp_path);seen=[]
        async def upstream(value):seen.append(value);return provider.ProviderResponse(200,b'{}')
        proxy=provider.ProviderProxy(fence,KEY,upstream=upstream)
        assert (await proxy.process(json.dumps(request(),indent=3).encode())).status==200
        assert (await proxy.process(provider.canonical(request()))).status==200
        assert (await proxy.process(provider.canonical(request('summary')))).status==200
        assert (await proxy.process(provider.canonical(request('third')))).status==429
        assert len(seen)==2 and fence.snapshot()['upstream_attempt_count']==2
    asyncio.run(run())


@pytest.mark.parametrize('change,expected',[
    ({'model':'claude-opus-4-6'},403),({'base_url':'https://attacker.invalid'},400),
    ({'max_tokens':4097},403),({'max_tokens':True},403),({'messages':[]},400),({'stream':'true'},400)])
def test_policy_refuses_before_forward(tmp_path,change,expected):
    async def run():
        fence=fence_at(tmp_path);seen=[]
        def upstream(value):seen.append(value);return provider.ProviderResponse(200,b'{}')
        proxy=provider.ProviderProxy(fence,KEY,upstream=upstream)
        body=dict(request(),**change)
        assert (await proxy.process(provider.canonical(body))).status==expected
        assert seen==[] and fence.snapshot()['upstream_attempt_count']==0
    asyncio.run(run())


@pytest.mark.parametrize('raw',[b'{"model":"a","model":"b"}',b'{"x":NaN}',b'\xff',b'[]',b'{"a":'+b'['*40+b'0'+b']'*40+b'}'])
def test_strict_request_refusal(tmp_path,raw):
    async def run():
        proxy=provider.ProviderProxy(fence_at(tmp_path),KEY,upstream=lambda _:pytest.fail('unexpected upstream'))
        assert (await proxy.process(raw)).status==400
    asyncio.run(run())


def test_expiry_clock_rollback_and_immutable_operation_binding(tmp_path):
    async def run():
        now=[NOW];op=str(uuid.uuid4())
        fence=provider.ProviderFence(tmp_path/'owned/db',operation_id=op,expires_at_ms=NOW+100,clock_ms=lambda:now[0])
        async def upstream(value):return provider.ProviderResponse(200,b'{}')
        proxy=provider.ProviderProxy(fence,KEY,upstream=upstream)
        assert (await proxy.process(provider.canonical(request()))).status==200
        now[0]=NOW-1
        assert (await proxy.process(provider.canonical(request('second')))).status==403
        now[0]=NOW+100
        assert (await proxy.process(provider.canonical(request('second')))).status==403
        assert (await proxy.process(provider.canonical(request()))).status==200 # historical cached read only
        for changes in ({'operation_id':str(uuid.uuid4())},{'expires_at_ms':NOW+200}):
            with pytest.raises(provider.ProviderRefused,match='foreign_or_changed_operation'):
                binding={'operation_id':op,'expires_at_ms':NOW+100};binding.update(changes)
                provider.ProviderFence(fence.path,**binding,clock_ms=lambda:NOW)
    asyncio.run(run())


def test_response_cache_refuses_redirect_secret_echo_and_oversize(tmp_path):
    async def run():
        cases=[(provider.ProviderResponse(302,b'go',{'Location':'https://attacker.invalid'}),502),
               (provider.ProviderResponse(200,KEY.encode()),502),
               (provider.ProviderResponse(200,b'{}',{'request-id':KEY}),502),
               (provider.ProviderResponse(200,b'x'*(provider.MAX_RESPONSE+1)),409)]
        for index,(response,status) in enumerate(cases):
            fence=fence_at(tmp_path/str(index));seen=[]
            def upstream(value):seen.append(value);return response
            proxy=provider.ProviderProxy(fence,KEY,upstream=upstream)
            result=await proxy.process(provider.canonical(request()))
            assert result.status==status and KEY.encode() not in result.body
            assert (await proxy.process(provider.canonical(request()))).status==status
            assert len(seen)==1 and KEY.encode() not in fence.path.read_bytes()
    asyncio.run(run())


def test_fixed_https_destination_and_owned_auth_ignore_proxy_environment(tmp_path,monkeypatch):
    observed=[]
    class Socket:
        def settimeout(self,value):assert value>0
    class Response:
        status=200
        body=b'{"ok":true}'
        def getheaders(self):return [('content-type','application/json')]
        def read1(self,n):result=self.body;self.body=b'';return result
    class Connection:
        def __init__(self,host,port,**kwargs):observed.append(('connect',host,port));self.sock=Socket()
        def connect(self):pass
        def request(self,method,path,body,headers):observed.append(('request',method,path,body,headers))
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(provider.http.client,'HTTPSConnection',Connection)
    monkeypatch.setenv('HTTPS_PROXY','https://attacker.invalid')
    async def run():
        proxy=provider.ProviderProxy(fence_at(tmp_path),KEY);port=await proxy.start(port=0)
        try:
            result=await post(port,provider.canonical(request()),extra='Authorization: Bearer foreign\r\nX-API-Key: foreign\r\nX-Forwarded-Host: attacker.invalid\r\n')
            assert result[0]==200
        finally:await proxy.close()
    asyncio.run(run())
    assert observed[0]==('connect','api.anthropic.com',443)
    _,method,path,raw,headers=observed[1]
    assert (method,path)==('POST','/v1/messages') and headers['x-api-key']==KEY
    assert headers['Anthropic-Version']=='2023-06-01' and 'Authorization' not in headers and 'X-Forwarded-Host' not in headers


def test_http_route_and_framing_refusals(tmp_path):
    async def run():
        fence=fence_at(tmp_path);proxy=provider.ProviderProxy(fence,KEY,upstream=lambda _:pytest.fail('unexpected upstream'))
        port=await proxy.start(port=0)
        try:
            assert (await post(port,provider.canonical(request()),path='/v1/messages?url=https://attacker.invalid'))[0]==404
            assert (await post(port,provider.canonical(request()),extra='Transfer-Encoding: chunked\r\n'))[0]==400
            assert (await post(port,provider.canonical(request()),extra='Content-Length: 1\r\n'))[0]==400
            assert fence.snapshot()['upstream_attempt_count']==0
        finally:await proxy.close()
    asyncio.run(run())


def process_claim(path,operation,expiry,effect_path,start,result_queue):
    f=provider.ProviderFence(path,operation_id=operation,expires_at_ms=expiry)
    start.wait()
    row=f.claim(request())
    if row['new_claim']:
        fd=os.open(effect_path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600);os.write(fd,b'one fixture upstream\n');os.fsync(fd);os.close(fd)
        f.finish(row['request_digest'],provider.ProviderResponse(200,b'{}'))
    result_queue.put(row['new_claim'])


def test_separate_processes_share_one_durable_forward_claim(tmp_path):
    operation=str(uuid.uuid4());expiry=int(time.time()*1000)+60000;path=tmp_path/'private/db'
    fence=provider.ProviderFence(path,operation_id=operation,expires_at_ms=expiry)
    context=multiprocessing.get_context('spawn');start=context.Event();queue=context.Queue();effect=tmp_path/'fixture-effects'
    children=[context.Process(target=process_claim,args=(path,operation,expiry,effect,start,queue)) for _ in range(8)]
    for child in children:child.start()
    start.set()
    try:
        for child in children:child.join(15);assert child.exitcode==0
        assert sum(queue.get(timeout=3) for _ in children)==1
        assert effect.read_bytes()==b'one fixture upstream\n' and fence.snapshot()['upstream_attempt_count']==1
    finally:
        for child in children:
            if child.is_alive():child.terminate();child.join(5)


def die_after_claim(path,operation,expiry):
    fence=provider.ProviderFence(path,operation_id=operation,expires_at_ms=expiry)
    assert fence.claim(request())['new_claim']
    os._exit(91)


def test_actual_process_death_leaves_unreplayable_claim(tmp_path):
    operation=str(uuid.uuid4());expiry=int(time.time()*1000)+60000;path=tmp_path/'private/db'
    child=multiprocessing.get_context('spawn').Process(target=die_after_claim,args=(path,operation,expiry));child.start();child.join(10)
    assert child.exitcode==91
    fence=provider.ProviderFence(path,operation_id=operation,expires_at_ms=expiry)
    async def run():
        proxy=provider.ProviderProxy(fence,KEY,upstream=lambda _:pytest.fail('unexpected replay'))
        for _ in range(4):assert (await proxy.process(provider.canonical(request()))).status==409
    asyncio.run(run())
    assert fence.snapshot()['upstream_attempt_count']==1


def guard_module():
    spec=importlib.util.spec_from_file_location('protected_guard_test',ROOT/'scripts/protected-guard.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def guard_home(tmp_path):
    home=provider.private_directory(tmp_path/'guard')
    provider.private_write(home/'guard.env',('ANTHROPIC_API_KEY='+KEY+'\nDEFENSECLAW_GATEWAY_TOKEN=fixture-private-guard-token\n').encode())
    config=('data_dir: '+str(home)+'\nllm:\n  model: anthropic/claude-sonnet-4-6\n  api_key_env: DEFENSECLAW_LLM_KEY\n  base_url: http://127.0.0.1:18888\n  forward_custom_headers: false\n').encode()
    provider.private_write(home/'config.yaml',config)
    policies=provider.private_directory(home/'policies');provider.private_write(policies/'fixture.yaml',b'fixture-only: true\n')
    manifest=[{'path':'policies/fixture.yaml','sha256':hashlib.sha256((policies/'fixture.yaml').read_bytes()).hexdigest()}]
    provider.private_write(home/'official-policy-manifest.json',manifest)
    return home,hashlib.sha256(config).hexdigest(),hashlib.sha256((home/'official-policy-manifest.json').read_bytes()).hexdigest()


def test_guard_runner_private_credentials_and_reviewed_config(tmp_path,monkeypatch):
    module=guard_module();home,config_hash,policy_hash=guard_home(tmp_path)
    secrets=module.load_guard_env(home)
    assert module.verify_config(home,config_hash,KEY)==config_hash
    assert module.verify_policies(home,policy_hash)==policy_hash
    monkeypatch.setenv('ANTHROPIC_API_KEY','foreign-inherited-key')
    monkeypatch.setenv('HTTPS_PROXY','http://attacker.invalid')
    environment=module.child_environment(home,secrets)
    assert 'ANTHROPIC_API_KEY' not in environment and 'HTTPS_PROXY' not in environment
    assert KEY not in environment.values() and environment['DEFENSECLAW_LLM_KEY']=='netclaw-operation-proxy'
    (home/'policies/fixture.yaml').write_bytes(b'changed')
    with pytest.raises(provider.ProviderRefused,match='guard_policy_changed'):module.verify_policies(home,policy_hash)
    with pytest.raises(provider.ProviderRefused,match='guard_config_changed'):module.verify_config(home,'f'*64,KEY)


def test_guard_runner_foreground_child_cleanup_and_sanitized_receipt(tmp_path):
    home,config_hash,policy_hash=guard_home(tmp_path)
    fake=tmp_path/'official-fixture'
    fake.write_text('#!'+sys.executable+'\nimport os,json\nfrom pathlib import Path\nPath(os.environ["DEFENSECLAW_HOME"],"fixture-child-env.json").write_text(json.dumps(dict(os.environ)))\n')
    fake.chmod(0o700)
    args=[sys.executable,str(ROOT/'scripts/protected-guard.py'),'--home',str(home),'--binary',str(fake),
          '--config-sha256',config_hash,'--policy-manifest-sha256',policy_hash,
          '--operation-id',str(uuid.uuid4()),'--expires-at-ms',str(int(time.time()*1000)+30000)]
    result=subprocess.run(args,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    child=json.loads((home/'fixture-child-env.json').read_text())
    assert 'ANTHROPIC_API_KEY' not in child and KEY not in json.dumps(child)
    receipt=json.loads((home/'provider-receipt.json').read_text())
    assert receipt['upstream_attempt_count']==0 and KEY not in json.dumps(receipt)
    assert KEY not in (home/'guard.log').read_text() and KEY not in result.stdout+result.stderr


def test_guard_policy_bootstrap_uses_only_pinned_image_and_preserves_existing(tmp_path):
    module=guard_module();source,_,manifest_hash=guard_home(tmp_path/'image')
    home=provider.private_directory(tmp_path/'new-guard')
    assert module.bootstrap_policies(home,manifest_hash,source)==manifest_hash
    assert (home/'policies/fixture.yaml').read_bytes()==b'fixture-only: true\n'
    assert (home/'official-policy-manifest.json').read_bytes()==(source/'official-policy-manifest.json').read_bytes()
    (home/'policies/fixture.yaml').write_bytes(b'changed existing runtime file')
    with pytest.raises(provider.ProviderRefused,match='guard_policy_changed'):
        module.bootstrap_policies(home,manifest_hash,source)
    assert (home/'policies/fixture.yaml').read_bytes()==b'changed existing runtime file'
    empty=provider.private_directory(tmp_path/'refused-guard')
    with pytest.raises(provider.ProviderRefused,match='guard_policy_manifest_changed'):
        module.bootstrap_policies(empty,'f'*64,source)
    assert not (empty/'policies').exists()


def test_guard_log_redacts_split_credentials_and_caps_output(tmp_path):
    module=guard_module();secret='sensitive-guard-token'
    class Reader:
        def __init__(self):self.parts=[b'before '+secret[:8].encode(),secret[8:].encode()+b' after\n'+b'x'*100,b'']
        async def read(self,_):return self.parts.pop(0)
    path=tmp_path/'guard.log'
    async def run():
        with path.open('wb') as stream:await module.drain_guard_log(Reader(),stream,{'credential':secret},maximum=64)
    asyncio.run(run())
    logged=path.read_bytes()
    assert secret.encode() not in logged and b'before [redacted] after' in logged and len(logged)==64
