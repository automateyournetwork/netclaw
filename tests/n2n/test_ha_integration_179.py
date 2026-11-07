"""Controlled harness tests; actual Docker/quorum matrix is coordinator-only."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from labs.ha.faults import ByteProxy, Evidence, validate_plan, fault_plan


def test_plan_explicitly_distinguishes_border_quorum_and_raft_paths():
    plan = fault_plan()
    validate_plan(plan)
    assert plan['class'] == 'FIXTURE'
    assert set(plan['rows']) >= {'minority', 'asymmetric-request', 'asymmetric-response', 'threeway',
        'delay-300ms', 'stale-member', 'clock-forward', 'clock-backward', 'clock-suspend',
        'unknown-commit', 'record-capacity', 'nospace', 'full-restart', 'retired-return', 'fenced-restore'}
    assert plan['network_scope'] == 'border-quorum-and-ncfed-byte-paths'
    assert plan['raft_peer_partition_qualified'] is False
    with pytest.raises(ValueError):
        validate_plan(dict(plan, raft_peer_partition_qualified=True))


def test_evidence_requires_exact_row_fault_and_real_counter_provenance(tmp_path):
    evidence = Evidence(tmp_path / 'evidence', {'class': 'FIXTURE', 'source_sha256': 'a' * 64})
    with pytest.raises(ValueError):
        evidence.row('minority', passed=True, effects_before={'model': 0, 'tool': 0},
                     effects_after={'model': 0, 'tool': 0}, observations=[])
    receipt = evidence.row('minority', passed=True,
        effects_before={'fixture_model': 0, 'fixture_tool': 0}, effects_after={'fixture_model': 0, 'fixture_tool': 0},
        observations=[{'kind': 'byte-proxy', 'dropped_bytes': 20}], operation_id='one')
    assert receipt['class'] == 'FIXTURE' and receipt['real_profile_qualified'] is False
    evidence.finish()
    assert json.loads((tmp_path / 'evidence/complete.json').read_text())['rows'][0]['case'] == 'minority'
    with pytest.raises(FileExistsError): Evidence(tmp_path / 'evidence', {})


def test_actual_loopback_byte_proxy_tracks_directed_drop_and_recovers():
    async def run():
        async def echo(reader, writer):
            try:
                while data := await reader.read(1024):
                    writer.write(data); await writer.drain()
            finally:
                writer.close(); await writer.wait_closed()
        server = await asyncio.start_server(echo, '127.0.0.1', 0)
        proxy = await ByteProxy('controlled-loopback', '127.0.0.1', server.sockets[0].getsockname()[1]).start()
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', proxy.port)
            writer.write(b'baseline'); await writer.drain()
            assert await reader.readexactly(8) == b'baseline'
            proxy.policy(request='drop', response='pass')
            writer.write(b'dropped'); await writer.drain()
            with pytest.raises(asyncio.TimeoutError): await asyncio.wait_for(reader.readexactly(7), .05)
            status = proxy.observation()
            assert status['request']['dropped_bytes'] == 7
            assert status['response']['forwarded_bytes'] == 8
            await proxy.reset()
            writer.close(); await writer.wait_closed()
            reader, writer = await asyncio.open_connection('127.0.0.1', proxy.port)
            writer.write(b'recovered'); await writer.drain()
            assert await reader.readexactly(9) == b'recovered'
            writer.close(); await writer.wait_closed()
        finally:
            await proxy.close(); server.close(); await server.wait_closed()
    asyncio.run(run())


def test_proxy_refuses_unbounded_delay_and_unknown_policy():
    proxy = ByteProxy('test', '127.0.0.1', 1234)
    with pytest.raises(ValueError): proxy.policy(request='allow', response='pass')
    with pytest.raises(ValueError): proxy.policy(delay_ms=301)


def test_owned_restart_exports_before_any_stop_and_never_adopts_a_replaced_id(tmp_path, monkeypatch):
    from labs.ha import owned_restart
    snapshot = tmp_path / 'snapshot.json'; snapshot.write_text('{"snapshot":"controlled"}')
    evidence = tmp_path / 'evidence'; evidence.mkdir()
    calls = []
    rows = [{'Id': str(i), 'State': {'Running': True, 'Paused': False, 'Pid': i+10}} for i in range(3)]
    class Lab:
        def inspect_owned(self):
            import copy
            return copy.deepcopy(rows)
    def command(root, stage, args, **kwargs):
        assert (evidence / 'voter-restart.claim.json').exists()
        calls.append(args)
        index = int(args[-1]); rows[index]['State']['Running'] = args[1] == 'start'
        if args[1] == 'start': rows[index]['State']['Pid'] += 100
        return ''
    monkeypatch.setattr(owned_restart, 'command', command)
    result = owned_restart.OwnedVoterRestart(Lab(), evidence, snapshot).execute()
    assert [call[1] for call in calls] == ['stop']*3 + ['start']*3
    assert result['baseline_pids'] != result['restarted_pids']
    assert (evidence / 'voter-restart.stopped.json').exists()


def test_matrix_parser_refuses_unreviewed_restart_before_any_runtime_access(tmp_path, monkeypatch):
    from labs.ha.matrix import main
    evidence = tmp_path / 'never-created'
    monkeypatch.setattr(sys, 'argv', ['matrix', '--fixture', str(tmp_path / 'nonexistent'),
        '--evidence', str(evidence), '--row', 'full-restart'])
    with pytest.raises(SystemExit) as stopped: main()
    assert stopped.value.code == 2 and not evidence.exists()


def test_fresh_raft_proxy_plan_keeps_peer_tls_end_to_end_and_images_pinned(tmp_path):
    from labs.ha.raft_topology import RaftProxyLab
    with pytest.raises(ValueError): RaftProxyLab(tmp_path, 'python:latest')
    lab = RaftProxyLab(tmp_path, 'python@sha256:' + 'a'*64)
    lab.document = {'name': 'netclaw-r08-test', 'containers': ['owned0', 'owned1', 'owned2'],
                    'ports': [12000, 12001, 12002]}
    plan = lab.start_plan()
    proxies, voters = plan['commands'][3:6], plan['commands'][6:9]
    assert plan['new_containers'] == 6 and plan['new_networks'] == 1
    assert all('--pull' in cmd and cmd[cmd.index('--pull')+1] == 'never' for cmd in proxies+voters)
    assert all(not any('/pki' in arg for arg in cmd) for cmd in proxies)
    assert all('--peer-client-cert-auth=true' in cmd and '--strict-reconfig-check=true' in cmd for cmd in voters)
    assert all('--cap-add' not in cmd for cmd in proxies+voters)
    assert {cmd[cmd.index('--initial-advertise-peer-urls')+1] for cmd in voters} == {
        'https://p0:2380', 'https://p1:2380', 'https://p2:2380'}


def test_raft_proxy_rejects_unknown_sources_bad_rules_and_policy_replay(tmp_path):
    from labs.ha.raft_proxy import RaftProxy
    policy = {'schema_version': 1, 'generation': 1, 'owner': 'netclaw-r08-controlled', 'target': 'v0',
              'peers': {'v1': '192.0.2.1'}, 'rules': {'v1': {'request': 'pass', 'response': 'pass', 'delay_ms': 0}}}
    path = tmp_path / 'policy.json'; path.write_text(json.dumps(policy))
    proxy = RaftProxy(tmp_path)
    assert proxy.policy()['generation'] == 1
    policy['rules']['v1']['request'] = 'drop'; path.write_text(json.dumps(policy))
    with pytest.raises(ValueError, match='policy_generation_reused'): proxy.policy()
    policy['generation'] = 2; path.write_text(json.dumps(policy)); assert proxy.policy()['generation'] == 2
    policy['generation'] = 1; path.write_text(json.dumps(policy))
    with pytest.raises(ValueError, match='stale_policy'): proxy.policy()
