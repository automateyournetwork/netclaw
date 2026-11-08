"""Explicit controlled state-machine fixture; no provider or native execution."""
from bgp.federation import certs, protected_contract as c
from bgp.federation.ha.config import verify_manifest, sign_manifest
from bgp.federation.ha.authority import Authority
from test_ha_contract_179 import manifest_fixture
from test_ha_authority_179 import MemoryStore


def cluster_with_keys():
    value, root, root_key = manifest_fixture()
    keys = []
    for node in value['nodes']:
        certificate, private_key = certs.create_self_signed(node['identity'])
        node.update(certificate=certificate, key_id=c.key_id(certificate))
        keys.append(private_key)
    manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=c.key_id(root))
    store = MemoryStore()
    nodes = [Authority(store, manifest, node['node_id']) for node in manifest.nodes]
    nodes[0].bootstrap(create=True); nodes[0].campaign()
    return store, manifest, nodes, keys
