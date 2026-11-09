#!/usr/bin/env python3
"""R09 on-VM finalize (run as root, stdlib only). Freezes source + Python env, writes the role contract.

  sudo python3 r09_vm_finalize.py --source-tar /tmp/source.tar --bundle /tmp/<code>.tar \
      --source-manifest-sha256 <hex> [--refreeze]

- /opt/nc182/source: root-owned, dirs 0555, files 0444 (0555 if executable), exactly the manifest closure.
- /opt/nc182/venv + python: root-owned, no group/other write; env manifest of every file/symlink.
- /var/lib/nc182: bundle extracted and owned by the nc182 service user (private 0600/0700).
- contract.json written from the template with the real python/env digests filled in.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import tarfile

STATE = Path('/var/lib/nc182')
SOURCE = Path('/opt/nc182/source')
VENV = Path('/opt/nc182/venv')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def freeze_tree(root, *, executable_keep=True):
    for directory, dirs, files in os.walk(root, followlinks=False):
        os.chown(directory, 0, 0)
        for name in files:
            p = Path(directory) / name
            if p.is_symlink():
                continue
            os.chown(p, 0, 0)
            mode = stat.S_IMODE(p.lstat().st_mode)
            os.chmod(p, 0o555 if mode & 0o111 else 0o444)
    for directory, dirs, files in os.walk(root, topdown=False, followlinks=False):
        os.chmod(directory, 0o555)


def env_manifest():
    files, links = {}, {}
    for directory, dirs, names in os.walk(VENV, followlinks=False):
        for name in dirs + names:
            p = Path(directory) / name
            rel = str(p.relative_to(VENV))
            if p.is_symlink():
                links[rel] = os.readlink(p)
            elif p.is_file():
                files[rel] = sha(p)
    return {'schemaVersion': 1, 'files': files, 'symlinks': links}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-tar', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--source-manifest-sha256', required=True)
    parser.add_argument('--source-manifest-file', required=True)
    parser.add_argument('--refreeze', action='store_true')
    args = parser.parse_args()
    assert os.geteuid() == 0, 'run as root'
    user = pwd.getpwnam('nc182')

    # Source closure
    if SOURCE.exists():
        assert args.refreeze, 'source exists; pass --refreeze to replace it'
        subprocess.run(['chmod', '-R', 'u+w', str(SOURCE)], check=True)
        shutil.rmtree(SOURCE)
    SOURCE.mkdir(mode=0o755, parents=True)
    with tarfile.open(args.source_tar) as archive:
        archive.extractall(SOURCE, filter='data')
    freeze_tree(SOURCE)

    # Bundle -> /var/lib/nc182 (service-owned, private)
    STATE.mkdir(mode=0o700, exist_ok=True)
    with tarfile.open(args.bundle) as archive:
        archive.extractall(STATE, filter='data')
    manifests = STATE / 'manifests'
    manifests.mkdir(mode=0o700, exist_ok=True)
    shutil.copy(args.source_manifest_file, manifests / 'source-manifest.json')
    assert sha(manifests / 'source-manifest.json') == args.source_manifest_sha256, 'source manifest changed'

    # Python env: root-owned, immutable, manifested
    for directory, dirs, files in os.walk(VENV, followlinks=False):
        os.chown(directory, 0, 0)
        for name in files:
            p = Path(directory) / name
            if not p.is_symlink():
                os.chown(p, 0, 0)
    subprocess.run(['chmod', '-R', 'go-w,u-w', str(VENV)], check=True)
    for directory, _, _ in os.walk(VENV, followlinks=False):
        os.chmod(directory, 0o555)
    manifest = env_manifest()
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
    (manifests / 'python-env-manifest.json').write_bytes(raw)
    env_sha = hashlib.sha256(raw).hexdigest()

    python = VENV / 'bin/python'
    python_sha = sha(python.resolve())

    contract = json.loads((STATE / 'contract.template.json').read_text())
    contract['python_sha256'] = python_sha
    contract['python_env_manifest_sha256'] = env_sha
    assert contract['source_manifest_sha256'] == args.source_manifest_sha256
    (STATE / 'contract.json').write_text(json.dumps(contract, sort_keys=True, separators=(',', ':')))

    for directory, dirs, files in os.walk(STATE):
        os.chown(directory, user.pw_uid, user.pw_gid); os.chmod(directory, 0o700)
        for name in files:
            p = Path(directory) / name
            os.chown(p, user.pw_uid, user.pw_gid); os.chmod(p, 0o600)
    print(json.dumps({'python_sha256': python_sha, 'python_env_manifest_sha256': env_sha,
                      'source_files': sum(1 for _ in SOURCE.rglob('*') if _.is_file()),
                      'env_files': len(manifest['files']), 'env_links': len(manifest['symlinks'])}))


if __name__ == '__main__':
    main()
