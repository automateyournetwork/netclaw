"""Source-only checks for the default-off REAL fenced-restore driver. No Docker, process or model."""
import copy
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from labs.ha import real_restore as rr
from labs.ha.real_budget import Budget, RehearsalRefused, private_directory, write_new
from labs.ha.etcd_lab import IMAGE, EtcdLab


def test_import_and_plan_are_inert(monkeypatch, capsys):
    def refused(*a, **k): raise AssertionError('process launched')
    monkeypatch.setattr(subprocess, 'run', refused)
    monkeypatch.setattr(subprocess, 'Popen', refused)
    assert rr.main(['plan']) == 0
    assert json.loads(capsys.readouterr().out)['phases'] == list(rr.PHASES)
    with pytest.raises(SystemExit):
        rr.main(['--help'])


def record(state, **extra): return {'value': {'state': state, **extra}, 'revision': 1}


def snapshots():
    from bgp.federation.ha.operations import reservation_keys
    review = {'member': {'installation_id': str(uuid.uuid4()), 'member_id': 'm'}, 'model_profile': {'profile_id': 'p'}}
    keys = reservation_keys(review); a, b = str(uuid.uuid4()), str(uuid.uuid4())
    stale = {'revision': 10, 'records': {'operations/' + a: record('completed'),
             **{k: record('released', operation_id=a) for k in keys}}}
    later = {'revision': 15, 'records': {'operations/' + a: record('completed'),
             'operations/' + b: record('dispatch_claimed', attempt_id=str(uuid.uuid4()), review=review),
             **{k: record('reserved', operation_id=b) for k in keys}}}
    return stale, later, a, b


def test_real_gap_accepts_unknown_without_committed_claim_and_reports_missing_evidence():
    stale, later, a, b = snapshots()
    gap = rr.real_stale_gap(stale, later, a, b)
    assert gap['missing_claim_keys'] == [] and gap['later_state'] == 'dispatch_claimed'
    assert len(gap['changed_resource_keys']) == 2 and gap['missing_evidence_recovered'] is False
    later['records']['claims/x'] = {'value': {'request': {'operation_id': b}}, 'revision': 2}
    assert rr.real_stale_gap(stale, later, a, b)['missing_claim_keys'] == ['claims/x']


@pytest.mark.parametrize('fault', ['b_in_stale', 'b_terminal', 'a_not_completed', 'still_released', 'no_new_revision', 'a_equals_b'])
def test_real_gap_rejects_genuine_gap_violations(fault):
    stale, later, a, b = snapshots()
    if fault == 'b_in_stale': stale['records']['operations/' + b] = record('review_pending')
    elif fault == 'b_terminal': later['records']['operations/' + b]['value']['state'] = 'completed'
    elif fault == 'a_not_completed': stale['records']['operations/' + a]['value']['state'] = 'dispatch_claimed'
    elif fault == 'still_released':
        for k, r in later['records'].items():
            if k.startswith('resources/'): r['value']['state'] = 'released'
    elif fault == 'no_new_revision': later['revision'] = 10
    else: b = a
    with pytest.raises(RehearsalRefused):
        rr.real_stale_gap(stale, later, a, b)


def test_counter_comparison_requires_unchanged_integer_counts():
    assert rr.compare_counters({'request_count': 7}, {'request_count': 7})['unchanged'] is True
    with pytest.raises(RehearsalRefused, match='model_counter_changed'):
        rr.compare_counters({'request_count': 7}, {'request_count': 8})
    with pytest.raises(RehearsalRefused, match='counter_observation_invalid'):
        rr.compare_counters({'request_count': '7'}, {'request_count': 7})


def fake_docker(rows):
    def docker(args):
        if args[0] == 'ps': return ' '.join(r['Id'] for r in rows).encode()
        return json.dumps(rows).encode()
    return docker


def voter(i): return {'Id': str(i) * 64, 'Name': f'/v{i}', 'Config': {'Image': IMAGE, 'Cmd': ['/usr/local/bin/etcd'], 'Labels': {'netclaw.spec': '179'}}}


def model(owner): return {'Id': 'a' * 64, 'Name': f'/{owner}-model', 'Config': {'Image': 'ollama', 'Cmd': [], 'Labels': {'netclaw.spec': '179', 'netclaw.owner': owner}}}


def test_voter_cap_tolerates_only_this_runs_model_container():
    owner = 'netclaw-r08-abcdef'; rows = [voter(1), voter(2), voter(3), model(owner)]
    ids = [r['Id'] for r in rows[:3]]
    assert rr.real_running_voters(ids, owner, fake_docker(rows)) == rows
    stranger = model('netclaw-r08-other'); stranger['Name'] = '/other-model'
    with pytest.raises(RehearsalRefused, match='unreviewed_running'):
        rr.real_running_voters(ids, owner, fake_docker(rows[:3] + [stranger]))
    with pytest.raises(RehearsalRefused, match='global_voter_bound'):
        rr.real_running_voters([], owner, fake_docker(rows))
    assert rr.real_running_voters([], owner, fake_docker([model(owner)])) is not None


def test_export_manifest_requires_private_absolute_files_and_bound(tmp_path):
    d = private_directory(tmp_path / 'p', create=True); f = d / 'a.json'; write_new(f, {'x': 1})
    manifest = rr.collect_exports([f, f])
    assert len(manifest['artifacts']) == 1 and manifest['artifacts'][0]['path'] == str(f)
    loose = d / 'loose'; loose.write_text('x'); os.chmod(loose, 0o644)
    with pytest.raises(RehearsalRefused, match='private_file_required'): rr.collect_exports([loose])
    with pytest.raises(RehearsalRefused, match='invalid_export_manifest'): rr.collect_exports(['relative'])
    with pytest.raises(RehearsalRefused, match='export_artifact_capacity'): rr.collect_exports([])


def test_sqlite_backup_is_new_only_and_includes_committed_wal_rows(tmp_path):
    d = private_directory(tmp_path / 'p', create=True); src = d / 'j.sqlite3'
    db = sqlite3.connect(src); db.execute('PRAGMA journal_mode=WAL'); db.execute('CREATE TABLE t(x)'); db.execute('INSERT INTO t VALUES (1)'); db.commit()
    os.chmod(src, 0o600)
    out = d / 'copy.sqlite3'; rr.backup_sqlite(src, out); db.close()
    assert sqlite3.connect(out).execute('SELECT x FROM t').fetchall() == [(1,)]
    with pytest.raises(FileExistsError): rr.backup_sqlite(src, out)


@pytest.fixture
def run(tmp_path):
    """A run-shaped root: old voters + offline identity. No process, no Docker."""
    rr._paths()
    root = private_directory(tmp_path.resolve() / 'run', create=True)
    old = EtcdLab(root / 'voters').prepare(); old.prepare_cluster_identity(organization='r08-real-restore-test')
    value = rr.Restore.__new__(rr.Restore)
    value.root, value.R = root, root / 'restore'
    value.plan = {'name': 'netclaw-r08-abcdef', 'run_id': str(uuid.uuid4()), 'source_sha256': 'a' * 64, 'ports': {'cluster': [1]}, 'root': str(root)}
    value.docker, value._observe_process = rr.docker_read, None
    return value


def test_prepare_is_offline_fresh_generation_same_anchor_and_one_shot(run, monkeypatch):
    def refused(*a, **k): raise AssertionError('offline prepare launched a process')
    monkeypatch.setattr(subprocess, 'run', refused); monkeypatch.setattr(subprocess, 'Popen', refused)
    result = run.prepare()
    plan = json.loads((run.R / 'plan.json').read_text())
    old, new = EtcdLab(run.root / 'voters').load(), EtcdLab(run.R / 'new-voters').load()
    om, nm = run.manifest(old), run.manifest(new)
    assert result['class'] == 'PLAN_ONLY' and result['running_resources_created'] == 0 and plan['limits']['budget_reservations'] == 0
    assert om.cluster_id == nm.cluster_id and om.generation != nm.generation and om.anchor_key_id == nm.anchor_key_id
    assert not (new.root / 'cluster-identity/root.key').exists()
    assert not {n['node_id'] for n in om.nodes} & {n['node_id'] for n in nm.nodes}
    assert old.document['name'] != new.document['name'] and (run.R / 'host/host.key').stat().st_mode & 0o077 == 0
    with pytest.raises(RehearsalRefused, match='restore_already_prepared'): run.prepare()


def test_phase_requires_hash_pins_predecessor_and_keeps_claim_without_retry(run):
    plan_hash = run.prepare()['plan_sha256']
    with pytest.raises(RehearsalRefused, match='reviewed_plan_changed'): run.run_phase('capture', 'f' * 64)
    run.run_phase('capture', plan_hash) if False else None
    with pytest.raises(RehearsalRefused, match='unknown_restore_phase'): run.run_phase('prepare', plan_hash)
    with pytest.raises(FileNotFoundError): run.run_phase('isolate', plan_hash)  # predecessor (exports chain) missing
    assert not (run.R / 'isolate.claim.json').exists()
    # capture's predecessor (prepare) is complete; make it fail and prove the claim is retained and not replayable.
    def boom(): raise RuntimeError('controlled')
    run.phase_capture = boom
    with pytest.raises(RuntimeError): run.run_phase('capture', plan_hash)
    assert (run.R / 'capture.claim.json').exists() and (run.R / 'capture.failed.json').exists()
    assert not (run.R / 'capture.complete.json').exists()
    with pytest.raises(FileExistsError): run.run_phase('capture', plan_hash)


def test_changed_prepared_input_is_refused_for_every_phase(run):
    plan_hash = run.prepare()['plan_sha256']
    (run.R / 'new-voters/cluster-identity/node0.key').chmod(0o600)
    with open(run.R / 'new-voters/cluster-identity/node0.key', 'ab') as f: f.write(b'x')
    with pytest.raises(RehearsalRefused, match='prepared_input_changed'): run.run_phase('capture', plan_hash)
    assert not (run.R / 'capture.claim.json').exists()


def test_isolate_refuses_without_pre_isolation_model_evidence_and_with_live_old_process(run):
    plan_hash = run.prepare()['plan_sha256']
    for name in ('capture', 'snapshot', 'gap'): write_new(run.R / (name + '.complete.json'), {})
    with pytest.raises(RehearsalRefused, match='pre_isolation_model_evidence_required'): run.run_phase('isolate', plan_hash)
    assert (run.R / 'isolate.claim.json').exists()  # one-shot: the refusal retains its claim, no retry
    (run.R / 'isolate.claim.json').unlink(); (run.R / 'isolate.failed.json').unlink()  # test-only: re-enter the next check
    write_new(run.R / 'counters/model-before.json', {'request_count': 4}); write_new(run.R / 'pre-isolation/model-access.log', b'log')
    write_new(run.R / 'isolation/owned-inventory.json', {'subjects': [{'kind': 'process', 'pid': 4242}]})
    run._observe_process = lambda pid: {'present': True}
    with pytest.raises(RehearsalRefused, match='old_processes_still_running'): run.run_phase('isolate', plan_hash)
    assert (run.R / 'isolate.failed.json').exists()


def test_gap_phase_requires_exactly_one_settled_and_one_unknown_budget_row(run):
    plan_hash = run.prepare()['plan_sha256']
    write_new(run.R / 'capture.complete.json', {}); write_new(run.R / 'snapshot.complete.json', {})
    budget = Budget(run.root, run_id=run.plan['run_id'], create=True)
    nonce = lambda: str(uuid.uuid4())
    a = budget.reserve(operation_id=nonce(), client_nonce=nonce(), review_digest='a' * 64, surface='runner')
    budget.claim_send(a, surface='runner'); budget.settle(a, receipt_sha256='b' * 64, inferences=2, native_effects=1)
    write_new(run.root / 'a.claim.json', a)
    with pytest.raises(RehearsalRefused, match='budget_must_show'):
        run.run_phase('gap', plan_hash, first_claim_file=run.root / 'a.claim.json',
                      unknown_claim_file=run.root / 'a.claim.json', later_evidence_file=run.root / 'a.claim.json')
