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


def test_restore_verifier_exercises_production_fenced_prepare_and_model_tool_gates():
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.config import Manifest
    from bgp.federation.ha.recovery import snapshot_document, verify_isolation, install_restored, activate_restored
    from labs.ha.restore_verify import verify_restore
    from test_ha_contract_179 import manifest_fixture
    from test_ha_operations_179 import prepared, dispatch_fixture, request
    from test_ha_recovery_179 import recovery_case, MemoryStore
    store, nodes, ledger, row, member = prepared()
    row = dispatch_fixture(store, nodes, ledger, row)
    ledger.admit(request(ledger, row), row['review']['member'])
    old = nodes[0].manifest
    snapshot = snapshot_document(old, store.rows, store.revision, now_ms=1000)
    value, _, _ = manifest_fixture()
    value.update(cluster_id=old.cluster_id, organization=old.value['organization'], revision=old.revision+1)
    new = Manifest(value)
    _, _, _, _, _, certificate, proof, _ = recovery_case()
    body = proof()['payload']
    body.update(**old.audience, new_generation=new.generation, snapshot_sha256=c.sha256(snapshot),
                nodes=sorted(n['node_id'] for n in old.nodes))
    receipt = verify_isolation(proof(body), certificate, expected_key_id=c.key_id(certificate),
        old_manifest=old, new_manifest=new, snapshot=snapshot, now_ms=2001)
    target = MemoryStore()
    install_restored(target, snapshot, old, new, receipt, now_ms=2001)
    before_activation = verify_restore(target, snapshot, old, new, new.nodes[0]['node_id'])
    assert before_activation['gate_results'] == [{'gate': 'campaign', 'code': 'recovery_fenced'}]
    activate_restored(target, snapshot, old, new, receipt, now_ms=2002)
    result = verify_restore(target, snapshot, old, new, new.nodes[0]['node_id'])
    assert [row['gate'] for row in result['gate_results']] == ['fresh-prepare', 'model-admission', 'tool-admission']
    assert all(row['code'] == 'recovery_fenced' for row in result['gate_results'])
    assert result['real_profile_qualified'] is False


def test_private_cli_setup_uses_merged_factory_and_preserves_ha_marker(tmp_path):
    import hashlib
    from bgp.federation import certs, protected_contract as c
    from bgp.federation.ha.config import sign_manifest, HAError
    from test_ha_contract_179 import manifest_fixture
    spec = importlib.util.spec_from_file_location('private_ha_cli', ROOT / 'scripts/ha-cluster.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    value, anchor, anchor_key = manifest_fixture()
    certificate, key = certs.create_self_signed('fixture-member')
    private = tmp_path / 'private'; private.mkdir(mode=0o700)
    def write(name, raw):
        path = private/name; path.write_bytes(raw); path.chmod(0o600); return str(path)
    config = {'schema_version': 1, 'role': 'member',
        'manifest_file': write('manifest.json', c.encode(sign_manifest(value, anchor_key))),
        'anchor_certificate_file': write('anchor.crt', anchor.encode()), 'anchor_key_id': c.key_id(anchor),
        'transport_ca_file': write('transport.crt', anchor.encode()),
        'certificate_file': write('member.crt', certificate.encode()), 'private_key_file': write('member.key', key.encode())}
    raw = c.encode(config); path = write('config.json', raw)
    args = cli.parser().parse_args(['setup', '--config-file', path, '--config-sha256', hashlib.sha256(raw).hexdigest(),
        '--role', 'member', '--state-dir', str(private/'n2n')])
    result = cli.execute(args)
    assert result['ha_required'] and result['generation'] == value['generation']
    marker = (private/'n2n/ha-required.json').read_bytes()
    assert cli.execute(args) == result and (private/'n2n/ha-required.json').read_bytes() == marker
    args.config_sha256 = '0'*64
    with pytest.raises(HAError, match='ha_configuration_changed'): cli.execute(args)
    assert (private/'n2n/ha-required.json').read_bytes() == marker


def test_cancelled_owned_fault_waits_for_bounded_thread_before_inspection():
    from labs.ha.faults import owned_call
    import threading
    import time
    async def run():
        started, finished = threading.Event(), threading.Event()
        def controlled_change():
            started.set(); time.sleep(.03); finished.set()
        task = asyncio.create_task(owned_call(controlled_change))
        while not started.is_set(): await asyncio.sleep(.001)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        assert finished.is_set(), 'inspection must not race an escaped mutation thread'
    asyncio.run(run())
