"""Full selector construction with real private files, sockets and SQLite fences.

No Docker daemon or provider runs. The valid dispatch test replaces only the
child's run method; startup, catalog and operation admission remain real.
"""
import asyncio
import copy
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_protected_revision_bindings import bound
from test_protected_cloud_mcp_173 import mcp_config
from test_protected_calculator_176 import source as native_source
from test_protected_ollama_176 import profile
from bgp.federation import protected_contract as contract
from bgp.federation import protected_docker as docker
from bgp.federation import protected_runtime as runtime
from bgp.federation.protected_selection import ProfiledExecutor


@pytest.fixture(params=[4, 6])
def selected(request, bound, mcp_config):
    config, _, root = bound
    family = request.param
    config = copy.deepcopy(config)
    del config['pyats']
    native = copy.deepcopy(mcp_config)
    native.pop('origin'); native.pop('credential_file')
    source = native_source(root / 'subnet-fixture')
    script = source / 'servers/subnetcalculator_mcp.py'
    script.chmod(0o600)
    skill = root / 'skills/subnet-calculator/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('Fixture reviewed subnet calculator skill\n')
    skill.chmod(0o600)
    arguments = {'cidr': '192.0.2.0/26' if family == 4 else '2001:db8:1234::/48'}
    tool = 'subnet_calculator' if family == 4 else 'subnet_calculator_v6'
    native.update(kind='subnet_summary', tool=tool, source_root=str(source),
        source_sha256={'servers/subnetcalculator_mcp.py': hashlib.sha256(script.read_bytes()).hexdigest()},
        skill={'path': str(skill), 'sha256': hashlib.sha256(skill.read_bytes()).hexdigest()},
        selection_sha256=runtime.sha({'tool': tool, 'arguments': arguments}),
        endpoint_sha256=runtime.sha({'kind': 'subnet', 'transport': 'private-stdio'}))
    config.update(mcp=native, relay_transport='unix', ollama=profile(root, family))
    config['ollama'].update(guard_uid=os.getuid(), model_uid=21006)
    config['model_profile'].update(profile_id='ollama-cpu-ipv' + str(family),
        provider='ollama', model='qwen3:0.6b')
    pins = docker.revision_bindings(config)
    config['model_profile'].update({key: pins[key] for key in ('profile_revision', 'guard_policy_sha256')})
    call = {'tool': tool, 'arguments': arguments, 'arguments_sha256': contract.sha256(arguments),
        'tool_schema_sha256': pins['tool_schema_sha256'], 'device_ref': arguments['cidr'],
        'inventory_revision': native['selection_sha256'], 'endpoint_sha256': native['endpoint_sha256']}
    item = {'model_profile_id': config['model_profile']['profile_id'], 'tool_call': call, 'runtime': config}
    wrapper = {'schemaVersion': 1, 'profiles': [item]}
    limits = {'inference_timeout_ms': 60000 if family == 4 else 120000,
        'tool_timeout_ms': 30000, 'max_inference_calls': 2, 'max_tool_calls': 1, 'max_output_bytes': 262144}
    catalog = {'member': {'installation_id': 'fixture-installation', 'member_id': 'r05/calculator',
        'key_id': 'a' * 64, 'enrollment_generation': 'fixture-generation'},
        'model_profiles': [config['model_profile']], 'tools': [dict(call, limits=limits)]}
    executor = ProfiledExecutor(wrapper, manager=SimpleNamespace())
    executor.validate_catalog(catalog, runtime_config=wrapper)
    payload = {'model_profile': copy.deepcopy(config['model_profile']), 'tool_call': copy.deepcopy(call),
        'issued_at_ms': 1000, 'limits': dict(limits, expires_at_ms=181000)}
    yield executor, config, payload
    for child in executor._children.values():
        child.runner_latch.close()
    executor.close()


def test_full_ollama_selector_starts_without_operation_limits(selected):
    executor, config, payload = selected
    assert executor._catalog_valid and len(executor._children) == 1
    child = next(iter(executor._children.values()))
    assert Path(config['state_dir'], 'inference.sqlite').is_file()
    assert child.runner_latch.snapshot()['state'] == 'idle'
    static = {key: payload[key] for key in ('model_profile', 'tool_call')}
    assert docker.validate_catalog_bindings(config, static) == docker.revision_bindings(config)
    with pytest.raises(runtime.RuntimeRefused, match='ollama_operation_limits_changed'):
        docker.validate_execution_bindings(config, static)


@pytest.mark.parametrize('change', [
    'missing_limits', 'missing_issued', 'missing_expiry', 'missing_call_timeout', 'missing_turns', 'missing_tools',
    'expired', 'overlong', 'call_timeout', 'zero_timeout', 'extra_turn', 'extra_tool', 'boolean_tool', 'noninteger_issued',
])
def test_actual_selector_execution_never_skips_signed_limits(selected, monkeypatch, change):
    executor, config, payload = selected
    if change == 'missing_limits': payload.pop('limits')
    elif change == 'missing_issued': payload.pop('issued_at_ms')
    elif change.startswith('missing_'):
        payload['limits'].pop({'missing_expiry': 'expires_at_ms', 'missing_call_timeout': 'inference_timeout_ms',
                              'missing_turns': 'max_inference_calls', 'missing_tools': 'max_tool_calls'}[change])
    elif change == 'expired': payload['limits']['expires_at_ms'] = payload['issued_at_ms']
    elif change == 'overlong': payload['limits']['expires_at_ms'] += 1
    elif change == 'call_timeout': payload['limits']['inference_timeout_ms'] += 1
    elif change == 'zero_timeout': payload['limits']['inference_timeout_ms'] = 0
    elif change == 'extra_turn': payload['limits']['max_inference_calls'] = 3
    elif change == 'extra_tool': payload['limits']['max_tool_calls'] = 2
    elif change == 'boolean_tool': payload['limits']['max_tool_calls'] = True
    elif change == 'noninteger_issued': payload['issued_at_ms'] = '1000'
    with pytest.raises(runtime.RuntimeRefused, match='ollama_operation_limits_changed'):
        docker.validate_execution_bindings(config, payload)
    called = []
    async def forbidden(*args): called.append(True)
    monkeypatch.setattr(docker.DockerExecutor, 'run', forbidden)
    with pytest.raises(runtime.RuntimeRefused, match='ollama_operation_limits_changed'):
        asyncio.run(executor.run(payload, None))
    assert called == []


def test_valid_operation_still_reaches_the_selected_child(selected, monkeypatch):
    executor, _, payload = selected
    called = []
    async def synthetic_child(self, approved, gate):
        called.append(approved)
        return {'fixture_dispatch': True}
    monkeypatch.setattr(docker.DockerExecutor, 'run', synthetic_child)
    assert asyncio.run(executor.run(payload, None)) == {'fixture_dispatch': True}
    assert called == [payload]


def test_constructor_and_execution_keep_exact_calculator_family(selected, monkeypatch):
    executor, config, payload = selected
    other = copy.deepcopy(payload['tool_call'])
    v4 = config['ollama']['family'] == 4
    other.update(tool='subnet_calculator_v6' if v4 else 'subnet_calculator',
                 arguments={'cidr': '2001:db8:1234::/48' if v4 else '192.0.2.0/26'})
    other['arguments_sha256'] = contract.sha256(other['arguments'])
    wrapper = contract.decode(executor._configuration)
    wrapper['profiles'][0]['tool_call'] = other
    called = []
    def forbidden(*args, **kwargs): called.append(True)
    monkeypatch.setattr(docker.DockerExecutor, '__init__', forbidden)
    with pytest.raises(contract.ProtectedError, match='calculator_family_mismatch'):
        ProfiledExecutor(wrapper, manager=SimpleNamespace())
    payload['tool_call'] = other
    with pytest.raises(contract.ProtectedError, match='calculator_family_mismatch'):
        asyncio.run(executor.run(payload, None))
    assert called == []
