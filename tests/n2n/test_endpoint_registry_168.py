"""Owned configuration and migration, using synthetic reservations only."""
import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from bgp.federation import certs
from bgp.federation.endpoint_registry import Registry, validate, export_bundle, import_bundle


@pytest.fixture
def registry_data(tmp_path):
    tmp_path.chmod(0o700)
    ca, _ = certs.create_risk_ca('example')
    ca_path = tmp_path / 'ca.pem'
    ca_path.write_text(ca)
    ca_path.chmod(0o600)
    common = dict(direction='listen', routing_host='1.tcp.example.test', tls_server_name='border.example.test',
                  ca_file=str(ca_path), bind_host='127.0.0.1', cert_file=str(tmp_path/'cert.pem'),
                  key_file=str(tmp_path/'key.pem'))
    return {'schemaVersion': 1, 'installationId': 'test-installation', 'revision': 1, 'entries': [
        dict(common, id='members', service='in2n', profile='in2n-tls-exporter-v1', routing_port=21001,
             bind_port=42101, reservation_id='ra_fixture_in2n', application_identity='example/border', application_trust=ca),
        dict(common, id='external', service='en2n', profile='en2n-tls13-v1', routing_port=21002,
             bind_port=42102, reservation_id='ra_fixture_en2n', application_identity='as65001-1.2.3.4', application_trust='a'*64)]}


def test_registry_roundtrip_and_projection(tmp_path, registry_data):
    registry = Registry(tmp_path/'registry.json', 'test-installation')
    registry.replace(registry_data, expected_revision=0)
    assert registry.load() == registry_data
    assert os.stat(registry.path).st_mode & 0o777 == 0o600
    status = registry.status()
    assert len(status['services']) == 2
    assert all(e['tcp_reachable'] is None and e['authenticated'] is False for e in status['services'])
    assert 'application_trust' not in json.dumps(status)
    assert str(tmp_path) not in json.dumps(status)


@pytest.mark.parametrize('change', ['duplicate', 'unknown', 'tls_name', 'profile', 'bind', 'reserved', 'trust', 'foreign'])
def test_invalid_registry_never_written(tmp_path, registry_data, change):
    value = copy.deepcopy(registry_data)
    entry = value['entries'][0]
    if change == 'duplicate': value['entries'][1]['routing_port'] = entry['routing_port']
    if change == 'unknown': entry['authtoken'] = 'do-not-store'
    if change == 'tls_name': entry['tls_server_name'] = ''
    if change == 'profile': entry['profile'] = 'plaintext'
    if change == 'bind': entry['bind_host'] = '0.0.0.0'
    if change == 'reserved': entry.pop('reservation_id')
    if change == 'trust': entry['application_trust'] = 'untrusted'
    if change == 'foreign': value['installationId'] = 'foreign'
    registry = Registry(tmp_path/'registry.json', 'test-installation')
    with pytest.raises(ValueError): registry.replace(value, expected_revision=0)
    assert not registry.path.exists()


def test_owner_symlink_and_permissions(tmp_path, registry_data):
    registry = Registry(tmp_path/'registry.json', 'test-installation')
    registry.replace(registry_data, expected_revision=0)
    registry.path.chmod(0o644)
    with pytest.raises(ValueError): registry.load()
    registry.path.chmod(0o600)
    (tmp_path/'link.json').symlink_to(registry.path)
    with pytest.raises((ValueError, OSError)): Registry(tmp_path/'link.json', 'test-installation').load()


def test_atomic_address_change_and_explicit_recovery(tmp_path, registry_data):
    registry = Registry(tmp_path/'registry.json', 'test-installation')
    registry.replace(registry_data, expected_revision=0)
    before = registry.load()['entries'][0]
    registry.update_address('members', '2.tcp.example.test', 22001, 'ra_fixture_replacement', expected_revision=1)
    current = registry.load()
    assert current['revision'] == 2
    after = current['entries'][0]
    assert {k:v for k,v in before.items() if k not in ('routing_host','routing_port','reservation_id')} == {
        k:v for k,v in after.items() if k not in ('routing_host','routing_port','reservation_id')}
    with pytest.raises(ValueError): registry.update_address('members', 'bad', 0, 'ra_bad', expected_revision=2)
    assert registry.load() == current
    registry.recover(expected_revision=2)
    assert registry.load() == dict(registry_data, revision=3)


def test_concurrent_revision_change_has_one_winner(tmp_path, registry_data):
    registry = Registry(tmp_path/'registry.json', 'test-installation')
    registry.replace(registry_data, expected_revision=0)
    def update(port):
        try:
            Registry(registry.path, 'test-installation').update_address('members', '2.tcp.example.test', port, 'ra_fixture', expected_revision=1)
            return True
        except ValueError: return False
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(update, [23001,23002])) == [False,True]
    assert registry.load()['revision'] == 2


def test_public_bundle_rebinds_second_installation(tmp_path, registry_data):
    bundle = export_bundle(registry_data['entries'][0])
    assert str(tmp_path) not in json.dumps(bundle)
    assert 'key_file' not in json.dumps(bundle) and 'token' not in json.dumps(bundle)
    other = tmp_path/'other';other.mkdir(mode=0o700)
    registry = Registry(other/'registry.json', 'second-installation')
    import_bundle(registry, bundle, expected_revision=0)
    entry = registry.entry('members', direction='dial', service='in2n')
    assert entry['application_identity'] == 'example/border'
    assert 'bind_port' not in entry
    assert registry.load()['installationId'] == 'second-installation'
    assert entry['ca_file'].startswith(str(other))
