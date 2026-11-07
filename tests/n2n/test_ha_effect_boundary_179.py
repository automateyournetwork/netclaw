"""Delays inside production callbacks must not release an old admission."""
import asyncio
import time
from types import SimpleNamespace

import pytest

from bgp.federation.ha.config import HAError
from bgp.federation.protected_runtime import RuntimeUnknown
from test_ha_admission_179 import setup
from test_ha_execution_contract_179 import ha_approval


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['delay', 'clock'])
async def test_guard_inspection_delay_is_checked_before_provider_launch(tmp_path, monkeypatch, fault):
    from bgp.federation import protected_docker as d
    journal, _, _, context, clock, response = setup(tmp_path)
    _, _, payload = ha_approval()
    payload['limits']['expires_at_ms'] = int(time.time()*1000) + 60000
    executor = d.DockerExecutor.__new__(d.DockerExecutor)
    executor.config, executor.ollama = {}, {'guard_uid': 501, 'model_container_id': 'fixture'}
    executor.guards = {payload['operation_id']: 'http://fixture-guard'}
    calls = []
    monkeypatch.setattr(d, 'validate_execution_bindings', lambda *args: None)
    async def inspect():
        await asyncio.sleep(0)
        if fault == 'delay': clock.update(mono=14., wall=1004.)
        else: clock['wall'] += 1
        return {'guard_url': 'http://fixture-guard'}
    async def command(*args, **kwargs): calls.append(args)
    executor.inspect_model, executor.command = inspect, command
    async def send(request): return response(request)
    with pytest.raises(HAError, match='admission_expired|clock_uncertain'):
        await journal.run(context, 'model', 1, 'c'*64, send, lambda: executor.forward(payload, {}))
    assert calls == []


@pytest.mark.asyncio
async def test_docker_process_start_delay_does_not_write_provider_request(tmp_path, monkeypatch):
    from bgp.federation import protected_docker as d
    from bgp.federation.ha.effect import scope
    journal, _, _, context, clock, response = setup(tmp_path)
    executor = d.DockerExecutor.__new__(d.DockerExecutor)
    executor.docker_config = tmp_path/'docker'; executor.docker_config.mkdir()
    (executor.docker_config/'config.json').write_bytes(b'{}')
    executor.config, executor.docker_host, executor.docker = {'docker_host': 'fixture'}, 'fixture', '/fixture'
    writes = []
    process = SimpleNamespace(returncode=0, stdin=SimpleNamespace(write=writes.append))
    async def communicate(): return b'', b''
    process.communicate = communicate
    async def create(*args, **kwargs):
        await asyncio.sleep(0)
        clock.update(mono=14., wall=1004.)
        return process
    monkeypatch.setattr(d, '_docker_host', lambda value: value)
    monkeypatch.setattr(d.asyncio, 'create_subprocess_exec', create)
    async def send(request): return response(request)
    async def invoke():
        permit = scope('model')
        return await executor.command('exec', input_data=b'private-provider-request',
                                      before_input=lambda: permit.handoff('model'))
    with pytest.raises(RuntimeUnknown, match='docker_client_interrupted'):
        await journal.run(context, 'model', 1, 'c'*64, send, invoke)
    assert writes == []


