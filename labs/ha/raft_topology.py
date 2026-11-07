"""Fresh proxy-fronted Raft topology; coordinator-only source, no NET_ADMIN.

Requires an already installed immutable Python image with `python` on PATH. The
coordinator reviews its exact digest and all six resource commands before start.
The existing direct lab and every retained network remain untouched.
"""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .etcd_lab import EtcdLab, IMAGE, certificate, private, command


def pinned_image(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}', value):
        raise ValueError('immutable_proxy_image_required')
    return value


class RaftProxyLab(EtcdLab):
    def __init__(self, root, proxy_image):
        super().__init__(root)
        self.proxy_image = pinned_image(proxy_image)
        self.proxy_source = Path(__file__).with_name('raft_proxy.py').resolve()

    def prepare(self, **kwargs):
        super().prepare(**kwargs)
        root = self.root; pki = root / 'pki'
        issuer = x509.load_pem_x509_certificate((pki / 'peer-ca.crt').read_bytes())
        issuer_key = serialization.load_pem_private_key((pki / 'peer-ca.key').read_bytes(), password=None)
        names = []
        for i in range(3):
            names.append(self.document['name'] + f'-proxy{i}')
            certificate(pki, f'proxy-peer{i}', issuer=issuer, issuer_key=issuer_key, names=(f'p{i}', f'v{i}'))
            target = root / f'voter{i}-proxy-pki'; target.mkdir(mode=0o700)
            for source, destination in [('client-ca.crt', 'client-ca.crt'), ('peer-ca.crt', 'peer-ca.crt'),
                (f'server{i}.crt', 'server.crt'), (f'server{i}.key', 'server.key'),
                (f'proxy-peer{i}.crt', 'peer.crt'), (f'proxy-peer{i}.key', 'peer.key')]:
                private(target / destination, (pki / source).read_bytes())
            control = root / f'proxy{i}'; control.mkdir(mode=0o700)
            private(control / 'policy.json', {'schema_version': 1, 'generation': 1, 'owner': self.document['name'],
                'target': f'v{i}', 'peers': {}, 'rules': {}})
        private(root / 'proxy-owned.json', {'schema_version': 1, 'containers': names,
            'image': self.proxy_image, 'source_sha256': hashlib.sha256(self.proxy_source.read_bytes()).hexdigest(),
            'purpose': 'fresh-raft-peer-byte-paths', 'memory_mib_each': 64, 'cpus_each': .1})
        private(root / 'raft-start-plan.json', self.start_plan())
        return self

    def load(self):
        super().load()
        owned = json.loads((self.root / 'proxy-owned.json').read_text())
        if (owned['image'] != self.proxy_image or owned['source_sha256'] != hashlib.sha256(self.proxy_source.read_bytes()).hexdigest()
                or owned['containers'] != [self.document['name'] + f'-proxy{i}' for i in range(3)]):
            raise RuntimeError('owned_proxy_mismatch')
        return self

    def start_plan(self):
        doc, root = self.document, self.root
        if doc is None: raise RuntimeError('prepare_required')
        commands = [['docker', 'image', 'inspect', IMAGE], ['docker', 'image', 'inspect', self.proxy_image],
            ['docker', 'network', 'create', '--label', 'netclaw.spec=179', '--label', 'netclaw.owner=' + doc['name'], doc['name']]]
        for i in range(3):
            commands.append(['docker', 'run', '--pull', 'never', '-d', '--name', doc['name'] + f'-proxy{i}',
                '--label', 'netclaw.spec=179', '--label', 'netclaw.owner=' + doc['name'], '--network', doc['name'],
                '--network-alias', f'p{i}', '--memory', '64m', '--memory-swap', '64m', '--cpus', '.1',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--read-only',
                '-v', f'{self.proxy_source}:/app/raft_proxy.py:ro', '-v', f'{root}/proxy{i}:/control',
                self.proxy_image, 'python', '-B', '/app/raft_proxy.py'])
        initial = ','.join(f'v{i}=https://p{i}:2380' for i in range(3))
        for i, name in enumerate(doc['containers']):
            commands.append(['docker', 'run', '--pull', 'never', '-d', '--name', name,
                '--label', 'netclaw.spec=179', '--label', 'netclaw.owner=' + doc['name'], '--network', doc['name'],
                '--network-alias', f'v{i}', '--memory', '512m', '--memory-swap', '512m', '--cpus', '.6',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '-e', 'GOMEMLIMIT=384MiB',
                '-p', f'127.0.0.1:{doc["ports"][i]}:2379', '-v', f'{root}/voter{i}-proxy-pki:/pki:ro',
                '-v', f'{root}/voter{i}-data:/data', IMAGE, '/usr/local/bin/etcd', '--name', f'v{i}', '--data-dir', '/data',
                '--listen-client-urls', 'https://0.0.0.0:2379', '--advertise-client-urls', f'https://v{i}:2379',
                '--listen-peer-urls', 'https://0.0.0.0:2380', '--initial-advertise-peer-urls', f'https://p{i}:2380',
                '--initial-cluster', initial, '--initial-cluster-token', doc['name'],
                '--cert-file', '/pki/server.crt', '--key-file', '/pki/server.key', '--trusted-ca-file', '/pki/client-ca.crt',
                '--client-cert-auth=true', '--peer-cert-file', '/pki/peer.crt', '--peer-key-file', '/pki/peer.key',
                '--peer-trusted-ca-file', '/pki/peer-ca.crt', '--peer-client-cert-auth=true', '--tls-min-version=TLS1.3',
                '--strict-reconfig-check=true', '--heartbeat-interval', '300', '--election-timeout', '3000',
                '--quota-backend-bytes', '134217728', '--auto-compaction-mode', 'periodic',
                '--auto-compaction-retention', '1m', '--log-level', 'warn'])
        return {'schema_version': 1, 'class': 'FIXTURE', 'owner': doc['name'], 'commands': commands,
                'new_containers': 6, 'new_networks': 1, 'external_ports': 'loopback-client-only',
                'requires_coordinator_execution': True}

    def start(self):
        self.load()
        planned = json.loads((self.root / 'raft-start-plan.json').read_text())
        if planned != self.start_plan(): raise RuntimeError('reviewed_raft_plan_changed')
        private(self.root / 'raft-start.claim.json', {'plan_sha256': hashlib.sha256(json.dumps(planned, sort_keys=True).encode()).hexdigest()})
        outputs = []
        for index, args in enumerate(planned['commands']):
            outputs.append(command(self.root, f'raft-start-{index}', args))
        private(self.root / 'network-id.json', {'id': outputs[2]})
        private(self.root / 'proxy-ids.json', outputs[3:6])
        private(self.root / 'container-ids.json', outputs[6:9])
        self.configure()
        self._bootstrap_rbac()
        private(self.root / 'raft-start.complete.json', {'proxies': outputs[3:6], 'voters': outputs[6:9]})
        return self

    def inspect_proxies(self):
        expected = json.loads((self.root / 'proxy-ids.json').read_text())
        result = subprocess.run(['docker', 'inspect', *expected], capture_output=True, timeout=15, check=True)
        rows = json.loads(result.stdout)
        if len(rows) != 3: raise RuntimeError('owned_proxy_mismatch')
        for index, row in enumerate(rows):
            if (row['Id'] != expected[index] or row['Name'] != '/' + self.document['name'] + f'-proxy{index}'
                    or row['Config']['Labels'].get('netclaw.owner') != self.document['name']
                    or row['Config']['Labels'].get('netclaw.spec') != '179' or row['Config']['Image'] != self.proxy_image):
                raise RuntimeError('owned_proxy_mismatch')
        return rows

    def configure(self, *, cuts=(), delay_ms=0):
        if type(delay_ms) is not int or not 0 <= delay_ms <= 150: raise ValueError('invalid_raft_delay')
        cuts = set(tuple(pair) for pair in cuts)
        if any(len(pair) != 2 or any(type(i) is not int or i not in range(3) for i in pair) or pair[0] == pair[1] for pair in cuts):
            raise ValueError('invalid_directed_raft_cut')
        voters, proxies = self.inspect_owned(), self.inspect_proxies()
        if any(not row['State']['Running'] or row['State']['Paused'] for row in voters + proxies):
            raise RuntimeError('owned_raft_topology_not_running')
        peers = {f'v{i}': row['NetworkSettings']['Networks'][self.document['name']]['IPAddress'] for i, row in enumerate(voters)}
        for address in peers.values(): ipaddress.IPv4Address(address)
        if len(set(peers.values())) != 3: raise RuntimeError('owned_raft_addresses_ambiguous')
        for target in range(3):
            path = self.root / f'proxy{target}' / 'policy.json'
            current = json.loads(path.read_text())
            policy = {'schema_version': 1, 'generation': current['generation'] + 1, 'owner': self.document['name'],
                'target': f'v{target}', 'peers': peers, 'rules': {f'v{source}': {
                    'request': 'drop' if (source, target) in cuts else 'pass',
                    'response': 'drop' if (target, source) in cuts else 'pass', 'delay_ms': delay_ms}
                    for source in range(3)}}
            temporary = path.with_name('policy.next.json'); private(temporary, policy)
            temporary.replace(path)
        return {'kind': 'owned-directed-raft-byte-policy', 'cuts': sorted(cuts), 'delay_ms': delay_ms, 'peers': peers}

    def observe(self):
        self.inspect_owned(); self.inspect_proxies()
        observations = []
        for target in range(3):
            path = self.root / f'proxy{target}'
            policy_raw = (path / 'policy.json').read_bytes()
            policy, metrics = json.loads(policy_raw), json.loads((path / 'metrics.json').read_text())
            if metrics['policy_generation'] != policy['generation'] or metrics['policy_sha256'] != hashlib.sha256(policy_raw).hexdigest():
                raise RuntimeError('raft_policy_not_yet_observed')
            observations.append({'target': target, 'policy': policy, 'metrics': metrics})
        return observations
