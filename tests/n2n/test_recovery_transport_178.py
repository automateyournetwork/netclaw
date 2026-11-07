"""Actual isolated child service processes and strict TLS; no cloud/provider calls."""
import asyncio
import multiprocessing
import time

import pytest

from bgp.federation import exporter_tls, endpoint_registry, internal_security
from bgp.federation.endpoint_registry import Registry
from test_exporter_tls_168 import material
from test_internal_transport import _service


def border_process(base, material, port, ready):
    async def run():
        border = _service(base, 65001, '192.0.2.1', 'R07 test Border')
        border.risk.set_role('border', risk_name='example', enabled_stacks='in2n')
        anchor, _ = border.risk.ensure_risk_ca()
        border.risk.hub_credential()
        registration = dict(id='members', direction='listen', service='in2n',
            profile='in2n-tls-exporter-v1', transport='direct_tcp', address_ref='isolated-process',
            routing_host='127.0.0.1', routing_port=port or 1, tls_server_name='border.example.test',
            ca_file=material['ca'], application_identity='example/border', application_trust=anchor,
            bind_host='127.0.0.1', bind_port=port or 1, cert_file=material['cert'], key_file=material['key'])
        async def accept(reader, writer):
            await border.accept_internal(reader, writer, registration=registration, registry_revision=1)
        server = await exporter_tls.start_server(accept, '127.0.0.1', port,
            cert_file=material['cert'], key_file=material['key'])
        actual = server.sockets[0].getsockname()[1]
        registration.update(routing_port=actual, bind_port=actual)
        ready.send(dict(port=actual, registration=registration,
                        token=border.risk.issue_token()['token'] if not border.risk.list_members() else None))
        await asyncio.Event().wait()
    asyncio.run(run())


async def launch_border(context, base, material, port=0):
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=border_process, args=(str(base), material, port, sender))
    process.start()
    sender.close()
    try:
        if not await asyncio.to_thread(receiver.poll, 10):
            raise AssertionError('isolated Border did not become ready')
        return process, receiver.recv()
    except BaseException:
        process.terminate()
        await asyncio.to_thread(process.join, 5)
        raise
    finally:
        receiver.close()


async def stop_process(process):
    process.terminate()
    await asyncio.to_thread(process.join, 5)
    assert not process.is_alive()


async def wait_closed(channel):
    for _ in range(200):
        if channel._closed:
            return
        await asyncio.sleep(.01)
    raise AssertionError('channel did not detect stopped service')


@pytest.mark.asyncio
async def test_actual_border_process_restart_and_registry_replacement(tmp_path, material, monkeypatch, record_property):
    context = multiprocessing.get_context('spawn')
    process, ready = await launch_border(context, tmp_path/'border', material)
    member = _service(tmp_path/'member', 65001, '192.0.2.1', 'R07 test member')
    member.risk.set_role('member', risk_name='example', self_member_id='example/test')
    entry = {k:v for k,v in ready['registration'].items() if k not in ('bind_host','bind_port','cert_file','key_file')}
    entry['direction'] = 'dial'
    registry = Registry(tmp_path/'owned/registry.json', 'isolated-member')
    registry.replace({'schemaVersion':2,'installationId':'isolated-member','revision':1,'entries':[entry]}, expected_revision=0)
    monkeypatch.setattr(endpoint_registry, 'configured', lambda **kw: registry)
    monkeypatch.setenv('N2N_BORDER_REGISTRY_ID', 'members')
    async def dial(token=''):
        host, port, options = internal_security.dial_options(member, 'ignored', 1)
        return await member.dial_border(host, port, enrollment_token=token, **options)
    try:
        enrolled = await dial(ready['token'])
        cert = member.risk.self_cert_pem()
        anchor = member.risk.risk_anchor()
        old_channel = member.border_channel
        start = time.monotonic()
        await stop_process(process)
        await wait_closed(old_channel)
        record_property('service_loss_detection_seconds', time.monotonic()-start)
        with pytest.raises(ConnectionError):
            await dial()
        observation = member.transport_observations['members']
        assert observation['failure_reason'] == 'connection_unavailable'
        assert observation['tls_verified'] is False
        start = time.monotonic()
        process, restarted = await launch_border(context, tmp_path/'border', material, ready['port'])
        assert restarted['token'] is None
        assert (await dial())['trusted']
        record_property('same_address_process_restore_seconds', time.monotonic()-start)
        assert member.risk.self_cert_pem() == cert and member.risk.risk_anchor() == anchor
        assert member.risk.protected_enrollment()['enrollment_generation'] == enrolled['enrollment_generation']
        await stop_process(process)
        await wait_closed(member.border_channel)
        process, replacement = await launch_border(context, tmp_path/'border', material)
        start = time.monotonic()
        registry.update_address('members', '127.0.0.1', replacement['port'], 'isolated-replacement', expected_revision=1)
        assert (await dial())['trusted']
        record_property('registry_replacement_recovery_seconds', time.monotonic()-start)
        assert registry.load()['revision'] == 2
        assert replacement['registration']['application_trust'] == anchor
        assert member.risk.self_cert_pem() == cert
        assert member.risk.protected_enrollment()['enrollment_generation'] == enrolled['enrollment_generation']
        assert member.manager._conn.execute('SELECT COUNT(*) FROM delegated_task').fetchone()[0] == 0
        with pytest.raises(ValueError, match='revision'):
            registry.update_address('members', '127.0.0.1', ready['port'], 'stale', expected_revision=1)
    finally:
        if member.border_channel:
            await member.border_channel.close()
        if process.is_alive():
            await stop_process(process)
        member.manager.close()


@pytest.mark.asyncio
async def test_failed_tls_name_reports_bounded_cause_without_fallback(tmp_path, material):
    from test_ngrok_transport_168 import pair, dial
    async with pair(tmp_path, material, direct=True) as (border, member, entry):
        token = border.risk.issue_token()['token']
        with pytest.raises(Exception):
            await dial(member, dict(entry, tls_server_name='wrong.example.test'), token)
        observation = member.transport_observations['members']
        assert observation['failure_reason'] == 'tls_identity_refused'
        assert observation['tls_verified'] is False
        assert not border.member_channels and border.risk.get_member('example/test') is None
        assert (await dial(member, entry, token))['pinned']
        assert 'failure_reason' not in member.transport_observations['members']
