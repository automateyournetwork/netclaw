"""Standalone setup must not downgrade an HA-required installation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lib'))
from ha_setup_guard import require_standalone_home
from setup_state import Conflict, guarded_write
from setup_schema import canonical
from setup_deploy import Deployment
from setup_engine import Engine
from setup_enrollment import materialize_remote_transport, binding
from setup_risk import configure_risk


def marked(tmp_path):
    home = tmp_path.resolve() / 'owned'; home.mkdir(mode=0o700)
    state = home / 'netclaw-federation'; state.mkdir(mode=0o700)
    guarded_write(state / 'ha-required.json', b'{damaged marker is still binding')
    return home


def test_missing_or_standalone_home_does_not_acquire_ha(tmp_path):
    home = tmp_path.resolve() / 'new'
    require_standalone_home(home); assert not home.exists()
    guarded_write(home / 'netclaw-federation/protected-profile.json', canonical({'schemaVersion': 1, 'role': 'border'}))
    require_standalone_home(home)


@pytest.mark.parametrize('kind', ('marker', 'dangling-marker', 'profile2', 'ha-field', 'invalid-profile', 'future-profile'))
def test_any_ha_or_ambiguous_state_refuses_without_repair(tmp_path, kind):
    home = marked(tmp_path); state = home / 'netclaw-federation'; marker = state / 'ha-required.json'
    if kind != 'marker': marker.unlink()
    if kind == 'dangling-marker': marker.symlink_to(state / 'missing')
    elif kind == 'profile2': guarded_write(state / 'protected-profile.json', canonical({'schemaVersion': 2}))
    elif kind == 'ha-field': guarded_write(state / 'protected-profile.json', canonical({'schemaVersion': 1, 'ha': None}))
    elif kind == 'invalid-profile': guarded_write(state / 'protected-profile.json', b'{invalid')
    elif kind == 'future-profile': guarded_write(state / 'protected-profile.json', canonical({'schemaVersion': 99}))
    before = {p.name: (os.readlink(p) if p.is_symlink() else p.read_bytes()) for p in state.iterdir()}
    with pytest.raises(Conflict): require_standalone_home(home)
    assert before == {p.name: (os.readlink(p) if p.is_symlink() else p.read_bytes()) for p in state.iterdir()}


def test_resume_and_risk_configuration_refuse_before_observation_or_write(tmp_path):
    home = marked(tmp_path)
    with pytest.raises(Conflict, match='ha_home_requires_cluster_workflow'):
        Engine._targets(SimpleNamespace(), {'claws': [{'runtimeHome': str(home)}]}, run={'effects': []})
    deploy = SimpleNamespace(root=home, claw={'role': 'border'})
    context = {'plan': {'claws': [{'role': 'border', 'runtimeHome': str(home)}]}}
    with pytest.raises(Conflict, match='ha_home_requires_cluster_workflow'): configure_risk({}, context, deploy, None)
    assert not (home / '.env').exists()


def test_remote_transport_import_cannot_write_registry_or_environment(tmp_path):
    home = marked(tmp_path); calls = []
    runtime = SimpleNamespace(home=home, fence=lambda: calls.append('fence'))
    with pytest.raises(Conflict, match='ha_home_requires_cluster_workflow'):
        materialize_remote_transport(runtime, {}, home / 'registry.json', expected_revision=0)
    assert not calls and not (home / 'registry.json').exists() and not (home / '.env').exists()


def test_setup_enrollment_refuses_both_border_and_member_before_db_creation(tmp_path):
    home = marked(tmp_path)
    other = tmp_path.resolve() / 'other'
    guarded_write(other / '.netclaw-setup-owner.json', canonical({
        'schema': 1, 'runId': 'run', 'installationId': 'other', 'planHash': 'hash'}))
    for key in ('border', 'claw'):
        record = {'runId': 'run', 'planHash': 'hash',
                  'border': {'runtimeHome': str(other), 'id': 'other'},
                  'claw': {'runtimeHome': str(other), 'id': 'other'}}
        record[key] = {'runtimeHome': str(home), 'id': 'ha'}
        with pytest.raises(Conflict, match='ha_home_requires_cluster_workflow'): binding(record)
    assert not (home / 'n2n/federation.db').exists()


def test_write_rechecks_after_artifact_intent_callback(tmp_path):
    home = tmp_path.resolve() / 'owned'; home.mkdir(mode=0o700)
    deploy = Deployment.__new__(Deployment); deploy.root = home; deploy.claw = {'id': 'fixture'}
    def intent(*_): guarded_write(home / 'netclaw-federation/ha-required.json', b'{}')
    deploy.context = {'artifactIntent': intent}
    with pytest.raises(Conflict, match='ha_home_requires_cluster_workflow'):
        deploy.write({'id': 'env'}, home / '.env', b'N2N_ROLE=standalone\n')
    assert not (home / '.env').exists()


def test_component_install_guard_runs_before_dependencies_or_config():
    source = ROOT / 'scripts/lib/install-steps.sh'
    script = 'source "$1"; require_standalone_setup_home(){ return 19; }; log_step(){ echo unexpected-write; }; component_install_n2n'
    result = subprocess.run(['bash', '-c', script, 'test', str(source)], capture_output=True, timeout=5)
    assert result.returncode == 1 and b'unexpected-write' not in result.stdout


def test_readiness_refuses_before_model_probe_or_output_file(tmp_path):
    home = marked(tmp_path); output = tmp_path / 'readiness.json'
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/installer-readiness.py'),
        '--runtime-root', str(home / 'python-runtimes'), '--config', str(home / 'openclaw.json'),
        '--components', 'n2n', '--probe', '--check-provider', '--output', str(output)], capture_output=True, timeout=10)
    assert result.returncode == 1 and b'private cluster status' in result.stderr and not output.exists()


def test_marker_guard_cli_does_not_print_private_bytes(tmp_path):
    home = marked(tmp_path)
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/lib/ha_setup_guard.py'), '--home', str(home)],
                            capture_output=True, timeout=5)
    assert result.returncode == 1 and b'damaged marker' not in result.stderr and not result.stdout


def test_legacy_member_provision_refuses_before_provider_config_read(tmp_path):
    home = marked(tmp_path)
    spec = importlib.util.spec_from_file_location('ha_guard_member_home', ROOT / 'scripts/in2n-member-home.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    runtime = SimpleNamespace(home=home)
    with pytest.raises(Conflict, match='ha_home_requires_cluster_workflow'):
        module.provision_convergence(runtime, 'fixture')
