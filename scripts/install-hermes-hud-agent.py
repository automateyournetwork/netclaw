#!/usr/bin/env python3
"""Install the reviewed Hermes source into a dedicated, owner-private environment."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--home',required=True);args=parser.parse_args()
    os.umask(0o077)
    home=Path(args.home).resolve();base=home/'python-runtimes/hermes-hud-agent';base.mkdir(parents=True,exist_ok=True,mode=0o700)
    if base.is_symlink() or base.stat().st_mode & 0o077:raise ValueError('Private companion directory required')
    uv=shutil.which('uv')
    if not uv:raise ValueError('Install uv, then rerun the Hermes HUD component installer.')
    manifest=json.loads((ROOT/'config/hermes-hud-compatibility.json').read_text())
    source=base/'source';venv=base/'venv'
    def run(argv):subprocess.run(argv,check=True)
    if not source.exists():
        run(['git','clone','--depth','1','--branch',manifest['release'],'https://github.com/NousResearch/hermes-agent.git',str(source)])
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if revision!=manifest['revision']:raise ValueError('Companion source differs from reviewed revision; preserve it and repair explicitly.')
    import sys
    sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
    from policy import verify_source
    verify_source(source)
    if not (venv/'bin/python').exists():run([uv,'venv','--python','3.14',str(venv)])
    run([uv,'pip','install','--python',str(venv/'bin/python'),'-c',str(ROOT/'config/hermes-hud-agent-constraints.txt'),'-e',str(source)+'[mcp]','aiohttp'])
    print('Private Hermes companion installed. Owner configuration was preserved. Launch with netclaw hud.')
if __name__=='__main__':main()
