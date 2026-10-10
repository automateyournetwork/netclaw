import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import time
import pytest
from bgp.federation.runtime import selected,ROOT
from bgp.federation.execution import ExecutionBroker,Refused
from bgp.federation.operator import OperatorBridge
from bgp.federation.operator_policy import wire_operation
from bgp.federation.service import FederationService


@pytest.mark.parametrize('name,args',[
    ('n2n_grant',{'peer':'p'}),('n2n_member_remove',{'member_id':'risk/subnet'}),
    ('n2n_invoke',{'peer':'p','target_type':'tool','target_name':'pyats/configure','arguments':'{}'}),
    ('n2n_route',{'request_text':'do anything'}),
    ('n2n_invoke',{'peer':'p','target_type':'tool','target_name':'subnet-calc-mcp/subnet_calculator','arguments':'{"cidr":"10.0.0.0/8"}'}),
    ('n2n_task_status',{'task_id':'../private'}),('n2n_status',{'origin':'operator'}),
])
def test_operator_surface_is_bounded(name,args):
    with pytest.raises(ValueError):wire_operation(name,args)


def test_official_n2n_mcp_operator_permit_and_owned_handle(tmp_path,monkeypatch,manager):
    home=tmp_path/'hermes';home.mkdir(mode=0o700)
    monkeypatch.setenv('NETCLAW_RUNTIME','hermes');monkeypatch.setenv('HERMES_HOME',str(home))
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    runtime=selected(initialize=True)
    records=home/'python-runtimes/records';records.mkdir(parents=True)
    (records/'hermes-hud').write_text(sys.executable+'\n')
    sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
    from ledger import Ledger
    from federation_tools import invoke_operator
    ledger=Ledger(home/'netclaw-hud/ledger.db',runtime.installation)
    ledger.open('operator-a');ledger.admit('operator-a','request-a','nonce-a','get subnet result',60000)
    service=FederationService(local_as=65001,router_id='1.1.1.1',manager=manager)
    service.runtime=runtime
    broker=ExecutionBroker(manager,runtime);broker.operator=OperatorBridge(service,broker)
    invoked=[]
    async def delegate(peer,skill,text,**kwargs):invoked.append((peer,skill,text));return {'task_id':'task-a'}
    service.invoker.submit_remote_skill=delegate
    async def run():
        await broker.start()
        try:
            args={'peer':'as65002-2.2.2.2','target_name':'subnet-calculator','input_text':'calculate 192.0.2.0/28'}
            name='mcp__n2n_mcp__n2n_delegate'
            first=await asyncio.to_thread(invoke_operator,home,ledger,'request-a','call-a',name,args)
            assert 'task-a' in first
            await asyncio.to_thread(invoke_operator,home,ledger,'request-a','call-a',name,args)
            assert len(invoked)==1
            with pytest.raises(Exception):await asyncio.to_thread(invoke_operator,home,ledger,'request-a','call-b','mcp__n2n_mcp__n2n_task_status',{'task_id':'foreign'})
            ledger.update('operator-a','request-a','cancelled')
            with pytest.raises(Exception):await asyncio.to_thread(invoke_operator,home,ledger,'request-a','call-c',name,args)
            assert len(invoked)==1
        finally:await broker.close()
    asyncio.run(run())


def test_installer_n2n_endpoint_is_removed_from_protected_discovery(tmp_path):
    sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
    from policy import qualified_servers
    home=tmp_path/'home'
    env={'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env'),
         'BGP_DAEMON_API':'${BGP_DAEMON_API:-http://127.0.0.1:8179}'}
    config={'mcp_servers':{'n2n-mcp':{'command':'python3','args':['-u',str(ROOT/'scripts/component-launch.py'),'n2n','--server','n2n-mcp'],'env':env}}}
    servers,_=qualified_servers(config,home=home)
    assert servers['n2n-mcp']['env']['NETCLAW_FEDERATION_SCOPED']=='1'
    assert 'BGP_DAEMON_API' not in servers['n2n-mcp']['env']
    env['BGP_DAEMON_API']='https://foreign.invalid/steal'
    assert 'n2n-mcp' not in qualified_servers(config,home=home)[0]
