"""Real local transport/admission through a byte forwarder; NOT live ngrok."""
import asyncio
import json
import ssl
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from contextlib import asynccontextmanager

import pytest

from bgp.federation import certs, exporter_tls
from bgp.federation.channel import RpcError
from bgp.federation.endpoint_registry import Registry
from test_exporter_tls_168 import material
from test_internal_transport import _service
from test_endpoint_registry_168 import registry_data


@pytest.mark.asyncio
async def test_listener_readiness_requires_current_bound_identity(tmp_path, material, registry_data):
    border = _service(tmp_path/'ready-border', 65001, '1.2.3.4', 'Border')
    registry = Registry(tmp_path/'ready-registry.json', 'test-installation')
    server = await exporter_tls.start_server(lambda r, w: w.close(), '127.0.0.1', 0,
                                             cert_file=material['cert'], key_file=material['key'])
    entry = dict(registry_data['entries'][0], bind_port=server.sockets[0].getsockname()[1],
                 cert_file=material['cert'], key_file=material['key'])
    registry.replace(dict(registry_data, entries=[entry]), expected_revision=0)
    border.transport_registry = lambda: registry
    border._in2n_server = server
    border._registered_listeners = {entry['id']:dict(entry)}
    try:
        assert border.endpoint_status()['services'][0]['listener_ready'] is True
        registry.update_address('members', 'new.example.test', 21003, 'ra_new', expected_revision=1)
        assert border.endpoint_status()['services'][0]['listener_ready'] is True
        value = registry.load(); value['entries'][0]['tls_server_name'] = 'changed.example.test'
        registry.replace(value, expected_revision=2)
        assert border.endpoint_status()['services'][0]['listener_ready'] is False
        registry.recover(expected_revision=3)
        assert border.endpoint_status()['services'][0]['listener_ready'] is True
        server.close(); await server.wait_closed()
        assert border.endpoint_status()['services'][0]['listener_ready'] is False
    finally:
        server.close(); await server.wait_closed(); border.manager.close()


@asynccontextmanager
async def pair(tmp_path, material, *, direct=False):
    border = _service(tmp_path/'border', 65001, '1.2.3.4', 'Border')
    member = _service(tmp_path/'member', 65001, '1.2.3.4', 'Member')
    border.risk.set_role('border', risk_name='example', enabled_stacks='in2n')
    member.risk.set_role('member', risk_name='example', self_member_id='example/test')
    anchor, _ = border.risk.ensure_risk_ca()
    border.risk.hub_credential()
    registration = dict(id='members', direction='listen', service='in2n', profile='in2n-tls-exporter-v1',
                        routing_host='127.0.0.1', routing_port=21001, reservation_id='ra_fixture',
                        tls_server_name='border.example.test', ca_file=material['ca'],
                        application_identity='example/border', application_trust=anchor,
                        bind_host='127.0.0.1', bind_port=42101,
                        cert_file=material['cert'], key_file=material['key'])
    if direct:
        registration.pop('reservation_id')
        registration.update(transport='direct_tcp', address_ref='direct-fixture')
    connections, bridges = [], set()
    async def accept(reader, writer):
        connections.append(writer)
        await border.accept_internal(reader, writer, registration=registration, registry_revision=1)
    server = await exporter_tls.start_server(accept, '127.0.0.1', 0,
                                             cert_file=material['cert'], key_file=material['key'])
    border._in2n_server = server
    registration['bind_port'] = server.sockets[0].getsockname()[1]
    async def forward(reader, writer):
        task = asyncio.current_task(); bridges.add(task)
        upstream = None
        try:
            remote, upstream = await asyncio.open_connection('127.0.0.1', registration['bind_port'])
            async def pipe(source, target):
                try:
                    while data := await source.read(65536):
                        target.write(data); await target.drain()
                finally: target.close()
            await asyncio.gather(pipe(reader, upstream), pipe(remote, writer))
        except (ConnectionError, asyncio.CancelledError): pass
        finally:
            writer.close()
            if upstream: upstream.close()
            bridges.discard(task)
    forwarder = None if direct else await asyncio.start_server(forward, '127.0.0.1', 0)
    border._test_forwarder = forwarder
    dial = {k:v for k,v in registration.items() if k not in ('bind_host','bind_port','cert_file','key_file')}
    dial.update(direction='dial', routing_port=(server if direct else forwarder).sockets[0].getsockname()[1])
    if direct:
        from bgp.federation.endpoint_registry import validate_entry
        validate_entry(registration, 2); validate_entry(dial, 2)
    try:
        yield border, member, dial
    finally:
        for channel in list(border.member_channels.values()) + ([member.border_channel] if member.border_channel else []):
            await channel.close()
        for writer in connections: writer.close()
        for bridge in list(bridges): bridge.cancel()
        if bridges: await asyncio.gather(*list(bridges), return_exceptions=True)
        if forwarder:
            forwarder.close(); await forwarder.wait_closed()
        server.close(); await server.wait_closed()
        border.manager.close(); member.manager.close()


async def dial(member, entry, token=''):
    return await member.dial_border(entry['routing_host'], entry['routing_port'],
                                    enrollment_token=token, registration=entry, registry_revision=1)


@pytest.mark.asyncio
async def test_strict_enrollment_reconnect_behind_loopback_forwarding(tmp_path, material):
    async with pair(tmp_path, material) as (border, member, entry):
        result = await dial(member, entry, border.risk.issue_token()['token'])
        assert result['pinned']
        old = member.risk.self_cert_pem()
        assert member.border_channel.trusted and member.border_channel.attestation == 'possession'
        first = border.member_channels['example/test'].auth_binding
        assert first.startswith(b'netclaw-in2n-tls-exporter-v1\0')
        await member.border_channel.close(); await asyncio.sleep(.02)
        result = await dial(member, entry)
        assert result['trusted'] and old == member.risk.self_cert_pem()
        assert first != border.member_channels['example/test'].auth_binding
        assert not member.member_channels


@pytest.mark.asyncio
async def test_wrong_border_anchor_refused_before_token_consumption(tmp_path, material):
    async with pair(tmp_path, material) as (border, member, entry):
        token = border.risk.issue_token()['token']
        wrong, _ = certs.create_risk_ca('wrong-border')
        with pytest.raises((RuntimeError, ValueError, RpcError, ConnectionError)):
            await dial(member, dict(entry, application_trust=wrong), token)
        assert border.risk.get_member('example/test') is None
        assert (await dial(member, entry, token))['pinned']


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['tls_name', 'ca', 'border_identity', 'altered_binding', 'forged_key', 'unknown', 'expired'])
async def test_strict_identity_refusals(tmp_path, material, failure):
    async with pair(tmp_path, material) as (border, member, entry):
        token = border.risk.issue_token(ttl_seconds=-10 if failure == 'expired' else 60)['token']
        if failure == 'tls_name': entry = dict(entry, tls_server_name='wrong.example.test')
        if failure == 'ca': entry = dict(entry, ca_file=material['other'])
        if failure == 'border_identity': entry = dict(entry, application_identity='different/border')
        if failure == 'altered_binding':
            sign = member.risk.self_sign
            member.risk.self_sign = lambda nonce,binding=b'': sign(nonce, b'altered'+binding)
        if failure == 'forged_key':
            _, key = certs.create_self_signed('forger')
            member.risk.self_sign = lambda nonce,binding=b'': member.risk.sign_challenge(key, nonce+binding)
        if failure == 'unknown': token = ''
        with pytest.raises((RuntimeError, ValueError, RpcError, ConnectionError, ssl.SSLError)):
            await dial(member, entry, token)
        assert not border.member_channels and not member.border_channel
        assert border.risk.get_member('example/test') is None


@pytest.mark.asyncio
async def test_cross_connection_proof_and_enrollment_replay(tmp_path, material):
    async with pair(tmp_path, material) as (border, member, entry):
        proof = []
        original = member.risk.self_sign
        def capture(nonce, binding=b''):
            signature = original(nonce, binding); proof.append(signature); return signature
        member.risk.self_sign = capture
        token = border.risk.issue_token()['token']
        await dial(member, entry, token)
        await member.border_channel.close(); await asyncio.sleep(.02)
        member.risk.self_sign = lambda nonce,binding=b'': proof[0]
        with pytest.raises((RpcError, ConnectionError)):
            await dial(member, entry)
        member.risk.self_sign = original
        with pytest.raises((RpcError, ConnectionError)):
            await dial(member, entry, token)
        assert not border.member_channels


@pytest.mark.asyncio
@pytest.mark.parametrize('action', ['repeat', 'revoke'])
async def test_repeated_authentication_and_revoked_open_channel(tmp_path, material, action):
    async with pair(tmp_path, material) as (border, member, entry):
        await dial(member, entry, border.risk.issue_token()['token'])
        channel = member.border_channel
        if action == 'revoke':
            border.risk.remove_member('example/test')
            method, params = 'n2n/inventory', {}
        else:
            method, params = 'in2n/hello', {}
        with pytest.raises((RpcError, ConnectionError)):
            await channel.call(method, params, timeout=2)
        await asyncio.sleep(.02)
        assert not border.member_channels
        if action == 'revoke':
            with pytest.raises((RpcError, ConnectionError)):
                await dial(member, entry)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['expired', 'forged', 'repeat', 'revoke'])
async def test_border_denial_is_audited_without_submitted_secrets(tmp_path, material, caplog, failure):
    async with pair(tmp_path, material) as (border, member, entry):
        token = border.risk.issue_token(ttl_seconds=-10 if failure == 'expired' else 60)['token']
        if failure == 'forged':
            _, key = certs.create_self_signed('forger')
            member.risk.self_sign = lambda nonce, binding=b'': member.risk.sign_challenge(key, nonce+binding)
        if failure in ('expired', 'forged'):
            with pytest.raises((RpcError, ConnectionError)):
                await dial(member, entry, token)
        else:
            await dial(member, entry, token)
            if failure == 'revoke':
                border.risk.remove_member('example/test')
            with pytest.raises((RpcError, ConnectionError)):
                await member.border_channel.call(
                    'in2n/hello' if failure == 'repeat' else 'n2n/inventory',
                    {'token': token, 'private_marker': 'never-log-submitted-data'}, timeout=2)
        await asyncio.sleep(.02)
        denials = [row for row in border.audit.recent()
                   if row['target_type'] == 'transport' and row['outcome'] == 'denied']
        assert len(denials) == 1
        assert denials[0]['channel_kind'] == 'in2n'
        assert denials[0]['peer_identity'] == entry['id']
        assert denials[0]['decision'] in ('authentication_refused', 'current_authority_refused')
        serialized = json.dumps(denials) + caplog.text
        assert token not in serialized and 'never-log-submitted-data' not in serialized
        assert not border.member_channels


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['call', 'notify'])
async def test_revoked_member_receives_no_new_work_on_open_channel(tmp_path, material, operation):
    async with pair(tmp_path, material) as (border, member, entry):
        await dial(member, entry, border.risk.issue_token()['token'])
        received = []
        async def harmless_probe(channel, params):
            received.append(params)
            return {'ok': True}
        member.border_channel.register('test/revocation-probe', harmless_probe)
        channel = border.member_channels['example/test']
        border.risk.remove_member('example/test')
        with pytest.raises((RpcError, ConnectionError)):
            await getattr(channel, operation)('test/revocation-probe', {})
        await asyncio.sleep(.02)
        assert received == [] and channel._closed
        denials = [row for row in border.audit.recent() if row['outcome'] == 'denied']
        assert len(denials) == 1 and denials[0]['decision'] == 'current_authority_refused'


def load_entrypoint(name, relative):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(name, root/relative)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
@pytest.mark.parametrize('launcher', ['lightweight', 'daemon'])
async def test_both_launchers_dial_registered_identity(tmp_path, material, monkeypatch, launcher):
    async with pair(tmp_path, material) as (border, member, entry):
        registry = Registry(tmp_path/'transport/registry.json', 'member')
        registry.replace({'schemaVersion':1, 'installationId':'member', 'revision':1, 'entries':[entry]}, expected_revision=0)
        monkeypatch.setenv('N2N_BORDER_REGISTRY_ID', 'members')
        from bgp.federation import endpoint_registry
        monkeypatch.setattr(endpoint_registry, 'configured', lambda **kw: registry)
        if launcher == 'lightweight':
            module = load_entrypoint('member168', 'scripts/in2n-member.py'); loop = module._dial_loop
        else:
            module = load_entrypoint('daemon168', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py'); loop = module._in2n_member_dialer
        real_dial = member.dial_border
        calls = []
        async def once(host, port, **kw):
            calls.append((host, port, kw['registration']['tls_server_name']))
            await real_dial(host, port, **kw)
            raise asyncio.CancelledError
        member.dial_border = once
        with pytest.raises(asyncio.CancelledError):
            await loop(member, 'ignored.example.test', 1, border.risk.issue_token()['token'])
        assert calls == [(entry['routing_host'],entry['routing_port'],'border.example.test')]
        assert member.border_channel.trusted


@pytest.mark.asyncio
async def test_strict_member_daemon_opens_no_listener(tmp_path, monkeypatch):
    module = load_entrypoint('daemon_no_listen168', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py')
    monkeypatch.setenv('N2N_ENDPOINT_REGISTRY', str(tmp_path/'reviewed.json'))
    monkeypatch.setenv('N2N_ROLE', 'member')
    from bgp.federation import service
    class MemberFixture:
        def __init__(self, **kw): self.manager=SimpleNamespace(close=lambda:None); self.border_channel=None
        async def start_runtime(self): pass
        async def stop_runtime(self): pass
    monkeypatch.setattr(service, 'FederationService', MemberFixture)
    async def no_listener(*args, **kwargs): raise AssertionError('member opened a listener')
    monkeypatch.setattr(asyncio, 'start_server', no_listener)
    async def started(fed): raise asyncio.CancelledError
    monkeypatch.setattr(module, '_start_in2n', started)
    with pytest.raises(asyncio.CancelledError): await module.main()
    assert module._speaker is None


@pytest.mark.asyncio
async def test_member_refuses_member_admission(tmp_path, material):
    async with pair(tmp_path, material) as (border, member, entry):
        closed = []
        writer = SimpleNamespace(close=lambda:closed.append(True))
        with pytest.raises(ValueError, match='members cannot accept'):
            await member.accept_internal(None, writer, registration=entry)
        assert closed and not member.member_channels


@pytest.mark.asyncio
async def test_address_relocation_preserves_keys_without_work_replay(tmp_path, material, monkeypatch):
    async with pair(tmp_path, material) as (border, member, entry):
        registry = Registry(tmp_path/'transport/registry.json', 'member')
        registry.replace({'schemaVersion':1, 'installationId':'member', 'revision':1, 'entries':[entry]}, expected_revision=0)
        from bgp.federation import endpoint_registry, internal_security
        monkeypatch.setattr(endpoint_registry, 'configured', lambda **kw: registry)
        monkeypatch.setenv('N2N_BORDER_REGISTRY_ID', 'members')
        await dial(member, entry, border.risk.issue_token()['token'])
        fingerprint = border.risk.get_member('example/test')['key_fingerprint']
        await member.border_channel.close(); await asyncio.sleep(.02)
        border._test_forwarder.close(); await border._test_forwarder.wait_closed()
        # Old address is unavailable. No automatic old/new-profile fallback.
        with pytest.raises(ConnectionError): await dial(member, entry)
        port = border._in2n_server.sockets[0].getsockname()[1]
        registry.update_address('members', '127.0.0.1', port, 'ra_fixture_moved', expected_revision=1)
        host, port, options = internal_security.dial_options(member, 'ignored', 1)
        result = await member.dial_border(host, port, **options)
        assert result['trusted']
        assert border.risk.get_member('example/test')['key_fingerprint'] == fingerprint
        assert member.manager._conn.execute('SELECT COUNT(*) FROM delegated_task').fetchone()[0] == 0
        assert border.manager._conn.execute('SELECT COUNT(*) FROM delegated_task').fetchone()[0] == 0


@asynccontextmanager
async def external_pair(tmp_path, *, direct=False):
    services, entries, registries, servers, writers = [], [], [], [], []
    for index in range(2):
        home = tmp_path / ('external-' + str(index))
        svc = _service(home, 65001 + index, '1.2.3.' + str(index + 1), 'External')
        home.chmod(0o700)
        services.append(svc)
        svc.risk.set_role('border', risk_name='external' + str(index), enabled_stacks='in2n,en2n')
        ca, key = certs.create_risk_ca('external' + str(index))
        name = 'border' + str(index) + '.example.test'
        certificate, private = certs.issue_cert(ca, key, name, san=name)
        for label, value in [('ca',ca), ('cert',certificate), ('key',private)]:
            path = home/(label+'.pem'); path.write_text(value); path.chmod(0o600)
        entry = dict(id='external', direction='listen', service='en2n', profile='en2n-tls13-v1',
                     routing_host='127.0.0.1', routing_port=24001+index, reservation_id='ra_fixture_'+str(index),
                     tls_server_name=name, ca_file=str(home/'ca.pem'), application_identity=svc.local_identity,
                     application_trust=certs.key_fingerprint(certificate), bind_host='127.0.0.1', bind_port=25001+index,
                     cert_file=str(home/'cert.pem'), key_file=str(home/'key.pem'))
        if direct:
            entry.pop('reservation_id')
            entry.update(transport='direct_tcp', address_ref='direct-fixture-'+str(index))
        entries.append(entry)
        registry = Registry(home/'transport/registry.json', str(index))
        registries.append(registry)
        svc.transport_registry = lambda registry=registry: registry
        async def accept(reader, writer, svc=svc, entry=entry):
            writers.append(writer)
            await svc.accept_public_ncfed(reader, writer, entry, 1)
        server = await asyncio.start_server(accept, '127.0.0.1', 0)
        entry['bind_port'] = entry['routing_port'] = server.sockets[0].getsockname()[1]
        servers.append(server)
    for index in range(2):
        remote = {k:v for k,v in entries[1-index].items() if k not in ('bind_host','bind_port','cert_file','key_file')}
        remote.update(id='peer', direction='dial')
        registries[index].replace({'schemaVersion':2 if direct else 1, 'installationId':str(index), 'revision':1,
                                   'entries':[entries[index],remote]}, expected_revision=0)
        services[index].manager.local_consent(services[1-index].local_as, services[1-index].router_id)
    try: yield services, entries, registries
    finally:
        for svc in services:
            for ch in list(svc.channels.values()): await ch.close()
        for writer in writers: writer.close()
        for server in servers: server.close()
        for server in servers: await server.wait_closed()
        for svc in services: svc.manager.close()


@pytest.mark.asyncio
async def test_public_ncfed_tls_pinned_identity_and_consent(tmp_path):
    async with external_pair(tmp_path) as (services, entries, registries):
        a, b = services
        # Caller-supplied stale address is ignored in favor of approved registry.
        await a.open_channel(b.local_as, b.router_id, '192.0.2.1', 1)
        assert b.local_identity in a.channels
        assert a.local_identity in b.channels
        assert a.manager.is_federated(b.local_identity) and b.manager.is_federated(a.local_identity)
        assert a.channels[b.local_identity].authenticated
        assert b.channels[a.local_identity].attestation == 'possession'
        assert not a.member_channels and not b.member_channels
        from bgp.federation.endpoint_registry import transport_kind
        expected = 'other' if transport_kind(entries[0]) == 'direct_tcp' else 'ngrok'
        assert a.manager.get_peer(b.local_identity)['transport'] == expected
        assert b.manager.get_peer(a.local_identity)['transport'] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['pin', 'name', 'ca', 'consent'])
async def test_external_strict_trust_refusal(tmp_path, failure):
    async with external_pair(tmp_path) as (services, entries, registries):
        a, b = services
        if failure == 'consent':
            b.manager.sever(a.local_identity)
        else:
            registry = registries[0]
            document = registry.load()
            peer = document['entries'][1]
            if failure == 'pin': peer['application_trust'] = 'f'*64
            if failure == 'name': peer['tls_server_name'] = 'wrong.example.test'
            if failure == 'ca': peer['ca_file'] = entries[0]['ca_file']
            registry.replace(document, expected_revision=1)
        await a.open_channel(b.local_as, b.router_id, entries[1]['routing_host'], entries[1]['routing_port'])
        await asyncio.sleep(.02)
        assert not a.channels and not b.channels


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [b'\xff'*19, b'NCTUN'+b'x'*16, b'GET / HTTP/1.1\r\n\r\n', b'PROXY TCP4 x y 1 2\r\n'])
async def test_public_listener_refuses_other_protocols_without_peer_mutation(tmp_path, payload):
    async with external_pair(tmp_path) as (services, entries, registries):
        service = services[1]
        before = service.manager.list_peers()
        reader, writer = await asyncio.open_connection('127.0.0.1', entries[1]['routing_port'])
        writer.write(payload); await writer.drain()
        try:
            assert await asyncio.wait_for(reader.read(), 2) == b''
        except ConnectionResetError:
            pass  # Refusal can be TCP reset when unread non-NCFED bytes remain.
        writer.close()
        try: await writer.wait_closed()
        except ConnectionResetError: pass
        assert service.manager.list_peers() == before and not service.channels
