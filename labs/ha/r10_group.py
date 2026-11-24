#!/usr/bin/env python3
"""Cloud-neutral naming and spec generation for one R10 HA group (spec 198). Pure functions; no cloud or network access.

An HA group is three Borders (codes nne1/ew1/ase1) of ONE provider (azure or gcp). The sandbox policy needs, per node, the
two REMOTE voters as `<internal-name>:12379` plus an exact private-IP `resolve` map (r09a_policy.build_policy):
  azure: `az{ca,us,se}.r10-<YYYYMMDD>.azure.internal`  (private DNS zone created by ha-r10-build-group.sh zone)
  gcp  : `<instance>.<zone>.c.<project>.internal`      (GCE zonal internal DNS; no zone to create)

  r10_group.py node-spec --provider P --run-date D --nodes FILE --code C [--project X --vm-prefix Y]
  r10_group.py prepare-args --provider P --run-date D --nodes FILE [...]
  r10_group.py peer-config --local-root GEN --peer-root GEN --label NAME --out DIR [--members M..] [--tools T..]
  r10_group.py node-spec ... --peer-summary PEER/summary.json   (adds the cross-group federation egress for that group)
FILE lines: `<code> <public-ip> <private-ip>` (the same nodes.txt the build script writes).
"""
import argparse
import json
from pathlib import Path
import re
import sys

CODES = ('nne1', 'ew1', 'ase1')
AZURE_NAMES = {'nne1': 'azca', 'ew1': 'azus', 'ase1': 'azse'}
GCP_ZONES = {'nne1': 'northamerica-northeast1-b', 'ew1': 'europe-west1-b', 'ase1': 'asia-southeast1-a'}
IP = re.compile(r'^(?:\d{1,3}\.){3}\d{1,3}$')
DATE = re.compile(r'^[0-9]{8}$')
PYTHON = '/usr/local/bin/python3.12'


def read_nodes(text):
    nodes = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith('#'):
            continue
        if len(parts) != 3 or parts[0] not in CODES or not IP.match(parts[1]) or not IP.match(parts[2]):
            raise ValueError('invalid_nodes_line')
        if parts[0] in nodes:
            raise ValueError('duplicate_node')
        nodes[parts[0]] = {'public': parts[1], 'private': parts[2]}
    if set(nodes) != set(CODES):
        raise ValueError('three_nodes_required')
    return nodes


def internal_host(provider, code, run_date, project=None, vm_prefix=None):
    if code not in CODES:
        raise ValueError('unknown_code')
    if provider == 'azure':
        if not DATE.match(run_date or ''):
            raise ValueError('run_date_required')
        return '%s.r10-%s.azure.internal' % (AZURE_NAMES[code], run_date)
    if provider == 'gcp':
        if not project or not vm_prefix:
            raise ValueError('project_and_vm_prefix_required')
        return '%s-%s.%s.c.%s.internal' % (vm_prefix, code, GCP_ZONES[code], project)
    raise ValueError('unknown_provider')


FEDERATION_PORT = 7445
STATE = '/sandbox/nc182'
FULL_ACTIONS = ['catalog', 'prepare', 'decision', 'status', 'reconcile', 'revoke']


def federation_endpoints(peer_summaries):
    """[(dns, public_ip)] for every Border of every peer group (the egress the sandbox policy must allow on one port)."""
    out = []
    for summary in peer_summaries:
        for node in summary['nodes']:
            out.append((node['dns'], node['public']))
    return out


def node_spec(provider, code, nodes, run_date=None, project=None, vm_prefix=None, peer_summaries=()):
    """The r09a_policy node spec: two remote voters only, exact private IPs, qualified python."""
    others = [o for o in CODES if o != code]
    hosts = {o: internal_host(provider, o, run_date, project, vm_prefix) for o in others}
    spec = {'node': code, 'etcd': [hosts[o] + ':12379' for o in others], 'peers': [hosts[o] + ':7443' for o in others],
            'anthropic': True, 'binaries': {'python': PYTHON},
            'resolve': {hosts[o]: nodes[o]['private'] for o in others}}
    federation = federation_endpoints(peer_summaries)
    if federation:
        spec['federation_peers'] = ['%s:%d' % (dns, FEDERATION_PORT) for dns, _ in federation]
        spec['resolve'].update({dns: ip for dns, ip in federation})
    return spec


def peer_config(local_root, peer_root, label, *, members=('*',), tools=('*',), actions=None, state=STATE):
    """(config, files) for ONE Border's private `peer-federation.json` pinning the peer group.

    The peer is pinned by its offline-anchor-signed manifest + anchor certificate (public parts only) and its transport CA.
    Grants are inbound: what the PEER may do on THIS group's members. Default is everything; narrow with members/tools/actions."""
    local_root, peer_root = Path(local_root), Path(peer_root)
    summary = json.loads((peer_root / 'summary.json').read_text())
    local = json.loads((local_root / 'summary.json').read_text())
    if summary['cluster_id'] == local['cluster_id']:
        raise ValueError('peer_is_local_cluster')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', label):
        raise ValueError('invalid_label')
    files = {
        'peer/%s/manifest.json' % label: (peer_root / 'identity/manifest.json').read_bytes(),
        'peer/%s/root.crt' % label: (peer_root / 'identity/root.crt').read_bytes(),
        'peer/%s/transport-ca.crt' % label: (peer_root / 'transport/transport-ca.crt').read_bytes()}
    files['peer/peer-ca-bundle.pem'] = files['peer/%s/transport-ca.crt' % label]
    config = {'schema_version': 1, 'listen': {'host': '127.0.0.1', 'port': FEDERATION_PORT}, 'dial_port': FEDERATION_PORT,
              'transport_certificate_file': state + '/transport/node.crt', 'private_key_file': state + '/transport/node.key',
              'peer_ca_bundle_file': state + '/peer/peer-ca-bundle.pem',
              'peers': [{'label': label, 'cluster_id': summary['cluster_id'], 'generation': summary['generation'],
                         'manifest_file': state + '/peer/%s/manifest.json' % label,
                         'anchor_certificate_file': state + '/peer/%s/root.crt' % label, 'anchor_key_id': summary['anchor_key_id'],
                         'transport_ca_file': state + '/peer/%s/transport-ca.crt' % label,
                         'grant': {'actions': list(actions or FULL_ACTIONS), 'members': list(members), 'tools': list(tools)}}]}
    return config, files


def merge_peer_configs(parts):
    """One config for several peer groups: peers concatenated, CA bundle = every peer transport CA."""
    config, files = None, {}
    bundle = b''
    for part_config, part_files in parts:
        config = part_config if config is None else dict(config, peers=config['peers'] + part_config['peers'])
        files.update({k: v for k, v in part_files.items() if k != 'peer/peer-ca-bundle.pem'})
        bundle += part_files['peer/peer-ca-bundle.pem'].rstrip(b'\n') + b'\n'
    files['peer/peer-ca-bundle.pem'] = bundle
    return config, files


def prepare_args(provider, nodes, run_date=None, project=None, vm_prefix=None):
    """`--node code=<private>,<public>,<internal-name>` arguments for r10_prepare.py prepare (the third field is the
    etcd/peer TLS name, so the server certificate carries the exact internal host)."""
    out = []
    for code in CODES:
        out += ['--node', '%s=%s,%s,%s' % (code, nodes[code]['private'], nodes[code]['public'],
                                           internal_host(provider, code, run_date, project, vm_prefix))]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=('node-spec', 'prepare-args', 'peer-config'))
    ap.add_argument('--provider', choices=('azure', 'gcp'))
    ap.add_argument('--run-date'); ap.add_argument('--nodes'); ap.add_argument('--code')
    ap.add_argument('--project'); ap.add_argument('--vm-prefix')
    ap.add_argument('--peer-summary', action='append', default=[])
    ap.add_argument('--local-root'); ap.add_argument('--peer-root', action='append', default=[]); ap.add_argument('--label', action='append', default=[])
    ap.add_argument('--out'); ap.add_argument('--members', nargs='*', default=['*']); ap.add_argument('--tools', nargs='*', default=['*'])
    a = ap.parse_args(argv)
    if a.verb == 'peer-config':
        if not (a.local_root and a.out and a.peer_root and len(a.peer_root) == len(a.label)):
            ap.error('--local-root, --out and matching --peer-root/--label pairs are required')
        config, files = merge_peer_configs([peer_config(a.local_root, root, label, members=a.members, tools=a.tools)
                                            for root, label in zip(a.peer_root, a.label)])
        out = Path(a.out); out.mkdir(mode=0o700, parents=True, exist_ok=True)
        for name, raw in dict(files, **{'peer-federation.json': json.dumps(config, sort_keys=True, separators=(',', ':')).encode()}).items():
            target = out / name; target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(raw); target.chmod(0o600)
        print(json.dumps({'out': str(out), 'peers': [p['label'] for p in config['peers']], 'files': sorted(files)}))
        return
    if not (a.provider and a.nodes):
        ap.error('--provider and --nodes are required')
    nodes = read_nodes(open(a.nodes, encoding='utf-8').read())
    summaries = [json.loads(Path(p).read_text()) for p in a.peer_summary]
    if a.verb == 'node-spec':
        if not a.code:
            ap.error('--code required')
        print(json.dumps(node_spec(a.provider, a.code, nodes, a.run_date, a.project, a.vm_prefix, summaries), sort_keys=True))
    else:
        print(' '.join(prepare_args(a.provider, nodes, a.run_date, a.project, a.vm_prefix)))


if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        sys.exit('refused: %s' % exc)
