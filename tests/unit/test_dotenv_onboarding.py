"""Checkout-to-runtime credential handoff without real credentials or services."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
IMPORTER = ROOT / 'scripts/import-env.py'
spec = importlib.util.spec_from_file_location('env_import', IMPORTER)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def cli(source, target, *args):
    return subprocess.run([sys.executable, str(IMPORTER), '--source', str(source),
                           '--target', str(target), *args], text=True, capture_output=True)


def test_preview_apply_precedence_private_and_idempotent(tmp_path):
    source, target = tmp_path / 'checkout.env', tmp_path / 'state with spaces/.env'
    target.parent.mkdir()
    original = b'# keep comment\r\nNETBOX_TOKEN=runtime-secret\r\nNETBOX_URL=\r\nOTHER=untouched'
    target.write_bytes(original)
    source.write_text('ANTHROPIC_API_KEY=fixture-provider\nNETBOX_TOKEN=checkout-secret\nNETBOX_URL=https://filled.example\n')
    preview = cli(source, target)
    assert preview.returncode == 0
    assert target.read_bytes() == original
    applied = cli(source, target, '--apply')
    assert applied.returncode == 0
    assert target.read_bytes().startswith(original + b'\n')
    assert dotenv_values(target, interpolate=False)['ANTHROPIC_API_KEY'] == 'fixture-provider'
    assert dotenv_values(target, interpolate=False)['NETBOX_TOKEN'] == 'runtime-secret'
    assert dotenv_values(target, interpolate=False)['NETBOX_URL'] == ''
    assert target.stat().st_mode & 0o777 == 0o600
    assert 'conflicts): NETBOX_TOKEN, NETBOX_URL' in applied.stdout
    after, mtime = target.read_bytes(), target.stat().st_mtime_ns
    assert cli(source, target, '--apply').returncode == 0
    assert (target.read_bytes(), target.stat().st_mtime_ns) == (after, mtime)
    for value in ('fixture-provider', 'runtime-secret', 'checkout-secret', 'https://filled.example'):
        assert value not in preview.stdout + preview.stderr + applied.stdout + applied.stderr


@pytest.mark.parametrize('assignment,expected', [
    ('export NETBOX_TOKEN="space & | ; `false` $(false) ${HOME} # literal" # comment',
     'space & | ; `false` $(false) ${HOME} # literal'),
    ("NETBOX_TOKEN='literal \\path $HOME'", 'literal \\path $HOME'),
    ('NETBOX_TOKEN=token # inline comment', 'token'),
    ('NETBOX_TOKEN=one two', 'one two'),
    ('NETBOX_TOKEN="escaped \\"quote\\""', 'escaped "quote"'),
])
def test_literal_dotenv_syntax(tmp_path, assignment, expected):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.write_text(assignment + '\n')
    result = cli(source, target, '--apply')
    assert result.returncode == 0, result.stderr
    assert target.read_text() == assignment + '\n'
    assert dotenv_values(target, interpolate=False)['NETBOX_TOKEN'] == expected


def test_never_executes_dotenv_or_promotes_arbitrary_host_controls(tmp_path):
    source, target, marker = tmp_path / 'source', tmp_path / 'target', tmp_path / 'executed'
    source.write_text(f'NETBOX_TOKEN="$(touch {marker})"\nPATH=/hostile\nNODE_OPTIONS=--hostile\nBASH_ENV=/hostile\n')
    result = cli(source, target, '--apply')
    assert result.returncode == 0
    assert not marker.exists()
    assert set(dotenv_values(target, interpolate=False)) == {'NETBOX_TOKEN'}
    assert 'Skipped undeclared names' in result.stdout
    assert '/hostile' not in result.stdout + result.stderr


@pytest.mark.parametrize('body', ['ANTHROPIC_API_KEY="unterminated-secret',
    'ANTHROPIC_API_KEY="multi\nline"', 'echo hidden-secret', 'ANTHROPIC_API_KEY=secret\0'])
def test_malformed_input_never_partially_imports_or_leaks(tmp_path, body):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.write_text('NETBOX_TOKEN=valid-secret\n' + body + '\n')
    target.write_text('ORIGINAL=keep\n')
    result = cli(source, target, '--apply')
    assert result.returncode != 0
    assert target.read_text() == 'ORIGINAL=keep\n'
    assert 'secret' not in result.stdout + result.stderr


@pytest.mark.parametrize('where', ['source', 'target'])
def test_refuses_symlinks_and_directories(tmp_path, where):
    source, target, other = tmp_path / 'source', tmp_path / 'target', tmp_path / 'other'
    source.write_text('ANTHROPIC_API_KEY=dummy\n')
    target.write_text('OTHER=keep\n')
    other.write_text('PRIVATE=untouched\n')
    path = source if where == 'source' else target
    path.unlink()
    path.symlink_to(other)
    assert cli(source, target, '--apply').returncode != 0
    assert other.read_text() == 'PRIVATE=untouched\n'
    path.unlink()
    path.mkdir()
    assert cli(source, target, '--apply').returncode != 0


def test_missing_source_blanks_placeholders_and_last_assignment(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    assert cli(source, target, '--apply').returncode == 0
    assert not target.exists()
    source.write_text('ANTHROPIC_API_KEY=sk-ant-...\nNETCLAW_PASSWORD=changeme\nNETBOX_TOKEN=your_token\n'
                      'OPENAI_API_KEY=\nNETBOX_URL="" # empty\nNETCLAW_USERNAME=first\nexport NETCLAW_USERNAME=last\n')
    result = cli(source, target, '--apply')
    assert result.returncode == 0
    assert dotenv_values(target, interpolate=False) == {'NETCLAW_USERNAME': 'last'}
    assert 'Skipped template placeholders' in result.stdout
    assert 'Skipped blank values' in result.stdout


def run_onboard(tmp_path, runtime='openclaw', failure=False, configured=False, malformed=False):
    repo, state, home = tmp_path / 'checkout with spaces', tmp_path / 'state with spaces', tmp_path / 'home'
    for path in (repo, state, home):
        path.mkdir()
    (repo / '.env').write_text('ANTHROPIC_API_KEY=fixture-provider\nNETBOX_TOKEN=fixture-network\n' + ('invalid-secret\n' if malformed else ''))
    config = state / ('config.yaml' if runtime == 'hermes' else 'custom.json')
    if configured:
        config.write_text('# operator config' if runtime == 'hermes' else '{"operator":"preserve"}')
    if runtime == 'hermes':
        (state / '.env').write_text('ANTHROPIC_API_KEY=fixture-selected-provider\nNETBOX_TOKEN=fixture-selected-network\n')
        (state / '.env').chmod(0o600)
    marker = tmp_path / 'wizard-ran'
    # Stub executable verifies the durable handoff at wizard launch (not just shell env).
    binary = tmp_path / runtime
    binary.write_text(f'''#!/bin/bash
set -eu
test -f "$FIXTURE_STATE/.env"
grep -q '^ANTHROPIC_API_KEY=fixture-{'selected-' if runtime == 'hermes' else ''}provider$' "$FIXTURE_STATE/.env"
grep -q '^NETBOX_TOKEN=fixture-{'selected-' if runtime == 'hermes' else ''}network$' "$FIXTURE_STATE/.env"
if [ "$1" = onboard ]; then
    test "$OPENCLAW_STATE_DIR" = "$FIXTURE_STATE"
    test "$OPENCLAW_CONFIG_PATH" = "$FIXTURE_CONFIG"
    test "$2" = --install-daemon
fi
touch "$FIXTURE_MARKER"
exit {23 if failure else 0}
''')
    binary.chmod(0o700)
    env = {'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'], 'HOME': str(home),
           'NETCLAW_DIR': str(repo), 'NETCLAW_RUNTIME': runtime, 'OPENCLAW_STATE_DIR': str(state),
           'OPENCLAW_CONFIG_PATH': str(config), 'HERMES_HOME': str(state),
           'FIXTURE_STATE': str(state), 'FIXTURE_CONFIG': str(config), 'FIXTURE_MARKER': str(marker)}
    # Absolute sources; caller cwd is unrelated to both the checkout and runtime.
    result = subprocess.run(['bash', '-c', f'set -euo pipefail; source "{ROOT}/scripts/lib/common.sh"; source "{ROOT}/scripts/lib/install-steps.sh"; core_onboard'],
                            cwd=home, env=env, text=True, capture_output=True)
    return result, state, config, marker


@pytest.mark.parametrize('runtime', ['openclaw', 'hermes'])
def test_onboard_receives_import_before_wizard_from_any_cwd(tmp_path, runtime):
    result, state, _, marker = run_onboard(tmp_path, runtime)
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.exists()
    if runtime == 'hermes':
        assert dotenv_values(state / '.env')['ANTHROPIC_API_KEY'] == 'fixture-selected-provider'
    assert (state / '.env').stat().st_mode & 0o777 == 0o600
    assert 'fixture-provider' not in result.stdout + result.stderr


@pytest.mark.parametrize('runtime', ['openclaw', 'hermes'])
def test_existing_config_skips_wizard_but_imports_missing_settings(tmp_path, runtime):
    result, state, config, marker = run_onboard(tmp_path, runtime, configured=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists()
    assert 'preserve' in config.read_text() or config.read_text() == '# operator config'
    assert 'ANTHROPIC_API_KEY' in dotenv_values(state / '.env')


@pytest.mark.parametrize('runtime', ['openclaw', 'hermes'])
def test_wizard_failure_is_not_success(tmp_path, runtime):
    result, _, _, marker = run_onboard(tmp_path, runtime, failure=True)
    assert marker.exists()
    assert result.returncode != 0
    assert 'onboarding is incomplete' in result.stdout
    assert 'onboard complete' not in result.stdout and 'setup complete' not in result.stdout


def test_bad_import_prevents_wizard(tmp_path):
    result, state, _, marker = run_onboard(tmp_path, malformed=True)
    assert result.returncode != 0
    assert not marker.exists() and not (state / '.env').exists()
    assert 'invalid-secret' not in result.stdout + result.stderr


@pytest.mark.parametrize('runtime,env_name', [('openclaw', 'OPENCLAW_STATE_DIR'), ('hermes', 'HERMES_HOME'), ('openclaw', 'OPENCLAW_HOME')])
def test_standalone_runtime_path_selection(tmp_path, runtime, env_name):
    source, state = tmp_path / 'source', tmp_path / 'state'
    source.write_text('ANTHROPIC_API_KEY=fixture-provider\n')
    result = subprocess.run([sys.executable, str(IMPORTER), '--source', str(source), '--runtime', runtime, '--apply'],
                            env={'HOME': str(tmp_path), env_name: str(state)}, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (state / '.env').is_file()


def test_platform_setup_imports_before_its_first_question(tmp_path):
    scripts, state = tmp_path / 'scripts', tmp_path / 'state'
    scripts.mkdir()
    state.mkdir()
    (scripts / 'setup.sh').write_text((ROOT / 'scripts/setup.sh').read_text())
    (scripts / 'lib').symlink_to(ROOT / 'scripts/lib', target_is_directory=True)
    (scripts / 'import-env.py').symlink_to(IMPORTER)
    (tmp_path / '.env').write_text('NETBOX_TOKEN=fixture-network\n')
    result = subprocess.run(['bash', str(scripts / 'setup.sh')], cwd=state,
                            env={'HOME': str(tmp_path), 'PATH': os.environ['PATH'], 'OPENCLAW_STATE_DIR': str(state)},
                            stdin=subprocess.DEVNULL, capture_output=True, text=True)
    # EOF at the first question exits setup; import must have already happened.
    assert 'NetClaw Platform Setup' in result.stdout
    assert dotenv_values(state / '.env')['NETBOX_TOKEN'] == 'fixture-network'
    assert 'fixture-network' not in result.stdout + result.stderr
