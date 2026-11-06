"""Production task handlers/SQLite over TLS with a controlled model adapter.

The adapter performs the actual installer-patched native subnet MCP once. It is
not hosted inference, a network-device read, or a protected Docker qualification.
"""
import asyncio
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import time

import pytest

from bgp.federation import gateway
from bgp.federation.runtime import Runtime, read_private, write_private
from bgp.federation.tasks import mark_gateway_dispatch
from test_cloud_workflows_177 import prepare_runtime
from test_exporter_tls_168 import material
from test_internal_transport import _service
from test_ngrok_transport_168 import pair
from test_recovery_transport_178 import stop_process, wait_closed


def member_process(base, entry, token, ready, events):
    async def run():
        member = _service(Path(base), 65001, '192.0.2.1', 'R07 isolated member')
        member.risk.set_role('member', risk_name='example', self_member_id='example/test')
        member.member_scope = {'subnet-calculator'}
        identity_file = Path(base)/'netclaw-hud/installation.json'
        if identity_file.exists():
            identity = read_private(identity_file)['installationId']
            member.runtime = Runtime('openclaw', Path(base), Path(base)/'openclaw.json', identity)
        else:
            prepare_runtime(member)
            write_private(identity_file, {'schemaVersion':1,'installationId':member.runtime.installation})
        os.environ.update(member.runtime.environment())
        await member.start_runtime()  # Production recovery marks lost workers, never replays.
        async def controlled_model(prompt, **kwargs):
            events.put({'stage':'entered','session':kwargs['session_key']})
            if 'cancel-before' in prompt:
                await asyncio.Event().wait()
            mark_gateway_dispatch()
            result = await member.invoker._exec_tool_stdio('subnet-calc-mcp/subnet_calculator', {'cidr':'192.0.2.0/26'})
            assert not result.get('isError'), result
            encoded = json.dumps(result, sort_keys=True).encode()
            fd = os.open(Path(base)/'native-effects.jsonl', os.O_WRONLY|os.O_APPEND|os.O_CREAT, 0o600)
            with os.fdopen(fd, 'ab') as stream:
                stream.write(json.dumps({'session':kwargs['session_key'],'result_sha256':hashlib.sha256(encoded).hexdigest()}).encode()+b'\n')
                stream.flush(); os.fsync(stream.fileno())
            events.put({'stage':'effect','session':kwargs['session_key']})
            if 'cancel-after' in prompt or 'crash-after' in prompt:
                await asyncio.Event().wait()
            return encoded.decode(), None
        gateway.run_agent_turn = controlled_model
        result = await member.dial_border(entry['routing_host'], entry['routing_port'],
            enrollment_token=token or '', registration=entry, registry_revision=1)
        ready.send({'trusted':result.get('trusted') or result.get('pinned'),
                    'identity':member.runtime.installation,'pid':os.getpid()})
        await asyncio.Event().wait()
    asyncio.run(run())


async def launch_member(context, base, entry, token, events):
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=member_process, args=(str(base), entry, token, sender, events))
    process.start(); sender.close()
    try:
        assert await asyncio.to_thread(receiver.poll, 15), 'isolated member failed to attach'
        return process, receiver.recv()
    except BaseException:
        await stop_process(process)
        raise
    finally:
        receiver.close()


async def event(events, stage):
    while True:
        value = await asyncio.to_thread(events.get, True, 15)
        if value['stage'] == stage:
            return value


async def terminal(channel, task, state):
    for _ in range(500):
        result = await channel.call('n2n/tasks/result', {'task_id':task}, timeout=2)
        if result['state'] == state:
            return result
        await asyncio.sleep(.01)
    raise AssertionError(f'expected {state}; got {result}')


@pytest.mark.asyncio
async def test_native_effect_duplicate_cancel_and_actual_member_restart(tmp_path, material, record_property):
    context = multiprocessing.get_context('spawn')
    events = context.Queue()
    process = None
    base = tmp_path/'worker'
    async with pair(tmp_path, material, direct=True) as (border, unused, entry):
        try:
            process, initial = await launch_member(context, base, entry, border.risk.issue_token()['token'], events)
            channel = border.member_channels['example/test']
            member_authority = border.risk.get_member('example/test')
            original = {'skill':'subnet-calculator','input_text':'complete','request_id':'original-complete'}
            submissions = await asyncio.gather(*(channel.call('n2n/tasks/submit', original) for _ in range(6)))
            assert len({row['task_id'] for row in submissions}) == 1
            completed_id = submissions[0]['task_id']
            completed = await terminal(channel, completed_id, 'completed')
            await event(events, 'effect')
            assert len((base/'native-effects.jsonl').read_text().splitlines()) == 1
            payload = json.loads(completed['output_text'])
            facts = json.loads(payload['content'][0]['text'])
            assert facts['network_address'] == '192.0.2.0' and facts['prefix_length'] == 26
            assert completed['usage_available'] is False  # No hosted-provider usage claim.
            assert (await channel.call('n2n/tasks/submit', original))['task_id'] == completed_id
            for label, expected, effect_count in [('cancel-before','cancelled',1), ('cancel-after','outcome_unknown',2)]:
                request = {'skill':'subnet-calculator','input_text':label,'request_id':label}
                admitted = await channel.call('n2n/tasks/submit', request)
                await event(events, 'entered' if label=='cancel-before' else 'effect')
                await channel.call('n2n/tasks/cancel', {'task_id':admitted['task_id']})
                state = await terminal(channel, admitted['task_id'], expected)
                assert (await channel.call('n2n/tasks/submit', request))['task_id'] == admitted['task_id']
                assert len((base/'native-effects.jsonl').read_text().splitlines()) == effect_count
                if expected == 'outcome_unknown':
                    assert state['may_have_executed']
            crash = {'skill':'subnet-calculator','input_text':'crash-after','request_id':'crash-after'}
            admitted = await channel.call('n2n/tasks/submit', crash)
            await event(events, 'effect')
            original_bytes = (base/'native-effects.jsonl').read_bytes()
            assert len(original_bytes.splitlines()) == 3
            start = time.monotonic()
            await stop_process(process)
            await wait_closed(channel)
            record_property('member_loss_detection_seconds', time.monotonic()-start)
            start = time.monotonic()
            process, restored = await launch_member(context, base, entry, None, events)
            record_property('member_process_restore_seconds', time.monotonic()-start)
            assert restored['identity'] == initial['identity'] and restored['pid'] != initial['pid']
            current = border.risk.get_member('example/test')
            assert all(current[k] == member_authority[k] for k in ('key_fingerprint','enrollment_generation','installation_id'))
            channel = border.member_channels['example/test']
            recovered = await terminal(channel, admitted['task_id'], 'outcome_unknown')
            assert recovered['may_have_executed']
            assert (await channel.call('n2n/tasks/submit', crash))['task_id'] == admitted['task_id']
            assert (await channel.call('n2n/tasks/submit', original))['task_id'] == completed_id
            assert (await channel.call('n2n/tasks/result', {'task_id':completed_id})) == completed
            await asyncio.sleep(.05)
            assert (base/'native-effects.jsonl').read_bytes() == original_bytes
            record_property('native_subnet_effects', 3)
            record_property('hosted_provider_calls', 0)
            record_property('cancel_before_native_effects', 0)
        finally:
            if process and process.is_alive():
                await stop_process(process)
            events.close()
            events.join_thread()
