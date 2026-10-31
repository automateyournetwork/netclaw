#!/usr/bin/env python3
"""Stage pinned pyATS source and dependencies before replacing a runtime."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

REVISION = '4a3c1e3404d5ed7a78cb094bf26d2a49065497d9'
REPOSITORY = 'https://github.com/automateyournetwork/pyATS_MCP.git'
MARKER = '.netclaw-pyats-generation'
SOURCE_FILES = ('pyats_mcp_server.py', 'pyats_tasks.py', 'pyats_testbed_builder.py')


def exists(path):
    return path.exists() or path.is_symlink()


def verify(target):
    subprocess.run([str(target/'bin/python'), '-c',
                    'import pyats, genie, unicon; from mcp.client.client import Client'], check=True)
    for source in SOURCE_FILES:
        if not (target/'upstream'/source).is_file():
            raise ValueError('Managed pyATS source is missing: '+source)


def setup(target, python='3.12', preview=False, restore=False, rebuild=False):
    target = Path(target).expanduser().absolute()
    if target == Path(target.anchor) or target == Path.home():
        raise ValueError('Refusing unsafe runtime destination')
    previous = target.with_name(target.name+'.previous')
    if preview:
        print('Preview:', 'restore saved runtime' if restore else 'stage pinned source and Python runtime')
        print('Target:', target, '; recovery point:', previous)
        print('No files, packages, testbeds or environment settings changed.')
        return
    if restore:
        if not exists(previous):
            raise ValueError('No previous runtime exists')
        retained = target.with_name(target.name+'.retained-'+uuid.uuid4().hex)
        had_target = exists(target)
        if had_target:
            target.rename(retained)
        try:
            previous.rename(target)
        except BaseException:
            if had_target:
                retained.rename(target)
            raise
        print('Previous runtime restored; replaced generation retained at:', retained)
        return
    marker = target/MARKER
    if target.is_symlink() and marker.is_file() and not rebuild:
        if json.loads(marker.read_text()).get('revision') == REVISION:
            verify(target)
            print('Current managed pyATS runtime verifies; unchanged.')
            return
    if exists(previous):
        raise ValueError('Previous runtime retained; archive it deliberately before rebuilding')
    if exists(target) and not target.is_dir():
        raise ValueError('Runtime target must be a directory or valid directory symlink')
    uv = shutil.which('uv')
    if not uv:
        raise ValueError('Install uv before creating the isolated pyATS runtime')
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    candidate = Path(tempfile.mkdtemp(prefix='.'+target.name+'-generation-', dir=target.parent))
    link = target.with_name('.'+target.name+'-promote-'+uuid.uuid4().hex)
    promoted = False
    try:
        subprocess.run([uv, 'venv', str(candidate), '--python', python], check=True)
        source = candidate/'upstream'
        subprocess.run(['git', 'clone', '--no-checkout', REPOSITORY, str(source)], check=True)
        subprocess.run(['git', '-C', str(source), 'checkout', '--detach', REVISION], check=True)
        subprocess.run([uv, 'pip', 'install', '--python', str(candidate/'bin/python'),
                        '-r', str(source/'requirements.txt'), 'mcp==2.3.0'], check=True)
        verify(candidate)
        (candidate/MARKER).write_text(json.dumps({'revision':REVISION})+'\n')
        link.symlink_to(candidate, target_is_directory=True)
        had_target = exists(target)
        if had_target:
            target.rename(previous)
        try:
            os.replace(link, target)
        except BaseException:
            if had_target:
                previous.rename(target)
            raise
        promoted = True
        print('Verified pyATS source/runtime ready:', target)
        if had_target:
            print('Previous runtime retained:', previous)
    finally:
        if link.is_symlink():
            link.unlink()
        if not promoted:
            shutil.rmtree(candidate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', default=os.environ.get('PYATS_VENV', str(Path.home()/'.openclaw/pyats-venv')))
    parser.add_argument('--python', default=os.environ.get('PYATS_PYTHON', '3.12'))
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    try:
        setup(args.target, args.python, args.preview, args.restore, args.rebuild)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('pyATS setup stopped:', type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
