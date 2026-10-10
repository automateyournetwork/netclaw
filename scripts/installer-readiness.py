#!/usr/bin/env python3
"""Report installed artifacts, access, discovery and provider readiness separately.

Default is configuration-only. --probe performs bounded MCP discovery, never
network device tool calls. --check-provider reads the configured Ollama model
catalog/capabilities; it does not generate text or download models.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load('component-launch')
registration = load('install-mcp-config')
probe = load('mcp-probe')
writer = load('write-env')


def expand(value, env):
    def replace(match):
        key, default = match.groups()
        return env.get(key) or (default if default is not None else match.group(0))
    return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}', replace, value)


def native_result(data, server, expected):
    """Do not accept the historical empty-catalog/exit-0 probe result."""
    if not isinstance(data, dict) or data.get('diagnostics') or data.get('error'):
        return False
    row = data.get('servers', {}).get(server, {})
    names = data.get('tools', [])
    return (isinstance(row.get('tools'), int) and row['tools'] > 0 and
            isinstance(names, list) and bool(names) and
            all(any(isinstance(name, str) and (name == tool or name.endswith('_'+tool))
                    for name in names) for tool in expected))


def native_probe(server, expected, env, config, timeout):
    cli = shutil.which('openclaw', path=env.get('PATH'))
    if not cli:
        return {'status':'failed', 'reason':'runtime_cli_missing'}
    probe_env = {**env, 'OPENCLAW_CONFIG_PATH':str(config)}
    try:
        # Capture stdout/stderr privately and bound both time and reported data.
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen([cli, 'mcp', 'probe', server, '--json'],
                env=probe_env, stdin=subprocess.DEVNULL, stdout=output,
                stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                rc = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                probe.stop(process)
                return {'status':'failed', 'reason':'runtime_probe_timeout'}
            output.seek(0)
            raw = output.read(8 * 1024 * 1024 + 1)
        if rc or len(raw) > 8 * 1024 * 1024:
            return {'status':'failed', 'reason':'runtime_probe_failed'}
        data = json.loads(raw)
        if not native_result(data, server, expected):
            return {'status':'failed', 'reason':'runtime_expected_tools_missing'}
        return {'status':'verified', 'tool_count':data['servers'][server]['tools']}
    except (OSError, ValueError, TypeError, AttributeError):
        return {'status':'failed', 'reason':'runtime_probe_invalid_response'}


def missing_credentials(rule, env):
    missing = [key for key in rule.get('required_env', []) if not env.get(key)]
    if 'SERVICENOW_INSTANCE_URL' in rule.get('required_env', []):
        auth = env.get('SERVICENOW_AUTH_TYPE') or 'basic'
        required = {'basic':['SERVICENOW_USERNAME','SERVICENOW_PASSWORD'],
                    'oauth':['SERVICENOW_CLIENT_ID','SERVICENOW_CLIENT_SECRET','SERVICENOW_TOKEN_URL'],
                    'api_key':['SERVICENOW_API_KEY']}.get(auth, ['SERVICENOW_AUTH_TYPE'])
        missing += [key for key in required if not env.get(key)]
    return missing


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError('redirect_refused')


def http_json(url, headers, body=None, timeout=5):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers={**headers,'Content-Type':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('response_too_large')
        return json.loads(raw)


def ollama_readiness(config, env, check=False, request=http_json):
    defaults = config.get('agents', {}).get('defaults', {})
    selection = defaults.get('model', '')
    model = selection.get('primary', '') if isinstance(selection, dict) else selection
    if not isinstance(model, str) or not model.startswith('ollama/'):
        return {'status':'unverified', 'reason':'not_an_ollama_primary', 'tool_calling':'unverified'}
    model = model.split('/', 1)[1]
    provider = config.get('models', {}).get('providers', {}).get('ollama', {})
    endpoint = provider.get('baseUrl') or env.get('OLLAMA_BASE_URL') or 'http://127.0.0.1:11434'
    endpoint = expand(endpoint, env)
    parsed = urlsplit(endpoint)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return {'status':'failed', 'reason':'invalid_ollama_endpoint', 'tool_calling':'unverified'}
    # OpenAI-compatible /v1 config still uses Ollama's native catalog endpoints.
    path = parsed.path.rstrip('/')
    if path.endswith('/v1'):
        path = path[:-3]
    base = urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))
    if not check:
        return {'status':'unverified', 'reason':'provider_check_not_requested', 'tool_calling':'unverified'}
    key = provider.get('apiKey') or env.get('OLLAMA_API_KEY') or ''
    if not isinstance(key, str):
        return {'status':'unverified', 'reason':'provider_secret_reference_requires_runtime', 'tool_calling':'unverified'}
    key = expand(key, env)
    if '${' in key:
        return {'status':'configuration_required', 'reason':'provider_key_unresolved', 'tool_calling':'unverified'}
    headers = {'Authorization':'Bearer '+key} if key else {}
    try:
        catalog = request(base+'/api/tags', headers)
        names = {row.get('name') or row.get('model') for row in catalog.get('models', [])}
        candidates = {model} if ':' in model else {model, model+':latest'}
        match = next((name for name in names if name in candidates), None)
        if not match:
            return {'status':'failed', 'reason':'ollama_model_missing', 'tool_calling':'unverified'}
        info = request(base+'/api/show', headers, {'model':match})
        capabilities = info.get('capabilities')
        if not isinstance(capabilities, list):
            return {'status':'unverified', 'reason':'ollama_model_capabilities_unknown', 'tool_calling':'unverified'}
        if 'tools' not in capabilities:
            return {'status':'failed', 'reason':'ollama_model_has_no_tool_capability', 'tool_calling':'unsupported'}
        return {'status':'verified', 'reason':'ollama_model_available', 'tool_calling':'advertised_not_exercised'}
    except (OSError, ValueError, TypeError, AttributeError):
        # URLs, response bodies and credentials never enter the saved report.
        return {'status':'failed', 'reason':'ollama_endpoint_or_api_unavailable', 'tool_calling':'unverified'}


def check_server(name, entry, component, rule, env, config, runtime, do_probe, timeout):
    row = {'server':name, 'access':'native_mcp', 'registration':'verified',
           'artifacts':'unverified', 'discovery':{'status':'unverified'}, 'endpoint':'unverified'}
    if entry.get('enabled') is False:
        row['discovery'] = {'status':'configuration_required', 'reason':'server_disabled'}
        return row
    child_env = dict(env)
    child_env.update({k:expand(str(v), env) for k,v in entry.get('env', {}).items()})
    missing = missing_credentials(rule, child_env)
    unresolved = any('${' in str(v) for v in entry.get('env', {}).values() if '${' in expand(str(v), child_env))
    try:
        if component in launcher.CONTRACT:
            launcher.resolve(component, name, env=child_env)
        command = entry.get('command')
        if command:
            command = expand(command, child_env)
            executable = shutil.which(command, path=child_env.get('PATH'))
            if not executable:
                raise ValueError('launcher_missing')
            parts = [executable] + [expand(v, child_env) for v in entry.get('args', [])]
            cwd = Path(entry.get('cwd', str(ROOT)))
            if not cwd.is_dir():
                raise ValueError('cwd_missing')
            for arg in parts[1:]:
                if arg.endswith(('.py', '.js', '.mjs')) and '/' in arg and not (cwd/arg).is_file():
                    raise ValueError('script_missing')
            row['artifacts'] = 'verified'
        else:
            row['artifacts'] = 'remote'
        if missing or unresolved:
            row['discovery'] = {'status':'configuration_required', 'reason':'missing_credentials', 'variables':missing}
            return row
        if not do_probe:
            return row
        expected = rule.get('expected_tools', [])
        if runtime == 'openclaw':
            row['discovery'] = native_probe(name, expected, child_env, config, timeout)
        elif command:
            row['discovery'] = probe.discover(parts, child_env, str(cwd), timeout, expected)
            # Direct discovery is not proof of Hermes's agent-visible catalog.
            row['access'] = 'hermes_registered_direct_probe'
            row['agent_discovery'] = 'unverified'
        else:
            row['discovery'] = {'status':'unverified', 'reason':'hermes_remote_probe_not_available'}
        return row
    except (OSError, ValueError, KeyError):
        row['artifacts'] = 'failed'
        row['discovery'] = {'status':'failed', 'reason':'launcher_or_runtime_missing'}
        return row


def report(selected, failed, templates, live, env, config_path, runtime, do_probe=False, timeout=25):
    components = []
    for component in selected:
        rule = launcher.CONTRACT.get(component, {})
        expected = rule.get('servers') or [name for name in templates if registration.component_for(name) == component]
        row = {'component':component, 'installation':'failed' if component in failed else 'recorded', 'servers':[]}
        if component in failed:
            row['status'] = 'failed'
        elif rule.get('access') == 'hud-private':
            row['status'] = 'unverified'
            row['access'] = 'hud-private'
            row['reason'] = 'Launch netclaw hud; inspect private companion readiness and run an owned canary. No agent registration is expected.'
        elif not expected:
            row['status'] = 'unverified'
            row['reason'] = 'no_native_binding_declared; consult_component_skill'
        else:
            for name in expected:
                if name not in live:
                    row['servers'].append({'server':name, 'registration':'failed',
                        'discovery':{'status':'failed','reason':'not_registered'}, 'endpoint':'unverified'})
                else:
                    row['servers'].append(check_server(name, live[name], component, rule, env,
                        config_path, runtime, do_probe, timeout))
            statuses = {item['discovery']['status'] for item in row['servers']}
            row['status'] = ('failed' if 'failed' in statuses else 'configuration_required'
                             if 'configuration_required' in statuses else 'discovery_verified'
                             if statuses == {'verified'} else 'unverified')
        components.append(row)
    return {'schema_version':1, 'runtime':runtime, 'components':components,
            'endpoint_operations':'unverified', 'agent_turn':'unverified',
            'ok':not any(row['status'] == 'failed' for row in components)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', choices=['openclaw','hermes'], default='openclaw')
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--components', required=True)
    parser.add_argument('--failed-components', default='')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--check-provider', action='store_true')
    parser.add_argument('--timeout', type=float, default=25)
    args = parser.parse_args()
    if not 0 < args.timeout <= 120:
        parser.error('timeout must be >0 and <=120 seconds')
    env = launcher.environment({**os.environ,'NETCLAW_RUNTIME_ROOT':str(args.runtime_root),
        'NETCLAW_RUNTIME_ENV':str(args.runtime_root.parent/'.env')})
    try:
        templates = json.loads((ROOT/'config/openclaw.json').read_text())['mcpServers']
        if args.runtime == 'openclaw':
            config = json.loads(args.config.read_text())
            live = config.get('mcp', {}).get('servers', config.get('mcpServers', {}))
        else:
            import yaml
            config = yaml.safe_load(args.config.read_text()) or {}
            live = config.get('mcp_servers', {})
        result = report(args.components.split(), set(args.failed_components.split()), templates, live,
                        env, args.config, args.runtime, args.probe, args.timeout)
        result['provider'] = (ollama_readiness(config, env, args.check_provider) if args.runtime == 'openclaw'
                              else {'status':'unverified','reason':'check_provider_with_hermes'})
        if result['provider']['status'] == 'failed':
            result['ok'] = False
        writer.write_private(args.output, json.dumps(result, indent=2)+'\n')
        for row in result['components']:
            print(f"[{row['status'].upper()}] {row['component']}")
        print('Provider: '+result['provider']['status'])
        print('Device/endpoint operations and agent answers remain unverified; discovery does not prove either.')
        print('Readiness report: '+str(args.output))
        return 0 if result['ok'] else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        print('Readiness could not inspect runtime configuration; no readiness claim made.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
