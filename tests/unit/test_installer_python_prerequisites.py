"""Prerequisite and retry checks without installing components or system packages."""
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def interpreter(path, supported=True, pip_failure=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('''#!/bin/sh
if [ "$1" = --version ]; then echo 'Python VERSION'; exit 0; fi
if [ "$1" = -c ]; then
    case "$2" in
        *'sys.version_info >='*) exit SUPPORTED_STATUS ;;
        *'sys.version_info[:2]'*) echo VERSION; exit 0 ;;
    esac
fi
if [ "$1 $2 $3" = '-m pip install' ]; then exit PIP_STATUS; fi
exit 0
'''.replace('VERSION', '3.12' if supported else '3.9')
        .replace('SUPPORTED_STATUS', '0' if supported else '1')
        .replace('PIP_STATUS', '23' if pip_failure else '0'))
    path.chmod(0o700)
    return path


def run(tmp_path, body, **extra):
    return subprocess.run(['/bin/bash', '-c', 'set -eu\n' + body], cwd=ROOT,
        env={**os.environ, 'NETCLAW_PY': str(tmp_path / 'base-python'),
             'NETCLAW_INSTALL_COMPONENT': 'arista-cvp', 'NETCLAW_VENV': '',
             'NETCLAW_RUNTIME_ROOT': str(tmp_path / 'runtimes'),
             'NETCLAW_INSTALL_FAILURE_FILE': '', **extra},
        capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize(('installer_old', 'base_old', 'component', 'uv_missing', 'ok'), [
    (False, False, 'pyats', False, True),
    (True, False, 'arista-cvp', False, False),
    (False, True, 'arista-cvp', False, False),
    (False, False, 'pyats', True, False),
    (False, False, 'gait', True, False),
    (False, False, 'arista-cvp', True, True),
])
def test_prerequisite_checks(tmp_path, installer_old, base_old, component, uv_missing, ok):
    interpreter(tmp_path / 'base-python', supported=not base_old)
    result = run(tmp_path, r'''
NETCLAW_DIR="$PWD"
source scripts/lib/install-steps.sh
log_step() { echo "$*"; }
log_info() { echo "$*"; }
log_warn() { echo "$*"; }
log_error() { echo "$*"; }
check_command() { [ "$1" != uv ] || [ "$FIXTURE_UV_MISSING" != 1 ]; }
node() { echo v24.16.0; }
python3() {
    if [[ "$1" == */runtime-policy.py ]]; then command python3 "$@"; return; fi
    case "${2:-}" in
        *'sys.version_info >='*) [ "$FIXTURE_INSTALLER_OLD" != 1 ] ;;
        *) return 1 ;;
    esac
}
prereqs_offer_install() { return 1; }
core_prereqs
''', SELECTED=component, FIXTURE_INSTALLER_OLD=str(int(installer_old)),
        FIXTURE_UV_MISSING=str(int(uv_missing)))
    assert (result.returncode == 0) == ok, result.stdout + result.stderr
    assert ('All prerequisites satisfied.' in result.stdout) == ok
    if installer_old or base_old:
        assert 'Python 3.10+' in result.stderr
    if uv_missing and component in ('pyats', 'gait'):
        assert 'uv is required' in result.stdout


def test_old_base_is_rejected_before_creating_runtime(tmp_path):
    interpreter(tmp_path / 'base-python', supported=False)
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_venv_create "$NETCLAW_RUNTIME_ROOT/new"
''')
    assert result.returncode != 0
    assert 'Python 3.10+' in result.stderr
    assert not (tmp_path / 'runtimes').exists()


def old_runtime(tmp_path):
    target = tmp_path / 'runtimes/arista-cvp-component-bounds'
    interpreter(target / 'bin/python', supported=False)
    (target / '.netclaw-managed').write_text('arista-cvp\n')
    (target / 'sentinel').write_bytes(b'operator state')
    interpreter(tmp_path / 'base-python')
    return target


@pytest.mark.parametrize('pip_failure', [False, True])
def test_retry_preserves_old_managed_runtime(tmp_path, pip_failure):
    old = old_runtime(tmp_path)
    record = tmp_path / 'runtimes/records/arista-cvp'
    record.parent.mkdir()
    record.write_text(str(old / 'bin/python') + '\n')
    original = {path.relative_to(old): path.read_bytes() for path in old.rglob('*') if path.is_file()}
    interpreter(tmp_path / 'base-python', pip_failure=pip_failure)
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_venv_create() { mkdir -p "$1/bin"; cp "$NETCLAW_PY" "$1/bin/python"; }
netclaw_pip_install example
''')
    assert (result.returncode == 0) == (not pip_failure), result.stdout + result.stderr
    assert {path.relative_to(old): path.read_bytes() for path in old.rglob('*') if path.is_file()} == original
    assert (tmp_path / 'runtimes/arista-cvp-component-bounds-py3.12/bin/python').exists()
    expected = old / 'bin/python' if pip_failure else tmp_path / 'runtimes/arista-cvp-component-bounds-py3.12/bin/python'
    assert record.read_text().strip() == str(expected)


@pytest.mark.parametrize('symlink', [False, True])
def test_retry_refuses_unmanaged_recovery_target(tmp_path, symlink):
    old_runtime(tmp_path)
    destination = tmp_path / 'runtimes/arista-cvp-component-bounds-py3.12'
    if symlink:
        victim = tmp_path / 'operator-runtime'
        victim.mkdir()
        (victim / '.netclaw-managed').touch()
        destination.symlink_to(victim, target_is_directory=True)
    else:
        destination.mkdir()
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_pip_install example
''')
    assert result.returncode != 0
    assert 'Refusing to adopt an unmanaged' in result.stderr
    assert not (destination / 'bin').exists()


def test_compatible_runtime_is_reused(tmp_path):
    target = tmp_path / 'runtimes/arista-cvp-component-bounds'
    interpreter(tmp_path / 'base-python')
    interpreter(target / 'bin/python')
    (target / '.netclaw-managed').touch()
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_venv_create() { echo 'unexpected recreation' >&2; return 42; }
netclaw_pip_install example
''')
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / 'runtimes/arista-cvp-component-bounds-py3.12').exists()


def test_explicit_old_runtime_is_not_replaced(tmp_path):
    target = tmp_path / 'operator-runtime'
    interpreter(target / 'bin/python', supported=False)
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_pip_install example
''', NETCLAW_VENV=str(target))
    assert result.returncode != 0
    assert 'Python 3.10+' in result.stderr
    assert (target / 'bin/python').exists()
    assert not (tmp_path / 'runtimes').exists()


def test_source_venv_retry_preserves_old_python_and_reuses_replacement(tmp_path):
    old = tmp_path / 'source/.venv'
    interpreter(old / 'bin/python', supported=False)
    (old / 'sentinel').write_bytes(b'keep source environment')
    interpreter(tmp_path / 'base-python')
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_venv_create() { mkdir -p "$1/bin"; cp "$NETCLAW_PY" "$1/bin/python"; }
netclaw_component_venv "$FIXTURE_SOURCE/.venv"
test "$NETCLAW_COMPONENT_VENV" = "$FIXTURE_SOURCE/.venv-py3.12"
netclaw_venv_create() { return 42; }
netclaw_component_venv "$FIXTURE_SOURCE/.venv"
''', FIXTURE_SOURCE=str(old.parent))
    assert result.returncode == 0, result.stdout + result.stderr
    assert (old / 'sentinel').read_bytes() == b'keep source environment'
    assert (old / 'bin/python').read_text().find('3.9') >= 0
    assert (old.parent / '.venv-py3.12/.netclaw-managed').is_file()


@pytest.mark.parametrize('symlink', [False, True])
def test_source_venv_retry_refuses_unmanaged_replacement(tmp_path, symlink):
    old = tmp_path / 'source/.venv'
    interpreter(old / 'bin/python', supported=False)
    interpreter(tmp_path / 'base-python')
    replacement = old.parent / '.venv-py3.12'
    if symlink:
        destination = tmp_path / 'operator-runtime'
        destination.mkdir()
        (destination / '.netclaw-managed').touch()
        replacement.symlink_to(destination, target_is_directory=True)
    else:
        replacement.mkdir()
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
netclaw_component_venv "$FIXTURE_SOURCE/.venv"
''', FIXTURE_SOURCE=str(old.parent))
    assert result.returncode != 0
    assert 'Refusing to adopt an unmanaged' in result.stderr
    assert not (replacement / 'bin').exists()


@pytest.mark.parametrize('system, failure, expected', [(False, 0, 0), (False, 23, 1), (True, 0, 1)])
def test_obsolete_pip_upgrade_is_isolated_and_failure_propagates(tmp_path, system, failure, expected):
    fake = tmp_path / 'base-python'
    fake.write_text('''#!/bin/sh
if [ "$1" = -c ]; then
    case "$2" in
        *'version("pip")'*) exit 1 ;;
        *'sys.prefix != sys.base_prefix'*) exit "$FIXTURE_SYSTEM" ;;
    esac
fi
printf '%s\n' "$@" >> "$FIXTURE_CALLS"
exit "$FIXTURE_UPGRADE_FAILURE"
''')
    fake.chmod(0o700)
    calls = tmp_path / 'pip-calls'
    result = run(tmp_path, '''
source scripts/lib/pip-helper.sh
_netclaw_modern_component_pip "$NETCLAW_PY"
''', FIXTURE_SYSTEM=str(int(system)), FIXTURE_UPGRADE_FAILURE=str(failure), FIXTURE_CALLS=str(calls))
    assert result.returncode == expected, result.stdout + result.stderr
    if system:
        assert not calls.exists()
        assert 'Refusing to upgrade system pip' in result.stderr
    else:
        assert 'pip>=23' in calls.read_text()
