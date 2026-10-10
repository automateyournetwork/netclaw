"""Actual installer CLI control flow with package/service effects substituted."""
import os
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('failure', ['component', 'verification', 'tokens', 'swallowed-pip', 'none'])
def test_cli_failure_is_visible_to_automation(tmp_path, failure):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (scripts / 'lib').symlink_to(ROOT / 'scripts/lib', target_is_directory=True)
    (tmp_path / 'workspace/skills/example').mkdir(parents=True)
    (tmp_path / 'mcp-servers/pyATS_MCP').mkdir(parents=True)
    if failure != 'verification':
        (tmp_path / 'mcp-servers/pyATS_MCP/pyats_mcp_server.py').touch()
    # Host checks have their own entrypoint suite; isolate downstream exit handling.
    (scripts / 'installer-preflight.py').write_text('raise SystemExit(0)\n')
    (scripts / 'mcp-call.py').touch()
    (scripts / 'netclaw').write_text('#!/bin/sh\nexit 0\n')
    (scripts / 'netclaw').chmod(0o700)
    source = (ROOT / 'scripts/install.sh').read_text()
    source = source.replace('core_prereqs\ncore_runtime\ncore_onboard\ncore_gateway_check\ncore_mcpdir', '''
core_prereqs() { :; }
core_runtime() { :; }
core_onboard() { :; }
core_gateway_check() { :; }
core_mcpdir() { :; }
core_deploy() { :; }
core_tokens() { [ "$FIXTURE_FAILURE" != tokens ]; }
component_install_pyats() {
    if [ "$FIXTURE_FAILURE" = swallowed-pip ]; then
        ( _netclaw_pip_install() { return 23; }; netclaw_pip_install example ) || true
    fi
    [ "$FIXTURE_FAILURE" != component ]
}
''')
    (scripts / 'install.sh').write_text(source)
    result = subprocess.run(['bash', str(scripts / 'install.sh'), '--components', 'pyats'],
        env={**os.environ, 'OPENCLAW_HOME': str(tmp_path / 'runtime'),
             'FIXTURE_FAILURE': failure, 'NETCLAW_MANIFEST': str(tmp_path / 'manifest')},
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) == (failure == 'none'), result.stdout + result.stderr
    if failure in ('component', 'swallowed-pip'):
        assert 'installation failed; artifact verification skipped' in result.stdout
        assert 'Cisco pyATS: OK' not in result.stdout


def test_core_tokens_propagates_package_failure(tmp_path):
    (tmp_path / 'src/netclaw_tokens').mkdir(parents=True)
    result = subprocess.run(['bash', '-c', '''
source scripts/lib/common.sh
source scripts/lib/install-steps.sh
NETCLAW_DIR="$FIXTURE_REPO"
netclaw_pip_install() { return 23; }
core_tokens
'''], cwd=ROOT, env={**os.environ, 'FIXTURE_REPO': str(tmp_path)}, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'library ready' not in result.stdout
