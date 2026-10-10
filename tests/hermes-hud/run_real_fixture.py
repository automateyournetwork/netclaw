#!/usr/bin/env python3
"""Real pinned Hermes + real installer-patched MCP + controlled local provider.
Runs in an isolated synthetic repository; never changes an owner's checkout or home.
Prerequisites: uv, git, Node 24.19+, and ui/netclaw-visual/node_modules (npm ci).
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workdir',type=Path);args=parser.parse_args()
    base=args.workdir or Path(tempfile.mkdtemp(prefix='netclaw-hermes148-'))
    base=base.resolve();base.mkdir(parents=True,exist_ok=True,mode=0o700)
    fixture=base/'repo';fixture.mkdir(exist_ok=True)
    if not (ROOT/'ui/netclaw-visual/node_modules').exists():raise SystemExit('Run npm ci in ui/netclaw-visual first.')
    def run(argv,**kwargs):subprocess.run([str(a) for a in argv],check=True,**kwargs)
    for relative in ['mcp-servers/hermes-hud-mcp','config','scripts','tests/hermes-hud','workspace/skills/subnet-calculator']:
        shutil.copytree(ROOT/relative,fixture/relative,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','.venv','*.log'))
    ui=fixture/'ui/netclaw-visual';ui.mkdir(parents=True,exist_ok=True)
    for file in (ROOT/'ui/netclaw-visual').iterdir():
        if file.is_file() and file.suffix in ('.js','.py'):shutil.copyfile(file,ui/file.name)
    shutil.copyfile(ROOT/'ui/netclaw-visual/package.json',ui/'package.json')
    shutil.copytree(ROOT/'ui/netclaw-visual/src',ui/'src',dirs_exist_ok=True)
    if not (ui/'node_modules').exists():(ui/'node_modules').symlink_to(ROOT/'ui/netclaw-visual/node_modules',target_is_directory=True)
    (fixture/'testbed').mkdir(exist_ok=True);(fixture/'testbed/testbed.yaml').write_text('devices: {}\n')
    rule=json.loads((ROOT/'config/hermes-hud-tool-policy.json').read_text())['servers']['subnet-calc-mcp']
    subnet=fixture/'mcp-servers/subnet-calculator-mcp'
    if not subnet.exists():
        run(['git','init','-q',subnet]);run(['git','-C',subnet,'fetch','--depth','1',rule['sourceRepository'],rule['reviewedCommit']]);run(['git','-C',subnet,'checkout','--detach','FETCH_HEAD'])
    run(['python3',fixture/'scripts/apply-fastmcp-patches.py','--root',fixture,'--component','subnet-calc'])
    uv=shutil.which('uv')
    if not uv:raise SystemExit('Install uv first.')
    bridge=base/'bridge';tool=base/'tool'
    for venv,requirements in [(bridge,ROOT/'mcp-servers/hermes-hud-mcp/requirements.txt'),(tool,ROOT/'config/python-components/subnet-calc.txt')]:
        if not (venv/'bin/python').exists():run([uv,'venv','--python','3.12',venv])
        run([uv,'pip','install','--python',venv/'bin/python','-r',requirements,'python-dotenv'])
    agent_home=base/'profile';agent_home.mkdir(exist_ok=True)
    run(['python3',ROOT/'scripts/install-hermes-hud-agent.py','--home',agent_home])
    agent=agent_home/'python-runtimes/hermes-hud-agent'
    env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','TMPDIR','SYSTEMROOT')}
    env.update(NETCLAW_HERMES_SOURCE=str(agent/'source'),NETCLAW_HERMES_PYTHON=str(agent/'venv/bin/python'),NETCLAW_SUBNET_PYTHON=str(tool/'bin/python'))
    run([bridge/'bin/python','-m','unittest','discover','-s',fixture/'tests/hermes-hud','-p','test_*integration.py','-v'],env=env)
    print('PASS: real Hermes and installer-patched FastMCP subnet tool; controlled model provider. No live-provider acceptance claimed.')
if __name__=='__main__':main()
