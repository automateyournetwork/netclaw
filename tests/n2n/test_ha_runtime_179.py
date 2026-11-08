"""Controlled callbacks at the actual guarded inference boundary; no REAL label."""
import pytest

from bgp.federation.protected_runtime import ScopedInference, InferenceFence, RuntimeRefused, RuntimeUnknown
from bgp.federation.ha.config import HAError
from test_ha_execution_contract_179 import ha_approval


def test_cluster_payload_requires_bound_guard_before_any_claim(tmp_path):
    _, _, payload = ha_approval()
    fence = InferenceFence(tmp_path / 'private' / 'inference.db')
    try:
        with pytest.raises(RuntimeRefused, match='ha_runtime_unqualified'):
            ScopedInference(payload, 'secret', fence, lambda _: None)
        assert fence.count(payload['operation_id']) == 0
    finally:
        fence.close()


@pytest.mark.asyncio
async def test_actual_docker_entry_refuses_missing_or_unqualified_ha_gate():
    from bgp.federation.protected_docker import DockerExecutor
    _, _, payload = ha_approval()
    executor = DockerExecutor.__new__(DockerExecutor)
    with pytest.raises(RuntimeRefused, match='ha_runtime_unqualified'):
        await executor.run(payload, lambda _: None)
    executor.ollama = None
    with pytest.raises(RuntimeRefused, match='ha_runtime_unqualified'):
        await executor.run(payload, lambda _: None, ha_admission=lambda *args: None)


@pytest.mark.asyncio
@pytest.mark.parametrize('quorum', [True, False])
async def test_each_model_forward_enters_fresh_admission(quorum, tmp_path):
    _, _, payload = ha_approval()
    fence = InferenceFence(tmp_path / 'private' / 'inference.db')
    effects, admissions = [], []
    finished = [False]
    async def forward(request):
        effects.append(request)
        return {'choices': []}
    async def admission(kind, ordinal, digest, invoke):
        admissions.append((kind, ordinal, digest))
        if not quorum: raise HAError('no_quorum', 503)
        return await invoke()
    facade = ScopedInference(payload, 'secret', fence, forward, tool_finished=lambda: finished[0],
                              clock_ms=lambda: payload['issued_at_ms'], ha_admission=admission)
    body = {'model': payload['model_profile']['model'], 'messages': []}
    try:
        if quorum:
            await facade.invoke('POST', '/v1/chat/completions', {'authorization': 'Bearer secret'}, body)
            finished[0] = True
            await facade.invoke('POST', '/v1/chat/completions', {'authorization': 'Bearer secret'},
                                dict(body, messages=[{'role': 'tool', 'content': 'controlled result'}]))
            assert [row[:2] for row in admissions] == [('model', 1), ('model', 2)]
            assert len(effects) == 2
        else:
            with pytest.raises(RuntimeUnknown):
                await facade.invoke('POST', '/v1/chat/completions', {'authorization': 'Bearer secret'}, body)
            assert len(admissions) == 1 and effects == []
    finally:
        fence.close()
