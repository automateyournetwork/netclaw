"""Spec 198: the outbound (member) protected role accepts a one-Border manifest; 0 and >3 stay refused."""
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lib'))

from bgp.federation import protected_contract as c  # noqa: E402
import protected_role as pr  # noqa: E402

HA_FILES = ('factory.py', 'config.py', 'authority.py', 'channel.py', 'internal.py', 'member.py', 'border.py',
            'operations.py', 'admission.py', 'store.py', 'effect.py', 'mcp_transport.py', 'model_transport.py')


def private_file(path, data=b'x'):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    return str(path)


def member_fixture(tmp_path, node_count):
    root = tmp_path.resolve()
    home = root / 'home'
    for sub in ('netclaw-federation', 'netclaw-hud'):
        (home / sub).mkdir(parents=True, mode=0o700)
    cluster = {'cluster_id': str(uuid.uuid4()), 'generation': str(uuid.uuid4())}
    nodes = [{'node_id': str(uuid.uuid4()), 'installation_id': str(uuid.uuid4()), 'key_id': 'b' * 64,
              'endpoints': {'https': f'https://n{i}.example.test'}} for i in range(node_count)]
    manifest = {'schema': 'netclaw.ncfed.cluster-manifest.v1', 'signature': {}, 'manifest': {**cluster, 'nodes': nodes}}
    files = {name: private_file(root / name) for name in ('anchor', 'ca', 'cert', 'key')}
    value = {'schema_version': 1, 'role': 'member', 'manifest_file': private_file(root / 'manifest.json', c.encode(manifest)),
             'anchor_certificate_file': files['anchor'], 'anchor_key_id': 'a' * 64, 'transport_ca_file': files['ca'],
             'certificate_file': files['cert'], 'private_key_file': files['key']}
    raw = c.encode(value)
    config_path = private_file(root / 'ha-config.json', raw)
    private_file(home / 'netclaw-federation/ha-required.json', c.encode({'schema_version': 1, **cluster}))
    sources = private_file(root / 'sources.json', json.dumps({'files': {
        'mcp-servers/protocol-mcp/bgp/federation/ha/' + name: 'f' * 64 for name in HA_FILES}}).encode())
    cfg = {'role': 'member', 'origin': None, 'source_manifest': sources, 'installation_id': str(uuid.uuid4())}
    profile = {'identity': {'key_id': 'b' * 64}, 'ha': {'config_file': config_path, 'config_sha256': hashlib.sha256(raw).hexdigest()}}
    return cfg, profile, home, root


@pytest.mark.parametrize('count', [1, 2, 3])
def test_member_role_accepts_one_to_three_borders(tmp_path, count):
    cfg, profile, home, root = member_fixture(tmp_path, count)
    assert pr.validate_ha_profile(cfg, profile, home, root)['role'] == 'member'


@pytest.mark.parametrize('count', [0, 4])
def test_member_role_still_refuses_zero_and_more_than_three(tmp_path, count):
    cfg, profile, home, root = member_fixture(tmp_path, count)
    with pytest.raises(pr.RoleRefused):
        pr.validate_ha_profile(cfg, profile, home, root)


def test_member_role_refuses_a_border_origin(tmp_path):
    cfg, profile, home, root = member_fixture(tmp_path, 1)
    cfg['origin'] = 'https://n0.example.test'
    with pytest.raises(pr.RoleRefused):
        pr.validate_ha_profile(cfg, profile, home, root)
