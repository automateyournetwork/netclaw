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
