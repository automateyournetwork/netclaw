"""Independent full-message lifecycle and real process-kill durability tests."""

import asyncio
import multiprocessing
import os

import pytest

from protected_support_171 import NOW, OperationPair, module, runtime_module
from test_protected_claims_171 import create_admitted


def test_lost_submit_reply_reconciles_original_execution_without_resubmit(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        pair.drop_submit_reply = True
        initial = await pair.decide(prepared)
        assert initial["state"] == "reconciliation_required"
        await pair.drain()
        result = await pair.reconcile(prepared["operation_id"])
        assert result["state"] == "completed"
        assert result["result"]["verified"] and result["result"]["durable_ack"]
        assert len(pair.effects) == pair.executor_calls == 1
        assert [method for method, _ in pair.transport_calls].count("execution/submit") == 1
        repeated = await pair.decide(prepared)
        assert repeated["operation_id"] == prepared["operation_id"]
        assert [method for method, _ in pair.transport_calls].count("execution/submit") == 1
    asyncio.run(run())


def test_lost_ack_reply_and_restart_preserve_receipt_ack_and_effect(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        pair.drop_ack_reply = True
        first = await pair.reconcile(prepared["operation_id"])
        assert first["state"] == "completed" and first["result"]["ack_delivery_pending"]
        old = pair.border.store.get("border", prepared["operation_id"])
        await pair.restart()
        pair.drop_ack_reply = False
        recovered = await pair.reconcile(prepared["operation_id"])
        new = pair.border.store.get("border", prepared["operation_id"])
        assert recovered["state"] == "completed" and not recovered["result"]["ack_delivery_pending"]
        assert new["receipt"] == old["receipt"] and new["ack"] == old["ack"]
        assert len(pair.effects) == pair.executor_calls == 1
        assert [method for method, _ in pair.transport_calls].count("execution/submit") == 1
    asyncio.run(run())


def test_unknown_submit_with_no_member_record_is_never_resent(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        sent = []
        async def lost_before_response(member, method, params):
            sent.append(method)
            if method == "execution/submit":
                raise ConnectionError("cannot know if peer admitted")
            raise module("protected_contract").ProtectedError("operation_not_found", 404)
        pair.border.transport = lost_before_response
        prepared = await pair.prepare()
        await pair.decide(prepared)
        result = await pair.reconcile(prepared["operation_id"])
        assert result["reconciliation_required"]
        assert sent.count("execution/submit") == 1
        assert len(pair.effects) == pair.executor_calls == 0
    asyncio.run(run())


def test_altered_member_result_cannot_become_completed(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        pair.mutate_receipt = lambda envelope: envelope["payload"].update(output={"forged": True})
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.reconcile(prepared["operation_id"])
        row = pair.border.store.get("border", prepared["operation_id"])
        assert row["state"] != "completed" and row["ack"] is None
        pair.mutate_receipt = None
        assert (await pair.reconcile(prepared["operation_id"]))["state"] == "completed"
        assert len(pair.effects) == 1
    asyncio.run(run())


def test_concurrent_reconciliation_converges_on_one_immutable_receipt_and_ack(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        results = await asyncio.gather(*(pair.reconcile(prepared["operation_id"]) for _ in range(8)))
        assert all(result["state"] == "completed" for result in results)
        assert len({result["result"]["digest"] for result in results}) == 1
        acknowledgements = [params["ack"] for method, params in pair.transport_calls if method == "execution/ack"]
        assert acknowledgements and all(ack == acknowledgements[0] for ack in acknowledgements)
        assert pair.executor_calls == len(pair.effects) == 1
    asyncio.run(run())


def test_unknown_provider_outcome_is_not_signed_as_known_refusal(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        pair.executor_error = runtime_module().RuntimeUnknown("inference_outcome_unknown")
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        row = pair.member.store.get("member", prepared["operation_id"])
        assert row["state"] == "outcome_unknown"
        assert row["receipt"] is None
        await pair.restart()
        await pair.reconcile(prepared["operation_id"])
        assert pair.executor_calls == 1 and pair.effects == []
    asyncio.run(run())


def crash_after_claim(db, operation, phase, effect_file):
    store = module("protected_store").ProtectedStore(db)
    store.claim_executor(operation, NOW)
    if phase != "executor":
        store.claim_effect(operation, {"fixture": "authorized"})
    if phase == "effect":
        descriptor = os.open(effect_file, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        os.write(descriptor, b"one synthetic effect\n")
        os.fsync(descriptor)
        os.close(descriptor)
    os._exit(91)  # No Python cleanup: simulate process death after durable claim/effect.


@pytest.mark.parametrize("phase", ["executor", "effect_claim", "effect"])
def test_actual_process_death_never_releases_original_claim(tmp_path, phase):
    db = tmp_path / "private" / "federation.db"
    store, original, _ = create_admitted(db)
    effect = tmp_path / "fixture-effects"
    child = multiprocessing.get_context("spawn").Process(target=crash_after_claim,
        args=(str(db), original["operation_id"], phase, str(effect)))
    child.start()
    child.join(timeout=20)
    try:
        assert child.exitcode == 91
        restarted = module("protected_store").ProtectedStore(db)
        restarted.recover()
        row = restarted.get("member", original["operation_id"])
        assert row["state"] == "outcome_unknown" and row["attempt_id"]
        assert row["approval_digest"] == original["approval_digest"]
        with pytest.raises(module("protected_contract").ProtectedError):
            restarted.claim_executor(original["operation_id"], NOW + 1)
        with pytest.raises(module("protected_contract").ProtectedError):
            restarted.claim_effect(original["operation_id"], {})
        assert effect.read_bytes() == b"one synthetic effect\n" if phase == "effect" else not effect.exists()
    finally:
        if child.is_alive():
            child.terminate()
            child.join(timeout=5)
