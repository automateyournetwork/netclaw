"""Synthetic native-artifact fixtures; no Docker/provider/NetBox invocation."""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from protected_support_171 import NOW, OperationPair, canonical, module, sha


async def failed_pair(tmp_path, monkeypatch, status=403):
    pair = OperationPair(tmp_path)
    arguments = {'object_type': 'dcim.device', 'object_id': 1,
                 'fields': ['id', 'name', 'status', 'site', 'device_type', 'last_updated'], 'brief': False}
    pair.template['tool_call'].update(tool='netbox_get_object_by_id', arguments=arguments,
                                     arguments_sha256=sha(arguments), device_ref='NetBox device 1')
    pair.catalog_entry['tools'] = [dict(pair.template['tool_call'], limits={
        key: value for key, value in pair.template['limits'].items() if key != 'expires_at_ms'})]
    state = tmp_path / 'execution'
    state.mkdir(mode=0o700)
    names = ('__init__.py', '__main__.py', 'server.py', 'config.py', 'netbox_client.py', 'netbox_types.py', 'netclaw_http.py')
    sources = {'src/netbox_mcp_server/' + name: b'# synthetic upstream fixture\n' for name in names}
    sources['src/netbox_mcp_server/netclaw_http.py'] = (Path(__file__).resolve().parents[2] / 'scripts/lib/netbox_http.py').read_bytes()
    schema = {'type': 'object', 'properties': {'object_id': {'type': 'integer'}}}
    runtime = {'state_dir': str(state), 'model_profile': pair.template['model_profile'],
        'agent_image': 'sha256:' + 'a' * 64, 'relay_image': 'sha256:' + 'b' * 64,
        'guard': {'image': 'sha256:' + 'c' * 64}, 'mcp': {'kind': 'netbox', 'tool': 'netbox_get_object_by_id',
            'origin': 'https://fixture.invalid', 'source_sha256': {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()},
            'input_schema_sha256': sha(schema)}}
    pair.member.config = {'role': 'member', 'identity': pair.template['member'], 'border': pair.template['border'],
        'runtime': {'schemaVersion': 1, 'profiles': [{'model_profile_id': pair.template['model_profile']['profile_id'],
                                                   'tool_call': pair.template['tool_call'], 'runtime': runtime}]}}
    # Existing revision/image/venv validation has separate tests. This fixture
    # exercises the new proof boundary without a real Docker runtime/credential.
    monkeypatch.setattr(module('protected_docker'), 'validate_execution_bindings', lambda *_: None)
    pair.inspect_calls = 0
    pair.inspect_mutator = lambda rows: rows
    async def inspect(runtime, names):
        pair.inspect_calls += 1
        images = {'agent': runtime['agent_image'], 'relay': runtime['relay_image'], 'guard': runtime['guard']['image']}
        rows = [{'Name': '/' + name, 'Image': images[name.rsplit('-', 1)[1]],
                 'State': {'Running': False, 'Restarting': False, 'Pid': 0, 'Status': 'exited'},
                 'Config': {'Labels': {'netclaw.spec': '171'}}} for name in names]
        return pair.inspect_mutator(rows)
    monkeypatch.setattr(module('protected_failure_recovery'), 'inspect_containers', inspect)
    def put(name, value):
        path = pair.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        for parent in [path.parent, *path.parent.parents]:
            parent.chmod(0o700)
            if parent == pair.root:
                break
        raw = value if isinstance(value, bytes) else canonical(value)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
        return path
    pair.put = put
    class Executor:
        async def run(self, payload, gate):
            pair.executor_calls += 1
            async def effect():
                pair.effects.append({'synthetic_http_status': status})
                pair.root = state / payload['operation_id']
                pair.root.mkdir(mode=0o700)
                pair.prefix = 'netclaw-r02-' + hashlib.sha256(payload['operation_id'].encode()).hexdigest()[:20]
                for name, raw in sources.items():
                    put('tool/source/' + name, raw).chmod(0o400)
                put('tool/mcp-call.json', {'tool': 'netbox_get_object_by_id', 'arguments': arguments, 'dispatched_at_ms': NOW + 1})
                put('tool/mcp-schema.json', {'tool': 'netbox_get_object_by_id', 'inputSchema': schema})
                policy = {'schemaVersion': 1, 'url': 'https://fixture.invalid/api/dcim/devices/1/',
                          'params': {'fields': ','.join(arguments['fields'])}}
                put('tool/http-policy.json', policy)
                put('tool/netbox-http-receipt.json', dict(policy, method='GET', http_requests=1,
                    state='failed', started_at_ms=NOW + 2, captured_at_ms=NOW + 3, status=status,
                    error_code='netbox_read_failed_or_unknown'))
                put('cleanup.json', {'owned': [pair.prefix + '-' + kind for kind in ('guard', 'relay', 'agent')], 'unresolved': []})
                put('containment.json', {'image': runtime['agent_image'], 'network': pair.prefix + '-net',
                    'read_only': True, 'no_new_privileges': True, 'user': str(os.getuid()),
                    'capabilities_dropped': ['ALL'], 'mount_destinations': ['/run/netclaw']})
                raise module('protected_contract').ProtectedOutcomeUnknown('mcp_read_failed_or_unknown')
            return await gate(copy.deepcopy(payload['tool_call']), effect)
    pair.member.executor = Executor()
    prepared = await pair.prepare()
    await pair.decide(prepared)
    await pair.drain()
    pair.operation = prepared['operation_id']
    pair.original = pair.member.store.get('member', pair.operation)
    assert pair.original['state'] == 'outcome_unknown'
    return pair


@pytest.mark.parametrize('status', [401, 403])
def test_known_denial_signs_failed_ack_without_replay(tmp_path, monkeypatch, status):
    async def run():
        pair = await failed_pair(tmp_path, monkeypatch, status)
        results = await asyncio.gather(*(pair.reconcile(pair.operation) for _ in range(5)))
        row = pair.member.store.get('member', pair.operation)
        assert all(result['state'] == 'failed' and result['result']['verified'] and result['result']['durable_ack'] for result in results)
        assert row['state'] == 'acknowledged' and row['effect_finished'] == 1 and row['tool_evidence'] is None
        for name in ('approval', 'approval_digest', 'attempt_id', 'effect_authorization', 'review', 'trust_snapshot'):
            assert row[name] == pair.original[name]
        result = row['receipt']['payload']
        assert result['outcome'] == 'failed' and result['effect_status'] == 'finished' and result['output'] == {}
        assert result['tool_evidence_sha256'] == sha(None) and result['error_code'] == 'native_netbox_http_' + str(status)
        proof = row['executor_result']['failure_recovery']
        audits = [record for event, record in pair.audit_events if event == 'protected_failure_recovery']
        assert len(audits) == 1 and audits[0]['failure_proof_digest'] == sha(proof)
        assert audits[0]['attempt_id'] == row['attempt_id'] and audits[0]['original_error_code'] == 'effect_outcome_unknown'
        assert result['audit_refs']['failure_recovery'] == row['audit_refs']['failure_recovery']
        assert pair.executor_calls == len(pair.effects) == pair.inspect_calls == 1
        await pair.restart()
        recovered = await pair.reconcile(pair.operation)
        assert recovered['result']['digest'] == results[0]['result']['digest']
        assert pair.executor_calls == len(pair.effects) == pair.inspect_calls == 1
    asyncio.run(run())


CASES = ['http200', 'http404', 'http429', 'http500', 'claimed', 'unknown', 'missing_status',
    'wrong_url', 'wrong_params', 'wrong_call', 'bool_call', 'bool_policy', 'wrong_schema', 'wrong_source',
    'unsupported_adapter', 'extra_source', 'too_early', 'too_late', 'bool_time', 'repeat_request',
    'missing_call', 'missing_http', 'success_result', 'success_evidence', 'symlink', 'hardlink',
    'unsafe_mode', 'wrong_owner', 'oversize', 'duplicate_json', 'missing_cleanup', 'extra_cleanup',
    'unresolved_cleanup', 'running_container', 'restarting_container', 'nonzero_pid', 'wrong_image', 'missing_container']


@pytest.mark.parametrize('case', CASES)
def test_incomplete_conflicting_or_unsafe_proof_stays_unknown(tmp_path, monkeypatch, case):
    async def run():
        pair = await failed_pair(tmp_path, monkeypatch)
        def change(name, **updates):
            value = json.loads((pair.root / name).read_bytes()); value.update(updates); pair.put(name, value)
        http = 'tool/netbox-http-receipt.json'
        if case.startswith('http'): change(http, status=int(case[4:]))
        elif case in ('claimed', 'unknown'): change(http, state=case)
        elif case == 'missing_status':
            value = json.loads((pair.root / http).read_bytes()); value.pop('status'); pair.put(http, value)
        elif case == 'wrong_url': change(http, url='https://other.invalid/api/dcim/devices/1/')
        elif case == 'wrong_params': change(http, params={'fields': 'id'})
        elif case in ('wrong_call', 'bool_call'):
            value = json.loads((pair.root / 'tool/mcp-call.json').read_bytes())
            value['arguments']['object_id'] = True if case == 'bool_call' else 2
            pair.put('tool/mcp-call.json', value)
        elif case == 'bool_policy': change('tool/http-policy.json', schemaVersion=True)
        elif case == 'wrong_schema': change('tool/mcp-schema.json', inputSchema={'type': 'array'})
        elif case == 'wrong_source':
            (pair.root / 'tool/source/src/netbox_mcp_server/server.py').chmod(0o600)
            pair.put('tool/source/src/netbox_mcp_server/server.py', b'# changed\n')
        elif case == 'unsupported_adapter': pair.member.config['runtime']['profiles'][0]['runtime']['mcp']['source_sha256']['src/netbox_mcp_server/netclaw_http.py'] = '0' * 64
        elif case == 'extra_source': pair.put('tool/source/extra.py', b'# unpinned\n')
        elif case == 'too_early': change('tool/mcp-call.json', dispatched_at_ms=NOW - 1)
        elif case == 'too_late': change(http, captured_at_ms=NOW + 999999)
        elif case == 'bool_time': change(http, started_at_ms=True)
        elif case == 'repeat_request': change(http, http_requests=2)
        elif case in ('missing_call', 'missing_http'): (pair.root / ('tool/mcp-call.json' if case == 'missing_call' else http)).unlink()
        elif case in ('success_result', 'success_evidence'): pair.put('tool/' + ('mcp-result.json' if case == 'success_result' else 'tool-evidence.json'), {})
        elif case == 'symlink':
            target = pair.root / http; target.rename(pair.root / 'old-http'); target.symlink_to(pair.root / 'old-http')
        elif case == 'hardlink': os.link(pair.root / http, pair.root / 'second-http')
        elif case == 'unsafe_mode': (pair.root / http).chmod(0o644)
        elif case == 'wrong_owner':
            private_os = SimpleNamespace(**vars(os)); private_os.getuid = lambda: 999999
            monkeypatch.setattr(module('protected_failure_recovery'), 'os', private_os)
        elif case == 'oversize': pair.put(http, b' ' * 16385)
        elif case == 'duplicate_json': pair.put(http, b'{"status":403,"status":403}')
        elif case == 'missing_cleanup': (pair.root / 'cleanup.json').unlink()
        elif case == 'extra_cleanup': change('cleanup.json', owned=[pair.prefix + '-' + x for x in ('guard', 'relay', 'agent', 'other')])
        elif case == 'unresolved_cleanup': change('cleanup.json', unresolved=['owned_http_server'])
        else:
            def mutate(rows):
                if case == 'running_container': rows[0]['State']['Running'] = True
                elif case == 'restarting_container': rows[0]['State']['Restarting'] = True
                elif case == 'nonzero_pid': rows[0]['State']['Pid'] = 42
                elif case == 'wrong_image': rows[0]['Image'] = 'sha256:' + '0' * 64
                elif case == 'missing_container': rows.pop()
                return rows
            pair.inspect_mutator = mutate
        result = await pair.member.member_status(pair.to_member, {'operation_id': pair.operation})
        row = pair.member.store.get('member', pair.operation)
        assert result['state'] == row['state'] == 'outcome_unknown'
        assert row['receipt'] is row['executor_result'] is row['tool_evidence'] is None and row['effect_finished'] == 0
        assert row['attempt_id'] == pair.original['attempt_id'] and pair.executor_calls == len(pair.effects) == 1
    asyncio.run(run())


def test_active_worker_cannot_be_recovered(tmp_path, monkeypatch):
    async def run():
        pair = await failed_pair(tmp_path, monkeypatch)
        worker = asyncio.create_task(asyncio.Event().wait())
        pair.member.workers.add(worker)
        try:
            result = await pair.member.member_status(pair.to_member, {'operation_id': pair.operation})
            assert result['state'] == 'outcome_unknown' and pair.inspect_calls == 0
            assert pair.executor_calls == len(pair.effects) == 1
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
    asyncio.run(run())


def test_dedicated_store_cas_has_only_one_winner(tmp_path, monkeypatch):
    async def run():
        pair = await failed_pair(tmp_path, monkeypatch)
        verifier = module('protected_failure_recovery')
        proof = await verifier.verify_known_netbox_failure(pair.original, pair.member.config)
        def finish():
            try:
                return pair.member.store.complete_known_netbox_failure(proof, 'synthetic-proof-audit')['state']
            except module('protected_contract').ProtectedError as exc:
                return exc.code
        results = await asyncio.gather(*(asyncio.to_thread(finish) for _ in range(2)))
        assert sorted(results) == ['audit_pending', 'failure_state_conflict']
        row = pair.member.store.get('member', pair.operation)
        assert row['attempt_id'] == pair.original['attempt_id'] and row['executor_result']['failure_recovery'] == proof.proof
        assert (await pair.reconcile(pair.operation))['state'] == 'failed'
        assert pair.executor_calls == len(pair.effects) == 1
    asyncio.run(run())


@pytest.mark.parametrize('stage', ['proof_audit', 'result_audit', 'store_cas', 'artifact_after_inspect'])
def test_interruption_or_stale_evidence_never_replays(tmp_path, monkeypatch, stage):
    async def run():
        pair = await failed_pair(tmp_path, monkeypatch)
        if stage in ('proof_audit', 'result_audit'):
            event = 'protected_failure_recovery' if stage == 'proof_audit' else 'protected_result'
            pair.failed_audits.add(event)
            with pytest.raises(module('protected_contract').ProtectedError):
                await pair.member.member_status(pair.to_member, {'operation_id': pair.operation})
            row = pair.member.store.get('member', pair.operation)
            assert row['state'] == ('outcome_unknown' if stage == 'proof_audit' else 'audit_pending')
            if stage == 'result_audit':
                assert row['executor_result']['failure_recovery']['http_status'] == 403
            configuration = pair.member.config
            await pair.restart()
            pair.member.config = configuration
            pair.failed_audits.clear()
            assert (await pair.reconcile(pair.operation))['state'] == 'failed'
        else:
            verifier = module('protected_failure_recovery')
            proof = await verifier.verify_known_netbox_failure(pair.original, pair.member.config)
            if stage == 'store_cas':
                pair.member.store.transition('member', pair.operation, 'outcome_unknown', error_code='new_observation')
            else:
                pair.put('tool/mcp-call.json', {})
            with pytest.raises(module('protected_contract').ProtectedError):
                pair.member.store.complete_known_netbox_failure(proof, 'synthetic-proof-audit')
            assert pair.member.store.get('member', pair.operation)['state'] == 'outcome_unknown'
        assert pair.executor_calls == len(pair.effects) == 1
    asyncio.run(run())
