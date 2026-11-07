"""Delays inside production callbacks must not release an old admission."""
import asyncio
import time

import pytest

from bgp.federation.ha.config import HAError
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

