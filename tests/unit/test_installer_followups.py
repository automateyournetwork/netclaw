"""Regression coverage for installer feedback; no real installs or operator config."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load('runtime-policy')
launch = load('component-launch')
register = load('install-mcp-config')


@pytest.mark.parametrize('value,ok', [('18.20.8', False), ('20.20.2', False), ('22.22.0', False),
    ('24.15.9', False), ('24.16.0', True), ('v24.19.0', True), ('25.9.0', False),
    ('26.0.9', False), ('26.1.0', True), ('26.11.0', True), ('26.1.0-rc.1', False), ('garbage', False)])
def test_openclaw_node_boundaries(value, ok):
    assert policy.node_supported(value) is ok


def test_hermes_does_not_inherit_openclaw_floor():
    assert policy.node_supported('22.0.0', 'hermes')


@pytest.mark.parametrize('version,flag', [('10.9.0',False),('11.15.9',False),('11.16.0',True),('12.0.0',True)])
def test_npm_script_policy(version, flag):
    args = policy.npm_args(version)
    assert ('--allow-scripts=openclaw' in args) is flag
    assert not any('koffi' in arg or '=all' in arg for arg in args)


def test_all_reported_components_registered():
    templates = json.loads((ROOT / 'config/openclaw.json').read_text())['mcpServers']
    assert len(launch.CONTRACT) == 13
    for component, rule in launch.CONTRACT.items():
        if rule.get('access') == 'hud-private':
            assert component == 'hermes-hud'
            assert all(name not in templates for name in rule['servers'])
            continue
        for server in rule['servers']:
            entry = templates[server]
            assert register.component_for(server) == component
            assert entry['transport'] == 'stdio'
            assert entry['args'][1:3] == ['scripts/component-launch.py', component]
            assert not any(k in entry for k in ('approval','autoApprove','toolFilter'))


def make_runtime(tmp_path, component):
    runtime = tmp_path / 'runtimes'
    record = runtime / 'records' / component
    record.parent.mkdir(parents=True, exist_ok=True)
    python = tmp_path / 'component/bin/python'
    python.parent.mkdir(parents=True, exist_ok=True)
    python.symlink_to(sys.executable)
    record.write_text(str(python))
    return runtime, python


@pytest.fixture
def netbox_repo(tmp_path):
    # Optional component clones are absent on a clean checkout/CI runner.
    # Keep launcher tests independent of the developer's installed components.
    repo = tmp_path / 'repo'
    script = repo / launch.CONTRACT['netbox']['script']
    script.parent.mkdir(parents=True)
    script.write_text('')
    return repo


def test_netbox_module_uses_record_and_source_not_gateway_path(tmp_path, netbox_repo):
    runtime, python = make_runtime(tmp_path, 'netbox')
    env = {'NETCLAW_RUNTIME_ROOT': str(runtime), 'PATH': '/wrong/python/bin', 'NETBOX_TOKEN': 'fixture'}
    parts, child_env, cwd = launch.resolve('netbox', env=env, repo=netbox_repo)
    assert parts == [str(python), '-u', '-m', 'netbox_mcp_server.server', '--transport', 'stdio']
    assert child_env['PYTHONPATH'] == str(netbox_repo / 'mcp-servers/netbox-mcp-server/src')
    assert child_env['NETBOX_TOKEN'] == 'fixture'
    assert cwd == str(netbox_repo)


def test_missing_record_fails_instead_of_global_fallback(tmp_path, netbox_repo):
    with pytest.raises(ValueError, match='interpreter record'):
        launch.resolve('netbox', env={'NETCLAW_RUNTIME_ROOT':str(tmp_path / 'runtimes')}, repo=netbox_repo)


def test_literal_env_precedence_and_custom_script_preserved(tmp_path):
    runtime, python = make_runtime(tmp_path, 'netbox')
    custom = tmp_path / 'custom.py'; custom.write_text('')
    (tmp_path / '.env').write_text('NETBOX_TOKEN="$(do-not-execute)"\nNETBOX_URL="https://fixture.invalid"\n')
    parts, env, _ = launch.resolve('netbox', env={'NETCLAW_RUNTIME_ROOT':str(runtime),
        'NETBOX_TOKEN':'explicit', 'NETBOX_MCP_SCRIPT':str(custom)})
    assert parts[:3] == [str(python), '-u', str(custom)]
    assert env['NETBOX_TOKEN'] == 'explicit'
    assert env['NETBOX_URL'] == 'https://fixture.invalid'


def test_legacy_skill_matches_only_owned_invocations():
    cmd=['python3','-u',str(ROOT/'mcp-servers/netbox-mcp-server/src/netbox_mcp_server/server.py')]
    assert launch.legacy_component(cmd,{}) == ('netbox','netbox-mcp')
    assert launch.legacy_component(['python3','/operator/custom.py'],{}) is None


def test_generated_entries_carry_runtime_location_without_credentials(tmp_path):
    out=tmp_path/'selected.json'
    result=subprocess.run([sys.executable,str(ROOT/'scripts/install-mcp-config.py'), '--repo',str(ROOT),
        '--runtime-root',str(tmp_path/'runtimes'),'--components',' '.join(launch.CONTRACT), '--output',str(out)],
        capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    entries=json.loads(out.read_text())['mcpServers']
    assert len(entries)==13
    for entry in entries.values():
        assert Path(entry['command']).is_absolute()
        assert entry['env']['NETCLAW_RUNTIME_ROOT']==str(tmp_path/'runtimes')
        assert set(entry['env'])=={'NETCLAW_RUNTIME_ROOT','NETCLAW_RUNTIME_ENV'}


@pytest.mark.parametrize('npm_rc,version_rc,expected', [(0,0,0),(1,0,1),(0,1,1)])
def test_npm_failure_and_executable_check_propagate(tmp_path,npm_rc,version_rc,expected):
    bin_dir=tmp_path/'bin';bin_dir.mkdir()
    for name,body in {
        'node':'echo v24.16.0',
        'npm':f'case "$1" in --version) echo 12.0.0;; config) echo "{tmp_path}";; *) printf "%s\\n" "$@" > "{tmp_path}/args"; exit {npm_rc};; esac',
        'openclaw':f'exit {version_rc}',
        'sudo':'exit 99',
    }.items():
        p=bin_dir/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o700)
    env={**os.environ,'PATH':str(bin_dir)+os.pathsep+os.environ['PATH'],'HOME':str(tmp_path),'NETCLAW_DIR':str(ROOT)}
    cmd='source scripts/lib/runtime-install.sh\nlog_info() { :; }; log_error() { :; }; netclaw_install_openclaw'
    r=subprocess.run(['bash','-c',cmd],cwd=ROOT,env=env,capture_output=True,text=True)
    assert r.returncode==expected,r.stdout+r.stderr
    assert '--allow-scripts=openclaw' in (tmp_path/'args').read_text()
