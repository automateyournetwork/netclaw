"""R09 multi-host Border preparation. Private local files only: no cloud, DNS or Docker call.

Adapts the R08 loopback preparation (`etcd_lab.py`, `real_runtime.prepare_identity/materialize`)
to three real hosts. Produces, under a fresh 0700 root, one deployable bundle per Border plus
the signed manifest. Offline enrollment key (`identity/root.key`) never enters a bundle.

Usage (from the repo root, with the protocol-mcp source on PYTHONPATH):
  python -m labs.ha.r09_prepare prepare --root ROOT \
      --node nne1=10.182.1.2,34.19.206.228 --node ew1=... --node ase1=...
Node order is the manifest order and the leader-preference order (first two are NA/EU).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import sys
import tarfile
import time
import uuid

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'mcp-servers/protocol-mcp'))
sys.path.insert(0, str(REPO))

from labs.ha.etcd_lab import certificate, private  # noqa: E402

DOMAIN = 'automateyournetwork.com'
VM_STATE = '/var/lib/nc182'
VM_SOURCE = '/opt/nc182/source'
VM_VENV = '/opt/nc182/venv'
PORTS = {'cluster': 7443, 'in2n': 7444, 'https': 443, 'edge': 8444, 'api': 8179, 'bgp': 1179}
# admission_ms: the admission clock starts at the member's challenge (ha/admission.py begin) and so includes the
# member->Border round trip plus the leader's cross-region etcd commit (~3 s observed here). The member's model handoff
# (ha/model_transport.py) then requires 250 < admission_ms - elapsed <= 3000, so the accepted elapsed window is
# [admission_ms-3000, admission_ms-250). Live finding: 6000 failed fast handoffs (<3 s), 3000 failed slow ones (>2.75 s).
# 4500 accepts 1.5 s .. 4.25 s, centred on the observed ~3 s.
LIMITS = {'leader_lease_s': 15, 'renewal_s': 5, 'admission_ms': 4500,
          'clock_uncertainty_ms': 250, 'max_operations': 1024, 'max_members': 32}
ETCD_HEARTBEAT_MS, ETCD_ELECTION_MS = 500, 5000
SOURCE_ROOTS = ('mcp-servers/protocol-mcp',)
SOURCE_EXTRA = ('scripts/federation-control.py', 'scripts/protected-role.py',
                'scripts/lib/protected_role.py', 'scripts/write-env.py', 'scripts/runtime-selection.py',
                'config/hermes-hud-compatibility.json')
SOURCE_SKIP_DIRS = {'tests', '__pycache__', '.pytest_cache'}
SOURCE_SKIP_SUFFIX = ('.md', '.pyc')


def need(value, code):
    if not value:
        raise SystemExit('refused:' + code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def private_canonical(path, value):
    """The role launcher pins raw file bytes, so hashed documents are written in canonical form."""
    private(path, canonical(value).encode())


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_dir(path):
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def source_files():
    """Closed Border import closure (python source only, no tests). Relative path -> absolute path."""
    files = {}
    for base in SOURCE_ROOTS:
        for path in sorted((REPO / base).rglob('*')):
            if (path.is_file() and not path.is_symlink()
                    and not any(part in SOURCE_SKIP_DIRS for part in path.relative_to(REPO).parts)
                    and not path.name.endswith(SOURCE_SKIP_SUFFIX) and path.name != 'pytest.ini'):
                files[str(path.relative_to(REPO))] = path
    for name in SOURCE_EXTRA:
        files[name] = REPO / name
    return files


def freeze_source(root):
    files = source_files()
    need(len(files) <= 20000 and sum(p.stat().st_size for p in files.values()) <= 64 * 1024 * 1024, 'source_bound')
    manifest = {'schemaVersion': 1, 'files': {name: sha256_file(p) for name, p in files.items()}}
    private(root / 'source-manifest.json', manifest)
    with tarfile.open(root / 'source.tar', 'w') as archive:
        for name, path in files.items():
            info = tarfile.TarInfo(name)
            raw = path.read_bytes()
            info.size = len(raw); info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
            info.mtime = 0; info.uid = info.gid = 0; info.uname = info.gname = 'root'
            archive.addfile(info, __import__('io').BytesIO(raw))
    return manifest, hashlib.sha256((root / 'source-manifest.json').read_bytes()).hexdigest()


def parse_nodes(values):
    nodes = []
    for value in values:
        code, _, rest = value.partition('=')
        internal, public = rest.split(',')
        need(re.fullmatch('[a-z0-9]{2,6}', code), 'node_code')
        socket.inet_aton(internal); socket.inet_aton(public)
        nodes.append({'code': code, 'internal': internal, 'public': public})
    need(len(nodes) == 3 and len({n['code'] for n in nodes}) == 3, 'three_nodes_required')
    return nodes


def prepare(args):
    from cryptography.hazmat.primitives import serialization
    from bgp.federation import protected_contract as c
    from bgp.federation.certs import create_self_signed
    from bgp.federation.ha.config import sign_manifest, verify_manifest
    from bgp.federation.ha.internal import border_binding
    from bgp.federation.manager import FederationManager
    from bgp.federation.risk import RiskManager

    root = Path(args.root).absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    nodes = parse_nodes(args.node)
    cluster_id, generation = str(uuid.uuid4()), str(uuid.uuid4())
    organization = args.organization
    identity = private_dir(root / 'identity')
    etcd = private_dir(root / 'etcd-pki')
    transport = private_dir(root / 'transport')

    # --- NCFED identity: offline enrollment anchor + one application key per Border -----
    anchor, anchor_key = create_self_signed('r09/offline-enrollment', days=args.days)
    private(identity / 'root.crt', anchor.encode()); private(identity / 'root.key', anchor_key.encode())
    for i, node in enumerate(nodes):
        node['installation_id'] = str(uuid.uuid4()); node['node_id'] = str(uuid.uuid4())
        node['id6'] = node['installation_id'][:6]
        node['dns'] = f"{node['code']}-{node['id6']}.{DOMAIN}"
        node['identity'] = f"{organization}-border-{node['code']}"
        crt, key = create_self_signed(f"r09/border-{node['code']}", days=args.days)
        node['crt'], node['key'] = crt, key
        private(identity / f'node{i}.crt', crt.encode()); private(identity / f'node{i}.key', key.encode())
    manifest_nodes = [{
        'node_id': n['node_id'], 'installation_id': n['installation_id'], 'identity': n['identity'],
        'key_id': c.key_id(n['crt']), 'certificate': n['crt'], 'role': 'border',
        'endpoints': {
            'cluster': {'host': n['internal'], 'port': PORTS['cluster'], 'server_name': n['dns']},
            'in2n': {'host': n['public'], 'port': PORTS['in2n'], 'server_name': n['dns']},
            'https': f"https://{n['dns']}", 'wss': f"wss://{n['dns']}/mobile/ws"}} for n in nodes]
    value = {'schema_version': 1, 'cluster_id': cluster_id, 'generation': generation,
             'organization': organization, 'revision': 1, 'nodes': manifest_nodes, 'limits': LIMITS}
    envelope = sign_manifest(value, anchor_key)
    verified = verify_manifest(envelope, anchor, expected_key_id=c.key_id(anchor))
    private(identity / 'manifest.json', envelope)

    # --- Separate transport CA; node certs carry the DNS server names ---------------------
    ca_key, ca = certificate(transport, 'transport-ca')
    for i, n in enumerate(nodes):
        key = serialization.load_pem_private_key(n['key'].encode(), password=None)
        certificate(transport, f'node{i}', issuer=ca, issuer_key=ca_key, key=key, names=(n['dns'], n['internal'], n['public']))
    member_key, member_cert = None, None  # members are generated by the member stage

    # --- etcd: separate client/peer CAs, server+peer certs per voter, per-Border users ----
    client_key, client_ca = certificate(etcd, 'client-ca')
    peer_key, peer_ca = certificate(etcd, 'peer-ca')
    certificate(etcd, 'admin', issuer_key=client_key, issuer=client_ca, names=('admin',), user=True)
    for i, n in enumerate(nodes):
        certificate(etcd, f'server{i}', issuer_key=client_key, issuer=client_ca,
                    names=(f'v{i}', 'localhost', '127.0.0.1', n['internal']))
        certificate(etcd, f'peer{i}', issuer_key=peer_key, issuer=peer_ca, names=(f'v{i}', n['internal']))
        certificate(etcd, f'border{i}', issuer_key=client_key, issuer=client_ca, names=(f'border{i}',), user=True)
    name = 'nc182-etcd-' + secrets.token_hex(4)
    prefix = f'/netclaw/ha/{cluster_id}/{generation}/'
    credentials = {n: secrets.token_urlsafe(32) for n in ('root', 'border0', 'border1', 'border2')}
    owned = {'schema_version': 1, 'name': name, 'cluster_id': cluster_id, 'generation': generation, 'prefix': prefix,
             'peers': [f"v{i}=https://{n['internal']}:2380" for i, n in enumerate(nodes)],
             'clients': [f"https://{n['internal']}:2379" for n in nodes],
             'heartbeat_ms': ETCD_HEARTBEAT_MS, 'election_ms': ETCD_ELECTION_MS}
    private(root / 'etcd-owned.json', owned); private(root / 'etcd-credentials.json', credentials)

    # --- Source closure and per-Border bundles -------------------------------------------
    source_manifest, source_manifest_sha = freeze_source(root)
    bundles = private_dir(root / 'bundles')
    summary = []
    anchor_id = c.key_id(anchor)
    for i, n in enumerate(nodes):
        b = private_dir(bundles / n['code'])
        home = private_dir(b / 'home')
        for child in ('n2n', 'netclaw-federation', 'netclaw-hud', 'n2n/keys'):
            private_dir(home / child)
        state = home / 'netclaw-federation'
        binding = border_binding(verified, n['node_id'])
        private(home / 'netclaw-hud/installation.json', {'schemaVersion': 1, 'installationId': n['installation_id']})
        private(state / 'owner.json', {'schemaVersion': 1, 'installationId': n['installation_id'], 'kind': 'openclaw',
                                       'home': f'{VM_STATE}/home'})
        private(state / 'ha-required.json', {'schema_version': 1, **verified.audience})
        old = os.umask(0o077)
        try:
            manager = FederationManager(base_dir=str(home / 'n2n'))
            RiskManager(manager).set_role('border', risk_name=organization, enabled_stacks='in2n', self_member_id=None)
            manager._conn.close()
        finally:
            os.umask(old)
        private(home / 'n2n/keys/self.crt', n['crt'].encode()); private(home / 'n2n/keys/self.key', n['key'].encode())
        for sub, fname in (('identity', 'manifest.json'), ('identity', 'root.crt'), ('transport', 'transport-ca.crt'),
                           ('transport', f'node{i}.crt'), ('transport', f'node{i}.key'),
                           ('etcd-pki', 'client-ca.crt'), ('etcd-pki', f'border{i}.crt'), ('etcd-pki', f'border{i}.key')):
            target = private_dir(b / (sub if sub != 'etcd-pki' else 'etcd-client'))
            private(target / (fname if not fname.startswith(('node', 'border')) else fname.replace(str(i), '') ),
                    (root / sub / fname).read_bytes())
        # Voter PKI for this host's etcd container.
        voter = private_dir(b / 'etcd-voter')
        for src, dst in (('client-ca.crt', 'client-ca.crt'), ('peer-ca.crt', 'peer-ca.crt'), (f'server{i}.crt', 'server.crt'),
                         (f'server{i}.key', 'server.key'), (f'peer{i}.crt', 'peer.crt'), (f'peer{i}.key', 'peer.key')):
            private(voter / dst, (etcd / src).read_bytes())
        if i == 0:  # bootstrap-only material, deleted from the VM after RBAC/authority bootstrap
            boot = private_dir(b / 'etcd-bootstrap')
            for fname in ('admin.crt', 'admin.key', 'client-ca.crt'):
                private(boot / fname, (etcd / fname).read_bytes())
            private(boot / 'credentials.json', credentials)
            private(boot / 'owned.json', owned)
        private(state / 'etcd-password', credentials[f'border{i}'].encode())
        private(state / 'protected-operator.env', ('NETCLAW_PROTECTED_OPERATOR_TOKEN=' + secrets.token_urlsafe(32) + '\n').encode())
        private(home / 'openclaw.json', {'netclaw': {'controlOnly': True}})
        order = [i] + [k for k in range(3) if k != i]
        config = {'schema_version': 1, 'role': 'border', 'manifest_file': f'{VM_STATE}/identity/manifest.json',
                  'anchor_certificate_file': f'{VM_STATE}/identity/root.crt', 'anchor_key_id': anchor_id,
                  'transport_ca_file': f'{VM_STATE}/transport/transport-ca.crt', 'node_id': n['node_id'],
                  'transport_certificate_file': f'{VM_STATE}/transport/node.crt',
                  'private_key_file': f'{VM_STATE}/transport/node.key',
                  'etcd': {'endpoints': [owned['clients'][k] for k in order],
                           'ca_file': f'{VM_STATE}/etcd-client/client-ca.crt',
                           'certificate_file': f'{VM_STATE}/etcd-client/border.crt',
                           'private_key_file': f'{VM_STATE}/etcd-client/border.key',
                           'username': f'border{i}', 'password_file': f'{VM_STATE}/home/netclaw-federation/etcd-password'}}
        private_canonical(state / 'ha-config.json', config)
        profile = {'schemaVersion': 2, 'role': 'border', 'identity': binding, 'access': {'mode': 'open-lab'},
                   'ha': {'config_file': f'{VM_STATE}/home/netclaw-federation/ha-config.json', 'config_sha256': digest(config)}}
        private_canonical(state / 'protected-profile.json', profile)
        environment = {'NETCLAW_LOCAL_AS': str(65182 + i), 'NETCLAW_ROUTER_ID': f'127.0.0.{i + 1}',
                       'N2N_DISPLAY_NAME': n['dns'], 'BGP_API_PORT': str(PORTS['api']),
                       'N2N_INVENTORY_REFRESH_S': '0', 'N2N_EDGE_WS_PORT': str(PORTS['edge']),
                       'BGP_LISTEN_PORT': str(PORTS['bgp'])}
        contract = {'schemaVersion': 3, 'installation_id': n['installation_id'], 'role': 'border', 'runtime_kind': 'openclaw',
                    'control_only': True, 'home': f'{VM_STATE}/home', 'source_root': VM_SOURCE,
                    'python': f'{VM_VENV}/bin/python', 'python_sha256': '@VM', 'python_env': VM_VENV,
                    'python_env_manifest': f'{VM_STATE}/manifests/python-env-manifest.json',
                    'python_env_manifest_sha256': '@VM',
                    'source_manifest': f'{VM_STATE}/manifests/source-manifest.json',
                    'source_manifest_sha256': source_manifest_sha, 'profile_sha256': digest(profile),
                    'origin': f"https://{n['dns']}", 'environment': environment}
        private(b / 'contract.template.json', contract)
        private(b / 'node.json', {**{k: n[k] for k in ('code', 'internal', 'public', 'installation_id', 'node_id', 'id6', 'dns')},
                                   'index': i, 'anchor_key_id': anchor_id})
        # Single self-contained tarball, extracted on the VM as the service user.
        with tarfile.open(bundles / f'{n["code"]}.tar', 'w') as archive:
            archive.add(b, arcname='.', recursive=True)
        summary.append({k: n[k] for k in ('code', 'internal', 'public', 'installation_id', 'id6', 'dns')})
    private(root / 'summary.json', {'schema_version': 1, 'cluster_id': cluster_id, 'generation': generation,
        'manifest_sha256': c.sha256(verified.value), 'anchor_key_id': anchor_id, 'limits': LIMITS,
        'etcd': {'heartbeat_ms': ETCD_HEARTBEAT_MS, 'election_ms': ETCD_ELECTION_MS},
        'source_files': len(source_manifest['files']), 'nodes': summary, 'prepared_at': time.time()})
    return json.loads((root / 'summary.json').read_text())


def refreeze(args):
    """Re-freeze the source closure into an existing root: new manifest/tar, bundle contract templates, tarballs."""
    root = Path(args.root).absolute()
    for stale in ('source-manifest.json', 'source.tar'):
        (root / stale).unlink()
    manifest, sha = freeze_source(root)
    for tarball in sorted((root / 'bundles').glob('*.tar')):
        code = tarball.stem
        bundle = root / 'bundles' / code
        template = json.loads((bundle / 'contract.template.json').read_text())
        template['source_manifest_sha256'] = sha
        (bundle / 'contract.template.json').write_bytes(canonical(template).encode())
        tarball.unlink()
        with tarfile.open(tarball, 'w') as archive:
            archive.add(bundle, arcname='.', recursive=True)
    return {'source_files': len(manifest['files']), 'source_manifest_sha256': sha}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--root', required=True)
    p.add_argument('--node', action='append', required=True, help='code=internal_ip,public_ip')
    p.add_argument('--organization', default='nc182-r09')
    p.add_argument('--days', type=int, default=7)
    r = sub.add_parser('refreeze')
    r.add_argument('--root', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args) if args.action == 'prepare' else refreeze(args), indent=2))


if __name__ == '__main__':
    main()
