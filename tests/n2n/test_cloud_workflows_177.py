"""Six-direction wire workflows: native subnet MCP; deterministic model fixture."""
import asyncio
import importlib.util
import json
import sys
import uuid
from types import SimpleNamespace

import pytest

from bgp.federation.runtime import Runtime, ROOT
from test_cloud_triangle_177 import triangle, connect_triangle


def prepare_runtime(svc):
    home = svc.manager.base_dir
    # Apply the installer's hash-checked external MCP migration to a private
    # test copy, preserving the repository's vendor checkout and owner homes.
    spec = importlib.util.spec_from_file_location('patch177', ROOT / 'scripts/apply-fastmcp-patches.py')
    patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patcher)
    manifest = json.loads((ROOT / 'config/fastmcp-external-patches.json').read_text())
    changes = patcher.prepare(ROOT, 'subnet-calc', manifest)
    script = home / 'subnetcalculator_mcp.py'
    script.write_text(changes[0][2] if changes else (ROOT / 'mcp-servers/subnet-calculator-mcp/servers/subnetcalculator_mcp.py').read_text())
    config = home / 'openclaw.json'
    config.write_text(json.dumps({'mcp': {'servers': {'subnet-calc-mcp': {
        'command': 'python3', 'args': ['-u', 'scripts/component-launch.py', 'subnet-calc', '--server', 'subnet-calc-mcp'],
        'tools': ['subnet_calculator'], 'env': {'SUBNET_MCP_SCRIPT': str(script)}}}}}))
    records = home / 'python-runtimes/records'
    records.mkdir(parents=True)
    (records / 'subnet-calc').write_text(sys.executable)
    svc.runtime = Runtime('openclaw', home, config, str(uuid.uuid4()))
    svc.inventory.runtime = svc.runtime
    svc.inventory.config_path = config
    svc.inventory.skills_dir = home / 'workspace/skills'
    svc.inventory.env_path = home / '.env'
    skill = svc.inventory.skills_dir / 'subnet-calculator'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: subnet-calculator\ndescription: Calculate a subnet.\n---\nUse subnet calculator.')
    contexts, executions = {}, []
    async def model(text, session_key='unused'):
        turns = contexts.setdefault(session_key, [])
        turns.append(text)
        return '|'.join(turns), 1
    async def skill_model(skill, input_text, **kwargs):
        executions.append(input_text)
        return f'{svc.local_identity}: {input_text}', 1
    svc.chat._ask_gateway = model
    svc.invoker._exec_skill_gateway = skill_model
    return contexts, executions


def test_six_direction_inventory_chat_native_tool_and_async_skill(tmp_path, monkeypatch):
    monkeypatch.setattr('bgp.federation.invocation._security_mode', lambda: 'hobby')
    asyncio.run(check_workflows(tmp_path))


async def check_workflows(tmp_path):
    async with triangle(tmp_path) as (services, entries, registries):
        trackers = [prepare_runtime(svc) for svc in services]
        await connect_triangle(services)
        sessions = set()
        for source in services:
            for destination in services:
                if source is destination:
                    continue
                ident = destination.local_identity
                inventory = await source.channels[ident].call('n2n/inventory_get', {}, timeout=2)
                assert any(s['name'] == 'subnet-calculator' for s in inventory['skills'])
                assert inventory['mcp_servers'][0]['tools'] == ['subnet_calculator']
                destination.manager.set_chat_enabled(source.local_identity, True)
                first = await source.chat.open_and_send(ident, f'context {source.local_identity}')
                second = await source.chat.open_and_send(ident, 'continue', first['session_id'])
                assert second['source'] == ident and second['trust'] == 'remote-untrusted'
                assert second['text'] == f'context {source.local_identity}|continue'
                sessions.add(first['session_id'])
                destination.authz.grant(source.local_identity, 'tool', 'subnet-calc-mcp/subnet_calculator')
                result = await source.invoker.invoke_remote_tool(ident, 'subnet-calc-mcp/subnet_calculator', {'cidr': '192.0.2.0/26'})
                assert result['source'] == ident and not result['result'].get('isError')
                payload = json.loads(result['result']['content'][0]['text'])
                assert payload['network_address'] == '192.0.2.0' and payload['prefix_length'] == 26
                destination.authz.grant(source.local_identity, 'skill', 'subnet-calculator')
                submitted = await source.invoker.submit_remote_skill(ident, 'subnet-calculator', source.local_identity)
                task = submitted['task_id']
                worker = destination.tasks._workers.get(task)
                if worker:
                    await worker
                result = await source.invoker.poll_remote_task(ident, task, 'result')
                assert result['state'] == 'completed' and result['output_text'] == f'{ident}: {source.local_identity}'
                other = next(s for s in services if s is not source and s is not destination)
                assert (await source.invoker.poll_remote_task(other.local_identity, task, 'result'))['state'] == 'unknown'
                channel = source.channels.pop(ident)
                try:
                    cached = await source.invoker.poll_remote_task(ident, task, 'result')
                    assert cached['source'] == ident and cached['trust'] == 'remote-untrusted'
                    assert cached['output_text'] == result['output_text'] and cached['tokens_used'] == 1
                finally:
                    source.channels[ident] = channel
        assert len(sessions) == 6
        for contexts, executions in trackers:
            assert len(contexts) == 2 and all(len(turns) == 2 for turns in contexts.values())
            assert len(executions) == 2


@pytest.mark.parametrize('dispatched', [False, True])
def test_original_task_gateway_failure_is_not_replayed(tmp_path, monkeypatch, dispatched):
    from bgp.federation import gateway
    from test_internal_transport import _service
    svc = _service(tmp_path / 'task', 65001, '192.0.2.1', 'recovery')
    calls = []
    class Client:
        async def call(self, *args):
            calls.append(args)
            raise ConnectionError('response lost after gateway dispatch')
    async def client():
        if not dispatched:
            raise ConnectionError('gateway unavailable before dispatch')
        return Client()
    monkeypatch.setattr(gateway.gateway_ws, 'get_gateway_ws_client', client)
    async def run():
        task = svc.tasks.create(direction='inbound', peer_identity='owner', target_type='edge_ask', target_name='ask', client_request='original')
        async def work(progress):
            return await gateway.run_agent_turn('fixture')
        await svc.tasks.run(task, work)
        result = svc.tasks.result(task)
        assert result['state'] == ('outcome_unknown' if dispatched else 'failed')
        assert len(calls) == int(dispatched)
        assert svc.tasks.create(direction='inbound', peer_identity='owner', target_type='edge_ask', target_name='ask', client_request='original') == task
        assert svc.tasks.run(task, work) is None
        svc.tasks.recover()
        assert svc.tasks.result(task)['state'] == result['state']
        assert len(calls) == int(dispatched)
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()


def test_remote_task_cannot_spoof_source_or_read_other_cached_owner(tmp_path):
    from test_internal_transport import _service
    svc = _service(tmp_path / 'source', 65001, '192.0.2.1', 'source')
    svc.tasks.record_outbound('remote-task', 'peer-a', 'skill', 'subnet-calculator')
    async def call(*args, **kwargs):
        return {'task_id': 'remote-task', 'state': 'completed', 'source': 'peer-b', 'trust': 'local', 'output_text': 'untrusted result'}
    svc.channels['peer-a'] = SimpleNamespace(call=call)
    async def run():
        result = await svc.invoker.poll_remote_task('peer-a', 'remote-task', 'result')
        assert result['source'] == 'peer-a' and result['trust'] == 'remote-untrusted'
        svc.channels.clear()
        assert (await svc.invoker.poll_remote_task('peer-b', 'remote-task', 'result'))['state'] == 'unknown'
        assert (await svc.invoker.poll_remote_task('peer-a', 'remote-task', 'result'))['source'] == 'peer-a'
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()
