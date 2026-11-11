"""Spec 185: a member spec's model may use a provider the Border configures, or a subscription login.

Source and fixture checks only: no gateway, provider, daemon or MCP server is started.
"""
import copy
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


T184 = load(ROOT / 'tests/n2n/test_member_spec_184.py', 'spec185_t184')
EXAMPLE, clean_env, slice_keys = T184.EXAMPLE, T184.clean_env, T184.slice_keys

CLOUD = {'api': 'ollama', 'baseUrl': 'https://ollama.com', 'apiKey': '${OLLAMA_API_KEY}',
         'models': [{'id': 'minimax-m3', 'name': 'MiniMax M3'}, {'id': 'minimax-m2.7', 'name': 'MiniMax M2.7'}]}
PROVIDERS = {
    'ollama-cloud': CLOUD,
    'llama-cpp': {'api': 'openai-completions', 'baseUrl': 'http://127.0.0.1:39891/v1', 'apiKey': 'x',
                  'localService': {'command': '/opt/llama-server'}, 'models': [{'id': 'local'}]},
    'leaky': {'api': 'ollama', 'baseUrl': 'https://example.net', 'apiKey': 'sk-literal-value',
              'models': [{'id': 'm1'}]},
    'other': {'api': 'ollama', 'baseUrl': 'https://other.example', 'apiKey': '${OTHER_KEY}', 'models': [{'id': 'o1'}]},
}


@pytest.fixture(scope='module')
def profiles():
    return load(ROOT / 'scripts/in2n-profiles.py', 'spec185_profiles')


@pytest.fixture(scope='module')
def template():
    servers = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    return {**servers, 'pfsense-mcp': T184.PFSENSE}


def spec(**changes):
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    return data


def test_border_provider_model_is_accepted_by_reference(profiles, template):
    result, warnings = profiles.load_member_spec(spec(model='ollama-cloud/minimax-m3'), template,
                                                 installed=[], providers=PROVIDERS)
    assert (result['provider'], result['model'], result['auth']) == ('ollama-cloud', 'minimax-m3', 'api-key')
    assert profiles.spec_model_binding(result, 'tier') == 'ollama-cloud/minimax-m3'
    entry = profiles.spec_provider_entry(result, PROVIDERS)
    assert entry == {**CLOUD, 'models': [{'id': 'minimax-m3', 'name': 'MiniMax M3'}]}
    assert PROVIDERS['ollama-cloud']['models'][1]['id'] == 'minimax-m2.7'  # the Border's entry is not changed


def test_anthropic_models_keep_the_built_in_api_key_provider(profiles, template):
    for model in (None, 'claude-sonnet-5', 'anthropic/claude-sonnet-5'):
        result, _ = profiles.load_member_spec(spec(model=model), template, installed=[], providers=PROVIDERS)
        assert result['provider'] is None and result['auth'] == 'api-key'
        assert profiles.spec_provider_entry(result, PROVIDERS) is None
    assert profiles.spec_model_binding(result, 'tier') == 'anthropic/claude-sonnet-5'
    result, _ = profiles.load_member_spec(spec(model=None), template, installed=[])
    assert profiles.spec_model_binding(result, 'claude-haiku-4-5-20251001') == 'anthropic/claude-haiku-4-5-20251001'


@pytest.mark.parametrize('changes,message', [
    (dict(model='nowhere/m1'), "provider 'nowhere' is not configured on the Border"),
    (dict(model='ollama-cloud/qwen3.5:9b'), "does not list model 'qwen3.5:9b' (it lists: minimax-m3, minimax-m2.7)"),
    (dict(model='llama-cpp/local'), 'starts a local service (localService)'),
    (dict(model='leaky/m1'), 'not a literal'),
    (dict(model='ollama-cloud/bad id'), 'the model id is not valid'),
    (dict(auth='oauth'), "auth must be 'api-key' (the default) or 'subscription'"),
    (dict(auth='subscription'), "auth 'subscription' needs a model"),
    (dict(auth='subscription', model='ollama-cloud/minimax-m3'), "model must be 'anthropic/<id>' or 'openai/<id>'"),
    (dict(auth='subscription', model='claude-sonnet-5'), "model must be 'anthropic/<id>' or 'openai/<id>'"),
])
def test_provider_errors(profiles, template, changes, message):
    with pytest.raises(profiles.MemberSpecError) as caught:
        profiles.load_member_spec(spec(**changes), template, installed=[], providers=PROVIDERS)
    assert message in str(caught.value)
    assert 'sk-literal-value' not in str(caught.value)  # literal secrets are named by path only


def test_without_border_providers_a_provider_model_is_refused(profiles, template):
    with pytest.raises(profiles.MemberSpecError, match="provider 'ollama-cloud' is not configured"):
        profiles.load_member_spec(spec(model='ollama-cloud/minimax-m3'), template, installed=[])


def test_subscription_models(profiles, template):
    for model, provider in (('openai/gpt-6.1-sol', 'openai'), ('anthropic/claude-sonnet-5', 'anthropic')):
        result, _ = profiles.load_member_spec(spec(model=model, auth='subscription'), template, installed=[],
                                              providers={})
        assert (result['provider'], result['auth']) == (provider, 'subscription')
        assert profiles.spec_model_binding(result, 'tier') == model
        assert profiles.spec_provider_entry(result, {}) is None


def test_env_slice_follows_the_provider(profiles, template):
    env = {'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY', 'OTHER_KEY', 'PFSENSE_URL', 'PFSENSE_API_KEY'}
    def keys(**changes):
        result, _ = profiles.load_member_spec(spec(**changes), template, installed=[], providers=PROVIDERS)
        return set(profiles.spec_env_slice_keys(result, env, template, PROVIDERS))
    cloud = keys(model='ollama-cloud/minimax-m3')
    assert 'OLLAMA_API_KEY' in cloud and not {'ANTHROPIC_API_KEY', 'OTHER_KEY'} & cloud
    assert 'ANTHROPIC_API_KEY' in keys(model=None) and 'OLLAMA_API_KEY' not in keys(model=None)
    sub = keys(model='openai/gpt-6.1-sol', auth='subscription')
    assert not {'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY', 'OTHER_KEY'} & sub
    assert {'PFSENSE_URL', 'PFSENSE_API_KEY'} <= cloud & sub  # server variables are unchanged


def border(tmp_path, env_text):
    path = tmp_path / '.openclaw'
    T184.border_with_pfsense(path, env_text)
    config = json.loads((path / 'openclaw.json').read_text())
    config['models'] = {'providers': PROVIDERS}
    (path / 'openclaw.json').write_text(json.dumps(config))
    return path


def provision(tmp_path, data):
    spec_file = tmp_path / 'investigator.json'
    spec_file.write_text(json.dumps(data))
    staged = T184.run_migrate(tmp_path, '--spec', str(spec_file), '--specs-only', '--hot', '')
    assert staged.returncode == 0, staged.stderr
    command = next(l.strip() for l in staged.stdout.splitlines() if 'in2n-member-home.py' in l)
    run = subprocess.run([sys.executable, *shlex.split(command)[1:]], env=clean_env(tmp_path),
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    envfile = tmp_path / 'stage/members/alert-investigator/.env'
    written = json.loads((tmp_path / '.openclaw-lab-alert-investigator/openclaw.json').read_text())
    staged_model = re.search(r'^N2N_MEMBER_MODEL=(\S+)\s*$', envfile.read_text(), re.M).group(1)
    return written, envfile, staged_model, run.stdout, command


def test_provider_member_end_to_end(tmp_path):
    border(tmp_path, 'ANTHROPIC_API_KEY=fixture\nOLLAMA_API_KEY=fixture\nOTHER_KEY=no\n'
                     'PFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    written, envfile, staged, out, _ = provision(tmp_path, spec(model='ollama-cloud/minimax-m3'))
    assert staged == 'ollama-cloud/minimax-m3'
    assert written['agents']['defaults']['model']['primary'] == staged and staged in written['agents']['defaults']['models']
    assert written['models']['providers'] == {'ollama-cloud': {**CLOUD, 'models': [CLOUD['models'][0]]}}
    keys = slice_keys(envfile)
    assert 'OLLAMA_API_KEY' in keys and not {'ANTHROPIC_API_KEY', 'OTHER_KEY'} & keys
    assert "the Border's ollama-cloud provider; OLLAMA_API_KEY: present" in out
    assert 'fixture' not in out


def test_subscription_member_end_to_end(tmp_path):
    border(tmp_path, 'ANTHROPIC_API_KEY=fixture\nOLLAMA_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    written, envfile, staged, out, _ = provision(tmp_path, spec(model='openai/gpt-6.1-sol', auth='subscription'))
    assert staged == 'openai/gpt-6.1-sol' and written['models']['providers'] == {}
    assert written['agents']['defaults']['model']['primary'] == 'openai/gpt-6.1-sol'
    assert not {'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY'} & slice_keys(envfile)
    home = tmp_path / '.openclaw-lab-alert-investigator'
    login = next(l.strip() for l in out.splitlines() if 'openclaw models auth login' in l)
    assert shlex.split(login.rstrip(')')) == [f'OPENCLAW_STATE_DIR={home}', f'OPENCLAW_CONFIG_PATH={home}/openclaw.json',
                                              'openclaw', 'models', 'auth', 'login', '--provider', 'openai']


def test_member_home_model_override_cannot_replace_a_provider_model(tmp_path):
    border(tmp_path, 'OLLAMA_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    spec_file = tmp_path / 'investigator.json'
    spec_file.write_text(json.dumps(spec(model='ollama-cloud/minimax-m3')))
    staged = T184.run_migrate(tmp_path, '--spec', str(spec_file), '--specs-only', '--hot', '')
    command = next(l.strip() for l in staged.stdout.splitlines() if 'in2n-member-home.py' in l)
    run = subprocess.run([sys.executable, *shlex.split(command)[1:], '--model', 'claude-sonnet-5'],
                         env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert run.returncode != 0 and '--model cannot override' in run.stderr
    assert not (tmp_path / '.openclaw-lab-alert-investigator/openclaw.json').exists()


def test_staged_member_runs_on_the_recorded_federation_runtime(tmp_path):
    """Found live: a member started with the system python3 lacked the federation runtime's
    packages (websockets, a current cryptography) and failed every task. run.sh now execs the
    n2n component's recorded interpreter, the one the mesh daemon runs on."""
    path = border(tmp_path, 'OLLAMA_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    spec_file = tmp_path / 'investigator.json'
    spec_file.write_text(json.dumps(spec(model='ollama-cloud/minimax-m3')))
    runner = tmp_path / 'stage/members/alert-investigator/run.sh'
    assert T184.run_migrate(tmp_path, '--spec', str(spec_file), '--specs-only', '--hot', '').returncode == 0
    assert shlex.split(runner.read_text().splitlines()[-1])[1] == 'python3'  # nothing recorded
    python = tmp_path / 'runtime dir/bin/python'
    python.parent.mkdir(parents=True)
    python.write_text('#!/bin/sh\n')
    python.chmod(0o755)
    (path / 'python-runtimes/records').mkdir(parents=True, exist_ok=True)
    (path / 'python-runtimes/records/n2n').write_text(f'{python}\n')
    assert T184.run_migrate(tmp_path, '--spec', str(spec_file), '--specs-only', '--hot', '').returncode == 0
    argv = shlex.split(runner.read_text().splitlines()[-1])
    assert argv[:2] == ['exec', str(python)] and argv[2].endswith('scripts/in2n-member.py')


@pytest.mark.parametrize('data', [dict(model='ollama-cloud/minimax-m3'),
                                  dict(model='openai/gpt-6.1-sol', auth='subscription'),
                                  dict(model='anthropic/claude-sonnet-5', auth='subscription')])
def test_member_home_validates_with_installed_openclaw(tmp_path, data):
    """When OpenClaw is installed: `openclaw config validate` accepts a provider member's home
    (the copied provider entry) and a subscription member's home (no provider entry, a built-in
    provider model as primary)."""
    import shutil
    dist = T184.openclaw_dist()
    cli = dist.parent / 'openclaw.mjs' if dist else None
    node = shutil.which('node')
    if not (cli and cli.is_file() and node):
        pytest.skip('OpenClaw is not installed globally')
    border(tmp_path, 'OLLAMA_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    provision(tmp_path, spec(**data))
    home = tmp_path / '.openclaw-lab-alert-investigator'
    env = {'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'HOME': str(tmp_path),
           'OPENCLAW_STATE_DIR': str(home), 'OPENCLAW_CONFIG_PATH': str(home / 'openclaw.json'),
           'OLLAMA_API_KEY': 'fixture'}
    result = subprocess.run([node, str(cli), 'config', 'validate'], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr


# ── Review round 1 ──

def providers_with(**entries):
    return {**PROVIDERS, **entries}


@pytest.mark.parametrize('entry,message', [
    ({**CLOUD, 'apiKey': {'source': 'file', 'provider': 'default', 'id': '/border/key'}}, 'file, exec and vault SecretRefs'),
    ({**CLOUD, 'apiKey': {'source': 'exec', 'provider': 'default', 'id': 'cat'}}, 'file, exec and vault SecretRefs'),
    ({**CLOUD, 'apiKey': 'sk-literal-value'}, 'not a literal'),
    ({**CLOUD, 'baseUrl': 'https://gw.example/v1?key=AIzaLITERAL'}, 'without credentials, query or fragment'),
    ({**CLOUD, 'baseUrl': 'https://user:pw@gw.example/v1'}, 'without credentials, query or fragment'),
    ({**CLOUD, 'baseUrl': 'ftp://gw.example'}, 'http(s) URL'),
    ({**CLOUD, 'baseUrl': 'https://${HOST}/v1'}, 'one ${NAME} reference or plain text'),
    ({**CLOUD, 'headers': {'X-Vendor-Key': 'LITERALVALUE'}}, "header 'X-Vendor-Key' must hold only"),
    ({**CLOUD, 'headers': {'X-Auth': '${TOKEN:-fallback}'}}, "header 'X-Auth' must hold only"),
    ({**CLOUD, 'request': {'proxy': 'http://p'}}, 'fields a member entry does not carry: request'),
    ({**CLOUD, 'headers': {'Authorization': 'Bearer ${SLACK_BOT_TOKEN}'}}, 'variables a member never receives: SLACK_BOT_TOKEN'),
    ({**CLOUD, 'apiKey': '${GAIT_DIR}'}, 'variables a member never receives: GAIT_DIR'),
    ({**CLOUD, 'timeoutSeconds': 'soon'}, 'timeoutSeconds'),
])
def test_provider_entry_is_built_from_allowed_fields_only(profiles, template, entry, message):
    with pytest.raises(profiles.MemberSpecError) as caught:
        profiles.load_member_spec(spec(model='edge/minimax-m3'), template, installed=[],
                                  providers=providers_with(edge=entry))
    assert message in str(caught.value)
    assert 'LITERAL' not in str(caught.value) and 'pw@' not in str(caught.value)


def test_provider_entry_keeps_references_env_secretref_and_whitelisted_model_keys(profiles, template):
    entry = {'api': 'openai-completions', 'baseUrl': '${EDGE_URL}', 'authHeader': True, 'timeoutSeconds': 120,
             'apiKey': {'source': 'env', 'provider': 'default', 'id': 'EDGE_KEY'},
             'headers': {'X-Org': '${EDGE_ORG}', 'Authorization': 'Bearer ${EDGE_TOKEN}'},
             'models': [{'id': 'vendor/model-1', 'name': 'M1', 'contextWindow': 1000, 'secret_note': 'x'},
                        {'id': 'other'}]}
    result, _ = profiles.load_member_spec(spec(model='edge/vendor/model-1'), template, installed=[],
                                          providers=providers_with(edge=entry))
    assert (result['provider'], result['model']) == ('edge', 'vendor/model-1')
    built = profiles.spec_provider_entry(result, providers_with(edge=entry))
    assert built['models'] == [{'id': 'vendor/model-1', 'name': 'M1', 'contextWindow': 1000}]
    assert built['apiKey'] == entry['apiKey'] and built['headers'] == entry['headers']
    env = {'EDGE_URL', 'EDGE_KEY', 'EDGE_ORG', 'EDGE_TOKEN', 'OLLAMA_API_KEY', 'ANTHROPIC_API_KEY'}
    keys = set(profiles.spec_env_slice_keys(result, env, template, providers_with(edge=entry)))
    assert {'EDGE_URL', 'EDGE_KEY', 'EDGE_ORG', 'EDGE_TOKEN'} <= keys
    assert not {'OLLAMA_API_KEY', 'ANTHROPIC_API_KEY'} & keys


def test_border_providers_named_like_built_ins(profiles, template):
    border = providers_with(anthropic={'api': 'anthropic-messages', 'baseUrl': 'https://proxy.example',
                                       'apiKey': '${PROXY_KEY}', 'models': [{'id': 'claude-sonnet-5'}]},
                            openai={'api': 'openai-responses', 'apiKey': '${OPENAI_API_KEY}',
                                    'models': [{'id': 'gpt-6.1-sol'}]})
    # api-key Anthropic specs keep NetClaw's built-in provider, never the Border's anthropic entry.
    result, _ = profiles.load_member_spec(spec(model='anthropic/claude-sonnet-5', auth='api-key'), template,
                                          installed=[], providers=border)
    assert result['provider'] is None and profiles.spec_provider_entry(result, border) is None
    # A Border openai entry is a provider like any other with api-key auth...
    result, _ = profiles.load_member_spec(spec(model='openai/gpt-6.1-sol'), template, installed=[], providers=border)
    assert result['provider'] == 'openai' and profiles.spec_provider_entry(result, border)['apiKey'] == '${OPENAI_API_KEY}'
    # ...and ignored for a subscription: no entry, no key.
    result, _ = profiles.load_member_spec(spec(model='openai/gpt-6.1-sol', auth='subscription'), template,
                                          installed=[], providers=border)
    assert profiles.spec_provider_entry(result, border) is None
    assert 'OPENAI_API_KEY' not in profiles.spec_env_slice_keys(result, {'OPENAI_API_KEY'}, template, border)
    with pytest.raises(profiles.MemberSpecError, match="provider 'Anthropic' is not configured"):
        profiles.load_member_spec(spec(model='Anthropic/claude-sonnet-5'), template, installed=[], providers=border)


def test_member_home_refuses_model_override_for_every_spec(tmp_path):
    border(tmp_path, 'ANTHROPIC_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    spec_file = tmp_path / 'investigator.json'
    spec_file.write_text(json.dumps(spec(model=None)))
    staged = T184.run_migrate(tmp_path, '--spec', str(spec_file), '--specs-only', '--hot', '')
    command = next(l.strip() for l in staged.stdout.splitlines() if 'in2n-member-home.py' in l)
    run = subprocess.run([sys.executable, *shlex.split(command)[1:], '--model', 'claude-opus-x'],
                         env=clean_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert run.returncode != 0 and "--model cannot override a member spec's model" in run.stderr


def test_member_record_names_provider_and_auth_and_export_lines_count(tmp_path):
    border(tmp_path, 'OLLAMA_API_KEY=fixture\nPFSENSE_URL=https://fw\nPFSENSE_API_KEY=k\n')
    written, envfile, staged, out, command = provision(tmp_path, spec(model='ollama-cloud/minimax-m3'))
    record = json.loads((tmp_path / '.openclaw-lab-alert-investigator/netclaw-member-spec.json').read_text())
    assert (record['provider'], record['model'], record['auth']) == ('ollama-cloud', 'minimax-m3', 'api-key')
    member_home = T184.load(ROOT / 'scripts/in2n-member-home.py', 'spec185_member_home')
    exported = tmp_path / 'exported.env'
    exported.write_text('export OLLAMA_API_KEY=x\n  OTHER = y\n# COMMENTED=z\n')
    assert member_home._env_names(exported) == {'OLLAMA_API_KEY', 'OTHER'}
