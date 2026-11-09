#!/usr/bin/env python3
"""R09 local HA execution member (Mac, arm64): private-file builder, one step per subcommand.

This only generates and validates private files. It never starts Docker, a model, a guard, a Border
connection or any role process, never touches the offline enrollment key (`identity/root.key` of the
Border deployment is not read; a member needs only the public anchor certificate), and never modifies
product files. The member attaches OUTBOUND: it dials every manifest node's `endpoints.in2n`
(host=public IP, port=7444, TLS server_name=the node DNS name) trusting only `transport-ca.crt`. There is
no per-member address, env or profile field for this; the signed manifest and `transport_ca_file` in
`ha-config.json` are the whole dial configuration (ha/internal.py MemberAttachments.connect).

Usage (all take --root; `identity` creates it fresh, 0700):
  r09_member.py plan                         print the ordered runbook (what you and the parent run)
  r09_member.py identity --root R            member key/cert/binding + public cluster inputs
  r09_member.py freeze --root R              closed, read-only member source closure + manifest
  r09_member.py python-env --root R          reuse the verified immutable 3.12 env (or --build via uv)
  r09_member.py artifacts --root R           model store copy, guard config/env/capability, native source
  (owner runs the printed `qualify.py prepare` to start the confined model namespace)
  r09_member.py materialize --root R         home, ha-config, profile, catalog, schema-3 contract
  r09_member.py validate --root R            the production role validator + closure import check
Files whose raw bytes the launcher pins (ha-config, profile, manifests, contract) are written in canonical
JSON and digested over those exact bytes. All *_file paths are absolute, canonical, symlink-free.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import uuid
from datetime import date

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
HOME = Path.home()
DEFAULT_DEPLOYMENT = HOME / '.local/share/netclaw/r09-20261109'
R05 = HOME / '.local/share/netclaw/roadmap-r05-20261105/local-member'
R04A = HOME / '.local/share/netclaw/roadmap-r04a-owner-20261104/local-member'
SOURCE_TREES = ('mcp-servers/protocol-mcp',)
SOURCE_EXTRA = ('scripts/federation-control.py', 'scripts/protected-role.py', 'scripts/lib/protected_role.py',
                'scripts/write-env.py', 'scripts/runtime-selection.py', 'config/hermes-hud-compatibility.json',
                'labs/ollama/qualify.py')
SKIP_DIRS = {'tests', '__pycache__', '.pytest_cache'}
SKIP_SUFFIX = ('.md', '.pyc')
MEMBER_REQUIREMENTS = ['cryptography==50.0.2', 'pyOpenSSL==26.4.0', 'service-identity==26.1.0', 'httpx>=0.27',
                       'websockets>=12.0,<17', 'PyYAML>=6.0', 'h2>=4.1', 'qrcode>=7.4']
TOOL_LIMITS = {'inference_timeout_ms': 60000, 'tool_timeout_ms': 30000, 'max_inference_calls': 2,
               'max_tool_calls': 1, 'max_output_bytes': 262144}
GUARD_ENV_VARIABLE = 'DEFENSECLAW_GATEWAY_TOKEN'
GUARD_TOKEN_ENV = 'NETCLAW_R09_GUARD_TOKEN'


class MemberRefused(SystemExit):
    pass


def need(value, code):
    if not value:
        raise MemberRefused('refused:' + code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_private(path, value):
    """Create-only 0600 file. Dict/list values are written canonically; bytes verbatim."""
    raw = value if isinstance(value, bytes) else canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return sha(raw)


def read_private(path, maximum=8 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'private_file_required')
        return stream.read(maximum + 1)


def private_dir(path):
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    need(path.resolve() == path and path.stat().st_uid == os.getuid(), 'canonical_private_directory_required')
    return path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ROLE = []


def role_module():
    if not _ROLE:
        _ROLE.append(load_module('r09_member_protected_role', REPO / 'scripts/lib/protected_role.py'))
    return _ROLE[0]


def use_source(root):
    """Compute bindings against the frozen closure when it exists (never a mixed source process)."""
    frozen = Path(root) / 'source/mcp-servers/protocol-mcp'
    directory = frozen if frozen.is_dir() else REPO / 'mcp-servers/protocol-mcp'
    if 'bgp' not in sys.modules and str(directory) not in sys.path:
        sys.path.insert(0, str(directory))


def state_path(root):
    return Path(root) / 'state.json'


def load_state(root):
    root = Path(root).resolve()
    need(root.is_dir() and (root / 'state.json').exists(), 'run_root_required')
    return root, json.loads(read_private(root / 'state.json'))


def save_state(root, state):
    path = Path(root) / 'state.json'
    tmp = Path(root) / 'state.json.new'
    if tmp.exists():
        tmp.unlink()
    write_private(tmp, state)
    os.replace(tmp, path)


def closure_files():
    files = {}
    for base in SOURCE_TREES:
        for path in sorted((REPO / base).rglob('*')):
            relative = path.relative_to(REPO)
            if (path.is_file() and not path.is_symlink() and not any(p in SKIP_DIRS for p in relative.parts)
                    and not path.name.endswith(SKIP_SUFFIX) and path.name != 'pytest.ini'):
                files[str(relative)] = path
    for name in SOURCE_EXTRA:
        need((REPO / name).is_file(), 'closure_file_missing:' + name)
        files[name] = REPO / name
    return files


# --------------------------------------------------------------------------------------------- identity
def cmd_identity(args):
    use_source(args.root)
    from bgp.federation import protected_contract as c
    from bgp.federation.certs import create_self_signed
    from bgp.federation.ha.config import verify_manifest
    deployment = Path(args.deployment).absolute()
    inputs = {'manifest': deployment / 'identity/manifest.json', 'anchor': deployment / 'identity/root.crt',
              'transport_ca': deployment / 'transport/transport-ca.crt', 'summary': deployment / 'summary.json'}
    for label, path in inputs.items():
        need(path.is_file(), 'deployment_input_missing:' + label)
    root = Path(args.root).resolve()  # macOS: /tmp and /var are symlinks; the launcher needs canonical paths
    need(not root.exists(), 'fresh_root_required')
    private_dir(root)
    cluster = private_dir(root / 'cluster')
    # Public inputs only. The offline `root.key` is deliberately never opened.
    anchor = inputs['anchor'].read_text()
    manifest_raw = inputs['manifest'].read_bytes()
    verified = verify_manifest(manifest_raw, anchor, expected_key_id=c.key_id(anchor))
    write_private(cluster / 'manifest.json', manifest_raw)
    write_private(cluster / 'root.crt', anchor.encode())
    write_private(cluster / 'transport-ca.crt', inputs['transport_ca'].read_bytes())
    identity = private_dir(root / 'identity')
    suffix = secrets.token_hex(3)
    certificate, key = create_self_signed('r09/member-' + suffix, days=args.days)
    write_private(identity / 'member.crt', certificate.encode())
    write_private(identity / 'member.key', key.encode())
    binding = {'installation_id': str(uuid.uuid4()), 'member_id': 'nc182-r09/mac-subnet-' + suffix,
               'key_id': c.key_id(certificate), 'enrollment_generation': str(uuid.uuid4())}
    c.validate_binding(binding, 'member')
    need(all(binding['installation_id'] != n['installation_id'] and binding['key_id'] != n['key_id']
             for n in verified.nodes), 'member_border_identity_collision')
    write_private(identity / 'member.json', {'binding': binding, 'certificate': certificate})
    name = 'netclaw-r08-r09m-' + suffix  # qualify.py (spec 179) requires this exact owner-name shape
    dial = [{'node': n['identity'], 'host': n['endpoints']['in2n']['host'], 'port': n['endpoints']['in2n']['port'],
             'server_name': n['endpoints']['in2n']['server_name']} for n in verified.nodes]
    save_state(root, {'schema_version': 1, 'name': name, 'deployment': str(deployment), 'binding': binding,
                      'cluster_id': verified.cluster_id, 'generation': verified.generation, 'steps': ['identity']})
    return {'root': str(root), 'member': binding, 'enrollment_packet': str(identity / 'member.json'),
            'outbound_dial': dial, 'anchor_key_id': c.key_id(anchor), 'name': name}


# ----------------------------------------------------------------------------------------------- freeze
def cmd_freeze(args):
    root, state = load_state(args.root)
    need(not (root / 'source').exists(), 'source_already_frozen')
    files = closure_files()
    need(1 <= len(files) <= 20000 and sum(p.stat().st_size for p in files.values()) <= 64 * 1024 * 1024, 'source_bound')
    manifest = {'schemaVersion': 1, 'files': {name: sha(path.read_bytes()) for name, path in files.items()}}
    destination = private_dir(root / 'source')
    for name, path in files.items():
        target = destination / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        os.chmod(target, 0o500 if os.access(path, os.X_OK) else 0o400)
    for directory, _, _ in os.walk(destination, topdown=False):
        os.chmod(directory, 0o500)
    manifest_sha = write_private(root / 'source-manifest.json', manifest)
    state['source_manifest_sha256'] = manifest_sha
    state['steps'].append('freeze')
    save_state(root, state)
    return {'source_files': len(files), 'source_manifest_sha256': manifest_sha}


# ------------------------------------------------------------------------------------------- python env
def env_manifest(venv):
    venv = Path(venv)
    files, links = {}, {}
    for directory, dirs, names in os.walk(venv, followlinks=False):
        for name in dirs + names:
            p = Path(directory) / name
            relative = str(p.relative_to(venv))
            if p.is_symlink():
                links[relative] = os.readlink(p)
            elif p.is_file():
                files[relative] = sha(p.read_bytes())
    return {'schemaVersion': 1, 'files': files, 'symlinks': links}


def verify_env(python, env, manifest_file, manifest_sha, python_sha):
    cfg = {'python': str(python), 'python_env': str(env), 'python_env_manifest': str(manifest_file),
           'python_env_manifest_sha256': manifest_sha, 'python_sha256': python_sha}
    role_module().validate_python_environment(cfg)
    return cfg


def build_env(root):
    """Network step (uv/pip). Immutable macOS arm64 3.12 env recipe used by R04A: a read-only copy of the
    interpreter, a venv whose bin/python links to it, every file hashed, nothing writable."""
    base = Path('/opt/homebrew/opt/python@3.12/bin/python3.12').resolve()
    need(base.exists(), 'python312_missing:brew install python@3.12')
    work = private_dir(Path(root) / 'python')
    native = private_dir(work / 'native')
    target = native / 'python3.12'
    shutil.copyfile(base, target)
    os.chmod(target, 0o500)
    venv = work / 'venv'
    subprocess.run([str(base), '-m', 'venv', '--without-pip', str(venv)], check=True)
    uv = shutil.which('uv')
    need(uv, 'uv_missing')
    subprocess.run([uv, 'pip', 'install', '--python', str(venv / 'bin/python'), *MEMBER_REQUIREMENTS], check=True)
    for name in ('python', 'python3', 'python3.12'):
        link = venv / 'bin' / name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target if name == 'python' else 'python')
    for directory, _, names in os.walk(venv, topdown=False, followlinks=False):
        for name in names:
            p = Path(directory) / name
            if not p.is_symlink():
                os.chmod(p, 0o500 if os.access(p, os.X_OK) else 0o400)
        os.chmod(directory, 0o500)
    os.chmod(native, 0o500)
    return venv, env_manifest(venv)


def cmd_python_env(args):
    root, state = load_state(args.root)
    need(not (root / 'python-env.json').exists(), 'python_env_already_recorded')
    if args.build:
        need(args.yes_network, 'build_needs_--yes-network')
        venv, manifest = build_env(root)
        raw = canonical(manifest)
        source_env, source_manifest = venv, None
        manifest_sha = write_private(root / 'python-env-manifest.json', raw)
    else:
        source_env = Path(args.env or R04A / 'venv')
        source_manifest = Path(args.env_manifest or R04A / 'python-env-manifest.json')
        raw = source_manifest.read_bytes()
        manifest_sha = write_private(root / 'python-env-manifest.json', raw)
    python = source_env / 'bin/python'
    python_sha = sha(python.resolve().read_bytes())
    verify_env(python, source_env, root / 'python-env-manifest.json', manifest_sha, python_sha)
    record = {'python': str(python), 'sha256': python_sha, 'environment': str(source_env),
              'manifest_file': str(root / 'python-env-manifest.json'), 'manifest_sha256': manifest_sha}
    write_private(root / 'python-env.json', record)
    state['steps'].append('python-env')
    save_state(root, state)
    return record


# ---------------------------------------------------------------------------------------------- artifacts
def cmd_artifacts(args):
    root, state = load_state(args.root)
    need('freeze' in state['steps'], 'freeze_first')
    use_source(root)
    from bgp.federation import protected_ollama as model
    from bgp.federation.protected_calculator import SUMMARY_SOURCE_SHA256
    template = json.loads(Path(args.template or R05 / 'runtime-template.json').read_text())
    runtime = copy.deepcopy(template['runtime'])
    need(runtime['mcp']['kind'] == 'subnet_summary' and runtime['ollama']['family'] == 4, 'qualified_native_template_required')
    artifacts = private_dir(root / 'artifacts')
    # Guard configuration is a public pinned file; the guard secret is fresh and never reused from R05.
    guard_config = Path(runtime['guard']['config_file']).read_bytes()
    need(sha(guard_config) == runtime['guard']['config_sha256'], 'guard_config_changed')
    write_private(artifacts / 'guard-config.yaml', guard_config)
    os.chmod(artifacts / 'guard-config.yaml', 0o400)
    token = secrets.token_urlsafe(32)
    need(re.fullmatch('[A-Za-z0-9_-]{43}', token), 'guard_token_shape')
    write_private(artifacts / 'guard.env', (GUARD_ENV_VARIABLE + '=' + token + '\n').encode())
    write_private(artifacts / 'guard-capability', token.encode())
    native_source = Path(runtime['mcp']['source_root']) / 'servers/subnetcalculator_mcp.py'
    raw = native_source.read_bytes()
    need(sha(raw) == SUMMARY_SOURCE_SHA256 == runtime['mcp']['source_sha256']['servers/subnetcalculator_mcp.py'], 'native_source_changed')
    native = private_dir(artifacts / 'native-subnet/servers')
    write_private(native / 'subnetcalculator_mcp.py', raw)
    os.chmod(native / 'subnetcalculator_mcp.py', 0o400)
    skill_dir = private_dir(artifacts / 'subnet-calculator')
    skill = (REPO / 'workspace/skills/subnet-calculator/SKILL.md').read_bytes()
    need(sha(skill) == runtime['mcp']['skill']['sha256'], 'skill_changed')
    write_private(skill_dir / 'SKILL.md', skill)
    os.chmod(skill_dir / 'SKILL.md', 0o400)
    manifest = Path(runtime['mcp']['python_manifest']).read_bytes()
    need(sha(manifest) == runtime['mcp']['python_manifest_sha256'], 'mcp_python_manifest_changed')
    write_private(artifacts / 'mcp-python-manifest.json', manifest)
    # Fresh copy of the pinned public model store (streamed, bounded, read-only), as R08 did.
    model.verify_store(runtime['ollama'])
    from labs.ha.real_runtime import copy_model_store
    copy_model_store(runtime['ollama']['model_store'], artifacts / 'models')
    new_model = dict(runtime['ollama'], model_store=str(artifacts / 'models'))
    model.verify_store(new_model)
    home = root / 'home'
    runtime.update(state_dir=str(home / 'netclaw-federation/runtime'), guard_token_env=GUARD_TOKEN_ENV, ollama=new_model)
    runtime['guard'].update(config_file=str(artifacts / 'guard-config.yaml'), env_file=str(artifacts / 'guard.env'))
    runtime['mcp'].update(source_root=str(artifacts / 'native-subnet'), python_manifest=str(artifacts / 'mcp-python-manifest.json'))
    runtime['mcp']['skill'] = dict(runtime['mcp']['skill'], path=str(skill_dir / 'SKILL.md'))
    write_private(root / 'runtime-template.json', runtime)
    state['steps'].append('artifacts')
    save_state(root, state)
    docker, docker_host = runtime['docker'], runtime['docker_host']
    env_python = json.loads(read_private(root / 'python-env.json'))['python'] if (root / 'python-env.json').exists() else sys.executable
    command = [env_python, '-B', str(root / 'source/labs/ollama/qualify.py'), 'prepare', '--docker', docker,
               '--docker-host', docker_host, '--state-dir', str(root / 'model'), '--owner-spec', '179',
               '--owner-name', state['name'], '--image', new_model['model_image'], '--model-store', str(artifacts / 'models'),
               '--name', state['name'] + '-model', '--family', '4', '--guard-uid', str(os.getuid()),
               '--model-uid', str(new_model['model_uid'])]
    return {'artifacts': str(artifacts), 'model_start_command_owner_runs': command}


# -------------------------------------------------------------------------------------------- materialize
def cmd_materialize(args):
    root, state = load_state(args.root)
    for step in ('identity', 'freeze', 'python-env', 'artifacts'):
        need(step in state['steps'], step + '_first')
    need((root / 'model/profile.json').exists(), 'model_profile_missing:run the qualify.py prepare command first')
    need(not (root / 'home').exists(), 'home_already_materialized')
    use_source(root)
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.config import verify_manifest
    from bgp.federation.manager import FederationManager
    from bgp.federation.protected_docker import revision_bindings, validate_runtime_fields
    from bgp.federation.risk import RiskManager
    cluster, identity = root / 'cluster', root / 'identity'
    anchor = (cluster / 'root.crt').read_text()
    manifest = verify_manifest(read_private(cluster / 'manifest.json'), anchor, expected_key_id=c.key_id(anchor))
    binding = state['binding']
    runtime = json.loads(read_private(root / 'runtime-template.json'))
    runtime['ollama'] = json.loads(read_private(root / 'model/profile.json'))
    bindings = revision_bindings(runtime)
    runtime['model_profile'].update({k: bindings[k] for k in ('guard_policy_sha256', 'profile_revision')})
    validate_runtime_fields(runtime)
    arguments = {'cidr': '192.0.2.0/26'}
    tool = {'tool': 'subnet_calculator', 'tool_schema_sha256': bindings['tool_schema_sha256'], 'arguments': arguments,
            'arguments_sha256': sha(canonical(arguments)), 'device_ref': '192.0.2.0/26',
            'inventory_revision': runtime['mcp']['selection_sha256'], 'endpoint_sha256': runtime['mcp']['endpoint_sha256'],
            'limits': dict(TOOL_LIMITS)}
    catalog = {'member': binding, 'model_profiles': [runtime['model_profile']], 'tools': [tool]}
    c.validate_catalog_entry(catalog)
    home = private_dir(root / 'home')
    for child in ('n2n', 'netclaw-federation', 'netclaw-hud'):
        private_dir(home / child)
    federation = home / 'netclaw-federation'
    write_private(home / 'netclaw-hud/installation.json', {'schemaVersion': 1, 'installationId': binding['installation_id']})
    write_private(federation / 'owner.json', {'schemaVersion': 1, 'installationId': binding['installation_id'],
                                              'kind': 'openclaw', 'home': str(home)})
    write_private(federation / 'ha-required.json', {'schema_version': 1, **manifest.audience})
    old = os.umask(0o077)
    try:
        db = FederationManager(base_dir=str(home / 'n2n'))
        RiskManager(db).set_role('member', risk_name=state['name'], enabled_stacks='in2n', self_member_id=binding['member_id'])
        db._conn.close()
    finally:
        os.umask(old)
    write_private(home / 'n2n/keys/self.crt', read_private(identity / 'member.crt'))
    write_private(home / 'n2n/keys/self.key', read_private(identity / 'member.key'))
    write_private(federation / 'guard-capability', read_private(root / 'artifacts/guard-capability'))
    config = {'schema_version': 1, 'role': 'member', 'manifest_file': str(cluster / 'manifest.json'),
              'anchor_certificate_file': str(cluster / 'root.crt'), 'anchor_key_id': c.key_id(anchor),
              'transport_ca_file': str(cluster / 'transport-ca.crt'),
              'certificate_file': str(identity / 'member.crt'), 'private_key_file': str(identity / 'member.key')}
    config_sha = write_private(federation / 'ha-config.json', config)
    profile = {'schemaVersion': 2, 'role': 'member', 'identity': binding, 'catalog': catalog, 'runtime': runtime,
               'ha': {'config_file': str(federation / 'ha-config.json'), 'config_sha256': config_sha}}
    profile_sha = write_private(federation / 'protected-profile.json', profile)
    python = json.loads(read_private(root / 'python-env.json'))
    contract = {'schemaVersion': 3, 'installation_id': binding['installation_id'], 'role': 'member', 'runtime_kind': 'openclaw',
                'control_only': False, 'home': str(home), 'source_root': str(root / 'source'),
                'python': python['python'], 'python_sha256': python['sha256'], 'python_env': python['environment'],
                'python_env_manifest': python['manifest_file'], 'python_env_manifest_sha256': python['manifest_sha256'],
                'source_manifest': str(root / 'source-manifest.json'),
                'source_manifest_sha256': state['source_manifest_sha256'], 'profile_sha256': profile_sha,
                'origin': None, 'guard_token_file': str(federation / 'guard-capability'),
                'environment': {'NETCLAW_LOCAL_AS': '65189', 'NETCLAW_ROUTER_ID': '127.0.0.9',
                                'N2N_DISPLAY_NAME': 'R09 Mac member', 'BGP_API_PORT': '18189',
                                'N2N_INVENTORY_REFRESH_S': '0'}}
    write_private(root / 'contract.json', contract)
    state['steps'].append('materialize')
    save_state(root, state)
    return {'contract': str(root / 'contract.json'), 'profile_sha256': profile_sha, 'ha_config_sha256': config_sha,
            'tool': {'tool': tool['tool'], 'arguments': arguments}}


# ------------------------------------------------------------------------------------------------ validate
def cmd_validate(args):
    root, state = load_state(args.root)
    need('materialize' in state['steps'], 'materialize_first')
    contract = root / 'contract.json'
    role = role_module()
    result = {'role_validate': None, 'closure_import': None}
    try:
        cfg, _ = role.validate(contract)
        result['role_validate'] = 'valid'
        result['control_only'] = cfg['control_only']
    except role.RoleRefused as exc:  # exact failing check, in-process (the launcher hides it by design)
        result['role_validate'] = 'refused:' + str(exc)
    if not args.skip_import_check and result['role_validate'] == 'valid':
        cfg = json.loads(read_private(contract))
        code = ("import sys; sys.path.insert(0, %r);"
                "import bgp.federation.ha.factory, bgp.federation.ha.member, bgp.federation.protected_docker, "
                "bgp.federation.protected_ollama, bgp.federation.protected_mcp; print('closure-ok')"
                % str(root / 'source/mcp-servers/protocol-mcp'))
        done = subprocess.run([cfg['python'], '-I', '-B', '-c', code], capture_output=True, text=True, timeout=120)
        result['closure_import'] = 'ok' if done.stdout.strip() == 'closure-ok' else 'failed:' + done.stderr.strip()[-400:]
    return result


def cmd_plan(_):
    return {'order': [
        {'who': 'builder', 'step': 'identity, freeze, python-env, artifacts (this script, offline)'},
        {'who': 'owner', 'step': 'run the labs/ollama/qualify.py prepare command printed by `artifacts` (Docker; measures confinement)'},
        {'who': 'builder', 'step': 'materialize, validate'},
        {'who': 'parent', 'step': 'ENROLL: stop 3 Borders, wait 15 s, one-shot Authority.campaign + OperationLedger.enroll_member '
                                  'with identity/member.json as Border 0 on nne1, restart Borders (costs one epoch)'},
        {'who': 'owner', 'step': 'start the member: python-env/bin/python -I -B <root>/source/scripts/protected-role.py '
                                 '--contract <root>/contract.json run  (cwd=home, env PATH=/usr/bin:/bin HOME=<home>)'},
        {'who': 'parent', 'step': 'verify 3 attachments (journal/status), then HUD/VS Code subnet_calculator 192.0.2.0/26'}]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('plan')
    for name in ('identity', 'freeze', 'python-env', 'artifacts', 'materialize', 'validate'):
        p = sub.add_parser(name)
        p.add_argument('--root', required=True)
        if name == 'identity':
            p.add_argument('--deployment', default=str(DEFAULT_DEPLOYMENT))
            p.add_argument('--days', type=int, default=7)
        if name == 'python-env':
            p.add_argument('--env'); p.add_argument('--env-manifest')
            p.add_argument('--build', action='store_true'); p.add_argument('--yes-network', action='store_true')
        if name == 'artifacts':
            p.add_argument('--template')
        if name == 'validate':
            p.add_argument('--skip-import-check', action='store_true')
    args = parser.parse_args(argv)
    command = {'plan': cmd_plan, 'identity': cmd_identity, 'freeze': cmd_freeze, 'python-env': cmd_python_env,
               'artifacts': cmd_artifacts, 'materialize': cmd_materialize, 'validate': cmd_validate}[args.action]
    print(json.dumps(command(args), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
