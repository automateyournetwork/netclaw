"""Spec175 native issuer/authority tests; isolated synthetic identities, no live effects."""
import asyncio
from dataclasses import replace
from pathlib import Path
import json
import time
from types import SimpleNamespace
import uuid

import pytest
from websockets.datastructures import Headers
from bgp.federation import certs
from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService
from bgp.federation.mobile_enrollment import MobileEnrollment, MOBILE_METHODS, protected_ws_request_allowed
from bgp.federation.protected_contract import ProtectedError
from bgp.federation.protected_device import DeviceAuthority
from bgp.federation.protected_access import OpenLabAccess
from bgp.federation.edge import RpcError
from protected_support_171 import OperationPair

INSTALLATION = '00000000-0000-4000-8000-000000000175'


def service(tmp_path, monkeypatch, *, protected=False):
    home = tmp_path / 'home'; (home / 'netclaw-hud').mkdir(parents=True, mode=0o700)
    (home / 'netclaw-hud/installation.json').write_text(json.dumps({'schemaVersion': 1, 'installationId': INSTALLATION}))
    (home / 'netclaw-hud/installation.json').chmod(0o600)
    monkeypatch.setenv('OPENCLAW_HOME', str(home))
    monkeypatch.setenv('OPENCLAW_STATE_DIR', str(home))
    monkeypatch.setenv('NETCLAW_RUNTIME', 'openclaw')
    monkeypatch.setenv('N2N_PROTECTED_OPERATIONS', '1' if protected else '0')
    fed = FederationService(local_as=65001, router_id='192.0.2.1', manager=FederationManager(base_dir=str(tmp_path / 'n2n')))
    fed.risk.set_role('border', risk_name='test', enabled_stacks='in2n')
    fed.edge_status = {'state': 'listening', 'domain': 'localhost', 'port': 8443, 'host': '127.0.0.1'}
    if protected:
        fed.edge_status.update(path='/mobile/ws', public_origin='https://mobile.example')
        fed.protected_operations = object()
    payloads = []
    original = MobileEnrollment._matrix
    fed.mobile_enrollment.matrix_factory = lambda payload: (payloads.append(payload) or original(payload))
    return fed, payloads


def issue(fed, replace_nonce=None, nonce=None):
    return fed.mobile_enrollment.issue({'installation_id': fed.runtime.installation,
        'client_nonce': nonce or str(uuid.uuid4()), 'replace_client_nonce': replace_nonce})


def status(fed, nonce):
    return fed.mobile_enrollment.status({'installation_id': fed.runtime.installation, 'client_nonce': nonce})


def test_issue_is_finite_single_outstanding_hash_only_and_never_rediscloses(tmp_path, monkeypatch):
    fed, payloads = service(tmp_path, monkeypatch)
    first = issue(fed)
    assert first['status'] == 'issued' and 21 <= len(first['qr_matrix']) <= 177
    assert first['expires_ms'] <= int(time.time() * 1000) + 120000
    assert payloads[0]['installation_id'] == INSTALLATION and payloads[0]['ws_path'] == '/'
    assert status(fed, first['client_nonce']) == issue(fed, nonce=first['client_nonce'])
    with pytest.raises(ProtectedError, match='mobile_offer_outstanding'):
        issue(fed)
    second = issue(fed, first['client_nonce'])
    assert status(fed, first['client_nonce'])['status'] == 'replaced'
    assert status(fed, second['client_nonce'])['status'] == 'issued'
    stored = Path(fed.manager.db_path).read_bytes()
    for payload in payloads:
        assert payload['enrollment_token'].encode() not in stored
    assert 'qr_matrix' not in json.dumps(status(fed, second['client_nonce']))
    fed.manager.close()


def test_scoped_tokens_refuse_agent_wrong_installation_expired_and_replaced(tmp_path, monkeypatch):
    fed, payloads = service(tmp_path, monkeypatch)
    one = issue(fed); token = payloads[0]['enrollment_token']
    cert, _ = certs.create_self_signed('test/phone')
    for args in ({}, {'node_type': 'edge', 'transport_binding': 'edge-ws'},
                 {'node_type': 'edge', 'transport_binding': 'edge-ws', 'installation_id': str(uuid.uuid4())}):
        with pytest.raises(ValueError, match='ENROLL_TOKEN_INVALID'):
            fed.risk.consume_token(token, 'test/phone', cert, **args)
    issue(fed, one['client_nonce'])
    with pytest.raises(ValueError, match='ENROLL_TOKEN_INVALID'):
        fed.risk.consume_token(token, 'test/phone', cert, node_type='edge', transport_binding='edge-ws', installation_id=INSTALLATION)
    token = payloads[-1]['enrollment_token']
    fed.manager._conn.execute('UPDATE mobile_enrollment_offer SET expires_ms=0'); fed.manager._conn.commit()
    with pytest.raises(ValueError, match='ENROLL_TOKEN_INVALID'):
        fed.risk.consume_token(token, 'test/phone', cert, node_type='edge', transport_binding='edge-ws', installation_id=INSTALLATION)
    assert fed.risk.get_member('test/phone') is None
    fed.manager.close()


def test_consumption_is_one_use_and_status_recovery_preserves_same_member(tmp_path, monkeypatch):
    fed, payloads = service(tmp_path, monkeypatch)
    first = issue(fed); token = payloads[0]['enrollment_token']
    cert, _ = certs.create_self_signed('test/phone')
    result = fed.risk.consume_token(token, 'test/phone', cert, node_type='edge', transport_binding='edge-ws', installation_id=INSTALLATION, scope=[])
    assert result['installation_id'] == INSTALLATION
    expected = dict(status(fed, first['client_nonce']))
    assert expected['status'] == 'consumed' and expected['member_id'] == 'test/phone'
    assert issue(fed, nonce=first['client_nonce']) == expected
    with pytest.raises(ValueError, match='ENROLL_TOKEN_INVALID'):
        fed.risk.consume_token(token, 'test/phone2', cert, node_type='edge', transport_binding='edge-ws', installation_id=INSTALLATION)
    second = issue(fed)
    with pytest.raises(ValueError, match='MEMBER_ID_TAKEN'):
        fed.risk.consume_token(payloads[-1]['enrollment_token'], 'test/phone', cert, node_type='edge', transport_binding='edge-ws', installation_id=INSTALLATION)
    assert fed.risk.get_member('test/phone')['enrollment_generation'] == result['enrollment_generation']
    fed.manager.close()


def test_readiness_fails_closed_without_listener_and_wrong_installation(tmp_path, monkeypatch):
    fed, _ = service(tmp_path, monkeypatch)
    fed.edge_status = {'state': 'no_port'}
    value = fed.mobile_enrollment.info({'installation_id': INSTALLATION})
    assert value['available'] is False and value['endpoint'] is None
    with pytest.raises(ProtectedError): issue(fed)
    with pytest.raises(ProtectedError, match='installation_changed'):
        fed.mobile_enrollment.info({'installation_id': str(uuid.uuid4())})
    assert not fed.manager._conn.execute('SELECT * FROM mobile_enrollment_offer').fetchall()
    fed.manager.close()


@pytest.mark.parametrize('path,host,origin,remote,allowed', [
    ('/mobile/ws', ['mobile.example'], [], '127.0.0.1', True),
    ('/mobile/ws', ['mobile.example'], ['https://mobile.example'], '127.0.0.1', True),
    ('/', ['mobile.example'], [], '127.0.0.1', False),
    ('/mobile/ws?x=1', ['mobile.example'], [], '127.0.0.1', False),
    ('/mobile/ws', ['evil.example'], [], '127.0.0.1', False),
    ('/mobile/ws', ['mobile.example', 'evil.example'], [], '127.0.0.1', False),
    ('/mobile/ws', ['mobile.example'], ['https://evil.example'], '127.0.0.1', False),
    ('/mobile/ws', ['mobile.example'], [], '192.0.2.1', False),
])
def test_proxy_ingress_exact_path_host_origin_and_loopback(path, host, origin, remote, allowed):
    headers = Headers([('Host', v) for v in host] + [('Origin', v) for v in origin])
    socket = SimpleNamespace(remote_address=(remote, 50000), request=SimpleNamespace(path=path, headers=headers))
    assert protected_ws_request_allowed(socket, 'https://mobile.example') is allowed


def test_device_operation_full_signed_flow_recovery_isolation_and_revocation(tmp_path, monkeypatch):
    async def run():
        fed, payloads = service(tmp_path / 'phone', monkeypatch, protected=True)
        pair = OperationPair(tmp_path / 'execution')
        fed.runtime = replace(fed.runtime, installation=pair.border.identity['installation_id'])
        fed.protected_operations = pair.border
        pair.border.owner = OpenLabAccess(fed.runtime.installation)
        def enroll(label):
            record = issue(fed)
            cert, _ = certs.create_self_signed(label)
            row = fed.risk.consume_token(payloads[-1]['enrollment_token'], label, cert,
                node_type='edge', transport_binding='edge-ws', installation_id=fed.runtime.installation, scope=[])
            ch = SimpleNamespace(member_id=label, trusted=True, _closed=False,
                owner_generation=row['enroll_fingerprint'], enrollment_generation=row['enrollment_generation'])
            fed.edge_channels[label] = ch
            return ch
        channel = enroll('test/phone1'); other = enroll('test/phone2')
        principal = DeviceAuthority(fed, channel).principal()
        assert principal['issuer'] == 'device-key' and principal != DeviceAuthority(fed, other).principal()
        async def call(action, ch=channel, **params):
            return await fed._edge_border_handlers['n2n/edge/operations/' + action](ch, dict(params, installation_id=fed.runtime.installation))
        cat = await call('catalog')
        candidate = {'client_nonce': 'same-nonce', 'catalog_revision': cat['revision'],
            'member_id': cat['members'][0]['member']['member_id'],
            'model_profile_id': cat['members'][0]['model_profiles'][0]['profile_id'],
            'tool': cat['members'][0]['tools'][0]['tool'], 'arguments': cat['members'][0]['tools'][0]['arguments']}
        prepared = await call('prepare', **candidate)
        assert prepared['review']['principal'] == principal and 'revoke' not in prepared['allowed_actions']
        for action, args in [('status', {'operation_id': prepared['operation_id']}),
                             ('status', {'client_nonce': 'same-nonce'}),
                             ('reconcile', {'operation_id': prepared['operation_id']})]:
            with pytest.raises(RpcError): await call(action, ch=other, **args)
        other_review = await call('prepare', ch=other, **candidate)
        assert other_review['operation_id'] != prepared['operation_id']
        await call('decision', operation_id=prepared['operation_id'], revision=prepared['revision'], review_digest=prepared['review_digest'], decision='approve')
        await pair.drain()
        result = await call('reconcile', operation_id=prepared['operation_id'])
        assert result['state'] == 'completed' and result['result']['durable_ack']
        assert result['result']['evidence']['principal'] == principal
        for _ in range(2):
            assert (await call('status', operation_id=prepared['operation_id']))['result'] == result['result']
        assert len(pair.effects) == pair.executor_calls == 1
        # Native channel authority is checked again; stale references cannot read.
        fed.edge_channels[channel.member_id] = SimpleNamespace()
        with pytest.raises(RpcError): await call('status', operation_id=prepared['operation_id'])
        assert len(pair.effects) == 1
        fed.manager.close()
    asyncio.run(run())


def test_actual_protected_listener_enrolls_then_same_key_hello_and_refuses_legacy(tmp_path, monkeypatch):
    import importlib.util
    import socket
    import websockets
    from test_edge_enrollment import _FakePhone
    from bgp.federation.risk import RiskManager
    daemon_path = Path(__file__).resolve().parents[2] / 'mcp-servers/protocol-mcp/bgp-daemon-v2.py'
    spec = importlib.util.spec_from_file_location('mobile_daemon_175', daemon_path)
    daemon = importlib.util.module_from_spec(spec); spec.loader.exec_module(daemon)
    async def run():
        fed, payloads = service(tmp_path, monkeypatch, protected=True)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
        monkeypatch.setenv('N2N_EDGE_WS_PORT', str(port))
        monkeypatch.setenv('NETCLAW_MOBILE_ORIGIN', 'https://mobile.example')
        await daemon._start_edge(fed)
        assert fed.edge_status['state'] == 'listening' and fed.edge_status['host'] == '127.0.0.1'
        offer = issue(fed)
        cert, key = certs.create_self_signed('test/native-phone')
        binding = None
        for action in ('in2n/enroll', 'in2n/hello'):
            async with websockets.connect('ws://mobile.example/mobile/ws', host='127.0.0.1', port=port) as ws:
                challenge = asyncio.get_running_loop().create_future()
                phone = _FakePhone(ws, handlers={'n2n/edge/challenge': lambda value: challenge.set_result(bytes.fromhex(value['nonce'])) or {}})
                nonce = await asyncio.wait_for(challenge, 2)
                params = {'member_id': 'test/native-phone', 'signature': RiskManager.sign_challenge(key, nonce).hex(), 'installation_id': INSTALLATION}
                params.update({'token': payloads[0]['enrollment_token'], 'cert_pem': cert} if action == 'in2n/enroll' else {'key_fingerprint': RiskManager.fingerprint_of(cert)})
                response = await phone.call(action, params)
                descriptor = response['border']['capabilities']['protected_operations']
                assert descriptor['methods'] == list(MOBILE_METHODS) and descriptor['origin'] == 'https://mobile.example'
                if binding is None: binding = descriptor['principal']
                else: assert descriptor['principal'] == binding
                for method in ('n2n/edge/ask', 'n2n/tasks/status', 'n2n/edge/register_push', 'n2n/edge/approval_resolve', 'n2n/edge/operations/revoke'):
                    with pytest.raises(RuntimeError): await phone.call(method, {})
                await phone.close()
        assert status(fed, offer['client_nonce'])['status'] == 'consumed'
        assert len(fed.risk.list_members()) == 1
        # Wrong Host and wrong path close before issuing a challenge.
        for url in (f'ws://127.0.0.1:{port}/mobile/ws', 'ws://mobile.example/'):
            async with websockets.connect(url, host='127.0.0.1', port=port) as ws:
                with pytest.raises(websockets.exceptions.ConnectionClosed): await ws.recv()
        fed._edge_server.close(); await fed._edge_server.wait_closed()
        fed.manager.close()
    asyncio.run(run())


def test_lost_issue_after_commit_recovers_status_without_mint_or_redisclosure(tmp_path, monkeypatch):
    fed, payloads = service(tmp_path, monkeypatch)
    nonce = str(uuid.uuid4())
    def fail_audit(**_): raise RuntimeError('retained synthetic post-commit failure')
    fed.audit.record = fail_audit
    with pytest.raises(RuntimeError): issue(fed, nonce=nonce)
    recovered = issue(fed, nonce=nonce)
    assert recovered['status'] == 'issued' and 'qr_matrix' not in recovered
    assert len(payloads) == 1
    assert fed.manager._conn.execute('SELECT count(*) FROM mobile_enrollment_offer').fetchone()[0] == 1
    fed.manager.close()


def test_enrollment_refusal_proof_requires_absent_exact_member(tmp_path, monkeypatch):
    async def run():
        fed, payloads = service(tmp_path, monkeypatch)
        cert, key = certs.create_self_signed('test/refused')
        from bgp.federation.risk import RiskManager
        nonce = b'x' * 32
        channel = SimpleNamespace(nonce=nonce, trusted=False)
        params = {'token': 'in2n_expired', 'member_id': 'test/refused', 'cert_pem': cert,
                  'signature': RiskManager.sign_challenge(key, nonce).hex(), 'installation_id': INSTALLATION}
        with pytest.raises(RpcError) as failed:
            await fed._edge_on_enroll(channel, params)
        assert failed.value.data == {'admission': 'not_enrolled', 'code': 'enrollment_refused', 'status': 400,
                                     'member_id': 'test/refused', 'key_fingerprint': RiskManager.fingerprint_of(cert)}
        first = issue(fed)
        fed.risk.consume_token(payloads[0]['enrollment_token'], 'test/refused', cert,
            node_type='edge', transport_binding='edge-ws', installation_id=INSTALLATION)
        with pytest.raises(RpcError) as retained:
            await fed._edge_on_enroll(channel, params)
        assert retained.value.data is None
        row = fed.manager._conn.execute('SELECT * FROM mobile_enrollment_offer').fetchone()
        assert row['consumed_generation'] == fed.risk.get_member('test/refused')['enrollment_generation']
        assert row['consumed_key_fingerprint'] == RiskManager.fingerprint_of(cert)
        fed.manager.close()
    asyncio.run(run())
