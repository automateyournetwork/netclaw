"""Attribution requires native run/tool events AND the local outbound receipt."""
import asyncio
import json

import pytest

from bgp.federation.external_provenance import ExternalProvenance
from bgp.federation.gateway_ws import GatewayWsClient
from bgp.federation.tasks import TaskManager
from test_internal_transport import _service


def evidence(svc):
    parent = svc.tasks.create(direction='inbound', peer_identity='device', target_type='edge_ask', target_name='ask')
    svc.tasks.outbound_intent('peer-a', 'n2n/tools/call', {'request_id': 'request-a'})
    svc.tasks.settle_intent('request-a', 'completed')
    collector = ExternalProvenance(svc.tasks, parent, 'native-run')
    start = {'runId': 'native-run', 'seq': 1, 'stream': 'tool', 'data': {
        'phase': 'start', 'name': 'n2n-mcp__n2n_invoke', 'toolCallId': 'call-a', 'args': {'peer': 'peer-a'}}}
    value = {'source': 'peer-a', 'trust': 'remote-untrusted', 'request_id': 'request-a', 'result': {'text': 'not retained'}}
    result = {'runId': 'native-run', 'seq': 3, 'stream': 'tool', 'data': {
        'phase': 'result', 'name': 'n2n-mcp__n2n_invoke', 'toolCallId': 'call-a', 'result': {
            'content': [{'type': 'text', 'text': json.dumps(value)}],
            'details': {'mcpServer': 'n2n-mcp', 'mcpTool': 'n2n_invoke'}}}}
    return parent, collector, start, result


@pytest.mark.parametrize('shape', ['text', 'structured', 'wrapped'])
def test_native_provenance_persists_and_remains_owned(tmp_path, shape):
    svc = _service(tmp_path, 65001, '192.0.2.1', 'provenance')
    try:
        parent, collector, start, result = evidence(svc)
        if shape != 'text':
            native = result['data']['result']
            text = native['content'][0]['text']
            native['details']['structuredContent'] = {'result': text} if shape == 'wrapped' else json.loads(text)
            native['content'][0]['text'] = 'structuredContent:\n' + json.dumps(native['details']['structuredContent'])
        collector.event(start)
        collector.event({'runId': 'native-run', 'seq': 2, 'stream': 'assistant', 'data': {'text': 'claimed peer-b'}})
        collector.event(result)
        collector.event(result)  # replay cannot duplicate source records
        expected = [{'peer': 'peer-a', 'kind': 'tool', 'request_id': 'request-a', 'task_id': None, 'trust': 'remote-untrusted'}]
        assert svc.tasks.result(parent, owner='device')['external_sources'] == expected
        assert 'external_sources' not in svc.tasks.result(parent, owner='different-device')
        recovered = TaskManager(svc.manager, svc.audit)
        assert recovered.status(parent, owner='device')['external_sources'] == expected
        assert 'not retained' not in json.dumps(recovered.external_sources(parent))
    finally:
        svc.manager.close()


@pytest.mark.parametrize('fault', ['no_start', 'wrong_run', 'wrong_stream', 'wrong_name', 'wrong_details', 'unreceipted', 'wrong_peer', 'error', 'reordered', 'not_json'])
def test_unproven_native_source_is_omitted(tmp_path, fault):
    svc = _service(tmp_path, 65001, '192.0.2.1', 'provenance')
    try:
        parent, collector, start, result = evidence(svc)
        if fault != 'no_start': collector.event(start)
        if fault == 'wrong_run': result['runId'] = 'another-run'
        if fault == 'wrong_stream': result['stream'] = 'assistant'
        if fault == 'wrong_name': result['data']['name'] = 'fake__n2n_invoke'
        if fault == 'wrong_details': result['data']['result']['details']['mcpServer'] = 'fake'
        if fault == 'unreceipted': result['data']['result']['content'][0]['text'] = result['data']['result']['content'][0]['text'].replace('request-a', 'invented')
        if fault == 'wrong_peer': result['data']['result']['content'][0]['text'] = result['data']['result']['content'][0]['text'].replace('peer-a', 'peer-b')
        if fault == 'error': result['data']['isError'] = True
        if fault == 'reordered': result['seq'] = 1
        if fault == 'not_json': result['data']['result']['content'][0]['text'] = 'model says peer-a'
        collector.event(result)
        assert svc.tasks.external_sources(parent) == []
    finally:
        svc.manager.close()


def test_gateway_routes_native_events_only_to_bound_run():
    async def run():
        client = GatewayWsClient('ws://unused.invalid', 'fixture')
        seen = []
        remove = client.watch_run('original', seen.append)
        async def frames():
            for run in ('other', 'original'):
                yield json.dumps({'type': 'event', 'event': 'agent', 'payload': {'runId': run, 'seq': 1}})
        client._ws = frames()
        await client._read_loop()
        remove()
        assert seen == [{'runId': 'original', 'seq': 1}]
        assert client._run_observers == {}
    asyncio.run(run())


def test_retention_removes_source_with_parent_but_preserves_live_source(tmp_path):
    svc = _service(tmp_path, 65001, '192.0.2.1', 'retention')
    try:
        parent, collector, start, result = evidence(svc)
        collector.event(start)
        collector.event(result)
        assert svc.tasks.sweep() == 0
        assert svc.tasks.external_sources(parent)
        svc.tasks._set(parent, state='completed', retention_until='2000-01-01T00:00:00Z')
        assert svc.tasks.sweep() == 1
        assert svc.tasks.external_sources(parent) == []
    finally:
        svc.manager.close()
