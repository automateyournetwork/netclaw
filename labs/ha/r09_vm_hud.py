#!/usr/bin/env python3
"""R09 on-VM HUD freeze + ingress preparation (run as root, stdlib only).

  sudo python3 r09_vm_hud.py --hud-tar /tmp/hud-source.tar --cert /tmp/fullchain.pem --key /tmp/key.pem

1. Extract the HUD closure to /opt/nc182/hud-source, `npm ci --omit=dev --ignore-scripts`, drop symlinks
   (the ingress refuses aliases), write the closure manifest, then freeze root-owned/no-write.
2. Install the TLS chain/key for the service user, write the ingress INPUT.json from node.json and run
   `hud_ingress_r09.mjs prepare` as nc182 (computes pins, writes ingress.json, validates, starts nothing).
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
ROOT = Path('/opt/nc182/hud-source')
NODE = Path('/opt/nc182/node/bin/node')
NPM = Path('/opt/nc182/node/bin/npm')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hud-tar', required=True)
    parser.add_argument('--cert', required=True)
    parser.add_argument('--key', required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0
    user = pwd.getpwnam('nc182')
    node_info = json.loads((STATE / 'node.json').read_text())
    summary_cluster = json.loads((STATE / 'cluster.json').read_text())

    if ROOT.exists():
        subprocess.run(['chmod', '-R', 'u+w', str(ROOT)], check=True)
        shutil.rmtree(ROOT)
    ROOT.mkdir(mode=0o755, parents=True)
    with tarfile.open(args.hud_tar) as archive:
        archive.extractall(ROOT, filter='data')
    env = {'PATH': f'{NODE.parent}:/usr/bin:/bin', 'HOME': '/root', 'npm_config_cache': '/root/.npm'}
    subprocess.run([str(NPM), 'ci', '--omit=dev', '--ignore-scripts', '--no-audit', '--no-fund'],
                   cwd=ROOT / 'ui/netclaw-visual', env=env, check=True, capture_output=True)
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        for name in list(dirs) + list(files):
            p = Path(directory) / name
            if p.is_symlink():
                p.unlink()
                if name in dirs:
                    dirs.remove(name)
    files = {}
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            files[str(p.relative_to(ROOT))] = sha(p)
    manifests = STATE / 'manifests'
    manifests.mkdir(mode=0o700, exist_ok=True)
    manifest_file = manifests / 'hud-source-manifest.json'
    manifest_file.write_text(json.dumps({'schemaVersion': 1, 'files': files}, sort_keys=True, separators=(',', ':')))
    # Freeze: root-owned, no write bits.
    for directory, dirs, names in os.walk(ROOT, followlinks=False):
        os.chown(directory, 0, 0)
        for name in names:
            p = Path(directory) / name
            os.chown(p, 0, 0)
            os.chmod(p, 0o555 if stat.S_IMODE(p.stat().st_mode) & 0o111 else 0o444)
    for directory, _, _ in os.walk(ROOT, topdown=False, followlinks=False):
        os.chmod(directory, 0o555)

    tls = STATE / 'tls'
    tls.mkdir(mode=0o700, exist_ok=True)
    for src, dst in ((args.cert, tls / 'fullchain.pem'), (args.key, tls / 'key.pem')):
        if Path(src).resolve() != dst.resolve():
            shutil.copy(src, dst)
    hud_state = STATE / 'hud'
    hud_state.mkdir(mode=0o700, exist_ok=True)
    for stale in hud_state.iterdir():  # pins/claims are write-once per prepare; keep only the input
        if stale.is_file() and stale.name != 'input.json':
            stale.unlink()
    data = {
        'origin': 'https://' + node_info['dns'], 'bind': '0.0.0.0', 'port': 443,
        'installation_id': node_info['installation_id'], 'home': str(STATE / 'home'),
        'source_root': str(ROOT), 'source_manifest_file': str(manifest_file),
        'dist': str(ROOT / 'ui/netclaw-visual/dist'), 'edge_ws_port': 8444,
        'manifest_file': str(STATE / 'identity/manifest.json'),
        'anchor_certificate_file': str(STATE / 'identity/root.crt'),
        'anchor_key_id': node_info['anchor_key_id'],
        'cluster': {'cluster_id': summary_cluster['cluster_id'], 'generation': summary_cluster['generation'],
                    'anchor_key_id': node_info['anchor_key_id']},
        'tls': {'cert_file': str(tls / 'fullchain.pem'), 'chain_file': None, 'key_file': str(tls / 'key.pem')},
        'state_dir': str(hud_state)}
    workspace = STATE / 'workspace/workspace.json'
    if workspace.exists():  # full workspace enabled: pinned edge copy written by scripts/ha-r09-vm-workspace.sh
        data['workspace'] = {'path': str(workspace)}
    (hud_state / 'input.json').write_text(json.dumps(data, sort_keys=True, separators=(',', ':')))
    for directory, dirs, names in os.walk(STATE):
        os.chown(directory, user.pw_uid, user.pw_gid); os.chmod(directory, 0o700)
        for name in names:
            p = Path(directory) / name
            os.chown(p, user.pw_uid, user.pw_gid); os.chmod(p, 0o600)
    result = subprocess.run(['sudo', '-u', 'nc182', '-H', str(NODE), str(ROOT / 'labs/ha/hud_ingress_r09.mjs'),
                             'prepare', str(hud_state / 'input.json')], capture_output=True, text=True)
    print(json.dumps({'files': len(files), 'prepare_exit': result.returncode,
                      'stdout': result.stdout[-400:], 'stderr': result.stderr[-400:]}))


if __name__ == '__main__':
    main()
