"""Real pinned Hermes, MCP tools, iN2N and bidirectional eN2N over loopback."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import pytest
from bgp.federation.runtime import ROOT
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.channel import read_handshake
from bgp.constants import NCFED_MAGIC


def configure(home,url):
    home.mkdir(mode=0o700)
    records=home/'python-runtimes/records';records.mkdir(parents=True)
    for name,value in [('hermes-hud',sys.executable),('n2n',sys.executable),('subnet-calc',os.environ['NETCLAW_SUBNET_PYTHON'])]:
        (records/name).write_text(value+'\n')
    (home/'.env').write_text('OPENAI_API_KEY=fixture-only\nOPENAI_BASE_URL='+url+'\n');(home/'.env').chmod(0o600)
    (home/'config.yaml').write_text(json.dumps({'model':{'default':'hud-fixture','provider':'custom','base_url':url},'mcp_servers':{
        'subnet-calc-mcp':{'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'subnet-calc','--server','subnet-calc-mcp'],
            'env':{'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env')}},
        'n2n-mcp':{'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'n2n','--server','n2n-mcp'],
            'env':{'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env'),'BGP_DAEMON_API':'${BGP_DAEMON_API:-http://127.0.0.1:8179}'}}}}))
    skill=home/'skills/subnet-calculator';skill.mkdir(parents=True);shutil.copyfile(ROOT/'workspace/skills/subnet-calculator/SKILL.md',skill/'SKILL.md')


async def terminal(service,peer,task,internal=False):
    for _ in range(150):
        value=await service.poll_member_task(peer,task,'result') if internal else await service.invoker.poll_remote_task(peer,task,'result')
        if value['state'] not in ('submitted','working'):return value
        await asyncio.sleep(.1)
    raise AssertionError('task never reached an observable outcome')


@pytest.mark.skipif(not all(os.environ.get(k) for k in ('NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON')),reason='real pinned Hermes fixture required')
def test_real_hermes_internal_and_bidirectional_external(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('federation_provider149',ROOT/'tests/hermes-hud/fixtures/provider.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    provider=module.Provider();url=provider.start()
    monkeypatch.setenv('N2N_CERT_MODE','on')
    monkeypatch.setenv('NETCLAW_RUNTIME','hermes');monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    monkeypatch.setenv('OPENAI_API_KEY','fixture-only');monkeypatch.setenv('OPENAI_BASE_URL',url)
    services=[];servers=[]
    async def run():
        for index in range(3):
            home=tmp_path/f'hermes-{index}';configure(home,url);monkeypatch.setenv('HERMES_HOME',str(home))
            service=FederationService(local_as=65001+index,router_id=f'{index+1}.{index+1}.{index+1}.{index+1}',manager=FederationManager(base_dir=str(home/'n2n')))
            await service.start_runtime();services.append(service)
        a,b,member=services
        a.risk.set_role('border',risk_name='risk',enabled_stacks='both')
        member.risk.set_role('member',risk_name='risk',self_member_id='risk/subnet');member.member_scope={'subnet-calculator'}
        server=await asyncio.start_server(a.accept_internal,'127.0.0.1',0);servers.append(server)
        await member.dial_border('127.0.0.1',server.sockets[0].getsockname()[1],enrollment_token=a.risk.issue_token()['token'])
        a.manager._conn.execute('UPDATE member SET scope=? WHERE member_id=?',(json.dumps([{'name':'subnet-calculator','type':'skill','tier':'specialty'}]),'risk/subnet'));a.manager._conn.commit()
        result=await a.delegate_to_member('risk/subnet','subnet-calculator','SUBNET')
        resolved=await terminal(a,'risk/subnet',result['task_id'],True)
        assert resolved['state']=='completed' and '192.0.2.' in resolved['output_text'],resolved
        # eN2N carries its normal consent, possession and grant gates.
        a.manager.local_consent(b.local_as,b.router_id);b.manager.local_consent(a.local_as,a.router_id)
        async def receive(reader,writer):
            assert await reader.readexactly(5)==NCFED_MAGIC
            asn,rid=await read_handshake(reader);await b.accept_channel(asn,rid,reader,writer)
        server=await asyncio.start_server(receive,'127.0.0.1',0);servers.append(server)
        await a.open_channel(b.local_as,b.router_id,'127.0.0.1',server.sockets[0].getsockname()[1])
        await asyncio.sleep(.3)
        for caller,receiver in [(a,b),(b,a)]:
            assert caller.manager.is_federated(receiver.local_identity)
            receiver.authz.grant(caller.local_identity,'tool','subnet-calc-mcp/subnet_calculator')
            receiver.authz.grant(caller.local_identity,'skill','subnet-calculator')
            receiver.manager.set_chat_enabled(caller.local_identity,True)
            caller.manager.set_chat_enabled(receiver.local_identity,True)
            tool=await caller.invoker.invoke_remote_tool(receiver.local_identity,'subnet-calc-mcp/subnet_calculator',{'cidr':'192.0.2.0/28'})
            assert '192.0.2.' in json.dumps(tool),tool
            submitted=await caller.invoker.submit_remote_skill(receiver.local_identity,'subnet-calculator','SUBNET')
            result=await terminal(caller,receiver.local_identity,submitted['task_id'])
            assert result['state']=='completed' and '192.0.2.' in result['output_text'],result
            chat=await caller.chat.open_and_send(receiver.local_identity,'remember violet')
            follow=await caller.chat.open_and_send(receiver.local_identity,'what colour?',chat['session_id'])
            assert 'violet' in follow['text'],follow
            separate=await caller.chat.open_and_send(receiver.local_identity,'what colour?')
            assert 'violet' not in separate['text'],separate
            card=caller.inventory.load_remote(receiver.local_identity)['inventory']
            assert card['harness']['type']=='hermes'
        # A phone reaches both permitted delegation paths through the protected
        # operator profile, official n2n MCP client, and actual remote receivers.
        from test_edge_ask import _serve,_enroll
        server,port=await _serve(a);servers.append(server)
        phone=await _enroll(a,port)
        try:
            for peer in ('risk/subnet',b.local_identity):
                accepted=await phone.call('n2n/edge/ask',{'text':'MOBILE_DELEGATE:'+peer,'request_id':'mobile-'+peer,'client_capabilities':['task_outcomes_v1']})
                for _ in range(450):
                    result=await phone.call('n2n/tasks/result',{'task_id':accepted['task_id']})
                    if result['state'] not in ('submitted','working'):break
                    await asyncio.sleep(.1)
                assert result['state']=='completed' and '192.0.2.' in result['output_text'],result
        finally:await phone.ws.close();await phone.close()

    async def owned():
        try:await run()
        finally:
            for service in services:
                for channel in list(service.channels.values())+list(service.member_channels.values()):await channel.close()
                if service.border_channel:await service.border_channel.close()
            for server in servers:server.close()
            for service in services:await service.stop_runtime();service.manager.close()
    try:asyncio.run(owned())
    finally:provider.close()
