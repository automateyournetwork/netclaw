import asyncio
import time
import pytest
from bgp.federation.execution import ExecutionScope, ExecutionBroker, Refused, OutcomeUnknown, digest, conversation_id
from bgp.federation.runtime import selected


def scope(runtime, **changes):
    return ExecutionScope(**dict(dict(installation=runtime.installation,requester='peer-a',origin='external',
        request='req-1',conversation='conv-1',target_type='skill',target='subnet-calculator',
        body_digest=digest('input'),deadline=time.time()+300,profile='subnet'),**changes))


@pytest.fixture
def runtime(tmp_path):
    return selected({'HOME':str(tmp_path),'NETCLAW_RUNTIME':'hermes','HERMES_HOME':str(tmp_path/'hermes')},initialize=True)


def test_receiver_cannot_promote_origin_or_tool(manager,runtime):
    with pytest.raises(Refused):scope(runtime,profile='operator')
    broker=ExecutionBroker(manager,runtime)
    permit=broker.issue(scope(runtime),lambda _:True)
    async def run():
        with pytest.raises(Refused):await broker.check(permit,'req-1','mcp__n2n_mcp__n2n_invoke',{})
        with pytest.raises(Refused):await broker.check(permit,'other')
        with pytest.raises(Refused):await broker.check(permit,'req-1','mcp__subnet_calc_mcp__subnet_calculator',{'cidr':'10.0.0.0/8'})
        assert (await broker.check(permit,'req-1','mcp__subnet_calc_mcp__subnet_calculator',{'cidr':'10.0.0.0/24'})).origin=='external'
    asyncio.run(run())


def test_revocation_restart_and_duplicate_fail_closed(manager,runtime):
    allowed=[True]
    broker=ExecutionBroker(manager,runtime)
    permit=broker.issue(scope(runtime),lambda _:allowed[0])
    with pytest.raises(Refused):broker.issue(scope(runtime),lambda _:True)
    allowed[0]=False
    with pytest.raises(Refused):asyncio.run(broker.check(permit,'req-1'))
    restarted=ExecutionBroker(manager,runtime)
    with pytest.raises(Refused):asyncio.run(restarted.check(permit,'req-1'))
    assert permit not in str([tuple(r) for r in manager._conn.execute('SELECT * FROM execution_scope')])


def test_operator_effect_replay_and_ownership(manager,runtime):
    broker=ExecutionBroker(manager,runtime)
    owner=scope(runtime,origin='operator',profile='operator')
    permit=broker.issue(owner,lambda _:True)
    count=[]
    async def invoke(*args):count.append(1);return {'task_id':'owned'}
    async def run():
        assert await broker.effect(permit,owner.request,'call1','delegate',{},invoke)=={'task_id':'owned'}
        assert await broker.effect(permit,owner.request,'call1','delegate',{},invoke)=={'task_id':'owned'}
        with pytest.raises(Refused):await broker.effect(permit,owner.request,'call1','delegate',{'different':1},invoke)
        async def uncertain(*args):raise ConnectionError('lost receipt')
        with pytest.raises(ConnectionError):await broker.effect(permit,owner.request,'call2','delegate',{},uncertain)
        with pytest.raises(OutcomeUnknown):await broker.effect(permit,owner.request,'call2','delegate',{},invoke)
    asyncio.run(run())
    assert len(count)==1
    broker.own(owner,'task','owned','peer-a')
    assert broker.owner(owner,'task','owned')=='peer-a'
    with pytest.raises(Refused):broker.owner(scope(runtime,conversation='foreign'),'task','owned')


def test_sessions_include_installation_owner_and_conversation():
    ids={conversation_id(i,p,c) for i in ('i1','i2') for p in ('p1','p2') for c in ('c1','c2')}
    assert len(ids)==8
