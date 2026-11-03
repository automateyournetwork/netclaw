#!/usr/bin/env python3
"""Exact-version R04 workload-identity projection. Never logs secret payloads."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import urllib.request
import uuid


class Refused(ValueError):
    pass


def need(test, code):
    if not test:
        raise Refused(code)


def pairs(rows):
    result = {}
    for key, value in rows:
        need(key not in result, 'duplicate_field')
        result[key] = value
    return result


def private(path, maximum=65536):
    p = Path(path)
    need(p.is_absolute() and p.resolve() == p, 'canonical_path_required')
    with os.fdopen(os.open(p, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
             and not info.st_mode & 0o077 and info.st_size <= maximum, 'private_file_required')
        return stream.read(maximum + 1)


def validate(config):
    need(isinstance(config, dict) and set(config) == {'schemaVersion', 'installationId', 'home', 'role', 'secrets'}, 'projection_fields_invalid')
    need(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'schema_invalid')
    need(str(uuid.UUID(config['installationId'])) == config['installationId'], 'installation_invalid')
    need(config['role'] in ('border', 'member'), 'role_invalid')
    home = Path(config['home'])
    need(home.is_absolute() and home.resolve() == home, 'canonical_home_required')
    expected = {'operator'} if config['role'] == 'border' else {'netbox', 'guard'}
    need(isinstance(config['secrets'], dict) and set(config['secrets']) == expected, 'role_secret_scope_invalid')
    run = None
    for name, value in config['secrets'].items():
        need(isinstance(value, dict) and set(value) == {'version', 'payloadSha256'}, 'secret_fields_invalid')
        match = re.fullmatch(r'(projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/secrets/netclaw-r04-\d{8}-[a-z0-9]{4,6})-' + name + r'/versions/[1-9][0-9]*', value['version'])
        need(match is not None, 'exact_r04_version_required')
        need(run is None or run == match.group(1), 'mixed_run_secrets_refused')
        run = match.group(1)
        need(re.fullmatch('[a-f0-9]{64}', value['payloadSha256']), 'digest_invalid')
    return config


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Refused('redirect_refused')


def get(url, headers):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(urllib.request.Request(url, headers=headers), timeout=10) as response:
        raw = response.read(65537)
    need(len(raw) <= 65536, 'response_overflow')
    return json.loads(raw, object_pairs_hook=pairs)


def value_text(value):
    need(isinstance(value, str) and 1 <= len(value) <= 4096 and value.isascii()
         and re.fullmatch(r'[A-Za-z0-9_./+@=-]+', value), 'secret_value_invalid')
    return value


def retrieve(config, request=get):
    validate(config)
    token = request('http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token', {'Metadata-Flavor': 'Google'})
    need(isinstance(token, dict) and isinstance(token.get('access_token'), str) and len(token['access_token']) <= 8192, 'metadata_token_invalid')
    outputs = {}
    for name, ref in config['secrets'].items():
        response = request('https://secretmanager.googleapis.com/v1/' + ref['version'] + ':access', {'Authorization': 'Bearer ' + token['access_token']})
        raw = base64.b64decode(response['payload']['data'], validate=True)
        need(len(raw) <= 16384 and hashlib.sha256(raw).hexdigest() == ref['payloadSha256'], 'payload_digest_mismatch')
        payload = json.loads(raw, object_pairs_hook=pairs)
        need(isinstance(payload, dict) and set(payload) == {'schemaVersion', 'installationId', 'environment'}
             and type(payload['schemaVersion']) is int and payload['schemaVersion'] == 1
             and payload['installationId'] == config['installationId'], 'payload_identity_mismatch')
        env = payload['environment']
        keys = {'operator': {'NETCLAW_PROTECTED_OPERATOR_TOKEN'}, 'netbox': {'NETBOX_TOKEN'},
                'guard': {'ANTHROPIC_API_KEY', 'DEFENSECLAW_GATEWAY_TOKEN'}}[name]
        need(isinstance(env, dict) and set(env) == keys, 'secret_environment_refused')
        for key, value in env.items(): value_text(value)
        if name == 'operator':
            need(re.fullmatch('[A-Za-z0-9_-]{43}', env['NETCLAW_PROTECTED_OPERATOR_TOKEN']), 'operator_token_invalid')
            target = 'protected-operator.env'
        elif name == 'netbox':
            target = 'broker-secrets/netbox.env'
        else:
            need(re.fullmatch('[A-Za-z0-9_-]{43}', env['DEFENSECLAW_GATEWAY_TOKEN'])
                 and env['ANTHROPIC_API_KEY'] != env['DEFENSECLAW_GATEWAY_TOKEN'], 'guard_capability_invalid')
            outputs['guard-capability'] = (env['DEFENSECLAW_GATEWAY_TOKEN'] + '\n').encode()
            target = 'guard-secrets/guard.env'
        outputs[target] = ''.join(key + '=' + env[key] + '\n' for key in sorted(env)).encode('ascii')
    return outputs


def owned_directory(p, create=False):
    if create and not p.exists(): p.mkdir(mode=0o700)
    info = p.stat()
    need(p.resolve() == p and stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
         and not info.st_mode & 0o077, 'private_home_required')


def project(config, outputs):
    home = Path(config['home']); directory = home / 'netclaw-federation'
    owned_directory(home); owned_directory(directory)
    installation = json.loads(private(home / 'netclaw-hud/installation.json'), object_pairs_hook=pairs)
    need(installation == {'schemaVersion': 1, 'installationId': config['installationId']}, 'installation_mismatch')
    expected = {'protected-operator.env'} if config['role'] == 'border' else {'broker-secrets/netbox.env', 'guard-secrets/guard.env', 'guard-capability'}
    need(set(outputs) == expected, 'projection_targets_refused')
    # Check ALL existing files before creating any missing one. Restart can only
    # restore identical bytes; rotation requires a new explicit installation plan.
    for name, content in outputs.items():
        p = directory / name
        if p.exists() or p.is_symlink(): need(private(p) == content, 'existing_secret_changed')
    for name, content in outputs.items():
        p = directory / name
        if p.parent != directory: owned_directory(p.parent, create=True)
        if p.exists(): continue
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        fd = os.open(p.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = validate(json.loads(private(args.config), object_pairs_hook=pairs))
    project(config, retrieve(config))


if __name__ == '__main__':
    try: main()
    except Exception:
        print('R04 secret projection refused; inspect private evidence.', file=sys.stderr)
        sys.exit(1)
