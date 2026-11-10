#!/usr/bin/env python3
"""R09 on-VM source-only update (run as root with the 3.12 venv python). Leaves Border state untouched.

  sudo /opt/nc182/venv/bin/python -B r09_vm_source.py --source-tar /tmp/source.tar \
      --source-manifest-file /tmp/source-manifest.json --source-manifest-sha256 <hex>

Stop nc182-hud and nc182-border first. Replaces only the frozen /opt/nc182/source closure, the pinned
source-manifest.json and the `source_manifest_sha256` field of /var/lib/nc182/contract.json. Unlike
r09_vm_finalize.py it does NOT re-extract the identity bundle, so the Border's home, federation database,
etcd client material and results stay as they are.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tarfile

STATE = Path('/var/lib/nc182')
SOURCE = Path('/opt/nc182/source')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze_tree(root):
    for directory, dirs, files in os.walk(root, followlinks=False):
        os.chown(directory, 0, 0)
        for name in files:
            p = Path(directory) / name
            if p.is_symlink():
                continue
            os.chown(p, 0, 0)
            os.chmod(p, 0o555 if p.stat().st_mode & 0o111 else 0o444)
    for directory, _, _ in os.walk(root, topdown=False, followlinks=False):
        os.chmod(directory, 0o555)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-tar', required=True)
    parser.add_argument('--source-manifest-file', required=True)
    parser.add_argument('--source-manifest-sha256', required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0, 'run as root'
    assert sha(args.source_manifest_file) == args.source_manifest_sha256, 'source manifest changed in transit'
    user = pwd.getpwnam('nc182')
    subprocess.run(['chmod', '-R', 'u+w', str(SOURCE)], check=True)
    shutil.rmtree(SOURCE)
    SOURCE.mkdir(mode=0o755, parents=True)
    with tarfile.open(args.source_tar) as archive:
        archive.extractall(SOURCE, filter='data')
    freeze_tree(SOURCE)
    target = STATE / 'manifests/source-manifest.json'
    shutil.copy(args.source_manifest_file, target)
    os.chown(target, user.pw_uid, user.pw_gid)
    os.chmod(target, 0o600)
    contract_path = STATE / 'contract.json'
    contract = json.loads(contract_path.read_text())
    contract['source_manifest_sha256'] = args.source_manifest_sha256
    contract_path.write_text(json.dumps(contract, sort_keys=True, separators=(',', ':')))
    os.chown(contract_path, user.pw_uid, user.pw_gid)
    os.chmod(contract_path, 0o600)
    print(json.dumps({'source_files': sum(1 for p in SOURCE.rglob('*') if p.is_file()),
                      'source_manifest_sha256': args.source_manifest_sha256}))


if __name__ == '__main__':
    main()
