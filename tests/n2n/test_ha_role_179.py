"""HA launch explicitly selects profile2 and refuses all standalone fallback."""
import hashlib
import json
from pathlib import Path

import pytest

from test_protected_role_172 import selected, role, write
from test_ha_contract_179 import manifest_fixture
from bgp.federation.ha.config import sign_manifest
from bgp.federation.protected_contract import key_id


@pytest.fixture
def ha_role(selected):
    file, cfg = selected
    home, source = Path(cfg['home']), Path(cfg['source_root'])
    value, root_cert, root_key = manifest_fixture()
    node = value['nodes'][0]; node['installation_id'] = cfg['installation_id']
    anchor = home/'anchor.pem'; write(anchor, root_cert.encode())
    manifest = home/'manifest.json'; write(manifest, sign_manifest(value, root_key))
    config = {'schema_version': 1, 'role': 'border', 'manifest_file': str(manifest),
        'anchor_certificate_file': str(anchor), 'anchor_key_id': key_id(root_cert),
        'transport_ca_file': str(home/'tls.crt'), 'node_id': node['node_id'],
        'transport_certificate_file': str(home/'tls.crt'), 'private_key_file': str(home/'tls.key'),
        'etcd': {'endpoints': ['https://localhost:12379'], 'ca_file': str(home/'tls.crt'),
                 'certificate_file': str(home/'tls.crt'), 'private_key_file': str(home/'tls.key'),
                 'username': 'fixture-only', 'password_file': str(home/'password')}}
    write(home/'password', b'fixture-only')
    config_path = home/'ha-config.json'; config_hash = write(config_path, config)
    identity = {'installation_id': cfg['installation_id'], 'identity': node['identity'],
                'key_id': node['key_id'], 'authority_generation': value['generation']}
    profile = {'schemaVersion': 2, 'role': 'border', 'identity': identity, 'access': {'mode': 'open-lab'},
               'ha': {'config_file': str(config_path), 'config_sha256': config_hash}}
    write(home/'netclaw-federation/ha-required.json', {k:value[k] for k in ('schema_version','cluster_id','generation')})
    write(home/'openclaw.json', {'netclaw': {'controlOnly': True}})
    cfg['profile_sha256'] = write(home/'netclaw-federation/protected-profile.json', profile)
    cfg.update(schemaVersion=3, origin=node['endpoints']['https'])
    cfg.pop('registry'); cfg.pop('registry_sha256')
    # Non-executing closed source fixture for the stdlib preflight only.
    for directory in [source, *[p for p in source.rglob('*') if p.is_dir()]]: directory.chmod(0o755)
    pinned = json.loads(Path(cfg['source_manifest']).read_text())
    for name in ('factory.py','config.py','authority.py','channel.py','internal.py','member.py','border.py','operations.py','admission.py','store.py','effect.py','mcp_transport.py','model_transport.py'):
        path = source/'mcp-servers/protocol-mcp/bgp/federation/ha'/name
        path.parent.mkdir(exist_ok=True); path.write_bytes(b'# controlled non-executing source fixture\n'); path.chmod(0o444)
        pinned['files'][str(path.relative_to(source))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for directory in [source, *[p for p in source.rglob('*') if p.is_dir()]]: directory.chmod(0o555)
    cfg['source_manifest_sha256'] = write(Path(cfg['source_manifest']), pinned)
    write(file, cfg)
    return file, cfg, profile


def test_ha_role_never_selects_standalone_registry_or_ambient_provider(ha_role, monkeypatch):
    file, cfg, _ = ha_role
    monkeypatch.setenv('N2N_ENDPOINT_REGISTRY', '/foreign/registry')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'unused')
    _, env = role.validate(file)
    assert 'N2N_ENDPOINT_REGISTRY' not in env and 'ANTHROPIC_API_KEY' not in env
    assert env['N2N_PROTECTED_OPERATIONS'] == '1' and env['N2N_ROLE'] == 'border'


@pytest.mark.parametrize('fault', ['marker', 'origin', 'registry', 'profile_version', 'config_hash', 'harness'])
def test_ha_role_refuses_downgrade_or_wrong_scope(ha_role, fault):
    file, cfg, profile = ha_role; home = Path(cfg['home'])
    if fault == 'marker': write(home/'netclaw-federation/ha-required.json', {'schema_version': 1, 'cluster_id': 'foreign', 'generation': 'foreign'})
    if fault == 'origin': cfg['origin'] = 'https://foreign.test'
    if fault == 'registry': cfg['registry'] = '/foreign/registry'
    if fault == 'profile_version': profile['schemaVersion'] = 1
    if fault == 'config_hash': profile['ha']['config_sha256'] = '0'*64
    if fault == 'harness': write(home/'openclaw.json', {'model': 'unqualified'})
    cfg['profile_sha256'] = write(home/'netclaw-federation/protected-profile.json', profile)
    write(file, cfg)
    with pytest.raises(role.RoleRefused): role.validate(file)


def test_standalone_role_cannot_ignore_durable_ha_marker(selected):
    file, cfg = selected
    write(Path(cfg['home'])/'netclaw-federation/ha-required.json', {'schema_version': 1})
    with pytest.raises(role.RoleRefused, match='ha_downgrade_refused'): role.validate(file)
