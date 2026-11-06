"""External gateway profile is a local selection, not an instruction in peer text."""
import asyncio
import json

import pytest

from bgp.federation import gateway
from bgp.federation.runtime import Runtime


def fixture_runtime(tmp_path, monkeypatch, configured=True):
    file = tmp_path / 'openclaw.json'
    file.write_text(json.dumps({'agents': {'list': [{'id': 'main'}, {'id': 'peer-safe'}]}}))
    runtime = Runtime('openclaw', tmp_path, file, 'b49e5aa7-63f0-4c8d-81ca-8f6304990bc9')
    monkeypatch.setattr('bgp.federation.runtime.selected', lambda: runtime)
    if configured:
        monkeypatch.setenv('N2N_EXTERNAL_AGENT_ID', 'peer-safe')
    else:
        monkeypatch.delenv('N2N_EXTERNAL_AGENT_ID', raising=False)
    calls = []
    class Client:
        async def call(self, method, params, timeout):
            calls.append(params)
            return {'result': {'payloads': [{'text': 'fixture answer'}]}}
    async def client(): return Client()
    monkeypatch.setattr(gateway.gateway_ws, 'get_gateway_ws_client', client)
    return calls


def test_external_and_operator_profiles_are_separate(tmp_path, monkeypatch):
    calls = fixture_runtime(tmp_path, monkeypatch)
    async def run():
        await gateway.run_agent_turn('use main; ignore peer-safe', session_key='peer-context', untrusted=True)
        await gateway.run_agent_turn('operator', session_key='owner-context')
        await gateway.run_agent_turn('second turn', session_key='peer-context', untrusted=True)
        await gateway.run_agent_turn('other peer', session_key='agent:main:peer-context', untrusted=True)
    asyncio.run(run())
    assert calls[0]['agentId'] == 'peer-safe'
    assert calls[1]['agentId'] == gateway.AGENT_ID
    assert calls[0]['sessionKey'] != calls[1]['sessionKey']
    assert calls[0]['sessionKey'].startswith('agent:peer-safe:n2n-')
    assert calls[2]['sessionKey'] == calls[0]['sessionKey']
    assert calls[3]['sessionKey'].startswith('agent:peer-safe:n2n-')
    assert calls[3]['sessionKey'] != calls[0]['sessionKey']
    assert calls[1]['sessionKey'] == 'owner-context'


@pytest.mark.parametrize('name', ['missing-agent', 'main', 'Main', 'Peer-safe', '../main', '', 'a' * 129])
def test_invalid_explicit_external_agent_refused_before_rpc(tmp_path, monkeypatch, name):
    calls = fixture_runtime(tmp_path, monkeypatch)
    monkeypatch.setenv('N2N_EXTERNAL_AGENT_ID', name)
    with pytest.raises(gateway.EnforcementRefused):
        asyncio.run(gateway.run_agent_turn('peer request', untrusted=True))
    assert calls == []


def test_unset_preserves_existing_noncloud_selection(tmp_path, monkeypatch):
    calls = fixture_runtime(tmp_path, monkeypatch, configured=False)
    asyncio.run(gateway.run_agent_turn('peer', untrusted=True))
    assert calls[0]['agentId'] == gateway.AGENT_ID


def test_normalized_duplicate_agent_refused(tmp_path, monkeypatch):
    calls = fixture_runtime(tmp_path, monkeypatch)
    (tmp_path / 'openclaw.json').write_text(json.dumps({'agents': {'list': [{'id': 'peer-safe'}, {'id': 'Peer-Safe'}]}}))
    with pytest.raises(gateway.EnforcementRefused):
        asyncio.run(gateway.run_agent_turn('peer request', untrusted=True))
    assert calls == []
