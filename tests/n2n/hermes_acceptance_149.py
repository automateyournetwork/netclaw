#!/usr/bin/env python3
"""Reproduce spec149 controlled-provider tests in a private synthetic checkout.

Uses the selected fixture interpreters and installer compatibility patch. Does
not modify the owner's third-party source checkout or contact a model provider.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]


def prepare(base):
    fixture=base/'repo'
    fixture.mkdir(parents=True,exist_ok=True,mode=0o700)
    for relative in ('mcp-servers/hermes-hud-mcp','mcp-servers/protocol-mcp','mcp-servers/n2n-mcp',
                     'config','scripts','tests/n2n','tests/hermes-hud','workspace/skills/subnet-calculator','docs/reference'):
        shutil.copytree(ROOT/relative,fixture/relative,dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('__pycache__','.venv','node_modules','.git','*.log','.env','.env.*'))
    rule=json.loads((ROOT/'config/hermes-hud-tool-policy.json').read_text())['servers']['subnet-calc-mcp']
    subnet=fixture/'mcp-servers/subnet-calculator-mcp'
    if not subnet.exists():
        for argv in (['git','init','-q',str(subnet)],['git','-C',str(subnet),'fetch','--depth','1',rule['sourceRepository'],rule['reviewedCommit']],
                     ['git','-C',str(subnet),'checkout','--detach','FETCH_HEAD']):
            subprocess.run(argv,check=True,capture_output=True)
    subprocess.run([sys.executable,str(fixture/'scripts/apply-fastmcp-patches.py'),'--root',str(fixture),'--component','subnet-calc'],check=True)
    if (ROOT/'ui/netclaw-visual/node_modules').exists():
        shutil.copytree(ROOT/'ui/netclaw-visual',fixture/'ui/netclaw-visual',dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('node_modules','.git','*.log','.env','.env.*','playwright-report','test-results'))
        modules=fixture/'ui/netclaw-visual/node_modules'
        if not modules.exists():modules.symlink_to(ROOT/'ui/netclaw-visual/node_modules',target_is_directory=True)
    return fixture


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workdir',type=Path)
    parser.add_argument('--tests',nargs='+',default=['tests/n2n/test_hermes_lifecycle_149.py'])
    args=parser.parse_args()
    for name in ('NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON'):
        if not os.environ.get(name):raise SystemExit(name+' is required; see tests/n2n/README.md')
    base=(args.workdir or Path(tempfile.mkdtemp(prefix='netclaw149-'))).resolve()
    fixture=prepare(base)
    env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','TMPDIR','SYSTEMROOT','NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON','NETCLAW_OPENCLAW_BIN')}
    # Process drift tests must only mutate a copied, test-owned source tree.
    if any('hermes-hud' in value for value in args.tests):
        source=base/'hermes-source'
        shutil.copytree(env['NETCLAW_HERMES_SOURCE'],source,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.git','__pycache__','.venv'))
        env['NETCLAW_HERMES_SOURCE']=str(source)
    env['HOME']=str(base/'owner');Path(env['HOME']).mkdir(exist_ok=True,mode=0o700)
    result=subprocess.run([sys.executable,'-m','pytest','-q',*args.tests],cwd=fixture,env=env)
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
