"""Serial actual-etcd/NCFED fixture matrix with controlled member effects.

The coordinator runs this against a fresh owned lab. Application identity, TLS,
quorum transactions and MemberAdmission are production code. Only effect callbacks
are controlled. The routing shim sends encrypted bytes through observed proxies;
it never replaces authentication, consensus, admission or the guard.
"""
import argparse
import asyncio
import contextvars
import copy
import json
from pathlib import Path
import secrets
import time
import uuid

from bgp.federation import exporter_tls, protected_contract as c
from bgp.federation.certs import create_self_signed
from bgp.federation.channel import RpcError
from bgp.federation.ha.admission import MemberAdmission
from bgp.federation.ha.authority import Authority, MAX_DECISIONS
from bgp.federation.ha.config import HAError, verify_manifest
from bgp.federation.ha.lifecycle import Lifecycle
from bgp.federation.ha.node import ClusterNode
from bgp.federation.ha.recovery import export_snapshot
from bgp.federation.ha.store import EtcdStore
from .etcd_lab import EtcdLab, private, command
from .faults import ByteProxy, Evidence, source_digest, owned_call, failure_details
from .qualify import eventually

SOURCE = contextvars.ContextVar('r08_fixture_source', default=None)
NETWORK_ROWS = ('minority', 'asymmetric-request', 'asymmetric-response', 'threeway', 'delay-300ms')
LOCAL_ROWS = ('stale-member', 'clock-forward', 'clock-backward', 'clock-suspend',
              'unknown-commit', 'lost-result', 'lost-ack', 'record-capacity', 'nospace', 'retired-return')
ALL_ROWS = ('leader-loss-each-node', 'quorum-loss-two-voters', *NETWORK_ROWS, *LOCAL_ROWS, 'full-restart')
REFUSALS = (HAError, RpcError, ConnectionError, asyncio.TimeoutError)


class MatrixHarness:
    def __init__(self, lab, evidence, rows):
        self.lab = lab
        identity = lab.root / 'cluster-identity'
        self.identity, self.transport = identity, lab.root / 'cluster-transport'
        root = (identity / 'root.crt').read_text()
        self.manifest = verify_manifest((identity / 'manifest.json').read_bytes(), root, expected_key_id=c.key_id(root))
        self.evidence = Evidence(evidence, {'source_sha256': source_digest(),
            'manifest_sha256': c.sha256(self.manifest.value), 'actual_etcd': True,
            'voter_image': lab.document['image'], 'bounds': lab.document['bounds'],
            'voter_container_ids': json.loads((lab.root / 'container-ids.json').read_text()),
            'actual_ncfed_cluster': True, 'actual_in2n_member': False,
            'raft_peer_partition_qualified': False,
            'network_scope': 'border-quorum-and-ncfed-byte-paths'}, required=rows)
        self.nodes, self.stores, self.proxies, self.quorum, self.links = [], [], [], {}, {}
        self.original_open = exporter_tls.open_connection
        self.effects, self.operations, self.case = [], [], 'startup'
        self.raft_proxy = hasattr(lab, 'configure') and hasattr(lab, 'observe')
        if (lab.root / 'proxy-owned.json').exists() and not self.raft_proxy:
            raise ValueError('raft_topology_requires_proxy_image')

    def counters(self):
        return {'fixture_model': self.effects.count('model'), 'fixture_tool': self.effects.count('tool')}

    def new_node(self, index):
        return ClusterNode(Authority(self.stores[index], self.manifest, self.manifest.nodes[index]['node_id']),
            private_key=(self.identity / f'node{index}.key').read_text(),
            ca_file=str(self.transport / 'transport-ca.crt'),
            cert_file=str(self.transport / f'node{index}.crt'), key_file=str(self.transport / f'node{index}.key'))

    async def start_node(self, index):
        token = SOURCE.set(self.manifest.nodes[index]['node_id'])
        try: await self.nodes[index].start()
        finally: SOURCE.reset(token)

    async def start(self):
        self.lab.inspect_owned()  # Exact labels, immutable IDs and image first.
        for source in range(3):
            store = self.lab.store(source)
            endpoints = []
            for target in range(3):
                proxy = await ByteProxy(f'border{source}-voter{target}', '127.0.0.1',
                    self.lab.document['ports'][target]).start()
                self.proxies.append(proxy); self.quorum[source, target] = proxy
                endpoints.append(f'https://127.0.0.1:{proxy.port}')
            # The unchanged etcd TLS/RBAC client uses loopback proxies; server
            # certificates already authenticate localhost independently of port.
            store.endpoints = tuple(endpoints)
            self.stores.append(store)
        for source, node in enumerate(self.manifest.nodes):
            for target, peer in enumerate(self.manifest.nodes):
                if node['node_id'] < peer['node_id']:
                    address = peer['endpoints']['cluster']
                    proxy = await ByteProxy(f'ncfed{source}-to-{target}', address['host'], address['port']).start()
                    self.proxies.append(proxy); self.links[source, target] = proxy
        async def routed(host, port, **kwargs):
            source = next((i for i, n in enumerate(self.manifest.nodes) if n['node_id'] == SOURCE.get()), None)
            for (origin, target), proxy in self.links.items():
                address = self.manifest.nodes[target]['endpoints']['cluster']
                if source == origin and (host, port) == (address['host'], address['port']):
                    return await self.original_open('127.0.0.1', proxy.port, **kwargs)
            return await self.original_open(host, port, **kwargs)
        exporter_tls.open_connection = routed
        self.nodes = [self.new_node(i) for i in range(3)]
        await asyncio.gather(*(self.start_node(i) for i in range(3)))
        await eventually(self.mesh)
        await self.leader()

    async def mesh(self):
        return all(n.closing or len(n.channels) == 2 for n in self.nodes)

    async def leader(self, excluded=()):
        async def find():
            for index, node in enumerate(self.nodes):
                if index in excluded or node.closing: continue
                try:
                    value, epoch = await asyncio.to_thread(node.authority.current)
                    for candidate_index, candidate in enumerate(self.nodes):
                        if candidate_index in excluded: continue
                        if (candidate.node_id == value['node_id'] and not candidate.closing
                                and candidate.authority.leader == value and candidate.authority.epoch == epoch):
                            return candidate
                except REFUSALS: pass
            return None
        return await eventually(find, 45)

    def index(self, node):
        return self.nodes.index(node)

    async def prepare(self, node=None, *, member=None, key=None, certificate=None):
        node = node or await self.leader()
        if member is None:
            certificate, key = create_self_signed('controlled-r08-member')
            member = {'installation_id': str(uuid.uuid4()), 'member_id': 'r08/controlled-' + uuid.uuid4().hex[:12],
                      'key_id': c.key_id(certificate), 'enrollment_generation': str(uuid.uuid4())}
            await asyncio.to_thread(node.ledger.enroll_member, member, certificate)
        binding = self.manifest.node(node.node_id)
        review = {'principal': {'issuer': 'open-lab', 'subject': str(uuid.uuid5(uuid.UUID(self.manifest.cluster_id), 'netclaw.open-lab.operator')),
            'display_name': 'Unauthenticated lab operator', 'roles': ['lab-operator']},
            'cluster': {**self.manifest.audience, 'manifest_revision': self.manifest.revision,
                        'issuer_node_id': node.node_id, 'authority_epoch': node.authority.epoch},
            'border': {'installation_id': binding['installation_id'], 'identity': binding['identity'],
                'key_id': binding['key_id'], 'authority_generation': self.manifest.generation}, 'member': member,
            'model_profile': {'profile_id': 'controlled-fixture', 'profile_revision': '1', 'runtime_kind': 'controlled',
                'runtime_version': 'fixture', 'provider': 'controlled', 'model': 'fixture', 'guard_policy_sha256': 'a'*64},
            'tool_call': {'tool': 'subnet_calculator', 'tool_schema_sha256': 'b'*64,
                'arguments': {'cidr': '192.0.2.0/26'}, 'arguments_sha256': c.sha256({'cidr': '192.0.2.0/26'}),
                'device_ref': 'documentation-subnet', 'inventory_revision': 'fixture', 'endpoint_sha256': 'c'*64},
            'limits': {'expires_at_ms': int(time.time()*1000) + 180000, 'inference_timeout_ms': 60000,
                'tool_timeout_ms': 60000, 'max_inference_calls': 2, 'max_tool_calls': 1, 'max_output_bytes': 65536},
            'change_request_ref': None}
        row = await asyncio.to_thread(node.ledger.prepare, 'matrix-' + str(uuid.uuid4()), 'd'*64, review)
        payload = dict(review, approval_id=str(uuid.uuid4()), operation_id=row['operation_id'],
                       nonce=secrets.token_urlsafe(32), issued_at_ms=int(time.time()*1000), review_sha256=row['review_digest'])
        approval = c.sign(c.HA_APPROVAL, payload, node.private_key)
        row = await asyncio.to_thread(node.ledger.approve, row['operation_id'], approval,
            revision=row['revision'], review_digest=row['review_digest'])
        row = await asyncio.to_thread(node.ledger.dispatch, row['operation_id'])
        journal = MemberAdmission(self.evidence.path / ('member-' + row['operation_id']), self.manifest, member)
        operation = {'row': row, 'journal': journal, 'member': member, 'key': key, 'certificate': certificate,
                     'context': {k: row[k] for k in ('operation_id', 'attempt_id', 'approval_digest')}}
        self.operations.append(operation)
        return operation

    async def send(self, operation, node, request):
        return await node.route('n2n/cluster/admission', {'request': request, 'member': operation['member']})

    async def probe(self, operation, node, kind, *, denied=False, ordinal=1):
        before = self.counters()
        async def invoke():
            if len(self.effects) >= 64: raise RuntimeError('fixture_effect_bound')
            self.effects.append(kind)
            return {'controlled_fixture': True}
        try:
            await operation['journal'].run(operation['context'], kind, ordinal, c.sha256({'kind': kind}),
                lambda req: self.send(operation, node, req), invoke)
        except REFUSALS as exc:
            if not denied: raise
            if before != self.counters(): raise AssertionError('refused_gate_invoked_callback')
            return {'kind': kind, 'outcome': 'refused', 'code': getattr(exc, 'code', type(exc).__name__)}
        if denied: raise AssertionError('fault_admitted_callback')
        return {'kind': kind, 'outcome': 'admitted'}

    def observations(self):
        return [p.observation() for p in self.proxies]

    def partition(self, indices, *, orientation='both'):
        for index in indices:
            for target in range(3):
                self.quorum[index, target].policy(request='drop' if orientation in ('both', 'request') else 'pass',
                    response='drop' if orientation in ('both', 'response') else 'pass')
            for (source, target), proxy in self.links.items():
                if index not in (source, target): continue
                outbound = 'request' if index == source else 'response'
                inbound = 'response' if index == source else 'request'
                mode = {'request': 'pass', 'response': 'pass'}
                if orientation in ('both', 'request'): mode[outbound] = 'drop'
                if orientation in ('both', 'response'): mode[inbound] = 'drop'
                proxy.policy(**mode)

    async def heal(self):
        await asyncio.gather(*(p.reset() for p in self.proxies))
        await self.leader()
        await eventually(self.mesh)

    async def network_row(self, name):
        old = await self.leader(); index = self.index(old)
        operation = await self.prepare(old)
        before, started = self.counters(), time.monotonic()
        proxy_before = {p.name: p.observation() for p in self.proxies}
        raft_before = await asyncio.to_thread(self.lab.observe) if self.raft_proxy else []
        probes = []
        try:
            if name == 'delay-300ms':
                if self.raft_proxy: await asyncio.to_thread(self.lab.configure, delay_ms=150)
                for proxy in self.proxies: proxy.policy(delay_ms=150)
                ingress = next(node for node in self.nodes if node is not old)
                probes.append(await self.probe(operation, ingress, 'model'))
                probes.append(await self.probe(operation, ingress, 'tool'))
            else:
                orientation = name.split('-', 1)[1] if name.startswith('asymmetric-') else 'both'
                indices = list(range(3)) if name == 'threeway' else [index]
                if self.raft_proxy:
                    cuts = set()
                    for isolated in indices:
                        for other in range(3):
                            if isolated == other: continue
                            if orientation in ('both', 'request'): cuts.add((isolated, other))
                            if orientation in ('both', 'response'): cuts.add((other, isolated))
                    await asyncio.to_thread(self.lab.configure, cuts=cuts)
                self.partition(indices, orientation=orientation)
                for isolated in indices:
                    # Fresh challenge for both kinds at every isolated target.
                    if name == 'threeway':
                        operation['journal'] = MemberAdmission(self.evidence.path / f'threeway-{isolated}', self.manifest, operation['member'])
                    probes.append(await self.probe(operation, self.nodes[isolated], 'model', denied=True))
                    probes.append(await self.probe(operation, self.nodes[isolated], 'tool', denied=True))
                if name != 'threeway':
                    successor = await self.leader(excluded=(index,))
                    if successor is old: raise AssertionError('isolated_old_authority_survived')
                    majority = await self.prepare(successor)
                    ingress = next(node for number, node in enumerate(self.nodes) if number != index and node is not successor)
                    probes.append(await self.probe(majority, ingress, 'model'))
            observed = self.observations()
            for observed_proxy in observed:
                for direction in ('request', 'response'):
                    observed_proxy[direction]['dropped_bytes_delta'] = (observed_proxy[direction]['dropped_bytes']
                        - proxy_before[observed_proxy['name']][direction]['dropped_bytes'])
            if name != 'delay-300ms' and not any(
                    row[d]['dropped_bytes_delta'] for row in observed for d in ('request', 'response')):
                raise AssertionError('fault_not_observed')
            raft_observations = []
            if self.raft_proxy:
                async def raft_observed():
                    current = await asyncio.to_thread(self.lab.observe)
                    if name == 'delay-300ms': return current
                    prior = {row['target']: row['metrics']['directions'] for row in raft_before}
                    delta = sum(value['dropped_bytes'] - prior[row['target']].get(key, {}).get('dropped_bytes', 0)
                        for row in current for key, value in row['metrics']['directions'].items())
                    return current if delta > 0 else None
                raft_observations = await eventually(raft_observed, 15)
            self.evidence.row(name, passed=True, effects_before=before, effects_after=self.counters(),
                observations=observed, raft_observations=raft_observations,
                raft_peer_partition_qualified=bool(raft_observations) and name != 'delay-300ms', probes=probes, operation_id=operation['row']['operation_id'],
                elapsed_s=round(time.monotonic()-started, 3), old_authority=old.node_id)
        finally:
            if self.raft_proxy: await asyncio.to_thread(self.lab.configure)
            await self.heal()
        positive = await self.prepare()
        current = await self.leader()
        await self.probe(positive, next(node for node in self.nodes if node is not current), 'model')

    async def freshness_row(self, name):
        node = await self.leader(); operation = await self.prepare(node)
        journal = operation['journal']; before = self.counters()
        request, started = journal.begin(operation['context'], 'model', 1, 'e'*64)
        proof = await self.send(operation, node, request)
        old_mono, old_wall = journal.monotonic, journal.wall
        if name == 'stale-member':
            await asyncio.sleep(self.manifest.limits['admission_ms']/1000 + .1)
        elif name == 'clock-forward': journal.wall = lambda: old_wall() + 1
        elif name == 'clock-backward': journal.wall = lambda: old_wall() - 1
        else:
            journal.monotonic = lambda: old_mono() + 4
            journal.wall = lambda: old_wall() + 4
        try:
            journal.consume(request, proof, started)
            raise AssertionError('stale_or_uncertain_claim_consumed')
        except HAError as exc:
            if exc.code not in ('admission_expired', 'clock_uncertain'): raise
            self.evidence.row(name, passed=True, effects_before=before, effects_after=self.counters(),
                observations=[{'kind': 'production-member-gate', 'code': exc.code,
                    'committed_revision': proof['payload']['commit_revision'], 'member_incarnation': journal.incarnation}],
                operation_id=operation['row']['operation_id'], injected_clock=name)
        finally:
            journal.monotonic, journal.wall = old_mono, old_wall
            journal._terminal(request, 'unknown')

    async def unknown_commit(self):
        import base64
        node = await self.leader(); operation = await self.prepare(node); before = self.counters()
        captured, store = {}, node.authority.store
        original_request = store._request
        def lose_committed_response(path, body, **options):
            response = original_request(path, body, **options)
            writes = body.get('success', []) if path == '/v3/kv/txn' else []
            is_claim = any(base64.b64decode(row.get('request_put', {}).get('key', '')).decode().startswith(
                store.prefix + 'claims/') for row in writes)
            if is_claim and response.get('succeeded') and 'commit_revision' not in captured:
                captured['commit_revision'] = int(response['header']['revision'])
                captured['consensus_replies_dropped'] = 1
                # Actual etcd committed. Withhold its reply beyond the existing
                # member deadline, then expose the transport-unknown outcome.
                time.sleep(self.manifest.limits['admission_ms']/1000 + .1)
                raise HAError('commit_unknown', 503)
            return response
        store._request = lose_committed_response
        async def send(request):
            captured['request'] = request
            return await self.send(operation, node, request)
        async def forbidden():
            self.effects.append('model'); raise AssertionError('unknown_claim_forwarded')
        try:
            try:
                await operation['journal'].run(operation['context'], 'model', 1, 'a'*64, send, forbidden)
                raise AssertionError('expired_reconciled_claim_forwarded')
            except HAError as exc:
                if exc.code != 'admission_expired': raise
        finally:
            store._request = original_request
        claim, revision = await asyncio.to_thread(node.ledger.admission_status, captured['request'], operation['member'])
        if claim['request'] != captured['request'] or revision != captured['commit_revision']:
            raise AssertionError('unknown_claim_changed')
        await self.probe(operation, node, 'model', denied=True)
        self.evidence.row('unknown-commit', passed=True, effects_before=before, effects_after=self.counters(),
            observations=[{'kind': 'actual-consensus-commit-response-discard', 'revision': revision,
                           'consensus_replies_dropped': captured['consensus_replies_dropped']}],
            operation_id=operation['row']['operation_id'])

    async def retired_return(self):
        current = await self.leader(); target = next(n for n in self.nodes if n is not current)
        operation = await self.prepare(current); before = self.counters()
        await asyncio.to_thread(Lifecycle(current.authority).drain, target.node_id)
        retired = await asyncio.to_thread(Lifecycle(current.authority).retire, target.node_id)
        await target.close()
        old_index = self.index(target)
        returned = self.new_node(old_index)
        try:
            await returned.start()
            raise AssertionError('retired_node_restarted')
        except HAError as exc:
            if exc.code != 'node_retired': raise
        await self.probe(operation, target, 'model', denied=True)
        await self.probe(operation, target, 'tool', denied=True)
        self.evidence.row('retired-return', passed=True, effects_before=before, effects_after=self.counters(),
            observations=[{'kind': 'durable-retirement', **retired}], old_key_id=self.manifest.node(target.node_id)['key_id'])

    async def capacity(self):
        node = await self.leader(); operation = await self.prepare(node); before = self.counters()
        store = node.authority.store
        control, revision = await asyncio.to_thread(store.read, 'control')
        original = control['decision_count']; control['decision_count'] = MAX_DECISIONS
        committed, fault_revision = await asyncio.to_thread(store.txn, [('control', 'revision', revision)], [('control', control, None)])
        if not committed: raise AssertionError('capacity_fault_not_committed')
        try:
            model = await self.probe(operation, node, 'model', denied=True)
            tool = await self.probe(operation, node, 'tool', denied=True)
            if any(row['code'] != 'state_capacity' for row in (model, tool)):
                raise AssertionError('capacity_fault_not_observed_at_gate')
            self.evidence.row('record-capacity', passed=True, effects_before=before, effects_after=self.counters(),
                observations=[{'kind': 'actual-quorum-capacity-counter', 'revision': fault_revision,
                               'counter': MAX_DECISIONS}], probes=[model, tool])
        finally:
            observed, revision = await asyncio.to_thread(store.read, 'control')
            if observed != control: raise AssertionError('capacity_restore_state_changed')
            observed['decision_count'] = original
            committed, _ = await asyncio.to_thread(store.txn, [('control', 'revision', revision)], [('control', observed, None)])
            if not committed: raise AssertionError('capacity_restore_unknown')

    def admin(self):
        document = self.lab.document; pki = self.lab.root / 'pki'
        credentials = json.loads((self.lab.root / 'credentials.json').read_text())
        return EtcdStore([f'https://127.0.0.1:{port}' for port in document['ports']], prefix=document['prefix'],
            ca=pki/'client-ca.crt', certificate=pki/'admin.crt', private_key=pki/'admin.key',
            username='root', password=credentials['root'])

    async def nospace(self):
        node = await self.leader(); operation = await self.prepare(node); before = self.counters()
        admin = self.admin()
        attempted = False
        try:
            baseline = await asyncio.to_thread(admin._request, '/v3/maintenance/alarm', {'action': 'GET'}, read_only=True)
            if baseline.get('alarms'): raise RuntimeError('preexisting_etcd_alarm')
            attempted = True
            await asyncio.to_thread(admin._request, '/v3/maintenance/alarm',
                {'action': 'ACTIVATE', 'memberID': '0', 'alarm': 'NOSPACE'})
            observed = await asyncio.to_thread(admin._request, '/v3/maintenance/alarm', {'action': 'GET'}, read_only=True)
            if not any(row.get('alarm') in ('NOSPACE', 1) for row in observed.get('alarms', [])):
                raise AssertionError('nospace_not_observed')
            probes = [await self.probe(operation, node, kind, denied=True) for kind in ('model', 'tool')]
            self.evidence.row('nospace', passed=True, effects_before=before, effects_after=self.counters(),
                observations=[{'kind': 'actual-etcd-nospace-alarm', 'alarms': observed['alarms']}], probes=probes)
        finally:
            alarms = (await asyncio.to_thread(admin._request, '/v3/maintenance/alarm', {'action': 'GET'}, read_only=True)
                      if attempted else {'alarms': []})
            for row in alarms.get('alarms', []):
                if row.get('alarm') in ('NOSPACE', 1):
                    await asyncio.to_thread(admin._request, '/v3/maintenance/alarm',
                        {'action': 'DEACTIVATE', 'memberID': str(row.get('memberID', '0')), 'alarm': 'NOSPACE'})
            restored = await asyncio.to_thread(admin._request, '/v3/maintenance/alarm', {'action': 'GET'}, read_only=True)
            private(self.evidence.path / 'nospace-restored.json', restored)
            if restored.get('alarms'): raise AssertionError('nospace_cleanup_failed')
            admin.close()

    async def signed_result(self, operation):
        row = operation['row']; review = row['review']; output = {'controlled_fixture_result': row['operation_id']}
        payload = {'receipt_id': str(uuid.uuid4()), 'operation_id': row['operation_id'],
            'approval_id': row['approval_id'], 'approval_sha256': row['approval_digest'], 'attempt_id': row['attempt_id'],
            **{k: review[k] for k in ('principal', 'border', 'member', 'model_profile', 'cluster')},
            'tool_call_sha256': c.sha256(review['tool_call']), 'started_at_ms': int(time.time()*1000),
            'finished_at_ms': int(time.time()*1000), 'outcome': 'succeeded', 'effect_status': 'finished',
            'output': output, 'output_sha256': c.sha256(output), 'tool_evidence_sha256': 'f'*64,
            'usage': {'available': False}, 'audit_refs': {'result': 'controlled-fixture-audit'}, 'error_code': None}
        return c.sign(c.HA_RESULT, payload, operation['key'])

    async def lost_result(self, name):
        node = await self.leader(); operation = await self.prepare(node)
        await self.probe(operation, node, 'model'); await self.probe(operation, node, 'tool')
        signed = await self.signed_result(operation)
        private(self.evidence.path / (name + '-original-result.json'), signed)
        before = self.counters()
        old_index = self.index(node)
        if name == 'lost-ack':
            accepted = await asyncio.to_thread(node.ledger.accept_result, operation['row']['operation_id'], signed,
                                               private_key=node.private_key, audit_ref='fixture-ack')
            original_ack = accepted['ack']
        else: original_ack = None
        await node.close()
        successor = await self.leader(excluded=(old_index,))
        accepted = await asyncio.to_thread(successor.ledger.accept_result, operation['row']['operation_id'], signed,
            private_key=successor.private_key, audit_ref='fixture-survivor')
        if accepted['result_ref']['digest'] != c.digest(c.HA_RESULT, signed['payload']):
            raise AssertionError('original_result_changed')
        if original_ack is not None and accepted['ack'] != original_ack: raise AssertionError('original_ack_changed')
        self.evidence.row(name, passed=True, effects_before=before, effects_after=self.counters(),
            observations=[{'kind': 'durable-original-result', 'result_sha256': accepted['result_ref']['digest'],
                           'ack_sha256': c.sha256(accepted['ack'])}], operation_id=operation['row']['operation_id'])
        self.nodes[old_index] = self.new_node(old_index); await self.start_node(old_index)
        await eventually(self.mesh)

    async def leader_loss_each(self):
        before, observations = self.counters(), []
        # Each exact node service is the leader before its own bounded loss.
        for index in range(3):
            for node in self.nodes:
                await node.authority.stop_renewal()
            current = await self.leader()
            lease = current.authority.lease_id
            if lease:
                await asyncio.to_thread(current.authority.store.revoke_lease, lease)
            target = self.nodes[index]
            target.authority.leader = target.authority.epoch = target.authority.lease_id = None
            if not await asyncio.to_thread(target.authority.campaign):
                raise AssertionError('target_leader_not_established')
            operation = await self.prepare(target)
            old_epoch = target.authority.epoch
            started = time.monotonic()
            await target.close()
            for other, node in enumerate(self.nodes):
                if other != index: await node.authority.start_renewal()
            successor = await self.leader(excluded=(index,))
            detection = time.monotonic() - started
            if successor.authority.epoch <= old_epoch: raise AssertionError('epoch_not_increased')
            request, _ = operation['journal'].begin(operation['context'], 'model', 1, 'e'*64)
            try:
                await asyncio.to_thread(target.ledger.admit, request, operation['member'])
                raise AssertionError('old_epoch_admitted')
            except HAError as exc:
                if exc.code not in ('stale_authority', 'not_leader'): raise
                refusal = exc.code
            observations.append({'kind': 'actual-ncfed-service-loss', 'node_id': target.node_id,
                'old_epoch': old_epoch, 'new_epoch': successor.authority.epoch,
                'successor': successor.node_id, 'failure_to_new_authority_s': round(detection, 3),
                'os_process_killed': False, 'old_epoch_refusal': refusal})
            self.nodes[index] = self.new_node(index); await self.start_node(index)
            await eventually(self.mesh)
        self.evidence.row('leader-loss-each-node', passed=True, effects_before=before,
            effects_after=self.counters(), observations=observations, actual_os_process_loss_qualified=False)

    async def quorum_loss(self):
        current = await self.leader(); operation = await self.prepare(current)
        before, paused = self.counters(), []
        try:
            for index in (0, 1):
                await owned_call(self.lab.fault, index, 'pause', self.evidence.path)
                paused.append(index)
            observations = await asyncio.to_thread(self.lab.inspect_owned)
            probes = [await self.probe(operation, current, kind, denied=True) for kind in ('model', 'tool')]
            self.evidence.row('quorum-loss-two-voters', passed=True, effects_before=before,
                effects_after=self.counters(), observations=[{'kind': 'actual-owned-voter-pause',
                    'ids': [row['Id'] for row in observations], 'paused': [row['State']['Paused'] for row in observations]}],
                probes=probes)
        finally:
            # Independently inspect, including a lost response from pause().
            observed = await asyncio.to_thread(self.lab.inspect_owned)
            for index, row in enumerate(observed):
                if row['State']['Paused']:
                    await owned_call(self.lab.fault, index, 'unpause', self.evidence.path)
            await self.leader()

    async def full_restart(self):
        from .owned_restart import OwnedVoterRestart
        node = await self.leader()
        completed = await self.prepare(node)
        await self.probe(completed, node, 'model'); await self.probe(completed, node, 'tool')
        signed = await self.signed_result(completed)
        completed_row = await asyncio.to_thread(node.ledger.accept_result, completed['row']['operation_id'], signed,
            private_key=node.private_key, audit_ref='fixture-before-restart')
        unknown = await self.prepare(node)
        await self.probe(unknown, node, 'model')
        await asyncio.to_thread(node.ledger.mark_unknown, unknown['row']['operation_id'])
        before = self.counters()
        snapshot = await asyncio.to_thread(export_snapshot, node.authority.store, self.manifest)
        snapshot_file = self.evidence.path / 'before-full-restart.snapshot.json'
        private(snapshot_file, c.encode(snapshot))
        incarnations = [n.authority.incarnation for n in self.nodes]
        await asyncio.gather(*(n.close() for n in self.nodes))
        # Pending bounded store calls finish before actual voter shutdown.
        await asyncio.sleep(7)
        observed = await owned_call(OwnedVoterRestart(self.lab, self.evidence.path, snapshot_file).execute)
        async def quorum_back():
            return (await asyncio.to_thread(self.stores[0].read, 'control'))[0] is not None
        await eventually(quorum_back, 40)
        self.nodes = [self.new_node(i) for i in range(3)]
        await asyncio.gather(*(self.start_node(i) for i in range(3)))
        current = await self.leader(); await eventually(self.mesh)
        after = await asyncio.to_thread(export_snapshot, current.authority.store, self.manifest)
        if snapshot['records'] != after['records']: raise AssertionError('restart_durable_state_changed')
        reopened = MemberAdmission(unknown['journal'].home, self.manifest, unknown['member'])
        if reopened.incarnation == unknown['journal'].incarnation: raise AssertionError('member_incarnation_reused')
        unknown['journal'] = reopened
        await self.probe(unknown, current, 'model', denied=True)
        try:
            await self.prepare(current, member=unknown['member'], key=unknown['key'], certificate=unknown['certificate'])
            raise AssertionError('new_id_bypassed_unknown_reservation')
        except HAError as exc:
            if exc.code != 'resource_recovery_required': raise
        result = await asyncio.to_thread(current.ledger.lookup, operation_id=completed['row']['operation_id'])
        if result['ack'] != completed_row['ack']: raise AssertionError('restart_ack_changed')
        self.evidence.row('full-restart', passed=True, effects_before=before, effects_after=self.counters(),
            observations=[observed, {'kind': 'production-service-and-journal-recreation',
                'old_incarnations': incarnations, 'new_incarnations': [n.authority.incarnation for n in self.nodes]}],
            actual_border_os_process_restart_qualified=False, actual_member_os_process_restart_qualified=False,
            completed_operation_id=completed['row']['operation_id'], unknown_operation_id=unknown['row']['operation_id'])

    async def close(self):
        private(self.evidence.path / 'cleanup-started.json', {'class': 'FIXTURE',
            'case': self.case, 'nodes': [node.node_id for node in self.nodes],
            'proxy_connections': {proxy.name: len(proxy.tasks) for proxy in self.proxies}})
        # Begin Node shutdown, then abort only this fixture's proxy transports.
        # Never wait for servers to lose clients while holding those clients open.
        closers = [asyncio.create_task(node.close()) for node in self.nodes]
        await asyncio.sleep(0)
        exporter_tls.open_connection = self.original_open
        proxy_results = await asyncio.gather(*(proxy.close() for proxy in self.proxies), return_exceptions=True)
        private(self.evidence.path / 'cleanup-proxies.json', {'class': 'FIXTURE',
            'results': [failure_details(result) if isinstance(result, BaseException) else {'closed': True}
                        for result in proxy_results]})
        done, pending = await asyncio.wait(closers, timeout=15) if closers else (set(), set())
        diagnostics = []
        for task in pending:
            diagnostics.append({'frames': [{'function': frame.f_code.co_name,
                'file': Path(frame.f_code.co_filename).name, 'line': frame.f_lineno} for frame in task.get_stack(limit=8)]})
            task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=3)
        results = []
        for task in closers:
            if task.cancelled(): results.append({'cancelled': True})
            elif task.done() and task.exception(): results.append(failure_details(task.exception()))
            elif task.done(): results.append({'closed': True})
            else: results.append({'pending': True})
        private(self.evidence.path / 'cleanup-nodes.json', {'class': 'FIXTURE', 'results': results,
                                                          'pending_diagnostics': diagnostics})
        # The bounded etcd authentication+read sequence can span two6s attempts.
        await asyncio.sleep(13)
        for store in self.stores: store.close()
        summary = {'class': 'FIXTURE', 'passed': not pending
            and all(result == {'closed': True} for result in results)
            and not any(isinstance(result, BaseException) for result in proxy_results),
            'thread_settle_seconds': 13}
        private(self.evidence.path / 'cleanup-complete.json', summary)
        return summary

    async def run_row(self, row):
        self.case = row
        if row == 'leader-loss-each-node': return await self.leader_loss_each()
        if row == 'quorum-loss-two-voters': return await self.quorum_loss()
        if row == 'full-restart': return await self.full_restart()
        if row in NETWORK_ROWS: return await self.network_row(row)
        if row in ('stale-member', 'clock-forward', 'clock-backward', 'clock-suspend'): return await self.freshness_row(row)
        if row == 'unknown-commit': return await self.unknown_commit()
        if row in ('lost-result', 'lost-ack'): return await self.lost_result(row)
        if row == 'record-capacity': return await self.capacity()
        if row == 'nospace': return await self.nospace()
        if row == 'retired-return': return await self.retired_return()
        raise ValueError('row_requires_owned_restart_driver')


async def run(lab, evidence, rows):
    harness = MatrixHarness(lab, evidence, rows)
    try:
        await harness.start()
        for row in rows:
            await asyncio.wait_for(harness.run_row(row), 180 if row in ('leader-loss-each-node', 'full-restart') else 90)
    except BaseException as exc:
        harness.evidence.fail(harness.case, exc)
        raise
    finally:
        cleanup = await harness.close()
    if not cleanup['passed']:
        exc = RuntimeError('fixture_cleanup_incomplete')
        harness.evidence.fail('cleanup', exc)
        raise exc
    return harness.evidence.finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--row', action='append', choices=ALL_ROWS, required=True)
    parser.add_argument('--allow-owned-voter-restart', action='store_true')
    parser.add_argument('--raft-proxy-image', help='Exact already-installed Python image digest from fresh proxy topology')
    args = parser.parse_args()
    if 'full-restart' in args.row and not args.allow_owned_voter_restart:
        parser.error('full-restart requires explicit --allow-owned-voter-restart')
    if len(set(args.row)) != len(args.row): parser.error('duplicate row')
    if 'retired-return' in args.row and args.row[-1] != 'retired-return': parser.error('retirement must be last')
    if args.raft_proxy_image:
        from .raft_topology import RaftProxyLab
        lab = RaftProxyLab(args.fixture, args.raft_proxy_image).load()
    else: lab = EtcdLab(args.fixture).load()
    result = asyncio.run(run(lab, args.evidence, args.row))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
