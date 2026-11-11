"""Spec 182 pyATS HA member: source-level fixtures only. No device, no CML, no Anthropic, no Docker, no Border.

Proves the product edits (hosted+pyats runtime shape, optional private credential file, HA effect admission around the
one tools/call) and their negatives, and the builder's offline pyats pipeline. It does NOT qualify the hosted guard path
or a real SSH session to a device (see specs/182-multi-region-ha-borders/pyats-member.md).

Run (python3.10 venv, no mcp):   .../r09venv/bin/python -m pytest tests/n2n/test_ha_pyats_member_182.py
Run (the member's own 3.12 env, has mcp, exercises invoke_pyats):
     PYTHONDONTWRITEBYTECODE=1 ~/.local/share/netclaw/roadmap-r04a-owner-20261104/local-member/venv/bin/python -m pytest -p no:cacheprovider ...
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'mcp-servers/protocol-mcp'))

from bgp.federation import protected_contract as contract  # noqa: E402
from bgp.federation import protected_docker as docker  # noqa: E402
from bgp.federation import protected_runtime as runtime  # noqa: E402
from bgp.federation.ha.config import HAError  # noqa: E402
from bgp.federation.protected_runtime import ExactToolBroker, RuntimeRefused, canonical  # noqa: E402

ARGUMENTS = {'device_name': 'R1', 'command': 'show version', 'timeout': 30, 'retries': 1}
HOSTED = {'schema_version': 1, 'provider': 'anthropic', 'model': 'claude-sonnet-4-6', 'egress_host': 'api.anthropic.com',
          'max_output_tokens': 1024, 'call_timeout_seconds': 60, 'task_timeout_seconds': 180}
FAKE_USER, FAKE_PASS, FAKE_ENABLE = 'fixtureuser', 'fixture-pass-0001', 'fixture-enable-0002'


try:
    import mcp  # noqa: F401
    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False
needs_mcp = pytest.mark.skipif(not HAVE_MCP, reason='needs the mcp SDK: run under the member 3.12 environment')


def h(label):
    return hashlib.sha256(label.encode()).hexdigest()


def write_credentials(path, user=FAKE_USER, password=FAKE_PASS, enable=FAKE_ENABLE, mode=0o600):
    path.write_text(f'PYATS_R02_USERNAME={user}\nPYATS_R02_PASSWORD={password}\nPYATS_R02_ENABLE_PASSWORD={enable}\n')
    path.chmod(mode)
    return path


def strict_document(known_hosts):
    return {'testbed': {'name': 'r09-test', 'credentials': {
        'default': {'username': '%ENV{PYATS_R02_USERNAME}', 'password': '%ENV{PYATS_R02_PASSWORD}'},
        'enable': {'password': '%ENV{PYATS_R02_ENABLE_PASSWORD}'}}},
        'devices': {'R1': {'os': 'iosxe', 'platform': 'iol', 'type': 'router', 'connections': {
            'defaults': {'class': 'unicon.Unicon'},
            'ssh': {'protocol': 'ssh', 'ip': '192.0.2.201', 'port': 22,
                    'ssh_options': docker_prefix() + str(known_hosts)}}}}}


def docker_prefix():
    return '-F /dev/null -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile='


def pyats_config(tmp_path, **changes):
    """A complete, file-backed pyats binding (nothing is launched: the python is only hashed)."""
    import yaml
    root = tmp_path.resolve()
    source = root / 'upstream'
    source.mkdir()
    contents = {name: ('# synthetic ' + name + '\n').encode() for name in
                ('pyats_mcp_server.py', 'pyats_testbed_builder.py', 'pyats_tasks.py')}
    for name, raw in contents.items():
        (source / name).write_bytes(raw)
        (source / name).chmod(0o644)
    venv = root / 'venv'
    (venv / 'bin').mkdir(parents=True)
    (venv / 'pyvenv.cfg').write_text('home = /usr/bin\ninclude-system-site-packages = false\n')
    # Pinned files must be owned by us (or root) and not group/world-writable, so the fixture sets its own
    # modes rather than inherit the umask (002 on many hosts), and points bin/python at a stub interpreter
    # it owns: the host interpreter (e.g. a CI tool cache) need not pass that check, and nothing runs it.
    (venv / 'pyvenv.cfg').chmod(0o644)
    interpreter = root / 'interpreter' / 'python3'
    interpreter.parent.mkdir()
    interpreter.write_bytes(b'#!/bin/sh\nexit 1\n')
    interpreter.chmod(0o755)
    (venv / 'bin/python').symlink_to(interpreter)
    known_hosts = root / 'known_hosts'
    known_hosts.write_bytes(b'192.0.2.201 ssh-rsa AAAAfixturepublickey\n')
    known_hosts.chmod(0o600)
    testbed = root / 'testbed.yaml'
    testbed.write_text(yaml.safe_dump(strict_document(known_hosts), sort_keys=False))
    testbed.chmod(0o600)
    credential = write_credentials(root / 'pyats-credential')
    manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in contents.items()}
    scripts = Path(runtime.__file__).resolve().parents[4] / 'scripts'
    config = {'python': str(venv / 'bin/python'), 'upstream': str(source / 'pyats_mcp_server.py'),
              'upstream_sha256': manifest['pyats_mcp_server.py'], 'source_sha256': manifest,
              'adapter_sha256': {name: hashlib.sha256((scripts / name).read_bytes()).hexdigest()
                                 for name in ('protected-tool-broker.py', 'lib/protected_pyats.py')},
              'testbed': str(testbed), 'testbed_sha256': hashlib.sha256(testbed.read_bytes()).hexdigest(),
              'known_hosts': str(known_hosts), 'known_hosts_sha256': hashlib.sha256(known_hosts.read_bytes()).hexdigest(),
              'endpoint_sha256': h('endpoint'), 'credential_env': sorted(runtime._PYATS_CREDENTIAL_NAMES),
              'credential_file': str(credential)}
    config.update(changes)
    return config


def unfreeze(path):
    for directory, dirs, files in os.walk(path):
        os.chmod(directory, 0o700)
        for name in files:
            p = Path(directory) / name
            if not p.is_symlink():
                os.chmod(p, 0o600)


# ------------------------------------------------------------------------------------------- runtime shape
def test_hosted_pyats_runtime_shape_is_accepted_and_neighbours_are_refused():
    shape = {key: None for key in docker._PYATS_HOSTED_FIELDS}
    shape['hosted'] = dict(HOSTED)
    assert docker.validate_runtime_fields(shape) == 'pyats'
    # The qualified R02 field set is untouched.
    assert docker.validate_runtime_fields({key: None for key in docker._RUNTIME_FIELDS}) == 'pyats'
    for extra in ('ollama', 'mcp', 'relay_transport', 'surprise'):
        with pytest.raises(RuntimeRefused, match='runtime_configuration_fields_refused'):
            docker.validate_runtime_fields({**shape, extra: None})
    with pytest.raises(RuntimeRefused):
        docker.validate_runtime_fields({k: v for k, v in shape.items() if k != 'pyats'})
    with pytest.raises(RuntimeRefused):  # an unreviewed hosted profile is still refused
        docker.validate_runtime_fields({**shape, 'hosted': dict(HOSTED, egress_host='example.com')})


@needs_mcp
def test_tool_contract_digest_is_unchanged_without_credential_file_and_binds_it_when_present(tmp_path):
    config = pyats_config(tmp_path)
    base = {k: v for k, v in config.items() if k != 'credential_file'}
    plain = docker.tool_contract_digest(base)
    bound = docker.tool_contract_digest(config)
    assert plain != bound and bound == docker.tool_contract_digest(dict(config))
    assert docker.tool_contract_digest(dict(config, credential_file=str(tmp_path / 'other' / 'pyats-credential'))) != bound
    for refused in (str(tmp_path / 'not-the-reviewed-name'), 'relative/pyats-credential', 123):
        with pytest.raises(RuntimeRefused, match='unsafe_credential_file'):
            docker.tool_contract_digest(dict(config, credential_file=refused))
    with pytest.raises(RuntimeRefused, match='pyats_configuration_fields_refused'):
        docker.tool_contract_digest(dict(config, surprise=1))
    with pytest.raises(RuntimeRefused, match='scoped_device_credentials_required'):
        docker.tool_contract_digest(dict(config, credential_env=['PYATS_R02_USERNAME']))


@needs_mcp
def test_revision_bindings_accept_the_hosted_pyats_runtime(tmp_path):
    """revision/tool bindings are computed over the real pyats config exactly as for the R02 path."""
    config = pyats_config(tmp_path)
    assert len(docker.tool_contract_digest(config)) == 64


# ------------------------------------------------------------------------------------ credential delivery
def test_credential_file_is_the_only_launcher_compatible_carrier(tmp_path, monkeypatch):
    for name in runtime._PYATS_CREDENTIAL_NAMES:
        monkeypatch.delenv(name, raising=False)
    config = pyats_config(tmp_path)
    assert runtime.pyats_credentials(config) == {'PYATS_R02_USERNAME': FAKE_USER, 'PYATS_R02_PASSWORD': FAKE_PASS,
                                                 'PYATS_R02_ENABLE_PASSWORD': FAKE_ENABLE}


def test_credential_file_refusals(tmp_path):
    base = pyats_config(tmp_path)
    path = Path(base['credential_file'])
    path.chmod(0o640)
    with pytest.raises(RuntimeRefused, match='unsafe_credential_file'):
        runtime.pyats_credentials(base)  # group-readable
    path.chmod(0o600)
    link = tmp_path / 'link-credential'
    link.symlink_to(path)
    with pytest.raises(RuntimeRefused, match='unsafe_credential_file'):
        runtime.pyats_credentials(dict(base, credential_file=str(link)))  # symlink path is not canonical
    for body, code in (('PYATS_R02_USERNAME=u\nPYATS_R02_PASSWORD=p\n', 'missing_scoped_device_credential'),
                       ('PYATS_R02_USERNAME=u\nPYATS_R02_PASSWORD=p\nPYATS_R02_ENABLE_PASSWORD=e\nEXTRA=1\n', 'unsafe_credential_file'),
                       ('PYATS_R02_USERNAME=u\nPYATS_R02_USERNAME=v\nPYATS_R02_PASSWORD=p\nPYATS_R02_ENABLE_PASSWORD=e\n', 'unsafe_credential_file'),
                       ('PYATS_R02_USERNAME=\nPYATS_R02_PASSWORD=p\nPYATS_R02_ENABLE_PASSWORD=e\n', 'unsafe_credential_file'),
                       ('not a pair\n', 'unsafe_credential_file')):
        bad = tmp_path / ('bad-' + code + str(len(body)))
        bad.write_text(body)
        bad.chmod(0o600)
        with pytest.raises(RuntimeRefused, match=code):
            runtime.pyats_credentials(dict(base, credential_file=str(bad)))
    with pytest.raises(RuntimeRefused, match='unsafe_credential_file'):
        runtime.pyats_credentials(dict(base, credential_file=str(tmp_path / 'missing' / 'pyats-credential')))  # absent: FileNotFound refused fail-closed


def test_original_environment_only_behaviour_is_unchanged(tmp_path, monkeypatch):
    config = {k: v for k, v in pyats_config(tmp_path).items() if k != 'credential_file'}
    for name in runtime._PYATS_CREDENTIAL_NAMES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeRefused, match='missing_scoped_device_credential'):
        runtime.pyats_credentials(config)
    for name, value in zip(runtime._PYATS_CREDENTIAL_NAMES, ('a', 'b', 'c')):
        monkeypatch.setenv(name, value)
    assert runtime.pyats_credentials(config) == dict(zip(runtime._PYATS_CREDENTIAL_NAMES, ('a', 'b', 'c')))


# ------------------------------------------------------------------------------------------ wrong command
@pytest.mark.parametrize('changed', [{'command': 'show running-config'}, {'command': 'show version | include x'},
                                     {'retries': 2}, {'timeout': 0}, {'timeout': 301}])
def test_catalog_and_contract_refuse_any_other_command_or_policy(changed):
    arguments = dict(ARGUMENTS, **changed)
    with pytest.raises(contract.ProtectedError, match='unsupported_tool_policy'):
        contract.validate_tool_arguments('pyats_run_show_command', arguments)


def test_child_side_validator_also_refuses_a_changed_command():
    child = REPO / 'scripts/lib'
    sys.path.insert(0, str(child))
    try:
        import protected_pyats as adapter
    finally:
        sys.path.remove(str(child))
    adapter.validate_arguments(ARGUMENTS)
    for changed in ({'command': 'show running-config'}, {'retries': 2}, {'device_name': ''}):
        with pytest.raises(adapter.ProtectedPyatsRefused):
            adapter.validate_arguments(dict(ARGUMENTS, **changed))


def test_exact_tool_broker_refuses_changed_arguments_and_a_second_claim():
    effects = []

    async def gate(approved, effect):
        effects.append('gate')
        return await effect()

    async def invoke(tool, arguments):
        effects.append('invoke')
        return {'ok': True}

    payload = {'tool_call': {'tool': 'pyats_run_show_command', 'arguments': dict(ARGUMENTS)}}
    broker = ExactToolBroker(payload, gate, invoke)
    with pytest.raises(RuntimeRefused, match='tool_arguments_changed'):
        asyncio.run(broker.call('pyats_run_show_command', dict(ARGUMENTS, command='show running-config')))
    with pytest.raises(RuntimeRefused, match='tool_arguments_changed'):
        asyncio.run(broker.call('some_other_tool', dict(ARGUMENTS)))
    assert effects == []  # nothing reached the gate or the effect
    assert asyncio.run(broker.call('pyats_run_show_command', dict(ARGUMENTS))) == {'ok': True}
    with pytest.raises(RuntimeRefused, match='tool_already_claimed'):
        asyncio.run(broker.call('pyats_run_show_command', dict(ARGUMENTS)))
    assert effects == ['gate', 'invoke']


# ------------------------------------------------------------- invoke_pyats under HA (needs the mcp SDK)
class FakeSession:
    calls = []
    instances = 0

    def __init__(self, reader, writer, *a, **k):
        FakeSession.instances += 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def initialize(self):
        return None

    async def call_tool(self, name, arguments):
        FakeSession.calls.append((name, dict(arguments)))
        return types.SimpleNamespace(is_error=False, content=[], structured_content={
            'status': 'completed', 'device': arguments['device_name'], 'command': arguments['command'],
            'output': 'fixture version output', 'raw_output': 'fixture version output', 'execute_calls': 1})


@pytest.fixture
def fake_transports(monkeypatch):
    mcp = pytest.importorskip('mcp')
    import mcp.client.stdio as stock
    from bgp.federation.ha import mcp_transport
    used = []
    FakeSession.calls, FakeSession.instances = [], 0

    @asynccontextmanager
    async def fake_stock(params, errlog=None, **k):
        used.append('stock')
        yield 'reader', 'writer'

    @asynccontextmanager
    async def fake_ha(params, errlog=None, **k):
        used.append('ha')
        yield 'reader', 'writer'

    monkeypatch.setattr(stock, 'stdio_client', fake_stock)
    monkeypatch.setattr(mcp_transport, 'ha_stdio_client', fake_ha)
    monkeypatch.setattr(mcp, 'ClientSession', FakeSession)
    return used


def run_invoke(config, operation, **kwargs):
    return asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation, **kwargs))


def test_ha_admission_wraps_the_one_call_and_uses_the_ha_transport(tmp_path, fake_transports):
    config = pyats_config(tmp_path)
    operation = tmp_path / 'operation'
    order = []

    async def admission(call):
        order.append(('admission-entered', len(FakeSession.calls)))
        result = await call()
        order.append(('admission-left', len(FakeSession.calls)))
        return result

    try:
        evidence = run_invoke(config, operation, ha_required=True, ha_admission=admission)
        assert order == [('admission-entered', 0), ('admission-left', 1)]  # the tool call happens inside, after, admission
        assert fake_transports == ['ha'] and FakeSession.calls == [('pyats_run_show_command', ARGUMENTS)]
        assert evidence['execute_calls'] == 1 and evidence['output'] == 'fixture version output'
        intent = json.loads((operation / 'pyats-call.json').read_text())
        assert intent['state'] == 'intent_prepared' and intent['arguments'] == ARGUMENTS
        assert json.loads((operation / 'tool-evidence.json').read_text()) == evidence
        # the device credentials never touch the operation files or evidence
        for path in operation.rglob('*'):
            if path.is_file():
                data = path.read_bytes()
                assert not any(secret.encode() in data for secret in (FAKE_USER, FAKE_PASS, FAKE_ENABLE)), path
    finally:
        unfreeze(operation)


def test_no_admission_means_no_tool_call(tmp_path, fake_transports):
    config = pyats_config(tmp_path)
    operation = tmp_path / 'operation'
    try:
        with pytest.raises(RuntimeRefused, match='ha_runtime_unqualified'):
            run_invoke(config, operation, ha_required=True)  # HA required but no admission supplied
        assert fake_transports == [] and FakeSession.calls == [] and not operation.exists()

        async def refused(call):
            raise HAError('admission_expired', 409)

        with pytest.raises(HAError, match='admission_expired'):
            run_invoke(config, tmp_path / 'operation2', ha_required=True, ha_admission=refused)
        assert FakeSession.calls == []  # a refused/expired admission never reaches the device
    finally:
        unfreeze(tmp_path / 'operation2')


def test_replay_into_the_same_operation_is_refused_and_never_calls_twice(tmp_path, fake_transports):
    config = pyats_config(tmp_path)
    operation = tmp_path / 'operation'

    async def admission(call):
        return await call()

    try:
        run_invoke(config, operation, ha_required=True, ha_admission=admission)
        assert len(FakeSession.calls) == 1
        with pytest.raises(Exception):
            run_invoke(config, operation, ha_required=True, ha_admission=admission)  # create-only files: spent
        assert len(FakeSession.calls) == 1
    finally:
        unfreeze(operation)


def test_original_r02_path_is_unchanged_without_ha(tmp_path, fake_transports, monkeypatch):
    config = {k: v for k, v in pyats_config(tmp_path).items() if k != 'credential_file'}
    for name, value in zip(runtime._PYATS_CREDENTIAL_NAMES, ('a', 'b', 'c')):
        monkeypatch.setenv(name, value)
    operation = tmp_path / 'operation'
    try:
        evidence = run_invoke(config, operation)
        assert fake_transports == ['stock'] and len(FakeSession.calls) == 1
        assert not (operation / 'pyats-call.json').exists() and evidence['execute_calls'] == 1
    finally:
        unfreeze(operation)


def test_a_wrong_known_hosts_binding_refuses_before_any_child(tmp_path, fake_transports):
    config = pyats_config(tmp_path)
    Path(config['known_hosts']).write_bytes(b'192.0.2.201 ssh-rsa AAAAchangedkey\n')

    async def admission(call):
        return await call()

    with pytest.raises(RuntimeRefused, match='known_hosts_changed'):
        run_invoke(config, tmp_path / 'operation', ha_required=True, ha_admission=admission)
    assert fake_transports == [] and FakeSession.calls == []
    unfreeze(tmp_path / 'operation')


# --------------------------------------------------------------------------------------- builder flavor
from labs.ha import r09_member as m  # noqa: E402
from labs.ha import r09_prepare  # noqa: E402

HAVE_LOCAL = (m.R04A.joinpath('venv/bin/python').exists() and m.R05.joinpath('runtime-template.json').exists()
              and m.R02_PYATS_RUNTIME.joinpath('bin/python').exists())
local_only = pytest.mark.skipif(not HAVE_LOCAL, reason='owner R02/R04A/R05 local artifacts not present')
FAKE_PROVIDER_KEY = 'sk-ant-api03-FIXTURE-not-a-real-key-0000000000'


@pytest.fixture
def deployment(tmp_path):
    root = tmp_path.resolve() / 'deploy'
    args = types.SimpleNamespace(root=str(root), organization='nc182-test', days=7, node=[
        'nne1=10.182.1.2,34.19.206.228', 'ew1=10.182.2.2,35.240.68.169', 'ase1=10.182.3.2,34.21.206.125'])
    r09_prepare.prepare(args)
    yield root
    unfreeze(root)


def owner_testbed(tmp_path):
    import yaml
    path = tmp_path.resolve() / 'owner-testbed.yaml'
    path.write_text(yaml.safe_dump({'testbed': {'name': 'owner', 'credentials': {
        'default': {'username': FAKE_USER, 'password': FAKE_PASS}, 'enable': {'password': FAKE_ENABLE}}},
        'devices': {'R1': {'os': 'iosxe', 'platform': 'iol', 'type': 'router', 'connections': {
            'defaults': {}, 'ssh': {'protocol': 'ssh', 'ip': '192.0.2.201', 'port': 22}}}}}))
    return path


def artifact_args(root, tmp_path, **changes):
    values = dict(root=str(root), template=None, netbox_url=None, hosted_model=m.HOSTED_MODEL, guard_image=None,
                  pyats_testbed=str(owner_testbed(tmp_path)), known_hosts_file=None)
    values.update(changes)
    return types.SimpleNamespace(**values)


def test_pyats_flavor_is_registered_and_steps_refuse_other_flavors(tmp_path, deployment):
    assert 'pyats' in m.FLAVORS
    root = tmp_path.resolve() / 'member'
    result = m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7, flavor='pyats'))
    try:
        assert result['member']['member_id'].startswith('nc182-r09/pyats-') and result['flavor'] == 'pyats'
        with pytest.raises(m.MemberRefused, match='freeze_first'):
            m.cmd_artifacts(artifact_args(root, tmp_path))
        other = tmp_path.resolve() / 'other'
        m.cmd_identity(types.SimpleNamespace(root=str(other), deployment=str(deployment), days=7, flavor='netbox'))
        with pytest.raises(m.MemberRefused, match='pyats_flavor_required'):
            m.cmd_pyats_env(types.SimpleNamespace(root=str(other), env=None, device='R1'))
    finally:
        unfreeze(root)
        unfreeze(tmp_path.resolve() / 'other')


def test_pyats_closure_adds_exactly_the_broker_and_adapter_and_other_flavors_do_not():
    base = set(m.closure_files())
    pyats = set(m.closure_files('pyats'))
    assert pyats - base == set(m.PYATS_CLOSURE_EXTRA) and base <= pyats
    assert set(m.closure_files('netbox')) == base and set(m.closure_files('ollama')) == base


def test_testbed_credentials_reader_never_returns_values_into_state_and_refuses_gaps(tmp_path):
    document, user, password, enable = m.read_testbed_credentials(owner_testbed(tmp_path), 'R1')
    assert (user, password, enable) == (FAKE_USER, FAKE_PASS, FAKE_ENABLE) and 'R1' in document['devices']
    import yaml
    gap = tmp_path / 'gap.yaml'
    gap.write_text(yaml.safe_dump({'testbed': {'credentials': {'default': {'username': 'u', 'password': 'p'}}},
                                   'devices': {'R1': {'connections': {}}}}))
    with pytest.raises(m.MemberRefused, match='pyats_testbed_credentials_missing'):
        m.read_testbed_credentials(gap, 'R1')
    with pytest.raises(m.MemberRefused, match='pyats_device_missing'):
        m.read_testbed_credentials(owner_testbed(tmp_path), 'R9')


@needs_mcp
@local_only
def test_pyats_flavor_full_offline_pipeline_validates_and_keeps_credentials_in_two_files(tmp_path, deployment, monkeypatch):
    pytest.importorskip('yaml')
    root = tmp_path.resolve() / 'member'
    monkeypatch.setenv('ANTHROPIC_API_KEY', FAKE_PROVIDER_KEY)
    known = tmp_path.resolve() / 'kh-scan'
    known.write_bytes(b'192.0.2.201 ssh-rsa AAAAfixturepublickey\n')
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7, flavor='pyats'))
    try:
        frozen = m.cmd_freeze(types.SimpleNamespace(root=str(root)))
        assert (root / 'source/scripts/protected-tool-broker.py').is_file() and (root / 'source/scripts/lib/protected_pyats.py').is_file()
        m.cmd_python_env(types.SimpleNamespace(root=str(root), env=None, env_manifest=None, build=False, yes_network=False))
        recorded = m.cmd_pyats_env(types.SimpleNamespace(root=str(root), env=None, device='R1'))
        assert recorded['native_policy'] == 'pass' and recorded['environment'] == str(m.R02_PYATS_RUNTIME.resolve())
        artifacts = m.cmd_artifacts(artifact_args(root, tmp_path, known_hosts_file=str(known)))
        assert artifacts['device']['host'] == '192.0.2.201' and artifacts['device']['platform'] == 'iol'
        for secret in (FAKE_PROVIDER_KEY, FAKE_USER, FAKE_PASS, FAKE_ENABLE):
            assert secret not in json.dumps(artifacts)
        m.cmd_materialize(types.SimpleNamespace(root=str(root)))
        result = m.cmd_validate(types.SimpleNamespace(root=str(root), skip_import_check=False))
        assert result['role_validate'] == 'valid' and result['control_only'] is False and result['closure_import'] == 'ok'
        federation = root / 'home/netclaw-federation'
        profile = json.loads((federation / 'protected-profile.json').read_text())
        rt = profile['runtime']
        assert set(rt) == set(docker._PYATS_HOSTED_FIELDS) and 'ollama' not in rt and 'mcp' not in rt
        assert rt['hosted']['model'] == m.HOSTED_MODEL and rt['pyats']['credential_file'] == str(root / 'artifacts/pyats-credential')
        tool = profile['catalog']['tools'][0]
        assert tool['tool'] == 'pyats_run_show_command' and tool['arguments'] == dict(m.PYATS_ARGUMENTS)
        assert tool['inventory_revision'] == rt['pyats']['testbed_sha256'] and tool['endpoint_sha256'] == rt['pyats']['endpoint_sha256']
        assert tool['limits']['tool_timeout_ms'] == 120000
        contract.validate_catalog_entry(profile['catalog'])
        # The reviewed testbed carries only credential REFERENCES; real values live in exactly two private files.
        assert '%ENV{PYATS_R02_PASSWORD}' in (root / 'artifacts/testbed.yaml').read_text()
        holders = set()
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                data = path.read_bytes()
                if any(secret.encode() in data for secret in (FAKE_PROVIDER_KEY, FAKE_USER, FAKE_PASS, FAKE_ENABLE)):
                    holders.add(str(path.relative_to(root)))
                    assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert holders == {'artifacts/guard.env', 'artifacts/pyats-credential'}
        # the signed endpoint pins the strict host key policy and the exact known_hosts bytes
        known_sha = m.sha((root / 'artifacts/known_hosts').read_bytes())
        assert known_sha == rt['pyats']['known_hosts_sha256'] == artifacts['known_hosts_sha256']
        contract_doc = json.loads((root / 'contract.json').read_text())
        assert contract_doc['environment']['BGP_API_PORT'] == '18191' and contract_doc['control_only'] is False
        assert frozen['source_files'] == len(m.closure_files('pyats')) and not (root / 'model').exists()
    finally:
        unfreeze(root)


@local_only
def test_pyats_env_refuses_an_environment_that_is_not_the_pinned_one(tmp_path, deployment):
    root = tmp_path.resolve() / 'member'
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7, flavor='pyats'))
    try:
        with pytest.raises(m.MemberRefused):
            m.cmd_pyats_env(types.SimpleNamespace(root=str(root), env=str(m.R04A / 'venv'), device='R1'))  # no upstream, no pyats 25.2
    finally:
        unfreeze(root)
