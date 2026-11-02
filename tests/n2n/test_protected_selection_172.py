"""Real local file/socket/pin checks with synthetic executor effects only.

No Docker daemon, provider, guard, SSH or device is called. The existing revision
fixture supplies owned executable files and a real, unserved local Unix socket;
only DockerExecutor.run is replaced for selection/concurrency observations.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import uuid

import pytest

from test_protected_revision_bindings import bound
from bgp.federation import protected_contract as contract
from bgp.federation import protected_docker as docker
from bgp.federation import protected_runtime as runtime
from bgp.federation.protected_selection import ProfiledExecutor


LIMITS = {'inference_timeout_ms': 90000, 'tool_timeout_ms': 120000,
          'max_inference_calls': 2, 'max_tool_calls': 1, 'max_output_bytes': 262144}
MEMBER = {'installation_id': 'fixture-installation', 'member_id': 'r03/pyats',
          'key_id': 'a' * 64, 'enrollment_generation': 'fixture-generation'}


def catalog_for(wrapper):
    models, tools = {}, {}
    for item in wrapper['profiles']:
        model, tool = item['runtime']['model_profile'], item['tool_call']
        models[model['profile_id']] = copy.deepcopy(model)
        tools[(tool['tool'], contract.encode(tool['arguments']))] = dict(copy.deepcopy(tool), limits=dict(LIMITS))
    return {'member': dict(MEMBER), 'model_profiles': list(models.values()), 'tools': list(tools.values())}


def payload_for(item):
    return {'operation_id': str(uuid.uuid4()), 'model_profile': copy.deepcopy(item['runtime']['model_profile']),
            'tool_call': copy.deepcopy(item['tool_call']), 'limits': dict(LIMITS, expires_at_ms=9_000_000_000_000)}


def second_model(wrapper):
    result = copy.deepcopy(wrapper)
    for original in wrapper['profiles']:
        item = copy.deepcopy(original)
        config = item['runtime']
        item['model_profile_id'] = 'hermes-fixture'
        config['model_profile'].update(profile_id='hermes-fixture', runtime_kind='hermes', runtime_version='v0.21.6')
        config['agent_image'] = 'sha256:' + '9' * 64
        config['model_profile']['profile_revision'] = docker.revision_bindings(config)['profile_revision']
        result['profiles'].append(item)
    return result


@pytest.fixture
def packet(bound):
    import yaml
    base, _, directory = bound
    profiles = []
    for index, device in enumerate(('R1', 'R2', 'SW1', 'SW2'), 1):
        config = copy.deepcopy(base)
        keys = directory / (device + '.known_hosts')
        keys.write_text(f'192.0.2.{index} ssh-ed25519 fixture-{device}-public-key\n')
        keys.chmod(0o600)
        document = {'testbed': {'name': 'fixture-' + device, 'credentials': {
            'default': {'username': '%ENV{PYATS_R02_USERNAME}', 'password': '%ENV{PYATS_R02_PASSWORD}'},
            'enable': {'password': '%ENV{PYATS_R02_ENABLE_PASSWORD}'}}}, 'devices': {
                device: {'os': 'iosxe', 'platform': 'iol', 'type': 'router' if device.startswith('R') else 'switch',
                    'connections': {'ssh': {'protocol': 'ssh', 'ip': f'192.0.2.{index}', 'port': 22,
                        'ssh_options': '-F /dev/null -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile=' + str(keys)}}}}}
        testbed = directory / (device + '.yaml')
        testbed.write_text(yaml.safe_dump(document))
        testbed.chmod(0o600)
        config['pyats'].update(testbed=str(testbed), testbed_sha256=hashlib.sha256(testbed.read_bytes()).hexdigest(),
                              known_hosts=str(keys), known_hosts_sha256=hashlib.sha256(keys.read_bytes()).hexdigest(),
                              endpoint_sha256=hashlib.sha256(('fixture endpoint ' + device).encode()).hexdigest())
        pins = docker.revision_bindings(config)
        arguments = {'device_name': device, 'command': 'show version', 'timeout': 60, 'retries': 1}
        tool = {'tool': 'pyats_run_show_command', 'arguments': arguments, 'arguments_sha256': contract.sha256(arguments),
                'device_ref': device, 'tool_schema_sha256': pins['tool_schema_sha256'],
                'inventory_revision': config['pyats']['testbed_sha256'], 'endpoint_sha256': config['pyats']['endpoint_sha256']}
        profiles.append({'model_profile_id': config['model_profile']['profile_id'], 'tool_call': tool, 'runtime': config})
    return {'schemaVersion': 1, 'profiles': profiles}


@pytest.fixture
def selectors():
    owned = []
    def create(packet, *, validate=True):
        selected = ProfiledExecutor(packet, manager=SimpleNamespace())
        owned.append(selected)
        if validate:
            selected.validate_catalog(catalog_for(packet), runtime_config=packet)
        return selected
    yield create
    for selected in owned:
        selected.close()


def test_four_profiles_select_private_single_device_children_concurrently(packet, selectors, monkeypatch):
    import yaml
    selected = selectors(packet)
    entered, effects, seen = [], [], []
    async def run():
        all_entered = asyncio.Event()
        async def synthetic_child(self, payload, gate):
            entered.append(payload['tool_call']['device_ref'])
            if len(entered) == 4:
                all_entered.set()
            await asyncio.wait_for(all_entered.wait(), 2)
            document = yaml.safe_load(Path(self.config['pyats']['testbed']).read_text())
            device = payload['tool_call']['arguments']['device_name']
            assert set(document['devices']) == {device}
            assert Path(self.config['pyats']['known_hosts']).name == device + '.known_hosts'
            seen.append((device, self.config['pyats']['endpoint_sha256']))
            async def effect():
                effects.append(device)
                return {'device': device}
            return await gate(payload['tool_call'], effect)
        async def gate(tool, effect):
            result = await effect()
            assert result['device'] == tool['device_ref']
            return result
        monkeypatch.setattr(docker.DockerExecutor, 'run', synthetic_child)
        return await asyncio.gather(*(selected.run(payload_for(item), gate) for item in packet['profiles']))
    results = asyncio.run(run())
    assert sorted(item['device'] for item in results) == sorted(effects) == ['R1', 'R2', 'SW1', 'SW2']
    assert dict(seen) == {item['tool_call']['device_ref']: item['tool_call']['endpoint_sha256'] for item in packet['profiles']}


def test_cartesian_models_share_calls_without_ambiguous_selection(packet, selectors, monkeypatch):
    packet = second_model(packet)
    selected = selectors(packet)
    seen = []
    async def synthetic_child(self, payload, gate):
        seen.append((self.config['model_profile']['runtime_kind'], payload['tool_call']['device_ref']))
    monkeypatch.setattr(docker.DockerExecutor, 'run', synthetic_child)
    async def run():
        for item in packet['profiles']:
            await selected.run(payload_for(item), None)
    asyncio.run(run())
    assert set(seen) == {(model, device) for model in ('openclaw', 'hermes') for device in ('R1', 'R2', 'SW1', 'SW2')}


@pytest.mark.parametrize('change', ['unknown', 'pin', 'endpoint', 'inventory', 'arguments', 'model_revision', 'guard', 'other_model'])
def test_complete_signed_identity_required_before_any_executor(packet, selectors, monkeypatch, change):
    selected = selectors(packet)
    payload = payload_for(packet['profiles'][0])
    if change == 'unknown':
        payload['tool_call']['device_ref'] = 'SANDBOX-R1'
    elif change in ('pin', 'endpoint', 'inventory'):
        key = {'pin': 'tool_schema_sha256', 'endpoint': 'endpoint_sha256', 'inventory': 'inventory_revision'}[change]
        payload['tool_call'][key] = 'e' * 64
    elif change == 'arguments':
        payload['tool_call']['arguments']['device_name'] = 'R2'
        payload['tool_call']['arguments_sha256'] = contract.sha256(payload['tool_call']['arguments'])
    else:
        key = {'model_revision': 'profile_revision', 'guard': 'guard_policy_sha256', 'other_model': 'profile_id'}[change]
        payload['model_profile'][key] = 'f' * 64
    calls = []
    async def forbidden(*args):
        calls.append('executor')
    monkeypatch.setattr(docker.DockerExecutor, 'run', forbidden)
    with pytest.raises(contract.ProtectedError, match='execution_profile_not_supported'):
        asyncio.run(selected.run(payload, None))
    assert calls == []


@pytest.mark.parametrize('change', ['version_bool', 'version_unknown', 'missing_discriminator', 'extra', 'empty', 'seventeen',
                                     'entry_extra', 'nested', 'duplicate', 'model_id', 'model_conflict', 'tool_conflict',
                                     'separate_state', 'relative_state', 'bad_pin', 'unknown_runtime_field', 'unsafe_pool', 'tool_timeout'])
def test_invalid_packet_refuses_before_child_state(packet, monkeypatch, change):
    state = Path(packet['profiles'][0]['runtime']['state_dir'])
    if change == 'version_bool': packet['schemaVersion'] = True
    elif change == 'version_unknown': packet['schemaVersion'] = 2
    elif change == 'missing_discriminator': del packet['schemaVersion']
    elif change == 'extra': packet['unexpected'] = True
    elif change == 'empty': packet['profiles'] = []
    elif change == 'seventeen': packet['profiles'] = [copy.deepcopy(packet['profiles'][0]) for _ in range(17)]
    elif change == 'entry_extra': packet['profiles'][0]['limits'] = LIMITS
    elif change == 'nested': packet['profiles'][0]['runtime'] = {'schemaVersion': 1, 'profiles': []}
    elif change == 'duplicate': packet['profiles'].append(copy.deepcopy(packet['profiles'][0]))
    elif change == 'model_id': packet['profiles'][0]['model_profile_id'] = 'different'
    elif change == 'model_conflict': packet['profiles'][1]['runtime']['model_profile']['profile_revision'] = 'e' * 64
    elif change == 'tool_conflict':
        packet = second_model(packet)
        packet['profiles'][-1]['tool_call']['endpoint_sha256'] = 'e' * 64
    elif change == 'separate_state': packet['profiles'][-1]['runtime']['state_dir'] += '-different'
    elif change == 'relative_state': packet['profiles'][-1]['runtime']['state_dir'] = 'relative'
    elif change == 'bad_pin': packet['profiles'][-1]['tool_call']['endpoint_sha256'] = 'e' * 64
    elif change == 'unknown_runtime_field': packet['profiles'][-1]['runtime']['inherited_environment'] = True
    elif change == 'unsafe_pool': packet['profiles'][-1]['runtime']['sandbox_address_pool'] = '192.168.0.0/16'
    elif change == 'tool_timeout':
        tool = packet['profiles'][-1]['tool_call']
        tool['arguments']['timeout'] = 121
        tool['arguments_sha256'] = contract.sha256(tool['arguments'])
    constructed = []
    def forbidden(*args, **kwargs):
        constructed.append(True)
        raise AssertionError('child must not be created')
    monkeypatch.setattr(docker.DockerExecutor, '__init__', forbidden)
    with pytest.raises(contract.ProtectedError):
        ProfiledExecutor(packet, manager=None)
    assert constructed == [] and not state.exists()


@pytest.mark.parametrize('change', ['missing', 'extra', 'model_pin', 'call_pin', 'duplicate_model', 'duplicate_call', 'bad_limits'])
def test_catalog_coverage_and_uniqueness_are_mandatory(packet, selectors, change):
    selected = selectors(packet, validate=False)
    catalog = catalog_for(packet)
    if change == 'missing': catalog['tools'].pop()
    elif change == 'extra':
        extra = copy.deepcopy(catalog['tools'][0])
        extra['arguments']['device_name'] = extra['device_ref'] = 'R5'
        extra['arguments_sha256'] = contract.sha256(extra['arguments'])
        catalog['tools'].append(extra)
    elif change == 'model_pin': catalog['model_profiles'][0]['profile_revision'] = 'e' * 64
    elif change == 'call_pin': catalog['tools'][0]['endpoint_sha256'] = 'e' * 64
    elif change == 'duplicate_model': catalog['model_profiles'].append(copy.deepcopy(catalog['model_profiles'][0]))
    elif change == 'duplicate_call': catalog['tools'].append(copy.deepcopy(catalog['tools'][0]))
    elif change == 'bad_limits': catalog['tools'][0]['limits']['max_tool_calls'] = 2
    with pytest.raises(contract.ProtectedError):
        selected.validate_catalog(catalog, runtime_config=packet)
    with pytest.raises(contract.ProtectedError, match='execution_catalog_unvalidated'):
        asyncio.run(selected.run(payload_for(packet['profiles'][0]), None))


def test_catalog_cannot_omit_one_model_device_combination(packet, selectors):
    full = second_model(packet)
    partial = copy.deepcopy(full)
    partial['profiles'].pop()
    selected = selectors(partial, validate=False)
    with pytest.raises(contract.ProtectedError, match='execution_catalog_mismatch'):
        selected.validate_catalog(catalog_for(full), runtime_config=partial)


def test_configuration_and_catalog_edits_require_restart_and_close_admission(packet, selectors):
    selected = selectors(packet)
    changed = copy.deepcopy(packet)
    changed['profiles'][0]['runtime']['guard']['env_file'] += '.changed'
    with pytest.raises(contract.ProtectedError, match='execution_profiles_changed'):
        selected.validate_catalog(catalog_for(packet), runtime_config=changed)
    with pytest.raises(contract.ProtectedError, match='execution_catalog_unvalidated'):
        asyncio.run(selected.run(payload_for(packet['profiles'][0]), None))
    with pytest.raises(contract.ProtectedError, match='execution_profiles_restart_required'):
        selected.validate_catalog(catalog_for(packet), runtime_config=packet)
    selected = selectors(packet)
    catalog = catalog_for(packet)
    catalog['tools'][0]['limits']['max_output_bytes'] -= 1
    with pytest.raises(contract.ProtectedError, match='execution_catalog_changed'):
        selected.validate_catalog(catalog, runtime_config=packet)
    with pytest.raises(contract.ProtectedError, match='execution_profiles_restart_required'):
        selected.validate_catalog(catalog_for(packet), runtime_config=packet)


def test_invalid_incoming_operation_does_not_poison_private_configuration(packet, selectors, monkeypatch):
    selected = selectors(packet)
    original = payload_for(packet['profiles'][0])
    altered = copy.deepcopy(original)
    altered['tool_call']['endpoint_sha256'] = 'e' * 64
    with pytest.raises(contract.ProtectedError, match='execution_profile_not_supported'):
        asyncio.run(selected.run(altered, None))
    calls = []
    async def child(self, approved, gate):
        calls.append(approved['operation_id'])
    monkeypatch.setattr(docker.DockerExecutor, 'run', child)
    selected.validate_catalog(catalog_for(packet), runtime_config=packet)
    asyncio.run(selected.run(original, None))
    assert calls == [original['operation_id']]


def test_private_profile_read_failure_invalidation_cannot_be_restored(packet, selectors):
    selected = selectors(packet)
    selected.invalidate()
    selected.invalidate()
    with pytest.raises(contract.ProtectedError, match='execution_profiles_restart_required'):
        selected.validate_catalog(catalog_for(packet), runtime_config=packet)
    with pytest.raises(contract.ProtectedError, match='execution_catalog_unvalidated'):
        asyncio.run(selected.run(payload_for(packet['profiles'][0]), None))
    # Starting a new executor revalidates the complete restored configuration.
    restarted = selectors(packet)
    restarted.validate_catalog(catalog_for(packet), runtime_config=packet)


def test_caller_mutation_cannot_change_snapshot_or_inflight_payload(packet, selectors, monkeypatch):
    selected = selectors(packet)
    payload = payload_for(packet['profiles'][0])
    entered, release = asyncio.Event(), asyncio.Event()
    observed = []
    async def child(self, approved, gate):
        entered.set()
        await release.wait()
        observed.append((approved['tool_call']['arguments']['device_name'], Path(self.config['pyats']['testbed']).name))
    monkeypatch.setattr(docker.DockerExecutor, 'run', child)
    async def run():
        task = asyncio.create_task(selected.run(payload, None))
        await entered.wait()
        packet['profiles'][0]['runtime']['pyats']['testbed'] = '/not/an/approved/inventory'
        payload['tool_call']['arguments']['device_name'] = 'SW2'
        release.set()
        await task
    asyncio.run(run())
    assert observed == [('R1', 'R1.yaml')]


def test_child_mutation_and_unvalidated_catalog_never_start_executor(packet, selectors, monkeypatch):
    selected = selectors(packet, validate=False)
    payload = payload_for(packet['profiles'][0])
    with pytest.raises(contract.ProtectedError, match='execution_catalog_unvalidated'):
        asyncio.run(selected.run(payload, None))
    selected.validate_catalog(catalog_for(packet), runtime_config=packet)
    children = list(selected._children.values())
    children[0].config['pyats']['testbed'] = children[1].config['pyats']['testbed']
    with pytest.raises(contract.ProtectedError, match='execution_profiles_changed'):
        asyncio.run(selected.run(payload, None))


def test_actual_endpoint_file_drift_stops_before_run_creates_operation(packet, selectors):
    selected = selectors(packet)
    payload = payload_for(packet['profiles'][0])
    path = Path(packet['profiles'][0]['runtime']['pyats']['known_hosts'])
    original = path.read_bytes()
    path.write_text('changed host identity\n')
    with pytest.raises(runtime.RuntimeRefused, match='inventory_or_host_key_changed'):
        asyncio.run(selected.run(payload, None))
    assert not (Path(packet['profiles'][0]['runtime']['state_dir']) / payload['operation_id']).exists()
    path.write_bytes(original)
    with pytest.raises(contract.ProtectedError, match='execution_profiles_restart_required'):
        selected.validate_catalog(catalog_for(packet), runtime_config=packet)


def test_shared_durable_inference_namespace_survives_selection_and_restart(packet, selectors):
    selected = selectors(packet)
    children = list(selected._children.values())
    operation = str(uuid.uuid4())
    children[0].fence.claim(operation, {'fixture': 'first'})
    assert all(child.fence.count(operation) == 1 for child in children)
    selected.close()
    restarted = selectors(packet)
    for child in restarted._children.values():
        with pytest.raises(runtime.RuntimeRefused, match='inference_spent_or_unreconciled'):
            child.fence.claim(operation, {'fixture': 'another device'})
    assert all(child.fence.count(operation) == 1 for child in restarted._children.values())


def test_factory_preserves_single_runtime_and_rejects_malformed_wrapper(packet):
    legacy = runtime.build_executor(packet['profiles'][0]['runtime'], manager=None)
    assert isinstance(legacy, docker.DockerExecutor)
    legacy.fence.close()
    selected = runtime.build_executor(packet, manager=None)
    assert isinstance(selected, ProfiledExecutor)
    selected.close()
    with pytest.raises(contract.ProtectedError):
        runtime.build_executor({'profiles': []}, manager=None)
    with pytest.raises(contract.ProtectedError):
        runtime.build_executor(dict(packet['profiles'][0]['runtime'], schemaVersion=1), manager=None)


def test_close_is_idempotent_and_refuses_later_validation_or_dispatch(packet, selectors):
    selected = selectors(packet)
    children = list(selected._children.values())
    selected.close()
    selected.close()
    with pytest.raises(contract.ProtectedError, match='execution_profiles_closed'):
        selected.validate_catalog(catalog_for(packet), runtime_config=packet)
    with pytest.raises(contract.ProtectedError, match='execution_catalog_unvalidated'):
        asyncio.run(selected.run(payload_for(packet['profiles'][0]), None))
    import sqlite3
    for child in children:
        with pytest.raises(sqlite3.ProgrammingError):
            child.fence.count('closed')


def test_constructor_failure_closes_already_created_connections(packet, monkeypatch):
    import sqlite3
    original = docker.DockerExecutor.__init__
    constructed = []
    def init(self, config, *, manager):
        if constructed:
            raise runtime.RuntimeRefused('fixture_constructor_failure')
        original(self, config, manager=manager)
        constructed.append(self)
    monkeypatch.setattr(docker.DockerExecutor, '__init__', init)
    with pytest.raises(runtime.RuntimeRefused, match='fixture_constructor_failure'):
        ProfiledExecutor(packet, manager=None)
    assert len(constructed) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        constructed[0].fence.count('closed')


def test_exact_sixteen_entry_bound_accepts_complete_catalog(packet, selectors):
    profiles = []
    for index in range(4):
        for original in packet['profiles']:
            item = copy.deepcopy(original)
            item['model_profile_id'] = 'qualified-alias-' + str(index)
            item['runtime']['model_profile']['profile_id'] = item['model_profile_id']
            profiles.append(item)
    packet['profiles'] = profiles
    selected = selectors(packet)
    assert len(selected._children) == 16


def test_selector_source_is_part_of_derived_runtime_revision(packet):
    assert 'protected_selection.py' in docker._HOST_SOURCE_PATHS
    source = Path(docker._HOST_SOURCE_PATHS['protected_selection.py'])
    assert docker._HOST_SOURCE_PINS['protected_selection.py'] == hashlib.sha256(source.read_bytes()).hexdigest()


@pytest.mark.parametrize('kind', ['bool_limit', 'expiry', 'extra', 'duplicate_tool', 'duplicate_model'])
def test_pure_catalog_validator_refuses_ambiguous_or_unbounded_metadata(packet, kind):
    catalog = catalog_for(packet)
    if kind == 'bool_limit': catalog['tools'][0]['limits']['max_tool_calls'] = True
    elif kind == 'expiry': catalog['tools'][0]['limits']['expires_at_ms'] = 123
    elif kind == 'extra': catalog['tools'][0]['path'] = '/untrusted'
    elif kind == 'duplicate_tool': catalog['tools'].append(copy.deepcopy(catalog['tools'][0]))
    elif kind == 'duplicate_model': catalog['model_profiles'].append(copy.deepcopy(catalog['model_profiles'][0]))
    with pytest.raises(contract.ProtectedError):
        contract.validate_catalog_entry(catalog)


def test_pure_catalog_validation_does_not_import_member_runtime(packet, tmp_path):
    catalog = catalog_for(packet)
    before = copy.deepcopy(catalog)
    contract.validate_catalog_entry(catalog)
    assert catalog == before
    file = tmp_path / 'catalog.json'
    file.write_bytes(contract.encode(catalog))
    source = Path(contract.__file__).resolve().parents[2]
    code = ('import sys,json;sys.path.insert(0,sys.argv[1]);'
            'from bgp.federation.protected_contract import validate_catalog_entry;'
            'validate_catalog_entry(json.load(open(sys.argv[2])));'
            'assert not any(name in sys.modules for name in '
            '["bgp.federation.protected_docker","bgp.federation.protected_runtime","bgp.federation.protected_selection"])')
    completed = subprocess.run([sys.executable, '-c', code, str(source), str(file)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
