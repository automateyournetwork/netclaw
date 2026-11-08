"""Explicit, installation-owned remote endpoints. No network discovery (R01)."""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import ssl
import stat
import uuid

from .runtime import private_dir

MAX_BYTES = 65536
PROFILES = {'in2n': 'in2n-tls-exporter-v1', 'en2n': 'en2n-tls13-v1'}
COMMON = {'id', 'direction', 'service', 'profile', 'routing_host', 'routing_port',
          'tls_server_name', 'ca_file', 'application_identity', 'application_trust', 'reservation_id'}
COMMON_V2 = (COMMON - {'reservation_id'}) | {'transport', 'address_ref'}
TRANSPORTS = {'direct_tcp', 'ngrok_tcp'}
LISTEN = {'bind_host', 'bind_port', 'cert_file', 'key_file'}
audit = logging.getLogger('n2n.audit')


def validate_cluster_endpoint(entry):
    """Separate R08 direct/mTLS profile; not an iN2N/eN2N registry entry.

    Application trust comes from the verified cluster manifest. This validates
    only the explicit local transport inputs; it confers no cluster enrollment.
    Legacy registry schemas deliberately continue to reject this service.
    """
    fields = {'profile', 'transport', 'routing_host', 'routing_port', 'tls_server_name',
              'ca_file', 'cert_file', 'key_file'}
    if not isinstance(entry, dict) or set(entry) != fields:
        raise ValueError('exact cluster endpoint fields required')
    if entry['profile'] != 'ncfed-cluster-mtls-v1' or entry['transport'] != 'direct_tcp':
        raise ValueError('cluster requires direct mutual TLS profile')
    if not _host(entry['routing_host']) or not _host(entry['tls_server_name']) or not _port(entry['routing_port']):
        raise ValueError('explicit cluster route and independent TLS name required')
    for field in ('ca_file', 'cert_file', 'key_file'):
        value = entry[field]
        if not isinstance(value, str) or '\x00' in value or len(value) > 4096 or not Path(value).is_absolute():
            raise ValueError('absolute local cluster certificate reference required')
    return entry


def _text(value, pattern, limit=253):
    return isinstance(value, str) and 0 < len(value) <= limit and re.fullmatch(pattern, value) is not None


def _host(value):
    if not isinstance(value, str) or len(value) > 253:
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return all(_text(label, r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?', 63)
                   for label in value.split('.'))


def _port(value):
    return type(value) is int and 1 <= value <= 65535


def _pem(value):
    if not isinstance(value, str) or len(value) > 16384:
        raise ValueError('bounded public CA certificate required')
    try:
        ssl.PEM_cert_to_DER_cert(value)
    except Exception:
        raise ValueError('public CA certificate PEM required') from None
    return value


def transport_kind(entry):
    """Schema1 is explicitly the legacy ngrok contract, never inferred from DNS."""
    return entry.get('transport', 'ngrok_tcp')


def entry_schema(entry):
    return 2 if 'transport' in entry or 'address_ref' in entry else 1


def validate_entry(entry, schema_version=None):
    if not isinstance(entry, dict) or entry.get('direction') not in ('listen', 'dial'):
        raise ValueError('endpoint direction must be listen or dial')
    schema_version = entry_schema(entry) if schema_version is None else schema_version
    keys = (COMMON_V2 if schema_version == 2 else COMMON) | (LISTEN if entry['direction'] == 'listen' else set())
    if set(entry) != keys:
        raise ValueError('endpoint fields are missing or unknown')
    if not _text(entry['id'], r'[a-z][a-z0-9_-]*', 64):
        raise ValueError('invalid endpoint ID')
    if entry['service'] not in PROFILES or entry['profile'] != PROFILES[entry['service']]:
        raise ValueError('strict service/profile mismatch')
    if not _host(entry['routing_host']) or not _port(entry['routing_port']) or not _host(entry['tls_server_name']):
        raise ValueError('explicit routing host/port and independent TLS name required')
    if schema_version == 2 and (not isinstance(entry['transport'], str) or entry['transport'] not in TRANSPORTS):
        raise ValueError('explicit direct_tcp or ngrok_tcp transport required')
    reference = entry['address_ref'] if schema_version == 2 else entry['reservation_id']
    if not _text(reference, r'[A-Za-z0-9_-]+', 128):
        raise ValueError('explicit stable address reference required; verify with provider separately')
    if not _text(entry['application_identity'], r'[A-Za-z0-9][A-Za-z0-9._/-]*', 128):
        raise ValueError('explicit application identity required')
    if entry['service'] == 'in2n':
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*/border', entry['application_identity']):
            raise ValueError('iN2N requires a Border application identity')
        _pem(entry['application_trust'])
    elif not _text(entry['application_trust'], r'[0-9a-f]{64}', 64):
        raise ValueError('eN2N requires an approved SHA256 application key fingerprint')
    for key in ('ca_file', 'cert_file', 'key_file'):
        if key in entry and (not isinstance(entry[key], str) or '\x00' in entry[key]
                             or len(entry[key]) > 4096 or not Path(entry[key]).is_absolute()):
            raise ValueError('local certificate references must be absolute paths')
    if entry['direction'] == 'listen':
        if not isinstance(entry['bind_host'], str):
            raise ValueError('explicit listener IP required')
        try:
            bind = ipaddress.ip_address(entry['bind_host'])
        except (ValueError, TypeError):
            raise ValueError('explicit listener IP required') from None
        if (not _port(entry['bind_port']) or bind.is_unspecified or bind.is_multicast
                or '%' in str(bind) or str(bind) == '255.255.255.255'):
            raise ValueError('listener must bind an exact unicast IP and port')
        if transport_kind(entry) == 'ngrok_tcp' and not bind.is_loopback:
            raise ValueError('ngrok upstream must be an explicit loopback listener')
    return entry


def validate(value, installation):
    if not isinstance(value, dict) or set(value) != {'schemaVersion','installationId','revision','entries'}:
        raise ValueError('registry fields are missing or unknown')
    if type(value['schemaVersion']) is not int or value['schemaVersion'] not in (1, 2):
        raise ValueError('unsupported endpoint registry schema')
    if not installation or value['installationId'] != installation:
        raise ValueError('foreign endpoint registry installation')
    if type(value['revision']) is not int or not 1 <= value['revision'] <= 2**53-1:
        raise ValueError('invalid registry revision')
    if not isinstance(value['entries'], list) or not 1 <= len(value['entries']) <= 128:
        raise ValueError('registry requires 1–128 entries')
    ids, addresses, listeners = set(), set(), set()
    for entry in value['entries']:
        validate_entry(entry, value['schemaVersion'])
        address = (entry['routing_host'].lower(), entry['routing_port'])
        if entry['id'] in ids or address in addresses:
            raise ValueError('duplicate registry ID or public address')
        ids.add(entry['id']); addresses.add(address)
        if entry['direction'] == 'listen':
            listener = (entry['bind_host'], entry['bind_port'])
            if listener in listeners:
                raise ValueError('services require distinct upstream listeners')
            listeners.add(listener)
    if len(json.dumps(value).encode()) > MAX_BYTES:
        raise ValueError('endpoint registry exceeds 64 KiB')
    return value


def _read(path):
    private_dir(Path(path).parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > MAX_BYTES):
            raise ValueError('owned private bounded file required')
        value = stream.read(MAX_BYTES + 1)
        if len(value) > MAX_BYTES:
            raise ValueError('private file too large')
        return value


def _atomic(path, data):
    path = Path(path)
    private_dir(path.parent)
    if len(data) > MAX_BYTES:
        raise ValueError('private file too large')
    if path.exists() or path.is_symlink():
        _read(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


class Registry:
    def __init__(self, path, installation):
        self.path = Path(path)
        self.installation = installation
        self.previous = self.path.with_name(self.path.name + '.previous')

    def load(self):
        return validate(json.loads(_read(self.path), object_pairs_hook=_unique), self.installation)

    @contextmanager
    def _lock(self):
        private_dir(self.path.parent)
        fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('invalid registry lock ownership')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _current(self, expected_revision):
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('expected_revision must be a nonnegative integer')
        try: current = self.load()
        except FileNotFoundError: current = None
        if (current['revision'] if current else 0) != expected_revision:
            raise ValueError('endpoint revision conflict; nothing changed')
        return current

    def _save(self, value, current, expected_revision):
        value = copy.deepcopy(value)
        value['revision'] = expected_revision + 1
        validate(value, self.installation)
        if current:
            _atomic(self.previous, json.dumps(current).encode())
        _atomic(self.path, json.dumps(value).encode())
        audit.info('endpoint_registry_updated installation=%s revision=%d', self.installation, value['revision'])
        return value

    def replace(self, value, *, expected_revision):
        validate(value, self.installation)
        with self._lock():
            return self._save(value, self._current(expected_revision), expected_revision)

    def update_address(self, entry_id, host, port, reservation_id, *, expected_revision):
        with self._lock():
            current = self._current(expected_revision)
            if not current:
                raise ValueError('registry does not exist')
            value = copy.deepcopy(current)
            matches = [e for e in value['entries'] if e['id'] == entry_id]
            if not matches:
                raise ValueError('endpoint ID not registered')
            reference_key = 'address_ref' if current['schemaVersion'] == 2 else 'reservation_id'
            matches[0].update(routing_host=host, routing_port=port, **{reference_key: reservation_id})
            return self._save(value, current, expected_revision)

    def recover(self, *, expected_revision):
        with self._lock():
            current = self._current(expected_revision)
            previous = validate(json.loads(_read(self.previous), object_pairs_hook=_unique), self.installation)
            return self._save(previous, current, expected_revision)

    def entry(self, entry_id, *, direction=None, service=None):
        matches = [e for e in self.load()['entries'] if e['id'] == entry_id]
        if (len(matches) != 1 or direction and matches[0]['direction'] != direction
                or service and matches[0]['service'] != service):
            raise ValueError('endpoint ID/service/direction mismatch')
        return matches[0]

    def status(self, document=None):
        value = self.load() if document is None else validate(document, self.installation)
        return {'schemaVersion': value['schemaVersion'], 'installationId': self.installation, 'revision': value['revision'],
                'services': [{key: entry[key] for key in ('id','service','direction','profile',
                             'routing_host','routing_port','tls_server_name','application_identity')}
                            | {'transport': transport_kind(entry), 'configured': True, 'tcp_reachable': None, 'tls_verified': False,
                               'authenticated': False, 'observation': 'not_observed'}
                            for entry in value['entries']]}


def export_bundle(entry):
    validate_entry(entry)
    ca = _pem(_read(entry['ca_file']).decode())
    schema_version = entry_schema(entry)
    public = {key: value for key, value in entry.items()
              if key in (COMMON_V2 if schema_version == 2 else COMMON) and key != 'ca_file'}
    public['direction'] = 'dial'
    return {'schemaVersion': schema_version, 'endpoint': public, 'tls_ca_pem': ca}


def import_bundle(registry, bundle, *, expected_revision):
    if (not isinstance(bundle, dict) or set(bundle) != {'schemaVersion','endpoint','tls_ca_pem'}
            or type(bundle['schemaVersion']) is not int or bundle['schemaVersion'] not in (1, 2)):
        raise ValueError('invalid public enrollment bundle')
    ca = _pem(bundle['tls_ca_pem'])
    entry = copy.deepcopy(bundle['endpoint'])
    if not isinstance(entry, dict) or entry.get('direction') != 'dial' or 'ca_file' in entry:
        raise ValueError('bundle must contain public dial metadata only')
    ca_path = registry.path.parent / ('ca-' + hashlib.sha256(ca.encode()).hexdigest() + '.pem')
    entry['ca_file'] = str(ca_path.absolute())
    validate_entry(entry, bundle['schemaVersion'])
    with registry._lock():
        current = registry._current(expected_revision)
        if current and current['schemaVersion'] != bundle['schemaVersion']:
            raise ValueError('cross-schema import requires explicit registry replacement')
        entries = copy.deepcopy(current['entries']) if current else []
        if any(e['id'] == entry['id'] for e in entries):
            raise ValueError('existing endpoint requires explicit replacement review')
        entries.append(entry)
        value = {'schemaVersion': bundle['schemaVersion'], 'installationId': registry.installation,
                 'revision': expected_revision + 1, 'entries': entries}
        validate(value, registry.installation)
        _atomic(ca_path, ca.encode())
        return registry._save(value, current, expected_revision)


def configured(env=None, runtime=None):
    """Absent selection is legacy; an invalid explicit selection never is."""
    env = os.environ if env is None else env
    path = env.get('N2N_ENDPOINT_REGISTRY')
    if not path:
        return None
    from .runtime import selected
    runtime = runtime or selected(env)
    runtime.fence()
    if not Path(path).is_absolute():
        raise ValueError('endpoint registry path must be absolute')
    registry = Registry(path, runtime.installation)
    registry.load()
    return registry
