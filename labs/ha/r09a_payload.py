#!/usr/bin/env python3
"""R09A: assemble one node's sandbox upload payload (tar rooted at nc182/) from an r09_prepare root.

  python -m labs.ha.r09a_payload --root ROOT --code nne1 --dns nne1-<id6>.automateyournetwork.com

Contents: the identity bundle (home/, identity/, transport/, etcd-client/, etcd-bootstrap/ on the first node,
contract.template.json, node.json), cluster.json, tls/{fullchain.pem,key.pem} (lego), policy.sha256 and the in-sandbox runner
and etcd bootstrap script. etcd-voter material stays host-side (not in the payload). Private modes (0700/0600).
"""
import argparse
import io
import json
from pathlib import Path
import tarfile

REPO = Path(__file__).resolve().parents[2]


def build(root, code, dns, policy_dir=None):
    root = Path(root)
    summary = json.loads((root / 'summary.json').read_text())
    policy_dir = Path(policy_dir) if policy_dir else root / 'policy' / f'out-{code}'
    sha = next(line for line in (policy_dir / 'policy.yaml').read_text().splitlines() if 'content sha256' in line).split(': ')[-1]
    out = root / f'node-{code}.tar'
    with tarfile.open(root / 'bundles' / f'{code}.tar') as bundle, tarfile.open(out, 'w') as tar:
        for member in bundle.getmembers():
            name = member.name.lstrip('./')
            if not name or name.startswith('etcd-voter'):
                continue
            info = tarfile.TarInfo('nc182/' + name)
            if member.isdir():
                info.type, info.mode = tarfile.DIRTYPE, 0o700
                tar.addfile(info)
            elif member.isfile():
                data = bundle.extractfile(member).read()
                info.size, info.mode = len(data), 0o600
                tar.addfile(info, io.BytesIO(data))

        def add(name, data, mode=0o600):
            info = tarfile.TarInfo('nc182/' + name)
            info.size, info.mode = len(data), mode
            tar.addfile(info, io.BytesIO(data))
        lego = root / f'lego-{code}' / 'certificates'
        add('cluster.json', json.dumps({'cluster_id': summary['cluster_id'], 'generation': summary['generation']}).encode())
        add('tls/fullchain.pem', (lego / f'{dns}.crt').read_bytes())
        add('tls/key.pem', (lego / f'{dns}.key').read_bytes())
        add('policy.sha256', sha.encode())
        add('bin/r09a_node_run.py', (REPO / 'labs/ha/r09a_node_run.py').read_bytes(), 0o700)
        add('bin/etcd_bootstrap.py', (REPO / 'labs/ha/r09_vm_etcd_bootstrap.py').read_bytes(), 0o700)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--code', required=True)
    parser.add_argument('--dns', required=True)
    parser.add_argument('--policy-dir')
    args = parser.parse_args()
    print(build(args.root, args.code, args.dns, args.policy_dir))
