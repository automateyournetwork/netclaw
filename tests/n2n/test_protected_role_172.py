"""Role validation is non-mutating and never inherits ambient execution authority."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import uuid
from protected_support_171 import identity as signer

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('protected_role_172', ROOT / 'scripts/lib/protected_role.py')
role = importlib.util.module_from_spec(spec); spec.loader.exec_module(role)


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    raw = json.dumps(value, sort_keys=True).encode() if not isinstance(value, bytes) else value
    p.write_bytes(raw); p.chmod(0o600)
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def selected(tmp_path):
    base = tmp_path.resolve(); home = base / 'home'; home.mkdir(mode=0o700)
    installation = str(uuid.uuid4()); source = base / 'source'; source.mkdir()
    files = {}
    for name in ('scripts/federation-control.py', 'scripts/protected-role.py', 'scripts/lib/protected_role.py', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py',
                 'mcp-servers/protocol-mcp/bgp/federation/endpoint_registry.py', 'mcp-servers/protocol-mcp/bgp/federation/runtime.py'):
        p = source / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes() if name.endswith(('endpoint_registry.py', '/runtime.py')) else b'# frozen fixture\n'); p.chmod(0o444)
        files[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(source.rglob('*'), reverse=True):
        if p.is_dir(): p.chmod(0o555)
    source.chmod(0o555)
    manifest = base / 'manifest.json'; manifest_hash = write(manifest, {'schemaVersion': 1, 'files': files})
    venv = base / 'venv'; (venv / 'bin').mkdir(parents=True)
    python = venv / 'bin/python'; python.write_bytes(b'fixture-never-executed'); python.chmod(0o555)
    (venv / 'pyvenv.cfg').write_text('include-system-site-packages = false\n'); (venv / 'pyvenv.cfg').chmod(0o444)
    env_files = {str(p.relative_to(venv)): hashlib.sha256(p.read_bytes()).hexdigest() for p in venv.rglob('*') if p.is_file()}
    env_manifest = base / 'python-manifest.json'; env_hash = write(env_manifest, {'schemaVersion': 1, 'files': env_files, 'symlinks': {}})
    (venv / 'bin').chmod(0o555); venv.chmod(0o555)
    write(home / 'netclaw-hud/installation.json', {'schemaVersion': 1, 'installationId': installation})
    write(home / 'netclaw-federation/owner.json', {'schemaVersion': 1, 'installationId': installation, 'kind': 'openclaw', 'home': str(home)})
    keys = signer('r03-fixture/border')
    profile_hash = write(home / 'netclaw-federation/protected-profile.json', {'schemaVersion': 1, 'role': 'border', 'identity': {
        'installation_id': installation, 'identity': 'r03-fixture/border', 'key_id': keys['key_id'], 'authority_generation': 'generation-1'}})
    cert = home / 'tls.crt'; key = home / 'tls.key'
    write(cert, keys['cert_pem'].encode()); write(key, keys['key_pem'].encode())
    registry = home / 'netclaw-federation/endpoints.json'
    entries = []
    for index, service in enumerate(('in2n', 'en2n')):
        entries.append({'id': service, 'service': service, 'direction': 'listen', 'transport': 'direct_tcp',
                        'bind_host': '10.172.0.2' if index == 0 else '127.0.0.1', 'bind_port': 42102 + index,
                        'routing_host': '203.0.113.10' if index == 0 else '127.0.0.1', 'routing_port': 42102 + index,
                        'tls_server_name': 'r03.example.test', 'ca_file': str(cert), 'cert_file': str(cert), 'key_file': str(key),
                        'profile': 'in2n-tls-exporter-v1' if index == 0 else 'en2n-tls13-v1', 'address_ref': service,
                        'application_identity': 'r03-fixture/border', 'application_trust': keys['cert_pem'] if index == 0 else keys['key_id']})
    registry_hash = write(registry, {'schemaVersion': 2, 'installationId': installation, 'revision': 1, 'entries': entries})
    (home / 'n2n').mkdir(mode=0o700)
    with sqlite3.connect(home / 'n2n/federation.db') as db:
        db.execute('CREATE TABLE risk (id INTEGER,role TEXT,risk_name TEXT,enabled_stacks TEXT,self_member_id TEXT)')
        db.execute("INSERT INTO risk VALUES(1,'border','r03-fixture','in2n',NULL)")
    cfg = dict(schemaVersion=1, installation_id=installation, role='border', runtime_kind='openclaw', control_only=True,
               home=str(home), source_root=str(source), python=str(python), python_sha256=hashlib.sha256(python.read_bytes()).hexdigest(),
               python_env=str(venv), python_env_manifest=str(env_manifest), python_env_manifest_sha256=env_hash,
               source_manifest=str(manifest), source_manifest_sha256=manifest_hash, profile_sha256=profile_hash,
               registry=str(registry), registry_sha256=registry_hash, origin='https://r03.example.test', environment={})
    file = base / 'role.json'; write(file, cfg)
    yield file, cfg
    # pytest owns these fixtures; restore permissions only so its temporary tree
    # cleanup remains possible. No runtime source/home is touched.
    source.chmod(0o755)
    for p in source.rglob('*'):
        if p.is_dir(): p.chmod(0o755)
    venv.chmod(0o755); (venv / 'bin').chmod(0o755)


def test_exact_environment_drops_ambient_credentials(selected, monkeypatch):
    file, cfg = selected
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'never-in-child')
    monkeypatch.setenv('PYTHONPATH', '/foreign')
    monkeypatch.setenv('OPENCLAW_HOME', '/foreign')
    result, env = role.validate(file)
    assert result == cfg and 'ANTHROPIC_API_KEY' not in env and 'PYTHONPATH' not in env
    assert env['OPENCLAW_HOME'] == cfg['home'] and env['N2N_PROTECTED_OPERATIONS'] == '1'
    assert env['NETCLAW_BGP_PEERS'] == '[]' and env['NETCLAW_DRY_RUN'] == 'true'


@pytest.mark.parametrize('field,value', [('control_only', False), ('runtime_kind', 'hermes'), ('origin', 'http://r03.example.test'),
                                         ('origin', 'https://r03.example.test/path'), ('environment', {'ANTHROPIC_API_KEY': 'no'}),
                                         ('environment', {'N2N_PROTECTED_OPERATIONS': '0'}), ('schemaVersion', True)])
def test_role_authority_changes_refuse(selected, field, value):
    file, cfg = selected; cfg[field] = value; write(file, cfg)
    with pytest.raises(role.RoleRefused): role.validate(file)


@pytest.mark.parametrize('name', ['.env', 'mesh.systemd.env'])
def test_ambient_runtime_environment_refused(selected, name):
    file, cfg = selected; write(Path(cfg['home']) / name, b'ANTHROPIC_API_KEY=fixture\n')
    with pytest.raises(role.RoleRefused, match='ambient_environment'): role.validate(file)


def test_extra_source_file_and_writable_source_refused(selected):
    file, cfg = selected; root = Path(cfg['source_root']); root.chmod(0o755)
    with pytest.raises(role.RoleRefused, match='immutable_source'): role.validate(file)
    (root / 'foreign.py').write_text('')
    with pytest.raises(role.RoleRefused, match='manifest_incomplete'): role.validate(file)


def test_changed_profile_refused_even_with_new_profile_pin(selected):
    file, cfg = selected; p = Path(cfg['home']) / 'netclaw-federation/protected-profile.json'
    d = json.loads(p.read_text()); d['runtime'] = {'provider': 'forbidden'}
    cfg['profile_sha256'] = write(p, d); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='fields_invalid'): role.validate(file)


def test_public_external_listener_refused(selected):
    file, cfg = selected; p = Path(cfg['registry']); d = json.loads(p.read_text())
    d['entries'][1]['bind_host'] = '10.172.0.2'; cfg['registry_sha256'] = write(p, d); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='dormant'): role.validate(file)


def test_uninitialized_home_never_created(selected):
    file, cfg = selected; cfg['home'] = str(file.parent / 'missing'); write(file, cfg)
    with pytest.raises(role.RoleRefused): role.validate(file)
    assert not Path(cfg['home']).exists()


def test_symlink_home_and_duplicate_json_refuse(selected):
    file, cfg = selected; link = file.parent / 'link'; link.symlink_to(cfg['home']); cfg['home'] = str(link); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='canonical'): role.validate(file)
    write(file, b'{"role":"border","role":"member"}')
    with pytest.raises(role.RoleRefused, match='duplicate'): role.validate(file)


def test_venv_interpreter_symlink_keeps_invocation_path(selected):
    file, cfg = selected; target = Path(cfg['python']); alias = target.with_name('python3')
    target.parent.chmod(0o755); alias.symlink_to('python'); target.parent.chmod(0o555)
    manifest = Path(cfg['python_env_manifest']); data = json.loads(manifest.read_text()); data['symlinks']['bin/python3'] = 'python'
    cfg['python_env_manifest_sha256'] = write(manifest, data)
    cfg['python'] = str(alias); write(file, cfg)
    actual, _ = role.validate(file)
    assert actual['python'] == str(alias)


def test_unpinned_python_import_file_refused(selected):
    file, cfg = selected; venv = Path(cfg['python_env']); venv.chmod(0o755)
    (venv / 'sitecustomize.py').write_text('raise RuntimeError("never imported")'); venv.chmod(0o555)
    with pytest.raises(role.RoleRefused, match='python_environment_changed'): role.validate(file)


@pytest.mark.parametrize('kind', ['identity', 'registry'])
def test_nested_role_schema_is_not_only_a_hash_check(selected, kind):
    file, cfg = selected
    p = Path(cfg['home']) / 'netclaw-federation/protected-profile.json' if kind == 'identity' else Path(cfg['registry'])
    data = json.loads(p.read_text())
    if kind == 'identity': data['identity']['provider_key'] = 'fixture-forbidden'
    else: data.pop('revision')
    cfg['profile_sha256' if kind == 'identity' else 'registry_sha256'] = write(p, data); write(file, cfg)
    with pytest.raises(ValueError): role.validate(file)


def test_cloud_member_activation_is_explicitly_unqualified(selected):
    file, cfg = selected; cfg.update(role='member', control_only=False, origin=None); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='member_activation_unqualified'): role.validate(file)


def test_duplicate_venv_site_policy_refused_even_with_fresh_manifest(selected):
    file, cfg = selected; venv = Path(cfg['python_env']); policy = venv / 'pyvenv.cfg'
    policy.chmod(0o644); policy.write_text('include-system-site-packages = false\ninclude-system-site-packages = true\n'); policy.chmod(0o444)
    manifest = Path(cfg['python_env_manifest']); data = json.loads(manifest.read_text())
    data['files']['pyvenv.cfg'] = hashlib.sha256(policy.read_bytes()).hexdigest()
    cfg['python_env_manifest_sha256'] = write(manifest, data); write(file, cfg)
    with pytest.raises(role.RoleRefused, match='system_site_packages_refused'): role.validate(file)


def test_mobile_listener_uses_only_reviewed_port_and_derived_origin(selected, monkeypatch):
    file, cfg = selected
    cfg['environment']['N2N_EDGE_WS_PORT'] = '13007'; write(file, cfg)
    monkeypatch.setenv('NETCLAW_MOBILE_ORIGIN', 'https://foreign.example')
    monkeypatch.setenv('N2N_EDGE_WS_HOST', '0.0.0.0')
    _, environment = role.validate(file)
    assert environment['N2N_EDGE_WS_PORT'] == '13007'
    assert environment['NETCLAW_MOBILE_ORIGIN'] == cfg['origin']
    assert 'N2N_EDGE_WS_HOST' not in environment
    cfg['environment']['N2N_EDGE_WS_HOST'] = '0.0.0.0'; write(file, cfg)
    with pytest.raises(role.RoleRefused, match='environment_refused'):
        role.validate(file)
