"""Issue 262: real catalog values must survive native configuration preparation."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lib'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_has_no_unsupported_expressions():
    assert not re.findall(r'\$\{[^}]*:-[^}]*\}', (ROOT / 'config/openclaw.json').read_text())


def test_every_optional_default_and_override_resolves_without_shell_evaluation():
    from mcp_environment import defaults_for, native_entry
    servers = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    catalog = json.loads((ROOT / 'config/mcp-env-defaults.json').read_text())['servers']
    assert len(catalog) == 65
    for name, defaults in catalog.items():
        entry = servers[name]
        assert defaults_for(name) == defaults
        for variable, expected in defaults.items():
            probe = {'env': {'VALUE': '${' + variable + '}'}}
            assert native_entry(name, probe, {})['env']['VALUE'] == expected
            assert native_entry(name, probe, {variable: ''})['env']['VALUE'] == expected
            value = 'literal-$(touch NOT_EXECUTED)-`noop`'
            assert native_entry(name, probe, {variable: value})['env']['VALUE'] == '${' + variable + '}'
            assert '${' + variable + '}' in json.dumps(entry)
    assert defaults_for('nautobot-mcp')['ITSM_LAB_MODE'] == 'false'


def test_selected_cli_applies_defaults_and_preserves_private_references(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('NAUTOBOT_TIMEOUT=91\nNAUTOBOT_TOKEN=private-canary\n')
    output = tmp_path / 'registrations.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/install-mcp-config.py'),
        '--repo', str(ROOT), '--runtime-root', str(tmp_path / 'python-runtimes'),
        '--components', 'nautobot redfish ue5 checkpoint', '--output', str(output)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'private-canary' not in output.read_text() + result.stdout + result.stderr
    servers = json.loads(output.read_text())['mcpServers']
    assert servers['nautobot-mcp']['env']['NAUTOBOT_TIMEOUT'] == '${NAUTOBOT_TIMEOUT}'
    assert servers['nautobot-mcp']['env']['ITSM_LAB_MODE'] == 'false'
    assert servers['redfish-mcp']['env']['REDFISH_PASSWORD'] == ''
    assert servers['unreal-mcp']['url'] == 'http://127.0.0.1:8000/mcp'
    assert servers['chkp-management']['env']['MANAGEMENT_PORT'] == '443'


def test_managed_default_can_be_replaced_by_a_new_override(tmp_path):
    installer = load('managed_defaults_installer', 'scripts/install-mcp-config.py')
    template = {'fixture': {'command': 'tool', 'env': {'TIMEOUT': '${TIMEOUT}'}}}
    path = tmp_path / 'config.json'
    installer.merge_config(path, {'fixture': {'command': 'tool', 'env': {'TIMEOUT': '60'}}}, template)
    installer.merge_config(path, template, template)
    assert json.loads(path.read_text())['mcp']['servers']['fixture']['env']['TIMEOUT'] == '${TIMEOUT}'


def test_custom_fallback_refuses_without_writes_and_remote_legacy_migrates(tmp_path):
    import pytest
    installer = load('remote_defaults_installer', 'scripts/install-mcp-config.py')
    from mcp_environment import native_entry
    template = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    path = tmp_path / 'config.json'
    old = {**template['unreal-mcp'], 'url': '${UE5_MCP_URL:-http://127.0.0.1:8000/mcp}'}
    path.write_text(json.dumps({'mcpServers': {'unreal-mcp': old}}))
    generated = {'unreal-mcp': native_entry('unreal-mcp', template['unreal-mcp'], {})}
    installer.merge_config(path, generated, template)
    assert json.loads(path.read_text())['mcpServers']['unreal-mcp']['url'] == 'http://127.0.0.1:8000/mcp'
    old['url'] = '${CUSTOM:-http://other.invalid}'
    path.write_text(json.dumps({'mcpServers': {'unreal-mcp': old}}))
    before = path.read_bytes()
    with pytest.raises(ValueError, match='manual reconciliation'):
        installer.merge_config(path, generated, template)
    assert path.read_bytes() == before


def test_known_legacy_merge_repairs_defaults_and_preserves_custom_values(tmp_path):
    installer = load('defaults_installer', 'scripts/install-mcp-config.py')
    config = tmp_path / 'openclaw.json'
    template = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    old = {**template['nautobot-mcp'], 'env': {'NAUTOBOT_TIMEOUT': '${NAUTOBOT_TIMEOUT:-60}',
        'NAUTOBOT_TOKEN': 'private-canary', 'ITSM_LAB_MODE': '${ITSM_LAB_MODE:-true}', 'CUSTOM': 'keep'}}
    config.write_text(json.dumps({'mcpServers': {'nautobot-mcp': old}}))
    from mcp_environment import native_entry
    generated = {'nautobot-mcp': native_entry('nautobot-mcp', template['nautobot-mcp'], {})}
    installer.merge_config(config, generated, template)
    actual = json.loads(config.read_text())['mcpServers']['nautobot-mcp']['env']
    assert actual['NAUTOBOT_TIMEOUT'] == '60'
    assert actual['ITSM_LAB_MODE'] == 'false'
    assert actual['NAUTOBOT_TOKEN'] == 'private-canary'
    assert actual['CUSTOM'] == 'keep'


def test_hermes_direct_conversion_preserves_optional_defaults():
    converter = load('defaults_converter', 'scripts/openclaw-to-hermes-mcp.py')
    template = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    text = converter.emit_yaml({'nautobot-mcp': template['nautobot-mcp']}, ROOT,
        {'NAUTOBOT_URL': 'https://fixture.invalid', 'NAUTOBOT_TOKEN': 'synthetic',
         'NAUTOBOT_CA_BUNDLE': '/synthetic/ca.pem'}, {})
    assert 'NAUTOBOT_TIMEOUT: "60"' in text
    assert 'ITSM_LAB_MODE: "false"' in text
    assert 'enabled: true' in text
    legacy = converter.emit_yaml({'fixture': {'command': 'tool',
        'env': {'PORT': '${PORT:-80}', 'TOKEN': '${TOKEN:-}'}}}, ROOT, {}, {})
    assert 'PORT: "80"' in legacy and 'TOKEN: ""' in legacy and 'enabled: true' in legacy


def test_setup_empty_optional_and_remote_url_do_not_create_empty_native_aliases():
    from setup_registration import native_environment
    from mcp_environment import native_entry
    values = {}
    result = native_environment('redfish-mcp', {'REDFISH_PASSWORD': '${REDFISH_PASSWORD}'}, values)
    assert result == {'REDFISH_PASSWORD': ''}
    assert values == {}
    entry = native_entry('topolograph-mcp', {'url': '${TOPOLOGRAPH_MCP_URL}'}, {})
    assert entry['url'] == 'https://topolograph.com/mcp'


def test_portability_gate_rejects_fallbacks_in_all_fields(tmp_path):
    validator = load('defaults_portability', 'scripts/check-mcp-portability.py')
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'mcpServers': {'fixture': {'url': '${URL:-http://localhost}',
        'env': {'PORT': '${PORT:-80}'}, 'headers': {'X-Test': '${HEADER:-x}'}}}}))
    failures, _, _ = validator.check(str(config), str(ROOT))
    assert len(failures) == 3


def test_actual_pinned_native_resolver_when_available():
    """Opt-in uses only the native pure resolver, never a gateway/provider."""
    import pytest
    from mcp_environment import native_entry
    module = os.environ.get('NETCLAW_TEST_OPENCLAW_ENV_MODULE')
    if not module:
        pytest.skip('Set NETCLAW_TEST_OPENCLAW_ENV_MODULE for actual native qualification')
    source = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    cases = []
    for name, entry in source.items():
        prepared = native_entry(name, entry, {})
        required = set(re.findall(r'\$\{([A-Z_][A-Z0-9_]*)\}', json.dumps(prepared)))
        cases.append({'entry': prepared, 'env': {key: 'synthetic-required' for key in required}})
    script = '''import fs from 'node:fs'; import {pathToFileURL} from 'node:url';
const {r:resolve}=await import(pathToFileURL(process.argv[1]));
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
for(const c of cases){const result=resolve(c.entry,c.env);if(JSON.stringify(result).includes('${'))throw Error('unresolved');}
console.log(JSON.stringify({passed:cases.length}));'''
    result = subprocess.run([os.environ.get('NETCLAW_TEST_NODE', 'node'), '--input-type=module',
        '-e', script, module], input=json.dumps(cases), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'passed': len(source)}
