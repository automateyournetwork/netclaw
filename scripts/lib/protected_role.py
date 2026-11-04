"""Explicit selected-role launch contract. No provisioning, secret lookup or fallback."""
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import types
from urllib.parse import urlsplit
import uuid


class RoleRefused(ValueError):
    pass


def need(value, code):
    if not value:
        raise RoleRefused(code)


def exact(value, fields):
    need(isinstance(value, dict) and set(value) == set(fields.split()), 'role_fields_invalid')


def pairs(rows):
    result = {}
    for key, value in rows:
        need(key not in result, 'duplicate_field')
        result[key] = value
    return result


def path(value):
    need(isinstance(value, str) and len(value) <= 4096 and '\x00' not in value, 'path_invalid')
    p = Path(value)
    need(p.is_absolute() and str(p) == value and p.resolve() == p, 'canonical_path_required')
    return p


def private_bytes(p, maximum=1048576):
    p = path(str(p))
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
             and not info.st_mode & 0o077 and info.st_size <= maximum, 'private_file_required')
        return stream.read(maximum + 1)


def document(p):
    return json.loads(private_bytes(p), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RoleRefused('invalid_number')))


def hashed(data, expected):
    need(isinstance(expected, str) and re.fullmatch('[a-f0-9]{64}', expected), 'digest_invalid')
    need(hashlib.sha256(data).hexdigest() == expected, 'content_changed')


def immutable(p):
    p = path(str(p)); info = p.stat()
    need(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o022, 'immutable_source_required')
    # Root-owned source is immutable to the non-root service. Local qualification
    # may instead use an owner-readable, non-writable frozen source copy.
    need(info.st_uid in (0, os.getuid()) and (info.st_uid != os.getuid() or not info.st_mode & 0o200), 'immutable_source_required')
    return p.read_bytes()


def executable(value):
    # A venv interpreter is normally a symlink; preserve its invocation path so
    # Python selects that venv, while pinning the immutable resolved binary.
    need(isinstance(value, str) and Path(value).is_absolute() and str(Path(value)) == value,
         'python_path_invalid')
    p = Path(value)
    need(p.parent.resolve() == p.parent and os.access(p, os.X_OK), 'python_path_invalid')
    return immutable(p.resolve())


def immutable_directory(directory):
    info = directory.stat()
    need(directory.resolve() == directory and stat.S_ISDIR(info.st_mode)
         and not info.st_mode & 0o022 and info.st_uid in (0, os.getuid())
         and (info.st_uid != os.getuid() or not info.st_mode & 0o200), 'immutable_source_required')


def validate_python_environment(cfg):
    root = path(cfg['python_env'])
    python = Path(cfg['python'])
    need(python.parent == root / 'bin' and python.name in ('python', 'python3', 'python3.12'), 'python_environment_mismatch')
    raw = private_bytes(path(cfg['python_env_manifest']), 8 * 1024 * 1024); hashed(raw, cfg['python_env_manifest_sha256'])
    manifest = json.loads(raw, object_pairs_hook=pairs)
    exact(manifest, 'schemaVersion files symlinks')
    files, links = manifest['files'], manifest['symlinks']
    need(type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 1
         and isinstance(files, dict) and isinstance(links, dict)
         and not set(files) & set(links) and 1 <= len(files) + len(links) <= 30000
         and 'pyvenv.cfg' in files, 'python_manifest_invalid')
    actual_files, actual_links = {}, {}
    immutable_directory(root)
    for directory, dirs, names in os.walk(root, followlinks=False):
        immutable_directory(Path(directory))
        for name in dirs + names:
            p = Path(directory) / name
            relative = str(p.relative_to(root))
            if p.is_symlink(): actual_links[relative] = os.readlink(p)
            elif p.is_file(): actual_files[relative] = p
            else: need(p.is_dir(), 'python_manifest_invalid')
    need(set(actual_files) == set(files) and actual_links == links, 'python_environment_changed')
    for relative, p in actual_files.items():
        hashed(immutable(p), files[relative])
    venv_config = (root / 'pyvenv.cfg').read_text()
    system_site = [line.split('=', 1)[1].strip().lower() for line in venv_config.splitlines()
                   if '=' in line and line.split('=', 1)[0].strip().lower() == 'include-system-site-packages']
    need(system_site == ['false'], 'system_site_packages_refused')
    target = python.resolve()
    for relative, destination in links.items():
        p = root / relative
        resolved = p.resolve()
        # No package/import link may escape the reviewed environment. Only the
        # pinned interpreter can reference the root-owned system Python binary.
        need(resolved.is_relative_to(root) or p.parent == root / 'bin'
             and p.name in ('python', 'python3', 'python3.12') and resolved == target,
             'python_environment_escape')
    hashed(executable(cfg['python']), cfg['python_sha256'])


def validate_source(root, manifest_path, expected):
    raw = private_bytes(manifest_path, 8 * 1024 * 1024); hashed(raw, expected)
    manifest = json.loads(raw, object_pairs_hook=pairs)
    exact(manifest, 'schemaVersion files')
    need(type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 1, 'source_manifest_invalid')
    files = manifest['files']
    need(isinstance(files, dict) and 1 <= len(files) <= 20000, 'source_manifest_invalid')
    required = {'scripts/federation-control.py', 'scripts/protected-role.py',
                'scripts/lib/protected_role.py', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py',
                'mcp-servers/protocol-mcp/bgp/federation/endpoint_registry.py',
                'mcp-servers/protocol-mcp/bgp/federation/runtime.py'}
    need(required <= files.keys(), 'source_manifest_incomplete')
    # The frozen source bundle is closed: no unpinned sibling import/source file.
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
    need(actual == set(files), 'source_manifest_incomplete')
    for directory in [root, *(p for p in root.rglob('*') if p.is_dir())]:
        immutable_directory(directory)
    for name, digest in files.items():
        relative = Path(name)
        need(not relative.is_absolute() and str(relative) == name and '..' not in relative.parts, 'source_path_invalid')
        hashed(immutable(root / relative), digest)


def validate_registry(registry, installation, source):
    """Reuse the pinned stdlib registry validator without importing BGP services.

    Only called after the complete source closure is verified. Its runtime.py
    dependency is also stdlib-only; no service initialization or third-party
    site packages are loaded by the -I -S bootstrap.
    """
    namespace = '_netclaw_role_registry_' + uuid.uuid4().hex
    package = types.ModuleType(namespace)
    directory = source / 'mcp-servers/protocol-mcp/bgp/federation'
    package.__path__ = [str(directory)]
    sys.modules[namespace] = package
    try:
        spec = importlib.util.spec_from_file_location(namespace + '.endpoint_registry', directory / 'endpoint_registry.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        module.validate(registry, installation)
    finally:
        for name in list(sys.modules):
            if name == namespace or name.startswith(namespace + '.'):
                sys.modules.pop(name, None)


# Role values cannot smuggle provider, tool, SSH or shell setup into the process.
_OPTIONAL = {'NETCLAW_LOCAL_AS', 'NETCLAW_ROUTER_ID', 'N2N_DISPLAY_NAME',
             'BGP_API_PORT', 'BGP_LISTEN_PORT', 'N2N_INVENTORY_REFRESH_S'}
_FIXED = {'N2N_ENABLED': 'true', 'N2N_PROTECTED_OPERATIONS': '1',
          'N2N_CERT_MODE': 'enforce', 'N2N_RISK_MODE': 'production',
          'N2N_STRICT_ALL': '1', 'NETCLAW_MESH_OPEN': 'false',
          'NETCLAW_BGP_PEERS': '[]', 'NETCLAW_DRY_RUN': 'true',
          'BGP_LISTEN_HOST': '127.0.0.1', 'PYTHON_DOTENV_DISABLED': '1',
          'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1'}


def validate(contract_path):
    contract_path = path(str(contract_path)); cfg = document(contract_path)
    fields = 'schemaVersion installation_id role runtime_kind control_only home source_root python python_sha256 python_env python_env_manifest python_env_manifest_sha256 source_manifest source_manifest_sha256 profile_sha256 registry registry_sha256 origin environment'
    member = cfg.get('role') == 'member' and type(cfg.get('schemaVersion')) is int and cfg['schemaVersion'] == 2
    exact(cfg, fields + (' guard_token_file' if member else ''))
    if not member:
        need(type(cfg['schemaVersion']) is int and cfg['schemaVersion'] == 1, 'role_schema_invalid')
        need(cfg['role'] == 'border', 'cloud_member_activation_unqualified')
    need(cfg['control_only'] is (not member), 'control_only_required')
    need(cfg['runtime_kind'] == 'openclaw', 'cloud_harness_unqualified')
    try:
        need(str(uuid.UUID(cfg['installation_id'])) == cfg['installation_id'], 'installation_invalid')
    except (ValueError, TypeError, AttributeError):
        raise RoleRefused('installation_invalid') from None
    home, root = path(cfg['home']), path(cfg['source_root'])
    need(home.is_dir() and home.stat().st_uid == os.getuid() and not home.stat().st_mode & 0o077, 'private_home_required')
    need(root.is_dir() and not root.is_relative_to(home) and not home.is_relative_to(root), 'separate_source_required')
    validate_python_environment(cfg)
    validate_source(root, path(cfg['source_manifest']), cfg['source_manifest_sha256'])
    installation = document(home / 'netclaw-hud/installation.json')
    need(installation == {'schemaVersion': 1, 'installationId': cfg['installation_id']}, 'installation_mismatch')
    owner = document(home / 'netclaw-federation/owner.json')
    need(owner == {'schemaVersion': 1, 'installationId': cfg['installation_id'], 'kind': cfg['runtime_kind'], 'home': str(home)}, 'owner_mismatch')
    raw = private_bytes(home / 'netclaw-federation/protected-profile.json'); hashed(raw, cfg['profile_sha256'])
    profile = json.loads(raw, object_pairs_hook=pairs)
    fields = 'schemaVersion role identity' if cfg['role'] == 'border' else 'schemaVersion role identity catalog runtime border'
    if not member and 'access' in profile:
        fields += ' access'
        need(profile['access'] == {'mode': 'open-lab'}, 'profile_access_invalid')
    exact(profile, fields)
    need(type(profile['schemaVersion']) is int and profile['schemaVersion'] == 1
         and profile['role'] == cfg['role'] and profile.get('identity', {}).get('installation_id') == cfg['installation_id'], 'profile_mismatch')
    binding = profile['identity']
    exact(binding, 'installation_id member_id key_id enrollment_generation' if member else 'installation_id identity key_id authority_generation')
    need(all(isinstance(v, str) and 0 < len(v) <= 200 and not any(ord(c) < 32 for c in v)
             for v in binding.values()) and re.fullmatch('[a-f0-9]{64}', binding['key_id']), 'identity_invalid')
    registry_path = path(cfg['registry'])
    need(registry_path.is_relative_to(home), 'registry_outside_home')
    registry_raw = private_bytes(registry_path); hashed(registry_raw, cfg['registry_sha256'])
    registry = json.loads(registry_raw, object_pairs_hook=pairs)
    validate_registry(registry, cfg['installation_id'], root)
    need(registry.get('schemaVersion') == 2 and registry.get('installationId') == cfg['installation_id'], 'registry_mismatch')
    entries = registry.get('entries')
    need(isinstance(entries, list), 'registry_invalid')
    if cfg['role'] == 'border':
        need(len(entries) == 2 and {e.get('service') for e in entries} == {'in2n', 'en2n'}, 'border_listeners_required')
        need(all(e.get('direction') == 'listen' and e.get('transport') == 'direct_tcp' for e in entries), 'direct_listeners_required')
        for entry in entries:
            address = ipaddress.ip_address(entry.get('bind_host', ''))
            need(not address.is_unspecified and not address.is_multicast, 'listener_invalid')
            if entry['service'] == 'en2n':
                need(address.is_loopback and ipaddress.ip_address(entry['routing_host']).is_loopback,
                     'external_listener_must_be_dormant')
        u = urlsplit(cfg['origin'])
        need(u.scheme == 'https' and u.hostname and not u.username and not u.password
             and cfg['origin'] == 'https://' + u.netloc and not u.port, 'exact_https_origin_required')
        # A deliberately empty harness configuration cannot contain a model,
        # provider, gateway or remote tool integration.
        config_path = home / 'openclaw.json'
        if config_path.exists():
            need(document(config_path) == {'netclaw': {'controlOnly': True}}, 'border_harness_config_refused')
    else:
        need(cfg['origin'] is None and len(entries) == 1 and entries[0].get('service') == 'in2n'
             and entries[0].get('direction') == 'dial' and entries[0].get('transport') == 'direct_tcp', 'member_outbound_only_required')
        border = profile['border']
        exact(border, 'installation_id identity key_id authority_generation')
        need(all(isinstance(v, str) and 0 < len(v) <= 200 and not any(ord(c) < 32 for c in v)
                 for v in border.values()) and re.fullmatch('[a-f0-9]{64}', border['key_id']), 'border_identity_invalid')
        need(entries[0]['application_identity'] == border['identity'], 'member_border_identity_mismatch')
        enrollment = document(home / 'n2n/keys/protected/enrollment.json')
        need(all(enrollment.get(k) == binding[k] for k in ('installation_id', 'member_id', 'enrollment_generation')), 'member_enrollment_mismatch')
        capability = path(cfg['guard_token_file'])
        need(capability == home / 'netclaw-federation/guard-capability', 'member_guard_path_refused')
        guard_token = private_bytes(capability, 256).decode('ascii').strip()
        need(re.fullmatch('[A-Za-z0-9_-]{43}', guard_token), 'member_guard_capability_invalid')
    env = cfg['environment']; need(isinstance(env, dict) and set(env) <= _OPTIONAL, 'environment_refused')
    need(all(isinstance(v, str) and 0 < len(v) <= 200 and not re.search('[\x00-\x1f\x7f]', v) for v in env.values()), 'environment_invalid')
    for key in ('BGP_API_PORT', 'BGP_LISTEN_PORT'):
        if key in env: need(env[key].isdigit() and 1024 <= int(env[key]) <= 65535, 'port_invalid')
    # Existing launchers read these files. Refuse extra ambient config rather than
    # letting them override this exact role environment at the last moment.
    for name in ('.env', 'mesh.systemd.env'):
        p = home / name
        if p.exists():
            need(not private_bytes(p).strip(), 'ambient_environment_refused')
    database = path(str(home / 'n2n/federation.db'))
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        row = db.execute('SELECT role,risk_name,enabled_stacks,self_member_id FROM risk WHERE id=1').fetchone()
    need(row and row[0] == cfg['role'] and isinstance(row[1], str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,127}', row[1]), 'persisted_role_required')
    if cfg['role'] == 'border': need(row[2] == 'in2n', 'internal_stack_required')
    environment = {'HOME': str(home), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', **_FIXED, **env,
                   'NETCLAW_RUNTIME': cfg['runtime_kind'], 'NETCLAW_INSTALLATION_ID': cfg['installation_id'],
                   'N2N_BASE_DIR': str(home / 'n2n'), 'N2N_ROLE': cfg['role'], 'N2N_RISK_NAME': row[1],
                   'N2N_ENABLED_STACKS': 'in2n', 'N2N_ENDPOINT_REGISTRY': str(registry_path),
                   'N2N_GAIT_DIR': str(home / 'n2n/gait'), 'NETCLAW_PROTECTED_ROLE_CONTRACT': str(contract_path)}
    if cfg['role'] == 'member':
        need(isinstance(row[3], str) and row[3] == binding['member_id'] and row[2] == 'in2n', 'member_identity_required')
        environment['N2N_MEMBER_ID'] = row[3]
        environment['N2N_BORDER_REGISTRY_ID'] = entries[0]['id']
        environment['NETCLAW_R04_GUARD_TOKEN'] = guard_token
    if cfg['runtime_kind'] == 'openclaw':
        environment.update(OPENCLAW_HOME=str(home), OPENCLAW_STATE_DIR=str(home), OPENCLAW_CONFIG_PATH=str(home / 'openclaw.json'))
    else:
        environment['HERMES_HOME'] = str(home)
    return cfg, environment
