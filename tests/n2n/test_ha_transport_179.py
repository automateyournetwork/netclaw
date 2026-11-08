"""Actual local TLS sockets; this is transport evidence, not runtime execution."""
import asyncio
import ssl

import pytest

from bgp.federation import certs, exporter_tls as tls
from bgp.federation.endpoint_registry import validate_cluster_endpoint


@pytest.fixture
def material(tmp_path):
    ca, key = certs.create_risk_ca('r08-transport')
    server, server_key = certs.issue_cert(ca, key, 'border.test', san='border.test')
    client, client_key = certs.issue_cert(ca, key, 'other.test', san='other.test')
    foreign_ca, foreign_key = certs.create_risk_ca('foreign')
    foreign, foreign_private = certs.issue_cert(foreign_ca, foreign_key, 'foreign.test')
    result = {}
    for name, value in locals().copy().items():
        if isinstance(value, str) and value.startswith('-----BEGIN'):
            path = tmp_path / (name + '.pem')
            path.write_text(value)
            path.chmod(0o600)
            result[name] = str(path)
    return result


@pytest.mark.asyncio
async def test_mutual_tls_preserves_exporter_and_identifies_both_peers(material):
    accepted = asyncio.Queue()
    server = await tls.start_server(lambda r, w: accepted.put_nowait((r, w)), '127.0.0.1', 0,
        cert_file=material['server'], key_file=material['server_key'], peer_ca_file=material['ca'])
    writers = []
    try:
        cr, cw = await tls.open_connection('127.0.0.1', server.sockets[0].getsockname()[1],
            ca_file=material['ca'], server_hostname='border.test',
            cert_file=material['client'], key_file=material['client_key'])
        sr, sw = await asyncio.wait_for(accepted.get(), 2)
        writers += [cw, sw]
        assert cw.get_extra_info('tls_exporter') == sw.get_extra_info('tls_exporter')
        for writer in writers:
            assert writer.get_extra_info('tls_profile') == 'ncfed-cluster-mtls-v1'
            assert writer.get_extra_info('tls_peer_certificate')
        cw.write(b'NCFED'); await cw.drain()
        assert await sr.readexactly(5) == b'NCFED'
    finally:
        for writer in writers:
            writer.close()
        server.close(); await server.wait_closed()
        for writer in writers:
            await writer.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize('peer', ['missing', 'foreign'])
async def test_unenrolled_transport_ca_refused_before_application(material, peer):
    admitted = []
    server = await tls.start_server(lambda r, w: admitted.append(w), '127.0.0.1', 0,
        cert_file=material['server'], key_file=material['server_key'], peer_ca_file=material['ca'],
        handshake_timeout=.3)
    writer = None
    try:
        kwargs = {} if peer == 'missing' else dict(cert_file=material['foreign'], key_file=material['foreign_private'])
        with pytest.raises((ssl.SSLError, ConnectionError)):
            reader, writer = await tls.open_connection('127.0.0.1', server.sockets[0].getsockname()[1],
                ca_file=material['ca'], server_hostname='border.test', **kwargs)
            await asyncio.wait_for(reader.readexactly(1), 1)
        assert admitted == []
    finally:
        if writer:
            writer.close(); await writer.wait_closed()
        server.close(); await server.wait_closed()


def test_cluster_endpoint_has_explicit_separate_profile_and_no_tunnel(material):
    endpoint = dict(profile='ncfed-cluster-mtls-v1', transport='direct_tcp',
        routing_host='127.0.0.1', routing_port=5443, tls_server_name='border.test',
        ca_file=material['ca'], cert_file=material['client'], key_file=material['client_key'])
    assert validate_cluster_endpoint(endpoint) == endpoint
    for key, value in [('profile', 'in2n-tls-exporter-v1'), ('transport', 'ngrok_tcp'),
                       ('routing_host', 'https://example.com'), ('key_file', 'relative.key')]:
        with pytest.raises(ValueError):
            validate_cluster_endpoint({**endpoint, key: value})
    with pytest.raises(ValueError):
        validate_cluster_endpoint({**endpoint, 'proxy': 'ambient'})


@pytest.mark.asyncio
async def test_owned_tls_listener_closes_live_and_pending_connections(material):
    accepted = asyncio.Event()
    cancelled = asyncio.Event()
    async def handle(reader, writer):
        accepted.set()
        try: await asyncio.Event().wait()
        finally: cancelled.set()
    server = await tls.start_server(handle, '127.0.0.1', 0,
        cert_file=material['server'], key_file=material['server_key'],
        peer_ca_file=material['ca'], close_clients=True)
    port = server.sockets[0].getsockname()[1]
    _, client = await tls.open_connection('127.0.0.1', port,
        ca_file=material['ca'], server_hostname='border.test',
        cert_file=material['client'], key_file=material['client_key'])
    _, pending = await asyncio.open_connection('127.0.0.1', port)
    await asyncio.wait_for(accepted.wait(), 2)
    try:
        server.close()
        await asyncio.wait_for(server.wait_closed(), 2)
        assert cancelled.is_set()
        await asyncio.wait_for(client.wait_closed(), 2)
    finally:
        client.close(); pending.close()
        await pending.wait_closed()
