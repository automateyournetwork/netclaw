"""NCFED cluster profile uses the existing five-byte framing over actual mTLS."""
import asyncio
import copy

import pytest

from bgp.federation import certs, exporter_tls
from bgp.federation.ha.channel import ClusterChannel, attach
from bgp.federation.ha.config import sign_manifest, verify_manifest, HAError
from bgp.federation.protected_contract import key_id
from test_ha_contract_179 import manifest_fixture


async def pair(tmp_path, *, corrupt=None):
    value, root, root_key = manifest_fixture()
    ca, ca_key = certs.create_risk_ca('cluster-tls')
    keys = []
    for i, node in enumerate(value['nodes']):
        node['certificate'], key = certs.issue_cert(ca, ca_key, node['identity'], san='cluster.test')
        node['key_id'] = key_id(node['certificate'])
        keys.append(key)
    manifest = verify_manifest(sign_manifest(value, root_key), root, expected_key_id=key_id(root))
    files = []
    for name, text in [('ca', ca)] + [(f'cert{i}', n['certificate']) for i, n in enumerate(value['nodes'])] + [(f'key{i}', k) for i, k in enumerate(keys)]:
        path = tmp_path / name
        path.write_text(text); path.chmod(0o600)
        files.append((name, str(path)))
    paths = dict(files)
    connected = asyncio.Queue()
    live = {'value': True}
    async def current(peer):
        if not live['value']:
            raise HAError('node_retired', 403)
    async def status(channel, params):
        return {'observed': params.get('value')}
    async def accept(reader, writer):
        try:
            channel = await attach(reader, writer, manifest=manifest, node_id=value['nodes'][0]['node_id'],
                peer_node_id=value['nodes'][1]['node_id'], private_key=keys[0],
                current=current, handlers={'n2n/cluster/status': status}, is_initiator=False)
            await connected.put(channel)
        except Exception as exc:
            await connected.put(exc)
    server = await exporter_tls.start_server(accept, '127.0.0.1', 0,
        cert_file=paths['cert0'], key_file=paths['key0'], peer_ca_file=paths['ca'])
    try:
        reader, writer = await exporter_tls.open_connection('127.0.0.1', server.sockets[0].getsockname()[1],
            ca_file=paths['ca'], server_hostname='cluster.test', cert_file=paths['cert1'], key_file=paths['key1'])
        options = dict(manifest=manifest, node_id=value['nodes'][1]['node_id'],
            peer_node_id=value['nodes'][0]['node_id'], private_key=keys[1], current=current,
            handlers={'n2n/cluster/status': status}, is_initiator=True)
        if corrupt:
            corrupt(options, keys, value)
        channel = await attach(reader, writer, **options)
        peer = await asyncio.wait_for(connected.get(), 2)
        if isinstance(peer, Exception):
            raise peer
        return channel, peer, server, live
    except BaseException:
        server.close(); await server.wait_closed()
        raise


@pytest.mark.asyncio
async def test_ncfed_authenticated_pair_and_role_separation(tmp_path):
    client, peer, server, live = await pair(tmp_path)
    try:
        assert isinstance(client, ClusterChannel)
        assert client.authenticated and peer.authenticated
        assert await client.call('n2n/cluster/status', {'value': 42}) == {'observed': 42}
        for method in ('n2n/tools/call', 'in2n/hello', 'execution/submit', 'n2n/hello'):
            with pytest.raises(HAError, match='cluster_method_refused'):
                await client.call(method, {})
        live['value'] = False
        with pytest.raises(HAError, match='node_retired'):
            await client.call('n2n/cluster/status', {})
    finally:
        await client.close(); await peer.close()
        server.close(); await server.wait_closed()


@pytest.mark.asyncio
async def test_wrong_application_key_cannot_use_valid_transport(tmp_path):
    with pytest.raises((HAError, ConnectionError)):
        await pair(tmp_path, corrupt=lambda opts, keys, value: opts.update(private_key=keys[2]))


@pytest.mark.asyncio
async def test_duplicate_json_closes_cluster_channel(tmp_path):
    client, peer, server, live = await pair(tmp_path)
    try:
        await client._dispatch(b'{"jsonrpc":"2.0","id":"x","id":"y","result":{}}')
        assert client._closed
    finally:
        await client.close(); await peer.close()
        server.close(); await server.wait_closed()
