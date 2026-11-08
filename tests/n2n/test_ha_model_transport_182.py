"""Spec 182 hosted-model protected profile: controlled in-process fixtures only.

Never contacts Anthropic, Docker, DefenseClaw or any network beyond loopback test servers.
No REAL label: these tests prove source behaviour, not hosted-guard qualification.
"""
import asyncio
import copy
import json
import time
from types import SimpleNamespace

import pytest

from bgp.federation import protected_hosted as hosted
from bgp.federation.ha.config import HAError
from bgp.federation.ha.effect import CURRENT, EffectScope
from bgp.federation.protected_runtime import RuntimeRefused, RuntimeUnknown

GOOD = {'schema_version': 1, 'provider': 'anthropic', 'model': 'claude-sonnet-5-5',
        'egress_host': 'api.anthropic.com', 'max_output_tokens': 1024,
        'call_timeout_seconds': 60, 'task_timeout_seconds': 180}


def bad(**changes):
    value = copy.deepcopy(GOOD)
    for key, new in changes.items():
        if new is hosted_missing:
            del value[key]
        else:
            value[key] = new
    return value


hosted_missing = object()


# ---- profile validation -------------------------------------------------

def test_valid_profile_and_stable_binding():
    hosted.validate_profile(GOOD)
    assert hosted.profile_id(GOOD) == 'hosted-anthropic-claude-sonnet-5-5'
    first, second = hosted.profile_binding(GOOD), hosted.profile_binding(copy.deepcopy(GOOD))
    assert first == second and first['schema'] == 'netclaw.hosted-profile.v1'
    assert first['limits']['max_inference_calls'] == 2 and first['limits']['max_tool_calls'] == 1
    assert hosted.digest(first) == hosted.digest(second)


@pytest.mark.parametrize('value', [
    bad(model='claude-sonnet-4-6'), bad(model='claude-opus-5-5'), bad(provider='openai'),
    bad(egress_host='example.com'), bad(egress_host='api.anthropic.com.evil.test'),
    bad(max_output_tokens=0), bad(max_output_tokens=100000), bad(max_output_tokens=True),
    bad(call_timeout_seconds=0), bad(call_timeout_seconds=121), bad(call_timeout_seconds='60'),
    bad(task_timeout_seconds=181), bad(task_timeout_seconds=0), bad(schema_version=2),
    bad(model=hosted_missing), bad(extra='x'), None, [], 'text'])
def test_invalid_profiles_refused(value):
    with pytest.raises(hosted.HostedRefused):
        hosted.validate_profile(value)


@pytest.mark.parametrize('field', ['api_key', 'token', 'secret', 'authorization', 'anthropic_api_key'])
def test_credential_fields_are_never_accepted(field):
    with pytest.raises(hosted.HostedRefused) as caught:
        hosted.validate_profile(dict(GOOD, **{field: 'value'}))
    assert 'value' not in str(caught.value)


@pytest.mark.parametrize('secret', ['sk-ant-api03-abcdefghijklmnop', 'sk-abcdefghijklmnopqrst'])
def test_credential_looking_values_are_refused_without_echo(secret):
    with pytest.raises(hosted.HostedRefused) as caught:
        hosted.validate_profile(dict(GOOD, egress_host=secret))
    assert secret not in str(caught.value) and secret not in repr(caught.value)


def test_limits_cap_and_parity_with_ollama_shape():
    limits = hosted.limits(GOOD)
    assert limits['max_inference_calls'] == 2 and limits['max_tool_calls'] == 1
    assert limits['call_timeout_seconds'] == 60 and limits['task_timeout_seconds'] == 180
    assert limits['model'] == 'claude-sonnet-5-5'


# ---- runtime field / binding wiring --------------------------------------

def runtime(**extra):
    from bgp.federation import protected_docker as docker
    value = {key: None for key in docker._MCP_RUNTIME_FIELDS}
    value.update(relay_transport='unix', mcp={'kind': 'subnet_summary'}, **extra)
    return value


def test_runtime_fields_accept_hosted_and_refuse_ambiguous_runtimes(monkeypatch):
    from bgp.federation import protected_docker as docker
    monkeypatch.setattr(docker, 'validate_mcp_binding', lambda *a, **k: None)
    assert docker.validate_runtime_fields(runtime(hosted=GOOD)) == 'mcp'
    with pytest.raises(RuntimeRefused, match='runtime_configuration_fields_refused'):
        docker.validate_runtime_fields(runtime(hosted=GOOD, ollama={'x': 1}))
    with pytest.raises(RuntimeRefused):
        docker.validate_runtime_fields(runtime(hosted=dict(GOOD, model='other')))
    with pytest.raises(RuntimeRefused, match='hosted_native_summary_required'):
        docker.validate_runtime_fields(dict(runtime(hosted=GOOD), mcp={'kind': 'pyats'}))


def test_hosted_operation_limits_enforced(monkeypatch):
    from bgp.federation import protected_docker as docker
    monkeypatch.setattr(docker, 'validate_catalog_bindings', lambda *a, **k: {})
    now = int(time.time() * 1000)
    ok = {'issued_at_ms': now, 'limits': {'expires_at_ms': now + 120000, 'inference_timeout_ms': 60000,
                                          'max_inference_calls': 2, 'max_tool_calls': 1}}
    assert docker.validate_execution_bindings({'hosted': GOOD}, ok) == {}
    for key, value in (('expires_at_ms', now + 181000), ('inference_timeout_ms', 61000),
                       ('max_inference_calls', 3), ('max_tool_calls', 2)):
        changed = copy.deepcopy(ok); changed['limits'][key] = value
        with pytest.raises(RuntimeRefused, match='hosted_operation_limits_changed'):
            docker.validate_execution_bindings({'hosted': GOOD}, changed)


def test_profile_revision_pins_hosted_model_and_binding(monkeypatch):
    from bgp.federation import protected_docker as docker
    monkeypatch.setattr(docker, 'validate_runtime_fields', lambda config: 'mcp')
    monkeypatch.setattr(docker, '_image', lambda value: value)
    monkeypatch.setattr(docker, 'guard_policy_digest', lambda guard: 'g' * 64)
    monkeypatch.setattr(docker, '_native_identity', lambda value: {'resolved_path': '/d'})
    monkeypatch.setattr(docker, '_docker_host', lambda value: value)
    base = {'model_profile': {'provider': 'anthropic', 'model': 'claude-sonnet-5-5', 'runtime_kind': 'openclaw',
                              'runtime_version': docker._QUALIFIED_HARNESSES['openclaw'],
                              'profile_id': hosted.profile_id(GOOD)},
            'hosted': GOOD, 'agent_image': 'a', 'relay_image': 'r', 'guard': {}, 'docker': {},
            'docker_host': 'h', 'sandbox_address_pool': '198.18.0.0/24', 'mcp': {}, 'relay_transport': 'unix'}
    first = docker.runtime_profile_revision(base)
    assert first == docker.runtime_profile_revision(copy.deepcopy(base))
    wrong = copy.deepcopy(base); wrong['model_profile']['model'] = 'claude-sonnet-4-6'
    with pytest.raises(RuntimeRefused, match='unqualified_hosted_execution_profile'):
        docker.runtime_profile_revision(wrong)
    changed = copy.deepcopy(base); changed['hosted']['max_output_tokens'] = 512
    assert docker.runtime_profile_revision(changed) != first


@pytest.mark.asyncio
async def test_docker_entry_still_refuses_without_any_ha_runtime():
    from bgp.federation.protected_docker import DockerExecutor
    from test_ha_execution_contract_179 import ha_approval
    _, _, payload = ha_approval()
    executor = DockerExecutor.__new__(DockerExecutor)
    executor.ollama = None
    with pytest.raises(RuntimeRefused, match='ha_runtime_unqualified'):
        await executor.run(payload, lambda _: None, ha_admission=lambda *args: None)


@pytest.mark.asyncio
async def test_docker_entry_passes_ha_gate_for_hosted_runtime():
    from bgp.federation.protected_docker import DockerExecutor
    from test_ha_execution_contract_179 import ha_approval
    _, _, payload = ha_approval()
    executor = DockerExecutor.__new__(DockerExecutor)
    executor.ollama, executor.hosted = None, GOOD
    with pytest.raises(Exception) as caught:
        await executor.run(payload, lambda _: None, ha_admission=lambda *args: None)
    assert 'ha_runtime_unqualified' not in str(caught.value)


@pytest.mark.asyncio
async def test_member_accepts_hosted_executor_when_importable():
    pytest.importorskip('service_identity')
    from bgp.federation.ha.member import ClusterMemberOperations
    from bgp.federation.protected_docker import DockerExecutor
    member = ClusterMemberOperations.__new__(ClusterMemberOperations)
    member.executor = DockerExecutor.__new__(DockerExecutor)
    member.executor.ollama, member.executor.hosted = None, GOOD
    assert (await member._authorize_native(None, {}))['ha_admission_required'] is True
    member.executor.hosted = None
    with pytest.raises(HAError, match='ha_runtime_unqualified'):
        await member._authorize_native(None, {})


@pytest.mark.asyncio
async def test_forward_routes_cluster_payload_to_hosted_transport(monkeypatch):
    from bgp.federation import protected_docker as docker
    from bgp.federation.ha import hosted_model_transport as transport
    calls = []

    async def fake(executor, payload, request, guard_url):
        calls.append((payload, request, guard_url))
        return b'{"ok":true}'
    monkeypatch.setattr(transport, 'ha_hosted_model_forward', fake)
    monkeypatch.setattr(docker, 'validate_execution_bindings', lambda *a: {})
    executor = docker.DockerExecutor.__new__(docker.DockerExecutor)
    executor.ollama, executor.hosted, executor.config = None, GOOD, {}
    executor.guards = {'op': 'http://127.0.0.1:4999'}
    payload = {'operation_id': 'op', 'cluster': {}, 'limits': {'inference_timeout_ms': 1000}}
    assert await executor.forward(payload, {'a': 1}) == {'ok': True}
    assert calls == [(payload, {'a': 1}, 'http://127.0.0.1:4999')]


# ---- transport -----------------------------------------------------------

class Guard:
    def __init__(self, mode='ok'):
        self.mode, self.seen, self.connections, self.server = mode, [], 0, None

    async def handle(self, reader, writer):
        self.connections += 1
        try:
            header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 2)
            size = int(next(line.split(b':', 1)[1] for line in header.split(b'\r\n')
                            if line.lower().startswith(b'content-length:')))
            body = await asyncio.wait_for(reader.readexactly(size), 2)
            self.seen.append((header, json.loads(body)))
            if self.mode == 'hang':
                await asyncio.sleep(5)
            elif self.mode == 'status':
                writer.write(b'HTTP/1.1 500 X\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}')
            elif self.mode == 'redirect':
                writer.write(b'HTTP/1.1 302 X\r\nLocation: http://127.0.0.1:1/\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            elif self.mode == 'oversize':
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: 2000000\r\nConnection: close\r\n\r\n' + b'x' * 2000000)
            elif self.mode == 'badjson':
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: 4\r\nConnection: close\r\n\r\nnope')
            elif self.mode == 'chunked':
                body = b'{"id":"c","choices":[]}'
                writer.write(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n'
                             + hex(len(body))[2:].encode() + b'\r\n' + body + b'\r\n0\r\n\r\n')
            elif self.mode == 'reset':
                writer.transport.abort(); return
            else:
                body = b'{"id":"x","choices":[]}'
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode()
                             + b'\r\nConnection: close\r\n\r\n' + body)
            await writer.drain()
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            writer.close()

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle, '127.0.0.1', 0)
        self.url = 'http://127.0.0.1:%d' % self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        self.server.close(); await self.server.wait_closed()


def executor():
    return SimpleNamespace(hosted=GOOD, guard_token='fake-capability', ollama=None)


def payload(ms=5000, inference_ms=1000):
    return {'limits': {'expires_at_ms': int(time.time() * 1000) + ms, 'inference_timeout_ms': inference_ms}}


async def forward(guard_url, remaining=3000, **kw):
    from bgp.federation.ha.hosted_model_transport import ha_hosted_model_forward
    scope = EffectScope('model', lambda: remaining)
    token = CURRENT.set(scope)
    try:
        return scope, await ha_hosted_model_forward(kw.pop('executor', executor()), kw.pop('payload', payload()),
                                                    kw.pop('request', {'messages': ['hi']}), guard_url)
    finally:
        CURRENT.reset(token)


@pytest.mark.asyncio
async def test_single_guarded_request_with_capability_only():
    async with Guard() as guard:
        scope, raw = await forward(guard.url)
    assert json.loads(raw)['id'] == 'x' and scope.handed_off and guard.connections == 1
    header, body = guard.seen[0]
    assert body == {'messages': ['hi']}
    lowered = header.lower()
    assert b'x-dc-auth: fake-capability' in lowered and b'/v1/chat/completions' in lowered
    for forbidden in (b'x-api-key', b'authorization', b'anthropic-version', b'x-dc-target-url'):
        assert forbidden not in lowered


@pytest.mark.asyncio
async def test_chunked_guard_response_is_decoded():
    async with Guard('chunked') as guard:
        _, raw = await forward(guard.url)
    assert json.loads(raw)['id'] == 'c' and guard.connections == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['status', 'redirect', 'oversize', 'badjson', 'reset', 'hang'])
async def test_every_post_handoff_failure_is_unknown_and_never_retried(mode):
    async with Guard(mode) as guard:
        started = time.monotonic()
        with pytest.raises(RuntimeUnknown, match='model_handoff_unknown') as caught:
            await forward(guard.url, payload=payload(inference_ms=300))
        assert time.monotonic() - started < 2
    assert guard.connections == 1
    assert 'fake-capability' not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('remaining', [250, 100, 0])
async def test_stale_or_low_budget_refuses_before_connecting(remaining):
    async with Guard() as guard:
        with pytest.raises(HAError, match='admission_expired'):
            await forward(guard.url, remaining=remaining)
    assert guard.connections == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('url', ['http://example.com:4000', 'https://127.0.0.1:4000', 'http://127.0.0.1',
                                 'http://127.0.0.1:4000/x', 'http://localhost:4000',
                                 'docker-exec://x/127.0.0.1:4000', ''])
async def test_guard_url_must_be_exact_loopback_http(url):
    with pytest.raises((HAError, RuntimeRefused)):
        await forward(url)


@pytest.mark.asyncio
async def test_requires_live_scope_and_hosted_profile():
    from bgp.federation.ha.hosted_model_transport import ha_hosted_model_forward
    with pytest.raises(HAError, match='ha_runtime_unqualified'):
        await ha_hosted_model_forward(executor(), payload(), {}, 'http://127.0.0.1:4000')
    async with Guard() as guard:
        with pytest.raises(HAError, match='ha_runtime_unqualified'):
            await forward(guard.url, executor=SimpleNamespace(hosted=None, guard_token='t', ollama=None))
        assert guard.connections == 0


@pytest.mark.asyncio
async def test_expired_operation_and_bad_token_refuse_before_connecting():
    async with Guard() as guard:
        with pytest.raises((HAError, RuntimeRefused)):
            await forward(guard.url, payload=payload(ms=-1000))
        with pytest.raises((HAError, RuntimeRefused)):
            await forward(guard.url, executor=SimpleNamespace(hosted=GOOD, guard_token='bad token\n', ollama=None))
    assert guard.connections == 0


@pytest.mark.asyncio
async def test_request_size_bound():
    async with Guard() as guard:
        with pytest.raises(HAError, match='model_request_bound'):
            await forward(guard.url, request={'messages': ['x' * 20000]})
    assert guard.connections == 0


def test_independent_counter_counts_only_guard_chat_posts():
    from bgp.federation.ha.hosted_model_transport import count_guard_requests
    log = '\n'.join(['POST /v1/chat/completions 200', 'GET /health 200', 'POST /v1/chat/completions 500',
                     'POST /v1/other 200', 'post /v1/chat/completions 200', '']).encode()
    assert count_guard_requests(log) == 2
    assert count_guard_requests(b'') == 0
    assert count_guard_requests('POST /v1/chat/completions 200') == 1
