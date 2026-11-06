import asyncio
import pytest
from test_ngrok_transport_168 import pair, dial
from test_exporter_tls_168 import material
from bgp.federation.channel import RpcError

@pytest.mark.asyncio
async def test_revocation_while_inbound_handler_waits(tmp_path,material):
    async with pair(tmp_path,material,direct=True) as (border,member,entry):
        await dial(member,entry,border.risk.issue_token()["token"])
        entered,release=asyncio.Event(),asyncio.Event()
        async def private_read(channel,params):
            entered.set()
            await release.wait()
            return {"private_result":"must-not-return-after-revocation"}
        border.member_channels["example/test"].register("test/private-read",private_read)
        pending=asyncio.create_task(member.border_channel.call("test/private-read",{},timeout=2))
        await entered.wait()
        border.risk.remove_member("example/test")
        release.set()
        with pytest.raises((RpcError,ConnectionError)):
            await pending

@pytest.mark.asyncio
async def test_revocation_while_outbound_result_waits(tmp_path,material):
    async with pair(tmp_path,material,direct=True) as (border,member,entry):
        await dial(member,entry,border.risk.issue_token()["token"])
        entered,release=asyncio.Event(),asyncio.Event()
        async def worker(channel,params):
            entered.set()
            await release.wait()
            return {"result":"revoked-authority-result"}
        member.border_channel.register("test/work",worker)
        pending=asyncio.create_task(border.member_channels["example/test"].call("test/work",{},timeout=2))
        await entered.wait()
        border.risk.remove_member("example/test")
        release.set()
        with pytest.raises((RpcError,ConnectionError)):
            await pending


@pytest.mark.asyncio
async def test_removal_commits_before_async_close_and_refuses_reconnect(tmp_path, material, monkeypatch):
    from test_ngrok_transport_168 import load_entrypoint
    daemon = load_entrypoint('recovery_remove178', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py')
    async with pair(tmp_path, material, direct=True) as (border, member, entry):
        await dial(member, entry, border.risk.issue_token()['token'])
        monkeypatch.setattr(daemon, '_federation', border)
        channel = border.member_channels['example/test']
        close = channel.close
        observed = []
        async def racing_close():
            observed.append(border.risk.get_member('example/test')['state'])
            with pytest.raises((RpcError, ConnectionError)):
                await dial(member, entry)
            await close()
        channel.close = racing_close
        status, result = await daemon.handle_n2n('POST', '/n2n/members/remove', {'member_id':'example/test'})
        assert status == 200 and result['removed']
        assert observed == ['removed']
        assert 'example/test' not in border.member_channels


@pytest.mark.asyncio
async def test_real_certificate_expiry_refuses_open_channel_and_reconnect(tmp_path, material, record_property):
    import datetime
    import time
    from bgp.federation import certs
    async with pair(tmp_path, material, direct=True) as (border, member, entry):
        member.risk.ensure_self_identity()
        cert, _ = certs.create_self_signed('example/test', days=3/86400,
            key_pem=(member.risk.keys_dir/'self.key').read_text())
        (member.risk.keys_dir/'self.crt').write_text(cert)
        token = border.risk.issue_token()['token']
        await dial(member, entry, token)
        channel = border.member_channels['example/test']
        generation = border.risk.get_member('example/test')['enrollment_generation']
        remaining = (certs.cert_not_after(cert)-datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        await asyncio.sleep(max(0, remaining)+.02)
        started = time.monotonic()
        with pytest.raises((RpcError, ConnectionError)):
            await channel.call('in2n/self-status', {}, timeout=2)
        record_property('expiry_refusal_seconds', time.monotonic()-started)
        assert channel._closed
        with pytest.raises((ValueError, RpcError, ConnectionError)):
            await dial(member, entry)
        assert border.risk.get_member('example/test')['enrollment_generation'] == generation
        assert border.manager._conn.execute('SELECT COUNT(*) FROM delegated_task').fetchone()[0] == 0


def test_time_valid_rejects_malformed_future_and_boundary():
    import datetime
    from cryptography import x509
    from bgp.federation import certs
    cert, _ = certs.create_self_signed('time-test')
    parsed = x509.load_pem_x509_certificate(cert.encode())
    assert certs.time_valid(cert, parsed.not_valid_before_utc)
    assert not certs.time_valid(cert, parsed.not_valid_before_utc-datetime.timedelta(microseconds=1))
    assert not certs.time_valid(cert, parsed.not_valid_after_utc)
    assert not certs.time_valid('malformed') and not certs.time_valid(None)


@pytest.mark.asyncio
async def test_member_refuses_changed_border_anchor_on_open_channel(tmp_path, material):
    from bgp.federation import certs
    async with pair(tmp_path, material, direct=True) as (border, member, entry):
        await dial(member, entry, border.risk.issue_token()['token'])
        channel = member.border_channel
        member.risk.store_risk_anchor(certs.create_risk_ca('replacement')[0])
        with pytest.raises((RpcError, ConnectionError)):
            await channel.call('n2n/inventory', {}, timeout=2)
        assert channel._closed


@pytest.mark.asyncio
@pytest.mark.parametrize('outcome', ['result', 'rpc_error', 'error'])
async def test_edge_revoked_during_handler_delivers_no_private_result(tmp_path, outcome):
    from test_edge_enrollment import _border, _serve, _enroll
    border = _border(tmp_path/'edge-border')
    server, port = await _serve(border)
    phone = None
    entered, release = asyncio.Event(), asyncio.Event()
    try:
        _, phone, _, _ = await _enroll(border, port)
        channel = border.edge_channels['risk/phone1']
        async def waiting_status(channel, params):
            entered.set()
            await release.wait()
            if outcome == 'rpc_error':
                from bgp.federation.edge import RpcError as EdgeError
                raise EdgeError(-32000, 'private message', data={'private':'data'})
            if outcome == 'error':
                raise ValueError('private exception message')
            return {'private_result':'must-not-deliver'}
        channel.register('n2n/tasks/status', waiting_status)
        pending = asyncio.create_task(phone.call('n2n/tasks/status', {}, timeout=.3))
        await entered.wait()
        border.risk.remove_member('risk/phone1')
        release.set()
        with pytest.raises((TimeoutError, ConnectionError)):
            await pending
        assert channel._closed and 'risk/phone1' not in border.edge_channels
    finally:
        release.set()
        if phone:
            await phone.ws.close()
            await phone.close()
        server.close()
        await server.wait_closed()
        border.manager.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['call', 'notify'])
async def test_edge_revocation_stops_outbound_traffic(tmp_path, operation):
    from test_edge_enrollment import _border, _serve, _enroll
    from bgp.federation.edge import RpcError as EdgeError
    border = _border(tmp_path/'edge-border')
    server, port = await _serve(border)
    phone = None
    try:
        _, phone, _, _ = await _enroll(border, port)
        channel = border.edge_channels['risk/phone1']
        seen = []
        phone.handlers['n2n/edge/self_status'] = lambda p: seen.append(p) or {}
        border.risk.remove_member('risk/phone1')
        with pytest.raises(EdgeError):
            await getattr(channel, operation)('n2n/edge/self_status', {})
        assert seen == [] and channel._closed
    finally:
        if phone:
            await phone.ws.close()
            await phone.close()
        server.close()
        await server.wait_closed()
        border.manager.close()


@pytest.mark.asyncio
async def test_internal_authority_lookup_failure_closes_without_delivery(tmp_path, material):
    async with pair(tmp_path, material, direct=True) as (border, member, entry):
        await dial(member, entry, border.risk.issue_token()['token'])
        channel = border.member_channels['example/test']
        def unavailable():
            raise RuntimeError('private database details')
        channel.authority_current = unavailable
        with pytest.raises((RpcError, ConnectionError)):
            await channel.call('in2n/self-status', {}, timeout=2)
        assert channel._closed


@pytest.mark.asyncio
async def test_internal_revocation_suppresses_private_rpc_error(tmp_path, material):
    async with pair(tmp_path, material, direct=True) as (border, member, entry):
        await dial(member, entry, border.risk.issue_token()['token'])
        entered, release = asyncio.Event(), asyncio.Event()
        async def failure(channel, params):
            entered.set()
            await release.wait()
            raise RpcError(-32000, 'private error after revocation')
        border.member_channels['example/test'].register('test/failure', failure)
        pending = asyncio.create_task(member.border_channel.call('test/failure', {}, timeout=2))
        await entered.wait()
        border.risk.remove_member('example/test')
        release.set()
        with pytest.raises((RpcError, ConnectionError)) as error:
            await pending
        assert 'private error' not in str(error.value)


@pytest.mark.asyncio
async def test_protected_reconnect_requires_strict_transport_before_authority_binding(tmp_path):
    from test_internal_transport import _service
    from bgp.federation.protected_contract import ProtectedError
    from bgp.federation.runtime import Runtime, write_private
    border = _service(tmp_path/'border', 65001, '192.0.2.1', 'Border')
    member = _service(tmp_path/'member', 65001, '192.0.2.2', 'Member')
    member.runtime = Runtime('openclaw', tmp_path/'member', tmp_path/'member/config.json', None)
    border.risk.set_role('border', risk_name='risk', enabled_stacks='in2n')
    member.risk.set_role('member', risk_name='risk', self_member_id='risk/member')
    server = await asyncio.start_server(border.accept_internal, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    try:
        await member.dial_border('127.0.0.1', port, enrollment_token=border.risk.issue_token()['token'])
        await member.border_channel.close()
        member.protected_enabled = True
        write_private(member.runtime.state/'protected-profile.json', {'border': {}})
        with pytest.raises(ProtectedError, match='protected_border_binding_refused'):
            await member.dial_border('127.0.0.1', port)
        assert member.border_channel is None or member.border_channel._closed
    finally:
        for channel in list(border.member_channels.values()):
            await channel.close()
        if member.border_channel:
            await member.border_channel.close()
        server.close()
        await server.wait_closed()
        border.manager.close()
        member.manager.close()
