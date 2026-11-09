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
NetBox flavor (hosted Sonnet via the DefenseClaw guard + the exact reviewed NetBox read; spec 182):
  r09_member.py identity --root R --flavor netbox      (everything after reads the flavor from state.json)
  r09_member.py freeze / python-env --root R           (unchanged)
  r09_member.py netbox-env --root R [--build --yes-network | --env VENV]   immutable fastmcp<3 env for the NetBox MCP
  NETBOX_TOKEN=... ANTHROPIC_API_KEY=... r09_member.py artifacts --root R [--netbox-url URL]   (secrets from the
        environment only, written 0600 to guard.env / the credential file, never printed, logged or stored in state)
  r09_member.py materialize / validate --root R        (no model namespace and no qualify.py for this flavor)
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
FLAVORS = ('ollama', 'netbox')
# NetBox flavor. The MCP server pins fastmcp<3 (mcp 1.x), so it needs its own immutable env, separate from the
# member env that runs mcp 2.x. Tool arguments are the single exact reviewed read; id 27 exists on demo.netbox.dev.
NETBOX_MCP_REQUIREMENTS = ['fastmcp>=2.14.0,<3', 'requests>=2.31.0', 'httpx>=0.28.1', 'pydantic>=2.0',
                           'pydantic-settings>=2.0']
NETBOX_FIELDS = ['id', 'name', 'status', 'site', 'device_type', 'last_updated']
NETBOX_ARGUMENTS = {'object_type': 'dcim.device', 'object_id': 27, 'fields': NETBOX_FIELDS, 'brief': False}
HOSTED_MODEL = 'claude-sonnet-4-6'  # the model the existing guard image pins; see protected_hosted.GUARD_IMAGE_MODEL
HOSTED_LIMITS = {'max_output_tokens': 1024, 'call_timeout_seconds': 60, 'task_timeout_seconds': 180}
PROVIDER_KEY_ENV = 'ANTHROPIC_API_KEY'
NETBOX_TOKEN_ENV = 'NETBOX_TOKEN'
NETBOX_URL_ENV = 'NETBOX_URL'
HARNESS_VERSION = '2026.7.1-2'


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


def secret_from_environment(name, environ=None):
    """A credential value from the process environment only. Never printed, logged or stored; refusals name the
    variable, never the value. The value is written once to a 0600 create-only file by the caller."""
    value = (os.environ if environ is None else environ).get(name)
    need(isinstance(value, str) and value != '', 'secret_missing:' + name)
    need(value.isascii() and value.strip() == value and '\n' not in value and '\r' not in value
         and 8 <= len(value) <= 4096 and all(32 < ord(ch) < 127 for ch in value), 'secret_shape:' + name)
    return value


def write_hosted_guard_env(path, provider_key, token):
    """guard.env exactly as protected-guard.py (hosted mode) loads it: the two reviewed names, distinct values."""
    need(provider_key != token, 'distinct_guard_credentials_required')
    return write_private(path, (PROVIDER_KEY_ENV + '=' + provider_key + '\n' + GUARD_ENV_VARIABLE + '=' + token + '\n').encode())


def hosted_profile(model=HOSTED_MODEL):
    return {'schema_version': 1, 'provider': 'anthropic', 'model': model, 'egress_host': 'api.anthropic.com',
            **HOSTED_LIMITS}


def hosted_guard_config(raw_config, model):
    """Derive the hosted guard configuration from the pinned public R05 DefenseClaw config.

    protected-guard.py (hosted mode) demands: every `base_url` is the loopback provider fence, every `api_key_env` is
    DEFENSECLAW_LLM_KEY, every `model:` is anthropic/<pinned model>, `data_dir` is /guard, no inline key and
    `forward_custom_headers` false. The real key is never in this file: it reaches only guard.env.
    Not exercised against the real DefenseClaw gateway here: a rejected config fails at guard start, before any call."""
    try:
        import yaml
    except ImportError:
        raise MemberRefused('refused:pyyaml_required_for_hosted_guard_config') from None
    config = yaml.safe_load(raw_config)
    need(isinstance(config, dict) and isinstance(config.get('guardrail'), dict) and isinstance(config.get('llm'), dict),
         'guard_config_shape')
    route = {'api_key_env': 'DEFENSECLAW_LLM_KEY', 'base_url': 'http://127.0.0.1:18888',
             'forward_custom_headers': False, 'model': 'anthropic/' + model}
    config['llm'] = dict(route)
    config['guardrail']['llm'] = dict(route)
    config['guardrail']['model'] = 'anthropic/' + model
    config['guardrail']['model_name'] = model
    need(config.get('data_dir') == '/guard', 'guard_data_dir')
    return yaml.safe_dump(config, sort_keys=True, default_flow_style=False).encode()


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
    flavor = getattr(args, 'flavor', 'ollama')
    need(flavor in FLAVORS, 'flavor_refused')
    binding = {'installation_id': str(uuid.uuid4()),
               'member_id': ('nc182-r09/netbox-' if flavor == 'netbox' else 'nc182-r09/mac-subnet-') + suffix,
               'key_id': c.key_id(certificate), 'enrollment_generation': str(uuid.uuid4())}
    c.validate_binding(binding, 'member')
    need(all(binding['installation_id'] != n['installation_id'] and binding['key_id'] != n['key_id']
             for n in verified.nodes), 'member_border_identity_collision')
    write_private(identity / 'member.json', {'binding': binding, 'certificate': certificate})
    name = 'netclaw-r08-r09m-' + suffix  # qualify.py (spec 179) requires this exact owner-name shape
    dial = [{'node': n['identity'], 'host': n['endpoints']['in2n']['host'], 'port': n['endpoints']['in2n']['port'],
             'server_name': n['endpoints']['in2n']['server_name']} for n in verified.nodes]
    save_state(root, {'schema_version': 1, 'name': name, 'deployment': str(deployment), 'binding': binding,
                      'cluster_id': verified.cluster_id, 'generation': verified.generation, 'steps': ['identity'],
                      'flavor': flavor})
    return {'root': str(root), 'member': binding, 'flavor': flavor, 'enrollment_packet': str(identity / 'member.json'),
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


def build_env(root, requirements=None, label='python'):
    """Network step (uv/pip). Immutable macOS arm64 3.12 env recipe used by R04A: a read-only copy of the
    interpreter, a venv whose bin/python links to it, every file hashed, nothing writable."""
    base = Path('/opt/homebrew/opt/python@3.12/bin/python3.12').resolve()
    need(base.exists(), 'python312_missing:brew install python@3.12')
    work = private_dir(Path(root) / label)
    native = private_dir(work / 'native')
    target = native / 'python3.12'
    shutil.copyfile(base, target)
    os.chmod(target, 0o500)
    venv = work / 'venv'
    subprocess.run([str(base), '-m', 'venv', '--without-pip', str(venv)], check=True)
    uv = shutil.which('uv')
    need(uv, 'uv_missing')
    subprocess.run([uv, 'pip', 'install', '--python', str(venv / 'bin/python'), *(requirements or MEMBER_REQUIREMENTS)], check=True)
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


# ------------------------------------------------------------------------------------------ netbox env
def cmd_netbox_env(args):
    """Immutable Python env for the NetBox MCP server (fastmcp<3), recorded for the artifacts step."""
    root, state = load_state(args.root)
    need(state.get('flavor') == 'netbox', 'netbox_flavor_required')
    need(not (root / 'netbox-env.json').exists(), 'netbox_env_already_recorded')
    if args.build:
        need(args.yes_network, 'build_needs_--yes-network')
        venv, _ = build_env(root, NETBOX_MCP_REQUIREMENTS, 'netbox-python')
    else:
        need(args.env, 'netbox_env_or_build_required')
        venv = Path(args.env).resolve()
    python = venv / 'bin/python'
    need(python.exists() and python.parent.resolve() == python.parent, 'netbox_env_python_missing')
    record = {'python': str(python), 'environment': str(venv)}
    write_private(root / 'netbox-env.json', record)
    state['steps'].append('netbox-env')
    save_state(root, state)
    return record


_SCHEMA_LISTING = """import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
python, home, source, policy, origin = sys.argv[1:6]
async def main():
    env = {'PATH': '/usr/bin:/bin', 'HOME': home, 'PYTHONPATH': source, 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHON_DOTENV_DISABLED': '1', 'LOG_LEVEL': 'ERROR', 'TRANSPORT': 'stdio', 'VERIFY_SSL': 'true',
           'NETBOX_URL': origin, 'NETBOX_TOKEN': 'nbt_schemalisting.placeholder', 'NETCLAW_NETBOX_POLICY': policy}
    params = StdioServerParameters(command=python, args=['-B', '-m', 'netbox_mcp_server.server', '--transport', 'stdio'],
                                   env=env, cwd=home)
    with open('/dev/null', 'w') as errors:
        async with stdio_client(params, errlog=errors) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                listing = await session.list_tools()
                tools = [t for t in listing.tools if t.name == 'netbox_get_object_by_id']
                assert len(tools) == 1
                print(json.dumps(tools[0].inputSchema, sort_keys=True))
asyncio.run(main())
"""


def list_netbox_schema(python, source_root, scratch, origin):
    """Actual tools/list from the real server process. tools/list contacts no NetBox: the token is a placeholder
    and the policy file only names the one URL a later real call would be allowed to read."""
    scratch = private_dir(scratch)
    policy = scratch / 'http-policy.json'
    write_private(policy, {'schemaVersion': 1, 'url': origin + '/api/dcim/devices/27/', 'params': {'fields': ','.join(NETBOX_FIELDS)}})
    done = subprocess.run([python, '-B', '-c', _SCHEMA_LISTING, python, str(scratch), str(Path(source_root) / 'src'),
                           str(policy), origin], capture_output=True, text=True, timeout=120, cwd=str(scratch),
                          env={'PATH': '/usr/bin:/bin', 'HOME': str(scratch)})
    need(done.returncode == 0 and done.stdout.strip(), 'netbox_schema_listing_failed:' + done.stderr.strip()[-200:])
    schema = json.loads(done.stdout)
    need(isinstance(schema, dict) and schema.get('type') == 'object', 'netbox_schema_shape')
    return schema


def artifacts_netbox(root, state, args):
    for step in ('freeze', 'python-env', 'netbox-env'):
        need(step in state['steps'], step + '_first')
    use_source(root)
    from bgp.federation import protected_hosted as hosted
    from bgp.federation import protected_mcp as mcp_source  # import before the profile script: keeps one source closure
    template = json.loads(Path(args.template or R05 / 'runtime-template.json').read_text())
    runtime = copy.deepcopy(template['runtime'])
    origin = (args.netbox_url or os.environ.get(NETBOX_URL_ENV) or '').rstrip('/')
    need(origin, 'netbox_url_required:' + NETBOX_URL_ENV)
    mcp_source.origin(origin)  # exact https origin or refused
    model = args.hosted_model
    need(model in hosted.ALLOWED_MODELS, 'hosted_model_refused')
    need(model == hosted.GUARD_IMAGE_MODEL or args.guard_image, 'model_needs_rebuilt_guard_image:pass --guard-image sha256:<new digest>')
    if args.guard_image:
        need(re.fullmatch('sha256:[0-9a-f]{64}', args.guard_image), 'guard_image_digest_shape')
        runtime['guard']['image'] = args.guard_image
    hosted.validate_profile(hosted_profile(model))
    provider_key = secret_from_environment(PROVIDER_KEY_ENV)
    netbox_token = secret_from_environment(NETBOX_TOKEN_ENV)
    need(provider_key != netbox_token and not provider_key.startswith('nbt_'), 'provider_key_shape')
    env_python = json.loads(read_private(root / 'netbox-env.json'))
    artifacts = private_dir(root / 'artifacts')
    # Guard: derived public config pinned by hash; secrets only in guard.env (read-only mount, guard process only).
    guard_raw = hosted_guard_config(Path(runtime['guard']['config_file']).read_bytes(), model)
    need(provider_key.encode() not in guard_raw, 'provider_key_in_guard_config')
    guard_sha = write_private(artifacts / 'guard-config.yaml', guard_raw)
    os.chmod(artifacts / 'guard-config.yaml', 0o400)
    token = secrets.token_urlsafe(32)
    need(re.fullmatch('[A-Za-z0-9_-]{43}', token) and token != provider_key, 'guard_token_shape')
    write_hosted_guard_env(artifacts / 'guard.env', provider_key, token)
    write_private(artifacts / 'guard-capability', token.encode())
    # NetBox MCP: reviewed upstream package + the managed HTTP compatibility patch, frozen read-only.
    native = private_dir(artifacts / 'native-netbox')
    package = private_dir(native / 'src/netbox_mcp_server')
    upstream = REPO / 'mcp-servers/netbox-mcp-server/src/netbox_mcp_server'
    for path in sorted(upstream.glob('*.py')):
        shutil.copyfile(path, package / path.name)
    compat = load_module('r09_netbox_compat', REPO / 'scripts/netbox-compat.py')
    compat.apply(str(native))  # refuses any unreviewed netbox_client.py; copies lib/netbox_http.py as netclaw_http.py
    for directory, dirs, names in os.walk(native):
        for name in names:
            os.chmod(Path(directory) / name, 0o400)
    for directory, _, _ in os.walk(native, topdown=False):
        os.chmod(directory, 0o500)
    skill_dir = private_dir(artifacts / 'netbox-reconcile')
    skill = (REPO / 'workspace/skills/netbox-reconcile/SKILL.md').read_bytes()
    write_private(skill_dir / 'SKILL.md', skill)
    os.chmod(skill_dir / 'SKILL.md', 0o400)
    credential = artifacts / 'netbox-credential'
    write_private(credential, ('NETBOX_TOKEN=' + netbox_token + '\n').encode())
    schema = list_netbox_schema(env_python['python'], native, artifacts / 'schema-listing', origin)
    write_private(artifacts / 'netbox-input-schema.json', schema)
    profile_script = load_module('r09_mcp_profile', REPO / 'scripts/protected-mcp-profile.py')
    binding = profile_script.materialize(kind='netbox', python=env_python['python'], source=str(native), skill=str(skill_dir / 'SKILL.md'),
                                         arguments=NETBOX_ARGUMENTS, input_schema=schema, output=artifacts / 'mcp-netbox.json',
                                         netbox_origin=origin, credential_file=str(credential))
    mcp_source.validate_binding(binding, arguments=NETBOX_ARGUMENTS)  # full file/closure/env/credential validation now
    home = root / 'home'
    runtime.pop('ollama', None)
    runtime.update(state_dir=str(home / 'netclaw-federation/runtime'), guard_token_env=GUARD_TOKEN_ENV,
                   hosted=hosted_profile(model), mcp=binding)
    runtime['guard'].update(config_file=str(artifacts / 'guard-config.yaml'), env_file=str(artifacts / 'guard.env'),
                            config_sha256=guard_sha)
    runtime['model_profile'] = {'provider': 'anthropic', 'model': model, 'runtime_kind': 'openclaw',
                                'runtime_version': HARNESS_VERSION, 'profile_id': hosted.profile_id(hosted_profile(model)),
                                'guard_policy_sha256': '0' * 64, 'profile_revision': '0' * 64}
    write_private(root / 'runtime-template.json', runtime)
    shutil.rmtree(artifacts / 'schema-listing', ignore_errors=True)
    state['hosted_model'] = model
    state['netbox_origin'] = origin
    state['steps'].append('artifacts')
    save_state(root, state)
    return {'artifacts': str(artifacts), 'netbox_origin': origin, 'hosted_model': model,
            'guard_config_sha256': guard_sha, 'selection_sha256': binding['selection_sha256'],
            'secrets': 'written 0600 to artifacts/guard.env and artifacts/netbox-credential; not printed or stored in state',
            'model_namespace': 'none (hosted flavor): do not run qualify.py'}


# ---------------------------------------------------------------------------------------------- artifacts
def cmd_artifacts(args):
    root, state = load_state(args.root)
    if state.get('flavor') == 'netbox':
        return artifacts_netbox(root, state, args)
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
    netbox = state.get('flavor') == 'netbox'
    for step in ('identity', 'freeze', 'python-env', 'artifacts') + (('netbox-env',) if netbox else ()):
        need(step in state['steps'], step + '_first')
    if not netbox:
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
    if not netbox:
        runtime['ollama'] = json.loads(read_private(root / 'model/profile.json'))
    bindings = revision_bindings(runtime)
    runtime['model_profile'].update({k: bindings[k] for k in ('guard_policy_sha256', 'profile_revision')})
    validate_runtime_fields(runtime)
    arguments = dict(NETBOX_ARGUMENTS) if netbox else {'cidr': '192.0.2.0/26'}
    tool = {'tool': 'netbox_get_object_by_id' if netbox else 'subnet_calculator',
            'tool_schema_sha256': bindings['tool_schema_sha256'], 'arguments': arguments,
            'arguments_sha256': sha(canonical(arguments)),
            'device_ref': 'dcim.device:%d' % arguments['object_id'] if netbox else '192.0.2.0/26',
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
                'environment': {'NETCLAW_LOCAL_AS': '65190' if netbox else '65189',
                                'NETCLAW_ROUTER_ID': '127.0.0.10' if netbox else '127.0.0.9',
                                'N2N_DISPLAY_NAME': 'R09 NetBox member' if netbox else 'R09 Mac member',
                                'BGP_API_PORT': '18190' if netbox else '18189', 'N2N_INVENTORY_REFRESH_S': '0'}}
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
        modules = ('bgp.federation.ha.factory, bgp.federation.ha.member, bgp.federation.protected_docker, '
                   'bgp.federation.protected_hosted, bgp.federation.ha.hosted_model_transport, bgp.federation.protected_mcp'
                   if state.get('flavor') == 'netbox' else
                   'bgp.federation.ha.factory, bgp.federation.ha.member, bgp.federation.protected_docker, '
                   'bgp.federation.protected_ollama, bgp.federation.protected_mcp')
        code = ("import sys; sys.path.insert(0, %r); import %s; print('closure-ok')"
                % (str(root / 'source/mcp-servers/protocol-mcp'), modules))
        done = subprocess.run([cfg['python'], '-I', '-B', '-c', code], capture_output=True, text=True, timeout=120)
        result['closure_import'] = 'ok' if done.stdout.strip() == 'closure-ok' else 'failed:' + done.stderr.strip()[-400:]
    return result


def cmd_plan(args):
    if getattr(args, 'flavor', 'ollama') == 'netbox':
        return {'order': [
            {'who': 'builder', 'step': 'identity --flavor netbox, freeze, python-env (offline)'},
            {'who': 'owner', 'step': 'netbox-env --build --yes-network (uv installs fastmcp<3 etc. into an immutable env) or --env <prepared venv>'},
            {'who': 'owner', 'step': 'source ~/.openclaw/.env (exports NETBOX_URL, NETBOX_TOKEN, ANTHROPIC_API_KEY into this shell only), then '
                                     'artifacts: writes guard.env and the NetBox credential file 0600; no value is printed or stored'},
            {'who': 'builder', 'step': 'materialize, validate (no qualify.py and no model namespace for this flavor)'},
            {'who': 'parent', 'step': 'ENROLL: stop 3 Borders, wait 15 s, one-shot enroll_member with identity/member.json, restart Borders'},
            {'who': 'owner', 'step': 'start the member with the production launcher (same command as the calculator member)'},
            {'who': 'parent', 'step': 'verify 3 attachments, then prepare/approve netbox_get_object_by_id dcim.device 27 from the HUD or VS Code'}]}
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
    plan = sub.add_parser('plan')
    plan.add_argument('--flavor', choices=FLAVORS, default='ollama')
    for name in ('identity', 'freeze', 'python-env', 'netbox-env', 'artifacts', 'materialize', 'validate'):
        p = sub.add_parser(name)
        p.add_argument('--root', required=True)
        if name == 'identity':
            p.add_argument('--deployment', default=str(DEFAULT_DEPLOYMENT))
            p.add_argument('--days', type=int, default=7)
            p.add_argument('--flavor', choices=FLAVORS, default='ollama')
        if name == 'netbox-env':
            p.add_argument('--env'); p.add_argument('--build', action='store_true'); p.add_argument('--yes-network', action='store_true')
        if name == 'python-env':
            p.add_argument('--env'); p.add_argument('--env-manifest')
            p.add_argument('--build', action='store_true'); p.add_argument('--yes-network', action='store_true')
        if name == 'artifacts':
            p.add_argument('--template')
            p.add_argument('--netbox-url', help='https origin (default: $NETBOX_URL); NetBox flavor only')
            p.add_argument('--hosted-model', default=HOSTED_MODEL, help='NetBox flavor; default is the model the existing guard image pins')
            p.add_argument('--guard-image', help='sha256 digest of a rebuilt guard image (required for any other model)')
        if name == 'validate':
            p.add_argument('--skip-import-check', action='store_true')
    args = parser.parse_args(argv)
    command = {'plan': cmd_plan, 'identity': cmd_identity, 'freeze': cmd_freeze, 'python-env': cmd_python_env,
               'netbox-env': cmd_netbox_env, 'artifacts': cmd_artifacts, 'materialize': cmd_materialize, 'validate': cmd_validate}[args.action]
    print(json.dumps(command(args), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
