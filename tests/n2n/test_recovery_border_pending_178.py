"""Actual Border death with a pending task, over authenticated TLS 1.3 WSS.

Production EdgeChannel, task handlers, SQLite and start_runtime are exercised.
The controlled model adapter marks dispatch then blocks: zero provider/native
calls. This is not native Mobile, protected execution, or live cloud evidence.
"""
import asyncio
import datetime
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import ssl
import time

import pytest
import websockets

from bgp.federation import certs, gateway
from bgp.federation.risk import RiskManager
from bgp.federation.runtime import Runtime, write_private
from bgp.federation.tasks import mark_gateway_dispatch
from test_edge_enrollment import _FakePhone
from test_exporter_tls_168 import material
from test_internal_transport import _service
from test_recovery_transport_178 import stop_process


def pending_border_process(home, material, port, ready, events):
    async def run():
        home_path = Path(home)
        os.environ.update(Runtime('openclaw', home_path, home_path/'openclaw.json', None).environment())
        service = _service(home_path/'n2n', 65001, '192.0.2.178', 'R07 pending Border')
        service.risk.set_role('border', risk_name='r07', enabled_stacks='in2n')
        await service.start_runtime()
        service.inventory.runtime = service.runtime
        service.inventory.config_path = service.runtime.config
        service.risk.ensure_risk_ca()
        service.risk.hub_credential()

        async def blocked_model(prompt, **kwargs):
            # Exercise the durable production dispatch boundary without any
            # external invocation. A lost process must retain its uncertainty.
            mark_gateway_dispatch()
            fd = os.open(home_path/'controlled-dispatch.jsonl', os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o600)
            with os.fdopen(fd, 'a') as stream:
                stream.write(json.dumps({'session': kwargs['session_key'],
                    'provider_calls': 0, 'native_calls': 0})+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            events.put('controlled_dispatch_claimed')
            await asyncio.Event().wait()

        gateway.run_agent_turn = blocked_model
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(material['cert'], material['key'])
        server = await websockets.serve(service.accept_edge_ws, '127.0.0.1', port, ssl=context)
        ready.send({'pid': os.getpid(), 'role': service.risk.role(),
            'installation': service.runtime.installation,
            'port': server.sockets[0].getsockname()[1],
            'token': service.risk.issue_token()['token'] if not service.risk.list_members() else None})
        await asyncio.Event().wait()
    asyncio.run(run())


async def launch_pending_border(context, home, material, events, port=0):
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=pending_border_process,
        args=(str(home), material, port, sender, events))
    process.start()
    sender.close()
    try:
        assert await asyncio.to_thread(receiver.poll, 10), 'isolated Border failed to start'
        return process, receiver.recv()
    except BaseException:
        await stop_process(process)
        raise
    finally:
        receiver.close()


async def connect_device(material, ready, cert, key):
    context = ssl.create_default_context(cafile=material['ca'])
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    ws = await websockets.connect(f"wss://127.0.0.1:{ready['port']}", ssl=context,
        server_hostname='border.example.test')
    assert ws.transport.get_extra_info('ssl_object').version() == 'TLSv1.3'
    challenge = asyncio.get_running_loop().create_future()
    def receive_challenge(params):
        if not challenge.done():
            challenge.set_result(bytes.fromhex(params['nonce']))
        return {}
    phone = _FakePhone(ws, {'n2n/edge/challenge': receive_challenge,
        'n2n/edge/heartbeat': lambda _: {}, 'n2n/edge/self_status': lambda _: {}})
    try:
        nonce = await asyncio.wait_for(challenge, 3)
        body = {'member_id': 'r07/phone', 'installation_id': ready['installation'],
            'signature': RiskManager.sign_challenge(key, nonce).hex()}
        if ready['token']:
            body.update(token=ready['token'], cert_pem=cert, runtime_kind='mobile')
            response = await phone.call('in2n/enroll', body)
            assert response['pinned']
        else:
            body['key_fingerprint'] = RiskManager.fingerprint_of(cert)
            response = await phone.call('in2n/hello', body)
            assert response['trusted']
        assert response['border']['installation_id'] == ready['installation']
        return phone
    except BaseException:
        await ws.close()
        await phone.close()
        raise


def snapshot(source, destination):
    source_db = sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)
    target_db = sqlite3.connect(destination)
    destination.chmod(0o600)
    try:
        source_db.backup(target_db)
        assert target_db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        target_db.row_factory = sqlite3.Row
        task = dict(target_db.execute('SELECT * FROM delegated_task').fetchone())
        member = dict(target_db.execute('SELECT * FROM member WHERE member_id=?', ('r07/phone',)).fetchone())
        assert target_db.execute('SELECT COUNT(*) FROM delegated_task').fetchone()[0] == 1
        return task, member
    finally:
        target_db.close()
        source_db.close()


@pytest.mark.asyncio
async def test_actual_border_pending_dispatch_recovers_without_replay(tmp_path, material, record_property):
    context = multiprocessing.get_context('spawn')
    events = context.Queue()
    home = tmp_path/'border-home'
    home.mkdir(mode=0o700)
    write_private(home/'openclaw.json', {})
    cert, key = certs.create_self_signed('r07/phone')
    write_private(tmp_path/'device-identity.json', {'certificate': cert, 'key': key})
    process, initial = await launch_pending_border(context, home, material, events)
    owned_processes = [process]
    phone = None
    timings = {}
    try:
        phone = await connect_device(material, initial, cert, key)
        request = {'text': 'Controlled pending Border task; no external execution',
            'request_id': 'border-pending-original', 'conversation_id': 'r07-pending',
            'client_capabilities': ['task_outcomes_v1']}
        admitted = await phone.call('n2n/edge/ask', request)
        task_id = admitted['task_id']
        assert await asyncio.to_thread(events.get, True, 5) == 'controlled_dispatch_claimed'
        assert (await phone.call('n2n/tasks/status', {'task_id': task_id}))['state'] == 'working'
        before, member_before = snapshot(home/'n2n/federation.db', tmp_path/'before-fault.sqlite')
        assert before['task_id'] == task_id and before['dispatch_started'] == 1
        assert before['state'] == 'working' and before['client_request'] == request['request_id']
        assert before['owner_generation'] == member_before['key_fingerprint']
        dispatch_bytes = (home/'controlled-dispatch.jsonl').read_bytes()
        assert len(dispatch_bytes.splitlines()) == 1
        write_private(tmp_path/'admission.json', {'task_id': task_id, 'request': request,
            'installation': initial['installation'], 'pid': initial['pid'],
            'role': initial['role'], 'port': initial['port']})

        timings['fault_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        started = time.monotonic()
        await stop_process(process)
        await asyncio.wait_for(phone.ws.wait_closed(), 3)
        timings['signal_to_socket_close_seconds'] = time.monotonic()-started
        await phone.close()
        phone = None
        stopped, _ = snapshot(home/'n2n/federation.db', tmp_path/'after-death-before-recovery.sqlite')
        assert stopped['state'] == 'working' and stopped['dispatch_started'] == 1

        timings['restore_start_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        started = time.monotonic()
        process, restored = await launch_pending_border(context, home, material, events, initial['port'])
        owned_processes.append(process)
        assert restored['token'] is None and restored['installation'] == initial['installation']
        assert restored['pid'] != initial['pid'] and restored['role'] == initial['role'] == 'border'
        phone = await connect_device(material, restored, cert, key)
        result = await phone.call('n2n/tasks/result', {'task_id': task_id})
        timings['process_start_to_authenticated_reconciliation_seconds'] = time.monotonic()-started
        timings['reconciled_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        assert result['state'] == 'outcome_unknown' and result['may_have_executed']
        assert result['tokens_used'] is None and not result['usage_available']
        assert 'output_text' not in result
        duplicates = await asyncio.gather(*(phone.call('n2n/edge/ask', request) for _ in range(4)))
        assert all(value['task_id'] == task_id for value in duplicates)
        await asyncio.sleep(.05)
        after, member_after = snapshot(home/'n2n/federation.db', tmp_path/'after-recovery.sqlite')
        assert after['state'] == 'outcome_unknown' and after['dispatch_started'] == 1
        for field in ('task_id', 'client_request', 'body_digest', 'owner_generation',
                      'peer_identity', 'created_at', 'result_ref', 'dispatch_started'):
            assert after[field] == before[field]
        for field in ('pinned_key', 'key_fingerprint', 'enrollment_generation', 'installation_id'):
            assert member_after[field] == member_before[field]
        assert (home/'controlled-dispatch.jsonl').read_bytes() == dispatch_bytes
        assert (await phone.call('n2n/tasks/result', {'task_id': task_id})) == result
        write_private(tmp_path/'reconciled.json', {'result': result, 'timings': timings,
            'controlled_worker_entries': 1, 'provider_calls': 0, 'native_calls': 0,
            'initial_pid': initial['pid'], 'restored_pid': restored['pid']})
        for name, value in timings.items():
            record_property(name, value)
        record_property('controlled_worker_entries', 1)
        record_property('provider_calls', 0)
        record_property('native_calls', 0)
    finally:
        if phone:
            await phone.ws.close()
            await phone.close()
        if process.is_alive():
            await stop_process(process)
        assert all(not owned.is_alive() and owned.exitcode is not None for owned in owned_processes)
        with pytest.raises(ConnectionRefusedError):
            reader, writer = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', initial['port']), 1)
            writer.close()
            await writer.wait_closed()
        write_private(tmp_path/'cleanup.json', {'processes': [
            {'pid': owned.pid, 'exitcode': owned.exitcode, 'alive': owned.is_alive()}
            for owned in owned_processes], 'listener_port': initial['port'],
            'listener_connection_refused': True})
        events.close()
        events.join_thread()
