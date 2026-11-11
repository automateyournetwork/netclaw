"""Spec 184: provision an iN2N member from a declarative member spec.

Source and fixture checks only: no gateway, provider, daemon or MCP server is started.
Fixture Borders are built by install-mcp-config.py, as in spec 183's tests.
"""
import copy
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE_SKILLS = ['memory', 'gait-session-tracking', 'humanrail-escalation']


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


T182 = load(ROOT / 'tests/n2n/test_member_mcp_mappings_183.py', 'spec183_t182')
install_config, private_file, slice_keys = T182.install_config, T182.private_file, T182.slice_keys

# The operator-registered pfsense server (not a NetClaw component) the Convergence
# investigator needs; a spec may keep any server the Border template has.
PFSENSE = {'command': 'npx', 'args': ['-y', 'pfsense-mcp'],
           'env': {'PFSENSE_URL': '${PFSENSE_URL}', 'PFSENSE_API_KEY': '${PFSENSE_API_KEY}'}}

EXAMPLE = {
    'version': 1, 'name': 'alert-investigator',
    'description': 'Read-only investigator for alert cases',
    'servers': ['prometheus-mcp', 'grafana-mcp', 'pfsense-mcp', 'pyats-mcp'],
    'skills': ['pyats-health-check'],
    'tools': {'allow': ['session_status', 'read', 'prometheus-mcp__*', 'pfsense-mcp__get_*',
                        'pfsense-mcp__list_*', 'pyats-mcp__pyats_list_devices']},
    'model': None,
}


@pytest.fixture(scope='module')
def profiles():
    return load(ROOT / 'scripts/in2n-profiles.py', 'spec183_profiles')


@pytest.fixture(scope='module')
def template():
    servers = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    return {**servers, 'pfsense-mcp': PFSENSE}


def border_with_pfsense(border, env_text):
    servers = install_config(border, env_text)
    servers['pfsense-mcp'] = PFSENSE
    (border / 'openclaw.json').write_text(json.dumps({'mcp': {'servers': servers},
                                                      'tools': {'profile': 'full', 'allow': ['*']}}))
    (border / 'workspace').mkdir(exist_ok=True)
    return servers


def write_spec(path, data=None, **changes):
    spec = copy.deepcopy(EXAMPLE if data is None else data)
    spec.update(changes)
    path.write_text(json.dumps(spec))
    return path


def clean_env(tmp_path):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'HERMES_', 'PYATS_', 'PROMETHEUS_',
                                'GRAFANA_', 'PFSENSE_', 'SERVICENOW_'))}
    env['HOME'] = str(tmp_path)
    return env


def run_member_home(tmp_path, border, member, spec, *extra, cwd=None):
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
         '--risk', 'lab', '--spec', str(spec), '--border-config', str(border / 'openclaw.json'),
         '--anthropic-key-from', str(border / '.env'), '--home', str(member), *extra],
        env=clean_env(tmp_path), capture_output=True, text=True, timeout=60, cwd=cwd)


# ── Format validation ──

def test_example_spec_is_valid(profiles, template):
    spec, warnings = profiles.load_member_spec(copy.deepcopy(EXAMPLE), template,
                                               installed=['pyats-health-check', 'cml-lab'])
    assert warnings == []
    assert spec['name'] == 'alert-investigator' and spec['model'] is None
    assert spec['servers'] == EXAMPLE['servers'] and spec['tools'] == EXAMPLE['tools']
    assert spec['scope'] == ['pyats-health-check']
    assert set(profiles.spec_member_servers(spec, template)) == set(EXAMPLE['servers']) | {'memory-mcp', 'gait-mcp'}


def test_spec_file_path_and_cli(profiles, template, tmp_path):
    border = tmp_path / 'border'
    border.mkdir()
    (border / 'openclaw.json').write_text(json.dumps({'mcp': {'servers': template}}))
    path = write_spec(tmp_path / 'm.json')
    spec, _ = profiles.load_member_spec(path, template)
    assert spec['name'] == 'alert-investigator'
    out = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-profiles.py'), 'spec', str(path),
                          '--border-config', str(border / 'openclaw.json')],
                         env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    printed = json.loads(out.stdout)
    assert printed['kept_servers'] == sorted(set(EXAMPLE['servers']) | {'memory-mcp', 'gait-mcp'})
    assert printed['tool_policy']['allow'] == EXAMPLE['tools']['allow'] + ['memory-mcp__*', 'gait-mcp__*']
    bad = write_spec(tmp_path / 'bad.json', servers=['nope-mcp'])
    out = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-profiles.py'), 'spec', str(bad),
                          '--border-config', str(border / 'openclaw.json')],
                         env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert out.returncode == 1 and 'nope-mcp' in out.stderr and 'Traceback' not in out.stderr


def without(key):
    data = copy.deepcopy(EXAMPLE)
    del data[key]
    return data


def changed(**changes):
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    return data


def allowing(*entries):
    return changed(tools={'allow': list(entries)})


@pytest.mark.parametrize('data,message', [
    ([1, 2], 'must be a JSON object'),
    (changed(extra=1), 'unknown keys: extra'),
    (changed(servers_=[], Tools={}), 'unknown keys: Tools, servers_'),
    (without('version'), 'missing required key: version'),
    (without('name'), 'missing required key: name'),
    (without('servers'), 'missing required key: servers'),
    (without('tools'), 'missing required key: tools'),
    (changed(version=2), 'version must be 1'),
    (changed(version='1'), 'version must be 1'),
    (changed(version=True), 'version must be 1'),
    (changed(name='../x'), 'name must match'),
    (changed(name=''), 'name must match'),
    (changed(name='a' * 65), 'name must match'),
    (changed(name=7), 'name must match'),
    (changed(name='convergence'), "name 'convergence' is reserved"),
    (changed(name='custom'), "name 'custom' is reserved"),
    (changed(description=['x']), 'description must be a string'),
    (changed(servers='pyats-mcp'), 'servers must be a list'),
    (changed(servers=['pyats-mcp', '']), 'servers must be a list'),
    (changed(servers=['pyats-mcp', 'pyats-mcp'], tools={'allow': ['read']}), 'more than once'),
    (changed(servers=['nope-mcp'], tools={'allow': ['read']}),
     "servers not in the Border template's mcp.servers: nope-mcp"),
    (changed(skills='pyats-health-check'), 'skills must be a list'),
    (changed(skills=['../evil']), 'skills must be a list'),
    (changed(skills=['a', 'a']), 'skills lists a skill more than once'),
    (changed(tools=['read']), 'tools must be {"allow": [...]}'),
    (changed(tools={'allow': ['read'], 'deny': []}), 'tools must be {"allow": [...]}'),
    (changed(tools={}), 'tools must be {"allow": [...]}'),
    (changed(tools={'allow': []}), 'tools.allow must be a non-empty list'),
    (changed(tools={'allow': 'read'}), 'tools.allow must be a non-empty list'),
    (allowing('read', 'nonsense_tool'), "'nonsense_tool': not an OpenClaw built-in tool"),
    (allowing('*'), "'*': not an OpenClaw built-in tool"),
    (allowing('group:fs'), "'group:fs': not an OpenClaw built-in tool"),
    (allowing('bundle-mcp'), "'bundle-mcp': not an OpenClaw built-in tool"),
    (allowing('bash'), "'bash': not an OpenClaw built-in tool"),
    (allowing(''), 'must be a non-empty string'),
    (allowing(' read'), 'must be a non-empty string'),
    (allowing(3), 'must be a non-empty string'),
    (allowing('*__get_x'), 'the server part must be a literal server name'),
    (allowing('prom*__get_x'), 'the server part must be a literal server name'),
    (allowing('pyats-mcp__run show'), 'the tool part may use only'),
    (allowing('pyats-mcp__run?'), 'the tool part may use only'),
    (allowing('pyats-mcp__'), 'the tool part may use only'),
    (allowing('READ'), "'READ': not an OpenClaw built-in tool"),
    (allowing('prometheus-mcp__query', 'prometheus-mcp__QUERY'), "'prometheus-mcp__QUERY': listed more than once"),
    (allowing('PROMETHEUS-MCP__query'), "'PROMETHEUS-MCP' is not one of this member's servers"),
    (changed(model='openai/gpt-5'), "provider 'openai' is not configured on the Border"),
    (changed(model=5), 'model must be null or a string'),
    (changed(model=''), 'model must be null, an Anthropic model id'),
])
def test_each_format_error(profiles, template, data, message):
    with pytest.raises(profiles.MemberSpecError) as caught:
        profiles.load_member_spec(data, template)
    assert message in str(caught.value)


def test_every_problem_is_reported_at_once(profiles, template):
    data = changed(version=3, name='convergence', extra=True, tools={'allow': ['*', 'gitlab-mcp__x']})
    with pytest.raises(profiles.MemberSpecError) as caught:
        profiles.load_member_spec(data, template)
    text = str(caught.value)
    for part in ('unknown keys: extra', 'version must be 1', 'reserved', "'*'", 'gitlab-mcp'):
        assert part in text


def test_unreadable_and_invalid_json_files(profiles, template, tmp_path):
    with pytest.raises(profiles.MemberSpecError, match='cannot read'):
        profiles.load_member_spec(tmp_path / 'missing.json', template)
    (tmp_path / 'bad.json').write_text('{not json')
    with pytest.raises(profiles.MemberSpecError, match='not valid JSON'):
        profiles.load_member_spec(tmp_path / 'bad.json', template)


def test_server_openclaw_would_rename_is_refused(profiles, template):
    servers = {**template, 'a.dotted.server': {'command': 'x'}, 'x' * 31: {'command': 'x'}}
    data = changed(servers=['a.dotted.server', 'x' * 31], tools={'allow': ['read']})
    with pytest.raises(profiles.MemberSpecError, match='OpenClaw renames') as caught:
        profiles.load_member_spec(data, servers)
    assert 'a.dotted.server' in str(caught.value) and 'x' * 31 in str(caught.value)


def test_model_accepts_anthropic_ids(profiles, template):
    for model, expected in (('claude-sonnet-5', 'claude-sonnet-5'),
                            ('anthropic/claude-haiku-4-5-20251001', 'claude-haiku-4-5-20251001')):
        spec, _ = profiles.load_member_spec(changed(model=model), template, installed=[])
        assert spec['model'] == expected


def test_skills_not_installed_warn_and_follow_scope_custom(profiles, template):
    data = changed(skills=['pyats-health-check', 'not-installed'])
    spec, warnings = profiles.load_member_spec(data, template, installed=['pyats-health-check'])
    assert warnings == ['skills not installed: not-installed']
    assert spec['scope'] == ['pyats-health-check']           # scope custom keeps the installed ones
    assert spec['skills'] == ['pyats-health-check', 'not-installed']
    spec, warnings = profiles.load_member_spec(changed(skills=['elsewhere']), template, installed=[])
    assert warnings == ['skills not installed: elsewhere']
    assert spec['scope'] == ['elsewhere']                     # ...and all of them when none is
    spec, warnings = profiles.load_member_spec(without('skills'), template, installed=[])
    assert spec['skills'] == [] and spec['scope'] == [] and warnings == []


def test_skills_installed_only_on_the_border_count_as_installed(profiles, template, tmp_path, monkeypatch):
    """A skill an integration installed into the Border's workspace, not the repository, is
    installed: in2n-member-home.py copies it from there, so the routing scope must keep it."""
    repo, border = tmp_path/'repo-skills', tmp_path/'border-skills'
    for root, name in ((repo, 'pyats-health-check'), (border, 'alert-triage')):
        (root/name).mkdir(parents=True)
        (root/name/'SKILL.md').write_text('---\nname: %s\n---\n' % name)
    (border/'no-skill-file').mkdir()
    monkeypatch.setattr(profiles, 'DEFAULT_SKILLS_DIRS', [str(repo), str(border), str(tmp_path/'absent')])
    assert profiles._all_installed_skills() == ['alert-triage', 'pyats-health-check']
    data = changed(skills=['alert-triage', 'pyats-health-check', 'not-installed'])
    spec, warnings = profiles.load_member_spec(data, template)
    assert warnings == ['skills not installed: not-installed']
    assert spec['scope'] == ['alert-triage', 'pyats-health-check']


# ── Allowlist and the kept servers ──

def test_allowlist_naming_a_server_not_kept_is_an_error(profiles, template):
    for entry in ('gitlab-mcp__list_projects', 'netbox-mcp__*', 'slack-mcp__send'):
        with pytest.raises(profiles.MemberSpecError) as caught:
            profiles.load_member_spec(allowing('read', entry), template)
        assert f"{entry.split('__')[0]!r} is not one of this member's servers" in str(caught.value)
    # memory-mcp is always kept, so its tools may be allowed without listing it.
    spec, _ = profiles.load_member_spec(allowing('memory-mcp__*'), template, installed=[])
    assert 'memory-mcp__*' in spec['tools']['allow']
    # ...but not when the Border has no memory-mcp to keep.
    servers = {k: v for k, v in template.items() if k != 'memory-mcp'}
    with pytest.raises(profiles.MemberSpecError, match="'memory-mcp' is not one of"):
        profiles.load_member_spec(allowing('memory-mcp__*'), servers)


def test_tool_policy(profiles, template):
    spec, _ = profiles.load_member_spec(copy.deepcopy(EXAMPLE), template, installed=[])
    assert profiles.spec_tool_policy(spec) == {
        'allow': EXAMPLE['tools']['allow'] + ['memory-mcp__*', 'gait-mcp__*'], 'fs': {'workspaceOnly': True},
        'elevated': {'enabled': False}, 'toolSearch': False}
    # Skills are loaded by reading SKILL.md: `read` is added only when skills are listed.
    spec, _ = profiles.load_member_spec(allowing('prometheus-mcp__*'), template, installed=[])
    assert profiles.spec_tool_policy(spec)['allow'] == ['prometheus-mcp__*', 'read', 'memory-mcp__*', 'gait-mcp__*']
    spec, _ = profiles.load_member_spec(changed(skills=[], tools={'allow': ['prometheus-mcp__*']}),
                                        template, installed=[])
    assert profiles.spec_tool_policy(spec)['allow'] == ['prometheus-mcp__*', 'read', 'memory-mcp__*', 'gait-mcp__*']


def openclaw_dist():
    """The installed OpenClaw's dist directory: NETCLAW_TEST_OPENCLAW_DIST, else npm's global root."""
    if os.environ.get('NETCLAW_TEST_OPENCLAW_DIST'):
        return Path(os.environ['NETCLAW_TEST_OPENCLAW_DIST'])
    node = shutil.which('node')
    npm = shutil.which('npm')
    if not node or not npm:
        return None
    root = subprocess.run([npm, 'root', '-g'], capture_output=True, text=True, timeout=30).stdout.strip()
    dist = Path(root) / 'openclaw/dist'
    return dist if dist.is_dir() else None


def test_matches_installed_openclaw(profiles):
    """When OpenClaw is installed: the vendored built-in names are its core tool ids,
    and its own allowlist matcher reads the spec's patterns as intended."""
    dist = openclaw_dist()
    catalogs = sorted(dist.glob('tool-catalog-*.mjs')) if dist else []
    globs = sorted(dist.glob('glob-pattern-*.mjs')) if dist else []
    names = sorted(dist.glob('agent-bundle-mcp-names-*.mjs')) if dist else []
    if not (catalogs and globs and names):
        pytest.skip('OpenClaw is not installed globally')
    script = """
const [catalog, glob, names, allow] = process.argv.slice(1);
const c = await import(catalog), g = await import(glob), n = await import(names);
const known = JSON.parse(process.argv[5]).filter((id) => !c.i(id));
const patterns = g.t({raw: JSON.parse(allow), normalize: (s) => s.toLowerCase()});
const probe = ["pfsense-mcp__get_rules", "pfsense-mcp__list_aliases", "pfsense-mcp__set_rule",
  "prometheus-mcp__query", "grafana-mcp__search", "pyats-mcp__pyats_list_devices",
  "pyats-mcp__pyats_configure_device", "read", "exec"];
const used = new Set();
const tool = n.n({serverName: n.o("pfsense-mcp", used), toolName: "get_rules", reservedNames: new Set()});
console.log(JSON.stringify({unknown: known, tool,
  allowed: probe.filter((name) => g.n(name.toLowerCase(), patterns))}));
"""
    result = subprocess.run(['node', '--input-type=module', '-e', script, str(catalogs[0]), str(globs[0]),
                             str(names[0]), json.dumps(EXAMPLE['tools']['allow'] + ['memory-mcp__*', 'gait-mcp__*']),
                             json.dumps(sorted(profiles.OPENCLAW_BUILTIN_TOOLS))],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out['unknown'] == []
    assert out['tool'] == 'pfsense-mcp__get_rules'
    assert out['allowed'] == ['pfsense-mcp__get_rules', 'pfsense-mcp__list_aliases', 'prometheus-mcp__query',
                              'pyats-mcp__pyats_list_devices', 'read']


# ── Env slice ──

def kept_names(profiles, kept):
    """What a member's kept servers may contribute: ${NAME} references and, for
    component-launched servers, their component's env keys; never a denied name."""
    names = set().union(*(profiles.server_env_refs(e) | profiles.component_env_keys(e) for e in kept.values()))
    return {n for n in names if profiles.derived_ref_allowed(n)}


PYATS_SETTINGS = {'PYATS_TESTBED_PATH', 'NETCLAW_USERNAME', 'NETCLAW_PASSWORD',
                  'NETCLAW_ENABLE_PASSWORD', 'NETCLAW_TESTBED_MODE', 'PYATS_MCP_SCRIPT'}


def test_env_slice_is_kept_server_refs_and_component_settings(profiles, installed_spec_border):
    border, servers = installed_spec_border
    spec, _ = profiles.load_member_spec(copy.deepcopy(EXAMPLE), servers, installed=[])
    allowed = kept_names(profiles, profiles.spec_member_servers(spec, servers))
    assert {'PFSENSE_URL', 'PFSENSE_API_KEY'} | PYATS_SETTINGS <= allowed
    env_keys = T182.every_ref(profiles, servers) | PYATS_SETTINGS | {
        'PYATS_UNREFERENCED', 'NETBOX_TOKEN', 'SLACK_BOT_TOKEN', 'SERVICENOW_PASSWORD',
        'GAIT_DIR', 'MEMPALACE_X', 'MCP_CALL', 'UNRELATED_SECRET', 'PCAP_UPLOAD_DIR',
        'MEMORY_DATA_DIR', 'GAIT_MCP_STICKY_FILE', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'}
    keys = set(profiles.spec_env_slice_keys(spec, env_keys, servers))
    base = {k for k in env_keys if k.startswith(tuple(profiles.BASE_MEMBER_ENV_PREFIXES))}
    assert keys == ((allowed & env_keys) | base | {'ANTHROPIC_API_KEY'}) - profiles.SPEC_MEMBER_STORE_KEYS
    # Round 2: the Border's memory/GAIT store locations never reach a spec member; its
    # own provider key does (openclaw.json references ${ANTHROPIC_API_KEY}); no other.
    assert not keys & {'MEMORY_DATA_DIR', 'GAIT_DIR', 'GAIT_MCP_STICKY_FILE', 'OPENAI_API_KEY'}
    # The pyats component's settings reach a spec member keeping pyats-mcp.
    assert PYATS_SETTINGS <= keys
    # No profile prefixes: PYATS_ does not pull a key the component does not declare.
    assert 'PYATS_UNREFERENCED' not in keys and 'NETBOX_TOKEN' not in keys
    # A server the spec does not keep contributes nothing (packet-buddy's PCAP_UPLOAD_DIR).
    assert 'PCAP_UPLOAD_DIR' not in keys
    assert not [k for k in keys if k.startswith(T182.SHARED)]


def test_component_env_keys_sources(profiles, template):
    keys = profiles.component_env_keys(template['pyats-mcp'])
    assert PYATS_SETTINGS <= keys                                    # catalog settings + required_env
    assert profiles.launched_component(template['pyats-mcp']) == 'pyats'
    assert profiles.component_env_keys(template['prometheus-mcp']) == set()   # not component-launched
    assert profiles.component_env_keys({'args': ['component-launch.py', 'no-such-component']}) == set()
    contract = json.loads((ROOT / 'config/installer-access.json').read_text())['components']
    catalog = {c['id'] for c in json.loads((ROOT / 'config/components/catalog.json').read_text())['components']}
    assert set(contract) <= catalog
    for component, rule in contract.items():
        assert (component not in profiles.COMPONENT_ENV_KEYS if component in profiles.BORDER_ONLY_COMPONENTS
                else set(rule.get('required_env') or []) <= profiles.COMPONENT_ENV_KEYS[component])


def test_denied_component_settings_never_appear(profiles, template, tmp_path):
    """A component's denied settings (ServiceNow, comms) never reach a slice."""
    servicenow = profiles.component_env_keys(template['servicenow-mcp'])
    assert {'SERVICENOW_INSTANCE_URL', 'SERVICENOW_PASSWORD'} <= servicenow
    spec, _ = profiles.load_member_spec(changed(servers=['servicenow-mcp'], skills=[],
                                                tools={'allow': ['servicenow-mcp__*']}), template, installed=[])
    env_keys = servicenow | {'SLACK_BOT_TOKEN', 'EMAIL_PASSWORD', 'MEMORY_DATA_DIR', 'MEMPALACE_X'}
    assert profiles.spec_env_slice_keys(spec, env_keys, template) == ['MEMPALACE_X']
    # Even if a catalog declared a comms secret as a component setting, the deny lists hold.
    patched = load(ROOT / 'scripts/in2n-profiles.py', 'spec183_patched')
    patched.COMPONENT_ENV_KEYS = {**patched.COMPONENT_ENV_KEYS, 'pyats': frozenset(
        patched.COMPONENT_ENV_KEYS['pyats'] | {'SLACK_BOT_TOKEN', 'EMAIL_PASSWORD', 'TWILIO_AUTH_TOKEN'})}
    keys = set(patched.env_slice_keys('pyats', {'SLACK_BOT_TOKEN', 'EMAIL_PASSWORD', 'TWILIO_AUTH_TOKEN',
                                                'NETCLAW_PASSWORD'}, template))
    assert keys == {'NETCLAW_PASSWORD'}


@pytest.mark.parametrize('profile,keys', [
    ('pyats', {'NETCLAW_USERNAME', 'NETCLAW_PASSWORD', 'NETCLAW_ENABLE_PASSWORD', 'NETCLAW_TESTBED_MODE'}),
    ('packet', {'PCAP_UPLOAD_DIR'}),
    ('netbox', {'PYATS_TESTBED_PATH'}),
])
def test_profile_members_get_component_settings(profiles, template, profile, keys):
    """Spec 183's profile slices had the same gap: these settings match no profile prefix."""
    env_keys = keys | {'SLACK_BOT_TOKEN', 'UNRELATED_SECRET'}
    assert set(profiles.env_slice_keys(profile, env_keys, template)) == keys


@pytest.fixture(scope='module')
def installed_spec_border(tmp_path_factory):
    border = tmp_path_factory.mktemp('installed183') / '.openclaw'
    return border, border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')


# ── Member home ──

def test_member_home_from_spec(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\nSLACK_BOT_TOKEN=must-not-reach-member\n')
    member = tmp_path / 'member'
    private_file(member / '.env', 'PFSENSE_URL=https://fw\n')
    spec = write_spec(tmp_path / 'investigator.json', model='claude-sonnet-5')
    result = run_member_home(tmp_path, border, member, spec)
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())
    assert set(written['mcp']['servers']) == set(EXAMPLE['servers']) | {'memory-mcp', 'gait-mcp'}
    assert written['tools'] == {'allow': EXAMPLE['tools']['allow'] + ['memory-mcp__*', 'gait-mcp__*'], 'fs': {'workspaceOnly': True},
                                'elevated': {'enabled': False}, 'toolSearch': False,
                                'sandbox': {'tools': {'allow': EXAMPLE['tools']['allow'] + ['memory-mcp__*', 'gait-mcp__*']}}}
    assert written['channels'] == {}
    # The member's agents load only the spec's skills (no Border roster: entries.main).
    assert written['agents']['entries'] == {'main': {'skills': ['pyats-health-check', *BASE_SKILLS], 'workspace': str(member / 'workspace')}}
    assert written['agents']['defaults']['skills'] == ['pyats-health-check', *BASE_SKILLS]
    assert written['models']['providers']['anthropic']['models'][0]['id'] == 'claude-sonnet-5'
    assert 'anthropic/claude-sonnet-5' in written['agents']['defaults']['models']
    text = json.dumps(written['mcp']['servers'])
    assert str((border / '.env').resolve()) not in text
    assert str((border / 'python-runtimes').resolve()) not in text
    assert written['mcp']['servers']['pyats-mcp']['env']['NETCLAW_RUNTIME_ENV'] == str(member / '.env')
    assert 'tools.allow:' in result.stdout


def test_member_name_defaults_to_and_must_match_spec(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    spec = write_spec(tmp_path / 's.json', servers=['prometheus-mcp'],
                      tools={'allow': ['prometheus-mcp__*']}, skills=[])
    result = run_member_home(tmp_path, border, tmp_path / 'm1', spec, '--member', 'other')
    assert result.returncode != 0 and "does not match the spec's name" in result.stderr
    assert not (tmp_path / 'm1').exists()
    result = run_member_home(tmp_path, border, tmp_path / 'm2', spec, '--member', 'alert-investigator')
    assert result.returncode == 0, result.stderr
    # Without --home the member home is ~/.openclaw-<risk>-<spec name>.
    env = clean_env(tmp_path)
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
                             '--risk', 'lab', '--spec', str(spec), '--border-config', str(border / 'openclaw.json'),
                             '--anthropic-key-from', str(border / '.env')],
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    written = json.loads((tmp_path / '.openclaw-lab-alert-investigator/openclaw.json').read_text())
    assert set(written['mcp']['servers']) == {'prometheus-mcp', 'memory-mcp', 'gait-mcp'}
    assert written['tools']['allow'] == ['prometheus-mcp__*', 'read', 'memory-mcp__*', 'gait-mcp__*']


def test_invalid_spec_writes_nothing(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    spec = write_spec(tmp_path / 's.json', tools={'allow': ['gitlab-mcp__x']})
    result = run_member_home(tmp_path, border, tmp_path / 'm', spec)
    assert result.returncode != 0 and "'gitlab-mcp' is not one of this member's servers" in result.stderr
    assert 'Traceback' not in result.stderr and not (tmp_path / 'm').exists()


def test_member_requires_member_or_spec(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--risk', 'lab'],
                            env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert result.returncode != 0 and '--member or --spec is required' in result.stderr


# ── Spec 183 protections hold for a spec member ──

def test_spec_member_refuses_missing_and_border_env(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\nSLACK_BOT_TOKEN=must-not-reach-member\n')
    before = (border / 'openclaw.json').read_text()
    member = tmp_path / 'member'
    spec = write_spec(tmp_path / 's.json')
    result = run_member_home(tmp_path, border, member, spec)          # no <home>/.env
    assert result.returncode != 0
    assert 'pyats-mcp' in result.stderr and '--member-env' in result.stderr and 'Traceback' not in result.stderr
    hardlink = tmp_path / 'hard.env'
    os.link(border / '.env', hardlink)
    for target in (border / '.env', tmp_path / 'member/../.openclaw/.env', hardlink):
        result = run_member_home(tmp_path, border, member, spec, '--member-env', str(target))
        assert result.returncode != 0 and "the Border's .env" in result.stderr, target
    link = tmp_path / 'link.env'
    link.symlink_to(private_file(tmp_path / 'real.env'))
    result = run_member_home(tmp_path, border, member, spec, '--member-env', str(link))
    assert result.returncode != 0 and 'not a regular file' in result.stderr
    assert not (member / 'openclaw.json').exists()
    for home in (border, tmp_path / 'x/../.openclaw'):
        result = run_member_home(tmp_path, border, home, spec, '--member-env', str(tmp_path / 'real.env'))
        assert result.returncode != 0 and "is the Border's home" in result.stderr
    assert (border / 'openclaw.json').read_text() == before


def test_spec_member_runtime_paths_and_records(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    staged = private_file(tmp_path / 'stage/members/net/.env', 'NETBOX_URL=https://nb\n')
    spec = write_spec(tmp_path / 'net.json', name='net', servers=['netbox-mcp', 'pyats-mcp'], skills=[],
                      tools={'allow': ['netbox-mcp__get_*', 'pyats-mcp__pyats_list_devices']})
    member = tmp_path / 'member-net'
    result = run_member_home(tmp_path, border, member, spec, '--member-env', str(staged))
    assert result.returncode == 0, result.stderr
    servers = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']
    for name in ('netbox-mcp', 'pyats-mcp'):
        assert servers[name]['env']['NETCLAW_RUNTIME_ENV'] == str(staged)
        assert servers[name]['env']['NETCLAW_RUNTIME_ROOT'] == str(member / 'python-runtimes')
    assert servers['pyats-mcp']['env']['PYATS_VENV'] == str((border / 'pyats-venv').resolve())
    record = member / 'python-runtimes/records/netbox'
    assert record.read_text().strip() == sys.executable and record.stat().st_mode & 0o777 == 0o600


def test_hermes_runtime_refuses_spec(tmp_path):
    spec = write_spec(tmp_path / 's.json')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'hermes',
                             '--risk', 'lab', '--spec', str(spec)],
                            env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert result.returncode != 0 and 'Hermes qualifies only the subnet member' in result.stderr


# ── Staging (in2n-migrate.py --spec) ──

def run_migrate(tmp_path, *extra, staging='stage'):
    env = clean_env(tmp_path)
    return subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-migrate.py'), '--risk', 'lab',
                           '--staging', str(tmp_path / staging), *extra],
                          env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize('staging', ['stage', 'st age$x'])
def test_migrate_stages_spec_member_and_command_works(tmp_path, staging):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n'
                                'PYATS_TESTBED_PATH=/fixture\nPYATS_UNREFERENCED=x\nNETBOX_TOKEN=no\n'
                                'SLACK_BOT_TOKEN=must-not-copy\nSERVICENOW_PASSWORD=must-not-copy\n'
                                'MEMORY_DATA_DIR=/fixture\nGAIT_DIR=/fixture\n')
    (tmp_path / 'spec dir').mkdir()
    spec = write_spec(tmp_path / 'spec dir/investigator.json', model='claude-sonnet-5')
    result = run_migrate(tmp_path, '--spec', str(spec), '--specs-only', '--hot', 'alert-investigator',
                         staging=staging)
    assert result.returncode == 0, result.stderr
    members = tmp_path / staging / 'members'
    assert sorted(p.name for p in members.iterdir()) == ['alert-investigator']
    envfile = members / 'alert-investigator/.env'
    assert envfile.stat().st_mode & 0o777 == 0o600
    keys = slice_keys(envfile)
    assert {'PFSENSE_URL', 'PFSENSE_API_KEY', 'ANTHROPIC_API_KEY'} <= keys
    assert not {'PYATS_UNREFERENCED', 'NETBOX_TOKEN', 'SLACK_BOT_TOKEN', 'SERVICENOW_PASSWORD',
                'MEMORY_DATA_DIR', 'GAIT_DIR'} & keys
    # pyats-mcp (component-launched) gets its component's settings, not by profile prefix.
    assert 'PYATS_TESTBED_PATH' in keys
    text = envfile.read_text()
    assert 'N2N_MEMBER_MODEL=anthropic/claude-sonnet-5' in text
    scope = json.loads(re.search(r'^N2N_MEMBER_SCOPE=(.*)$', text, re.M).group(1))
    assert scope[-1] == 'pyats-health-check'
    # The printed command names the spec and the staged slice; it is in the runbook and works.
    command = next(l.strip() for l in result.stdout.splitlines() if 'in2n-member-home.py' in l)
    argv = shlex.split(command)
    assert argv[argv.index('--spec') + 1] == str(spec)
    assert argv[-2:] == ['--member-env', str(envfile)]
    runbook = (tmp_path / staging / 'RUNBOOK.md').read_text()
    assert command in runbook
    body = json.loads(re.search(r"-d '(\{\"name\":\"alert-investigator\".*?\})'", runbook).group(1))
    assert body['profile'] == 'custom' and body['specialty'] == ['pyats-health-check']
    assert body['on_demand'] is False
    run = subprocess.run([sys.executable, *argv[1:]], env=clean_env(tmp_path),
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    written = json.loads((tmp_path / '.openclaw-lab-alert-investigator/openclaw.json').read_text())
    assert set(written['mcp']['servers']) == set(EXAMPLE['servers']) | {'memory-mcp', 'gait-mcp'}
    assert written['mcp']['servers']['pyats-mcp']['env']['NETCLAW_RUNTIME_ENV'] == str(envfile)
    assert written['tools']['allow'] == EXAMPLE['tools']['allow'] + ['memory-mcp__*', 'gait-mcp__*']


def test_null_model_stages_the_model_the_member_home_configures(tmp_path):
    """model null: the staged N2N_MEMBER_MODEL (passed as --model) is the member tier that
    in2n-member-home.py configures and allows, not a placeholder the agent would reject."""
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    spec = write_spec(tmp_path / 'investigator.json', model=None)
    result = run_migrate(tmp_path, '--spec', str(spec), '--specs-only', '--hot', '')
    assert result.returncode == 0, result.stderr
    envfile = tmp_path / 'stage/members/alert-investigator/.env'
    staged = re.search(r'^N2N_MEMBER_MODEL=(\S+)\s*$', envfile.read_text(), re.M).group(1)
    command = next(l.strip() for l in result.stdout.splitlines() if 'in2n-member-home.py' in l)
    run = subprocess.run([sys.executable, *shlex.split(command)[1:]], env=clean_env(tmp_path),
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    written = json.loads((tmp_path / '.openclaw-lab-alert-investigator/openclaw.json').read_text())
    assert written['agents']['defaults']['model']['primary'] == staged
    assert staged in written['agents']['defaults']['models']


def test_migrate_refuses_invalid_or_duplicate_spec(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    bad = write_spec(tmp_path / 'bad.json', servers=['nope-mcp'])
    result = run_migrate(tmp_path, '--spec', str(bad), '--specs-only')
    assert result.returncode != 0 and 'nope-mcp' in result.stderr and 'Traceback' not in result.stderr
    assert not (tmp_path / 'stage/members').exists()
    good = write_spec(tmp_path / 'good.json')
    result = run_migrate(tmp_path, '--spec', str(good), '--spec', str(good), '--specs-only')
    assert result.returncode != 0 and 'already staged' in result.stderr
    result = run_migrate(tmp_path, '--specs-only')
    assert result.returncode != 0 and '--specs-only needs at least one --spec' in result.stderr


def test_migrate_hermes_runtime_refuses_spec(tmp_path):
    spec = write_spec(tmp_path / 's.json')
    env = clean_env(tmp_path)
    env.update(NETCLAW_RUNTIME='hermes', HERMES_HOME=str(tmp_path / '.hermes'))
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-migrate.py'), '--risk', 'lab',
                             '--staging', str(tmp_path / 'stage'), '--spec', str(spec)],
                            env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode != 0 and 'Hermes qualifies only the subnet member' in result.stderr
    assert not (tmp_path / 'stage').exists()


def test_migrate_spec_name_colliding_with_profile_member(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\nPYATS_MCP_SCRIPT=/fixture\n')
    spec = write_spec(tmp_path / 'p.json', name='pyats')
    result = run_migrate(tmp_path, '--spec', str(spec))
    assert result.returncode != 0 and "name 'pyats' is a member profile id" in result.stderr


# ── netclaw risk add spec ──

def extract_functions(*names):
    text = (ROOT / 'scripts/netclaw').read_text()
    out = []
    for name in names:
        match = re.search(r'^' + name + r'\(\) \{.*?^\}\n', text, re.M | re.S)
        assert match, name
        out.append(match.group(0))
    return '\n'.join(out)


def test_netclaw_risk_add_spec(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    spec = write_spec(tmp_path / 'investigator.json')
    posted = tmp_path / 'posted.json'
    script = extract_functions('risk_add', 'risk_add_spec') + f'''
api_post() {{ printf '%s' "$2" > {shlex.quote(str(posted))}; echo '{{"member_id":"lab/alert-investigator","profile":"custom","enrollment_token":"tok-1","join":{{"N2N_RISK_NAME":"lab","N2N_BORDER_ENDPOINT":"border.example:11790"}}}}'; }}
NETCLAW_ROOT={shlex.quote(str(ROOT))}
cd {shlex.quote(str(tmp_path))} && risk_add spec investigator.json
'''
    result = subprocess.run(['bash', '-c', script], env=clean_env(tmp_path), capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(posted.read_text()) == {'name': 'alert-investigator', 'profile': 'custom',
                                              'specialty': ['pyats-health-check']}
    assert 'enrollment token: tok-1' in result.stdout
    assert f'--spec {spec}' in result.stdout and '--specs-only' in result.stdout
    staged = shlex.split(next(line.strip() for line in result.stdout.splitlines() if 'in2n-migrate.py --risk' in line))
    assert staged[staged.index('--staging') + 1] == str(ROOT / 'migration-staging/lab')
    assert staged[staged.index('--border-endpoint') + 1] == 'border.example:11790'
    assert staged[staged.index('--hot') + 1] == ''
    # An invalid spec is refused before the daemon is called.
    posted.unlink()
    write_spec(spec, tools={'allow': ['*']})
    result = subprocess.run(['bash', '-c', script], env=clean_env(tmp_path), capture_output=True,
                            text=True, timeout=60)
    assert result.returncode != 0 and "'*'" in result.stderr and not posted.exists()


# ── Skills: OpenClaw's per-agent skill allowlist ──

@pytest.fixture(scope='module')
def member_home():
    return load(ROOT / 'scripts/in2n-member-home.py', 'spec183_member_home')


@pytest.mark.parametrize('agents,expected_entries', [
    (None, {'main': {'skills': ['a', 'b']}}),
    ({'defaults': {'workspace': '/w'}}, {'main': {'skills': ['a', 'b']}}),
    ({'entries': {'main': {'workspace': '/w'}, 'ops': {}}, 'ownership': 'explicit'},
     {'main': {'workspace': '/w', 'skills': ['a', 'b']}, 'ops': {'skills': ['a', 'b']}}),
])
def test_skill_allowlist_on_every_agent(member_home, agents, expected_entries):
    config = {} if agents is None else {'agents': copy.deepcopy(agents)}
    member_home.spec_skill_allowlist(config, ['a', 'b'])
    assert config['agents']['entries'] == expected_entries
    assert config['agents']['defaults']['skills'] == ['a', 'b']
    if agents and 'ownership' in agents:
        assert config['agents']['ownership'] == 'explicit'


def test_skill_allowlist_legacy_list_and_empty(member_home):
    config = {'agents': {'list': [{'id': 'main', 'default': True}, {'id': 'ops'}]}}
    member_home.spec_skill_allowlist(config, [])
    assert config['agents']['list'] == [{'id': 'main', 'default': True, 'skills': []},
                                        {'id': 'ops', 'skills': []}]
    assert 'entries' not in config['agents'] and config['agents']['defaults']['skills'] == []


def test_member_home_with_border_agents_and_no_skills(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    config = json.loads((border / 'openclaw.json').read_text())
    config['agents'] = {'entries': {'main': {}, 'ops': {'skills': ['memory']}}, 'ownership': 'explicit'}
    (border / 'openclaw.json').write_text(json.dumps(config))
    spec = write_spec(tmp_path / 's.json', servers=['prometheus-mcp'], skills=[],
                      tools={'allow': ['prometheus-mcp__*']})
    result = run_member_home(tmp_path, border, tmp_path / 'm', spec)
    assert result.returncode == 0, result.stderr
    agents = json.loads((tmp_path / 'm/openclaw.json').read_text())['agents']
    # Round 2: the member's roster is built, not copied: main only (the Border's ops agent
    # is the Border's), so gateway._member_agent_args passes no --agent.
    assert agents['entries'] == {'main': {'skills': BASE_SKILLS, 'workspace': str(tmp_path / 'm/workspace')}}
    assert agents['defaults']['skills'] == BASE_SKILLS


def test_skill_filter_matches_installed_openclaw(member_home):
    """When OpenClaw is installed: its resolveEffectiveAgentSkillFilter and
    isSessionSkillEnabled admit only the spec's skills for every agent of the home."""
    dist = openclaw_dist()
    filters = sorted(dist.glob('agent-filter-*.mjs')) if dist else []
    if not filters:
        pytest.skip('OpenClaw is not installed globally')
    configs = []
    for agents in (None, {'entries': {'main': {'workspace': '/w'}, 'ops': {'skills': ['memory']}},
                          'ownership': 'explicit', 'defaults': {'skills': ['memory']}}):
        for skills in (['pyats-health-check'], []):
            config = {} if agents is None else {'agents': copy.deepcopy(agents)}
            configs.append((skills, member_home.spec_skill_allowlist(config, skills)))
    script = """
const f = await import(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
const names = ["pyats-health-check", "memory", "subnet-calculator"];
console.log(JSON.stringify(cases.map(([skills, cfg]) => ["main", "ops"].map((agent) => {
  const filter = f.n(cfg, agent);
  return names.filter((name) => f.t(name, filter, undefined));
}))));
"""
    result = subprocess.run(['node', '--input-type=module', '-e', script, str(filters[0]), json.dumps(configs)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    for (skills, _), per_agent in zip(configs, json.loads(result.stdout)):
        assert per_agent == [skills, skills]

# Review regression boundaries: opt-in, control-plane exclusion, own workspace.
@pytest.mark.parametrize('tool', sorted({'write', 'exec', 'edit', 'apply_patch', 'process',
    'gateway', 'secrets', 'openclaw', 'plugins', 'code_execution', 'terminal', 'computer',
    'sessions_spawn', 'subagents', 'skill_workshop', 'message', 'conversations_send'}))
def test_dangerous_builtin_requires_opt_in(profiles, template, tool):
    with pytest.raises(profiles.MemberSpecError, match='allow-dangerous-tools'):
        profiles.load_member_spec(allowing(tool), template)
    spec, warnings = profiles.load_member_spec(allowing(tool), template, allow_dangerous=True)
    assert spec['dangerous_tools'] == [tool]
    assert any('allow-dangerous-tools' in w for w in warnings)

@pytest.mark.parametrize('server', ['n2n-mcp', 'protocol-mcp', 'hermes-hud-mcp',
                                   'netconverter-mcp', 'convergence-read-mcp'])
def test_control_servers_refused(profiles, template, server):
    with pytest.raises(profiles.MemberSpecError, match='Border-only'):
        profiles.load_member_spec(changed(servers=[server], tools={'allow': ['read']}),
                                  {**template, server: {'command': 'fixture'}})


def test_control_component_keys_never_derived(profiles):
    for component in profiles.BORDER_ONLY_COMPONENTS:
        assert component not in profiles.COMPONENT_ENV_KEYS
    entry = {'args': ['component-launch.py', 'protocol'], 'env': {'SECRET': '${BGP_DAEMON_API}'}}
    assert profiles._slice([], {'alias': entry}, {'BGP_DAEMON_API'}) == []


def test_all_profile_names_reserved_even_when_unoffered(profiles, template):
    for name in profiles.reserved_member_names():
        with pytest.raises(profiles.MemberSpecError):
            profiles.load_member_spec(changed(name=name), template)


def test_isolated_workspace_hardened_policy_and_optin_record(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    (border / 'workspace/private-border.txt').write_text('private fixture')
    skill = border / 'workspace/skills/fixture-skill'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('fixture skill')
    (skill / 'leak').symlink_to(border / 'workspace/private-border.txt')
    config = json.loads((border / 'openclaw.json').read_text())
    config['agents'] = {'entries': {'main': {'agentDir': '/border/state',
        'tools': {'alsoAllow': ['exec'], 'profile': 'full', 'allow': ['*']}}}}
    config['tools']['sandbox'] = {'tools': {'alsoAllow': ['bundle-mcp'], 'allow': ['*']}}
    config['skills'] = {'load': {'extraDirs': ['/border/skills']},
                        'workshop': {'autonomous': {'mode': 'auto'}}}
    (border / 'openclaw.json').write_text(json.dumps(config))
    spec = write_spec(tmp_path / 's.json', servers=['prometheus-mcp'],
                      skills=['fixture-skill'], tools={'allow': ['exec']})
    member = tmp_path / 'member'
    denied = run_member_home(tmp_path, border, member, spec)
    assert denied.returncode != 0 and not member.exists()
    result = run_member_home(tmp_path, border, member, spec, '--allow-dangerous-tools')
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())
    ws = member / 'workspace'
    assert not ws.is_symlink() and sorted(p.name for p in ws.iterdir()) == ['skills']
    assert sorted(p.name for p in (ws / 'skills').iterdir()) == sorted(['fixture-skill', *BASE_SKILLS])
    assert not (ws / 'skills/fixture-skill/leak').exists()
    assert (ws / 'skills/fixture-skill/SKILL.md').read_text() == 'fixture skill'
    assert written['tools']['sandbox']['tools'] == {'allow': written['tools']['allow']}
    assert written['skills']['workshop']['autonomous']['mode'] == 'off'
    assert 'load' not in written['skills']
    assert 'tools' not in written['agents']['entries']['main']
    assert 'agentDir' not in written['agents']['entries']['main']
    assert written['agents']['entries']['main']['workspace'] == str(ws)
    record = json.loads((member / 'netclaw-member-spec.json').read_text())
    assert record['allow_dangerous_tools'] and record['dangerous_tools_allowed'] == ['exec']
    assert 'WARNING' in result.stdout and 'allow-dangerous-tools' in result.stderr


# ── Review round 1 (continued): OpenClaw-derived evidence, opt-in plumbing ──

def openclaw_module(dist, pattern, marker):
    """(path, export letter) of the dist module defining `marker` (minified exports)."""
    for path in sorted(dist.glob(pattern)):
        match = re.search(r'\b' + marker + r' as (\w+)\b', path.read_text())
        if match:
            return path, match.group(1)
    return None, None


def test_dangerous_set_covers_installed_openclaw_groups(profiles):
    """When OpenClaw is installed: every tool of its runtime, automation, nodes and
    messaging groups, the fs writers, and every core tool its sandbox denies by
    default are dangerous; and every dangerous name is a core tool id."""
    dist = openclaw_dist()
    catalog, groups = openclaw_module(dist, 'tool-catalog-*.mjs', 'CORE_TOOL_GROUPS') if dist else (None, None)
    constants, deny = openclaw_module(dist, 'constants-*.mjs', 'DEFAULT_TOOL_DENY') if dist else (None, None)
    if not (catalog and constants):
        pytest.skip('OpenClaw is not installed globally')
    script = f"""
const c = await import(process.argv[1]), k = await import(process.argv[2]);
console.log(JSON.stringify({{groups: c.{groups}, deny: k.{deny}}}));
"""
    result = subprocess.run(['node', '--input-type=module', '-e', script, str(catalog), str(constants)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    expected = set().union(*(out['groups'][g] for g in ('group:runtime', 'group:automation',
                                                         'group:nodes', 'group:messaging')))
    expected |= {'write', 'edit', 'apply_patch'}
    expected |= set(out['deny']) & profiles.OPENCLAW_BUILTIN_TOOLS
    assert expected <= profiles.DANGEROUS_BUILTINS
    assert profiles.DANGEROUS_BUILTINS <= profiles.OPENCLAW_BUILTIN_TOOLS


def hardened_border(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    config = json.loads((border / 'openclaw.json').read_text())
    config['tools']['sandbox'] = {'tools': {'alsoAllow': ['bundle-mcp']}}
    config['agents'] = {'defaults': {'sandbox': {'mode': 'all'}},
                        'entries': {'main': {'tools': {'sandbox': {'tools': {'allow': ['*']}}}}}}
    (border / 'openclaw.json').write_text(json.dumps(config))
    return border


def test_sandbox_layer_matches_installed_openclaw(tmp_path):
    """A member built from a hardened (sandboxed, bundle-mcp) Border: OpenClaw's own
    sandbox resolver admits exactly the spec's tools, MCP tools included."""
    dist = openclaw_dist()
    policy, resolve = openclaw_module(dist, 'tool-policy-*.mjs', 'resolveSandboxToolPolicyForAgent') if dist else (None, None)
    _, allowed = openclaw_module(dist, 'tool-policy-*.mjs', 'isToolAllowed') if dist else (None, None)
    if not policy:
        pytest.skip('OpenClaw is not installed globally')
    border = hardened_border(tmp_path)
    spec = write_spec(tmp_path / 's.json')
    member = tmp_path / 'member'
    private_file(member / '.env', 'PFSENSE_URL=https://fw\n')
    result = run_member_home(tmp_path, border, member, spec)
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())
    assert 'tools' not in written['agents']['entries']['main']
    script = f"""
const p = await import(process.argv[1]);
const cfg = JSON.parse(process.argv[2]);
const policy = p.{resolve}(cfg, "main");
const probe = ["pfsense-mcp__get_rules", "pfsense-mcp__set_rule", "prometheus-mcp__query",
  "memory-mcp__memory_recall", "gait-mcp__gait_log", "read", "exec", "write", "sessions_spawn"];
console.log(JSON.stringify(probe.filter((name) => p.{allowed}(policy, name))));
"""
    result = subprocess.run(['node', '--input-type=module', '-e', script, str(policy), json.dumps(written)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ['pfsense-mcp__get_rules', 'prometheus-mcp__query',
                                         'memory-mcp__memory_recall', 'gait-mcp__gait_log', 'read']


def test_profile_member_keeps_shared_workspace(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    member = tmp_path / 'member'
    private_file(member / '.env', 'X=1\n')
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
         '--risk', 'lab', '--member', 'subnet', '--border-config', str(border / 'openclaw.json'),
         '--anthropic-key-from', str(border / '.env'), '--home', str(member)],
        env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert (member / 'workspace').is_symlink()
    assert (member / 'workspace').resolve() == (border / 'workspace').resolve()
    assert not (member / 'netclaw-member-spec.json').exists()


def test_allow_dangerous_tools_needs_spec(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
         '--risk', 'lab', '--member', 'subnet', '--allow-dangerous-tools',
         '--border-config', str(border / 'openclaw.json'), '--home', str(tmp_path / 'm')],
        env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert result.returncode != 0 and 'only with --spec' in result.stderr
    assert not (tmp_path / 'm').exists()


def test_migrate_dangerous_spec_needs_opt_in_and_carries_it(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\nPFSENSE_URL=https://fw\n')
    spec = write_spec(tmp_path / 'investigator.json', tools={'allow': ['read', 'exec']})
    refused = run_migrate(tmp_path, '--spec', str(spec), '--specs-only', '--hot', '')
    assert refused.returncode != 0 and 'allow-dangerous-tools' in refused.stderr
    result = run_migrate(tmp_path, '--spec', str(spec), '--specs-only', '--hot', '',
                         '--allow-dangerous-tools', staging='stage2')
    assert result.returncode == 0, result.stderr
    command = next(l.strip() for l in result.stdout.splitlines() if 'in2n-member-home.py' in l)
    argv = shlex.split(command)
    assert '--allow-dangerous-tools' in argv
    run = subprocess.run([sys.executable, *argv[1:]], env=clean_env(tmp_path),
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    record = json.loads((tmp_path / '.openclaw-lab-alert-investigator/netclaw-member-spec.json').read_text())
    assert record['dangerous_tools_allowed'] == ['exec'] and record['allow_dangerous_tools'] is True
    # A safe spec's command never carries the flag, even when the operator passed it.
    safe = write_spec(tmp_path / 'safe.json', name='safe-investigator')
    result = run_migrate(tmp_path, '--spec', str(safe), '--specs-only', '--hot', '',
                         '--allow-dangerous-tools', staging='stage3')
    assert result.returncode == 0, result.stderr
    assert '--allow-dangerous-tools' not in next(l for l in result.stdout.splitlines()
                                                 if 'in2n-member-home.py' in l)


def risk_add_spec_script(tmp_path, posted, spec_name, endpoint, *extra):
    reply = json.dumps({'member_id': 'lab/alert-investigator', 'profile': 'custom',
                        'enrollment_token': 'tok-1',
                        'join': {'N2N_RISK_NAME': 'lab', 'N2N_BORDER_ENDPOINT': endpoint}})
    return extract_functions('risk_add', 'risk_add_spec') + f'''
api_post() {{ printf '%s' "$2" > {shlex.quote(str(posted))}; echo {shlex.quote(reply)}; }}
NETCLAW_ROOT={shlex.quote(str(ROOT))}
cd {shlex.quote(str(tmp_path))} && risk_add spec {spec_name} {' '.join(extra)}
'''


def test_netclaw_risk_add_spec_placeholder_endpoint_and_opt_in(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    write_spec(tmp_path / 'investigator.json', tools={'allow': ['read', 'exec']})
    posted = tmp_path / 'posted.json'
    script = risk_add_spec_script(tmp_path, posted, 'investigator.json', '<border-host:port>')
    result = subprocess.run(['bash', '-c', script], env=clean_env(tmp_path), capture_output=True,
                            text=True, timeout=60)
    assert result.returncode != 0 and 'allow-dangerous-tools' in result.stderr and not posted.exists()
    script = risk_add_spec_script(tmp_path, posted, 'investigator.json', '<border-host:port>',
                                  '--allow-dangerous-tools')
    result = subprocess.run(['bash', '-c', script], env=clean_env(tmp_path), capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    staged = shlex.split(next(line.strip() for line in result.stdout.splitlines() if 'in2n-migrate.py --risk' in line))
    assert staged[staged.index('--border-endpoint') + 1] == '127.0.0.1:11790'
    assert staged[staged.index('--hot') + 1] == ''
    assert '--allow-dangerous-tools' in staged
    script = risk_add_spec_script(tmp_path, posted, 'investigator.json', 'x', '--bogus')
    result = subprocess.run(['bash', '-c', script], env=clean_env(tmp_path), capture_output=True,
                            text=True, timeout=60)
    assert result.returncode != 0 and 'usage:' in result.stdout


def test_profile_member_slice_never_gets_border_only_settings(profiles):
    """Profile members too: a kept Border-only server contributes nothing to a slice."""
    keys = {'BGP_DAEMON_API', 'NETCLAW_BGP_PEERS', 'N2N_REGISTRY_TOKEN',
            'NETCLAW_HERMES_HUD_API_KEY', 'NETCONVERTER_API_KEY', 'GAIT_DIR'}
    servers = {name: {'command': 'x', 'env': {k: '${' + k + '}' for k in keys}}
               for name in profiles.BORDER_ONLY_SERVERS}
    for profile in profiles.PROFILE_MATCHERS:
        if profile == 'convergence':
            continue
        assert profiles.env_slice_keys(profile, keys, servers) == ['GAIT_DIR']


def test_member_home_validates_with_installed_openclaw(tmp_path):
    """When OpenClaw is installed: `openclaw config validate` accepts a spec member's
    home built from a hardened Border (agents.entries.main, per-agent skills and
    workspace, narrowed tools.sandbox, skills.workshop.autonomous.mode off), and
    rejects the same home with an invalid workshop mode (the check is not vacuous)."""
    dist = openclaw_dist()
    cli = dist.parent / 'openclaw.mjs' if dist else None
    node = shutil.which('node')
    if not (cli and cli.is_file() and node):
        pytest.skip('OpenClaw is not installed globally')
    border = hardened_border(tmp_path)
    config = json.loads((border / 'openclaw.json').read_text())
    config['skills'] = {'workshop': {'autonomous': {'mode': 'auto'}}}
    (border / 'openclaw.json').write_text(json.dumps(config))
    member = tmp_path / 'member'
    private_file(member / '.env', 'PFSENSE_URL=https://fw\n')
    result = run_member_home(tmp_path, border, member, write_spec(tmp_path / 's.json'))
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())
    assert written['skills']['workshop']['autonomous']['mode'] == 'off'
    bad = copy.deepcopy(written)
    bad['skills']['workshop']['autonomous']['mode'] = 'bogus'
    (tmp_path / 'bad.json').write_text(json.dumps(bad))

    def validate(path):
        env = {'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'HOME': str(tmp_path),
               'OPENCLAW_STATE_DIR': str(member), 'OPENCLAW_CONFIG_PATH': str(path)}
        return subprocess.run([node, str(cli), 'config', 'validate'], env=env, cwd=tmp_path,
                              capture_output=True, text=True, timeout=180)
    good = validate(member / 'openclaw.json')
    assert good.returncode == 0, good.stdout + good.stderr
    assert validate(tmp_path / 'bad.json').returncode != 0


# ── Review round 2: the spec member's config is built, not copied ──

BORDER_SECRETS = ('gw-token-literal', 'gw-password-literal', 'hooks-token-literal', 'cron-webhook-literal',
                  'env-vars-foo-literal', 'openai-key-literal', 'memory-remote-key-literal',
                  'legacy-memorysearch-key-literal', '/border/extra-memory', '/border/secret-bind',
                  'docker-env-literal', 'other-plugin-secret', '/border/plugins/other',
                  'skill-entry-key-literal', 'ssh-identity-literal', '/border/sandbox-root',
                  'anthropic-literal-in-border-config')


def leaky_border(tmp_path):
    border = tmp_path / '.openclaw'
    border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture-border-env-key\n')
    config = json.loads((border / 'openclaw.json').read_text())
    config.update(
        gateway={'mode': 'local', 'auth': {'mode': 'token', 'token': 'gw-token-literal',
                                           'password': 'gw-password-literal'}},
        hooks={'enabled': True, 'token': 'hooks-token-literal', 'mappings': [{'match': {'path': 'x'}}]},
        cron={'enabled': True, 'webhookToken': 'cron-webhook-literal'},
        env={'vars': {'FOO': 'env-vars-foo-literal'}},
        models={'providers': {'openai': {'apiKey': 'openai-key-literal', 'models': []},
                              'anthropic': {'apiKey': 'anthropic-literal-in-border-config'}}},
        memory={'search': {'remote': {'apiKey': 'memory-remote-key-literal'},
                           'extraPaths': ['/border/extra-memory']}},
        plugins={'entries': {'other': {'enabled': True, 'config': {'token': 'other-plugin-secret'}}},
                 'load': {'paths': ['/border/plugins/other']}},
        skills={'entries': {'pyats-health-check': {'enabled': True, 'apiKey': 'skill-entry-key-literal'}}},
        agents={'defaults': {
            'memorySearch': {'remote': {'apiKey': 'legacy-memorysearch-key-literal'}},
            'sandbox': {'mode': 'all', 'workspaceRoot': '/border/sandbox-root', 'scope': 'agent',
                        'docker': {'image': 'sandbox-img', 'network': 'none',
                                   'binds': ['/border/secret-bind:/x:ro'],
                                   'env': {'TOKEN': 'docker-env-literal'}},
                        'ssh': {'identityData': 'ssh-identity-literal'}}}},
    )
    (border / 'openclaw.json').write_text(json.dumps(config))
    return border


def test_spec_member_config_carries_no_border_section(tmp_path, member_home):
    border = leaky_border(tmp_path)
    member = tmp_path / 'member'
    private_file(member / '.env', 'PFSENSE_URL=https://fw\nANTHROPIC_API_KEY=member-key\n')
    result = run_member_home(tmp_path, border, member, write_spec(tmp_path / 's.json'))
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())
    text = json.dumps(written)
    for secret in BORDER_SECRETS + ('fixture-border-env-key', 'member-key'):
        assert secret not in text, secret
    assert set(written) <= set(member_home.SPEC_MEMBER_TOP_KEYS)
    assert not {'gateway', 'env', 'auth', 'secrets'} & set(written)
    assert written['hooks'] == {'enabled': False} and written['cron'] == {'enabled': False}
    assert written['memory'] == {'search': {'enabled': False}}
    assert 'memorySearch' not in written['agents']['defaults']
    assert list(written['models']['providers']) == ['anthropic']
    assert written['models']['providers']['anthropic']['apiKey'] == '${ANTHROPIC_API_KEY}'
    assert written['agents']['defaults']['sandbox'] == {
        'mode': 'all', 'scope': 'agent', 'docker': {'image': 'sandbox-img', 'network': 'none'}}
    assert 'plugins' not in written          # no DefenseClaw guard in this Border; nothing else
    assert written['skills'] == {'workshop': {'autonomous': {'mode': 'off'}},
                                 'entries': {'pyats-health-check': {'enabled': True}}}
    assert list(written['agents']['entries']) == ['main']
    assert 'apiKey ${ANTHROPIC_API_KEY}: present' in result.stdout


def test_spec_member_config_keeps_only_the_guard_plugin(member_home, profiles, template, monkeypatch):
    import bgp.federation.controls as controls
    guard = {'entries': {'defenseclaw': {'enabled': True}}, 'load': {'paths': ['/ext/defenseclaw']},
             'allow': ['defenseclaw']}
    seen = []
    monkeypatch.setattr(controls, 'defenseclaw_plugin_config', lambda cfg: seen.append(cfg) or guard)
    spec, _ = profiles.load_member_spec(copy.deepcopy(EXAMPLE), template, installed=[])
    border = {'plugins': {'entries': {'defenseclaw': {'enabled': True}, 'other': {'enabled': True}},
                          'load': {'paths': ['/ext/defenseclaw', '/ext/other']}}}
    config = member_home.spec_member_config(border, {}, spec, profiles, '/m', 'claude-sonnet-5')
    assert config['plugins'] == guard and seen == [border]


def test_sandbox_ssh_backend_is_refused(member_home):
    with pytest.raises(ValueError, match='ssh'):
        member_home.spec_sandbox({'defaults': {'sandbox': {'mode': 'all', 'backend': 'ssh'}}})
    assert member_home.spec_sandbox({}) is None
    merged = member_home.spec_sandbox({'defaults': {'sandbox': {'mode': 'non-main', 'docker': {'image': 'a'}}},
                                       'entries': {'main': {'sandbox': {'mode': 'all',
                                                                        'docker': {'binds': ['/x:/x']}}}}})
    assert merged == {'mode': 'all', 'docker': {'image': 'a'}}


def test_spec_member_config_validates_with_installed_openclaw(tmp_path):
    dist = openclaw_dist()
    cli = dist.parent / 'openclaw.mjs' if dist else None
    node = shutil.which('node')
    if not (cli and cli.is_file() and node):
        pytest.skip('OpenClaw is not installed globally')
    border = leaky_border(tmp_path)
    member = tmp_path / 'member'
    private_file(member / '.env', 'PFSENSE_URL=https://fw\nANTHROPIC_API_KEY=member-key\n')
    assert run_member_home(tmp_path, border, member, write_spec(tmp_path / 's.json')).returncode == 0
    env = {'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'HOME': str(tmp_path),
           'OPENCLAW_STATE_DIR': str(member), 'OPENCLAW_CONFIG_PATH': str(member / 'openclaw.json')}
    result = subprocess.run([node, str(cli), 'config', 'validate'], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr


# ── Review round 2: own memory and GAIT stores ──

def test_spec_member_has_own_memory_and_gait_stores(tmp_path):
    border = tmp_path / '.openclaw'
    servers = border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    border_memory = servers['memory-mcp']['env']['MEMORY_DATA_DIR']
    member = tmp_path / 'member'
    private_file(member / '.env', 'PFSENSE_URL=https://fw\n')
    result = run_member_home(tmp_path, border, member, write_spec(tmp_path / 's.json'))
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']
    assert written['memory-mcp']['env']['MEMORY_DATA_DIR'] == str(member / 'memory')
    assert border_memory not in json.dumps(written['memory-mcp'])
    gait = written['gait-mcp']
    assert gait['cwd'] == str(member / 'gait')
    assert gait['env']['HOME'] == str(member / 'gait')
    assert gait['env']['GAIT_MCP_STICKY_FILE'] == str(member / 'gait/.gait_mcp_root')
    assert gait['env']['GAIT_VENV'] == servers['gait-mcp']['env']['GAIT_VENV']   # shared executable
    for store in ('memory', 'gait'):
        assert (member / store).is_dir() and (member / store).stat().st_mode & 0o777 == 0o700
    # The Border's own stores are untouched and not referenced.
    assert str(border) not in json.dumps({k: written[k] for k in ('memory-mcp',)})


def test_spec_store_overrides_without_installed_env(member_home, tmp_path):
    servers = {'memory-mcp': {'command': 'python3', 'env': {'MEMORY_DATA_DIR': '${MEMORY_DATA_DIR}'}},
               'gait-mcp': {'command': 'python3', 'env': {'GAIT_DIR': '/border/gait'}}}
    stores = member_home.spec_store_overrides(servers, tmp_path / 'm', tmp_path / 'border')
    assert stores == [tmp_path / 'm/memory', tmp_path / 'm/gait']
    assert servers['memory-mcp']['env'] == {'MEMORY_DATA_DIR': str(tmp_path / 'm/memory')}
    assert servers['gait-mcp']['env']['GAIT_VENV'] == str(tmp_path / 'border/gait-venv')
    assert 'GAIT_DIR' not in servers['gait-mcp']['env']
    with pytest.raises(ValueError, match='mapping'):
        member_home.spec_store_overrides({'memory-mcp': {'env': ['x']}}, tmp_path, tmp_path)


def test_profile_member_memory_store_unchanged(tmp_path):
    """Known behaviour (predates spec 184): a profile member's memory-mcp keeps the
    Border template's MEMORY_DATA_DIR. Pinned so a change is deliberate."""
    border = tmp_path / '.openclaw'
    servers = border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    member = tmp_path / 'member'
    private_file(member / '.env', 'X=1\n')
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--runtime', 'openclaw',
         '--risk', 'lab', '--member', 'subnet', '--border-config', str(border / 'openclaw.json'),
         '--anthropic-key-from', str(border / '.env'), '--home', str(member)],
        env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    written = json.loads((member / 'openclaw.json').read_text())['mcp']['servers']
    assert written['memory-mcp']['env']['MEMORY_DATA_DIR'] == servers['memory-mcp']['env']['MEMORY_DATA_DIR']


# ── Review round 2: an explicit safe built-in list ──

@pytest.mark.parametrize('tool', ['web_fetch', 'web_search', 'x_search', 'image_generate', 'video_generate',
                                  'music_generate', 'tts', 'personal_instructions', 'memory_get',
                                  'memory_search', 'ls', 'view_image', 'skills_search'])
def test_non_safe_builtins_need_opt_in(profiles, template, tool):
    with pytest.raises(profiles.MemberSpecError, match='outside the safe set'):
        profiles.load_member_spec(allowing(tool), template)
    spec, _ = profiles.load_member_spec(allowing(tool), template, allow_dangerous=True)
    assert spec['dangerous_tools'] == [tool]


def test_safe_builtins_are_exactly_read_and_session_status(profiles, template):
    assert profiles.SAFE_BUILTINS == {'read', 'session_status'}
    assert profiles.DANGEROUS_BUILTINS == profiles.OPENCLAW_BUILTIN_TOOLS - profiles.SAFE_BUILTINS
    spec, warnings = profiles.load_member_spec(allowing('read', 'session_status'), template)
    assert spec['dangerous_tools'] == [] and warnings == []


# ── Review round 2: copy_skill opens, then checks ──

def test_copy_skill_skips_hard_links_and_special_files(member_home, tmp_path):
    source = tmp_path / 'skill'
    (source / 'sub').mkdir(parents=True)
    (source / 'SKILL.md').write_text('skill')
    (source / 'sub/notes.md').write_text('notes')
    outside = tmp_path / 'border-secret'
    outside.write_text('secret')
    os.link(outside, source / 'linked.md')
    os.mkfifo(source / 'pipe')
    (source / 'sym').symlink_to(outside)
    target = tmp_path / 'out'
    member_home.copy_skill(source, target)
    copied = sorted(str(p.relative_to(target)) for p in target.rglob('*'))
    assert copied == ['SKILL.md', 'sub', 'sub/notes.md']
    assert (target / 'SKILL.md').stat().st_mode & 0o777 == 0o600


# ── Review round 3: literal secrets and symlink-safe skill copy ──

def test_literal_secrets_finds_paths_never_values(profiles):
    entry = {
        'command': 'python3',
        'args': ['server.py', '--api-key', 'abc123', '--token=${TOKEN}', '--timeout', '30',
                 'https://user:pw@example.test/x', '--auth-token=literal-xyz'],
        'env': {'PROMETHEUS_TOKEN': 'literal-abc', 'PROMETHEUS_URL': 'http://prom:9090',
                'GNS3_TOKEN_TTL': '3600', 'VERIFY_TOKEN_SSL': 'true', 'SECRET_REF': '${SECRET_REF}',
                'EMPTY_PASSWORD': ''},
        'headers': {'Authorization': 'Bearer literal', 'X-Trace': 'on'},
        'url': 'https://u:p@mcp.example.test/sse',
    }
    found = profiles.literal_secrets(entry)
    assert 'env.PROMETHEUS_TOKEN' in found
    assert 'headers.Authorization' in found
    assert 'url (URL credentials)' in found
    assert 'args[1]' in found and 'args[6] (URL credentials)' in found and 'args[7]' in found
    for clean in ('env.PROMETHEUS_URL', 'env.GNS3_TOKEN_TTL', 'env.VERIFY_TOKEN_SSL', 'env.SECRET_REF',
                  'env.EMPTY_PASSWORD', 'headers.X-Trace', 'args[3]', 'args[4]'):
        assert clean not in found
    assert not any('abc' in item or 'literal' in item or 'pw' in item for item in found)


def test_spec_member_refuses_a_literal_secret_in_a_kept_server(tmp_path):
    border = tmp_path / '.openclaw'
    servers = border_with_pfsense(border, 'ANTHROPIC_API_KEY=fixture\n')
    config = json.loads((border / 'openclaw.json').read_text())
    config['mcp']['servers']['prometheus-mcp'].setdefault('env', {})['PROMETHEUS_TOKEN'] = 'literal-abc'
    (border / 'openclaw.json').write_text(json.dumps(config))
    spec = write_spec(tmp_path / 's.json', servers=['prometheus-mcp'], skills=[],
                      tools={'allow': ['prometheus-mcp__*']})
    member = tmp_path / 'member'
    out = run_member_home(tmp_path, border, member, spec)
    assert out.returncode != 0
    assert 'prometheus-mcp: env.PROMETHEUS_TOKEN' in out.stderr
    assert 'literal-abc' not in out.stderr + out.stdout
    assert not (member / 'openclaw.json').exists()
    # A server the spec does not keep does not block it.
    config['mcp']['servers']['prometheus-mcp']['env'].pop('PROMETHEUS_TOKEN')
    config['mcp']['servers']['pfsense-mcp'] = {**servers['pfsense-mcp'],
                                               'env': {'PFSENSE_API_KEY': 'literal-unkept'}}
    (border / 'openclaw.json').write_text(json.dumps(config))
    ok = run_member_home(tmp_path, border, member, spec)
    assert ok.returncode == 0, ok.stderr
    assert 'literal-unkept' not in (member / 'openclaw.json').read_text()


def test_copy_skill_does_not_enter_a_symlinked_skill_or_subdirectory(member_home, tmp_path):
    private = tmp_path / 'border-private'
    private.mkdir()
    (private / 'token.txt').write_text('secret')
    swapped = tmp_path / 'swapped-skill'
    swapped.symlink_to(private, target_is_directory=True)
    member_home.copy_skill(swapped, tmp_path / 'out1')
    assert not any((tmp_path / 'out1').rglob('*'))
    source = tmp_path / 'skill'
    source.mkdir()
    (source / 'SKILL.md').write_text('skill')
    (source / 'refs').symlink_to(private, target_is_directory=True)
    member_home.copy_skill(source, tmp_path / 'out2')
    assert sorted(str(p.relative_to(tmp_path / 'out2')) for p in (tmp_path / 'out2').rglob('*')) == ['SKILL.md']


def test_literal_secrets_accepts_references_with_an_auth_scheme(profiles):
    for value in ('${X}', 'Bearer ${X}', 'Basic ${A}', 'token ${X}', '${A}:${B}', 'Bot ${X}'):
        assert profiles.literal_secrets({'headers': {'Authorization': value}}) == [], value
    for value in ('Bearer abc', 'x${A}', 'Basic dXNlcjpwYXNz'):
        assert profiles.literal_secrets({'headers': {'Authorization': value}}) == ['headers.Authorization'], value


def test_literal_secrets_flags_nothing_in_the_shipped_template(profiles, template):
    assert {name: found for name, entry in template.items()
            if (found := profiles.literal_secrets(entry))} == {}


def test_literal_secrets_round3_residuals(profiles):
    flagged = {
        'default': {'env': {'TOKEN': '${TOKEN:-sk-abc}'}},
        'aws': {'env': {'AWS_ACCESS_KEY_ID': 'AKIAFIXTURE'}},
        'pwd': {'env': {'DB_PWD': 'x1'}},
        'url': {'url': 'https://user:pw@host'},
        'url-token-user': {'url': 'https://ghp_fixture@github.com/x'},
    }
    clean = {
        'ttl': {'env': {'TOKEN_TTL': '30s'}},
        'file': {'env': {'API_TOKEN_FILE': '/etc/tok'}},
        'domain': {'env': {'COOKIE_DOMAIN': 'example.com'}},
        'url-ref': {'url': 'https://user:${PASS}@host'},
        'url-ref-user': {'url': 'https://${TOKEN}@github.com/x'},
        'token-file-flag': {'args': ['--token-file', '/run/x']},
        'empty-default': {'env': {'TOKEN': '${TOKEN:-}'}},
    }
    for name, entry in flagged.items():
        assert profiles.literal_secrets(entry), name
    for name, entry in clean.items():
        assert profiles.literal_secrets(entry) == [], name
