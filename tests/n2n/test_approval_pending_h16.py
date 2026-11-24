"""H16: an approval-gated n2n/tools/call is answered APPROVAL_PENDING (-32002)
at once, instead of being held open for the approval window while the caller
times out with -32006. The caller retries with the same request_id."""
import asyncio
from types import SimpleNamespace

import pytest

from bgp.federation import invocation
from bgp.federation.channel import FederationChannel, RpcError
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.service import FederationService

TOOL = 'fixture/read'


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr(invocation, '_security_mode', lambda: 'hobby')
    s = FederationService(local_as=65001, router_id='4.4.4.4', display_name='fixture',
                          manager=FederationManager(base_dir=str(tmp_path)))
    s.manager.local_consent(65007, '7.7.7.7')
    s.manager.remote_consent(65007, '7.7.7.7')
    s.notified = []
    s.notify_approval = lambda *a: s.notified.append(a)
    s.executed = []

    async def execute(*args):
        s.executed.append(args)
        return {'ok': True}

    async def never_wait(_):
        raise AssertionError('tools/call must not wait for an approval')

    s.invoker._exec_tool_stdio = execute
    s.invoker._await_approval = never_wait
    s.authz.grant(peer_identity(65007, '7.7.7.7'), 'tool', TOOL, requires_approval=True)
    yield s
    s.manager.close()


CHANNEL = SimpleNamespace(peer_identity=peer_identity(65007, '7.7.7.7'), attestation='possession')
PARAMS = {'tool': TOOL, 'arguments': {'x': 1}, 'request_id': 'req-1'}


def call(s, params=PARAMS):
    return asyncio.run(s.invoker.handle_tools_call(CHANNEL, dict(params)))


def approvals(s):
    return s.manager._conn.execute('SELECT id, status FROM approval_request').fetchall()


def test_first_call_returns_32002_immediately_with_retry_data(svc):
    with pytest.raises(RpcError) as e:
        call(svc)
    assert e.value.code == -32002
    assert e.value.data['request_id'] == 'req-1'
    assert e.value.data['expires_at']
    assert 'approval_id' not in e.value.data
    assert len(approvals(svc)) == 1 and len(svc.notified) == 1
    assert svc.executed == []


def test_retry_while_pending_does_not_create_another_approval(svc):
    for _ in range(3):
        with pytest.raises(RpcError) as e:
            call(svc)
        assert e.value.code == -32002
    assert len(approvals(svc)) == 1 and len(svc.notified) == 1
    assert svc.executed == []


def test_retry_after_approval_executes_once(svc):
    with pytest.raises(RpcError):
        call(svc)
    svc.authz.resolve_approval(approvals(svc)[0]['id'], 'approve')
    assert call(svc) == {'ok': True}
    assert len(svc.executed) == 1


def test_retry_after_denial_is_32003(svc):
    with pytest.raises(RpcError):
        call(svc)
    svc.authz.resolve_approval(approvals(svc)[0]['id'], 'deny')
    with pytest.raises(RpcError) as e:
        call(svc)
    assert e.value.code == -32003
    assert svc.executed == []


def test_error_data_is_on_the_wire():
    frame = FederationChannel._err(None, 7, -32002, 'pending', {'request_id': 'r'})
    assert frame['error'] == {'code': -32002, 'message': 'pending', 'data': {'request_id': 'r'}}
    assert 'data' not in FederationChannel._err(None, 7, -32001, 'no')['error']


def test_caller_records_approval_pending_not_denied(svc):
    async def refuse(method, params, timeout):
        raise RpcError(-32002, 'approval pending', {'request_id': params['request_id']})

    async def channel(_):
        return SimpleNamespace(call=refuse)

    svc.invoker._channel = channel
    with pytest.raises(RpcError) as e:
        asyncio.run(svc.invoker.invoke_remote_tool('peer-x', TOOL, {}, request_id='req-9'))
    assert e.value.code == -32002 and e.value.data == {'request_id': 'req-9'}
    outcomes = [r[0] for r in svc.manager._conn.execute(
        "SELECT outcome FROM remote_invocation_record WHERE request_id='req-9' ORDER BY id")]
    assert outcomes == ['pending', 'approval_pending']
    state = svc.manager._conn.execute(
        "SELECT state FROM outbound_intent WHERE request='req-9'").fetchone()[0]
    assert state == 'approval_pending'


def test_actual_caller_can_retry_pending_request_then_execute_once(svc, tmp_path):
    caller = FederationService(local_as=65008, router_id='8.8.8.8', display_name='caller',
                               manager=FederationManager(base_dir=str(tmp_path / 'caller')))
    sends = []

    async def transport(method, params, timeout):
        sends.append(dict(params))
        return await svc.invoker.handle_tools_call(CHANNEL, params)

    async def channel(_):
        return SimpleNamespace(call=transport)

    caller.invoker._channel = channel

    def invoke(**kwargs):
        return asyncio.run(caller.invoker.invoke_remote_tool(
            'callee', TOOL, {'x': 1}, request_id='original-request', **kwargs))

    try:
        for _ in range(2):
            with pytest.raises(RpcError) as pending:
                invoke()
            assert pending.value.code == -32002
        assert len(approvals(svc)) == len(svc.notified) == 1
        svc.authz.resolve_approval(approvals(svc)[0]['id'], 'approve')
        assert invoke()['result'] == {'ok': True}
        assert len(svc.executed) == 1
        with pytest.raises(ValueError, match='outbound_request_not_retryable'):
            invoke()
        assert len(sends) == 3 and len(svc.executed) == 1
    finally:
        caller.manager.close()


@pytest.mark.parametrize('fault', ['peer', 'arguments', 'target', 'outcome_unknown', 'dispatching', 'refused'])
def test_caller_retry_cannot_change_binding_or_reopen_nonpending_outcome(svc, fault):
    sends = []

    async def transport(method, params, timeout):
        sends.append(params)
        raise RpcError(-32002, 'pending', {'request_id':params['request_id']})

    async def channel(_):
        return SimpleNamespace(call=transport)

    svc.invoker._channel = channel
    def invoke(peer='callee', tool=TOOL, arguments=None):
        return asyncio.run(svc.invoker.invoke_remote_tool(
            peer, tool, arguments or {'x':1}, request_id='fixed-request'))

    with pytest.raises(RpcError):
        invoke()
    changed = {}
    if fault == 'peer': changed['peer'] = 'different-peer'
    elif fault == 'arguments': changed['arguments'] = {'x':2}
    elif fault == 'target': changed['tool'] = 'fixture/other'
    else: svc.tasks.settle_intent('fixed-request', fault)
    with pytest.raises(ValueError, match='outbound_request_not_retryable'):
        invoke(**changed)
    assert len(sends) == 1
    state = svc.manager._conn.execute(
        "SELECT state FROM outbound_intent WHERE request='fixed-request'").fetchone()[0]
    assert state == ('approval_pending' if changed else fault)
    assert svc.manager._conn.execute(
        "SELECT outcome FROM remote_invocation_record WHERE request_id='fixed-request' ORDER BY id DESC LIMIT 1"
    ).fetchone()[0] == 'denied'


def test_concurrent_pending_retries_dispatch_only_one(svc):
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        sends = []
        async def transport(method, params, timeout):
            sends.append(params)
            if len(sends) > 1:
                entered.set()
                await release.wait()
            raise RpcError(-32002, 'pending')
        async def channel(_): return SimpleNamespace(call=transport)
        svc.invoker._channel = channel
        async def invoke():
            return await svc.invoker.invoke_remote_tool('callee', TOOL, {}, request_id='concurrent')
        with pytest.raises(RpcError): await invoke()
        first = asyncio.create_task(invoke())
        await asyncio.wait_for(entered.wait(), 1)
        try:
            with pytest.raises(ValueError, match='outbound_request_not_retryable'):
                await invoke()
            assert len(sends) == 2
        finally:
            release.set()
            with pytest.raises(RpcError): await first
    asyncio.run(run())
