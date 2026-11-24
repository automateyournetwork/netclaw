"""Operator-only selected-runtime collection with durable, non-replaying IDs.

This is not a member tool or an alternative read policy. Run with the already
selected pyATS Python. The private pinned capability freezes inventory, strict
trust, source, credentials and profile. The public result has metadata only;
raw/parsed observations and facts stay in the private request directory.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import uuid

HERE = Path(__file__).resolve().parent
SOURCE_FILES = ('collector.py', 'collection_request.py', 'facts.py',
                'native_adapter.py', 'native_connection.py', 'native_read.py',
                'native_session.py', '../lib/protected_pyats.py', '../write-env.py')
LIMIT = 1024 * 1024
qualified_read_only_capture = True  # Contract marker, never a live qualification claim.
_binding = None


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def utc():
    return datetime.now(timezone.utc).isoformat()


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def private_bytes(path, pin=None, limit=LIMIT):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve(strict=True), 'private_path_required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1 and not info.st_mode & 0o077
                and 0 < info.st_size <= limit, 'private_file_required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        after = os.fstat(fd)
        require(len(data) == info.st_size and info.st_mtime_ns == after.st_mtime_ns
                and info.st_ctime_ns == after.st_ctime_ns, 'private_file_changed')
        require(pin is None or digest(data) == pin, 'private_digest_changed')
        return data
    finally:
        os.close(fd)


def private_json(path, pin=None, limit=LIMIT):
    return json.loads(private_bytes(path, pin, limit), object_pairs_hook=_object,
                      parse_constant=lambda _: require(False, 'nonfinite_json'))


def private_root(path):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve(strict=True), 'private_root_required')
    info = path.stat()
    require(path.is_dir() and info.st_uid == os.getuid()
            and not info.st_mode & 0o077, 'private_root_required')
    return path


def write_new(path, value):
    data = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_capability(path, pin):
    require(isinstance(pin, str) and re.fullmatch('[a-f0-9]{64}', pin), 'capability_pin_required')
    c = private_json(path, pin)
    fields = {'schema', 'profile', 'runtime_executable', 'runtime_prefix', 'parser_version',
              'inventory_sha256', 'policy_file', 'policy_sha256', 'source_files', 'devices'}
    require(set(c) == fields and c['schema'] == 1, 'capability_schema')
    require(c['runtime_executable'] == sys.executable and c['runtime_prefix'] == sys.prefix,
            'selected_runtime_changed')
    require(c['parser_version'] == importlib.metadata.version('genie'), 'parser_version_changed')
    require(c['profile'] in ('initial', 'detailed'), 'collection_profile')
    require(re.fullmatch('[a-f0-9]{64}', c['inventory_sha256']) is not None, 'inventory_digest')
    require(set(c['source_files']) == set(SOURCE_FILES), 'collector_source_closure')
    for name, expected in c['source_files'].items():
        require(digest((HERE / name).read_bytes()) == expected, 'collector_source_changed')
    policy = Path(c['policy_file'])
    require(policy.is_absolute() and policy == policy.resolve(strict=True)
            and policy.name == 'pyats_mcp_server.py'
            and digest(policy.read_bytes()) == c['policy_sha256'], 'native_policy_changed')
    require(isinstance(c['devices'], dict) and 1 <= len(c['devices']) <= 4, 'device_limit')
    for name, d in c['devices'].items():
        require(isinstance(name, str) and re.fullmatch('[A-Za-z0-9_.-]{1,128}', name), 'device_identity')
        require(set(d) == {'document', 'document_sha256', 'endpoint_sha256',
                           'credential_file', 'credential_sha256'}, 'device_binding')
        require(digest(canonical(d['document'])) == d['document_sha256'], 'frozen_testbed_changed')
        require(re.fullmatch('[a-f0-9]{64}', d['endpoint_sha256']) is not None, 'endpoint_digest')
        # Check pinned private bytes without importing secrets into logs/results.
        private_bytes(d['credential_file'], d['credential_sha256'], 16384)
    return c


@contextmanager
def capture_context(device, command, *, timeout, evidence_directory):
    """Only called by collector's fresh, deadline-owned child."""
    global _binding
    c = load_capability(os.environ['NETCLAW_GENIE_COLLECTOR_CAPABILITY'],
                        os.environ['NETCLAW_GENIE_COLLECTOR_CAPABILITY_SHA256'])
    require(_binding is None and device in c['devices'], 'one_capture_per_child')
    d = c['devices'][device]
    writer = load_module('_collector_env_reader', HERE.parent / 'write-env.py')
    credentials = writer.values(private_bytes(d['credential_file'], d['credential_sha256'], 16384).decode('utf8'))
    require(set(credentials) == {'SPEC200_PYATS_USERNAME', 'SPEC200_PYATS_PASSWORD',
                                  'SPEC200_PYATS_ENABLE_PASSWORD'}
            and all(isinstance(v, str) and 0 < len(v) <= 4096 for v in credentials.values()),
            'scoped_credentials_required')
    os.environ.update(credentials)
    os.environ['PYTHON_DOTENV_DISABLED'] = '1'
    os.environ['PYATS_MCP_DYNAMIC_ONLY'] = '1'
    os.environ['PYATS_TESTBED_PATH'] = ''
    os.environ['PYATS_MCP_LOG_STDOUT'] = '0'
    os.environ['PYATS_MCP_ARTIFACTS_DIR'] = str(evidence_directory)
    adapter = load_module('_selected_genie_adapter', HERE / 'native_adapter.py')
    # Validate the minimal document and actual installed plugin before importing
    # the selected server; never import an arbitrary adapter from tool input.
    adapter.connection.prepare_device(d['document'], device,
        document_sha256=d['document_sha256'], endpoint_sha256=d['endpoint_sha256'])
    sys.path.insert(0, str(Path(c['policy_file']).parent))
    server = load_module('pyats_mcp_server', c['policy_file'])
    _binding = adapter.FrozenCapture(d['document'], device,
        document_sha256=d['document_sha256'], endpoint_sha256=d['endpoint_sha256'],
        server=server, source_sha256=c['policy_sha256'])
    with _binding.capture_context(device, command, timeout=timeout,
                                   evidence_directory=evidence_directory) as raw:
        yield raw


def parse_captured(device, command, *, output):
    require(_binding is not None, 'capture_required')
    return _binding.parse_captured(device, command, output=output)


class Requests:
    """Single owner, immutable request digest, persistent unknown-outcome latch."""
    def __init__(self, root):
        self.root = private_root(root)
        self.lock = os.open(self.root / 'collection.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        info = os.fstat(self.lock)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1 and not info.st_mode & 0o077, 'private_lock_required')
        path = self.root / 'collections.sqlite'
        if path.exists() or path.is_symlink():
            private_bytes(path, limit=64 * LIMIT)
        self.db = sqlite3.connect(path, timeout=5)
        os.chmod(path, 0o600)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL, response TEXT NOT NULL)')
        self.db.commit()

    def close(self):
        self.db.close()
        os.close(self.lock)

    def own(self):
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def recover(self):
        # Caller holds the process lock. Never run a pending request again; child
        # deadlines still bound surviving children after owner loss.
        for rid, body in self.db.execute("SELECT id,response FROM requests WHERE state='pending'").fetchall():
            response = json.loads(body)
            response.update(state='unknown', reason='owner_lost_no_replay')
            self.save(rid, response)

    def save(self, rid, response):
        self.db.execute('UPDATE requests SET state=?,response=? WHERE id=?',
                        (response['state'], canonical(response).decode(), rid))
        self.db.commit()

    def get(self, rid):
        row = self.db.execute('SELECT digest,response FROM requests WHERE id=?', (rid,)).fetchone()
        return (row[0], json.loads(row[1])) if row else None


def request_id(value):
    require(str(uuid.UUID(value)) == value, 'canonical_request_id_required')
    return value


def status(root, rid):
    request_id(rid)
    db = Requests(root)
    try:
        if db.own():
            db.recover()
        row = db.get(rid)
        require(row is not None, 'request_not_found')
        return row[1]
    finally:
        db.close()


def collect_request(root, rid, capability_path, pin):
    request_id(rid)
    db = Requests(root)
    request_digest = digest(canonical({'capability_sha256': pin}))
    try:
        owns = db.own()
        if owns:
            db.recover()
        old = db.get(rid)
        if old:
            require(old[0] == request_digest, 'request_conflict')
            return old[1]
        require(owns, 'collector_busy')
        require(db.db.execute("SELECT count(*) FROM requests WHERE state IN ('pending','unknown')").fetchone()[0] == 0,
                'prior_collection_unknown')
        c = load_capability(capability_path, pin)
        directory = db.root / rid
        directory.mkdir(mode=0o700)  # Never reuse an unregistered evidence directory.
        response = {'schema_version': 1, 'request_id': rid, 'snapshot_id': rid,
                    'classification': 'private', 'state': 'pending', 'started_at': utc(),
                    'finished_at': None, 'profile': c['profile'], 'capability_sha256': pin,
                    'artifact_ref': rid, 'observations': [], 'complete': False}
        db.db.execute('INSERT INTO requests VALUES (?,?,?,?)',
                      (rid, request_digest, 'pending', canonical(response).decode()))
        db.db.commit()  # Durable before importing/starting the collector.
        write_new(directory / 'request.json', {'request_id': rid, 'capability_sha256': pin,
                                               'capability': c})
        collector = load_module('_durable_genie_collector', HERE / 'collector.py')
        environment = {**{k: v for k, v in os.environ.items() if k in
                         ('HOME', 'PATH', 'TMPDIR', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR')},
                       'NETCLAW_GENIE_COLLECTOR_CAPABILITY': str(capability_path),
                       'NETCLAW_GENIE_COLLECTOR_CAPABILITY_SHA256': pin,
                       'PYTHONDONTWRITEBYTECODE': '1'}
        result = collector.collect(list(c['devices']), Path(__file__).resolve(), c['parser_version'],
                                   evidence_root=directory, profile=c['profile'], child_env=environment)
        # Raw, parsed fields and normalization never enter this closed envelope.
        write_new(directory / 'private-result.json', result)
        observations = []
        for o in result['observations']:
            source = {'runtime_sha256': digest(canonical([c['runtime_executable'], c['runtime_prefix']])),
                      'policy_sha256': c['policy_sha256'], 'inventory_sha256': c['inventory_sha256'],
                      'endpoint_sha256': c['devices'][o['device_ref']]['endpoint_sha256']}
            raw_file = directory / o['artifact_ref'] / 'raw'
            observations.append({k: o[k] for k in ('id', 'device_ref', 'command', 'command_index',
                'started_at', 'finished_at', 'outcome', 'parser_version', 'artifact_ref',
                'failure_reason', 'capture_outcome_unknown', 'cleanup_outcome_unknown')}
                | {'snapshot_id': rid, 'source': source,
                   'sha256': digest(raw_file.read_bytes()) if raw_file.exists() else None})
        unknown = any(o['capture_outcome_unknown'] or o['cleanup_outcome_unknown']
                      or o['outcome'] == 'timeout' for o in observations)
        response.update(state='unknown' if unknown else 'complete', finished_at=utc(),
                        observations=observations, complete=result['complete'],
                        scheduled_reads=len(c['devices']) * len(collector.facts.PROFILES[c['profile']][0]),
                        attempted_reads=len(observations))
        write_new(directory / 'response.json', response)
        db.save(rid, response)
        return response
    finally:
        db.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('collect', 'status'))
    parser.add_argument('--state-root', required=True)
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--capability')
    parser.add_argument('--capability-sha256')
    args = parser.parse_args()
    try:
        value = (status(args.state_root, args.request_id) if args.action == 'status' else
                 collect_request(args.state_root, args.request_id, args.capability, args.capability_sha256))
        print(json.dumps(value))
    except Exception as error:
        # Only our bounded refusal names escape; no native exception/credential text.
        reason = str(error)
        if not re.fullmatch('[a-z_]{1,80}', reason):
            reason = 'collection_failed_inspect_original_request'
        print(json.dumps({'schema_version': 1, 'request_id': args.request_id,
                          'state': 'refused', 'reason': reason}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
