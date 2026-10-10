"""Serve the real launcher/agent with the controlled provider for host browsers.

Run after run_real_fixture.py --workdir PATH. This creates a new private home;
it never imports owner credentials. Ctrl+C stops only this launcher's children.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent / 'fixtures'))
from provider import Provider

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--ui-port', type=int, default=34010)
    parser.add_argument('--api-port', type=int, default=34011)
    parser.add_argument('--companion-port', type=int, default=8645)
    args = parser.parse_args()
    os.umask(0o077)
    base = Path(tempfile.mkdtemp(prefix='browser-host-', dir=args.fixture))
    home = base / 'Hermes Home'
    home.mkdir()
    records = home / 'python-runtimes/records'
    records.mkdir(parents=True)
    for component, interpreter in [('hermes-hud', args.fixture/'bridge/bin/python'), ('subnet-calc', args.fixture/'tool/bin/python')]:
        (records/component).write_text(str(interpreter)+'\n')
    provider = Provider()
    url = provider.start()
    config = {'model': {'default':'hud-fixture', 'provider':'custom', 'base_url':url},
        'mcp_servers': {'subnet-calc-mcp': {'command':'python3',
            'args':['-u',str(ROOT/'scripts/component-launch.py'),'subnet-calc','--server','subnet-calc-mcp'],
            'env':{'NETCLAW_RUNTIME_ROOT':str(home/'python-runtimes'),'NETCLAW_RUNTIME_ENV':str(home/'.env')}}}}
    (home/'config.yaml').write_text(json.dumps(config))
    (home/'.env').write_text('OPENAI_API_KEY=fixture-only-key\nOPENAI_BASE_URL='+url+'\n')
    installed = home/'skills/subnet-calculator'
    installed.mkdir(parents=True)
    shutil.copyfile(ROOT/'workspace/skills/subnet-calculator/SKILL.md',installed/'SKILL.md')
    agent = args.fixture/'profile/python-runtimes/hermes-hud-agent'
    env = {k:v for k,v in os.environ.items() if k in ('PATH','LANG')}
    env.update(HOME=str(base), XDG_CONFIG_HOME=str(base/'config'), NETCLAW_RUNTIME='hermes',
        HERMES_HOME=str(home), NETCLAW_HERMES_SOURCE=str(agent/'source'),
        NETCLAW_HERMES_PYTHON=str(agent/'venv/bin/python'),
        HUD_UI_PORT=str(args.ui_port), HUD_PORT=str(args.api_port),
        NETCLAW_HERMES_HUD_PORT=str(args.companion_port))
    subprocess.run(['node',str(ROOT/'scripts/hud-launch.mjs'),'select','hermes',str(home)],env=env,check=True)
    process = subprocess.Popen(['node',str(ROOT/'scripts/hud-launch.mjs')],env=env)
    print('Synthetic browser profile: '+str(home),flush=True)
    signal.signal(signal.SIGTERM, lambda *_: process.send_signal(signal.SIGINT))
    try:
        process.wait()
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=20)
    finally:
        provider.close()
        (base/'provider-count.json').write_text(json.dumps({'requests':len(provider.calls)}))
    return process.returncode

if __name__ == '__main__':
    sys.exit(main())
