"""Source-only qualification safeguards; no model, daemon or Docker startup."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
from types import SimpleNamespace
import uuid

import pytest

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
from labs.ha.real_budget import Budget, RehearsalRefused, digest, private_directory, validate_claim, write_new
from labs.ha.real_runtime import Rehearsal, freeze_source, validate_plan, copy_model_store
from labs.ollama import qualify as model


def identity(): return str(uuid.uuid4())


def budget(tmp_path):
    root = private_directory(tmp_path / 'private', create=True)
    return Budget(root, run_id=identity(), create=True)


def reserve(value, surface='runner', **changes):
    return value.reserve(**dict(operation_id=identity(), client_nonce=identity(), review_digest='a' * 64,
                               surface=surface, **changes))


def test_unknown_is_durable_and_other_surfaces_cannot_take_the_slot(tmp_path):
    value = budget(tmp_path); claim = reserve(value, 'hud')
    value.claim_send(claim, surface='hud'); value.unknown(claim['claim_id'])
    restarted = Budget(value.root)
    for surface in ('runner', 'hud', 'vscode', 'mobile'):
        with pytest.raises(RehearsalRefused, match='unresolved'): reserve(restarted, surface)
    with pytest.raises(RehearsalRefused): restarted.claim_send(claim, surface='hud')
    with pytest.raises(RehearsalRefused): restarted.claim_send(claim, surface='runner')
    assert restarted.snapshot()['reservations'][0]['state'] == 'unknown'


def test_cumulative_budget_is_not_refunded_by_settlement(tmp_path):
    value = budget(tmp_path)
    for _ in range(10):
        claim = reserve(value); value.claim_send(claim, surface='runner')
        value.settle(claim, receipt_sha256='b' * 64, inferences=0, native_effects=0)
    assert value.snapshot()['reserved'] == {'operations': 10, 'inferences': 20, 'native_effects': 10}
    with pytest.raises(RehearsalRefused, match='budget_exhausted'): reserve(value)


def test_concurrent_senders_have_exactly_one_reservation_and_send(tmp_path):
    value = budget(tmp_path)
    def claim(_):
        try: return reserve(Budget(value.root))
        except RehearsalRefused: return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = [c for c in pool.map(claim, range(4)) if c]
    assert len(claims) == 1
    def send(_):
        try: Budget(value.root).claim_send(claims[0], surface='runner'); return True
        except RehearsalRefused: return False
    with ThreadPoolExecutor(max_workers=4) as pool: assert sum(pool.map(send, range(4))) == 1


@pytest.mark.parametrize('mutate', [lambda c: c.update(surface='mobile'), lambda c: c.update(operation_id=identity()),
    lambda c: c.update(review_digest='c' * 64), lambda c: c['limits'].update(inferences=3),
    lambda c: c.update(extra=True), lambda c: c.update(claim_sha256='0' * 64)])
def test_external_claim_is_exact_and_hash_bound(tmp_path, mutate):
    value = budget(tmp_path); original = reserve(value, 'vscode'); changed = copy.deepcopy(original); mutate(changed)
    with pytest.raises(RehearsalRefused):
        validate_claim(changed, operation_id=original['operation_id'], client_nonce=original['client_nonce'],
                       review_digest=original['review_digest'], surface='vscode', run_id=value.run_id)


def test_unsent_claim_cannot_be_settled_or_reused(tmp_path):
    value = budget(tmp_path); claim = reserve(value)
    with pytest.raises(RehearsalRefused): value.settle(claim, receipt_sha256='b' * 64, inferences=0, native_effects=0)
    with pytest.raises(RehearsalRefused):
        value.reserve(operation_id=claim['operation_id'], client_nonce=identity(), review_digest='a' * 64, surface='runner')


def test_private_budget_rejects_writable_by_others_and_symlink(tmp_path):
    value = budget(tmp_path); value.path.chmod(0o644)
    with pytest.raises(RehearsalRefused): Budget(value.root)
    value.path.chmod(0o600)
    link = tmp_path / 'link'; link.symlink_to(value.root, target_is_directory=True)
    with pytest.raises(RehearsalRefused): Budget(link)


def test_model_owner_labels_are_explicit_and_keep_standalone_default(tmp_path):
    args = SimpleNamespace(family=4, image='sha256:' + 'a' * 64, name='netclaw-r08-test-model',
        model_store=str(tmp_path / 'models'), state_dir=str(tmp_path / 'model'), guard_uid=os.getuid(), model_uid=21006)
    assert model.owner_labels(args) == ['--label', 'netclaw.spec=176']
    args.owner_spec = 179
    with pytest.raises(model.QualificationRefused, match='owner_name_required'): model.owner_labels(args)
    args.owner_name = 'netclaw-r08-test'
    assert model.owner_labels(args) == ['--label', 'netclaw.spec=179', '--label', 'netclaw.owner=netclaw-r08-test']
    argv = model.create_model_args(model.selected_profile(args), 'owned', owner=179, owner_name=args.owner_name)
    assert 'netclaw.spec=179' in argv and 'netclaw.owner=netclaw-r08-test' in argv
    assert argv[argv.index('--log-driver') + 1] == 'json-file'
    assert argv[argv.index('--log-opt') + 1] == 'max-size=-1'
    assert '--log-driver' not in model.create_model_args(model.selected_profile(args), 'owned')
    row = {'Name': '/netclaw-r08-test-model', 'Image': args.image, 'Id': 'b' * 64,
           'Config': {'Labels': {'netclaw.spec': '179', 'netclaw.owner': 'another-owned-run'}}}
    with pytest.raises(model.QualificationRefused):
        model.owned_container(row, args.image, args.name, 'b' * 64, owner=179, owner_name=args.owner_name)


def fixture_plan(tmp_path):
    source = private_directory(tmp_path / 'source-input', create=True)
    write_new(source / 'runner.py', b'print("test")\n')
    files = {'runner.py': hashlib.sha256((source / 'runner.py').read_bytes()).hexdigest()}
    gate = tmp_path / 'fixture-gate.json'
    write_new(gate, {'schema_version': 1, 'class': 'FIXTURE', 'passed': True, 'source_sha256': digest(files)})
    return {'schema_version': 1, 'root': str(tmp_path / 'real'), 'run_id': identity(), 'name': 'netclaw-r08-testing',
        'source_root': str(source), 'source_files': files, 'source_sha256': digest(files), 'fixture_gate_file': str(gate),
        'fixture_gate_sha256': hashlib.sha256(gate.read_bytes()).hexdigest(), 'template_file': str(tmp_path / 'template.json'),
        'template_sha256': 'a' * 64, 'python': {'executable': '/absolute/python', 'sha256': 'b' * 64,
            'environment': '/absolute', 'manifest_file': '/manifest.json', 'manifest_sha256': 'c' * 64},
        'ports': {'cluster': [31000,31001,31002], 'in2n': [31003,31004,31005], 'https': [31006,31007,31008],
                  'edge': [31009,31010,31011], 'api': [31012,31013,31014,31015], 'bgp': [31016,31017,31018]},
        'guard_token_variable': 'DEFENSECLAW_GATEWAY_TOKEN'}


def test_matching_gate_freezes_exact_source_without_editing_input(tmp_path):
    tmp_path.chmod(0o700); plan = fixture_plan(tmp_path); validate_plan(plan)
    root = private_directory(plan['root'], create=True)
    frozen = freeze_source(plan, root)
    assert (frozen / 'runner.py').read_bytes() == (Path(plan['source_root']) / 'runner.py').read_bytes()
    assert (frozen / 'runner.py').stat().st_mode & 0o222 == 0
    assert frozen.stat().st_mode & 0o222 == 0
    assert json.loads((root / 'source-manifest.json').read_bytes())['files'] == plan['source_files']
    # Undo only the test's owned temporary readonly directories for pytest cleanup.
    frozen.chmod(0o700)


@pytest.mark.parametrize('change', ('unpassed', 'wrong-source', 'changed-file', 'symlink'))
def test_fixture_gate_or_source_change_prevents_freeze(tmp_path, change):
    tmp_path.chmod(0o700); plan = fixture_plan(tmp_path); root = private_directory(plan['root'], create=True)
    if change in ('unpassed', 'wrong-source'):
        gate = Path(plan['fixture_gate_file']); value = json.loads(gate.read_bytes())
        value.update({'passed': False} if change == 'unpassed' else {'source_sha256': '0' * 64})
        gate.write_text(json.dumps(value)); plan['fixture_gate_sha256'] = hashlib.sha256(gate.read_bytes()).hexdigest()
    elif change == 'changed-file': (Path(plan['source_root']) / 'runner.py').write_text('changed')
    else:
        original = Path(plan['source_root']) / 'runner.py'; target = original.with_name('real.py'); original.rename(target); original.symlink_to(target)
    with pytest.raises(RehearsalRefused): freeze_source(plan, root)
    assert not (root / 'source').exists()


def test_unknown_runner_send_keeps_original_claim_and_never_sends_again(tmp_path):
    value = budget(tmp_path); run = Rehearsal.__new__(Rehearsal); run.root = value.root; run.budget = value
    run.validate_review = lambda _: None; run.context = lambda _: {}; calls = []
    def fail(*args): calls.append(args); raise TimeoutError('fixture timeout')
    run.operator = fail
    review = {'operation_id': identity(), 'client_nonce': identity(), 'review_digest': 'a' * 64, 'revision': 1}
    path = value.root / 'review.json'; write_new(path, review)
    with pytest.raises(TimeoutError): run.approve_once('border0', path)
    with pytest.raises(RehearsalRefused): run.approve_once('border1', path)
    assert len(calls) == 1 and value.snapshot()['reservations'][0]['state'] == 'unknown'
    assert value.snapshot()['reservations'][0]['claim']['operation_id'] == review['operation_id']


def test_external_publication_claims_send_before_file_becomes_visible(tmp_path):
    value = budget(tmp_path); run = Rehearsal.__new__(Rehearsal); run.root = value.root; run.budget = value
    run.validate_review = lambda _: None
    review = {'operation_id': identity(), 'client_nonce': identity(), 'review_digest': 'a' * 64}
    path = value.root / 'review.json'; write_new(path, review); destination = value.root / 'claim.json'
    run.publish_claim(path, 'mobile', destination)
    assert value.snapshot()['reservations'][0]['sender'] == 'mobile'
    assert value.snapshot()['reservations'][0]['state'] == 'send_claimed'
    assert json.loads(destination.read_bytes()) == value.snapshot()['reservations'][0]['claim']


def test_help_performs_no_runtime_import_or_action():
    result = subprocess.run([sys.executable, '-S', '-B', '-m', 'labs.ha.real_runtime', '--help'],
                            cwd=SOURCE, capture_output=True, timeout=5)
    assert result.returncode == 0 and b'export-operation' in result.stdout


def evidence_run(tmp_path):
    value = budget(tmp_path)
    run = Rehearsal.__new__(Rehearsal)
    run.root, run.budget, run.source = value.root, value, SOURCE
    run.plan = {'run_id': value.run_id, 'source_sha256': 'c' * 64}
    runtime = value.root / 'homes/member/netclaw-federation/runtime'
    runtime.mkdir(parents=True, mode=0o700)
    for parent in runtime.parents:
        if parent == value.root: break
        parent.chmod(0o700)
    claim = reserve(value); value.claim_send(claim, surface='runner')
    write_new(value.root / 'claim.json', claim)
    path = runtime / 'inference.sqlite'
    write_new(path, b'')
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE protected_inference(operation_id TEXT, ordinal INTEGER, state TEXT, request_sha256 TEXT, response_sha256 TEXT)')
        db.execute('INSERT INTO protected_inference VALUES(?,1,?,?,NULL)', (claim['operation_id'], 'claimed', 'd' * 64))
    return run, claim, runtime


def test_claimed_inference_and_native_intent_are_not_actual_call_counters(tmp_path):
    from labs.ha.real_evidence import execution_evidence
    run, claim, runtime = evidence_run(tmp_path)
    tool = runtime / claim['operation_id'] / 'tool'; tool.mkdir(parents=True, mode=0o700)
    tool.parent.chmod(0o700)
    write_new(tool / 'mcp-call.json', {'state': 'intent_prepared', 'tool': 'subnet_calculator'})
    observed = execution_evidence(run.root, claim['operation_id'])
    assert observed['inference_claims']['total'] == 1
    assert observed['inference_claims']['finished_responses'] == 0
    assert observed['actual_effect_totals'] == {'model_forwards': None, 'native_handoffs': None}
    assert observed['operation_artifacts']['tool/mcp-call.json']['value']['state'] == 'intent_prepared'
    assert observed['independent_counter_artifacts']['model']['available'] is False


def test_unknown_export_survives_missing_ack_and_quorum_without_releasing_slot(tmp_path):
    run, claim, runtime = evidence_run(tmp_path)
    run._consensus_evidence = lambda: {'available': False, 'reason': 'no_quorum'}
    destination = run.root / 'unknown-export'
    result = run.export_unknown(run.root / 'claim.json', destination)
    packet = json.loads((destination / 'packet.json').read_bytes())
    assert result['successful_native_workload'] is False
    assert packet['original_ids'] == {k: claim[k] for k in ('operation_id', 'client_nonce', 'review_digest')}
    assert packet['result_available'] is False and packet['ack_available'] is False
    assert packet['actual_effect_totals'] == {'model_forwards': None, 'native_handoffs': None}
    assert packet['globally_consistent_snapshot'] is False and packet['full_matrix_qualified'] is False
    assert json.loads((destination / 'execution-evidence.json').read_bytes())['journals']['inference']['available'] is True
    assert run.budget.snapshot()['reservations'][0]['state'] == 'unknown'
    with pytest.raises(RehearsalRefused, match='unresolved'):
        reserve(run.budget, 'mobile')


def test_unknown_export_retains_consensus_claims_and_rejects_wrong_operation(tmp_path):
    run, claim, runtime = evidence_run(tmp_path)
    row = {'operation_id': claim['operation_id'], 'client_nonce': claim['client_nonce'],
           'review_digest': claim['review_digest'], 'attempt_id': identity(), 'state': 'outcome_unknown',
           'approval': None, 'ack': None}
    records = {'operations/' + claim['operation_id']: {'value': row, 'mod_revision': 7},
               'resources/held': {'value': {'state': 'reserved', 'operation_id': claim['operation_id']}, 'mod_revision': 7},
               'claims/' + claim['operation_id'] + '/model1': {'value': {'state': 'committed'}, 'mod_revision': 8}}
    run._consensus_evidence = lambda: {'available': True, 'snapshot': {'records': records}}
    run.export_unknown(run.root / 'claim.json', run.root / 'snapshot-export')
    assert json.loads((run.root / 'snapshot-export/consensus-evidence.json').read_bytes())['snapshot']['records'] == records
    row['operation_id'] = identity()
    with pytest.raises(RehearsalRefused, match='original_operation_mismatch'):
        run.export_unknown(run.root / 'claim.json', run.root / 'bad-export')
    assert run.budget.snapshot()['reservations'][0]['state'] == 'unknown'


def test_counter_observations_are_copied_but_do_not_assert_measured_totals(tmp_path):
    from labs.ha.real_evidence import execution_evidence
    run, claim, _ = evidence_run(tmp_path)
    directory = private_directory(run.root / 'counter-observations', create=True)
    # Even plausible caller-provided values are observations, not proof of sends.
    write_new(directory / 'model.json', {'actual_calls': 0, 'at_ms': 1})
    observed = execution_evidence(run.root, claim['operation_id'])
    artifact = observed['independent_counter_artifacts']['model']
    assert artifact['available'] is True and artifact['value']['actual_calls'] == 0
    assert artifact['interpretation'] == 'unverified_observation'
    assert observed['actual_effect_totals']['model_forwards'] is None


def test_evidence_reads_committed_wal_rows_without_changing_execution_state(tmp_path):
    from labs.ha.real_evidence import execution_evidence
    run, claim, runtime = evidence_run(tmp_path)
    db = sqlite3.connect(runtime / 'inference.sqlite')
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute("UPDATE protected_inference SET state='finished',response_sha256=?", ('e' * 64,))
        db.commit()
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE protected_inference SET state='uncommitted-change'")
        observed = execution_evidence(run.root, claim['operation_id'])
        assert observed['inference_claims']['finished_responses'] == 1
        assert observed['actual_effect_totals']['model_forwards'] is None
        assert db.execute('SELECT state FROM protected_inference').fetchone()[0] == 'uncommitted-change'
        db.rollback()
        assert db.execute('SELECT state FROM protected_inference').fetchone()[0] == 'finished'
    finally:
        db.close()


def test_unknown_export_failure_does_not_release_budget(tmp_path):
    from labs.ha.real_evidence import execution_evidence
    run, claim, runtime = evidence_run(tmp_path)
    directory = private_directory(run.root / 'counter-observations', create=True)
    (directory / 'model.json').symlink_to(run.root / 'claim.json')
    with pytest.raises(RehearsalRefused, match='private_path_required'):
        run.export_unknown(run.root / 'claim.json', run.root / 'refused-export')
    assert run.budget.snapshot()['reservations'][0]['state'] == 'unknown'
    assert not (run.root / 'refused-export').exists()
