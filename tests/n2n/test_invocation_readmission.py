"""Admission must still be valid after approval waits and scheduling."""
import asyncio
from types import SimpleNamespace
import pytest
from bgp.federation import invocation
from bgp.federation.channel import RpcError
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.service import FederationService


def service(tmp_path, monkeypatch):
    monkeypatch.setattr(invocation, '_security_mode', lambda: 'hobby')
    svc = FederationService(local_as=65001, router_id='4.4.4.4', display_name='fixture', manager=FederationManager(base_dir=str(tmp_path)))
    svc.manager.local_consent(65007, '7.7.7.7')
    svc.manager.remote_consent(65007, '7.7.7.7')
    return svc, SimpleNamespace(peer_identity=peer_identity(65007, '7.7.7.7'), attestation='possession')


@pytest.mark.parametrize('replace', [False, True])
def test_approval_cannot_restore_revoked_grant(tmp_path, monkeypatch, replace):
    svc, channel = service(tmp_path, monkeypatch)
    grant = svc.authz.grant(channel.peer_identity, 'tool', 'fixture/read', requires_approval=True)
    executed = []
    async def approve(_):
        svc.authz.revoke(grant)
        if replace: svc.authz.grant(channel.peer_identity, 'tool', 'fixture/read')
        return True
    async def execute(*args): executed.append(args); return {}
    svc.invoker._await_approval = approve
    svc.invoker._exec_tool_stdio = execute
    try:
        with pytest.raises(RpcError):
            asyncio.run(svc.invoker.handle_tools_call(channel, {'tool': 'fixture/read'}))
        assert executed == []
    finally:
        svc.manager.close()


def test_pending_skills_reserve_budget_before_execution(tmp_path, monkeypatch):
    svc, channel = service(tmp_path, monkeypatch)
    svc.authz.daily_requests = 1
    svc.authz.grant(channel.peer_identity, 'skill', 'fixture-skill')
    executed = []
    async def run():
        release = asyncio.Event()
        async def execute(*args, **kwargs):
            executed.append(args)
            await release.wait()
            return 'done', 3
        svc.invoker._exec_skill_gateway = execute
        one = await svc.invoker.handle_task_submit(channel, {'skill':'fixture-skill'})
        two = await svc.invoker.handle_task_submit(channel, {'skill':'fixture-skill'})
        workers = list(svc.tasks._workers.values())
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(*workers)
        assert len(executed) == 1
        assert sorted(svc.tasks.status(t['task_id'])['state'] for t in [one,two]) == ['completed','failed']
        assert svc.authz.budget_status(channel.peer_identity)['requests_used'] == 1
    try: asyncio.run(run())
    finally: svc.manager.close()


def test_replica_unshared_during_approval_refuses(tmp_path, monkeypatch):
    svc, channel = service(tmp_path, monkeypatch)
    collection = 'rag:fixture'
    svc.authz.grant(channel.peer_identity, 'knowledge_replica', collection, requires_approval=True)
    visible = [{'collection_id': collection}]
    svc.inventory._load_knowledge = lambda peer: visible
    async def approve(_):
        visible.clear()
        return True
    svc.invoker._await_approval = approve
    try:
        with pytest.raises(RpcError):
            asyncio.run(svc.invoker._replicate_gate(channel, {'collection_id': collection}, 'replicate_manifest'))
        assert svc.authz.budget_status(channel.peer_identity)['requests_used'] == 0
    finally:
        svc.manager.close()


@pytest.mark.parametrize('fault',['none','expired','changed','reused'])
def test_exact_approval_is_consumed_once(tmp_path,monkeypatch,fault):
    svc,channel=service(tmp_path,monkeypatch)
    svc.authz.grant(channel.peer_identity,'tool','fixture/read',requires_approval=True)
    executed=[]
    args={'x':1}
    async def approve(approval):
        svc.authz.resolve_approval(approval,'approve')
        if fault=='expired':
            svc.manager._conn.execute("UPDATE approval_request SET expires_at='2000-01-01T00:00:00Z' WHERE id=?",(approval,));svc.manager._conn.commit()
        if fault=='changed':args['x']=2
        if fault=='reused':
            svc.manager._conn.execute("UPDATE approval_request SET consumed_at='2026-10-10T00:00:00Z' WHERE id=?",(approval,));svc.manager._conn.commit()
        return True
    async def execute(*args):executed.append(args);return {}
    svc.invoker._await_approval=approve;svc.invoker._exec_tool_stdio=execute
    try:
        if fault=='none':
            asyncio.run(svc.invoker.handle_tools_call(channel,{'tool':'fixture/read','arguments':args}))
            assert len(executed)==1
            assert svc.manager._conn.execute('SELECT consumed_at FROM approval_request').fetchone()[0]
        else:
            with pytest.raises(RpcError):asyncio.run(svc.invoker.handle_tools_call(channel,{'tool':'fixture/read','arguments':args}))
            assert executed==[]
    finally:svc.manager.close()
