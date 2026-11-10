"""Bounded cluster identity, offline enrollment signatures and durable HA marker."""
import base64
import copy
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

from ..certs import time_valid
from ..protected_contract import (
    ProtectedError, decode, encode, exact, ident, key_id, uuid_field,
)
from ..protected_runtime import private_directory, private_write

SCHEMA = 'netclaw.ncfed.cluster-manifest.v1'
MAX_DOCUMENT = 128 * 1024
PREFIX = b'netclaw.ncfed.ha/manifest/v1\0'


class HAError(ProtectedError):
    """Only a fixed code crosses an HA boundary; private errors remain local."""


def check(condition, code='invalid_ha_contract', status=400):
    if not condition:
        raise HAError(code, status)


def bounded_int(value, minimum, maximum):
    check(type(value) is int and minimum <= value <= maximum)


def host(value):
    check(isinstance(value, str) and 0 < len(value) <= 253
          and re.fullmatch(r'[A-Za-z0-9._:\-]+', value) is not None)


LISTEN_SERVICES = ('cluster', 'in2n')


def validate_listen(value):
    """Optional, default-off bind override from the PRIVATE ha-config (never the signed manifest).

    `{cluster: {host, port}, in2n: {host, port}}`, each entry optional. `host` must be an IP literal (a sandbox
    loopback address, a private address or 0.0.0.0); names are refused so no resolver is involved. Only the
    listening socket changes: dialing, TLS server_name, member targets and every signed value stay on the manifest.
    """
    check(isinstance(value, dict) and 1 <= len(value) <= len(LISTEN_SERVICES) and set(value) <= set(LISTEN_SERVICES),
          'invalid_ha_listen')
    for entry in value.values():
        check(isinstance(entry, dict) and set(entry) == {'host', 'port'}, 'invalid_ha_listen')
        check(isinstance(entry['host'], str) and len(entry['host']) <= 45, 'invalid_ha_listen')
        try:
            ipaddress.ip_address(entry['host'])
        except ValueError:
            raise HAError('invalid_ha_listen') from None
        check(type(entry['port']) is int and 1 <= entry['port'] <= 65535, 'invalid_ha_listen')
    return value


def listen_address(listen, service, advertised):
    """(host, port) to bind: the override when configured, else the signed advertised address."""
    entry = (listen or {}).get(service)
    return (entry['host'], entry['port']) if entry else (advertised['host'], advertised['port'])


def endpoint(value, scheme):
    check(isinstance(value, str) and len(value) <= 1024)
    try:
        parsed = urlsplit(value)
        check(parsed.scheme == scheme and parsed.hostname
              and not parsed.username and not parsed.password
              and not parsed.query and not parsed.fragment)
        host(parsed.hostname)
        if parsed.port is not None:
            bounded_int(parsed.port, 1, 65535)
        check(parsed.path in ('', '/') if scheme == 'https' else parsed.path == '/mobile/ws')
    except (ValueError, TypeError):
        raise HAError('invalid_endpoint') from None


class Manifest:
    """Validated value object. Construction does not establish signer trust."""
    def __init__(self, value):
        try:
            check(len(encode(value)) <= MAX_DOCUMENT, 'manifest_capacity')
            exact(value, 'schema_version cluster_id generation organization revision nodes limits')
            check(type(value['schema_version']) is int and value['schema_version'] == 1)
            uuid_field(value['cluster_id']); uuid_field(value['generation'])
            ident(value['organization'])
            bounded_int(value['revision'], 1, 2**53 - 1)
            check(isinstance(value['nodes'], list) and 1 <= len(value['nodes']) <= 3)
            seen = {field: set() for field in ('node_id', 'installation_id', 'key_id')}
            for node in value['nodes']:
                exact(node, 'node_id installation_id identity key_id certificate role endpoints')
                uuid_field(node['node_id']); uuid_field(node['installation_id'])
                ident(node['identity'])
                check(node['role'] == 'border', 'cluster_role_required')
                check(node['installation_id'] != value['cluster_id'], 'identity_role_collision')
                check(isinstance(node['certificate'], str) and len(node['certificate']) <= 8192)
                check(key_id(node['certificate']) == node['key_id'], 'node_key_mismatch')
                check(time_valid(node['certificate']), 'node_certificate_expired')
                for field, values in seen.items():
                    check(node[field] not in values, 'duplicate_node_identity')
                    values.add(node[field])
                exact(node['endpoints'], 'cluster in2n https wss')
                for service in ('cluster', 'in2n'):
                    address = node['endpoints'][service]
                    exact(address, 'host port server_name')
                    host(address['host']); host(address['server_name'])
                    bounded_int(address['port'], 1, 65535)
                endpoint(node['endpoints']['https'], 'https')
                endpoint(node['endpoints']['wss'], 'wss')
            limits = value['limits']
            exact(limits, 'leader_lease_s renewal_s admission_ms clock_uncertainty_ms max_operations max_members')
            bounded_int(limits['leader_lease_s'], 6, 60)
            bounded_int(limits['renewal_s'], 1, limits['leader_lease_s'] // 3)
            bounded_int(limits['admission_ms'], 100, 10000)
            bounded_int(limits['clock_uncertainty_ms'], 0, 1000)
            bounded_int(limits['max_operations'], 1, 1024)
            bounded_int(limits['max_members'], 1, 32)
            self._value = copy.deepcopy(value)
            self.anchor_key_id = None
        except HAError:
            raise
        except (ProtectedError, ValueError, TypeError, KeyError):
            raise HAError('invalid_ha_contract') from None

    @property
    def value(self):
        return copy.deepcopy(self._value)

    @property
    def cluster_id(self):
        return self._value['cluster_id']

    @property
    def generation(self):
        return self._value['generation']

    @property
    def revision(self):
        return self._value['revision']

    @property
    def nodes(self):
        return copy.deepcopy(self._value['nodes'])

    @property
    def limits(self):
        return dict(self._value['limits'])

    @property
    def audience(self):
        return {'cluster_id': self.cluster_id, 'generation': self.generation}

    def node(self, node_id):
        rows = [n for n in self.nodes if n['node_id'] == node_id]
        check(len(rows) == 1, 'node_not_enrolled', 403)
        return rows[0]


def sign_manifest(value, private_key):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    manifest = Manifest(value)
    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    check(isinstance(key, ec.EllipticCurvePrivateKey) and isinstance(key.curve, ec.SECP256R1))
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    body = {'schema': SCHEMA, 'manifest': manifest.value}
    signature = key.sign(PREFIX + encode(body), ec.ECDSA(hashes.SHA256()))
    return dict(body, signature={'algorithm': 'ecdsa-p256-sha256',
                                'key_id': hashlib.sha256(public).hexdigest(),
                                'value': base64.urlsafe_b64encode(signature).rstrip(b'=').decode()})


def verify_manifest(envelope, anchor_certificate, *, expected_key_id, minimum_revision=1):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    try:
        if isinstance(envelope, (str, bytes)):
            envelope = decode(envelope, MAX_DOCUMENT)
        check(len(encode(envelope)) <= MAX_DOCUMENT, 'manifest_capacity')
        exact(envelope, 'schema manifest signature')
        check(envelope['schema'] == SCHEMA, 'invalid_manifest_schema')
        signature = envelope['signature']
        exact(signature, 'algorithm key_id value')
        check(signature['algorithm'] == 'ecdsa-p256-sha256')
        check(signature['key_id'] == expected_key_id == key_id(anchor_certificate), 'manifest_anchor_mismatch', 403)
        check(time_valid(anchor_certificate), 'manifest_anchor_expired', 403)
        check(isinstance(signature['value'], str) and re.fullmatch(r'[A-Za-z0-9_-]{8,200}', signature['value']))
        raw = base64.urlsafe_b64decode(signature['value'] + '=' * (-len(signature['value']) % 4))
        check(base64.urlsafe_b64encode(raw).rstrip(b'=').decode() == signature['value'])
        public = x509.load_pem_x509_certificate(anchor_certificate.encode()).public_key()
        check(isinstance(public, ec.EllipticCurvePublicKey) and isinstance(public.curve, ec.SECP256R1))
        public.verify(raw, PREFIX + encode({'schema': SCHEMA, 'manifest': envelope['manifest']}), ec.ECDSA(hashes.SHA256()))
        result = Manifest(envelope['manifest'])
        check(result.revision >= minimum_revision, 'stale_manifest', 409)
        result.anchor_key_id = expected_key_id
        return result
    except HAError:
        raise
    except Exception:
        raise HAError('invalid_manifest_signature', 403) from None


def read_private(path, maximum=MAX_DOCUMENT):
    path = Path(path)
    check(path.absolute() == path.resolve(), 'unsafe_private_file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        check(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
              and not info.st_mode & 0o077 and info.st_size <= maximum, 'unsafe_private_file')
        raw = stream.read(maximum + 1)
        check(len(raw) <= maximum, 'unsafe_private_file')
        return raw


def install_marker(home, manifest):
    home = private_directory(home)
    path = home / 'ha-required.json'
    marker = {'schema_version': 1, **manifest.audience}
    if path.exists() or path.is_symlink():
        check(decode(read_private(path)) == marker, 'cluster_changed', 409)
        return
    private_write(path, encode(marker))


def require_ha(home, manifest, *, adapter_ready=False):
    path = Path(home) / 'ha-required.json'
    if not path.exists() and not path.is_symlink():
        check(manifest is None, 'ha_marker_missing', 503)
        return False
    marker = decode(read_private(path))
    check(manifest is not None, 'ha_required', 503)
    check(marker == {'schema_version': 1, **manifest.audience}, 'cluster_changed', 409)
    check(adapter_ready, 'ha_runtime_unqualified', 503)
    return True
