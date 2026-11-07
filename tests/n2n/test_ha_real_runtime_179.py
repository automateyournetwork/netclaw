"""Source-only qualification safeguards; no model, daemon or Docker startup."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
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
