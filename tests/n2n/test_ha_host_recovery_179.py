"""Host inspector tests use explicit controlled subprocess observations only."""
import copy
import importlib.util
from pathlib import Path
import types

import pytest

from bgp.federation import protected_contract as c
from bgp.federation.ha.config import HAError
from test_ha_recovery_179 import recovery_case

PATH = Path(__file__).resolve().parents[2] / 'scripts/lib/ha_cluster.py'
spec = importlib.util.spec_from_file_location('ha_cluster_host', PATH)
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)


def observation(identifier, owner, running=True):
    return {'Id': identifier, 'Name': '/owned-' + identifier[:8],
            'Config': {'Labels': {'netclaw.owner': owner, 'netclaw.spec': '179'}, 'Image': 'pinned-image'},
            'HostConfig': {'RestartPolicy': {'Name': 'no'}},
            'NetworkSettings': {'Networks': {'owned': {'NetworkID': 'network'}} if running else {}},
            'State': {'Running': running, 'Paused': False, 'Restarting': False, 'Pid': 50 if running else 0}}


def host_fixture(tmp_path, monkeypatch):
    _, _, old, snap, new, certificate, proof, receipt = recovery_case()
    from bgp.federation.certs import create_self_signed
    cert, key = create_self_signed('host-inspector')
    root = tmp_path / 'private'; root.mkdir(mode=0o700)
    cert_file = root / 'host.crt'; key_file = root / 'host.key'
    host.write_new(cert_file, cert.encode()); host.write_new(key_file, key.encode())
    owner = 'netclaw-r08-fixture'
    subjects = []
    for index in range(3):
        subjects.append({'kind': 'container', 'role': 'voter', 'node_id': None, 'id': f'{index + 1:064x}'})
        subjects.append({'kind': 'container', 'role': 'border', 'node_id': old.nodes[index]['node_id'], 'id': f'{index + 4:064x}'})
    subjects.append({'kind': 'container', 'role': 'executor', 'node_id': None, 'id': f'{7:064x}'})
    rows = {row['id']: observation(row['id'], owner) for row in subjects}
    def run(arguments, **kwargs):
        import json
        assert arguments[:2] == ['docker', 'inspect']
        return types.SimpleNamespace(returncode=0, stdout=json.dumps([rows[i] for i in arguments[2:]]).encode(), stderr=b'')
    monkeypatch.setattr(host.subprocess, 'run', run)
    inspector = host.HostIsolation(root, cert_file, key_file)
    inventory = inspector.capture(old, owner, subjects)
    host.write_new(root / 'snapshot.json', c.encode(snap))
    import hashlib
    host.write_new(root / 'exports.json', c.encode({'schema_version': 1, 'artifacts': [
        {'path': str(root / 'snapshot.json'), 'sha256': hashlib.sha256(c.encode(snap)).hexdigest()}]}))
    return inspector, inventory, rows, old, snap, new, certificate, root


def test_host_proof_requires_actual_stopped_disconnected_owned_objects(tmp_path, monkeypatch):
    inspector, inventory, rows, old, snap, new, certificate, root = host_fixture(tmp_path, monkeypatch)
    with pytest.raises(HAError, match='old_authority_not_isolated'):
        inspector.issue(old, new, root / 'snapshot.json', root / 'exports.json')
    for identifier, row in rows.items():
        rows[identifier] = observation(identifier, inventory['owner'], False)
    proof = inspector.issue(old, new, root / 'snapshot.json', root / 'exports.json')
    assert proof['payload']['snapshot_sha256'] == c.sha256(snap)
    assert proof['payload']['nodes'] == sorted(n['node_id'] for n in old.nodes)
    assert (root / 'isolation-observations.json').exists()


@pytest.mark.parametrize('fault', ['paused', 'network', 'restart', 'wrong_id', 'wrong_owner'])
def test_host_inspection_rejects_unsafe_or_replaced_object(tmp_path, monkeypatch, fault):
    inspector, inventory, rows, old, snap, new, certificate, root = host_fixture(tmp_path, monkeypatch)
    for identifier in rows:
        rows[identifier] = observation(identifier, inventory['owner'], False)
    row = next(iter(rows.values()))
    if fault == 'paused': row['State']['Paused'] = True
    if fault == 'network': row['NetworkSettings']['Networks'] = {'live': {}}
    if fault == 'restart': row['HostConfig']['RestartPolicy']['Name'] = 'always'
    if fault == 'wrong_id': row['Id'] = 'f' * 64
    if fault == 'wrong_owner': row['Config']['Labels']['netclaw.owner'] = 'other'
    with pytest.raises(HAError):
        inspector.issue(old, new, root / 'snapshot.json', root / 'exports.json')


def test_host_rejects_incomplete_inventory_and_snapshot_after_isolation(tmp_path, monkeypatch):
    inspector, inventory, rows, old, snap, new, certificate, root = host_fixture(tmp_path, monkeypatch)
    malformed = copy.deepcopy(inventory); malformed['subjects'] = malformed['subjects'][:-1]
    with pytest.raises(HAError, match='incomplete_owned_inventory'):
        host.validate_inventory(malformed, old)
    for identifier in rows:
        rows[identifier] = observation(identifier, inventory['owner'], False)
    bad = dict(snap, created_at_ms=10**15)
    host.write_new(root / 'future.json', c.encode(bad))
    import hashlib
    host.write_new(root / 'future-exports.json', c.encode({'schema_version': 1, 'artifacts': [
        {'path': str(root / 'future.json'), 'sha256': hashlib.sha256(c.encode(bad)).hexdigest()}]}))
    with pytest.raises(HAError, match='snapshot_after_isolation'):
        inspector.issue(old, new, root / 'future.json', root / 'future-exports.json')


def test_process_observation_uses_start_and_command_identity_and_denies_ps_errors(monkeypatch):
    def observed(arguments, **kwargs):
        assert arguments == ['/bin/ps', '-p', '12345', '-o', 'uid=,lstart=,command=']
        return types.SimpleNamespace(returncode=0,
            stdout=b'501 Sat Nov 7 12:00:00 2026 /private/python runtime.py\n', stderr=b'')
    monkeypatch.setattr(host.subprocess, 'run', observed)
    row = host.process_observation(12345)
    assert row['present'] and row['uid'] == 501
    assert len(row['start_id']) == len(row['command_sha256']) == 64
    monkeypatch.setattr(host.subprocess, 'run', lambda *a, **k:
        types.SimpleNamespace(returncode=1, stdout=b'', stderr=b''))
    assert host.process_observation(12345) == {'pid': 12345, 'present': False}
    monkeypatch.setattr(host.subprocess, 'run', lambda *a, **k:
        types.SimpleNamespace(returncode=1, stdout=b'', stderr=b'permission denied'))
    with pytest.raises(HAError, match='host_inspection_unavailable'):
        host.process_observation(12345)


def test_host_process_pid_reuse_is_not_isolation(tmp_path, monkeypatch):
    inspector, inventory, rows, old, snap, new, certificate, root = host_fixture(tmp_path, monkeypatch)
    process = {'kind': 'process', 'role': 'executor', 'node_id': None,
               'pid': 12345, 'start_id': 'a' * 64, 'command_sha256': 'b' * 64}
    replaced = copy.deepcopy(inventory)
    replaced['subjects'][-1] = process
    for identifier in rows:
        rows[identifier] = observation(identifier, inventory['owner'], False)
    monkeypatch.setattr(host, 'process_observation', lambda pid:
        {'pid': pid, 'present': True, 'uid': 501, 'start_id': 'c' * 64, 'command_sha256': 'd' * 64})
    with pytest.raises(HAError, match='old_authority_not_isolated'):
        inspector._observe(replaced, isolated=True)
    monkeypatch.setattr(host, 'process_observation', lambda pid: {'pid': pid, 'present': False})
    assert len(inspector._observe(replaced, isolated=True)) == 7
