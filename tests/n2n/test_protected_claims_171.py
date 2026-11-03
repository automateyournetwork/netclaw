"""Separate-process durable-claim tests. Counters represent fixture effects only."""

import copy
import multiprocessing
import os
from pathlib import Path
import traceback
import uuid

import pytest

from protected_support_171 import APPROVAL, NOW, approval, identity, module, wire_sign


def create_admitted(db_path):
    border, member = identity("border"), identity("member")
    payload = approval(border, member)
    store = module("protected_store").ProtectedStore(db_path)
    review = {key: payload[key] for key in (
        "principal", "border", "member", "model_profile", "tool_call", "limits", "change_request_ref")}
    row = store.create("member", payload["operation_id"],
        owner_subject=payload["principal"]["subject"], review=review,
        review_digest=payload["review_sha256"], trust_snapshot={"certificate": border["cert_pem"]},
        state="admitted", approval=wire_sign(APPROVAL, payload, border))
    return store, row, payload


def claim_worker(db_path, operation_id, kind, ready, start, answers):
    try:
        store = module("protected_store").ProtectedStore(db_path)
        ready.put(os.getpid())
        if not start.wait(15):
            raise RuntimeError("independent test barrier timed out")
        if kind == "executor":
            result = store.claim_executor(operation_id, NOW)
            answers.put(("winner", result["attempt_id"]))
        elif kind == "effect":
            result = store.claim_effect(operation_id, {"fixture": "authorization"})
            answers.put(("winner", result["attempt_id"]))
        else:
            answers.put(("winner", store.claim_model_call(operation_id, NOW)))
    except module("protected_contract").ProtectedError as exc:
        answers.put(("refused", exc.code))
    except BaseException:
        answers.put(("test_error", traceback.format_exc()))


def race(db_path, operation_id, kind, count=8):
    context = multiprocessing.get_context("spawn")
    ready, answers, start = context.Queue(), context.Queue(), context.Event()
    processes = [context.Process(target=claim_worker,
        args=(str(db_path), operation_id, kind, ready, start, answers)) for _ in range(count)]
    try:
        for process in processes:
            process.start()
        for _ in processes:
            ready.get(timeout=20)
        start.set()
        results = [answers.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0
        assert not [item for item in results if item[0] == "test_error"], results
        return results
    finally:
        start.set()
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)


@pytest.mark.parametrize("kind,winners", [("executor", 1), ("effect", 1), ("model", 2)])
def test_independent_processes_cannot_multiply_claims(tmp_path, kind, winners):
    db = tmp_path / "private" / "federation.db"
    store, row, _ = create_admitted(db)
    operation = row["operation_id"]
    if kind != "executor":
        store.claim_executor(operation, NOW)
    results = race(db, operation, kind)
    accepted = [value for status, value in results if status == "winner"]
    assert len(accepted) == winners
    assert len([item for item in results if item[0] == "refused"]) == 8 - winners
    if kind == "model":
        assert sorted(accepted) == [1, 2]
    else:
        assert store.get("member", operation)["attempt_id"] == accepted[0]


def test_reused_nonce_or_approval_id_cannot_create_another_operation(tmp_path):
    store, original, payload = create_admitted(tmp_path / "private" / "federation.db")
    reused = copy.deepcopy(original["approval"])
    reused["payload"]["operation_id"] = str(uuid.uuid4())
    with pytest.raises(module("protected_contract").ProtectedError):
        store.create("member", reused["payload"]["operation_id"],
            owner_subject=payload["principal"]["subject"], review=original["review"],
            review_digest=original["review_digest"], trust_snapshot=original["trust_snapshot"],
            state="admitted", approval=reused)
    assert store.get("member", payload["operation_id"])["state"] == "admitted"


def test_revocation_before_claim_refuses_executor_and_effect(tmp_path):
    store, row, _ = create_admitted(tmp_path / "private" / "federation.db")
    store.revoke("member", row["operation_id"])
    with pytest.raises(module("protected_contract").ProtectedError):
        store.claim_executor(row["operation_id"], NOW)
    with pytest.raises(module("protected_contract").ProtectedError):
        store.claim_effect(row["operation_id"], {})


def test_store_refuses_symlink_without_changing_target(tmp_path):
    target = tmp_path / "unrelated"
    target.write_text("preserve me")
    link = tmp_path / "linked.db"
    link.symlink_to(target)
    with pytest.raises(module("protected_contract").ProtectedError):
        module("protected_store").ProtectedStore(link)
    assert target.read_text() == "preserve me"


def test_claim_history_cannot_be_reset_through_state_transition(tmp_path):
    store, row, _ = create_admitted(tmp_path / "private" / "federation.db")
    operation = row["operation_id"]
    claimed = store.claim_executor(operation, NOW)
    store.claim_effect(operation, {"fixture": "authorization"})
    store.recover()
    with pytest.raises(module("protected_contract").ProtectedError):
        store.transition("member", operation, "outcome_unknown", state="admitted",
                         attempt_id=None, effect_claimed=0)
    assert store.get("member", operation)["attempt_id"] == claimed["attempt_id"]
    with pytest.raises(module("protected_contract").ProtectedError):
        store.claim_executor(operation, NOW + 100)
