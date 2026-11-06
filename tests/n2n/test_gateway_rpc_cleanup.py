"""Offline response-deadline and cancellation bookkeeping regressions."""
import asyncio
import pytest
from bgp.federation.gateway_ws import GatewayWsClient


def test_lost_response_never_retries_agent_dispatch():
    async def run():
        client = GatewayWsClient('ws://unused.invalid', 'fixture-token')
        calls = []
        async def once(*args):
            calls.append(args)
            raise OSError('response lost')
        client._call_once = once
        with pytest.raises(OSError):
            await client.call('agent', {'idempotencyKey': 'original'}, 1)
        assert len(calls) == 1
    asyncio.run(run())


def test_clean_socket_close_wakes_pending_call_without_retry():
    async def run():
        from bgp.federation.gateway_ws import GatewayWsError
        client = GatewayWsClient('ws://unused.invalid', 'fixture-token')
        async def ended():
            if False:
                yield ''
        client._ws = ended()
        pending = asyncio.get_running_loop().create_future()
        client._pending['original'] = (pending, True)
        await client._read_loop()
        with pytest.raises(GatewayWsError):
            await pending
        assert client._pending == {}
    asyncio.run(run())


def test_pending_call_removed_on_cancellation_and_send_failure():
    async def run(fail_send):
        client = GatewayWsClient('ws://unused.invalid', 'fixture-token')
        async def connected():
            pass
        class Socket:
            async def send(self, _frame):
                if fail_send:
                    raise RuntimeError('synthetic send failure')
        client._ensure_connected = connected
        client._ws = Socket()
        if fail_send:
            with pytest.raises(RuntimeError, match='synthetic'):
                await client._call_once('agent', {}, None, True)
        else:
            task = asyncio.create_task(client._call_once('agent', {}, None, True))
            await asyncio.sleep(0)
            assert len(client._pending) == 1
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert client._pending == {}
    asyncio.run(run(False))
    asyncio.run(run(True))
