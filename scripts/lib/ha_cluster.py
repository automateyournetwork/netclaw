"""Private maintainer host observations for NCFED HA recovery.

Only this host-side helper owns the isolation signer. No Border/member, HTTP API,
caller-supplied callback or `isolated=true` field can manufacture a host receipt.
Inspection is read-only: stop/disconnect/export remain separately reviewed actions.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from bgp.federation import protected_contract as c
from bgp.federation.ha.config import HAError, check, read_private
from bgp.federation.ha.recovery import isolation_message, validate_snapshot, _new_generation
from bgp.federation.protected_runtime import private_directory


def write_new(path, data):
    path = Path(path)
    private_directory(path.parent)
    check(path.absolute() == path.resolve(), 'unsafe_private_file')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    parent = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def validate_inventory(value, manifest):
    c.exact(value, 'schema_version cluster_id generation owner captured_at_ms subjects')
    check(value['schema_version'] == 1 and {k: value[k] for k in manifest.audience} == manifest.audience,
          'owned_inventory_mismatch')
    check(isinstance(value['owner'], str) and re.fullmatch(r'netclaw-r08-[a-zA-Z0-9-]{1,80}', value['owner']),
          'owned_inventory_mismatch')
    check(type(value['captured_at_ms']) is int and value['captured_at_ms'] > 0, 'owned_inventory_mismatch')
    subjects = value['subjects']
    check(isinstance(subjects, list) and 7 <= len(subjects) <= 38, 'incomplete_owned_inventory')
    seen, borders, voters, executors = set(), set(), 0, 0
    for row in subjects:
        check(isinstance(row, dict) and row.get('kind') in ('container', 'process'), 'invalid_owned_subject')
        fields = 'kind role node_id id' if row['kind'] == 'container' else 'kind role node_id pid start_id command_sha256'
        c.exact(row, fields)
        check(row['role'] in ('voter', 'border', 'executor'), 'invalid_owned_subject')
        if row['kind'] == 'container':
            check(isinstance(row['id'], str) and re.fullmatch('[0-9a-f]{64}', row['id']), 'invalid_owned_subject')
            identity = ('container', row['id'])
        else:
            check(row['role'] != 'voter' and type(row['pid']) is int and 1 < row['pid'] < 2**31,
                  'invalid_owned_subject')
            c.digest_field(row['start_id']); c.digest_field(row['command_sha256'])
            identity = ('process', row['pid'])
        check(identity not in seen, 'duplicate_owned_subject'); seen.add(identity)
        if row['role'] == 'border':
            c.uuid_field(row['node_id'])
            check(row['node_id'] not in borders, 'duplicate_owned_subject'); borders.add(row['node_id'])
        else:
            check(row['node_id'] is None, 'invalid_owned_subject')
        voters += row['role'] == 'voter'; executors += row['role'] == 'executor'
    check(voters == 3 and 1 <= executors <= 32
          and borders == {n['node_id'] for n in manifest.nodes}, 'incomplete_owned_inventory')
    return value


def process_observation(pid):
    """OS observation only, with PID reuse treated as non-isolation.

    Caller records both command and start identities before the fault. No process
    is signalled. Nonzero ps errors are distinct from a proven empty PID query.
    """
    check(type(pid) is int and 1 < pid < 2**31, 'invalid_owned_subject')
    try:
        result = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'uid=,lstart=,command='],
            capture_output=True, timeout=5, env={**os.environ, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired):
        raise HAError('host_inspection_unavailable', 503) from None
    check(len(result.stdout) <= 65536 and not result.stderr, 'host_inspection_unavailable', 503)
    if result.returncode == 1 and not result.stdout.strip():
        return {'pid': pid, 'present': False}
    check(result.returncode == 0, 'host_inspection_unavailable', 503)
    fields = result.stdout.decode().strip().split(None, 6)
    check(len(fields) == 7 and fields[0].isdigit(), 'host_inspection_unavailable', 503)
    uid, started, command = int(fields[0]), ' '.join(fields[1:6]), fields[6]
    return {'pid': pid, 'present': True, 'uid': uid,
            'start_id': hashlib.sha256(started.encode()).hexdigest(),
            'command_sha256': hashlib.sha256(command.encode()).hexdigest()}


class HostIsolation:
    def __init__(self, root, certificate_file, private_key_file):
        self.root = private_directory(Path(root).absolute())
        self.certificate = read_private(certificate_file).decode()
        self.key = read_private(private_key_file).decode()
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = serialization.load_pem_private_key(self.key.encode(), password=None)
        check(isinstance(key, ec.EllipticCurvePrivateKey) and isinstance(key.curve, ec.SECP256R1), 'invalid_host_signer')
        public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        check(hashlib.sha256(public).hexdigest() == c.key_id(self.certificate), 'host_signer_mismatch')

    def _observe(self, inventory, *, isolated):
        containers = [r for r in inventory['subjects'] if r['kind'] == 'container']
        try:
            response = subprocess.run(['docker', 'inspect', *[r['id'] for r in containers]],
                                      capture_output=True, timeout=15)
            check(response.returncode == 0 and len(response.stdout) <= 4 * 1024 * 1024,
                  'host_inspection_unavailable', 503)
            observed = c.decode(response.stdout, 4 * 1024 * 1024)
        except HAError:
            raise
        except (OSError, subprocess.TimeoutExpired):
            raise HAError('host_inspection_unavailable', 503) from None
        check(isinstance(observed, list) and len(observed) == len(containers), 'owned_inventory_mismatch')
        results = []
        for expected, row in zip(containers, observed):
            try:
                labels, state = row['Config']['Labels'], row['State']
                check(row['Id'] == expected['id'] and labels['netclaw.owner'] == inventory['owner']
                      and labels['netclaw.spec'] == '179', 'owned_identity_mismatch', 403)
                check(row['HostConfig']['RestartPolicy']['Name'] in ('', 'no'), 'owned_restart_policy_unsafe')
                if isolated:
                    check(state['Running'] is False and state['Paused'] is False and state['Restarting'] is False
                          and state['Pid'] == 0 and row['NetworkSettings']['Networks'] == {},
                          'old_authority_not_isolated', 409)
                else:
                    check(state['Running'] is True and state['Paused'] is False and state['Restarting'] is False
                          and type(state['Pid']) is int and state['Pid'] > 0, 'owned_baseline_not_running')
                results.append({'subject': expected, 'observation': row})
            except (KeyError, TypeError):
                raise HAError('owned_inventory_mismatch') from None
        for expected in inventory['subjects']:
            if expected['kind'] != 'process':
                continue
            row = process_observation(expected['pid'])
            if isolated:
                # Even an unrelated replacement PID is denied. A negative is
                # conservative and never guesses that a surviving process is safe.
                check(row['present'] is False, 'old_authority_not_isolated', 409)
            else:
                check(row['present'] and row['uid'] == os.getuid()
                      and row['start_id'] == expected['start_id']
                      and row['command_sha256'] == expected['command_sha256'], 'owned_identity_mismatch', 403)
            results.append({'subject': expected, 'observation': row})
        return results

    def capture(self, manifest, owner, subjects):
        inventory = {'schema_version': 1, **manifest.audience, 'owner': owner,
                     'captured_at_ms': int(time.time() * 1000), 'subjects': subjects}
        validate_inventory(inventory, manifest)
        observed = self._observe(inventory, isolated=False)
        write_new(self.root / 'owned-baseline.json', c.encode(observed))
        write_new(self.root / 'owned-inventory.json', c.encode(inventory))
        return inventory

    def issue(self, old_manifest, new_manifest, snapshot_file, exports_file):
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        _new_generation(old_manifest, new_manifest)
        inventory = validate_inventory(c.decode(read_private(self.root / 'owned-inventory.json')), old_manifest)
        # Baseline must exist; receipt issuance cannot register already-absent
        # objects as if they had been captured while the old authority was live.
        baseline = c.decode(read_private(self.root / 'owned-baseline.json', 4 * 1024 * 1024), 4 * 1024 * 1024)
        check(isinstance(baseline, list) and len(baseline) == len(inventory['subjects']), 'owned_baseline_missing')
        raw = read_private(snapshot_file, 4 * 1024 * 1024)
        snapshot = validate_snapshot(c.decode(raw, 4 * 1024 * 1024), old_manifest)
        enrolled_count = snapshot['records']['control']['value'].get('member_count', 0)
        check(type(enrolled_count) is int and enrolled_count <= sum(
            subject['role'] == 'executor' for subject in inventory['subjects']), 'incomplete_owned_inventory')
        export_raw = read_private(exports_file, 4 * 1024 * 1024)
        exports = c.decode(export_raw, 4 * 1024 * 1024)
        c.exact(exports, 'schema_version artifacts')
        check(exports['schema_version'] == 1 and isinstance(exports['artifacts'], list)
              and 1 <= len(exports['artifacts']) <= 256, 'invalid_export_manifest')
        snapshot_exported = False
        for item in exports['artifacts']:
            c.exact(item, 'path sha256')
            c.digest_field(item['sha256'])
            check(Path(item['path']).is_absolute(), 'invalid_export_manifest')
            check(hashlib.sha256(read_private(item['path'], 64 * 1024 * 1024)).hexdigest() == item['sha256'],
                  'export_digest_mismatch', 409)
            snapshot_exported |= (Path(item['path']) == Path(snapshot_file)
                                  and item['sha256'] == hashlib.sha256(raw).hexdigest())
        check(snapshot_exported, 'snapshot_export_missing')
        observed_at = int(time.time() * 1000)
        check(snapshot['created_at_ms'] <= observed_at, 'snapshot_after_isolation')
        observations = self._observe(inventory, isolated=True)
        payload = {'schema_version': 1, 'receipt_id': str(uuid.uuid4()), **old_manifest.audience,
                   'new_generation': new_manifest.generation, 'snapshot_sha256': c.sha256(snapshot),
                   'inventory_sha256': c.sha256(inventory), 'export_sha256': hashlib.sha256(export_raw).hexdigest(),
                   'observed_at_ms': observed_at, 'method': 'owned-host-isolation-v1',
                   'nodes': sorted(n['node_id'] for n in old_manifest.nodes), 'voter_count': 3,
                   'executor_count': sum(s['role'] == 'executor' for s in inventory['subjects']),
                   'observations_sha256': c.sha256(observations)}
        key = serialization.load_pem_private_key(self.key.encode(), password=None)
        signature = key.sign(isolation_message(payload), ec.ECDSA(hashes.SHA256()))
        proof = {'payload': payload, 'key_id': c.key_id(self.certificate),
                 'signature': base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}
        # Files are new-only: rerunning an issuance cannot replace old evidence.
        write_new(self.root / 'isolation-observations.json', c.encode(observations))
        write_new(self.root / 'isolation-receipt.json', c.encode(proof))
        return proof
