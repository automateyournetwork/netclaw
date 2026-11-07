"""Production service dispatch with signed device proofs; controlled transport."""
import asyncio
from types import SimpleNamespace
import uuid

import pytest

from bgp.federation import certs, protected_contract as c
from bgp.federation.ha.border import ClusterBorderOperations
from bgp.federation.ha.node import ClusterNode
from bgp.federation.ha.factory import HAServiceRuntime
from bgp.federation.ha.edge import proof_bytes, REQUEST_PREFIX
from bgp.federation.ha.edge_service import wire, challenge
from bgp.federation.risk import RiskManager
from bgp.federation.service import FederationService
from bgp.federation.edge import RpcError
from ha_support_179 import cluster_with_keys


def services(tmp_path):
    store, manifest, authorities, keys = cluster_with_keys()
    result = []
    for i in range(2):
        service = SimpleNamespace(runtime=SimpleNamespace(installation=manifest.nodes[i]['installation_id']),
            member_channels={}, edge_channels={}, protected_enabled=True,
            risk=SimpleNamespace(is_border=lambda: True),
            inventory=SimpleNamespace(_harness_card=lambda: {'kind': 'openclaw'}),
            audit=SimpleNamespace(record=lambda **kwargs: None),
            edge_status={'state': 'listening', 'public_origin': manifest.nodes[i]['endpoints']['https'],
                         'host': '127.0.0.1', 'path': '/mobile/ws'})
        adapter = HAServiceRuntime(service, {}, manifest, {'manifest': manifest.value}, 'fixture-anchor')
        node = adapter.node = ClusterNode(authorities[i], private_key=keys[i],
                                          ca_file='unused', cert_file='unused', key_file='unused')
        operations = ClusterBorderOperations(node, state_dir=tmp_path/str(i), member_channels={},
                                             audit_writer=lambda *args: 'audit-fixture')
        service.ha_runtime, service.protected_operations, adapter.operations = adapter, operations, operations
        service._edge_border_capabilities = lambda ch=None, s=service: FederationService._edge_border_capabilities(s, ch)
        async def heartbeat(*args): await asyncio.Event().wait()
        service._edge_heartbeat_loop = heartbeat
        wire(service, adapter, operations)
        result.append(service)
    class Link:
        authenticated = True
        async def call(self, method, params, timeout):
            peer = SimpleNamespace(peer={'node_id': result[1].ha_runtime.node.node_id})
            return await result[0].ha_runtime.node.handlers[method](peer, params)
    result[1].ha_runtime.node.channels[authorities[0].node_id] = Link()
    return store, manifest, result


@pytest.mark.asyncio
async def test_follower_enrollment_and_signed_request_reverified_by_leader(tmp_path):
    store, manifest, nodes = services(tmp_path)
    follower = nodes[1]
    offer = await follower.ha_edge_route('edge/issue', {'node_id': manifest.nodes[1]['node_id'],
        'client_nonce': str(uuid.uuid4()), 'replace_client_nonce': None})
    cert, key = certs.create_self_signed('mobile-fixture')
    ch = SimpleNamespace(trusted=False, _closed=False)
    async def close(): ch._closed = True
    ch.close = close
    hello_challenge = await challenge(follower, ch)
    response = await FederationService._edge_on_enroll(follower, ch, {
        'installation_id': follower.runtime.installation, 'client_nonce': offer['client_nonce'],
        'token': offer['enrollment_token'], 'member_id': 'mobile-fixture', 'cert_pem': cert,
        'signature': RiskManager.sign_challenge(key, proof_bytes(hello_challenge, 'mobile-fixture',
            'enroll', offer['enrollment_token'])).hex(), 'runtime_kind': 'mobile', 'display_name': 'Fixture phone'})
    assert response['border']['cluster']['authority']['state'] == 'follower'
    assert response['border']['capabilities']['protected_operations']['enrollment_generation']
    params = {'installation_id': follower.runtime.installation}
    proof = {'schema_version': 1, **manifest.audience, 'member_id': ch.member_id,
        'enrollment_generation': ch.ha_binding['enrollment_generation'], 'request_id': str(uuid.uuid4()),
        'method': 'n2n/edge/operations/catalog', 'params_sha256': c.sha256(params)}
    proof['signature'] = RiskManager.sign_challenge(key, REQUEST_PREFIX + c.encode(proof)).hex()
    handler = FederationService._edge_protected_handler(follower, 'catalog')
    assert (await handler(ch, dict(params, device_proof=proof)))['capabilities'] == ['cluster_execution_v2']
    context = {'access_mode': 'cluster-device-proof', 'proof': proof, 'params': params}
    with pytest.raises(c.ProtectedError, match='device_ingress_mismatch'):
        await nodes[0].protected_operations._local('catalog', {'auth_context': context},
                                                  ingress_node_id=manifest.nodes[0]['node_id'])
    nodes[0].ha_edge.revoke(ch.member_id)
    with pytest.raises(RpcError) as refused:
        await handler(ch, dict(params, device_proof=proof))
    assert refused.value.data['code'] == 'device_authority_changed'
    for service in nodes:
        # Link is a controlled transport rather than a live NCFED channel.
        service.ha_runtime.node.channels.clear()
        await service.ha_runtime.close()


@pytest.mark.asyncio
async def test_cluster_edge_forwarding_cannot_select_another_ingress(tmp_path):
    _, manifest, nodes = services(tmp_path)
    with pytest.raises(c.ProtectedError, match='device_ingress_mismatch'):
        await nodes[1].ha_edge_route('edge/challenge', {'node_id': manifest.nodes[0]['node_id']})
