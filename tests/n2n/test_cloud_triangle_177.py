"""Three independent strict TLS organizations on loopback; no cloud claim."""
import asyncio
from contextlib import asynccontextmanager

from bgp.constants import ncfed_initiates
from bgp.federation import certs
from bgp.federation.endpoint_registry import Registry
from test_internal_transport import _service


@asynccontextmanager
async def triangle(tmp_path):
    services, entries, registries, servers, writers = [], [], [], [], []
    try:
        for index, label in enumerate(('local-c', 'cloud-a', 'cloud-b')):
            home = tmp_path / label
            svc = _service(home, 65001 + index, f'192.0.2.{index + 1}', label)
            home.chmod(0o700)
            svc.risk.set_role('border', risk_name=label, enabled_stacks='both')
            services.append(svc)
            ca, ca_key = certs.create_risk_ca(label)
            name = label + '.example.test'
            certificate, private = certs.issue_cert(ca, ca_key, name, san=name)
            for filename, value in [('ca', ca), ('cert', certificate), ('key', private)]:
                file = home / (filename + '.pem')
                file.write_text(value)
                file.chmod(0o600)
            entry = dict(id='external', direction='listen', service='en2n', profile='en2n-tls13-v1',
                         transport='direct_tcp', address_ref=label, routing_host='127.0.0.1', routing_port=24001 + index,
                         tls_server_name=name, ca_file=str(home / 'ca.pem'), application_identity=svc.local_identity,
                         application_trust=certs.key_fingerprint(certificate), bind_host='127.0.0.1', bind_port=25001 + index,
                         cert_file=str(home / 'cert.pem'), key_file=str(home / 'key.pem'))
            entries.append(entry)
            registry = Registry(home / 'transport/registry.json', label)
            registries.append(registry)
            svc.transport_registry = lambda registry=registry: registry
            async def accept(reader, writer, svc=svc, entry=entry):
                writers.append(writer)
                await svc.accept_public_ncfed(reader, writer, entry, 1)
            server = await asyncio.start_server(accept, '127.0.0.1', 0)
            entry['bind_port'] = entry['routing_port'] = server.sockets[0].getsockname()[1]
            servers.append(server)
        for index, svc in enumerate(services):
            peers = []
            for remote_index, remote in enumerate(services):
                if index == remote_index:
                    continue
                entry = {k: v for k, v in entries[remote_index].items() if k not in ('bind_host', 'bind_port', 'cert_file', 'key_file')}
                entry.update(id=f'peer-{remote_index}', direction='dial')
                peers.append(entry)
                svc.manager.local_consent(remote.local_as, remote.router_id)
            registries[index].replace({'schemaVersion': 2, 'installationId': ('local-c', 'cloud-a', 'cloud-b')[index],
                                       'revision': 1, 'entries': [entries[index], *peers]}, expected_revision=0)
        # A real listener exists for C's certificate identity, but no inbound
        # connection is possible. All pairs still carry both RPC directions.
        servers[0].close()
        await servers[0].wait_closed()
        yield services, entries, registries
    finally:
        for svc in services:
            for channel in list(svc.channels.values()):
                await channel.close()
        for writer in writers:
            writer.close()
        for server in servers:
            server.close()
        for server in servers:
            await server.wait_closed()
        for svc in services:
            svc.manager.close()


async def connect_triangle(services):
    for first, second in ((0, 1), (0, 2), (1, 2)):
        a, b = services[first], services[second]
        assert ncfed_initiates(a.local_as, a.router_id, b.local_as, b.router_id)
        await a.open_channel(b.local_as, b.router_id, '192.0.2.254', 1)
        assert b.local_identity in a.channels and a.local_identity in b.channels


def test_full_triangle_outbound_local_and_six_directions(tmp_path):
    asyncio.run(check_full_triangle(tmp_path))


async def check_full_triangle(tmp_path):
    async with triangle(tmp_path) as (services, entries, registries):
        assert len({e['application_trust'] for e in entries}) == 3
        await connect_triangle(services)
        for destination in services:
            async def probe(channel, params, destination=destination):
                return {'at': destination.local_identity, 'from': channel.peer_identity}
            for channel in destination.channels.values():
                channel.register('test/triangle', probe)
        for source in services:
            assert len(source.channels) == 2 and not source.member_channels
            for destination in services:
                if source is destination:
                    continue
                channel = source.channels[destination.local_identity]
                assert channel.authenticated and channel.attestation == 'possession'
                assert source.manager.is_federated(destination.local_identity)
                assert await channel.call('test/triangle', {}, timeout=2) == {
                    'at': destination.local_identity, 'from': source.local_identity}
        # Loss of one pair leaves the other two independent channels usable.
        a, b, c = services
        await a.channels[b.local_identity].close()
        assert (await a.channels[c.local_identity].call('test/triangle', {}, timeout=2))['at'] == c.local_identity
        assert (await b.channels[c.local_identity].call('test/triangle', {}, timeout=2))['at'] == c.local_identity
