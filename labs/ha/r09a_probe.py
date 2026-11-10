#!/usr/bin/env python3
"""R09A cluster probe: authority state of each public Border as the HUD ingress reports it (stdlib, read-only).
  python3 labs/ha/r09a_probe.py [--watch SECONDS]
Reads summary.json from the R09A run directory for the node list and cluster identity."""
import json
import os
import sys
import time
import urllib.request

RUN = os.path.expanduser(os.environ.get('R09A_RUN', '~/.local/share/netclaw/r09a2-20261110'))


def probe(summary):
    out = {}
    for node in summary['nodes']:
        req = urllib.request.Request(f"https://{node['dns']}/api/hud/cluster", headers={
            'X-NetClaw-Installation': node['installation_id'], 'X-NetClaw-Cluster-ID': summary['cluster_id'],
            'X-NetClaw-Cluster-Generation': summary['generation']})
        t0 = time.time()
        try:
            body = json.load(urllib.request.urlopen(req, timeout=10))
            auth = body.get('authority') or {}
            out[node['code']] = {'state': auth.get('state'), 'leader': auth.get('leader_node_id'), 'epoch': auth.get('epoch'),
                                 'ms': int((time.time() - t0) * 1000)}
        except Exception as exc:
            out[node['code']] = {'state': 'unreachable', 'error': type(exc).__name__, 'ms': int((time.time() - t0) * 1000)}
    return out


def main():
    summary = json.load(open(os.path.join(RUN, 'summary.json')))
    names = {}
    watch = float(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == '--watch' else 0
    end = time.time() + watch
    while True:
        print(json.dumps({'t': round(time.time(), 1), **probe(summary)}, sort_keys=True), flush=True)
        if time.time() >= end:
            break
        time.sleep(2)


if __name__ == '__main__':
    main()
