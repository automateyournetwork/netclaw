#!/usr/bin/env python3
"""Project one exact cloud-only operator token to its fixed private .env file.

No latest-version lookup, ambient credentials, subprocess, identity/archive replay
or logging of responses. The service runs as the same dedicated UID as Border/HUD.
"""
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


def need(value, code):
    if not value:
        raise Refused(code)


def pairs(rows):
    result = {}
    for key, value in rows:
        need(key not in result, 'duplicate_field')
        result[key] = value
    return result


def read_private(path):
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path, 'canonical_path_required')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077 and info.st_size <= 65536, 'private_file_required')
        return stream.read(65537)


def validate(config):
    need(isinstance(config, dict) and set(config) == {'schemaVersion', 'installationId', 'home', 'version', 'payloadSha256'}, 'projection_fields_invalid')
    need(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'schema_invalid')
    need(str(uuid.UUID(config['installationId'])) == config['installationId'], 'installation_invalid')
    need(re.fullmatch(r'projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/secrets/netclaw-r03-\d{8}-[a-z0-9]{4,8}-operator/versions/[1-9][0-9]*', config['version']), 'exact_r03_version_required')
    need(re.fullmatch('[a-f0-9]{64}', config['payloadSha256']), 'digest_invalid')
    home = Path(config['home'])
    need(home.is_absolute() and home.resolve() == home, 'canonical_home_required')
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


def retrieve(config, request=get):
    token = request('http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token', {'Metadata-Flavor': 'Google'})
    need(isinstance(token, dict) and isinstance(token.get('access_token'), str) and len(token['access_token']) <= 8192, 'metadata_token_invalid')
    response = request('https://secretmanager.googleapis.com/v1/' + config['version'] + ':access', {'Authorization': 'Bearer ' + token['access_token']})
    raw = base64.b64decode(response['payload']['data'], validate=True)
    need(len(raw) <= 4096 and hashlib.sha256(raw).hexdigest() == config['payloadSha256'], 'payload_digest_mismatch')
    payload = json.loads(raw, object_pairs_hook=pairs)
    need(isinstance(payload, dict) and set(payload) == {'schemaVersion', 'installationId', 'environment'} and type(payload['schemaVersion']) is int and payload['schemaVersion'] == 1 and payload['installationId'] == config['installationId'], 'payload_identity_mismatch')
    env = payload['environment']
    need(isinstance(env, dict) and set(env) == {'NETCLAW_PROTECTED_OPERATOR_TOKEN'}, 'cloud_only_environment_required')
    value = env['NETCLAW_PROTECTED_OPERATOR_TOKEN']
    need(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_-]{43}', value), 'operator_token_invalid')
    return ('NETCLAW_PROTECTED_OPERATOR_TOKEN=' + value + '\n').encode('ascii')


def project(config, content):
    home = Path(config['home'])
    directory = home / 'netclaw-federation'
    for path in (home, directory):
        info = path.stat()
        need(path.resolve() == path and stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'private_home_required')
    installation = json.loads(read_private(home / 'netclaw-hud/installation.json'), object_pairs_hook=pairs)
    need(installation == {'schemaVersion': 1, 'installationId': config['installationId']}, 'installation_mismatch')
    target = directory / 'protected-operator.env'
    if target.exists() or target.is_symlink():
        # A new revision/rotation is a separately reviewed action; never silently
        # replace live credentials or initial identity state during restart.
        need(read_private(target) == content, 'existing_operator_token_changed')
        return
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = validate(json.loads(read_private(args.config), object_pairs_hook=pairs))
    project(config, retrieve(config))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('R03 operator secret projection refused.', file=sys.stderr)
        sys.exit(1)
