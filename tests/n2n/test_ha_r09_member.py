"""R09 member builder (labs/ha/r09_member.py): offline, no Docker, no model, no process start.

Run: <python3.10 venv with cryptography/pyOpenSSL/service-identity/httpx>/bin/python -m pytest tests/n2n/test_ha_r09_member.py
Tests needing the owner's R04A/R05 local artifacts are skipped when those are absent.
"""
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import types

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'mcp-servers/protocol-mcp'))

from labs.ha import r09_member as m  # noqa: E402
from labs.ha import r09_prepare  # noqa: E402

HAVE_LOCAL = m.R04A.joinpath('venv/bin/python').exists() and m.R05.joinpath('runtime-template.json').exists()
local_only = pytest.mark.skipif(not HAVE_LOCAL, reason='owner R04A/R05 local artifacts not present')


def unfreeze(path):
    for directory, dirs, files in os.walk(path):
        os.chmod(directory, 0o700)
        for name in files:
            p = Path(directory) / name
            if not p.is_symlink():
                os.chmod(p, 0o600)


@pytest.fixture
def deployment(tmp_path):
    """A real signed three-Border deployment generated offline by the Border prepare tool."""
    root = tmp_path.resolve() / 'deploy'
    args = types.SimpleNamespace(root=str(root), organization='nc182-test', days=7, node=[
        'nne1=10.182.1.2,34.19.206.228', 'ew1=10.182.2.2,35.240.68.169', 'ase1=10.182.3.2,34.21.206.125'])
    r09_prepare.prepare(args)
    yield root
    unfreeze(root)


@pytest.fixture
def member_root(tmp_path, deployment):
    root = tmp_path.resolve() / 'member'
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7))
    yield root
    unfreeze(root)


def test_canonical_and_private_files(tmp_path):
    raw = m.canonical({'b': 1, 'a': [1, 'é']})
    assert raw == '{"a":[1,"é"],"b":1}'.encode()
    target = tmp_path / 'f'
    digest = m.write_private(target, {'x': 1})
    assert digest == m.sha(target.read_bytes()) and stat.S_IMODE(target.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        m.write_private(target, {'x': 2})  # create-only, never overwritten


def test_closure_is_closed_and_has_required_files():
    files = m.closure_files()
    required = {'scripts/federation-control.py', 'scripts/protected-role.py', 'scripts/lib/protected_role.py',
                'mcp-servers/protocol-mcp/bgp-daemon-v2.py', 'mcp-servers/protocol-mcp/bgp/federation/endpoint_registry.py',
                'mcp-servers/protocol-mcp/bgp/federation/runtime.py', 'labs/ollama/qualify.py'}
    assert required <= files.keys()
    for name in ('factory', 'config', 'authority', 'channel', 'internal', 'member', 'border', 'operations', 'admission',
                 'store', 'effect', 'mcp_transport', 'model_transport'):
        assert f'mcp-servers/protocol-mcp/bgp/federation/ha/{name}.py' in files
    assert not any('/tests/' in name or name.endswith(('.pyc', '.md')) or '__pycache__' in name for name in files)
    assert not any(name.endswith(('root.key', '.key')) for name in files)
    assert 100 <= len(files) <= 200


def test_identity_uses_only_public_anchor_and_pins_cluster(member_root, deployment):
    # The offline enrollment key must never be needed or read: make it unreadable.
    os.chmod(deployment / 'identity/root.key', 0)
    state = json.loads((member_root / 'state.json').read_text())
    binding = state['binding']
    packet = json.loads((member_root / 'identity/member.json').read_text())
    assert packet['binding'] == binding and packet['certificate'].startswith('-----BEGIN CERTIFICATE-----')
    assert set(binding) == {'installation_id', 'member_id', 'key_id', 'enrollment_generation'}
    manifest = json.loads((deployment / 'identity/manifest.json').read_text())['manifest']
    assert all(binding['installation_id'] != n['installation_id'] and binding['key_id'] != n['key_id']
               for n in manifest['nodes'])
    assert state['name'].startswith('netclaw-r08-r09m-')
    for name in ('manifest.json', 'root.crt', 'transport-ca.crt'):
        assert stat.S_IMODE((member_root / 'cluster' / name).stat().st_mode) == 0o600
    assert not (member_root / 'cluster/root.key').exists()
    assert stat.S_IMODE((member_root / 'identity/member.key').stat().st_mode) == 0o600


def test_identity_refuses_existing_root(member_root, deployment):
    with pytest.raises(SystemExit):
        m.cmd_identity(types.SimpleNamespace(root=str(member_root), deployment=str(deployment), days=7))


def test_outbound_dial_comes_from_signed_manifest_only(member_root, deployment):
    manifest = json.loads((deployment / 'identity/manifest.json').read_text())['manifest']
    expected = [(n['endpoints']['in2n']['host'], n['endpoints']['in2n']['port'], n['endpoints']['in2n']['server_name'])
                for n in manifest['nodes']]
    assert [e[1] for e in expected] == [7444, 7444, 7444]
    assert all(e[2].endswith('.automateyournetwork.com') for e in expected)


def test_freeze_is_read_only_manifested_and_exact(member_root):
    result = m.cmd_freeze(types.SimpleNamespace(root=str(member_root)))
    source = member_root / 'source'
    manifest = json.loads((member_root / 'source-manifest.json').read_text())
    assert result['source_files'] == len(manifest['files']) == len(m.closure_files())
    on_disk = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    assert on_disk == set(manifest['files'])
    assert all(not p.stat().st_mode & 0o222 for p in source.rglob('*'))
    assert m.sha((member_root / 'source-manifest.json').read_bytes()) == result['source_manifest_sha256']
    with pytest.raises(SystemExit):
        m.cmd_freeze(types.SimpleNamespace(root=str(member_root)))  # one-shot


def fake_env(root):
    """Immutable env shaped like R04A: root-owned-by-me, no write bits, python links to a read-only copy."""
    native = root / 'native'
    native.mkdir(mode=0o700, parents=True)
    interpreter = native / 'python3.12'
    shutil.copyfile(Path(sys.executable).resolve(), interpreter)
    os.chmod(interpreter, 0o500)
    venv = root / 'venv'
    (venv / 'bin').mkdir(parents=True)
    (venv / 'lib').mkdir()
    (venv / 'pyvenv.cfg').write_text('home = /x\ninclude-system-site-packages = false\n')
    (venv / 'lib/dummy.py').write_text('X = 1\n')
    (venv / 'bin/python').symlink_to(interpreter)
    for name in ('python3', 'python3.12'):
        (venv / 'bin' / name).symlink_to('python')
    for directory, _, names in os.walk(venv, topdown=False):
        for name in names:
            p = Path(directory) / name
            if not p.is_symlink():
                os.chmod(p, 0o400)
        os.chmod(directory, 0o500)
    os.chmod(native, 0o500)
    return venv, interpreter


def test_env_manifest_verifies_and_detects_change(tmp_path):
    venv, interpreter = fake_env(tmp_path.resolve() / 'env')
    try:
        manifest = m.env_manifest(venv)
        assert 'pyvenv.cfg' in manifest['files'] and set(manifest['symlinks']) == {'bin/python', 'bin/python3', 'bin/python3.12'}
        raw = m.canonical(manifest)
        manifest_file = tmp_path.resolve() / 'env-manifest.json'
        m.write_private(manifest_file, raw)
        py_sha = m.sha(interpreter.read_bytes())
        m.verify_env(venv / 'bin/python', venv, manifest_file, m.sha(raw), py_sha)
        with pytest.raises(m.role_module().RoleRefused):
            m.verify_env(venv / 'bin/python', venv, manifest_file, '0' * 64, py_sha)
        os.chmod(venv / 'lib', 0o700)
        os.chmod(venv / 'lib/dummy.py', 0o600)
        (venv / 'lib/dummy.py').write_text('X = 2\n')
        os.chmod(venv / 'lib/dummy.py', 0o400); os.chmod(venv / 'lib', 0o500)
        with pytest.raises(m.role_module().RoleRefused):
            m.verify_env(venv / 'bin/python', venv, manifest_file, m.sha(raw), py_sha)
    finally:
        unfreeze(tmp_path / 'env')


def test_plan_orders_enrollment_before_member_start():
    steps = [s['step'] for s in m.cmd_plan(None)['order']]
    assert steps.index(next(s for s in steps if s.startswith('ENROLL'))) < steps.index(next(s for s in steps if s.startswith('start the member')))
    assert any('qualify.py' in s for s in steps)


@local_only
def test_full_offline_pipeline_validates_with_production_validator(tmp_path, deployment, monkeypatch):
    """identity -> freeze -> python-env(R04A) -> artifacts -> (fake model profile) -> materialize -> validate."""
    root = tmp_path.resolve() / 'member'
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7))
    try:
        m.cmd_freeze(types.SimpleNamespace(root=str(root)))
        m.cmd_python_env(types.SimpleNamespace(root=str(root), env=None, env_manifest=None, build=False, yes_network=False))
        # Avoid copying 500 MB: stub the copy + store verification, everything else is the real code path.
        from labs.ha import real_runtime
        def small_copy(source, destination):
            Path(destination).mkdir(mode=0o700)
        monkeypatch.setattr(real_runtime, 'copy_model_store', small_copy)
        from bgp.federation import protected_ollama
        monkeypatch.setattr(protected_ollama, 'verify_store', lambda profile: None)
        artifacts = m.cmd_artifacts(types.SimpleNamespace(root=str(root), template=None))
        assert artifacts['model_start_command_owner_runs'][2].endswith('source/labs/ollama/qualify.py')
        template = json.loads((m.R05 / 'runtime-template.json').read_text())
        profile = dict(template['runtime']['ollama'], model_store=str(root / 'artifacts/models'))
        (root / 'model').mkdir(mode=0o700)
        m.write_private(root / 'model/profile.json', profile)
        m.cmd_materialize(types.SimpleNamespace(root=str(root)))
        result = m.cmd_validate(types.SimpleNamespace(root=str(root), skip_import_check=False))
        assert result['role_validate'] == 'valid' and result['control_only'] is False
        assert result['closure_import'] == 'ok'
        federation = root / 'home/netclaw-federation'
        contract = json.loads((root / 'contract.json').read_text())
        # Hash-pinned files are canonical bytes and match their pins exactly.
        for path in (federation / 'ha-config.json', federation / 'protected-profile.json', root / 'contract.json',
                     root / 'source-manifest.json'):
            raw = path.read_bytes()
            assert raw == m.canonical(json.loads(raw))
        profile_doc = json.loads((federation / 'protected-profile.json').read_text())
        assert m.sha((federation / 'protected-profile.json').read_bytes()) == contract['profile_sha256']
        assert m.sha((federation / 'ha-config.json').read_bytes()) == profile_doc['ha']['config_sha256']
        config = json.loads((federation / 'ha-config.json').read_text())
        assert set(config) == {'schema_version', 'role', 'manifest_file', 'anchor_certificate_file', 'anchor_key_id',
                               'transport_ca_file', 'certificate_file', 'private_key_file'}
        assert 'etcd' not in config and 'node_id' not in config  # a member holds no consensus credential
        assert contract['origin'] is None and contract['control_only'] is False
        assert 'N2N_EDGE_WS_PORT' not in contract['environment']
        paths = [v for v in config.values() if isinstance(v, str) and v.startswith('/')]
        paths += [contract[k] for k in ('home', 'source_root', 'source_manifest', 'python_env_manifest', 'guard_token_file')]
        assert all(Path(p).resolve() == Path(p) for p in paths)
        assert not [p for p in root.rglob('*') if p.is_symlink()]
        assert profile_doc['catalog']['tools'][0]['limits']['max_output_bytes'] == 262144
        assert profile_doc['runtime']['guard_token_env'] == m.GUARD_TOKEN_ENV
        # The guard capability is the exact 43-char token in the member home and the guard env file.
        token = (federation / 'guard-capability').read_text()
        assert len(token) == 43 and (root / 'artifacts/guard.env').read_text() == f'{m.GUARD_ENV_VARIABLE}={token}\n'
    finally:
        unfreeze(root)


# ======================================================================================= NetBox flavor (spec 182)
import importlib.util  # noqa: E402

FAKE_PROVIDER_KEY = 'sk-ant-api03-FIXTURE-not-a-real-key-0000000000'
FAKE_NETBOX_TOKEN = 'nbt_fixture.tokenvalue0001'
OLLAMA_GUARD_CONFIG = """config_version: 9
data_dir: /guard
deployment_mode: server
gateway:
  api_bind: 127.0.0.1
  api_port: 18970
guardrail:
  allow_empty_providers: false
  allow_unknown_llm_domains: false
  connector: openclaw
  enabled: true
  host: 0.0.0.0
  llm:
    forward_custom_headers: false
    model: ollama/qwen3:0.6b
  mode: action
  model: ollama/qwen3:0.6b
  model_name: qwen3:0.6b
  port: 4000
llm:
  forward_custom_headers: false
  model: ollama/qwen3:0.6b
"""


def guard_module():
    sys.path.insert(0, str(REPO / 'scripts/lib'))
    spec = importlib.util.spec_from_file_location('r09_test_protected_guard', REPO / 'scripts/protected-guard.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_secret_from_environment_names_the_variable_and_never_the_value():
    assert m.secret_from_environment('K', {'K': 'abcdefgh12'}) == 'abcdefgh12'
    for value in (None, '', 'short', 'has space1', 'new\nline1234', ' lead12345', 'é' * 12, 'x' * 5000):
        with pytest.raises(m.MemberRefused) as caught:
            m.secret_from_environment('SECRET_NAME', {'SECRET_NAME': value} if value is not None else {})
        assert 'SECRET_NAME' in str(caught.value) and (value is None or value not in str(caught.value) or value == '')


qualified_only = pytest.mark.skipif(not m.QUALIFIED_GUARD_CONFIG.is_file(), reason='R04A qualified guard config not present')


@qualified_only
def test_hosted_guard_config_is_the_qualified_anthropic_file_verbatim():
    yaml = pytest.importorskip('yaml')
    raw = m.load_qualified_guard_config()
    derived = m.hosted_guard_config(raw, m.QUALIFIED_GUARD_MODEL)
    assert derived == raw and m.sha(derived) == m.QUALIFIED_GUARD_CONFIG_SHA256
    config = yaml.safe_load(derived)
    guardrail = config['guardrail']
    # The shape the real guard accepted; the Ollama-derived config lacked these and was answered with
    # `provider "" is not supported by DefenseClaw guardrail - traffic blocked`.
    assert guardrail['llm_role'] == 'judge_and_agent'
    assert guardrail.get('allow_empty_providers') is not False and guardrail.get('allow_unknown_llm_domains') is not False
    route = {'model': 'anthropic/claude-sonnet-4-6', 'api_key_env': 'DEFENSECLAW_LLM_KEY',
             'base_url': 'http://127.0.0.1:18888', 'forward_custom_headers': False}
    assert config['llm'] == route and guardrail['llm'] == route
    assert guardrail['model'] == 'anthropic/claude-sonnet-4-6' and guardrail['api_key_env'] == 'DEFENSECLAW_LLM_KEY'
    assert guardrail['mode'] == 'action' and guardrail['connector'] == 'openclaw' and guardrail['port'] == 4000
    assert config['gateway'] == {'api_bind': '127.0.0.1', 'api_port': m.HOSTED_GUARD_API_PORT, 'fleet_mode': 'disabled',
                                 'token_env': 'DEFENSECLAW_GATEWAY_TOKEN'} and m.HOSTED_GUARD_API_PORT == 4001
    assert config['ai_discovery'] == {'enabled': False} and config['data_dir'] == '/guard'
    text = derived.decode()
    assert 'ollama' not in text and 'qwen' not in text and FAKE_PROVIDER_KEY not in text and 'api_key:' not in text


@qualified_only
def test_hosted_guard_config_satisfies_the_guard_runners_own_verifier(tmp_path):
    guard = guard_module()
    from protected_provider import MODEL as guard_model
    raw = m.hosted_guard_config(m.load_qualified_guard_config(), guard_model)
    assert m.QUALIFIED_GUARD_MODEL == m.HOSTED_MODEL == guard_model  # the guard image pins this model
    home = tmp_path.resolve() / 'guardhome'
    home.mkdir(mode=0o700)
    raw = raw.replace(b'data_dir: /guard', b'data_dir: ' + str(home).encode())  # the verifier checks the real home path
    m.write_private(home / 'config.yaml', raw)
    assert guard.verify_config(home, m.sha(raw), FAKE_PROVIDER_KEY) == m.sha(raw)
    for broken in (raw.replace(b'base_url: http://127.0.0.1:18888', b'base_url: https://api.anthropic.com'),
                   raw.replace(b'api_key_env: DEFENSECLAW_LLM_KEY', b'api_key_env: ANTHROPIC_API_KEY'),
                   raw.replace(b'anthropic/' + guard_model.encode(), b'anthropic/claude-sonnet-5-5')):
        other = tmp_path / 'other'
        other.mkdir(mode=0o700, exist_ok=True)
        (other / 'config.yaml').unlink(missing_ok=True)
        m.write_private(other / 'config.yaml', broken)
        with pytest.raises(Exception):
            guard.verify_config(other, m.sha(broken), FAKE_PROVIDER_KEY)


@qualified_only
def test_qualified_guard_config_is_pinned_and_other_models_only_swap_the_model_string(tmp_path):
    raw = m.load_qualified_guard_config()
    other = m.hosted_guard_config(raw, 'claude-sonnet-5-5')
    assert other == raw.replace(b'anthropic/claude-sonnet-4-6', b'anthropic/claude-sonnet-5-5') and other != raw
    tampered = tmp_path / 'guard-config.yaml'
    tampered.write_bytes(raw + b'# changed\n')
    with pytest.raises(m.MemberRefused, match='qualified_guard_config_changed'):
        m.load_qualified_guard_config(tampered)
    with pytest.raises(m.MemberRefused, match='qualified_guard_config_missing'):
        m.load_qualified_guard_config(tmp_path / 'absent.yaml')


def test_the_ollama_derived_config_shape_can_never_be_selected():
    """The config shape the real guard answered with `provider "" is not supported` is refused by construction."""
    with pytest.raises(m.MemberRefused, match='guard_config_model_shape'):
        m.hosted_guard_config(OLLAMA_GUARD_CONFIG.encode(), m.HOSTED_MODEL)
    for broken in (b'api_key: inline\n', b'not yaml but has anthropic/claude-sonnet-4-6 x3'):
        with pytest.raises(m.MemberRefused):
            m.hosted_guard_config(broken, m.HOSTED_MODEL)


def test_hosted_guard_env_matches_the_guard_loader_and_stays_private(tmp_path):
    guard = guard_module()
    home = tmp_path.resolve()
    token = 'T' * 43
    m.write_hosted_guard_env(home / 'guard.env', FAKE_PROVIDER_KEY, token)
    assert stat.S_IMODE((home / 'guard.env').stat().st_mode) == 0o600
    assert guard.load_guard_env(home, local=False) == {'ANTHROPIC_API_KEY': FAKE_PROVIDER_KEY, 'DEFENSECLAW_GATEWAY_TOKEN': token}
    with pytest.raises(m.MemberRefused, match='distinct_guard_credentials_required'):
        m.write_hosted_guard_env(home / 'other.env', token, token)


def test_member_identity_flavor_is_recorded_and_default_is_unchanged(tmp_path, deployment):
    plain = tmp_path.resolve() / 'plain'
    box = tmp_path.resolve() / 'box'
    a = m.cmd_identity(types.SimpleNamespace(root=str(plain), deployment=str(deployment), days=7))
    b = m.cmd_identity(types.SimpleNamespace(root=str(box), deployment=str(deployment), days=7, flavor='netbox'))
    try:
        assert a['flavor'] == 'ollama' and a['member']['member_id'].startswith('nc182-r09/mac-subnet-')
        assert b['flavor'] == 'netbox' and b['member']['member_id'].startswith('nc182-r09/netbox-')
        assert json.loads((box / 'state.json').read_text())['flavor'] == 'netbox'
        with pytest.raises(m.MemberRefused, match='flavor_refused'):
            m.cmd_identity(types.SimpleNamespace(root=str(tmp_path.resolve() / 'x'), deployment=str(deployment), days=7, flavor='cml'))
    finally:
        unfreeze(plain); unfreeze(box)


def test_netbox_steps_refuse_the_calculator_flavor_and_missing_prerequisites(tmp_path, deployment):
    root = tmp_path.resolve() / 'plain'
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7))
    try:
        with pytest.raises(m.MemberRefused, match='netbox_flavor_required'):
            m.cmd_netbox_env(types.SimpleNamespace(root=str(root), env=None, build=False, yes_network=False))
    finally:
        unfreeze(root)
    box = tmp_path.resolve() / 'box'
    m.cmd_identity(types.SimpleNamespace(root=str(box), deployment=str(deployment), days=7, flavor='netbox'))
    try:
        with pytest.raises(m.MemberRefused, match='netbox_env_or_build_required'):
            m.cmd_netbox_env(types.SimpleNamespace(root=str(box), env=None, build=False, yes_network=False))
        with pytest.raises(m.MemberRefused, match='build_needs_--yes-network'):
            m.cmd_netbox_env(types.SimpleNamespace(root=str(box), env=None, build=True, yes_network=False))
        with pytest.raises(m.MemberRefused, match='freeze_first|python-env_first'):
            m.cmd_artifacts(types.SimpleNamespace(root=str(box), template=None, netbox_url=None, hosted_model=m.HOSTED_MODEL, guard_image=None))
    finally:
        unfreeze(box)


def fake_netbox_env(base):
    """A tiny immutable venv shaped like the real one (pyvenv.cfg, bin/python -> real interpreter, one module)."""
    venv = base / 'nbvenv'
    (venv / 'bin').mkdir(parents=True)
    (venv / 'lib').mkdir()
    (venv / 'pyvenv.cfg').write_text('home = /usr/bin\ninclude-system-site-packages = false\n')
    (venv / 'lib/marker.py').write_text('X = 1\n')
    (venv / 'bin/python').symlink_to(Path(sys.executable).resolve())
    for name in ('python3', 'python3.12'):
        (venv / 'bin' / name).symlink_to('python')
    for directory, _, names in os.walk(venv, topdown=False):
        for name in names:
            p = Path(directory) / name
            if not p.is_symlink():
                os.chmod(p, 0o400)
        os.chmod(directory, 0o500)
    return venv


@local_only
def test_netbox_flavor_full_offline_pipeline_validates_and_keeps_secrets_in_two_files(tmp_path, deployment, monkeypatch):
    pytest.importorskip('yaml')
    root = tmp_path.resolve() / 'member'
    monkeypatch.setenv('NETBOX_TOKEN', FAKE_NETBOX_TOKEN)
    monkeypatch.setenv('ANTHROPIC_API_KEY', FAKE_PROVIDER_KEY)
    monkeypatch.setenv('NETBOX_URL', 'https://demo.netbox.dev')
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7, flavor='netbox'))
    nb_env = fake_netbox_env(tmp_path.resolve())
    try:
        m.cmd_freeze(types.SimpleNamespace(root=str(root)))
        m.cmd_python_env(types.SimpleNamespace(root=str(root), env=None, env_manifest=None, build=False, yes_network=False))
        m.cmd_netbox_env(types.SimpleNamespace(root=str(root), env=str(nb_env), build=False, yes_network=False))
        monkeypatch.setattr(m, 'list_netbox_schema', lambda *a, **k: {'type': 'object', 'properties': {'object_type': {'type': 'string'}}})
        artifacts = m.cmd_artifacts(types.SimpleNamespace(root=str(root), template=None, netbox_url=None,
                                                          hosted_model=m.HOSTED_MODEL, guard_image=None))
        assert artifacts['hosted_model'] == m.HOSTED_MODEL and 'qualify' in artifacts['model_namespace']
        for secret in (FAKE_PROVIDER_KEY, FAKE_NETBOX_TOKEN):
            assert secret not in json.dumps(artifacts)
        m.cmd_materialize(types.SimpleNamespace(root=str(root)))
        result = m.cmd_validate(types.SimpleNamespace(root=str(root), skip_import_check=False))
        assert result['role_validate'] == 'valid' and result['control_only'] is False and result['closure_import'] == 'ok'
        federation = root / 'home/netclaw-federation'
        profile = json.loads((federation / 'protected-profile.json').read_text())
        runtime = profile['runtime']
        assert 'ollama' not in runtime and runtime['hosted']['model'] == m.HOSTED_MODEL and runtime['mcp']['kind'] == 'netbox'
        assert runtime['model_profile']['provider'] == 'anthropic' and runtime['mcp']['origin'] == 'https://demo.netbox.dev'
        tool = profile['catalog']['tools'][0]
        assert tool['tool'] == 'netbox_get_object_by_id' and tool['arguments'] == m.NETBOX_ARGUMENTS
        assert tool['endpoint_sha256'] == runtime['mcp']['endpoint_sha256'] and tool['inventory_revision'] == runtime['mcp']['selection_sha256']
        from bgp.federation import protected_contract as c
        c.validate_catalog_entry(profile['catalog'])
        # Credentials live in exactly two private files; nowhere else under the member root.
        holders = set()
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                data = path.read_bytes()
                if FAKE_PROVIDER_KEY.encode() in data or FAKE_NETBOX_TOKEN.encode() in data:
                    holders.add(str(path.relative_to(root)))
                    assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert holders == {'artifacts/guard.env', 'artifacts/netbox-credential'}
        assert (root / 'artifacts/netbox-credential').read_text() == 'NETBOX_TOKEN=' + FAKE_NETBOX_TOKEN + '\n'
        contract = json.loads((root / 'contract.json').read_text())
        assert contract['environment']['BGP_API_PORT'] == '18190' and contract['control_only'] is False
        assert not (root / 'model').exists()
    finally:
        unfreeze(root)
        unfreeze(nb_env)


@local_only
def test_netbox_artifacts_refuse_a_model_the_guard_image_does_not_pin(tmp_path, deployment, monkeypatch):
    root = tmp_path.resolve() / 'member'
    monkeypatch.setenv('NETBOX_TOKEN', FAKE_NETBOX_TOKEN)
    monkeypatch.setenv('ANTHROPIC_API_KEY', FAKE_PROVIDER_KEY)
    m.cmd_identity(types.SimpleNamespace(root=str(root), deployment=str(deployment), days=7, flavor='netbox'))
    nb_env = fake_netbox_env(tmp_path.resolve())
    try:
        m.cmd_freeze(types.SimpleNamespace(root=str(root)))
        m.cmd_python_env(types.SimpleNamespace(root=str(root), env=None, env_manifest=None, build=False, yes_network=False))
        m.cmd_netbox_env(types.SimpleNamespace(root=str(root), env=str(nb_env), build=False, yes_network=False))
        with pytest.raises(m.MemberRefused, match='model_needs_rebuilt_guard_image'):
            m.cmd_artifacts(types.SimpleNamespace(root=str(root), template=None, netbox_url='https://demo.netbox.dev',
                                                  hosted_model='claude-sonnet-5-5', guard_image=None))
        with pytest.raises(m.MemberRefused, match='hosted_model_refused'):
            m.cmd_artifacts(types.SimpleNamespace(root=str(root), template=None, netbox_url='https://demo.netbox.dev',
                                                  hosted_model='claude-opus-5-5', guard_image=None))
        with pytest.raises(Exception):
            m.cmd_artifacts(types.SimpleNamespace(root=str(root), template=None, netbox_url='http://demo.netbox.dev',
                                                  hosted_model=m.HOSTED_MODEL, guard_image=None))
        assert not (root / 'artifacts/guard.env').exists()  # refusals happen before any secret is written
    finally:
        unfreeze(root)
        unfreeze(nb_env)
