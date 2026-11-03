"""Backend integration checks for native owner auth, bridge and enrollment."""
import asyncio
import json
import secrets
from types import SimpleNamespace
import uuid

import pytest
from bgp.federation.protected_contract import decode, encode
from bgp.federation.protected_owner import OwnerAuthority, write_private
from bgp.federation.protected_service import OperatorBridge
from bgp.federation.risk import RiskManager


@pytest.mark.asyncio
async def test_real_fixed_bridge_consumes_ticket_and_refuses_unknown_method(tmp_path):
    state = tmp_path / 'private'
    installation = str(uuid.uuid4())
    owner = OwnerAuthority(state, installation)
    owner.init('Local owner')
    token = secrets.token_urlsafe(32)
    write_private(state / 'protected-operator.env', ('NETCLAW_PROTECTED_OPERATOR_TOKEN=' + token + '\n').encode())
    bridge = OperatorBridge(SimpleNamespace(owner=owner), state, installation)
    port = await bridge.start()
    async def post(method, params, bearer=token):
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        body = encode({'method': method, 'params': params})
        writer.write((f'POST /operator HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nAuthorization: Bearer {bearer}\r\nContent-Length: {len(body)}\r\n\r\n').encode() + body)
        await writer.drain()
        raw = await reader.read()
        writer.close(); await writer.wait_closed()
        head, body = raw.split(b'\r\n\r\n', 1)
        return int(head.split()[1]), decode(body)
    try:
        ticket = owner.ticket()
        code, response = await post('owner.login', {'ticket': ticket})
        assert code == 200 and response['ok']
        session = response['result']
        assert session['principal']['roles'] == ['owner']
        assert (await post('owner.login', {'ticket': ticket}))[0] == 401
        assert (await post('owner.session', {'cookie': session['cookie']}, bearer='foreign'))[0] == 401
        assert (await post('shell', {'command': 'id'}))[0] == 403
        assert (await post('owner.logout', {'cookie': session['cookie'], 'csrf_token': session['csrf_token']}))[0] == 200
        assert (await post('owner.session', {'cookie': session['cookie']}))[0] == 401
        descriptor = json.loads((state / 'protected-operator.json').read_text())
        assert descriptor['installationId'] == installation and descriptor['port'] == port
        assert token not in json.dumps(descriptor)
    finally:
        await bridge.close()


def test_same_key_reenrollment_gets_new_durable_authority(manager):
    border = RiskManager(manager)
    border.set_role('border', risk_name='test')
    certificate, _ = RiskManager._generate_self_signed('test/member')
    installation = str(uuid.uuid4())
    first = border.consume_token(border.issue_token()['token'], 'test/member', certificate, installation_id=installation)
    second = border.consume_token(border.issue_token()['token'], 'test/member', certificate, installation_id=installation)
    assert first['enroll_fingerprint'] == second['enroll_fingerprint']
    assert first['enrollment_generation'] != second['enrollment_generation']
    assert border.get_member('test/member')['enrollment_generation'] == second['enrollment_generation']
    assert border.get_member('test/member')['installation_id'] == installation


def test_bad_enrollment_rolls_back_generation_and_token(manager):
    border = RiskManager(manager)
    border.set_role('border', risk_name='test')
    certificate, _ = RiskManager._generate_self_signed('test/member')
    token = border.issue_token()['token']
    with pytest.raises(ValueError, match='INVALID_INSTALLATION'):
        border.consume_token(token, 'test/member', certificate, installation_id={'foreign': True})
    assert border.get_member('test/member') is None
    assert border.consume_token(token, 'test/member', certificate, installation_id=str(uuid.uuid4()))['pinned']
