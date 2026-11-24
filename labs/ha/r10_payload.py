#!/usr/bin/env python3
"""R10 (spec 198): one node's sandbox upload payload = the R09A payload plus the full-stack R10 runner.

  python -m labs.ha.r10_payload --root ROOT --code nne1 --dns nne1-<id6>.automateyournetwork.com

r10_node_run.py imports r09a_node_run (its base), so both must sit in nc182/bin/. The R09A builder is reused unchanged.
"""
import argparse
import io
import json
import secrets
from pathlib import Path
import tarfile
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from labs.ha import r09a_payload  # noqa: E402


def build(root, code, dns, policy_dir=None, guard_config=None, workspace_config=None, peer_dir=None, region=None):
    out = Path(r09a_payload.build(root, code, dns, policy_dir))
    with tarfile.open(out, 'a') as tar:
        def add(name, raw, mode=0o600):
            info = tarfile.TarInfo('nc182/' + name)
            info.size, info.mode = len(raw), mode
            tar.addfile(info, io.BytesIO(raw))
        if region:
            # Observed cloud placement is display metadata, never execution authority.
            with tarfile.open(out, 'r') as original:
                node = json.load(original.extractfile('nc182/node.json'))
            node['region'] = region
            add('node.json', json.dumps(node).encode())
        add('bin/r10_node_run.py', (REPO / 'labs/ha/r10_node_run.py').read_bytes(), 0o700)
        add('bin/r09a_guard_up.sh', (REPO / 'labs/ha/r09a_guard_up.sh').read_bytes(), 0o700)
        add('gateway-token', secrets.token_hex(24).encode())
        if guard_config:
            add('guard-config.yaml', Path(guard_config).read_bytes())
        if workspace_config:
            add('workspace.json', Path(workspace_config).read_bytes())
        if peer_dir:   # spec 198: `r10_group.py peer-config` output; the Border enables federation only if this file exists
            base = Path(peer_dir)
            for path in sorted(base.rglob('*')):
                if path.is_file():
                    rel = path.relative_to(base).as_posix()
                    add('home/netclaw-federation/peer-federation.json' if rel == 'peer-federation.json' else rel, path.read_bytes())
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True); p.add_argument('--code', required=True)
    p.add_argument('--dns', required=True); p.add_argument('--policy-dir')
    p.add_argument('--guard-config'); p.add_argument('--workspace-config'); p.add_argument('--peer-dir')
    p.add_argument('--region', help='observed cloud region for posture display only')
    a = p.parse_args()
    print(build(a.root, a.code, a.dns, a.policy_dir, a.guard_config, a.workspace_config, a.peer_dir, a.region))
