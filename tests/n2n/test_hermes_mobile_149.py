"""Actual authenticated edge ingress into the pinned protected Hermes runtime."""
import asyncio
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
import pytest
from bgp.federation.runtime import ROOT
from test_edge_ask import _border,_serve,_enroll,_FakePhone
from bgp.federation.risk import RiskManager
import websockets


async def reconnect(port,previous):
    ws=await websockets.connect(f'ws://127.0.0.1:{port}')
    challenge=asyncio.get_running_loop().create_future()
    def receive(params):
        if not challenge.done():challenge.set_result(bytes.fromhex(params['nonce']))
        return {}
    phone=_FakePhone(ws,{'n2n/edge/challenge':receive})
    nonce=await asyncio.wait_for(challenge,5)
    await phone.call('in2n/hello',{'member_id':previous.member_id,'key_fingerprint':previous.fingerprint,
        'signature':RiskManager.sign_challenge(previous.key_pem,nonce).hex()})
    phone.key_pem=previous.key_pem;phone.fingerprint=previous.fingerprint;phone.member_id=previous.member_id
    return phone


@pytest.mark.skipif(not all(os.environ.get(k) for k in ('NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON')),reason='real pinned Hermes fixture required')
def test_authenticated_mobile_text_voice_recovery_and_media_refusal(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('mobile149_provider',ROOT/'tests/hermes-hud/fixtures/provider.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    provider=module.Provider();url=provider.start()
    home=tmp_path/'Hermes Border';home.mkdir(mode=0o700)
    monkeypatch.setenv('NETCLAW_RUNTIME','hermes');monkeypatch.setenv('HERMES_HOME',str(home))
    monkeypatch.setenv('OPENAI_API_KEY','fixture-only-key');monkeypatch.setenv('OPENAI_BASE_URL',url)
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    records=home/'python-runtimes/records';records.mkdir(parents=True,mode=0o700)
    (records/'hermes-hud').write_text(sys.executable+'\n');(records/'subnet-calc').write_text(os.environ['NETCLAW_SUBNET_PYTHON']+'\n')
    config={'model':{'default':'hud-fixture','provider':'custom','base_url':url},'mcp_servers':{
        'subnet-calc-mcp':{'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'subnet-calc','--server','subnet-calc-mcp'],
            'env':{'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env')}},
        'n2n-mcp':{'command':'python3','args':['-u',str(ROOT/'mcp-servers/n2n-mcp/server.py')]}}}
    (home/'config.yaml').write_text(json.dumps(config))
    skill=home/'skills/subnet-calculator';skill.mkdir(parents=True);shutil.copyfile(ROOT/'workspace/skills/subnet-calculator/SKILL.md',skill/'SKILL.md')
    border=_border(home/'n2n')
    async def run():
        await border.start_runtime()
        server,port=await _serve(border)
        phones=[]
        try:
            phone=await _enroll(border,port);phones.append(phone)
            other=await _enroll(border,port,'risk/phone2');phones.append(other)
            async def ask(text,request,**extra):
                body={'text':text,'request_id':request,'conversation_id':'conversation-a','client_capabilities':['task_outcomes_v1'],**extra}
                accepted=await phone.call('n2n/edge/ask',body)
                task=accepted['task_id']
                for _ in range(300):
                    result=await phone.call('n2n/tasks/result',{'task_id':task})
                    if result['state'] not in ('submitted','working'):break
                    await asyncio.sleep(.1)
                assert result['state']=='completed',result
                # Receipt recovery reads the original admission; never sends again.
                found=await phone.call('n2n/tasks/result',{'request_id':request})
                assert found['task_id']==task and found['output_text']==result['output_text']
                assert (await other.call('n2n/tasks/result',{'task_id':task}))['state']=='unknown'
                return result
            result=await ask('SUBNET','request-subnet')
            assert '192.0.2.' in result['output_text']
            await ask('remember violet','request-remember')
            result=await ask('what colour did I say?','request-followup')
            assert 'violet' in result['output_text']
            await ask('speak my status','request-voice',origin='voice')
            from bgp.federation.gateway import _VOICE_COMPOSITION_INSTRUCTION
            assert any(_VOICE_COMPOSITION_INSTRUCTION in str(message.get('content')) for call in provider.calls for message in call.get('messages',[]))
            # A real disconnection during an admitted turn is recovered by an
            # authenticated hello, and the result is pushed to the new socket.
            provider.started.clear();provider.release.clear()
            accepted=await phone.call('n2n/edge/ask',{'text':'WAIT_FOR_TEST reconnect','request_id':'slow-reconnect','client_capabilities':['task_outcomes_v1']})
            assert await asyncio.to_thread(provider.started.wait,10)
            await phone.wait_for_notification('n2n/edge/task_progress',timeout=15)
            await phone.ws.close();await phone.close()
            phone=await reconnect(port,phone);phones.append(phone)
            provider.release.set()
            for _ in range(150):
                result=await phone.call('n2n/tasks/result',{'request_id':'slow-reconnect'})
                if result['state']=='completed':break
                await asyncio.sleep(.1)
            assert result['state']=='completed',result
            pushed=await phone.wait_for_notification('n2n/edge/ask_result',timeout=5)
            assert pushed['task_id']==accepted['task_id']
            # A cancellation acknowledgement is a request, never proof of stop.
            provider.started.clear();provider.release.clear()
            accepted=await phone.call('n2n/edge/ask',{'text':'WAIT_FOR_TEST cancel','request_id':'slow-cancel','client_capabilities':['task_outcomes_v1']})
            assert await asyncio.to_thread(provider.started.wait,10)
            response=await phone.call('n2n/tasks/cancel',{'task_id':accepted['task_id']})
            assert response['cancel_requested'] and not response['cancellation_confirmed']
            provider.release.set()
            for _ in range(150):
                result=await phone.call('n2n/tasks/result',{'task_id':accepted['task_id']})
                if result['state'] not in ('working','submitted'):break
                await asyncio.sleep(.1)
            assert result['state'] in ('cancelled','outcome_unknown','completed'),result
            assert result['state'] not in ('working','submitted')
            count=len(provider.calls)
            with pytest.raises(RuntimeError,match='attachments are unavailable'):
                await phone.call('n2n/edge/ask',{'text':'photo','attachment':{'content_type':'image','content':'ZmFrZQ=='}})
            assert len(provider.calls)==count
            caps=border._edge_border_capabilities()
            assert caps['harness']['type']=='hermes' and caps['capabilities']['attachments'] is False
            # Revocation/key replacement prevents retrieving prior-generation work.
            border.manager._conn.execute("UPDATE member SET key_fingerprint='replacement' WHERE member_id='risk/phone1'")
            border.manager._conn.commit()
            assert (await phone.call('n2n/tasks/result',{'request_id':'request-subnet'}))['state']=='unknown'
        finally:
            for phone in phones:await phone.ws.close();await phone.close()
            server.close();await server.wait_closed()
            await border.stop_runtime()
    try:asyncio.run(run())
    except Exception:
        log=home/'netclaw-federation/companion.log'
        if log.exists():print(log.read_text()[-10000:])
        raise
    finally:provider.close();border.manager.close()
