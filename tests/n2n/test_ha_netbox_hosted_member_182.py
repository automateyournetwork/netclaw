"""Spec 182 hosted + NetBox HA member: source-level fixtures only.

No Anthropic, NetBox, Docker or guard process; loopback test servers and temp files only. These prove the
rule relaxation and its negatives, the hosted freshness window and the independent counter reader. They do not
qualify the hosted guard path (see specs/182-multi-region-ha-borders/model-transport.md and netbox-member.md).
"""
import asyncio
import copy
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from bgp.federation import protected_contract as contract
from bgp.federation import protected_docker as docker
from bgp.federation import protected_hosted as hosted
from bgp.federation import protected_mcp as mcp
from bgp.federation.ha.config import HAError
from bgp.federation.protected_runtime import RuntimeRefused, canonical, sha

ORIGIN = 'https://demo.netbox.dev'
DEVICE = {'object_type': 'dcim.device', 'object_id': 27, 'fields': contract.NETBOX_FIELDS['dcim.device'], 'brief': False}
HOSTED = {'schema_version': 1, 'provider': 'anthropic', 'model': 'claude-sonnet-4-6', 'egress_host': 'api.anthropic.com',
          'max_output_tokens': 1024, 'call_timeout_seconds': 60, 'task_timeout_seconds': 180}


def h(label):
    return hashlib.sha256(label.encode()).hexdigest()


def netbox_binding(tmp_path, **changes):
    root = tmp_path.resolve()
    sources = {name: h(name) for name in ('src/netbox_mcp_server/server.py', 'src/netbox_mcp_server/netbox_client.py',
                                          'src/netbox_mcp_server/netclaw_http.py', 'src/netbox_mcp_server/netbox_types.py',
                                          'src/netbox_mcp_server/config.py')}
    value = {'kind': 'netbox', 'tool': 'netbox_get_object_by_id', 'python': str(root / 'venv/bin/python'),
             'python_manifest': str(root / 'm.json'), 'python_manifest_sha256': h('manifest'),
             'source_root': str(root / 'src-root'), 'source_sha256': sources, 'input_schema_sha256': h('schema'),
             'endpoint_sha256': sha({'kind': 'netbox', 'origin': ORIGIN}),
             'selection_sha256': sha({'tool': 'netbox_get_object_by_id', 'arguments': DEVICE}),
             'skill': {'path': str(root / 'netbox-reconcile/SKILL.md'), 'sha256': h('skill')},
             'origin': ORIGIN, 'credential_file': str(root / 'netbox-token')}
    value.update(changes)
    return value


def runtime(mcp_config, **extra):
    value = {key: None for key in docker._MCP_RUNTIME_FIELDS}
    value.update(relay_transport='tcp', mcp=mcp_config, **extra)
    return value


# ---- rule relaxation and its negatives -----------------------------------------------------------

def test_hosted_accepts_the_exact_reviewed_netbox_binding(tmp_path):
    assert docker.validate_runtime_fields(runtime(netbox_binding(tmp_path), hosted=HOSTED)) == 'mcp'


def test_hosted_still_accepts_the_native_summary_calculator(monkeypatch):
    monkeypatch.setattr(docker, 'validate_mcp_binding', lambda *a, **k: None)
    assert docker.validate_runtime_fields(runtime({'kind': 'subnet_summary'}, hosted=HOSTED)) == 'mcp'


@pytest.mark.parametrize('kind', ['subnet', 'pyats', 'cml', '', None, 'NETBOX', 'netbox '])
def test_hosted_refuses_every_other_mcp_kind(monkeypatch, kind):
    monkeypatch.setattr(docker, 'validate_mcp_binding', lambda *a, **k: None)
    with pytest.raises(RuntimeRefused, match='hosted_mcp_kind_refused'):
        docker.validate_runtime_fields(runtime({'kind': kind}, hosted=HOSTED))


def test_ollama_with_netbox_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(docker._ollama, 'validate_profile', lambda value: None)
    ollama = {'guard_uid': os.getuid()}
    with pytest.raises(RuntimeRefused, match='ollama_native_summary_required'):
        docker.validate_runtime_fields(runtime(netbox_binding(tmp_path), ollama=ollama))


def test_hosted_and_ollama_together_are_still_refused(monkeypatch, tmp_path):
    with pytest.raises(RuntimeRefused, match='runtime_configuration_fields_refused'):
        docker.validate_runtime_fields(runtime(netbox_binding(tmp_path), hosted=HOSTED, ollama={'x': 1}))


@pytest.mark.parametrize('origin', ['http://demo.netbox.dev', 'https://demo.netbox.dev/api', 'https://demo.netbox.dev:8443',
                                    'https://DEMO.netbox.dev', 'https://user@demo.netbox.dev', 'https://demo.netbox.dev?x=1', ''])
def test_wrong_netbox_origin_is_refused(tmp_path, origin):
    with pytest.raises(RuntimeRefused):
        docker.validate_runtime_fields(runtime(netbox_binding(tmp_path, origin=origin), hosted=HOSTED))


def test_netbox_endpoint_hash_must_match_the_origin(tmp_path):
    other = sha({'kind': 'netbox', 'origin': 'https://other.netbox.dev'})
    with pytest.raises(RuntimeRefused, match='mcp_endpoint_changed'):
        docker.validate_runtime_fields(runtime(netbox_binding(tmp_path, endpoint_sha256=other), hosted=HOSTED))


@pytest.mark.parametrize('change', [{'tool': 'netbox_get_objects'}, {'kind': 'netbox2'}, {'extra': 'x'}])
def test_netbox_binding_tool_kind_and_fields_are_exact(tmp_path, change):
    with pytest.raises(RuntimeRefused):
        docker.validate_runtime_fields(runtime(netbox_binding(tmp_path, **change), hosted=HOSTED))


def test_netbox_binding_without_credential_file_is_refused(tmp_path):
    value = netbox_binding(tmp_path)
    del value['credential_file']
    with pytest.raises(RuntimeRefused):
        docker.validate_runtime_fields(runtime(value, hosted=HOSTED))


def test_netbox_source_closure_must_contain_the_reviewed_files(tmp_path):
    value = netbox_binding(tmp_path)
    del value['source_sha256']['src/netbox_mcp_server/netclaw_http.py']
    with pytest.raises(RuntimeRefused, match='mcp_source_closure_required'):
        docker.validate_runtime_fields(runtime(value, hosted=HOSTED))


def test_exact_arguments_are_bound_to_the_selection_hash(tmp_path):
    value = netbox_binding(tmp_path)
    mcp.validate_binding(value, arguments=DEVICE, check_files=False)
    changed = dict(DEVICE, object_id=28)
    with pytest.raises(RuntimeRefused, match='mcp_selection_changed'):
        mcp.validate_binding(value, arguments=changed, check_files=False)
    for bad in (dict(DEVICE, fields=['id']), dict(DEVICE, brief=True), dict(DEVICE, object_type='dcim.site')):
        with pytest.raises(Exception):
            mcp.validate_binding(value, arguments=bad, check_files=False)


# ---- hosted profile model rule ---------------------------------------------------------------------

def test_profile_accepts_the_guard_image_model_and_ids_differ_per_model():
    other = dict(HOSTED, model='claude-sonnet-5-5')
    hosted.validate_profile(HOSTED); hosted.validate_profile(other)
    assert hosted.profile_id(HOSTED) == 'hosted-anthropic-claude-sonnet-4-6'
    assert hosted.profile_id(other) == 'hosted-anthropic-claude-sonnet-5-5'
    assert hosted.limits(HOSTED)['model'] == 'claude-sonnet-4-6'
    assert hosted.profile_binding(HOSTED) != hosted.profile_binding(other)
    assert hosted.GUARD_IMAGE_MODEL == 'claude-sonnet-4-6'
    for model in ('claude-opus-5-5', 'claude-sonnet-4-5', ''):
        with pytest.raises(hosted.HostedRefused):
            hosted.validate_profile(dict(HOSTED, model=model))


def test_runtime_revision_binds_the_profile_model(monkeypatch):
    monkeypatch.setattr(docker, 'validate_runtime_fields', lambda config: 'mcp')
    monkeypatch.setattr(docker, '_image', lambda value: value)
    monkeypatch.setattr(docker, 'guard_policy_digest', lambda guard: 'g' * 64)
    monkeypatch.setattr(docker, '_native_identity', lambda value: {'resolved_path': '/d'})
    monkeypatch.setattr(docker, '_docker_host', lambda value: value)
    base = {'model_profile': {'provider': 'anthropic', 'model': 'claude-sonnet-4-6', 'runtime_kind': 'openclaw',
                              'runtime_version': docker._QUALIFIED_HARNESSES['openclaw'], 'profile_id': hosted.profile_id(HOSTED)},
            'hosted': HOSTED, 'agent_image': 'a', 'relay_image': 'r', 'guard': {}, 'docker': {}, 'docker_host': 'h',
            'sandbox_address_pool': '198.18.0.0/24', 'mcp': {}, 'relay_transport': 'tcp'}
    first = docker.runtime_profile_revision(base)
    mismatch = copy.deepcopy(base); mismatch['model_profile']['model'] = 'claude-sonnet-5-5'
    with pytest.raises(RuntimeRefused, match='unqualified_hosted_execution_profile'):
        docker.runtime_profile_revision(mismatch)
    switched = copy.deepcopy(base)
    switched['hosted']['model'] = 'claude-sonnet-5-5'
    switched['model_profile'].update(model='claude-sonnet-5-5', profile_id=hosted.profile_id(switched['hosted']))
    assert docker.runtime_profile_revision(switched) != first


# ---- catalog contract for hosted + netbox -----------------------------------------------------------

def catalog_entry(arguments=DEVICE, tool='netbox_get_object_by_id'):
    member = {'installation_id': str(uuid.uuid4()), 'member_id': 'nc182-r09/netbox-aaaaaa', 'key_id': h('key'),
              'enrollment_generation': str(uuid.uuid4())}
    model = {'profile_id': hosted.profile_id(HOSTED), 'profile_revision': h('rev'), 'runtime_kind': 'openclaw',
             'runtime_version': '2026.7.1-2', 'provider': 'anthropic', 'model': 'claude-sonnet-4-6', 'guard_policy_sha256': h('g')}
    entry = {'member': member, 'model_profiles': [model], 'tools': [{
        'tool': tool, 'tool_schema_sha256': h('schema'), 'arguments': arguments, 'arguments_sha256': sha(arguments),
        'device_ref': 'dcim.device:27', 'inventory_revision': h('sel'), 'endpoint_sha256': h('endpoint'),
        'limits': {'inference_timeout_ms': 60000, 'tool_timeout_ms': 30000, 'max_inference_calls': 2, 'max_tool_calls': 1,
                   'max_output_bytes': 262144}}]}
    return entry


def test_hosted_netbox_catalog_entry_validates():
    contract.validate_catalog_entry(catalog_entry())


@pytest.mark.parametrize('arguments', [dict(DEVICE, fields=['id', 'name']), dict(DEVICE, brief=True), dict(DEVICE, object_type='dcim.site'),
                                       dict(DEVICE, object_id=0), dict(DEVICE, extra=1)])
def test_hosted_netbox_catalog_refuses_any_changed_selection(arguments):
    with pytest.raises(Exception):
        contract.validate_catalog_entry(catalog_entry(arguments=arguments))


# ---- hosted freshness window (independent of the Ollama 3000 ms ceiling) -----------------------------

import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from bgp.federation.ha.effect import CURRENT, EffectScope  # noqa: E402
from bgp.federation.ha import hosted_model_transport as transport  # noqa: E402


async def _serve(handler):
    server = await asyncio.start_server(handler, '127.0.0.1', 0)
    return server, 'http://127.0.0.1:%d' % server.sockets[0].getsockname()[1]


async def _guard(reader, writer):
    header = await reader.readuntil(b'\r\n\r\n')
    size = int(next(line.split(b':', 1)[1] for line in header.split(b'\r\n') if line.lower().startswith(b'content-length:')))
    await reader.readexactly(size)
    body = b'{"id":"x","choices":[]}'
    writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\nConnection: close\r\n\r\n' + body)
    await writer.drain(); writer.close()


def _payload():
    return {'limits': {'expires_at_ms': int(time.time() * 1000) + 5000, 'inference_timeout_ms': 1000}}


async def _forward(url, remaining):
    scope = EffectScope('model', lambda: remaining)
    token = CURRENT.set(scope)
    try:
        return await transport.ha_hosted_model_forward(SimpleNamespace(hosted=HOSTED, guard_token='cap', ollama=None),
                                                       _payload(), {'messages': []}, url)
    finally:
        CURRENT.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize('remaining', [4400, 4300, 3001, 3000, 1500, 251])
async def test_window_accepts_fast_and_slow_wan_admissions(remaining):
    """admission_ms 4500: elapsed 100 ms (remaining 4400) .. 4249 ms (remaining 251) all hand off. The Ollama helper
    would refuse everything above 3000, which is what stranded the first live operations."""
    server, url = await _serve(_guard)
    try:
        assert json.loads(await _forward(url, remaining))['id'] == 'x'
    finally:
        server.close(); await server.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize('remaining', [250, 0, 10001])
async def test_window_bounds_are_still_enforced(remaining):
    server, url = await _serve(_guard)
    try:
        with pytest.raises(HAError, match='admission_expired'):
            await _forward(url, remaining)
    finally:
        server.close(); await server.wait_closed()


# ---- independent counter from the guard's own durable fence -------------------------------------------

def _fence(path, rows):
    guard = path / 'guard'
    guard.mkdir()
    db = sqlite3.connect(guard / 'provider.sqlite')
    db.execute('CREATE TABLE provider_request(request_digest TEXT, ordinal INTEGER, canonical_request BLOB, state TEXT, '
               'upstream_attempt_count INTEGER)')
    db.executemany('INSERT INTO provider_request VALUES(?,?,?,?,?)', rows)
    db.commit(); db.close()


def test_provider_fence_reader_counts_guard_side_requests(tmp_path):
    _fence(tmp_path, [('a', 1, b'{}', 'finished', 1), ('b', 2, b'{}', 'finished', 1)])
    assert transport.read_provider_fence(tmp_path) == {'requests': 2, 'upstream_attempts': 2,
                                                       'states': ['finished', 'finished'], 'ordinals': [1, 2]}


def test_provider_fence_reader_is_read_only_and_fails_closed(tmp_path):
    with pytest.raises(RuntimeRefused, match='provider_fence_unavailable'):
        transport.read_provider_fence(tmp_path)
    _fence(tmp_path, [('a', 1, b'{}', 'claimed', 2)])
    before = (tmp_path / 'guard/provider.sqlite').read_bytes()
    assert transport.read_provider_fence(tmp_path)['upstream_attempts'] == 2
    assert (tmp_path / 'guard/provider.sqlite').read_bytes() == before


# ---- live finding: a hosted refusal inside the MCP session manager must stay a refusal --------------------

def _make_group(name, errors):
    """Faithful stand-in on every Python: the code keys on the type name and the `exceptions` tuple only."""
    cls = type(name, (BaseException,), {})
    value = cls('group')
    value.exceptions = tuple(errors)
    return value


def test_single_protected_error_is_unwrapped():
    from bgp.federation.protected_runtime import RuntimeUnknown
    refusal, unknown = RuntimeRefused('guard_not_ready'), RuntimeUnknown('model_handoff_unknown')
    assert docker._single_protected_error(_make_group('ExceptionGroup', [refusal])) is refusal
    assert docker._single_protected_error(_make_group('BaseExceptionGroup', [unknown])) is unknown


@pytest.mark.parametrize('group', [
    _make_group('ExceptionGroup', [RuntimeRefused('a'), RuntimeRefused('b')]),   # more than one member: ambiguous
    _make_group('ExceptionGroup', [ValueError('x')]),                            # not a reviewed Protected* error
    _make_group('ExceptionGroup', []),
    _make_group('SomethingElse', [RuntimeRefused('a')]),                         # not a group type
    RuntimeRefused('plain'), ValueError('plain'), KeyboardInterrupt()])
def test_nothing_else_is_unwrapped(group):
    assert docker._single_protected_error(group) is None


def test_unwrapping_is_wired_for_the_hosted_path_only():
    import inspect
    source = inspect.getsource(docker.DockerExecutor.run)
    assert "_single_protected_error(group) if getattr(self, 'hosted', None) is not None else None" in source
    assert source.index('except BaseException as group') < source.index('finally:\n            # No retries')


def test_real_task_group_wraps_a_refusal_and_the_helper_restores_it():
    pytest.importorskip('mcp.server.mcpserver')
    from mcp.server.mcpserver import MCPServer
    server = MCPServer('x')
    server.streamable_http_app(json_response=True, stateless_http=True)

    async def body():
        try:
            async with server.session_manager.run():
                raise RuntimeRefused('guard_not_ready')
        except BaseException as caught:
            return caught
    caught = asyncio.run(body())
    assert not isinstance(caught, RuntimeRefused)          # the wrapping that made the member go silent
    restored = docker._single_protected_error(caught)
    assert isinstance(restored, RuntimeRefused) and restored.code == 'guard_not_ready'


def test_hosted_guard_management_port_matches_the_health_probe():
    """guard_health_probe() for every non-Ollama guard queries one fixed port; the derived config must serve it."""
    import re
    probe = docker.guard_health_probe(None)
    port = int(re.search(r'127\.0\.0\.1:(\d+)/health', probe).group(1))
    from labs.ha import r09_member as builder
    assert builder.HOSTED_GUARD_API_PORT == port == 4001
    assert docker.guard_health_probe({'any': 'ollama'}).count('18970') == 1  # the Ollama probe is unchanged


def test_hosted_request_bound_fits_the_reviewed_netbox_skill_context():
    """Live finding (gen4): the reviewed netbox-reconcile skill context is ~18.6 KB; a 13 KB hosted bound made every
    NetBox model call fail pre-connect with model_request_bound (HTTP 503), the agent retried, and the fence refused."""
    import importlib
    module = importlib.import_module('bgp.federation.ha.hosted_model_transport')
    assert module.MAX_REQUEST >= 65536
    assert module.MAX_REQUEST <= 1024 * 1024
