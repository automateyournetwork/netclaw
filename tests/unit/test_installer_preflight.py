"""Offline host fixtures and entrypoint checks; never install operator runtimes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('installer_preflight', ROOT / 'scripts/installer-preflight.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
POLICY, CATALOG = module.load_policy()


class FixtureHost:
    def __init__(self, version=(3, 12), system='Darwin', arch='arm64', commands=()):
        self.env = {}
        self.commands = set(POLICY['core_commands']) | {'python3'} | set(commands)
        self.python_info = {'version': version, 'os': system, 'arch': arch, 'venv': True,
                            'ensurepip': True, 'isolated': True, 'libc': ['glibc','2.36']}
        self.outputs = {('node', '--version'): 'v24.16.0', ('go', 'version'): 'go version go1.25.1 darwin/arm64',
            ('go', 'env', 'CGO_ENABLED'): '1', ('go', 'env', 'CC'): 'clang',
            ('xcode-select', '-p'): '/fixture/CommandLineTools',
            ('docker', 'info', '--format', '{{.ServerVersion}}'): '28.0.0'}
        self.calls = []

    def command(self, name):
        return name if name in self.commands else None

    def python(self, executable):
        return self.python_info if executable else None

    def output(self, args):
        self.calls.append(tuple(args))
        return self.outputs.get(tuple(args))


def evaluate(selected, host=None, system='Darwin', arch='arm64', **kwargs):
    return module.evaluate(POLICY, selected.split(), system, arch, 'component-python',
                           host or FixtureHost(), module.launch_commands(), **kwargs)


def messages(report):
    return '\n'.join(report['core_errors'] + [m for r in report['components'] for m in r['errors']])


def test_policy_and_derived_launcher_coverage():
    assert POLICY['components'].keys() <= CATALOG
    assert 'computer-use' in CATALOG
    commands = module.launch_commands()
    assert commands['aws'] == {'uvx'}
    assert commands['github'] == {'docker'}
    assert commands.keys() <= CATALOG
    report = evaluate(' '.join(CATALOG), FixtureHost(commands={'uv', 'uvx', 'docker', 'kubectl', 'tshark', 'nmap', 'ollama', 'go', 'clang'}))
    assert len(report['components']) == len(CATALOG)


@pytest.mark.parametrize('system,arch,ok', [('Darwin','arm64',True), ('Linux','x86_64',True), ('FreeBSD','x86_64',False)])
def test_host_platforms(system, arch, ok):
    assert evaluate('subnet-calc', system=system, arch=arch)['ok'] == ok


@pytest.mark.parametrize('component,version,ok', [
    ('panorama',(3,12),True), ('panorama',(3,13),False), ('panorama',(3,14),False),
    ('zoom-rtms',(3,13),True), ('zoom-rtms',(3,14),False),
    ('memory-mcp',(3,10),False), ('memory-mcp',(3,11),True),
    ('cml',(3,11),False), ('cml',(3,12),True), ('zabbix',(3,14),True), ('zabbix',(3,9),False),
])
def test_component_python_bounds(component, version, ok):
    report = evaluate(component, FixtureHost(version=version))
    assert report['ok'] == ok, messages(report)
    if not ok:
        assert 'Python' in messages(report)


@pytest.mark.parametrize('system,host_arch,python_arch,ok', [
    ('Darwin','arm64','arm64',True), ('Darwin','x86_64','x86_64',False),
    ('Darwin','arm64','x86_64',False), ('Linux','x86_64','x86_64',True),
    ('Linux','aarch64','aarch64',False),
])
def test_zoom_native_sdk_architecture(system, host_arch, python_arch, ok):
    host = FixtureHost(system=system, arch=python_arch)
    assert evaluate('zoom-rtms', host, system, host_arch)['ok'] == ok


@pytest.mark.parametrize('component,command', [('pyats','uv'), ('gait','uv'), ('aws','uvx'),
    ('github','docker'), ('nsm','docker'), ('batfish','docker'), ('kubeshark','kubectl'),
    ('packet-buddy','tshark'), ('ollama','ollama'), ('nmap','nmap')])
def test_selected_command_requirements(component, command):
    report = evaluate(component)
    assert not report['ok']
    assert command in messages(report)
    ready = evaluate(component, FixtureHost(commands={command}))
    assert ready['ok'], messages(ready)


def test_missing_unselected_tools_and_optional_tools_do_not_block():
    host = FixtureHost()
    assert evaluate('netbox', host)['ok']
    assert not any(c[0] in ('go','docker') for c in host.calls)
    report = evaluate('packet-buddy', FixtureHost(commands={'tshark'}))
    assert report['ok']
    assert 'capinfos' in report['components'][0]['warnings'][0]


@pytest.mark.parametrize('go,ok', [('go version go1.24.9 darwin/arm64',False),
    ('go version go1.25.1 darwin/arm64',True), ('go version go2.0.0 linux/amd64',True), ('invalid',False)])
def test_forward_go_versions(go, ok):
    host = FixtureHost(commands={'go','clang'})
    host.outputs[('go','version')] = go
    assert evaluate('forward', host)['ok'] == ok


@pytest.mark.parametrize('failure', ['missing-go','cgo','compiler','xcode'])
def test_forward_build_prerequisites(failure):
    host = FixtureHost(commands={'go','clang'})
    if failure == 'missing-go': host.commands.remove('go')
    if failure == 'cgo': host.outputs[('go','env','CGO_ENABLED')] = '0'
    if failure == 'compiler': host.commands.remove('clang')
    if failure == 'xcode': host.outputs[('xcode-select','-p')] = None
    assert not evaluate('forward', host)['ok']


def test_docker_daemon_readiness_and_selection_isolation():
    host = FixtureHost(commands={'docker'})
    host.outputs[('docker','info','--format','{{.ServerVersion}}')] = None
    assert 'daemon unavailable' in messages(evaluate('github', host))
    assert evaluate('netbox', host)['ok']


def test_aggregate_blockers_and_supported_linux_desktop():
    report = evaluate('forward panorama zoom-rtms computer-use', FixtureHost(version=(3,14)))
    assert all(row['errors'] for row in report['components'])
    assert evaluate('computer-use', system='Linux', arch='x86_64')['ok']


def test_vendor_sdk_source_config_and_no_secret_disclosure(tmp_path):
    host = FixtureHost()
    assert 'SDK is hosted' in messages(evaluate('radkit', host))
    host.env['PIP_EXTRA_INDEX_URL'] = 'https://user:fixture-secret@radkit.cisco.com/pip/'
    report = evaluate('radkit', host)
    assert report['ok']
    assert 'fixture-secret' not in json.dumps(report)
    host.env = {'PIP_FIND_LINKS': str(tmp_path)}
    assert not evaluate('radkit', host)['ok']
    (tmp_path/'cisco_radkit_client-1.9.0-py3-none-any.whl').touch()
    assert evaluate('radkit', host)['ok']


def test_explicit_venv_is_checked_instead_of_base():
    host = FixtureHost(version=(3,14))
    host.outputs[('/operator/venv/bin/python','-m','pip','--version')] = 'pip 25'
    report = evaluate('panorama', host, explicit_venv='/operator/venv')
    assert not report['ok']
    assert report['python'] == '/operator/venv/bin/python'


def test_explicit_venv_cannot_alias_system_python():
    host = FixtureHost()
    host.python_info['isolated'] = False
    host.outputs[('/operator/venv/bin/python','-m','pip','--version')] = 'pip 25'
    assert 'refusing system Python' in messages(evaluate('zabbix', host, explicit_venv='/operator/venv'))


@pytest.mark.parametrize('libc,value,ok', [('glibc','2.34',True), ('glibc','2.33',False),
    ('musl','1.2.5',False), ('','',False)])
def test_zoom_linux_native_wheel_libc_requirement(libc, value, ok):
    host = FixtureHost(system='Linux',arch='x86_64')
    host.python_info['libc'] = [libc,value]
    assert evaluate('zoom-rtms',host,'Linux','x86_64')['ok'] == ok


def test_probe_timeout_and_go_cannot_download_toolchains(monkeypatch):
    def timeout(*args, **kwargs):
        assert kwargs['env']['GOTOOLCHAIN'] == 'local'
        assert kwargs['stdin'] == subprocess.DEVNULL
        assert kwargs['timeout'] == 5
        raise subprocess.TimeoutExpired('fixture', 5)
    monkeypatch.setattr(subprocess, 'run', timeout)
    assert module.Host().output(['go','version']) is None


def executable(path, body):
    path.write_text('#!/bin/sh\n' + body)
    path.chmod(0o700)


@pytest.mark.parametrize('preflight,component,ok', [(True,'subnet-calc',True),
    (True,'computer-use',False), (False,'computer-use',False)])
def test_installer_preflight_never_writes_operator_state(tmp_path, preflight, component, ok):
    bin_dir = tmp_path/'bin'; bin_dir.mkdir()
    (bin_dir/'python3').symlink_to(sys.executable)
    for name in ('node','npm','npx'):
        executable(bin_dir/name, 'if [ "$1" = --version ]; then echo v24.16.0; exit 0; fi\necho unexpected-install >&2\nexit 42\n')
    executable(bin_dir/'uname', 'case "$1" in -s) echo Darwin;; -m) echo arm64;; -r) echo fixture;; esac\n')
    args = ['/bin/bash','scripts/install.sh','--runtime','hermes','--components',component]
    if preflight: args.append('--preflight')
    result = subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=15,
        env={**os.environ,'PATH':str(bin_dir)+':'+os.environ['PATH'], 'NETCLAW_PY':sys.executable,
             'HERMES_HOME':str(tmp_path/'hermes'),'OPENCLAW_HOME':str(tmp_path/'openclaw')})
    assert (result.returncode == 0) == ok, result.stdout + result.stderr
    assert 'Host: Darwin' in result.stdout
    assert 'unexpected-install' not in result.stderr
    assert not (tmp_path/'hermes').exists()
    assert not (tmp_path/'openclaw').exists()
    assert 'Checking prerequisites...' not in result.stdout


@pytest.mark.parametrize('explicit', [False, True])
def test_prefer_existing_python312_but_preserve_explicit_override(tmp_path, explicit):
    executable(tmp_path/'python3.12', 'exit 0\n')
    result = subprocess.run(['/bin/bash','-c', '''set -eu
source scripts/lib/preflight.sh
NETCLAW_PY=operator-python
netclaw_choose_component_python
echo "$NETCLAW_PY"
'''],cwd=ROOT,capture_output=True,text=True,env={**os.environ,
        'PATH':str(tmp_path)+':'+os.environ['PATH'],'NETCLAW_PY_EXPLICIT':str(int(explicit))})
    assert result.returncode == 0
    assert result.stdout.strip() == ('operator-python' if explicit else str(tmp_path/'python3.12'))


def test_picker_disables_unsupported_rows(tmp_path):
    source=(ROOT/'scripts/install.sh').read_text()
    function=source[source.index('build_checklist() {'):source.index('\nselect_runtime() {')]
    result=subprocess.run(['/bin/bash','-c','''set -eu
source scripts/lib/preflight.sh
source scripts/lib/catalog.sh
NETCLAW_UNSUPPORTED_COMPONENTS='computer-use|requires Linux'
''' + function + '''
build_checklist computer-use
printf '%s\n' "${CL_IDS[@]}"
printf '%s\n' "${CL_LABELS[@]}" >&2
'''],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert 'computer-use' not in result.stdout.splitlines()
    assert 'unavailable: requires Linux' in result.stderr


def test_run_logs_do_not_reuse_previous_component_errors(tmp_path):
    source=(ROOT/'scripts/install.sh').read_text()
    setup=source[source.index('INSTALL_LOG_ROOT='):source.index('\nNETCLAW_RUNTIME_ROOT=')]
    result=subprocess.run(['/bin/bash','-c','''set -eu
source scripts/lib/common.sh
NETCLAW_OS=Darwin NETCLAW_ARCH=arm64 NETCLAW_OS_VERSION=15
NETCLAW_PY=fixture SELECTED=jev
''' + setup + '''
first="$INSTALL_LOG_DIR"
echo old-failure > "$first/jev.log"
''' + setup + '''
test "$INSTALL_LOG_DIR" != "$first"
test ! -e "$INSTALL_LOG_DIR/jev.log"
test -f "$INSTALL_LOG_DIR/run-info.txt"
'''],cwd=ROOT,capture_output=True,text=True,env={**os.environ,'OPENCLAW_HOME':str(tmp_path)})
    assert result.returncode == 0, result.stdout + result.stderr


def test_zabbix_relative_vendor_requirement_resolves_from_component(tmp_path):
    source=tmp_path/'mcp-servers/zabbix-mcp'
    (source/'vendor/zabbix-mcp-server').mkdir(parents=True)
    (source/'requirements.txt').write_text('./vendor/zabbix-mcp-server\n')
    result=subprocess.run(['/bin/bash','-c','''set -eu
source scripts/lib/common.sh
source scripts/lib/install-steps.sh
netclaw_component_venv() { NETCLAW_COMPONENT_VENV="$FIXTURE_ROOT/runtime"; }
netclaw_pip_install() {
    test "$PWD" = "$FIXTURE_ROOT/mcp-servers/zabbix-mcp"
    test -d "$(cat "$2")"
}
component_install_zabbix
'''],cwd=ROOT,capture_output=True,text=True,env={**os.environ,'NETCLAW_PY':sys.executable,
        'NETCLAW_DIR':str(tmp_path),'FIXTURE_ROOT':str(tmp_path)})
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('explicit', [False, True])
def test_component_upper_bound_preserves_existing_python314(tmp_path, explicit):
    old = tmp_path/'source/.venv'
    (old/'bin').mkdir(parents=True)
    (old/'sentinel').write_text('preserve existing environment')
    def python_fixture(path, minor):
        path.write_text('#!' + sys.executable + '\n' +
            'import sys,json,importlib.metadata\n' +
            'if sys.argv[1] == "--version": print("Python 3.' + str(minor) + '.0")\n' +
            'elif sys.argv[1] == "-c":\n' +
            '    code=sys.argv[2]; sys.argv=["-c",*sys.argv[3:]]\n' +
            '    sys.version_info=(3,' + str(minor) + ',0,"final",0)\n' +
            '    exec(code)\n' +
            'else: sys.exit(0)\n')
        path.chmod(0o700)
    python_fixture(old/'bin/python',14)
    python_fixture(tmp_path/'base-python',12)
    script = """set -eu
source scripts/lib/pip-helper.sh
netclaw_venv_create() { mkdir -p "$1/bin"; cp "$NETCLAW_PY" "$1/bin/python"; }
netclaw_component_venv "$FIXTURE_SOURCE/.venv"
"""
    if explicit:
        script = 'set -eu\nsource scripts/lib/pip-helper.sh\nnetclaw_pip_install example\n'
    result = subprocess.run(['/bin/bash','-c',script],cwd=ROOT,capture_output=True,text=True,
        env={**os.environ,'NETCLAW_DIR':'','NETCLAW_INSTALL_FAILURE_FILE':'',
             'NETCLAW_PY':str(tmp_path/'base-python'),
             'NETCLAW_INSTALL_COMPONENT':'panorama','FIXTURE_SOURCE':str(old.parent),
             'NETCLAW_VENV':str(old) if explicit else ''})
    assert (result.returncode == 0) != explicit, result.stdout + result.stderr
    assert (old/'sentinel').read_text() == 'preserve existing environment'
    assert (old.parent/'.venv-py3.12/bin/python').exists() != explicit


@pytest.mark.parametrize('failure', ['node','seeding','explicit-pip'])
def test_core_prerequisite_failures(failure):
    host=FixtureHost()
    kwargs={}
    if failure == 'node': host.outputs[('node','--version')]='v16.0.0'
    if failure == 'seeding': host.python_info['ensurepip']=False
    if failure == 'explicit-pip': kwargs['explicit_venv']='/fixture/venv'
    assert evaluate('zabbix',host,**kwargs)['core_errors']


@pytest.mark.parametrize('system,arch,expected', [('Darwin','arm64','arm64'),
    ('Linux','aarch64','arm64'), ('Linux','amd64','x86_64')])
def test_shell_platform_detection(tmp_path, system, arch, expected):
    executable(tmp_path/'uname', 'case "$1" in -s) echo ' + system +
        ';; -m) echo ' + arch + ';; -r) echo fixture-kernel;; esac\n')
    executable(tmp_path/'sw_vers','echo 15.7.9\n')
    result=subprocess.run(['/bin/bash','-c',
        'source scripts/lib/preflight.sh; netclaw_detect_platform; '
        'echo "$NETCLAW_OS/$NETCLAW_ARCH/$NETCLAW_OS_VERSION"'],cwd=ROOT,
        env={**os.environ,'PATH':str(tmp_path)+':'+os.environ['PATH']},capture_output=True,text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == system + '/' + expected + '/' + (
        '15.7.9' if system == 'Darwin' else 'fixture-kernel')
