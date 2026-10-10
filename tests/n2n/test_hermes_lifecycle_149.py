import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import pytest
from bgp.federation.runtime import selected,ROOT
from bgp.federation.execution import ExecutionBroker,ExecutionScope,digest
from bgp.federation.hermes_runtime import HermesRuntime


@pytest.mark.skipif(not all(os.environ.get(k) for k in ('NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON')),reason='real pinned Hermes fixture required')
def test_real_private_runtime_tool_and_chat_profiles(tmp_path,monkeypatch,manager):
    spec=importlib.util.spec_from_file_location('fixture149_provider',ROOT/'tests/hermes-hud/fixtures/provider.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    provider=module.Provider();url=provider.start()
    home=tmp_path/'Hermes Home';home.mkdir(mode=0o700)
    monkeypatch.setenv('NETCLAW_RUNTIME','hermes');monkeypatch.setenv('HERMES_HOME',str(home))
    monkeypatch.setenv('OPENAI_API_KEY','fixture-only-key');monkeypatch.setenv('OPENAI_BASE_URL',url)
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    records=home/'python-runtimes/records';records.mkdir(parents=True,mode=0o700)
    (records/'hermes-hud').write_text(sys.executable+'\n')
    (records/'subnet-calc').write_text(os.environ['NETCLAW_SUBNET_PYTHON']+'\n')
    config={'model':{'default':'hud-fixture','provider':'custom','base_url':url},'mcp_servers':{'subnet-calc-mcp':{
        'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'subnet-calc','--server','subnet-calc-mcp'],
        'env':{'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env')}}}}
    (home/'config.yaml').write_text(json.dumps(config));original=(home/'config.yaml').read_bytes()
    skill=home/'skills/subnet-calculator';skill.mkdir(parents=True)
    shutil.copyfile(ROOT/'workspace/skills/subnet-calculator/SKILL.md',skill/'SKILL.md')
    runtime=selected(initialize=True)
    broker=ExecutionBroker(manager,runtime)
    companion=HermesRuntime(runtime,broker)
    async def run():
        await broker.start()
        try:
            await companion.start()
            status=await companion.call('status')
            assert status['installationId']==runtime.installation and status['namespace']=='federation'
            for request,prompt,profile,target in [('r1','SUBNET','subnet','subnet-calculator'),('r2','remember violet','chat','chat-a')]:
                scope=ExecutionScope(runtime.installation,'peer-a','external',request,'conversation-'+request,
                    'skill' if profile=='subnet' else 'chat',target,digest(prompt),time.time()+60,profile)
                token=broker.issue(scope,lambda _:True)
                output,tokens=await companion.turn(prompt,scope,token)
                assert output
            # Constructor snapshot survives the upstream worker-thread handoff.
            import sqlite3
            with sqlite3.connect(runtime.state/'ledger.db') as db:
                evidence=db.execute("SELECT tool,state FROM evidence WHERE request='r1'").fetchall()
                assert any('subnet_calculator' in tool and state=='completed' for tool,state in evidence)
                assert not db.execute("SELECT 1 FROM evidence WHERE request='r2'").fetchone()
            assert (home/'config.yaml').read_bytes()==original
            assert not (home/'netclaw-hud/ledger.db').exists()
            # Kill only this fixture's child after actual provider dispatch.
            from bgp.federation.execution import OutcomeUnknown
            prompt='WAIT_FOR_TEST'
            scope=ExecutionScope(runtime.installation,'peer-a','external','lost-child','lost-conversation',
                'chat','chat-lost',digest(prompt),time.time()+60,'chat')
            permit=broker.issue(scope,lambda _:True)
            work=asyncio.create_task(companion.turn(prompt,scope,permit))
            assert await asyncio.to_thread(provider.started.wait,20)
            companion.process.kill();await companion.process.wait()
            with pytest.raises(OutcomeUnknown):await work
            count=len(provider.calls)
            provider.release.set()
            await companion.close();await companion.start()
            recovered=await companion.call('request_status',conversationId=scope.conversation,requestId=scope.request)
            assert recovered['state'] in ('unknown','interrupted'),recovered
            assert len(provider.calls)==count  # restart reads evidence; never resubmits

        finally:await companion.close();await broker.close()
    try:asyncio.run(run())
    except Exception:
        log=runtime.state/'companion.log'
        if log.exists():print(log.read_text()[-12000:])
        raise
    finally:provider.close()
