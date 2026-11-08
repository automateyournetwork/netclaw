"""Three outbound member attachments remain separate from cluster peer roles."""
import asyncio
import uuid

import pytest

from bgp.federation import certs, exporter_tls
from bgp.federation.ha.internal import MemberAttachments, accept_member
from bgp.federation.ha.config import HAError, sign_manifest, verify_manifest
from bgp.federation.ha.authority import Authority
from bgp.federation.ha.node import ClusterNode
from bgp.federation.protected_contract import key_id
from test_ha_authority_179 import MemoryStore
from test_ha_contract_179 import manifest_fixture


@pytest.mark.asyncio
async def test_one_member_attaches_to_three_distinct_borders_and_rejects_cluster_method(tmp_path):
    value, root, root_key = manifest_fixture()
    ca, ca_key = certs.create_risk_ca('attachment-tls')
    keys, paths = [], {}
    for i, node in enumerate(value['nodes']):
        node['certificate'], private = certs.issue_cert(ca, ca_key, node['identity'], san='member-border.test')
        node['key_id'] = key_id(node['certificate']); keys.append(private)
        for kind, content in [('cert', node['certificate']), ('key', private)]:
            path = tmp_path / (kind + str(i)); path.write_text(content); path.chmod(0o600)
            paths[kind + str(i)] = str(path)
    path = tmp_path / 'ca'; path.write_text(ca); paths['ca'] = str(path)
    # Reserve actual listeners before signing endpoints, preserving exact names.
    servers, accepted = [], {}
    runtime_nodes = []
    async def accept(index, reader, writer):
        channel = await accept_member(runtime_nodes[index], reader, writer,
            handlers={'execution/catalog': catalog}, on_authenticated=lambda ch: accepted.update({index: ch}))
        return channel
    async def catalog(channel, params): return {'controlled': True}
    try:
        for i in range(3):
            async def incoming(r, w, index=i): return await accept(index, r, w)
            server = await exporter_tls.start_server(incoming, '127.0.0.1', 0,
                cert_file=paths['cert'+str(i)], key_file=paths['key'+str(i)])
            servers.append(server)
            value['nodes'][i]['endpoints']['in2n'] = {'host': '127.0.0.1',
                'port': server.sockets[0].getsockname()[1], 'server_name': 'member-border.test'}
        manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=key_id(root))
        store = MemoryStore()
        for i, node in enumerate(manifest.nodes):
            authority = Authority(store, manifest, node['node_id'])
            if i == 0: authority.bootstrap(create=True); authority.campaign()
            runtime_nodes.append(ClusterNode(authority, private_key=keys[i], ca_file=paths['ca'],
                cert_file=paths['cert'+str(i)], key_file=paths['key'+str(i)]))
        member_cert, member_private = certs.create_self_signed('test-member')
        binding = {'installation_id': str(uuid.uuid4()), 'member_id': 'risk/member',
                   'key_id': key_id(member_cert), 'enrollment_generation': str(uuid.uuid4())}
        runtime_nodes[0].ledger.enroll_member(binding, member_cert)
        async def current(): return None
        attachments = MemberAttachments(manifest, binding, member_private, ca_file=paths['ca'],
                                         handlers={'execution/catalog': catalog}, current=current)
        try:
            for node in manifest.nodes:
                await attachments.connect(node['node_id'])
            assert len(attachments.channels) == len(accepted) == 3
            assert len({ch.protected_peer_binding['installation_id'] for ch in attachments.channels.values()}) == 3
            for channel in accepted.values():
                assert channel.protected_peer_binding == binding
                assert await channel.call('execution/catalog', {}) == {'controlled': True}
                with pytest.raises(HAError, match='attachment_method_refused'):
                    await channel.call('n2n/cluster/forward', {})
            old = attachments.channels[manifest.nodes[0]['node_id']]
            await old.close()
            assert len(attachments.channels) == 2
            replacement = await attachments.connect(manifest.nodes[0]['node_id'])
            assert replacement is not old and len(attachments.channels) == 3
        finally:
            await attachments.close()
            for channel in accepted.values(): await channel.close()
    finally:
        for server in servers:
            server.close(); await server.wait_closed()
