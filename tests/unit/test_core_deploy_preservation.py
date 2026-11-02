"""Run the real deployment function against a synthetic operator workspace."""
import importlib.util
import os
from pathlib import Path
import subprocess
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('deploy_env_writer', ROOT / 'scripts/write-env.py')
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


def deploy(tmp_path, *, extra_env=None, expect_success=True):
    repo = tmp_path / "checkout & pipe|quote' space"
    repo.mkdir(exist_ok=True)
    (repo / 'workspace/skills/example').mkdir(parents=True, exist_ok=True)
    (repo / 'workspace/skills/example/SKILL.md').write_text('new skill\n')
    (repo / 'testbed').mkdir(exist_ok=True)
    (repo / 'testbed/testbed.yaml').write_text('devices: {}\n')
    for name in ('scripts/configure-testbed.py','scripts/write-env.py','scripts/lib/pyats_testbeds.py',
                 'scripts/lib/setup_state.py','scripts/lib/setup_schema.py','config/pyats-testbed-sources.json'):
        target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    for name in ('SOUL.md', 'USER.md', 'TOOLS.md'):
        (repo / name).write_text('repository default\n')
    runtime = tmp_path / '.openclaw'
    script = '''
set -eu
source scripts/lib/common.sh
source scripts/lib/install-steps.sh
NETCLAW_DIR="$FIXTURE_REPO"
define_paths
RUNTIME_HOME="$FIXTURE_RUNTIME"
RUNTIME_WORKSPACE="$RUNTIME_HOME/workspace"
RUNTIME_SKILLS="$RUNTIME_WORKSPACE/skills"
RUNTIME_ENV="$RUNTIME_HOME/.env"
core_deploy
'''
    result = subprocess.run(['bash', '-c', script], cwd=ROOT,
        env={**os.environ, 'FIXTURE_REPO': str(repo), 'FIXTURE_RUNTIME': str(runtime), **(extra_env or {})},
        capture_output=True, text=True, timeout=30)
    if expect_success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0, 'Injected failure must stop deployment'
    return repo, runtime


def test_real_deploy_literal_private_environment_and_repeat(tmp_path):
    repo, runtime = deploy(tmp_path)
    env = runtime / '.env'
    for _ in range(2):
        values = writer.values(env.read_text())
        assert values['PYATS_MCP_SCRIPT'] == str(repo / 'scripts/pyats-stdio.py')
        assert env.stat().st_mode & 0o777 == 0o600
        deploy(tmp_path)


def test_upgrade_preserves_persona_testbed_and_custom_stores(tmp_path):
    runtime = tmp_path / '.openclaw'
    workspace = runtime / 'workspace'
    (workspace / 'testbed').mkdir(parents=True)
    for name in ('SOUL.md', 'USER.md', 'TOOLS.md'):
        (workspace / name).write_text('operator notes\n')
    testbed = workspace / 'testbed/testbed.yaml'
    testbed.write_text('operator testbed\n')
    (runtime / '.env').write_text('RAG_DATA_DIR=/custom/rag\nMEMORY_DATA_DIR=/custom/memory\nPYATS_TESTBED_PATH=/custom/testbed.yaml\n')
    deploy(tmp_path)
    for name in ('SOUL.md', 'USER.md', 'TOOLS.md'):
        assert (workspace / name).read_text() == 'operator notes\n'
    assert not testbed.is_symlink()
    assert testbed.read_text() == 'operator testbed\n'
    values = writer.values((runtime / '.env').read_text())
    assert values['RAG_DATA_DIR'] == '/custom/rag'
    assert values['MEMORY_DATA_DIR'] == '/custom/memory'
    assert values['PYATS_TESTBED_PATH'] == '/custom/testbed.yaml'


def test_upgrade_retains_skill_original_and_ignores_custom_only_file(tmp_path):
    runtime = tmp_path / '.openclaw'
    skill = runtime / 'workspace/skills/example/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('operator skill\n')
    custom = skill.parent / 'custom.md'
    custom.write_text('operator .openclaw custom\n')
    deploy(tmp_path)
    assert skill.read_text() == 'new skill\n'
    assert custom.read_text() == 'operator .openclaw custom\n'
    generations = list((runtime / 'skill-deployment-backups').glob('deploy-*'))
    assert len(generations) == 1
    assert (generations[0] / 'originals/example/SKILL.md').read_text() == 'operator skill\n'
    deploy(tmp_path)
    assert len(list((runtime / 'skill-deployment-backups').glob('deploy-*'))) == 1


def test_dynamic_deploy_preserves_policy_and_never_creates_static_placeholder(tmp_path):
    runtime=tmp_path/'.openclaw';runtime.mkdir(mode=0o700)
    env=runtime/'.env'
    env.write_text('NETCLAW_TESTBED_MODE=dynamic\nNETCLAW_TESTBED_SOURCES=cml,netbox\nNETCLAW_PASSWORD=fixture-private\n')
    env.chmod(0o600)
    deploy(tmp_path)
    assert not (runtime/'workspace/testbed').exists()
    data=env.read_text()
    assert 'PYATS_TESTBED_PATH=' not in data
    assert 'NETCLAW_TESTBED_MODE=dynamic' in data
    assert 'NETCLAW_PASSWORD=fixture-private' in data


def test_upgrade_replaces_legacy_checkout_symlinks_only(tmp_path):
    repo = tmp_path / "checkout & pipe|quote' space"
    repo.mkdir()
    (repo / 'USER.md').write_text('repository default\n')
    elsewhere = tmp_path / 'operator-tools.md'
    elsewhere.write_text('operator tools\n')
    workspace = tmp_path / '.openclaw/workspace'
    workspace.mkdir(parents=True)
    (workspace / 'USER.md').symlink_to(repo / 'USER.md')
    (workspace / 'TOOLS.md').symlink_to(elsewhere)
    (workspace / 'SOUL.md').write_text('operator notes\n')
    deploy(tmp_path)
    user = workspace / 'USER.md'
    assert not user.is_symlink()
    assert user.read_text() == 'repository default\n'
    assert (workspace / 'TOOLS.md').is_symlink()
    assert (workspace / 'TOOLS.md').read_text() == 'operator tools\n'
    assert (workspace / 'SOUL.md').read_text() == 'operator notes\n'
    assert not list(workspace.glob('.*.netclaw-copy'))


@pytest.mark.parametrize('occupied', ['symlink', 'file', 'directory'])
def test_bootstrap_repair_preserves_occupied_staging_paths(tmp_path, occupied):
    repo = tmp_path / "checkout & pipe|quote' space"
    repo.mkdir()
    (repo / 'USER.md').write_text('repository default\n')
    workspace = tmp_path / '.openclaw/workspace'
    workspace.mkdir(parents=True)
    (workspace / 'USER.md').symlink_to(repo / 'USER.md')
    victim = tmp_path / 'operator-private-file'
    victim.write_text('operator-owned contents\n')
    staging = workspace / '.USER.md.netclaw-copy'
    if occupied == 'symlink':
        staging.symlink_to(victim)
    elif occupied == 'file':
        staging.write_text('operator staging contents\n')
    else:
        staging.mkdir()
    deploy(tmp_path)
    assert victim.read_text() == 'operator-owned contents\n'
    assert not (workspace / 'USER.md').is_symlink()
    assert (workspace / 'USER.md').read_text() == 'repository default\n'
    assert (workspace / 'USER.md').stat().st_mode & 0o777 == 0o600
    if occupied == 'symlink':
        assert staging.is_symlink() and staging.readlink() == victim
    elif occupied == 'file':
        assert staging.read_text() == 'operator staging contents\n'
    else:
        assert staging.is_dir()
    assert not list(workspace.glob('.USER.md.netclaw-copy-*'))


@pytest.mark.parametrize('failure', ['copy', 'replace', 'changed'])
def test_failed_bootstrap_repair_preserves_original_and_cleans_owned_temp(tmp_path, failure):
    repo = tmp_path / "checkout & pipe|quote' space"
    repo.mkdir()
    (repo / 'USER.md').write_text('repository default\n')
    workspace = tmp_path / '.openclaw/workspace'
    workspace.mkdir(parents=True)
    user = workspace / 'USER.md'
    user.symlink_to(repo / 'USER.md')
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    wrapper = binaries / 'python3'
    # Exercise the actual shell function and embedded Python; inject only the I/O
    # fault or concurrent operator edit inside its bootstrap-copy subprocess.
    wrapper.write_text(f'''#!{sys.executable}
import os, shutil, sys
if len(sys.argv) > 3 and sys.argv[1] == '-' and sys.argv[2] == os.environ['FIXTURE_BOOTSTRAP']:
    program = sys.stdin.read()
    sys.argv = sys.argv[1:]
    failure = os.environ['FIXTURE_FAILURE']
    if failure == 'replace':
        def fail(*args):
            raise OSError('fixture rename failure')
        os.replace = fail
    else:
        copy = shutil.copyfileobj
        def fail(source, output):
            if failure == 'copy':
                output.write(b'partial')
                raise OSError('fixture copy failure')
            copy(source, output)
            path = os.environ['FIXTURE_BOOTSTRAP']
            os.unlink(path)
            with open(path, 'w') as updated:
                updated.write('concurrent operator notes\\n')
        shutil.copyfileobj = fail
    exec(compile(program, '<bootstrap-repair>', 'exec'))
else:
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
''')
    wrapper.chmod(0o700)
    deploy(tmp_path, extra_env={'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
                               'FIXTURE_BOOTSTRAP': str(user), 'FIXTURE_FAILURE': failure},
           expect_success=False)
    if failure == 'changed':
        assert not user.is_symlink()
        assert user.read_text() == 'concurrent operator notes\n'
    else:
        assert user.is_symlink() and user.readlink() == repo / 'USER.md'
    assert (repo / 'USER.md').read_text() == 'repository default\n'
    assert not list(workspace.glob('.USER.md.netclaw-copy-*'))
