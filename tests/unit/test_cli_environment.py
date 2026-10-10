"""Exercise the CLI's actual environment helpers without starting services."""
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT/'scripts/netclaw').read_text()
FUNCTIONS = SOURCE[SOURCE.index('env_get() {'):SOURCE.index('\nngrok_up()')]


@pytest.mark.parametrize('systemd', [False, True])
def test_literal_role_round_trip_and_private_permissions(tmp_path, systemd):
    envfile = tmp_path/('mesh.systemd.env' if systemd else '.env')
    envfile.write_text('OTHER=preserved\nN2N_RISK_NAME=old\n')
    if systemd:
        (tmp_path/'.env').write_text('N2N_RISK_NAME=stale\n')
    value = 'lab & primary | "quote" apostrophe\' $HOME `id` \\path\ttab'
    env = dict(os.environ, RUNTIME_HOME=str(tmp_path), NETCLAW_ROOT=str(ROOT))
    result = subprocess.run(['bash','-c', FUNCTIONS+'\nenv_set N2N_RISK_NAME "$1" && env_get N2N_RISK_NAME', 'test',value],
                            env=env,capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.rstrip('\n') == value
    assert 'OTHER=preserved' in envfile.read_text()
    assert envfile.stat().st_mode & 0o777 == 0o600


def test_failed_cli_write_preserves_existing_file(tmp_path):
    path=tmp_path/'.env';path.write_text('OTHER=preserved\n')
    env=dict(os.environ,RUNTIME_HOME=str(tmp_path),NETCLAW_ROOT=str(ROOT))
    result=subprocess.run(['bash','-c',FUNCTIONS+'\nenv_set N2N_RISK_NAME "$1"','test','name\nINJECTED=yes'],
                          env=env,capture_output=True,text=True)
    assert result.returncode != 0
    assert path.read_text() == 'OTHER=preserved\n'


def test_descriptor_only_cli_uses_custom_hermes_home(tmp_path):
    import json
    home=tmp_path/'Hermes with spaces';home.mkdir()
    config=tmp_path/'xdg/netclaw';config.mkdir(parents=True)
    descriptor=config/'runtime.json';descriptor.write_text(json.dumps({'schemaVersion':1,'kind':'hermes','home':str(home)}));descriptor.chmod(0o600)
    env={k:v for k,v in os.environ.items() if k not in ('NETCLAW_RUNTIME','HERMES_HOME','OPENCLAW_HOME','OPENCLAW_STATE_DIR','OPENCLAW_CONFIG_PATH','NETCLAW_BGP_API')}
    env.update(HOME=str(tmp_path),XDG_CONFIG_HOME=str(tmp_path/'xdg'))
    result=subprocess.run(['python3',str(ROOT/'scripts/federation-control.py'),'env'],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert "NETCLAW_RUNTIME=hermes" in result.stdout and str(home) in result.stdout
    assert not (home/'netclaw-hud').exists(), 'status/selection must not create a runtime'


def test_owned_daemon_start_status_stop_and_foreign_home_isolation(tmp_path):
    import json,socket,time,sys
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    home=tmp_path/'openclaw';home.mkdir(mode=0o700)
    (home/'.env').write_text(f'BGP_API_PORT={port}\nBGP_LISTEN_PORT=0\nNETCLAW_DRY_RUN=true\nN2N_ENABLED=false\nNETCLAW_BGP_PEERS=[]\n')
    env=dict(os.environ,HOME=str(tmp_path),XDG_CONFIG_HOME=str(tmp_path/'config'),NETCLAW_RUNTIME='openclaw',OPENCLAW_STATE_DIR=str(home))
    for key in ('NETCLAW_BGP_API','HERMES_HOME','NETCLAW_DAEMON_LOCK_FD'):env.pop(key,None)
    cmd=[sys.executable,str(ROOT/'scripts/federation-control.py')]
    try:
        started=subprocess.run(cmd+['start'],env=env,capture_output=True,text=True,timeout=40)
        assert started.returncode==0,started.stderr+(home/'netclaw-federation/daemon.log').read_text()[-2000:]
        status=json.loads(started.stdout);assert status['federation_ready'] is False and status['n2n_enabled'] is False and status['harness_type']=='openclaw'
        other=dict(env,OPENCLAW_STATE_DIR=str(tmp_path/'different'))
        assert subprocess.run(cmd+['status'],env=other,capture_output=True).returncode!=0
        assert subprocess.run(cmd+['stop'],env=other,capture_output=True).returncode==0
        assert subprocess.run(cmd+['status'],env=env,capture_output=True).returncode==0
    finally:
        stopped=subprocess.run(cmd+['stop'],env=env,capture_output=True,text=True,timeout=15)
        assert stopped.returncode==0,stopped.stderr
    assert subprocess.run(cmd+['status'],env=env,capture_output=True).returncode!=0
