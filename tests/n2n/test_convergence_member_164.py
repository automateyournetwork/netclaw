"""Real Risk routing/channel/receiver fixtures with a stubbed model, no provider calls."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService


CAPABILITY = 'convergence-observations'


def test_border_routes_convergence_member_and_preserves_receiver_authority(tmp_path, monkeypatch):
    monkeypatch.setenv('NETCLAW_RUNTIME', 'openclaw')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path/'xdg'))
    monkeypatch.setenv('N2N_RISK_MODE', 'testing')
    services=[];calls=[]
    for label in ('border','member'):
        home=tmp_path/label;home.mkdir(mode=0o700)
        monkeypatch.setenv('OPENCLAW_STATE_DIR', str(home))
        monkeypatch.setenv('OPENCLAW_CONFIG_PATH', str(home/'openclaw.json'))
        services.append(FederationService(local_as=65001, router_id='192.0.2.1',
            manager=FederationManager(base_dir=str(home/'n2n'))))
    border,member=services
    border.risk.set_role('border',risk_name='risk',enabled_stacks='in2n')
    member.risk.set_role('member',risk_name='risk',self_member_id='risk/convergence')
    member.member_scope={CAPABILITY}
    from bgp.federation import gateway
    async def model(prompt, **kwargs):
        calls.append((prompt, kwargs))
        assert kwargs['local'] is True
        # OpenClaw retains native config/tool controls; protected receiver
        # ExecutionScope is Hermes-only and is not widened by this profile.
        assert 'execution' not in kwargs
        return 'fixture evidence: record_limit=100; intent unknown',1
    monkeypatch.setattr(gateway,'run_agent_turn',model)

    async def terminal(task):
        for _ in range(100):
            result=await border.poll_member_task('risk/convergence',task,'result')
            if result['state'] in ('completed','failed','cancelled'):return result
            await asyncio.sleep(.01)
        raise AssertionError('member task did not settle')

    async def run():
        server=await asyncio.start_server(border.accept_internal,'127.0.0.1',0)
        try:
            await member.dial_border('127.0.0.1',server.sockets[0].getsockname()[1],
                enrollment_token=border.risk.issue_token(label='convergence')['token'])
            # Registration scope, not arbitrary observation text, determines routing.
            border.manager._conn.execute('UPDATE member SET scope=? WHERE member_id=?',
                (json.dumps([{'name':CAPABILITY,'type':'skill','tier':'specialty'}]),'risk/convergence'))
            border.manager._conn.commit()
            accepted=await border.route_and_delegate(CAPABILITY,'same-window evidence')
            assert accepted['member_id']=='risk/convergence'
            result=await terminal(accepted['task_id'])
            assert result['state']=='completed',result
            assert 'record_limit=100' in result['output_text']
            assert not calls[-1][1].get('untrusted', False)
            missing=await border.route_and_delegate('missing-dns-source','corroborate')
            assert missing['error']=='IN2N_ERR_NO_CAPABLE_MEMBER'
            denied=await border.delegate_to_member('risk/convergence','pyats-config-mgmt','write')
            assert denied['error']=='out_of_scope'
            # External origin must still reach the existing untrusted execution gate.
            forwarded=await border.route_and_delegate(CAPABILITY,'external evidence',
                execution_scope=SimpleNamespace(origin='external',deadline=time.time()+30))
            assert (await terminal(forwarded['task_id']))['state']=='completed'
            assert calls[-1][1]['untrusted'] is True
            assert len({item[1]['session_key'] for item in calls})==2
            member.member_scope.clear()
            revoked=await border.route_and_delegate(CAPABILITY,'revoked source')
            assert revoked['error']=='out_of_scope'
            assert len(calls)==2
        finally:
            server.close()
            if member.border_channel:await member.border_channel.close()
            for ch in list(border.member_channels.values()):await ch.close()
            await server.wait_closed()
            for service in services:
                if service.tasks._workers:
                    await asyncio.gather(*service.tasks._workers.values(),return_exceptions=True)
                service.manager.close()
    asyncio.run(run())
