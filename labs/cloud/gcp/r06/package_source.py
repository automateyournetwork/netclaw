#!/usr/bin/env python3
"""Freeze the current R06 public source closure in a fresh private directory.

This is not an installer. It copies no runtime home, environment, credential,
private state, dependency directory or historical activation payload.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[4]
PREFIXES = ('scripts/', 'config/', 'mcp-servers/protocol-mcp/', 'mcp-servers/n2n-mcp/',
            'ui/netclaw-visual/', 'workspace/skills/subnet-calculator/', 'labs/cloud/gcp/r06/', 'docs/')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(output, node):
    output = Path(output)
    if not output.is_absolute() or output.resolve() != output:
        raise ValueError('canonical_private_destination_required')
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    source = output / 'source'
    source.mkdir()
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-co', '--exclude-standard', '-z']).decode().split('\0')
    for name in sorted(set(tracked)):
        if not name or not name.startswith(PREFIXES):
            continue
        original = ROOT / name
        if not original.is_file() or original.is_symlink() or any(
                part in ('.git', 'node_modules', '__pycache__', '.env') for part in Path(name).parts):
            continue
        if name.endswith(('.pyc', '.pem', '.key', '.tfstate')) or '.test.' in name:
            continue
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    shutil.copytree(ROOT / 'ui/netclaw-visual/dist', source / 'ui/netclaw-visual/dist', dirs_exist_ok=True)
    native = Path('mcp-servers/subnet-calculator-mcp/servers/subnetcalculator_mcp.py')
    target = source / native
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / native, target)
    spec = importlib.util.spec_from_file_location('bounded_subnet', ROOT / 'scripts/apply-subnet-summary.py')
    patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patcher)
    patched = patcher.apply(target.parent.parent)
    with (output / 'assets.log').open('x') as log:
        subprocess.run([str(node), str(ROOT / 'ui/netclaw-visual/scripts/protected-assets.mjs'),
                        '--dist', str(source / 'ui/netclaw-visual/dist'), '--output', str(output / 'hud-assets.json'),
                        '--workspace'], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    files = {}
    for path in source.rglob('*'):
        if path.is_symlink():
            raise ValueError('source_symlink_refused')
        if path.is_file():
            files[str(path.relative_to(source))] = digest(path)
            path.chmod(0o444)
    for path in sorted(source.rglob('*'), reverse=True):
        if path.is_dir():
            path.chmod(0o555)
    source.chmod(0o555)
    manifest = output / 'source-manifest.json'
    manifest.write_text(json.dumps({'schemaVersion': 1, 'files': files}, sort_keys=True))
    archive = output / 'source-r06.tar.gz'
    with tarfile.open(archive, 'w:gz') as stream:
        stream.add(source, arcname='source')
    receipt = dict(base_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip(),
                   working_changes_included=True, archive_sha256=digest(archive), manifest_sha256=digest(manifest),
                   assets_sha256=digest(output / 'hud-assets.json'), files=len(files), archive_bytes=archive.stat().st_size,
                   subnet_patch=patched, private_state_or_credentials_included=False)
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--node', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    print(json.dumps(package(args.output, args.node)))
