"""Triangle refusals must have zero local tool/model effects."""
import asyncio

import pytest

from bgp.federation.channel import RpcError
from test_cloud_triangle_177 import triangle, connect_triangle
from test_cloud_workflows_177 import prepare_runtime


@pytest.mark.parametrize('fault', ['no_grant', 'revoked', 'wrong_scope', 'budget', 'approval'])
def test_triangle_tool_refusals_have_zero_effects(tmp_path, monkeypatch, fault):
    monkeypatch.setattr('bgp.federation.invocation._security_mode', lambda: 'hobby')
    async def run():
        async with triangle(tmp_path) as (services, entries, registries):
            effects = []
            for svc in services:
                prepare_runtime(svc)
                async def execute(*args):
                    effects.append(args)
                    return {}
                async def refuse(_): return False
                svc.invoker._exec_tool_stdio = execute
                svc.invoker._await_approval = refuse
                if fault == 'budget': svc.authz.daily_requests = 0
            await connect_triangle(services)
            for source in services:
                for destination in services:
                    if source is destination: continue
                    if fault != 'no_grant':
                        grant = destination.authz.grant(source.local_identity, 'tool',
                            'other/tool' if fault == 'wrong_scope' else 'subnet-calc-mcp/subnet_calculator', requires_approval=fault == 'approval')
                        if fault == 'revoked': destination.authz.revoke(grant)
                    with pytest.raises(RpcError):
                        await source.invoker.invoke_remote_tool(destination.local_identity, 'subnet-calc-mcp/subnet_calculator', {'cidr': '192.0.2.0/26'})
            assert effects == []
    asyncio.run(run())


def test_chat_disabled_hidden_inventory_and_cross_peer_context(tmp_path):
    async def run():
        async with triangle(tmp_path) as (services, entries, registries):
            trackers = [prepare_runtime(svc) for svc in services]
            await connect_triangle(services)
            a, b, c = services
            assert 'not enabled' in (await a.chat.open_and_send(b.local_identity, 'denied'))['error']
            b.manager._conn.execute("INSERT INTO visibility_setting VALUES ('skill','subnet-calculator','hidden',NULL)")
            b.manager._conn.commit()
            inventory = await a.channels[b.local_identity].call('n2n/inventory_get', {}, timeout=2)
            assert inventory['skills'] == []
            b.manager.set_chat_enabled(a.local_identity, True)
            b.manager.set_chat_enabled(c.local_identity, True)
            opened = await a.chat.open_and_send(b.local_identity, 'owned context')
            with pytest.raises(RpcError):
                await c.channels[b.local_identity].call('n2n/chat/message', {'session_id': opened['session_id'], 'text': 'steal context'}, timeout=2)
            with pytest.raises(RpcError):
                await a.channels[b.local_identity].call('in2n/member/list', {}, timeout=2)
            assert len(trackers[1][0]) == 1
    asyncio.run(run())
