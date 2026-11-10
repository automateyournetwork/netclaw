"""Spec 183: a member's scoped config keeps the MCP servers its skills call.

Source and fixture checks only: no gateway, provider or MCP server is started.
"""
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / 'workspace/skills'

# Servers a profile may name although config/openclaw.json does not register
# them: the operator adds them, following the named enable script.
OPERATOR_REGISTERED = {'ipfabric-mcp': 'scripts/ipfabric-enable.sh'}
# MCP_SERVERS keys with no PROFILE_MATCHERS entry (in2n-member-home.py --member <key>).
UNMATCHED_KEYS = {'splunk', 'gnmi'}
# Catalog-bound servers a profile deliberately does not keep (research.md).
NOT_KEPT = {
    'asa': {'pyats-mcp'},            # unresolved: profile gated on ASA_*, skill calls pyATS
    'checkpoint': {'chkp-argos-erm', 'chkp-cpinfo-analysis', 'chkp-documentation',
                   'chkp-gw-connection-analysis', 'chkp-harmony-sase', 'chkp-https-inspection',
                   'chkp-quantum-gw-cli', 'chkp-reputation-service', 'chkp-spark-management',
                   'chkp-threat-emulation'},  # unresolved: existing subset kept
    # The catalog binds per component: drawio-diagram inherits rfc-mcp (drawio-rfc) and
    # aws-architecture-diagram every AWS server; those skills call only drawio/aws-diagram.
    'viz': {'rfc-mcp', 'aws-network-mcp', 'aws-iam-mcp', 'aws-cloudtrail-mcp',
            'aws-cloudwatch-mcp', 'aws-cost-explorer-mcp'},
}


def load(name):
    spec = importlib.util.spec_from_file_location('spec182_' + name.replace('-', '_'),
                                                  ROOT / 'scripts' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def profiles():
    return load('in2n-profiles.py')


@pytest.fixture(scope='module')
def registered():
    return set(json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers'])


@pytest.fixture(scope='module')
def catalog_servers():
    catalog = json.loads((ROOT / 'config/components/catalog.json').read_text())
    return {skill['id']: set(skill.get('servers') or []) for skill in catalog['skills']}


def installed():
    return sorted(p.name for p in SKILLS.iterdir() if (p / 'SKILL.md').is_file())


def test_every_named_server_is_registered(profiles, registered):
    missing = {}
    for profile, servers in profiles.MCP_SERVERS.items():
        for server in servers:
            if server in registered:
                continue
            script = OPERATOR_REGISTERED.get(server)
            if script and server in (ROOT / script).read_text():
                continue
            missing.setdefault(profile, []).append(server)
    assert missing == {}


def test_every_key_is_a_profile(profiles):
    assert set(profiles.MCP_SERVERS) - set(profiles.PROFILE_MATCHERS) == UNMATCHED_KEYS


@pytest.mark.parametrize('profile,expected', [
    ('pyats', ['pyats-mcp']),
    ('cml', ['cml-mcp']),
    ('nautobot', ['nautobot-mcp']),
    ('github', ['github-mcp']),
    ('netbox', ['netbox-mcp']),
    ('catalyst-center', ['catc-mcp']),
    ('fortimanager', ['fortinet-mcp']),
])
def test_corrected_mappings(profiles, profile, expected):
    assert profiles.MCP_SERVERS[profile] == expected


def test_github_member_no_longer_gets_gitlab(profiles):
    assert 'gitlab-mcp' not in profiles.MCP_SERVERS['github']


def test_unresolved_profiles_unchanged(profiles):
    for profile in ('eve-ng', 'containerlab', 'aci', 'f5', 'ise', 'infoblox', 'asa'):
        assert profile not in profiles.MCP_SERVERS
    assert profiles.MCP_SERVERS['checkpoint'] == [
        'chkp-management', 'chkp-management-logs', 'chkp-policy-insights',
        'chkp-threat-prevention', 'chkp-quantum-gaia']


def test_mappings_match_catalog_skill_bindings(profiles, catalog_servers):
    """Each profile keeps exactly the catalog servers its matched skills are bound to,
    apart from the recorded exceptions. Catches drift when skills or servers change."""
    skills = installed()
    drift = {}
    for profile in profiles.PROFILE_MATCHERS:
        bound = set().union(*(catalog_servers.get(s, set())
                              for s in profiles._match_profile(profile, skills)))
        kept = set(profiles.MCP_SERVERS.get(profile, []))
        extra = kept - bound - {s for s in kept if s in OPERATOR_REGISTERED}
        lacking = bound - kept - NOT_KEPT.get(profile, set())
        if extra or lacking:
            drift[profile] = {'extra': sorted(extra), 'lacking': sorted(lacking)}
    assert drift == {}


def test_scoped_mcp_servers_on_minimal_template(profiles):
    home = load('in2n-member-home.py')
    servers = {name: {'command': name} for name in (
        'pyats-mcp', 'cml-mcp', 'gitlab-mcp', 'github-mcp', 'memory-mcp', 'slack-mcp')}
    assert set(home.scoped_mcp_servers(servers, 'pyats', profiles)) == {'pyats-mcp', 'memory-mcp'}
    assert set(home.scoped_mcp_servers(servers, 'github', profiles)) == {'github-mcp', 'memory-mcp'}
    # A server the Border has not registered is skipped, not invented.
    assert set(home.scoped_mcp_servers(servers, 'nautobot', profiles)) == {'memory-mcp'}
    assert set(home.scoped_mcp_servers(servers, 'eve-ng', profiles)) == {'memory-mcp'}


def test_member_home_writes_scoped_servers(tmp_path):
    border = tmp_path / 'border'
    (border / 'workspace').mkdir(parents=True)
    template = {'mcp': {'servers': {name: {'command': name} for name in (
        'cml-mcp', 'pyats-mcp', 'gitlab-mcp', 'memory-mcp')}},
        'plugins': {'entries': {'slack': {'enabled': True}}}, 'channels': {'slack': {}}}
    (border / 'openclaw.json').write_text(json.dumps(template))
    (border / '.env').write_text('ANTHROPIC_API_KEY=fixture\n')
    member = tmp_path / 'member'
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'HERMES_'))}
    env['HOME'] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
         '--risk', 'lab', '--member', 'cml', '--border-config', str(border / 'openclaw.json'),
         '--anthropic-key-from', str(border / '.env'), '--home', str(member)],
        env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())
    assert set(written['mcp']['servers']) == {'cml-mcp', 'memory-mcp'}
    assert written['channels'] == {}


# ── Env slices: a kept server's ${VAR}s reach the member ──

COMMS = ('SLACK_', 'DISCORD_', 'WEBEX_', 'TWILIO_', 'TWITTER_', 'MSTEAMS_')
SHARED = ('SERVICENOW_',) + COMMS


@pytest.fixture(scope='module')
def template():
    """The repository template's servers (install-mcp-config.py's input)."""
    return json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']


def install_config(border, env_text=''):
    """Run install-mcp-config.py for every component, as the installer does, into a
    fixture Border; return its mcp.servers (native_entry output, NETCLAW_RUNTIME_*)."""
    border.mkdir(mode=0o700, exist_ok=True)
    (border / '.env').write_text(env_text)
    (border / '.env').chmod(0o600)
    records = border / 'python-runtimes/records'
    records.mkdir(parents=True, exist_ok=True)
    for component in ('netbox', 'nmap', 'nvd-cve', 'packet-buddy', 'subnet-calc'):
        (records / component).write_text(sys.executable + '\n')
    components = ' '.join(c['id'] for c in json.loads(
        (ROOT / 'config/components/catalog.json').read_text())['components'])
    out = border / 'generated.json'
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'HERMES_'))}
    env['HOME'] = str(border.parent)
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/install-mcp-config.py'), '--repo', str(ROOT),
                             '--runtime-root', str(border / 'python-runtimes'), '--components', components,
                             '--output', str(out)], env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    servers = json.loads(out.read_text())['mcpServers']
    (border / 'openclaw.json').write_text(json.dumps({'mcp': {'servers': servers}}))
    (border / 'openclaw.json').chmod(0o600)
    return servers


@pytest.fixture(scope='module')
def installed_border(tmp_path_factory):
    border = tmp_path_factory.mktemp('installed') / '.openclaw'
    return border, install_config(border)


def every_ref(profiles, servers):
    return set().union(*(profiles.server_env_refs(v) for v in servers.values()))


def all_profiles(profiles):
    return sorted(set(profiles.PROFILE_MATCHERS) | set(profiles.MCP_SERVERS))


@pytest.mark.parametrize('source', ['template', 'installed'])
def test_slice_holds_every_var_kept_servers_reference(profiles, template, installed_border, source):
    servers = template if source == 'template' else installed_border[1]
    env_keys = every_ref(profiles, servers) | {'SLACK_BOT_TOKEN', 'UNRELATED_SECRET'}
    missing = {}
    for profile in all_profiles(profiles):
        wanted = {n for n in every_ref(profiles, profiles.member_servers(profile, servers))
                  if profiles.derived_ref_allowed(n)}
        lacking = wanted - set(profiles.env_slice_keys(profile, env_keys, servers))
        if lacking:
            missing[profile] = sorted(lacking)
    assert missing == {}


def test_slice_holds_only_prefixes_and_kept_server_refs(profiles, template):
    env_keys = every_ref(profiles, template) | {'SLACK_BOT_TOKEN', 'DISCORD_TOKEN', 'UNRELATED_SECRET'}
    for profile in all_profiles(profiles):
        prefixes = tuple(profiles.ENV_PREFIXES.get(profile, []) + profiles.BASE_MEMBER_ENV_PREFIXES)
        allowed = every_ref(profiles, profiles.member_servers(profile, template))
        keys = profiles.env_slice_keys(profile, env_keys, template)
        for key in keys:
            assert key.startswith(prefixes) or key in allowed, (profile, key)
        assert not [k for k in keys if k.startswith(SHARED)], profile


@pytest.mark.parametrize('profile,keys', [
    ('aap', {'EDA_URL', 'EDA_TOKEN', 'REDHAT_USERNAME', 'REDHAT_PASSWORD'}),
    ('catalyst-center', {'CATALYST_CENTER_HOST', 'CATALYST_CENTER_PASSWORD'}),
    ('terraform', {'TFC_TOKEN', 'TFC_ORG'}),
    ('claroty', {'NETCLAW_LAB_MODE'}),
    ('nautobot', {'ITSM_ENABLED', 'ITSM_LAB_MODE'}),
    ('viz', {'KROKI_SERVER', 'PLANTUML_SERVER', 'AWS_REGION'}),
    ('sdwan', {'PAN_CLIENT_ID', 'PAN_CLIENT_SECRET'}),
    ('gns3', {'GNS3_URL', 'GNS3_PASSWORD'}),
    ('splunk', {'SPLUNK_HOST', 'SPLUNK_TOKEN'}),
    ('gnmi', {'GNMI_TARGETS', 'GNMI_TLS_CLIENT_KEY'}),
])
def test_previously_missing_vars_now_in_slice(profiles, template, profile, keys):
    assert keys <= set(profiles.env_slice_keys(profile, every_ref(profiles, template), template))


@pytest.mark.parametrize('profile', ['claroty', 'fortimanager', 'gnmi'])
def test_servicenow_is_not_derived(profiles, template, profile):
    """Their servers reference SERVICENOW_*, and their gates fail closed without it."""
    assert 'SERVICENOW_PASSWORD' in every_ref(profiles, profiles.member_servers(profile, template))
    keys = profiles.env_slice_keys(profile, every_ref(profiles, template), template)
    assert not [k for k in keys if k.startswith('SERVICENOW_')]


def test_operator_can_grant_shared_prefix(template):
    granted = load('in2n-profiles.py')
    granted.ENV_PREFIXES['claroty'] = granted.ENV_PREFIXES['claroty'] + ['SERVICENOW_']
    assert 'SERVICENOW_PASSWORD' in granted.env_slice_keys('claroty', {'SERVICENOW_PASSWORD'}, template)


def test_comms_keys_never_derived(profiles):
    servers = {'memory-mcp': {'env': {'A': '${EMAIL_PASSWORD}', 'B': '${SLACK_BOT_TOKEN}',
                                      'C': '${TELEGRAM_BOT_TOKEN}', 'D': '${MEMORY_DATA_DIR}'}}}
    assert 'EMAIL_PASSWORD' in profiles.DERIVED_DENY_KEYS   # from config/components/comms.json
    assert profiles.env_slice_keys('nmap', {'EMAIL_PASSWORD', 'SLACK_BOT_TOKEN', 'TELEGRAM_BOT_TOKEN',
                                            'MEMORY_DATA_DIR'}, servers) == ['MEMORY_DATA_DIR']


def test_server_not_kept_contributes_nothing(profiles):
    servers = {
        'github-mcp': {'command': 'docker', 'env': {'T': '${GITHUB_PERSONAL_ACCESS_TOKEN}'}},
        'gitlab-mcp': {'command': 'npx', 'env': {'T': '${GITLAB_PERSONAL_ACCESS_TOKEN}'}},
        'twilio-mcp': {'command': 'npx', 'args': ['--sid', '${TWILIO_ACCOUNT_SID}']},
        'memory-mcp': {'command': 'python3', 'env': {'D': '${MEMORY_DATA_DIR}'}},
    }
    env_keys = {'GITHUB_PERSONAL_ACCESS_TOKEN', 'GITLAB_PERSONAL_ACCESS_TOKEN',
                'TWILIO_ACCOUNT_SID', 'SLACK_BOT_TOKEN', 'MEMORY_DATA_DIR'}
    assert profiles.env_slice_keys('github', env_keys, servers) == [
        'GITHUB_PERSONAL_ACCESS_TOKEN', 'MEMORY_DATA_DIR']
    # A Border that has not registered the profile's server adds nothing for it.
    assert profiles.env_slice_keys('terraform', {'TFC_TOKEN'}, servers) == []


def test_refs_in_command_args_url_and_defaults(profiles):
    entry = {'command': '${LAUNCHER}', 'args': ['--host', 'https://${HOST_A}:${PORT:-443}/x'],
             'url': '${REMOTE_URL}', 'headers': {'Authorization': 'Bearer ${TOKEN-none}'},
             'env': {'X': '${X_VAR}', 'LITERAL': '$NOT_BRACED'}}
    assert profiles.server_env_refs(entry) == {'LAUNCHER', 'HOST_A', 'PORT', 'REMOTE_URL', 'TOKEN', 'X_VAR'}


def test_ref_parsing_edge_cases(profiles):
    # A nested default references both names.
    assert profiles.server_env_refs({'env': {'X': '${A:-${B}}'}}) == {'A', 'B'}
    # Dict keys name what the server sees; they are not references.
    assert profiles.server_env_refs({'env': {'${KEY_REF}': 'literal'}}) == set()
    # No escape: $${ESC} still contains ${ESC}, as mcp_environment.BARE reads it.
    assert profiles.server_env_refs({'args': ['$${ESC}', '$$', '$', '${', '${1BAD}']}) == {'ESC'}


def test_without_template_only_prefixes_apply(profiles):
    assert profiles.env_slice_keys('terraform', {'TFC_TOKEN', 'TF_TOKEN', 'GAIT_X'}) == ['GAIT_X', 'TF_TOKEN']


# ── Member runtime paths: never the Border's .env (review round 1) ──

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def test_installed_entries_carry_border_runtime(installed_border):
    border, servers = installed_border
    launched = [k for k, v in servers.items() if (v.get('env') or {}).get('NETCLAW_RUNTIME_ENV')]
    assert {'pyats-mcp', 'netbox-mcp', 'nmap-mcp', 'drawio-mcp'} <= set(launched)
    assert servers['pyats-mcp']['env']['NETCLAW_RUNTIME_ENV'] == str((border / '.env').resolve())


def test_no_kept_entry_points_at_border_runtime(profiles, installed_border, tmp_path):
    home = load('in2n-member-home.py')
    border, servers = installed_border
    border_env, border_root = str((border / '.env').resolve()), str((border / 'python-runtimes').resolve())
    member = tmp_path / 'member'
    for profile in all_profiles(profiles):
        kept = home.scoped_mcp_servers(servers, profile, profiles, home=member)
        for name, entry in kept.items():
            for text in strings(entry):
                assert border_env not in text and border_root not in text, (profile, name, text)
            env = entry.get('env') or {}
            if 'NETCLAW_RUNTIME_ENV' in env:
                assert env['NETCLAW_RUNTIME_ENV'] == str(member / '.env')
                assert env['NETCLAW_RUNTIME_ROOT'] == str(member / 'python-runtimes')
    # The Border's own map is not modified.
    assert servers['pyats-mcp']['env']['NETCLAW_RUNTIME_ENV'] == border_env


def test_component_launch_entry_without_runtime_env_gets_member_paths(profiles, tmp_path):
    home = load('in2n-member-home.py')
    servers = {'nmap-mcp': {'command': 'python3', 'args': ['-u', '/repo/scripts/component-launch.py',
                                                           'nmap', '--server', 'nmap-mcp']}}
    kept = home.scoped_mcp_servers(servers, 'nmap', profiles, home=tmp_path, member_env=tmp_path / 'm.env')
    assert kept['nmap-mcp']['env'] == {'NETCLAW_RUNTIME_ROOT': str(tmp_path / 'python-runtimes'),
                                       'NETCLAW_RUNTIME_ENV': str(tmp_path / 'm.env')}


def run_member_home(tmp_path, border, member, profile, *extra, cwd=None):
    (border / 'workspace').mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'HERMES_'))}
    env['HOME'] = str(tmp_path)
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
         '--risk', 'lab', '--member', profile, '--border-config', str(border / 'openclaw.json'),
         '--anthropic-key-from', str(border / '.env'), '--home', str(member), *extra],
        env=env, capture_output=True, text=True, timeout=60, cwd=cwd)


def test_member_home_refuses_border_env_and_home(tmp_path):
    """Round 3: the fail-closed check must not accept the Border's own .env or home."""
    border = tmp_path / '.openclaw'
    install_config(border, 'ANTHROPIC_API_KEY=fixture\nSLACK_BOT_TOKEN=must-not-reach-member\n')
    before = (border / 'openclaw.json').read_text()
    member = tmp_path / 'member-pyats'
    hardlink = tmp_path / 'hard.env'
    os.link(border / '.env', hardlink)
    for target in (border / '.env', tmp_path / 'member-pyats/../.openclaw/.env', hardlink):
        result = run_member_home(tmp_path, border, member, 'pyats', '--member-env', str(target))
        assert result.returncode != 0, target
        assert "the Border's .env" in result.stderr and 'Traceback' not in result.stderr
        assert not (member / 'openclaw.json').exists()
    # --home at the Border's home, with or without --member-env, is refused before any write.
    for extra in ((), ('--member-env', str(private_file(tmp_path / 'm.env')))):
        result = run_member_home(tmp_path, border, border, 'pyats', *extra)
        assert result.returncode != 0
        assert "is the Border's home" in result.stderr and 'Traceback' not in result.stderr
    result = run_member_home(tmp_path, border, tmp_path / 'x/../.openclaw', 'cml')
    assert result.returncode != 0 and "is the Border's home" in result.stderr
    assert (border / 'openclaw.json').read_text() == before


def test_member_env_directory_refused_and_relative_made_absolute(tmp_path):
    border = tmp_path / '.openclaw'
    install_config(border, 'ANTHROPIC_API_KEY=fixture\n')
    member = tmp_path / 'member-nmap'
    (tmp_path / 'envdir').mkdir()
    result = run_member_home(tmp_path, border, member, 'nmap', '--member-env', str(tmp_path / 'envdir'))
    assert result.returncode != 0 and 'not a regular file' in result.stderr
    assert not (member / 'openclaw.json').exists()
    private_file(tmp_path / 'stage/members/nmap/.env', 'NMAP_MCP_SCRIPT=/fixture\n')
    result = run_member_home(tmp_path, border, member, 'nmap', '--member-env', 'stage/members/nmap/.env',
                             cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    nmap = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']['nmap-mcp']
    assert nmap['env']['NETCLAW_RUNTIME_ENV'] == str(tmp_path / 'stage/members/nmap/.env')


def private_file(path, text=''):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)
    return path


def test_member_home_from_installed_config(tmp_path):
    border = tmp_path / '.openclaw'
    install_config(border, 'ANTHROPIC_API_KEY=fixture\nSLACK_BOT_TOKEN=must-not-reach-member\n')
    for profile in ('pyats', 'netbox', 'viz'):
        member = tmp_path / ('member-' + profile)
        private_file(member / '.env', 'MEMORY_DATA_DIR=/fixture\n')   # default: <home>/.env
        result = run_member_home(tmp_path, border, member, profile)
        assert result.returncode == 0, result.stderr
        written = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']
        text = json.dumps(written)
        assert str((border / '.env').resolve()) not in text
        assert str((border / 'python-runtimes').resolve()) not in text
        for entry in written.values():
            env = entry.get('env') or {}
            if 'NETCLAW_RUNTIME_ENV' in env:
                assert env['NETCLAW_RUNTIME_ENV'] == str(member / '.env')
    pyats = json.loads((tmp_path / 'member-pyats/openclaw.json').read_text())['mcp']['servers']['pyats-mcp']
    assert pyats['env']['PYATS_VENV'] == str((border / 'pyats-venv').resolve())
    record = tmp_path / 'member-netbox/python-runtimes/records/netbox'
    assert record.read_text().strip() == sys.executable
    assert record.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / 'member-netbox/python-runtimes/records').stat().st_mode & 0o777 == 0o700
    # --member-env selects the member's private file instead of <home>/.env.
    member = tmp_path / 'member-nmap'
    staged = private_file(tmp_path / 'stage/members/nmap/.env', 'NMAP_MCP_SCRIPT=/fixture\n')
    result = run_member_home(tmp_path, border, member, 'nmap', '--member-env', str(staged))
    assert result.returncode == 0, result.stderr
    nmap = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']['nmap-mcp']
    assert nmap['env']['NETCLAW_RUNTIME_ENV'] == str(staged)


def test_member_home_refuses_without_member_env(tmp_path):
    """Fail closed: a component-launched server must not point at a missing env file."""
    border = tmp_path / '.openclaw'
    install_config(border, 'ANTHROPIC_API_KEY=fixture\n')
    member = tmp_path / 'member-pyats'
    result = run_member_home(tmp_path, border, member, 'pyats')
    assert result.returncode != 0
    assert '--member-env' in result.stderr and 'pyats-mcp' in result.stderr
    assert str(member / '.env') in result.stderr and 'Traceback' not in result.stderr
    assert not (member / 'openclaw.json').exists()
    missing = tmp_path / 'stage/members/pyats/.env'
    result = run_member_home(tmp_path, border, member, 'pyats', '--member-env', str(missing))
    assert result.returncode != 0 and str(missing) in result.stderr
    # A symlinked env file is refused too.
    target = private_file(tmp_path / 'real.env')
    link = tmp_path / 'link.env'
    link.symlink_to(target)
    result = run_member_home(tmp_path, border, member, 'pyats', '--member-env', str(link))
    assert result.returncode != 0 and not (member / 'openclaw.json').exists()
    # A member whose kept servers load no env file needs none.
    result = run_member_home(tmp_path, border, tmp_path / 'member-cml', 'cml')
    assert result.returncode == 0, result.stderr


def test_pyats_venv_from_border_root_when_entry_has_no_runtime(profiles, tmp_path):
    home = load('in2n-member-home.py')
    servers = {'pyats-mcp': {'command': 'python3', 'args': ['/repo/scripts/component-launch.py', 'pyats']}}
    border_root = tmp_path / 'border/python-runtimes'
    kept = home.scoped_mcp_servers(servers, 'pyats', profiles, home=tmp_path / 'm', border_root=border_root)
    env = kept['pyats-mcp']['env']
    assert env['PYATS_VENV'] == str(tmp_path / 'border/pyats-venv')
    assert env['NETCLAW_RUNTIME_ROOT'] == str(tmp_path / 'm/python-runtimes')
    # main() derives the Border root from the config's directory for such an entry.
    border = tmp_path / '.openclaw'
    border.mkdir(mode=0o700)
    (border / 'openclaw.json').write_text(json.dumps({'mcp': {'servers': servers}}))
    (border / '.env').write_text('ANTHROPIC_API_KEY=fixture\n')
    member = tmp_path / 'member'
    private_file(member / '.env')
    result = run_member_home(tmp_path, border, member, 'pyats')
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']['pyats-mcp']
    assert written['env']['PYATS_VENV'] == str((border / 'pyats-venv').resolve())


def test_copy_runtime_records_refuses_symlinked_target(tmp_path):
    home = load('in2n-member-home.py')
    border_root = tmp_path / 'border/python-runtimes'
    private_file(border_root / 'records/nmap', sys.executable + '\n')
    records = tmp_path / 'member/python-runtimes/records'
    records.mkdir(parents=True, mode=0o700)
    (tmp_path / 'member/python-runtimes').chmod(0o700)
    elsewhere = private_file(tmp_path / 'elsewhere', 'keep')
    (records / 'nmap').symlink_to(elsewhere)
    servers = {'nmap-mcp': {'args': ['/repo/scripts/component-launch.py', 'nmap']}}
    with pytest.raises(ValueError, match='symlink'):
        home.copy_runtime_records(servers, tmp_path / 'member', border_root)
    assert elsewhere.read_text() == 'keep'


def test_member_pyats_change_root_is_the_members(tmp_path):
    """component-launch derives NETCLAW_CHANGE_ROOT from the member's runtime root, and a
    member vault holds no HUD grant, policy or signing key, so a private apply is refused."""
    spec = importlib.util.spec_from_file_location('spec182_launch', ROOT / 'scripts/component-launch.py')
    launch = importlib.util.module_from_spec(spec); spec.loader.exec_module(launch)
    member = tmp_path / 'member'
    border_env = private_file(tmp_path / 'border/.env', 'SLACK_BOT_TOKEN=must-not-load\n')
    private_file(member / '.env', 'PYATS_TESTBED_PATH=/fixture\n')
    env = {'HOME': str(tmp_path), 'PATH': os.environ.get('PATH', ''),
           'NETCLAW_RUNTIME_ROOT': str(member / 'python-runtimes'),
           'NETCLAW_RUNTIME_ENV': str(member / '.env'),
           'PYATS_VENV': str(tmp_path / 'border/pyats-venv')}
    _parts, resolved, _cwd = launch.resolve('pyats', 'pyats-mcp', env)
    assert resolved['NETCLAW_CHANGE_ROOT'] == str(member / 'netclaw-changes')
    assert resolved['PYATS_TESTBED_PATH'] == '/fixture' and 'SLACK_BOT_TOKEN' not in resolved
    assert resolved['PYATS_VENV'] == str(tmp_path / 'border/pyats-venv')
    assert border_env.read_text()  # untouched; never loaded
    sys.path.insert(0, str(ROOT / 'scripts/lib'))
    from migration_artifacts import PrivateMigration, Refused
    vault = PrivateMigration(resolved['NETCLAW_CHANGE_ROOT'])
    with pytest.raises(Refused):   # no grants/ directory: nothing the HUD issued
        vault.claim('0' * 32, '1' * 32, {'testbed': 'x', 'devices': []}, {'id': 'r1'})
    assert not (member / 'netclaw-changes/attempts').exists()


def run_migrate(tmp_path, staging='stage'):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'HERMES_', 'CATC_', 'CATALYST_', 'CLAROTY_',
                                'PYATS_', 'SERVICENOW_'))}
    env['HOME'] = str(tmp_path)
    return subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-migrate.py'), '--risk', 'lab',
                           '--staging', str(tmp_path / staging)],
                          env=env, capture_output=True, text=True, timeout=120)


def slice_keys(path):
    return {line.split('=', 1)[0] for line in path.read_text().splitlines()
            if '=' in line and not line.startswith('#')}


def test_migrate_writes_server_vars_from_installed_config(tmp_path):
    border = tmp_path / '.openclaw'
    install_config(border, 'CATC_MCP_SCRIPT=/fixture\nCATALYST_CENTER_HOST=fixture\n'
                           'CATALYST_CENTER_PASSWORD=fixture\nCLAROTY_MCP_CMD=/fixture\n'
                           'CLAROTY_API_TOKEN=fixture\nNETCLAW_LAB_MODE=false\n'
                           'SERVICENOW_PASSWORD=must-not-copy\nPYATS_MCP_SCRIPT=/fixture\n'
                           'PYATS_TESTBED_PATH=/fixture\nSLACK_BOT_TOKEN=must-not-copy\n'
                           'GITLAB_PERSONAL_ACCESS_TOKEN=must-not-copy\nMEMORY_DATA_DIR=/fixture\n')
    result = run_migrate(tmp_path)
    assert result.returncode == 0, result.stderr
    assert 'WARNING' not in result.stderr
    stage = tmp_path / 'stage/members'
    never = {'SLACK_BOT_TOKEN', 'GITLAB_PERSONAL_ACCESS_TOKEN', 'SERVICENOW_PASSWORD'}
    catc = slice_keys(stage / 'catalyst-center/.env')
    assert {'CATC_MCP_SCRIPT', 'CATALYST_CENTER_HOST', 'CATALYST_CENTER_PASSWORD', 'MEMORY_DATA_DIR'} <= catc
    claroty = slice_keys(stage / 'claroty/.env')
    assert {'CLAROTY_MCP_CMD', 'CLAROTY_API_TOKEN', 'NETCLAW_LAB_MODE'} <= claroty
    pyats = slice_keys(stage / 'pyats/.env')
    assert {'PYATS_MCP_SCRIPT', 'PYATS_TESTBED_PATH'} <= pyats
    for keys in (catc, claroty, pyats):
        assert not keys & never
    assert 'CLAROTY_API_TOKEN' not in catc | pyats
    assert not {k for k in catc | claroty if k.startswith('PYATS_')}
    for member in ('catalyst-center', 'claroty', 'pyats'):
        assert (stage / member / '.env').stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('staging', ['stage', 'st age$x'])
def test_migrate_prints_member_home_command_that_works(tmp_path, staging):
    border = tmp_path / '.openclaw'
    install_config(border, 'ANTHROPIC_API_KEY=fixture\nPYATS_MCP_SCRIPT=/fixture\n'
                           'PYATS_TESTBED_PATH=/fixture\nSLACK_BOT_TOKEN=must-not-copy\n')
    (border / 'workspace').mkdir()
    result = run_migrate(tmp_path, staging)
    assert result.returncode == 0, result.stderr
    staged = tmp_path / staging / 'members/pyats/.env'
    lines = [l.strip() for l in result.stdout.splitlines() if 'in2n-member-home.py' in l]
    command = next(l for l in lines if '--member pyats' in l)
    assert command.endswith('--member-env ' + shlex.quote(str(staged)))
    assert command in (tmp_path / staging / 'RUNBOOK.md').read_text()
    argv = shlex.split(command)
    assert argv[0] == 'python3' and argv[-2:] == ['--member-env', str(staged)]
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'HERMES_'))}
    env['HOME'] = str(tmp_path)
    run = subprocess.run([sys.executable, *argv[1:]], env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    written = json.loads((tmp_path / '.openclaw-lab-pyats/openclaw.json').read_text())['mcp']['servers']
    assert written['pyats-mcp']['env']['NETCLAW_RUNTIME_ENV'] == str(staged)


def test_migrate_warns_without_border_config(tmp_path):
    border = tmp_path / '.openclaw'
    border.mkdir(mode=0o700)
    (border / 'openclaw.json').write_text('{not json')
    (border / '.env').write_text('CATC_MCP_SCRIPT=/fixture\nCATALYST_CENTER_HOST=fixture\n')
    (border / '.env').chmod(0o600)
    result = run_migrate(tmp_path)
    assert result.returncode == 0, result.stderr
    assert 'WARNING: Border config ' + str(border / 'openclaw.json') in result.stderr
    assert 'catc-mcp' in result.stderr
    assert 'CATALYST_CENTER_HOST' not in slice_keys(tmp_path / 'stage/members/catalyst-center/.env')
