#!/usr/bin/env python3
"""Trusted-native one-use protected member enrollment; never starts execution.

Invoke with the qualified Python's -I -B flags. A failed attempt leaves its fresh
home and durable unknown record intact. `status` only reads retained local files;
it does not reconnect, reenroll, fetch Border evidence or create a full profile.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mcp-servers/protocol-mcp'))
from bgp.federation.protected_contract import (ProtectedError, decode, encode, exact,
                                              key_id, require, validate_binding)
from bgp.federation.protected_owner import private_directory, private_file, write_private


def owned_path(value):
    path = Path(value)
    require(path.is_absolute() and path == path.resolve(), 'canonical_absolute_path_required')
    return path


def read_packet(path):
    packet = decode(private_file(owned_path(path), 65536))
    exact(packet, 'schemaVersion runtime_kind member_id border registration')
    require(type(packet['schemaVersion']) is int and packet['schemaVersion'] == 1,
            'enrollment_packet_schema_invalid')
    require(packet['runtime_kind'] in ('openclaw', 'hermes'), 'unsupported_runtime_kind')
    validate_binding(packet['border'], 'border')
    require(isinstance(packet['member_id'], str) and
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]{0,127}',
                         packet['member_id']) is not None, 'enrollment_member_id_invalid')
    from bgp.federation.endpoint_registry import validate_entry
    entry = validate_entry(packet['registration'], 2)
    require(entry['direction'] == 'dial' and entry['service'] == 'in2n'
            and entry['transport'] == 'direct_tcp'
            and entry['application_identity'] == packet['border']['identity']
            == packet['member_id'].split('/', 1)[0] + '/border', 'enrollment_binding_mismatch')
    ca = private_file(owned_path(entry['ca_file']), 65536)
    # Public transport trust is the sole copied input. It cannot be a secret
    # bundle or arbitrary file: require exactly one bounded X.509 certificate.
    from cryptography import x509
    require(ca.count(b'-----BEGIN CERTIFICATE-----') == 1
            and ca.count(b'-----END CERTIFICATE-----') == 1
            and re.fullmatch(rb'\s*-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----\s*', ca),
            'transport_ca_certificate_required')
    x509.load_pem_x509_certificate(ca)
    return packet, ca


def enrollment_status(home):
    """Read-only local evidence. Unknown stays unknown, even with a saved generation."""
    home = owned_path(home)
    private_directory(home)
    installation = decode(private_file(home / 'netclaw-hud/installation.json'))['installationId']
    owner = decode(private_file(home / 'netclaw-federation/owner.json'))
    require(owner.get('installationId') == installation and owner.get('home') == str(home)
            and owner.get('kind') in ('openclaw', 'hermes'), 'enrollment_owner_mismatch')
    attempt_path = home / 'netclaw-federation/protected-enrollment-attempt.json'
    try:
        attempt = decode(private_file(attempt_path, 65536))
    except FileNotFoundError:
        return {'state': 'not_attempted', 'installation_id': installation,
                'replay_allowed': False, 'enrollment_generation': None}
    require(attempt.get('schemaVersion') == 1 and attempt.get('installation_id') == installation
            and attempt.get('state') in ('outcome_unknown', 'enrolled'), 'enrollment_attempt_invalid')
    validate_binding(attempt['border'], 'border')
    certificate = private_file(home / 'n2n/keys/self.crt', 65536).decode('ascii')
    require(key_id(certificate) == attempt['member_key_id'], 'enrollment_member_key_changed')
    try:
        enrollment = decode(private_file(home / 'n2n/keys/protected/enrollment.json'))
    except FileNotFoundError:
        enrollment = None
    if enrollment is not None:
        require(enrollment.get('installation_id') == installation
                and enrollment.get('member_id') == attempt['member_id'], 'enrollment_generation_mismatch')
        validate_binding(dict(enrollment, key_id=attempt['member_key_id']), 'member')
    if attempt['state'] == 'enrolled':
        require(enrollment is not None and enrollment['enrollment_generation'] == attempt['enrollment_generation'],
                'enrollment_generation_mismatch')
    return {'state': attempt['state'], 'attempt_id': attempt['attempt_id'],
            'installation_id': installation, 'member_id': attempt['member_id'],
            'member_key_id': attempt['member_key_id'], 'border': attempt['border'],
            'enrollment_generation': enrollment['enrollment_generation'] if enrollment else None,
            'local_generation_retained': enrollment is not None, 'replay_allowed': False,
            'attempt_sha256': hashlib.sha256(encode(attempt)).hexdigest()}


async def enroll(home, packet_path, token_path):
    packet, ca = read_packet(packet_path)
    token = private_file(owned_path(token_path), 256).decode('ascii').strip()
    require(re.fullmatch(r'in2n_[A-Za-z0-9_-]{32}', token) is not None, 'enrollment_token_required')
    home = owned_path(home)
    private_directory(home.parent)
    # Never initialize, repair or select an existing home, even when it looks empty.
    home.mkdir(mode=0o700, exist_ok=False)
    kind = packet['runtime_kind']
    env = {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'NETCLAW_RUNTIME': kind, 'N2N_BASE_DIR': str(home / 'n2n'),
           'N2N_ROLE': 'member', 'N2N_RISK_NAME': packet['member_id'].split('/', 1)[0],
           'N2N_MEMBER_ID': packet['member_id'], 'N2N_ENABLED_STACKS': 'in2n',
           'N2N_PROTECTED_OPERATIONS': '1', 'N2N_CERT_MODE': 'enforce',
           'N2N_RISK_MODE': 'production', 'N2N_STRICT_ALL': '1',
           'PYTHON_DOTENV_DISABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1'}
    if kind == 'hermes':
        env['HERMES_HOME'] = str(home)
    else:
        env.update(OPENCLAW_HOME=str(home), OPENCLAW_STATE_DIR=str(home),
                   OPENCLAW_CONFIG_PATH=str(home / 'openclaw.json'))
    os.environ.clear(); os.environ.update(env)
    from bgp.federation.runtime import selected
    from bgp.federation.endpoint_registry import Registry
    from bgp.federation.manager import FederationManager
    from bgp.federation.service import FederationService
    runtime = selected(initialize=True).fence(initialize=True)
    ca_path = runtime.state / 'enrollment-transport-ca.pem'
    write_private(ca_path, ca)
    entry = dict(packet['registration'], ca_file=str(ca_path))
    registry = Registry(runtime.state / 'member-registry.json', runtime.installation)
    registry.replace({'schemaVersion': 2, 'installationId': runtime.installation,
                      'revision': 1, 'entries': [entry]}, expected_revision=0)
    os.environ.update(N2N_ENDPOINT_REGISTRY=str(registry.path), N2N_BORDER_REGISTRY_ID=entry['id'])
    write_private(runtime.state / 'enrollment-packet.json', {
        'schemaVersion': 1, 'packet_sha256': hashlib.sha256(encode(packet)).hexdigest(),
        'transport_ca_sha256': hashlib.sha256(ca).hexdigest(),
        'runtime_kind': kind, 'member_id': packet['member_id'],
        'border': packet['border'], 'registration': entry})
    manager = FederationManager(base_dir=str(runtime.base))
    try:
        service = FederationService(local_as=0, router_id='0.0.0.0',
                                    display_name=packet['member_id'], manager=manager)
        service.risk.set_role('member', risk_name=env['N2N_RISK_NAME'],
                              self_member_id=packet['member_id'], enabled_stacks='in2n')
        await service.enroll_protected_member(registration=entry, registry_revision=1,
                                              border_binding=packet['border'], enrollment_token=token)
    finally:
        manager.close()
    return enrollment_status(home)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    start = sub.add_parser('enroll')
    start.add_argument('--packet', required=True)
    start.add_argument('--token-file', required=True)
    sub.add_parser('status')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        require(sys.flags.isolated and sys.dont_write_bytecode, 'isolated_python_required')
        result = (asyncio.run(enroll(args.home, args.packet, args.token_file))
                  if args.action == 'enroll' else enrollment_status(args.home))
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:
        # Transport/decoder messages can contain untrusted material; emit only
        # fixed contract codes. The durable record is the recovery authority.
        code = (exc.code if isinstance(exc, ProtectedError)
                and re.fullmatch(r'[a-z0-9_]{1,80}', exc.code) else 'enrollment_unavailable')
        print(json.dumps({'error': code, 'replay_allowed': False}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
