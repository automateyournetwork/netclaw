import pytest

from bgp.federation.ha.node import ClusterNode
from bgp.federation.ha.config import HAError, sign_manifest, verify_manifest
from bgp.federation.protected_contract import key_id
from test_ha_authority_179 import MemoryStore
from test_ha_contract_179 import manifest_fixture
from bgp.federation.ha.authority import Authority


def nodes():
    value, root, root_key = manifest_fixture()
    manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=key_id(root))
    store = MemoryStore()
    authorities = [Authority(store, manifest, item['node_id']) for item in manifest.nodes]
    authorities[0].bootstrap(create=True); authorities[0].campaign()
    result = [ClusterNode(a, private_key='unused', ca_file='unused', cert_file='unused', key_file='unused') for a in authorities]
    return store, result


@pytest.mark.asyncio
async def test_forwarding_lost_reply_does_not_select_another_channel():
    store, cluster = nodes()
    calls = []
    class Channel:
        authenticated = True
        async def call(self, method, params, timeout):
            calls.append((method, params))
            store.revoke_lease('123'); cluster[2].authority.campaign()
            raise ConnectionError('lost reply')
    cluster[1].channels[cluster[0].node_id] = Channel()
    with pytest.raises(ConnectionError):
        await cluster[1].route('n2n/cluster/forward', {'action': 'prepare', 'params': {}})
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_forward_does_not_grant_authority_from_serialized_principal():
    store, cluster = nodes()
    seen = []
    async def authenticate(action, params, *, ingress_node_id):
        assert ingress_node_id == cluster[0].node_id
        seen.append((action, params))
        raise HAError('lab_context_refused', 403)
    cluster[0].dispatch = authenticate
    with pytest.raises(HAError, match='lab_context_refused'):
        await cluster[0]._forward(None, {'action': 'prepare', 'params': {'principal': 'asserted'}})
    assert seen == [('prepare', {'principal': 'asserted'})]
    with pytest.raises(HAError, match='cluster_method_refused'):
        await cluster[0]._forward(None, {'action': 'shell', 'params': {}})


@pytest.mark.asyncio
async def test_quorum_or_retirement_closes_current_authority():
    store, cluster = nodes()
    await cluster[0].current(cluster[1].node_id)
    control, revision = store.read('control')
    control['nodes'][cluster[1].node_id]['state'] = 'retired'
    store.txn([('control', 'revision', revision)], [('control', control, None)])
    with pytest.raises(HAError, match='node_retired'):
        await cluster[0].current(cluster[1].node_id)
    store.available = False
    with pytest.raises(HAError, match='no_quorum'):
        await cluster[0].current(cluster[2].node_id)
