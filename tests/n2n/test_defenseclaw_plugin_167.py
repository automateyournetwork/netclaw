"""Spec 167: DefenseClaw 1.x OpenClaw plugin route (F3), member plugin copy (F5)
and gateway SecretRef tokens (F2). Fixtures only; no gateway, proxy or provider."""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from bgp.federation import controls, gateway, gateway_ws, runtime as runtime_module
from bgp.federation.runtime import ROOT, Runtime

PLUGIN = 'guarded via DefenseClaw OpenClaw plugin'


GUARDRAIL = 'guardrail:\n  connector: openclaw\n  enabled: true\n  scanner_mode: local\nllm:\n  model: x\n'


def plugin_config(tmp_path, model='ollama-cloud/minimax-m3'):
    ext = tmp_path / '.openclaw/extensions/defenseclaw'
    ext.mkdir(parents=True, exist_ok=True)
    (ext / 'openclaw.plugin.json').write_text(json.dumps({'id': 'defenseclaw', 'name': 'DefenseClaw'}))
    dc = tmp_path / '.defenseclaw'
    dc.mkdir(exist_ok=True)
    if not (dc / 'config.yaml').exists():
        (dc / 'config.yaml').write_text(GUARDRAIL)
    other = tmp_path / '.openclaw/extensions/slack'
    other.mkdir(parents=True, exist_ok=True)
    return {
        'agents': {'defaults': {'model': {'primary': model, 'fallbacks': ['openai/direct']}}},
        'plugins': {'allow': ['slack', 'defenseclaw'], 'deny': ['other'],
                    'entries': {'defenseclaw': {'enabled': True, 'config': {'sidecar': 'http://127.0.0.1:18970'}},
                                'slack': {'enabled': True, 'config': {'token': 'must-not-copy'}}},
                    'load': {'paths': [str(other), str(ext)]}},
    }


@pytest.fixture
def route(monkeypatch, tmp_path):
    """Write the effective OpenClaw config; return a function running the checks."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('N2N_RISK_MODE', 'production')
    monkeypatch.delenv('OPENCLAW_STATE_DIR', raising=False)
    monkeypatch.delenv('OPENCLAW_HOME', raising=False)
    monkeypatch.delenv('NETCLAW_RUNTIME', raising=False)
    monkeypatch.delenv('DEFENSECLAW_HOME', raising=False)
    config = tmp_path / 'runtime/openclaw.json'
    config.parent.mkdir()
    monkeypatch.setenv('OPENCLAW_CONFIG_PATH', str(config))
    security = tmp_path / '.openclaw/config/openclaw.json'
    security.parent.mkdir(parents=True)
    security.write_text(json.dumps({'security': {'mode': 'defenseclaw'}}))
    monkeypatch.setattr(controls.shutil, 'which', lambda _: '/fixture/defenseclaw')
    async def reachable(): return True
    monkeypatch.setattr(controls, '_guard_proxy_up', reachable)

    def check(cfg, override=None):
        config.write_text(json.dumps(cfg))
        controls.invalidate_cache()
        return controls.guarded_model_route(override)
    check.security = security
    return check


def test_plugin_route_accepted_for_any_model_and_override(route, tmp_path):
    cfg = plugin_config(tmp_path)
    assert route(cfg) == (True, PLUGIN)
    assert route(cfg, 'anthropic/direct-override') == (True, PLUGIN)
    assert asyncio.run(controls.defenseclaw_available()) == (True, '')
    # gateway --model override is admitted under the plugin route
    cmd = ['openclaw', 'agent', '--local', '--model', 'anthropic/model']
    assert asyncio.run(gateway._apply_production_controls(list(cmd), 'fixture')) == cmd


def test_plugin_route_without_allow_or_deny_lists(route, tmp_path):
    cfg = plugin_config(tmp_path)
    del cfg['plugins']['allow'], cfg['plugins']['deny']
    assert route(cfg) == (True, PLUGIN)


def test_plugin_route_still_needs_security_mode_and_proxy(route, tmp_path, monkeypatch):
    route(plugin_config(tmp_path))
    route.security.write_text('{"security":{"mode":"hobby"}}')
    assert asyncio.run(controls.defenseclaw_available())[0] is False
    route.security.write_text('{"security":{"mode":"defenseclaw"}}')
    async def down(): return False
    monkeypatch.setattr(controls, '_guard_proxy_up', down)
    controls.invalidate_cache()
    ok, detail = asyncio.run(controls.defenseclaw_available())
    assert ok is False and 'not reachable' in detail


def _mutations(tmp_path):
    wrong = tmp_path / '.openclaw/extensions/not-defenseclaw'
    wrong.mkdir(parents=True, exist_ok=True)
    afile = tmp_path / 'file/defenseclaw'
    afile.parent.mkdir(parents=True, exist_ok=True)
    afile.write_text('')
    return {
        'disabled': lambda p: p['entries']['defenseclaw'].update(enabled=False),
        'enabled-not-bool': lambda p: p['entries']['defenseclaw'].update(enabled='true'),
        'enabled-missing': lambda p: p['entries']['defenseclaw'].pop('enabled'),
        'entry-not-object': lambda p: p['entries'].update(defenseclaw=True),
        'plugins-disabled': lambda p: p.update(enabled=False),
        'not-allowed': lambda p: p['allow'].remove('defenseclaw'),
        'allow-not-list': lambda p: p.update(allow='defenseclaw'),
        'denied': lambda p: p['deny'].append('defenseclaw'),
        'deny-not-list': lambda p: p.update(deny='other'),
        'no-load': lambda p: p.pop('load'),
        'no-paths': lambda p: p['load'].pop('paths'),
        'nonexistent-path': lambda p: p['load'].update(paths=[str(tmp_path / 'missing/defenseclaw')]),
        'relative-path': lambda p: p['load'].update(paths=['extensions/defenseclaw']),
        'file-not-dir': lambda p: p['load'].update(paths=[str(afile)]),
        'wrong-basename': lambda p: p['load'].update(paths=[str(wrong)]),
        'only-other-plugin': lambda p: p['load'].update(paths=[p['load']['paths'][0]]),
    }


CASES = ['disabled', 'enabled-not-bool', 'enabled-missing', 'entry-not-object', 'plugins-disabled',
         'not-allowed', 'allow-not-list', 'denied', 'deny-not-list', 'no-load', 'no-paths',
         'nonexistent-path', 'relative-path', 'file-not-dir', 'wrong-basename', 'only-other-plugin']


def test_case_list_covers_mutations(tmp_path):
    assert sorted(CASES) == sorted(_mutations(tmp_path))


@pytest.mark.parametrize('case', CASES)
def test_each_missing_plugin_criterion_rejects(route, tmp_path, case):
    cfg = plugin_config(tmp_path)
    _mutations(tmp_path)[case](cfg['plugins'])
    ok, detail = route(cfg)
    assert ok is False
    assert 'defenseclaw provider' in detail
    assert controls.defenseclaw_plugin_config(cfg) is None
    assert asyncio.run(controls.defenseclaw_available())[0] is False


def test_absent_plugin_keeps_provider_detail(route, tmp_path):
    cfg = plugin_config(tmp_path)
    del cfg['plugins']['entries']['defenseclaw']
    assert route(cfg) == (False, 'primary, override and fallback models must use the defenseclaw provider')
    assert route({'agents': {'defaults': {'model': 'anthropic/x'}}})[1] == \
        'primary, override and fallback models must use the defenseclaw provider'


def test_legacy_provider_route_unchanged(route, tmp_path):
    port = controls.DEFENSECLAW_GUARD_PORT
    cfg = {'agents': {'defaults': {'model': {'primary': 'defenseclaw/model'}}},
           'models': {'providers': {'defenseclaw': {'baseUrl': f'http://127.0.0.1:{port}/v1'}}}}
    assert route(cfg) == (True, 'guarded model route configured')
    assert route(cfg, 'anthropic/model')[0] is False
    cfg['models']['providers']['defenseclaw']['baseUrl'] = 'https://unguarded.invalid/v1'
    assert route(cfg) == (False, 'defenseclaw provider must target the configured loopback guard port')
    # with the provider route valid AND the plugin present, the provider detail wins
    both = plugin_config(tmp_path, 'defenseclaw/model')
    both['agents']['defaults']['model'].pop('fallbacks')
    both['models'] = {'providers': {'defenseclaw': {'baseUrl': f'http://localhost:{port}/v1'}}}
    assert route(both) == (True, 'guarded model route configured')


def test_unreadable_config_fails_closed(route, tmp_path, monkeypatch):
    route(plugin_config(tmp_path))
    Path(controls.os.environ['OPENCLAW_CONFIG_PATH']).write_text('[]')
    assert controls.guarded_model_route()[0] is False
    monkeypatch.setenv('OPENCLAW_CONFIG_PATH', str(tmp_path / 'missing.json'))
    assert controls.guarded_model_route() == (False, 'effective model route configuration is unavailable or invalid')


def test_config_path_resolution_uses_state_dir(route, tmp_path, monkeypatch):
    state = tmp_path / 'state'
    state.mkdir()
    (state / 'openclaw.json').write_text(json.dumps(plugin_config(tmp_path)))
    monkeypatch.delenv('OPENCLAW_CONFIG_PATH')
    monkeypatch.setenv('OPENCLAW_STATE_DIR', str(state))
    assert controls.guarded_model_route() == (True, PLUGIN)


def test_hermes_unchanged_even_with_plugin(route, tmp_path, monkeypatch):
    route(plugin_config(tmp_path))
    hermes = Runtime('hermes', tmp_path, tmp_path / 'config.yaml', None)
    monkeypatch.setattr(runtime_module, 'selected', lambda *a, **k: hermes)
    ok, detail = controls.guarded_model_route()
    assert ok is False and 'Hermes' in detail


# ---- F5: member home keeps only the DefenseClaw plugin ----------------------

def script(name):
    spec = importlib.util.spec_from_file_location('fixture167_' + name.replace('-', '_'), ROOT / 'scripts' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENV = {'CONVERGENCE_ENABLED': 'true', 'CONVERGENCE_API_URL': 'https://convergence.example',
       'CONVERGENCE_API_TOKEN': 'fixture-viewer', 'CONVERGENCE_SITE': 'lab',
       'CONVERGENCE_EXPORTERS': '192.0.2.1', 'OLLAMA_API_KEY': 'fixture-provider'}


@pytest.fixture
def border(tmp_path, monkeypatch):
    monkeypatch.delenv('NETCLAW_RUNTIME', raising=False)
    monkeypatch.setenv('DEFENSECLAW_HOME', str(tmp_path / '.defenseclaw'))
    home = tmp_path / 'Border'
    home.mkdir(mode=0o700)
    rt = Runtime('openclaw', home, home / 'openclaw.json', None)
    (home / '.env').write_text(''.join(k + '=' + json.dumps(v) + '\n' for k, v in ENV.items()))
    (home / '.env').chmod(0o600)
    records = home / 'python-runtimes/records'
    records.mkdir(parents=True)
    for component in ('convergence-read', 'n2n'):
        (records / component).write_text(sys.executable + '\n')
    base = {'mcp': {'servers': {'convergence-read-mcp': {'command': 'danger'}}},
            'agents': {'defaults': {'model': {'primary': 'ollama/fixture-model'}}},
            'models': {'providers': {'ollama': {'api': 'openai-completions', 'baseUrl': 'https://ollama.example/v1',
                'apiKey': '${OLLAMA_API_KEY}', 'models': [{'id': 'fixture-model', 'name': 'Fixture'}]}}},
            'channels': {'slack': {'token': 'must-not-copy'}}}

    def provision(cfg, name):
        rt.config.write_text(json.dumps(cfg))
        rt.config.chmod(0o600)
        module = script('in2n-member-home.py')
        member = module.provision_convergence(rt, 'lab', tmp_path / name)
        return json.loads((member / 'openclaw.json').read_text())
    return base, provision


def test_member_home_copies_only_defenseclaw_plugin(border, tmp_path):
    base, provision = border
    plugins = plugin_config(tmp_path)['plugins']
    member = provision({**base, 'plugins': plugins}, 'member-plugin')
    ext = str(tmp_path / '.openclaw/extensions/defenseclaw')
    assert member['plugins'] == {'allow': ['defenseclaw'],
                                 'entries': {'defenseclaw': plugins['entries']['defenseclaw']},
                                 'load': {'paths': [ext]}}
    assert 'must-not-copy' not in json.dumps(member) and 'slack' not in json.dumps(member['plugins'])
    assert controls.defenseclaw_plugin_route(member) == (True, PLUGIN)
    # without an allow list in the source none is invented
    del plugins['allow']
    member = provision({**base, 'plugins': plugins}, 'member-noallow')
    assert 'allow' not in member['plugins']


def test_member_home_has_no_plugins_when_defenseclaw_absent_or_unusable(border, tmp_path):
    base, provision = border
    assert 'plugins' not in provision(base, 'member-none')
    plugins = plugin_config(tmp_path)['plugins']
    plugins['entries']['defenseclaw']['enabled'] = False
    assert 'plugins' not in provision({**base, 'plugins': plugins}, 'member-disabled')
    plugins = plugin_config(tmp_path)['plugins']
    plugins['allow'] = ['slack']
    assert 'plugins' not in provision({**base, 'plugins': plugins}, 'member-notallowed')


# ---- F2: gateway auth token SecretRef --------------------------------------

@pytest.fixture
def gw_config(tmp_path, monkeypatch):
    for key in ('OPENCLAW_GATEWAY_WS_URL', 'OPENCLAW_GATEWAY_TOKEN', 'FIXTURE_GW_TOKEN'):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / 'openclaw.json'

    def write(token):
        path.write_text(json.dumps({'gateway': {'port': 18800, 'auth': {'token': token}}}))
        return str(path)
    return write


def test_gateway_string_token_unchanged(gw_config):
    assert gateway_ws.resolve_gateway_ws_config(gw_config('literal')) == ('ws://127.0.0.1:18800', 'literal')


def test_gateway_env_secretref_resolves(gw_config, monkeypatch):
    monkeypatch.setenv('FIXTURE_GW_TOKEN', 'from-env')
    ref = {'source': 'env', 'provider': 'default', 'id': 'FIXTURE_GW_TOKEN'}
    assert gateway_ws.resolve_gateway_ws_config(gw_config(ref)) == ('ws://127.0.0.1:18800', 'from-env')


def test_gateway_env_secretref_missing_names_variable(gw_config):
    ref = {'source': 'env', 'provider': 'default', 'id': 'FIXTURE_GW_TOKEN'}
    with pytest.raises(gateway_ws.GatewayWsError, match='FIXTURE_GW_TOKEN'):
        gateway_ws.resolve_gateway_ws_config(gw_config(ref))
    with pytest.raises(gateway_ws.GatewayWsError):
        gateway_ws.resolve_gateway_ws_config(gw_config({'source': 'env'}))


@pytest.mark.parametrize('source', ['store', 'file', 'exec', None])
def test_gateway_other_secretref_sources_refused(gw_config, source):
    ref = {'source': source, 'provider': 'default', 'id': 'gateway-token'}
    with pytest.raises(gateway_ws.GatewayWsError, match='OPENCLAW_GATEWAY_TOKEN') as err:
        gateway_ws.resolve_gateway_ws_config(gw_config(ref))
    assert 'not supported' in str(err.value)


def test_gateway_env_override_wins_over_secretref(gw_config, monkeypatch):
    path = gw_config({'source': 'store', 'provider': 'default', 'id': 'gateway-token'})
    monkeypatch.setenv('OPENCLAW_GATEWAY_TOKEN', 'override')
    assert gateway_ws.resolve_gateway_ws_config(path) == ('ws://127.0.0.1:18800', 'override')
    monkeypatch.setenv('OPENCLAW_GATEWAY_WS_URL', 'ws://127.0.0.1:1')
    assert gateway_ws.resolve_gateway_ws_config(path) == ('ws://127.0.0.1:1', 'override')


def test_gateway_missing_token_error_unchanged(gw_config):
    with pytest.raises(gateway_ws.GatewayWsError, match='no gateway auth token'):
        gateway_ws.resolve_gateway_ws_config(gw_config(None))



def test_plugin_route_requires_the_plugin_manifest(route, tmp_path):
    cfg = plugin_config(tmp_path)
    (tmp_path / '.openclaw/extensions/defenseclaw/openclaw.plugin.json').unlink()
    ok, detail = route(cfg)
    assert not ok and 'plugin manifest' in detail
    (tmp_path / '.openclaw/extensions/defenseclaw/openclaw.plugin.json').write_text('{"id": "other"}')
    assert route(cfg)[0] is False


@pytest.mark.parametrize('yaml,reason', [
    (None, 'config.yaml is unavailable'),
    ('guardrail:\n  connector: openclaw\n  enabled: false\n', 'not enabled'),
    ('guardrail:\n  connector: codex\n  enabled: true\n', 'connector is not openclaw'),
    ('guardrail:\n  connector: openclaw\n  enabled: true\n  port: 4100\n', 'port 4100'),
    ('llm:\n  enabled: true\n  connector: openclaw\n', 'not enabled'),
])
def test_plugin_route_requires_defenseclaw_guardrail_on_the_probed_port(route, tmp_path, yaml, reason):
    cfg = plugin_config(tmp_path)
    conf = tmp_path / '.defenseclaw/config.yaml'
    if yaml is None:
        conf.unlink()
    else:
        conf.write_text(yaml)
    ok, detail = route(cfg)
    assert not ok and reason in detail
    conf.write_text('guardrail:\n  connector: openclaw\n  enabled: true\n  port: 4000\n')
    assert route(cfg) == (True, PLUGIN)


@pytest.mark.parametrize('model,providers', [
    ('ollama/llama3', {}),                                                    # local by default
    ('lan/llm', {'lan': {'baseUrl': 'http://192.168.1.20:8000/v1'}}),         # private
    ('loop/llm', {'loop': {'baseUrl': 'http://127.0.0.1:11434'}}),            # loopback
    ('host/llm', {'host': {'baseUrl': 'http://gpu.local:8000'}}),             # mDNS
])
def test_plugin_route_refuses_local_or_private_providers(route, tmp_path, model, providers):
    cfg = plugin_config(tmp_path, model=model)
    cfg['models'] = {'providers': providers}
    ok, detail = route(cfg)
    assert not ok and model in detail and 'local or private provider' in detail
    cloud = plugin_config(tmp_path)
    cloud['models'] = {'providers': {'ollama-cloud': {'baseUrl': 'https://ollama.com'}}}
    assert route(cloud) == (True, PLUGIN)
    assert route(cloud, override='loop/llm')[0] is True                        # undeclared: cloud built-in
    cloud['models']['providers']['loop'] = {'baseUrl': 'http://127.0.0.1:1'}
    assert route(cloud, override='loop/llm')[0] is False                       # override checked too


def test_generic_member_builder_mirrors_only_security_mode(tmp_path):
    # Spec 167: generic (non-Convergence) OpenClaw members also check security.mode in
    # their own home; run the real script entry point for a generic profile.
    import os
    import subprocess
    border = tmp_path / 'Border'
    (border / 'config').mkdir(parents=True)
    (border / 'openclaw.json').write_text(json.dumps({'mcp': {'servers': {}}}))
    (border / 'config/openclaw.json').write_text(json.dumps(
        {'security': {'mode': 'defenseclaw', 'other': 'must-not-copy'}}))
    (border / '.env').write_text('')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OPENCLAW_', 'NETCLAW_', 'N2N_'))}
    env.update(HOME=str(tmp_path), NETCLAW_RUNTIME='openclaw', OPENCLAW_STATE_DIR=str(border),
               OPENCLAW_CONFIG_PATH=str(border / 'openclaw.json'), NETCLAW_RUNTIME_ENV=str(border / '.env'))
    member = tmp_path / 'member'
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/in2n-member-home.py'), '--risk', 'lab',
                           '--member', 'cml', '--home', str(member),
                           '--border-config', str(border / 'openclaw.json')],
                          env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    mirrored = member / 'config/openclaw.json'
    assert json.loads(mirrored.read_text()) == {'security': {'mode': 'defenseclaw'}}
    assert mirrored.stat().st_mode & 0o777 == 0o600
