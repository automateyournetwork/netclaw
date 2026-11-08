"""R08 cluster trust is explicit and cannot silently become standalone."""
import copy
import json
import uuid

import pytest

from bgp.federation.certs import create_self_signed
from bgp.federation.protected_contract import key_id
from bgp.federation.ha.config import (
    HAError, Manifest, sign_manifest, verify_manifest, require_ha, install_marker,
)


def manifest_fixture():
    root_cert, root_key = create_self_signed('r08-enrollment')
    nodes = []
    for number in range(3):
        cert, _ = create_self_signed(f'r08-border-{number}')
        nodes.append({
            'node_id': str(uuid.uuid4()), 'installation_id': str(uuid.uuid4()),
            'identity': f'r08-border-{number}', 'key_id': key_id(cert),
            'certificate': cert, 'role': 'border',
            'endpoints': {
                'cluster': {'host': '127.0.0.1', 'port': 5000 + number,
                            'server_name': f'border-{number}.r08.test'},
                'in2n': {'host': '127.0.0.1', 'port': 5100 + number,
                         'server_name': f'border-{number}.r08.test'},
                'https': f'https://border-{number}.r08.test:{5200 + number}',
                'wss': f'wss://border-{number}.r08.test:{5200 + number}/mobile/ws',
            },
        })
    value = {
        'schema_version': 1, 'cluster_id': str(uuid.uuid4()),
        'generation': str(uuid.uuid4()), 'organization': 'r08-fixture',
        'revision': 1, 'nodes': nodes,
        'limits': {'leader_lease_s': 12, 'renewal_s': 3, 'admission_ms': 3000,
                   'clock_uncertainty_ms': 250, 'max_operations': 1024,
                   'max_members': 32},
    }
    return value, root_cert, root_key


def test_root_signed_manifest_preserves_distinct_node_identity():
    value, cert, key = manifest_fixture()
    signed = sign_manifest(value, key)
    result = verify_manifest(signed, cert, expected_key_id=key_id(cert))
    assert result.cluster_id == value['cluster_id']
    assert result.generation == value['generation']
    assert result.node(value['nodes'][0]['node_id'])['installation_id'] != result.cluster_id
    assert len({n['key_id'] for n in result.nodes}) == 3


@pytest.mark.parametrize('mutation', [
    lambda v: v.update(etcd_password='not-a-public-field'),
    lambda v: v['nodes'][0].update(role='member'),
    lambda v: v['nodes'][1].update(node_id=v['nodes'][0]['node_id']),
    lambda v: v['nodes'][1].update(installation_id=v['nodes'][0]['installation_id']),
    lambda v: v['nodes'][1].update(key_id=v['nodes'][0]['key_id'], certificate=v['nodes'][0]['certificate']),
    lambda v: v['nodes'][0]['endpoints'].update(https='http://untrusted.test'),
    lambda v: v['nodes'][0]['endpoints'].update(https='https://user:password@host.test'),
    lambda v: v['nodes'][0]['endpoints']['cluster'].update(port=True),
    lambda v: v['limits'].update(admission_ms=600000),
    lambda v: v['limits'].update(renewal_s=12),
    lambda v: v.update(revision=True),
])
def test_invalid_or_role_confused_manifest_refused(mutation):
    value, _, _ = manifest_fixture()
    mutation(value)
    with pytest.raises(HAError):
        Manifest(value)


def test_manifest_signature_and_public_anchor_are_not_advertised_trust():
    value, cert, key = manifest_fixture()
    other_cert, _ = create_self_signed('untrusted')
    signed = sign_manifest(value, key)
    with pytest.raises(HAError, match='manifest_anchor_mismatch'):
        verify_manifest(signed, cert, expected_key_id=key_id(other_cert))
    altered = copy.deepcopy(signed)
    altered['manifest']['nodes'][0]['endpoints']['https'] = 'https://attacker.test'
    with pytest.raises(HAError, match='invalid_manifest_signature'):
        verify_manifest(altered, cert, expected_key_id=key_id(cert))
    with pytest.raises(HAError, match='stale_manifest'):
        verify_manifest(signed, cert, expected_key_id=key_id(cert), minimum_revision=2)


def test_ha_marker_survives_missing_config_or_adapter(tmp_path):
    home = tmp_path / 'private'
    home.mkdir(mode=0o700)
    value, _, _ = manifest_fixture()
    manifest = Manifest(value)
    assert require_ha(home, None) is False
    install_marker(home, manifest)
    with pytest.raises(HAError, match='ha_required'):
        require_ha(home, None)
    with pytest.raises(HAError, match='ha_runtime_unqualified'):
        require_ha(home, manifest, adapter_ready=False)
    assert require_ha(home, manifest, adapter_ready=True) is True
    changed = copy.deepcopy(value)
    changed['generation'] = str(uuid.uuid4())
    with pytest.raises(HAError, match='cluster_changed'):
        require_ha(home, Manifest(changed), adapter_ready=True)


def test_marker_replacement_permissions_and_symlink_refused(tmp_path):
    home = tmp_path / 'private'
    home.mkdir(mode=0o700)
    value, _, _ = manifest_fixture()
    manifest = Manifest(value)
    install_marker(home, manifest)
    path = home / 'ha-required.json'
    assert path.stat().st_mode & 0o777 == 0o600
    before = path.read_bytes()
    install_marker(home, manifest)
    assert path.read_bytes() == before
    path.chmod(0o644)
    with pytest.raises(HAError, match='unsafe_private_file'):
        require_ha(home, manifest, adapter_ready=True)


def test_duplicate_json_keys_are_refused_at_manifest_boundary():
    value, cert, key = manifest_fixture()
    signed = sign_manifest(value, key)
    raw = json.dumps(signed).replace('"schema":', '"schema":"forged","schema":', 1)
    with pytest.raises(HAError):
        verify_manifest(raw, cert, expected_key_id=key_id(cert))
