"""Real SQLite recovery/rebind durability; host proofs are explicitly test fixtures."""
import asyncio
import copy
import json
import sqlite3
import uuid

import pytest

from protected_support_171 import module, runtime_module
from test_protected_ollama_176 import payload, request

ollama = module('protected_ollama')
OLD, NEW, NEXT = 'a' * 64, 'b' * 64, 'c' * 64


def receipt(latch, new=NEW):
    return {'operation': str(uuid.uuid4()), 'old_profile_sha256': latch.profile_sha256,
            'new_profile_sha256': new, 'prior_state': latch.snapshot(),
            'fixture_owned_processes_stopped': True}


def rows(latch, table):
    return [dict(row) for row in latch.db.execute('SELECT * FROM ' + table)]


def verified(value, previous, new):
    return (value['fixture_owned_processes_stopped'] is True
            and value['prior_state'] == previous and value['new_profile_sha256'] == new)


def test_real_uncertain_inference_recovery_and_rebind_preserve_claim_and_history(tmp_path):
    runtime = runtime_module()
    fence = runtime.InferenceFence(tmp_path / 'inference.sqlite')
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    approved, calls = payload(), []

    async def forward(body):
        calls.append(body)
        raise TimeoutError('fixture provider reply lost')

    scoped = runtime.ScopedInference(approved, 'token', fence, forward, runner_latch=latch)
    async def invoke():
        with pytest.raises(runtime.RuntimeUnknown):
            await scoped.invoke('POST', '/v1/chat/completions',
                                {'authorization': 'Bearer token'}, request(approved))
    asyncio.run(invoke())
    uncertain = latch.snapshot()
    inference = [tuple(row) for row in fence.db.execute('SELECT * FROM protected_inference')]
    recovery_receipt = {'prior_state': uncertain, 'fixture_stopped_container_id': 'd' * 64}
    recovery = latch.recover(recovery_receipt, verify=lambda value, old: value['prior_state'] == old)
    recovered = latch.snapshot()
    history = rows(latch, 'runner_recovery')
    transition_receipt = receipt(latch)
    checksum = latch.rebind(NEW, transition_receipt, verify=verified)
    after = latch.snapshot()
    assert checksum == ollama.digest(transition_receipt)
    assert after == {**recovered, 'profile_sha256': NEW, 'updated_ms': after['updated_ms']}
    assert after['operation_id'] == approved['operation_id']
    assert after['reservation_id'] == uncertain['reservation_id']
    assert after['recovery_sha256'] == recovery
    assert rows(latch, 'runner_recovery') == history
    transition = rows(latch, 'runner_profile_transition')
    assert len(transition) == 1 and transition[0]['receipt_sha256'] == checksum
    assert json.loads(transition[0]['prior_state_json']) == recovered
    assert json.loads(transition[0]['receipt_json']) == transition_receipt
    assert [tuple(row) for row in fence.db.execute('SELECT * FROM protected_inference')] == inference
    # Rebinding a model profile does not grant another attempt of the old claim.
    async def retry():
        with pytest.raises(runtime.RuntimeRefused):
            await scoped.invoke('POST', '/v1/chat/completions',
                                {'authorization': 'Bearer token'}, request(approved))
    asyncio.run(retry())
    assert len(calls) == 1 and fence.count(approved['operation_id']) == 1
    latch.close()
    reopened = ollama.RunnerLatch(tmp_path / 'runner.sqlite', NEW)
    assert reopened.snapshot() == after
    assert rows(reopened, 'runner_profile_transition') == transition
    with pytest.raises(ollama.OllamaRefused, match='profile_changed'):
        ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    reopened.close()
    fence.close()


def test_idle_transition_retains_unclaimed_fields_and_appends_each_verified_change(tmp_path):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    original = latch.snapshot()
    one = receipt(latch)
    latch.rebind(NEW, one, verify=verified)
    two = receipt(latch, NEXT)
    latch.rebind(NEXT, two, verify=verified)
    history = rows(latch, 'runner_profile_transition')
    assert [(row['old_profile_sha256'], row['new_profile_sha256']) for row in history] == [(OLD, NEW), (NEW, NEXT)]
    assert json.loads(history[0]['prior_state_json']) == original
    assert json.loads(history[0]['receipt_json']) == one
    assert all(latch.snapshot()[key] is None for key in ('operation_id', 'reservation_id', 'recovery_sha256'))
    assert rows(latch, 'runner_recovery') == []
    latch.close()


@pytest.mark.parametrize('state', ['in_flight', 'uncertain'])
def test_active_or_uncertain_latch_cannot_rebind_even_with_true_verifier(tmp_path, state):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    reservation = latch.begin(str(uuid.uuid4()), 'd' * 64)
    if state == 'uncertain':
        latch.uncertain(reservation)
    before, calls = latch.snapshot(), []
    with pytest.raises(ollama.OllamaRefused, match='verified_profile_transition'):
        latch.rebind(NEW, receipt(latch), verify=lambda *args: calls.append(args) or True)
    assert latch.snapshot() == before and latch.profile_sha256 == OLD and calls == []
    assert rows(latch, 'runner_profile_transition') == []
    latch.close()


@pytest.mark.parametrize('value', [None, '', 'A' * 64, 'a' * 63, 'g' * 64, True])
def test_invalid_new_profile_digest_refuses_without_state_change(tmp_path, value):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    before = latch.snapshot()
    with pytest.raises(ollama.OllamaRefused, match='digest_invalid'):
        latch.rebind(value, receipt(latch), verify=lambda *_: True)
    assert latch.snapshot() == before and rows(latch, 'runner_profile_transition') == []
    latch.close()


@pytest.mark.parametrize('mutation', [
    lambda value: value.update(old_profile_sha256='f' * 64),
    lambda value: value.update(new_profile_sha256='f' * 64),
    lambda value: value['prior_state'].update(updated_ms=0),
    lambda value: value['prior_state'].update(operation_id=str(uuid.uuid4())),
    lambda value: value.pop('old_profile_sha256'),
    lambda value: value.pop('new_profile_sha256'),
    lambda value: value.pop('prior_state'),
])
def test_receipt_must_independently_bind_exact_old_new_and_prior_state(tmp_path, mutation):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    before, value, called = latch.snapshot(), receipt(latch), []
    mutation(value)
    with pytest.raises(ollama.OllamaRefused, match='verified_profile_transition'):
        latch.rebind(NEW, value, verify=lambda *args: called.append(args) or True)
    assert not called and latch.snapshot() == before and rows(latch, 'runner_profile_transition') == []
    latch.close()


@pytest.mark.parametrize('value', [None, [], 'receipt', {}])
def test_missing_or_wrong_receipt_type_cannot_rebind(tmp_path, value):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    before = latch.snapshot()
    with pytest.raises(ollama.OllamaRefused, match='verified_profile_transition'):
        latch.rebind(NEW, value, verify=lambda *_: True)
    assert latch.snapshot() == before and rows(latch, 'runner_profile_transition') == []
    latch.close()


@pytest.mark.parametrize('answer', [False, None, 1, 'true'])
def test_only_literal_verified_true_allows_rebind(tmp_path, answer):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    before = latch.snapshot()
    with pytest.raises(ollama.OllamaRefused, match='verified_profile_transition'):
        latch.rebind(NEW, receipt(latch), verify=lambda *_: answer)
    assert latch.snapshot() == before and rows(latch, 'runner_profile_transition') == []
    latch.close()


@pytest.mark.parametrize('which', ['receipt', 'prior'])
def test_verifier_cannot_replace_the_evidence_being_recorded(tmp_path, which):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    before, value = latch.snapshot(), receipt(latch)
    original = copy.deepcopy(value)
    def changed(selected, prior, new):
        (selected if which == 'receipt' else prior)['injected'] = True
        return True
    with pytest.raises(ollama.OllamaRefused, match='verified_profile_transition'):
        latch.rebind(NEW, value, verify=changed)
    assert value == original and latch.snapshot() == before
    assert rows(latch, 'runner_profile_transition') == []
    latch.close()


def test_failed_profile_write_rolls_back_history_and_object_binding(tmp_path):
    latch = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    before = latch.snapshot()
    latch.db.execute("""CREATE TRIGGER fail_profile_update BEFORE UPDATE OF profile_sha256 ON runner_latch
        BEGIN SELECT RAISE(ABORT, 'fixture write failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match='fixture write failure'):
        latch.rebind(NEW, receipt(latch), verify=verified)
    assert latch.profile_sha256 == OLD and latch.snapshot() == before
    assert rows(latch, 'runner_profile_transition') == []
    latch.close()
    reopened = ollama.RunnerLatch(tmp_path / 'runner.sqlite', OLD)
    assert reopened.snapshot() == before
    reopened.close()


def test_same_profile_and_stale_object_cannot_transition_or_admit(tmp_path):
    path = tmp_path / 'runner.sqlite'
    latch, stale = ollama.RunnerLatch(path, OLD), ollama.RunnerLatch(path, OLD)
    before = latch.snapshot()
    with pytest.raises(ollama.OllamaRefused, match='verified_profile_transition'):
        latch.rebind(OLD, receipt(latch, OLD), verify=verified)
    assert latch.snapshot() == before
    old_receipt = receipt(stale, NEXT)
    latch.rebind(NEW, receipt(latch), verify=verified)
    with pytest.raises(ollama.OllamaRefused, match='profile_changed'):
        stale.rebind(NEXT, old_receipt, verify=lambda *_: True)
    with pytest.raises(ollama.OllamaRefused, match='profile_changed'):
        stale.begin(str(uuid.uuid4()), 'd' * 64)
    assert latch.snapshot()['state'] == 'idle'
    assert len(rows(latch, 'runner_profile_transition')) == 1
    latch.close()
    stale.close()


def test_existing_database_upgrade_preserves_prior_recovery_rows(tmp_path):
    path = tmp_path / 'runner.sqlite'
    latch = ollama.RunnerLatch(path, OLD)
    reservation = latch.begin(str(uuid.uuid4()), 'd' * 64)
    latch.uncertain(reservation)
    latch.recover({'fixture_stopped': True}, verify=lambda *_: True)
    before, history = latch.snapshot(), rows(latch, 'runner_recovery')
    # Reconstruct the pre-rebind schema without altering its existing authority.
    latch.db.execute('DROP TABLE runner_profile_transition')
    latch.close()
    reopened = ollama.RunnerLatch(path, OLD)
    assert reopened.snapshot() == before and rows(reopened, 'runner_recovery') == history
    assert rows(reopened, 'runner_profile_transition') == []
    reopened.close()
