"""Disposable NetClaw R08 voters. Prepare first; preserve partial/unknown starts.

The manifest records every intended owned name before Docker mutations. Startup
is one-shot. Cleanup is an explicit separate action after evidence export.
No existing runtime, network, trust store, cloud resource or secret is adopted.
"""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import ssl
import subprocess
import time
import uuid

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

REPO = Path(__file__).resolve().parents[2]
LOCK = json.loads((Path(__file__).parent / 'dependencies.json').read_text())
IMAGE = LOCK['etcd']['image']


def private(path, data):
    path = Path(path)
    raw = data if isinstance(data, bytes) else json.dumps(data, indent=2).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def command(root, stage, args, timeout=40):
    # Arguments contain only file references, never credential values.
    record = {'stage': stage, 'args': args, 'started': datetime.now(timezone.utc).isoformat()}
    private(root / (stage + '.started.json'), record)
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        private(root / (stage + '.unknown.json'), {'state': 'outcome_unknown'})
        raise RuntimeError('owned_command_outcome_unknown') from None
    private(root / (stage + '.stdout'), result.stdout)
    private(root / (stage + '.stderr'), result.stderr)
    private(root / (stage + '.result.json'), {'returncode': result.returncode})
    if result.returncode:
        raise RuntimeError('owned_command_failed:' + stage)
    return result.stdout.decode().strip()


def certificate(root, name, *, issuer_key=None, issuer=None, names=(), user=False, key=None):
    key = key or ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME if user else NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    builder = (x509.CertificateBuilder().subject_name(subject)
               .issuer_name(issuer.subject if issuer else subject).public_key(key.public_key())
               .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
               .not_valid_after(now + timedelta(days=3))
               .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=0 if issuer is None else None), True)
               .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
               .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key((issuer_key or key).public_key()), False)
               .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                    key_encipherment=False, data_encipherment=False, key_agreement=False,
                    key_cert_sign=issuer is None, crl_sign=issuer is None,
                    encipher_only=False, decipher_only=False), True))
    if issuer:
        san = []
        for value in names:
            try:
                san.append(x509.IPAddress(ipaddress.ip_address(value)))
            except ValueError:
                san.append(x509.DNSName(value))
        builder = builder.add_extension(x509.SubjectAlternativeName(san), False)
        builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH,
                                                             ExtendedKeyUsageOID.CLIENT_AUTH]), False)
    cert = builder.sign(issuer_key or key, hashes.SHA256())
    private(root / (name + '.crt'), cert.public_bytes(serialization.Encoding.PEM))
    private(root / (name + '.key'), key.private_bytes(serialization.Encoding.PEM,
                                                    serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))
    return key, cert


class EtcdLab:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.document = None

    def prepare(self, *, cluster_id=None, generation=None):
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        name = 'netclaw-r08-' + secrets.token_hex(5)
        names, ports = [name + '-v' + str(i) for i in range(3)], []
        cluster_id, generation = cluster_id or str(uuid.uuid4()), generation or str(uuid.uuid4())
        uuid.UUID(cluster_id); uuid.UUID(generation)
        certs = self.root / 'pki'; certs.mkdir(mode=0o700)
        ca_key, ca = certificate(certs, 'client-ca')
        peer_key, peer_ca = certificate(certs, 'peer-ca')
        certificate(certs, 'admin', issuer_key=ca_key, issuer=ca, names=('admin',), user=True)
        for i in range(3):
            certificate(certs, f'server{i}', issuer_key=ca_key, issuer=ca,
                        names=(f'v{i}', 'localhost', '127.0.0.1'))
            certificate(certs, f'peer{i}', issuer_key=peer_key, issuer=peer_ca, names=(f'v{i}',))
            certificate(certs, f'border{i}', issuer_key=ca_key, issuer=ca, names=(f'border{i}',), user=True)
            node_certs = self.root / f'voter{i}-pki'; node_certs.mkdir(mode=0o700)
            for source, target in [('client-ca.crt', 'client-ca.crt'), ('peer-ca.crt', 'peer-ca.crt'),
                                   (f'server{i}.crt', 'server.crt'), (f'server{i}.key', 'server.key'),
                                   (f'peer{i}.crt', 'peer.crt'), (f'peer{i}.key', 'peer.key')]:
                private(node_certs / target, (certs / source).read_bytes())
            (self.root / f'voter{i}-data').mkdir(mode=0o700)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); ports.append(sock.getsockname()[1])
        self.document = {'schema_version': 1, 'name': name, 'containers': names, 'ports': ports,
                         'cluster_id': cluster_id, 'generation': generation, 'image': IMAGE,
                         'prefix': f'/netclaw/ha/{cluster_id}/{generation}/',
                         'prepared': datetime.now(timezone.utc).isoformat(),
                         'bounds': LOCK['qualification']}
        private(self.root / 'owned.json', self.document)
        private(self.root / 'credentials.json', {n: secrets.token_urlsafe(32)
                                                for n in ('root', 'border0', 'border1', 'border2')})
        return self

    def load(self):
        self.document = json.loads((self.root / 'owned.json').read_text())
        if self.document['image'] != IMAGE or not self.document['name'].startswith('netclaw-r08-'):
            raise RuntimeError('owned_manifest_mismatch')
        return self

    def start(self):
        if self.document is None:
            self.load()
        doc = self.document
        private(self.root / 'start.claim.json', {'manifest_sha256': hashlib.sha256((self.root / 'owned.json').read_bytes()).hexdigest()})
        command(self.root, 'image-inspect', ['docker', 'image', 'inspect', IMAGE])
        network_id = command(self.root, 'network-create', ['docker', 'network', 'create',
                          '--label', 'netclaw.spec=179', '--label', 'netclaw.owner=' + doc['name'], doc['name']])
        private(self.root / 'network-id.json', {'id': network_id})
        initial = ','.join(f'v{i}=https://v{i}:2380' for i in range(3))
        ids = []
        for i, name in enumerate(doc['containers']):
            args = ['docker', 'run', '-d', '--name', name, '--label', 'netclaw.spec=179',
                    '--label', 'netclaw.owner=' + doc['name'], '--network', doc['name'],
                    '--network-alias', f'v{i}', '--memory', '512m', '--memory-swap', '512m',
                    '--cpus', '0.6', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                    '-e', 'GOMEMLIMIT=384MiB', '-p', f'127.0.0.1:{doc["ports"][i]}:2379',
                    '-v', f'{self.root}/voter{i}-pki:/pki:ro', '-v', f'{self.root}/voter{i}-data:/data',
                    IMAGE, '/usr/local/bin/etcd', '--name', f'v{i}', '--data-dir', '/data',
                    '--listen-client-urls', 'https://0.0.0.0:2379', '--advertise-client-urls', f'https://v{i}:2379',
                    '--listen-peer-urls', 'https://0.0.0.0:2380', '--initial-advertise-peer-urls', f'https://v{i}:2380',
                    '--initial-cluster', initial, '--initial-cluster-token', doc['name'],
                    '--cert-file', '/pki/server.crt', '--key-file', '/pki/server.key',
                    '--trusted-ca-file', '/pki/client-ca.crt', '--client-cert-auth=true',
                    '--peer-cert-file', '/pki/peer.crt', '--peer-key-file', '/pki/peer.key',
                    '--peer-trusted-ca-file', '/pki/peer-ca.crt', '--peer-client-cert-auth=true',
                    '--tls-min-version=TLS1.3', '--heartbeat-interval', '300', '--election-timeout', '3000',
                    '--quota-backend-bytes', '134217728', '--auto-compaction-mode', 'periodic',
                    '--auto-compaction-retention', '1m', '--log-level', 'warn']
            identifier = command(self.root, f'voter{i}-start', args)
            ids.append(identifier)
        private(self.root / 'container-ids.json', ids)
        self._bootstrap_rbac()
        private(self.root / 'start.complete.json', {'containers': ids, 'network': network_id})
        return self

    def _bootstrap_rbac(self):
        doc = self.document
        certs = self.root / 'pki'
        context = ssl.create_default_context(cafile=str(certs / 'client-ca.crt'))
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(certs / 'admin.crt', certs / 'admin.key')
        credentials = json.loads((self.root / 'credentials.json').read_text())
        with httpx.Client(verify=context, timeout=2, trust_env=False, follow_redirects=False) as client:
            url = f'https://127.0.0.1:{doc["ports"][0]}/v3/'
            def request(path, value):
                response = client.post(url + path, json=value)
                if response.status_code != 200 or 'error' in response.json():
                    raise RuntimeError('etcd_bootstrap_refused')
                return response.json()
            deadline = time.monotonic() + 30
            while True:
                try:
                    request('kv/range', {'key': base64.b64encode(b'initial-read').decode(), 'serializable': False})
                    break
                except (httpx.HTTPError, RuntimeError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('etcd_readiness_timeout') from None
                    time.sleep(.25)
            # Every write is single-attempt. A partial/unknown bootstrap requires
            # inspected completion, not invoking start() again.
            private(self.root / 'rbac.claim.json', {'scope': doc['prefix']})
            request('auth/user/add', {'name': 'root', 'password': credentials['root']})
            request('auth/user/grant', {'user': 'root', 'role': 'root'})
            request('auth/role/add', {'name': 'ncfed-cluster'})
            prefix = doc['prefix'].encode(); end = prefix[:-1] + bytes([prefix[-1] + 1])
            request('auth/role/grant', {'name': 'ncfed-cluster', 'perm': {'permType': 'READWRITE',
                    'key': base64.b64encode(prefix).decode(), 'range_end': base64.b64encode(end).decode()}})
            for i in range(3):
                user = f'border{i}'
                request('auth/user/add', {'name': user, 'password': credentials[user]})
                request('auth/user/grant', {'user': user, 'role': 'ncfed-cluster'})
            request('auth/enable', {})
            private(self.root / 'rbac.complete.json', {'enabled': True, 'scope': doc['prefix']})

    def store(self, index):
        from bgp.federation.ha.store import EtcdStore
        if self.document is None:
            self.load()
        doc = self.document; certs = self.root / 'pki'
        credentials = json.loads((self.root / 'credentials.json').read_text())
        return EtcdStore([f'https://127.0.0.1:{doc["ports"][(index + j) % 3]}' for j in range(3)],
                         prefix=doc['prefix'], ca=certs / 'client-ca.crt',
                         certificate=certs / f'border{index}.crt', private_key=certs / f'border{index}.key',
                         username=f'border{index}', password=credentials[f'border{index}'])

    def inspect_owned(self):
        if self.document is None:
            self.load()
        expected = json.loads((self.root / 'container-ids.json').read_text())
        result = subprocess.run(['docker', 'inspect', *expected], capture_output=True, timeout=15, check=True)
        rows = json.loads(result.stdout)
        if len(rows) != 3:
            raise RuntimeError('owned_voter_inventory_mismatch')
        for index, row in enumerate(rows):
            labels = row['Config']['Labels'] or {}
            if (row['Id'] != expected[index] or row['Name'] != '/' + self.document['containers'][index]
                    or labels.get('netclaw.owner') != self.document['name'] or labels.get('netclaw.spec') != '179'
                    or row['Config']['Image'] != IMAGE):
                raise RuntimeError('owned_voter_identity_mismatch')
        return rows

    def fault(self, index, action, evidence):
        if type(index) is not int or index not in range(3) or action not in ('pause', 'unpause'):
            raise ValueError('unsupported_owned_fault')
        rows = self.inspect_owned()
        row = rows[index]
        if not row['State']['Running'] or row['State']['Paused'] != (action == 'unpause'):
            raise RuntimeError('owned_voter_state_changed')
        private(Path(evidence) / (action + f'-v{index}.baseline.json'), row)
        command(Path(evidence), action + f'-v{index}', ['docker', action, row['Id']])
        updated = self.inspect_owned()[index]
        private(Path(evidence) / (action + f'-v{index}.verified.json'), updated)
        if updated['State']['Paused'] != (action == 'pause'):
            raise RuntimeError('owned_fault_verification_failed')

    def prepare_cluster_identity(self, *, organization='r08-fixture', revision=1):
        """Fresh offline NCFED enrollment plus separate loopback transport PKI.

        File/key preparation only: no voter/client request, container or runtime
        mutation. Existing identity/transport directories are never overwritten.
        The enrollment root.key stays with the offline coordinator; do not mount
        this directory wholesale into any Border, member or proxy container.
        """
        from bgp.federation import protected_contract as c
        from bgp.federation.certs import create_self_signed
        from bgp.federation.ha.config import sign_manifest, verify_manifest
        if self.document is None:
            self.load()
        identity = self.root / 'cluster-identity'
        identity.mkdir(mode=0o700, exist_ok=False)
        private(identity / 'prepare.claim.json', {'schema_version': 1,
            'cluster_id': self.document['cluster_id'], 'generation': self.document['generation'],
            'revision': revision})
        held, used = [], set(self.document['ports'])
        def available_port():
            # Keep every selection bound until the whole manifest is written,
            # so cluster/in2n/HTTPS choices cannot reuse the same ephemeral port.
            for _ in range(32):
                listener = socket.socket()
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
                if port in used:
                    listener.close(); continue
                held.append(listener); used.add(port)
                return port
            raise RuntimeError('fresh_endpoint_capacity')
        try:
            anchor, anchor_key = create_self_signed('r08/offline-enrollment', days=3)
            private(identity / 'root.crt', anchor.encode())
            private(identity / 'root.key', anchor_key.encode())
            nodes = []
            for index in range(3):
                name = f'r08/border-{index}'
                application_certificate, application_key = create_self_signed(name, days=3)
                private(identity / f'node{index}.crt', application_certificate.encode())
                private(identity / f'node{index}.key', application_key.encode())
                cluster_port, in2n_port, https_port = available_port(), available_port(), available_port()
                server_name = f'border-{index}.r08.test'
                nodes.append({'node_id': str(uuid.uuid4()), 'installation_id': str(uuid.uuid4()),
                    'identity': name, 'key_id': c.key_id(application_certificate),
                    'certificate': application_certificate, 'role': 'border',
                    'endpoints': {'cluster': {'host': '127.0.0.1', 'port': cluster_port, 'server_name': server_name},
                        'in2n': {'host': '127.0.0.1', 'port': in2n_port, 'server_name': server_name},
                        'https': f'https://{server_name}:{https_port}',
                        'wss': f'wss://{server_name}:{https_port}/mobile/ws'}})
            manifest = {'schema_version': 1, 'cluster_id': self.document['cluster_id'],
                'generation': self.document['generation'], 'organization': organization, 'revision': revision,
                'nodes': nodes, 'limits': {'leader_lease_s': 12, 'renewal_s': 3, 'admission_ms': 3000,
                    'clock_uncertainty_ms': 250, 'max_operations': 1024, 'max_members': 32}}
            envelope = sign_manifest(manifest, anchor_key)
            verified = verify_manifest(envelope, anchor, expected_key_id=c.key_id(anchor))
            private(identity / 'manifest.json', envelope)
            # Separate CA and DNS transport certificates retain only each node's
            # own application key; none uses the offline enrollment signer key.
            self.prepare_cluster_transport()
            private(identity / 'complete.json', {'schema_version': 1, **verified.audience,
                'manifest_sha256': c.sha256(verified.value), 'anchor_key_id': c.key_id(anchor),
                'node_ids': [node['node_id'] for node in nodes],
                'endpoint_reservation': 'released-before-return;actual-bind-required'})
        finally:
            for listener in held:
                listener.close()
        return self

    def prepare_cluster_transport(self):
        """Separate transport CA; retain the enrolled application keys/manifest.

        Internal NCFED identity certificates use URI SANs. They must never be
        mistaken for DNS transport certificates or relax hostname verification.
        """
        identity = self.root / 'cluster-identity'
        target = self.root / 'cluster-transport'
        target.mkdir(mode=0o700, exist_ok=False)
        value = json.loads((identity / 'manifest.json').read_text())['manifest']
        ca_key, ca = certificate(target, 'transport-ca')
        for i, node in enumerate(value['nodes']):
            key = serialization.load_pem_private_key((identity / f'node{i}.key').read_bytes(), password=None)
            names = {node['endpoints'][name]['server_name'] for name in ('cluster', 'in2n')}
            certificate(target, f'node{i}', issuer=ca, issuer_key=ca_key, key=key, names=sorted(names))
        private(target / 'complete.json', {'application_manifest_unchanged': True,
                                          'transport_ca_separate': True, 'nodes': len(value['nodes'])})
