import asyncio
import pytest
from bgp.federation.audit import Auditor
from bgp.federation.tasks import TaskManager
from bgp.federation.execution import Refused,OutcomeUnknown


def test_duplicate_request_is_owned_and_body_bound(manager):
    tasks=TaskManager(manager,Auditor(manager))
    def create(peer='a',text='input'):
        return tasks.create(direction='inbound',peer_identity=peer,target_type='skill',target_name='subnet-calculator',input_text=text,client_request='request')
    one=create()
    assert create()==one
    assert create('b')!=one
    with pytest.raises(Refused):create(text='changed')


def test_cancel_after_dispatch_is_uncertain_and_restart_does_not_replay(manager):
    tasks=TaskManager(manager,Auditor(manager))
    task=tasks.create(direction='inbound',peer_identity='a',target_type='skill',target_name='subnet-calculator')
    async def run():
        started=asyncio.Event()
        async def worker(progress):
            tasks.mark_dispatch(task)
            started.set()
            await asyncio.Event().wait()
        work=tasks.run(task,worker)
        await started.wait()
        assert tasks.cancel(task,owner='other') is False
        assert tasks.cancel(task,owner='a') is True
        await asyncio.gather(work,return_exceptions=True)
        assert tasks.status(task)['state']=='outcome_unknown'
        assert tasks.run(task,worker) is None
    asyncio.run(run())
    restarted=TaskManager(manager,Auditor(manager));restarted.recover()
    assert restarted.result(task,owner='a')['state']=='outcome_unknown'
    assert restarted.result(task,owner='other')['state']=='unknown'


def test_unknown_usage_and_foreign_remote_id_never_overwrite(manager):
    tasks=TaskManager(manager,Auditor(manager))
    task=tasks.create(direction='inbound',peer_identity='a',target_type='skill',target_name='subnet-calculator')
    async def worker(progress):return 'actual reply',None
    async def run():await tasks.run(task,worker)
    asyncio.run(run())
    assert tasks.result(task)['tokens_used'] is None
    assert tasks.result(task)['usage_available'] is False
    with pytest.raises(OutcomeUnknown):tasks.record_outbound(task,'b','skill','subnet-calculator')
    assert tasks.result(task,owner='a')['output_text']=='actual reply'


def test_queued_cancel_is_confirmed_without_dispatch(manager):
    tasks=TaskManager(manager,Auditor(manager))
    task=tasks.create(direction='inbound',peer_identity='a',target_type='skill',target_name='subnet-calculator')
    async def run():
        async def forbidden(progress):raise AssertionError('cancelled queue must not execute')
        work=tasks.run(task,forbidden)
        assert tasks.cancel(task,owner='a')
        await asyncio.gather(work,return_exceptions=True)
        assert tasks.status(task)['state']=='cancelled'
        assert not tasks.dispatched(task)
    asyncio.run(run())
