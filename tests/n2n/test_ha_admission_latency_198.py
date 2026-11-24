"""Controlled WAN-cost reproduction; real TLS, fixture quorum, NO provider.

The 320 ms store delay is the recorded r10l observation, not a new WAN
measurement. Approval is seeded with the existing state-machine fixture.
"""
import asyncio
import time

import pytest

from bgp.federation import certs, exporter_tls, protected_contract as c
from bgp.federation.channel import RpcError
from bgp.federation.ha.admission import MemberAdmission
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.config import HAError, sign_manifest, verify_manifest
from bgp.federation.ha.internal import MemberAttachments, accept_member
from bgp.federation.ha.node import ClusterNode
from test_ha_authority_179 import MemoryStore
from test_ha_contract_179 import manifest_fixture
from test_ha_execution_contract_179 import ha_approval
from test_ha_operations_179 import dispatch_fixture


class DelayedStore(MemoryStore):
    delay = 0

    def __init__(self):
        super().__init__()
        self.calls = []

    def read_many(self, keys):
        if self.delay:
            self.calls.append('snapshot')
            time.sleep(self.delay)
        return super().read_many(keys)

    def txn(self, comparisons, writes):
        if self.delay:
            self.calls.append('txn')
            time.sleep(self.delay)
        return super().txn(comparisons, writes)


@pytest.mark.asyncio
@pytest.mark.parametrize('admission_ms,ingress,delay,succeeds', [
    (4500, 1, .320, False), (9000, 0, .320, True), (9000, 1, .320, True),
    (9000, 1, .400, True), (9000, 1, .700, False)])
async def test_real_attachment_and_follower_admission_with_recorded_quorum_delay(
        tmp_path, admission_ms, ingress, delay, succeeds, record_property):
    value, root, root_key = manifest_fixture()
    value['limits']['admission_ms'] = admission_ms
    ca, ca_key = certs.create_risk_ca('latency-fixture')
    paths, keys, servers, nodes, accepted, dialers = {}, [], [], [], [], []
    store = DelayedStore()
    attachments = None
    for i, node in enumerate(value['nodes']):
        node['certificate'], key = certs.issue_cert(ca, ca_key, node['identity'], san='latency.test')
        node['key_id'] = c.key_id(node['certificate'])
        keys.append(key)
        for kind, content in [('cert', node['certificate']), ('key', key)]:
            path = tmp_path / (kind + str(i)); path.write_text(content); path.chmod(0o600)
            paths[kind + str(i)] = str(path)
    path = tmp_path / 'ca'; path.write_text(ca); paths['ca'] = str(path)
    try:
        for i, node in enumerate(value['nodes']):
            async def incoming(r, w, index=i):
                await nodes[index]._accept(r, w)
            async def member_incoming(r, w, index=i):
                await accept_member(nodes[index], r, w,
                    handlers={'execution/admission': nodes[index].admit_member},
                    on_authenticated=accepted.append)
            for kind, handler in [('cluster', incoming), ('in2n', member_incoming)]:
                server = await exporter_tls.start_server(handler, '127.0.0.1', 0,
                    cert_file=paths['cert'+str(i)], key_file=paths['key'+str(i)],
                    **({'peer_ca_file': paths['ca']} if kind == 'cluster' else {}))
                servers.append(server)
                node['endpoints'][kind] = {'host': '127.0.0.1',
                    'port': server.sockets[0].getsockname()[1], 'server_name': 'latency.test'}
        manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=c.key_id(root))
        authorities = [Authority(store, manifest, n['node_id']) for n in manifest.nodes]
        authorities[0].bootstrap(create=True); authorities[0].campaign()
        for i, authority in enumerate(authorities):
            nodes.append(ClusterNode(authority, private_key=keys[i], ca_file=paths['ca'],
                cert_file=paths['cert'+str(i)], key_file=paths['key'+str(i)]))
        for node in nodes:
            for peer in manifest.nodes:
                if node.node_id < peer['node_id']:
                    dialers.append(asyncio.create_task(node._dial(peer)))
        async with asyncio.timeout(5):
            while any(len(n.channels) != 2 for n in nodes):
                await asyncio.sleep(.01)
        for task in dialers: task.cancel()
        await asyncio.gather(*dialers, return_exceptions=True)
        _, member, payload = ha_approval()
        leader = manifest.nodes[0]
        payload['border'] = {'installation_id': leader['installation_id'], 'identity': leader['identity'],
            'key_id': leader['key_id'], 'authority_generation': manifest.generation}
        payload['cluster'] = {**manifest.audience, 'manifest_revision': manifest.revision,
            'issuer_node_id': leader['node_id'], 'authority_epoch': authorities[0].epoch}
        import uuid
        payload['principal']['subject'] = str(uuid.uuid5(uuid.UUID(manifest.cluster_id), 'netclaw.open-lab.operator'))
        review = c.review_from_payload(payload)
        ledger = nodes[0].ledger
        ledger.now = lambda: payload['issued_at_ms']
        ledger.enroll_member(review['member'], member['cert_pem'])
        row = ledger.prepare('latency-fixture', 'a'*64, review)
        row = dispatch_fixture(store, authorities, ledger, row)
        async def current(): pass
        attachments = MemberAttachments(manifest, review['member'], member['key_pem'],
            ca_file=paths['ca'], handlers={}, current=current)
        for node in manifest.nodes: await attachments.connect(node['node_id'])
        # Exercise the selected ingress through the production selector. These
        # controlled rankings are not represented as measured cloud RTTs.
        for index, node in enumerate(manifest.nodes):
            attachments.channels[node['node_id']].rtt_ms = 1 if index == ingress else 100
        journal = MemberAdmission(tmp_path / 'journal', manifest, review['member'])
        context = {k: row[k] for k in ('operation_id', 'attempt_id', 'approval_digest')}
        effects = []
        async def effect(): effects.append('fixture'); return 'fixture'
        store.delay = delay
        started = time.monotonic()
        try:
            if succeeds:
                assert await journal.run(context, 'model', 1, 'c'*64, attachments.send_admission, effect) == 'fixture'
            else:
                with pytest.raises((HAError, RpcError)):
                    await journal.run(context, 'model', 1, 'c'*64, attachments.send_admission, effect)
        finally:
            elapsed = time.monotonic() - started
            record_property('admission_seconds', elapsed)
            record_property('quorum_calls', len(store.calls))
            print({'admission_ms': admission_ms, 'ingress': ingress, 'store_delay': delay, 'seconds': round(elapsed, 3),
                   'quorum_calls': len(store.calls), 'effects': len(effects)})
        assert effects == (['fixture'] if succeeds else [])
        with pytest.raises(HAError, match='admission_spent'):
            await journal.run(context, 'model', 1, 'c'*64, attachments.send_admission, effect)
    finally:
        store.delay = 0
        for task in dialers: task.cancel()
        if dialers: await asyncio.gather(*dialers, return_exceptions=True)
        if attachments: await attachments.close()
        for channel in accepted: await channel.close()
        for node in nodes: await node.close()
        for server in servers: server.close(); await server.wait_closed()
