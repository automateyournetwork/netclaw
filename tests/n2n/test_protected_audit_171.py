"""Independent mandatory-audit failures and real concurrent Git serialization."""

import asyncio
import json
import multiprocessing
from pathlib import Path
import subprocess
import uuid

import pytest

from protected_support_171 import OperationPair, module
from test_protected_approvals_171 import resign_modified


@pytest.mark.parametrize("failed", ["protected_approval", "protected_dispatch", "protected_executor", "protected_effect"])
def test_required_pre_boundary_audit_failure_prevents_effect(tmp_path, failed):
    async def run():
        pair = OperationPair(tmp_path)
        pair.failed_audits.add(failed)
        prepared = await pair.prepare()
        if failed in ("protected_approval", "protected_dispatch"):
            with pytest.raises(module("protected_contract").ProtectedError):
                await pair.decide(prepared)
        else:
            await pair.decide(prepared)
        await pair.drain()
        assert pair.effects == []
        row = pair.member.store.get("member", prepared["operation_id"])
        assert row is None or not row["effect_claimed"]
    asyncio.run(run())


def test_post_effect_audit_failure_recovers_evidence_without_reexecution(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        pair.failed_audits.add("protected_result")
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        row = pair.member.store.get("member", prepared["operation_id"])
        assert row["state"] == "audit_pending"
        assert row["receipt"] is None and row["effect_claimed"]
        assert len(pair.effects) == pair.executor_calls == 1
        await pair.restart()
        pair.failed_audits.clear()
        completed = await pair.reconcile(prepared["operation_id"])
        assert completed["state"] == "completed"
        assert len(pair.effects) == pair.executor_calls == 1
        assert completed["result"]["evidence"]["output"]["tool_evidence"] == pair.effects[0]
    asyncio.run(run())


def test_border_audit_failure_does_not_publish_verified_completion(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        pair.failed_audits.add("protected_result_accepted")
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.reconcile(prepared["operation_id"])
        row = pair.border.store.get("border", prepared["operation_id"])
        assert row["ack"] is None and row["state"] != "completed"
        pair.failed_audits.clear()
        assert (await pair.reconcile(prepared["operation_id"]))["state"] == "completed"
        assert len(pair.effects) == 1
    asyncio.run(run())


def test_principal_and_operation_correlate_across_all_audit_events(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        await pair.reconcile(prepared["operation_id"])
        names = {event for event, _ in pair.audit_events}
        assert {"protected_approval", "protected_dispatch", "protected_executor",
                "protected_effect", "protected_result", "protected_result_accepted"} <= names
        for _, record in pair.audit_events:
            assert record["principal"] == pair.principal
            assert record["operation_id"] == prepared["operation_id"]
            assert record["member"] == pair.template["member"]
        assert all("cookie" not in record and "auth_context" not in record for _, record in pair.audit_events)
    asyncio.run(run())


def test_refusal_outcome_and_reason_are_explicit_in_attributed_audit(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        pair.executor_error = module("protected_contract").ProtectedError("tool_call_changed", 403)
        prepared = await pair.prepare()
        await pair.decide(prepared)
        await pair.drain()
        result = await pair.reconcile(prepared["operation_id"])
        assert result["state"] == "refused" and pair.effects == []
        refusals = [record for _, record in pair.audit_events if record.get("outcome") == "refused"]
        assert refusals, "GAIT must distinguish a refusal from an ordinary successful result"
        assert any(record.get("error_code") == "tool_call_changed" for record in refusals)
        assert all(record["principal"] == pair.principal and record["operation_id"] == prepared["operation_id"] for record in refusals)
    asyncio.run(run())


def test_authenticated_signed_admission_refusal_is_audited_before_execution(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        envelope = resign_modified(pair, lambda p: p["tool_call"]["arguments"].update(device_name="foreign-router"))
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.member.submit(pair.to_member, {"approval": envelope})
        assert pair.executor_calls == 0 and pair.effects == []
        refusals = [record for _, record in pair.audit_events if record.get("outcome") == "refused"]
        assert refusals, "An authenticated, correctly signed scope refusal needs attributed evidence"
        assert all(record["principal"] == pair.principal for record in refusals)
        assert any(record["operation_id"] == envelope["payload"]["operation_id"] for record in refusals)
    asyncio.run(run())


def audit_worker(directory, record, ready, start, results):
    ready.put(True)
    start.wait(15)
    try:
        reference = module("gait").emit_protected("protected_executor", record=record, gait_dir=Path(directory))
        results.put(("ok", record["operation_id"], reference))
    except Exception as exc:
        results.put(("error", type(exc).__name__, str(exc)))


def test_separate_processes_append_distinct_durable_gait_commits(tmp_path):
    directory = tmp_path / "gait"
    principal = {"issuer": "local", "subject": str(uuid.uuid4()), "display_name": "Synthetic owner", "roles": ["owner"]}
    records = [{"principal": principal, "operation_id": str(uuid.uuid4()), "approval_id": str(uuid.uuid4())} for _ in range(4)]
    context = multiprocessing.get_context("spawn")
    ready, results, start = context.Queue(), context.Queue(), context.Event()
    workers = [context.Process(target=audit_worker, args=(str(directory), record, ready, start, results)) for record in records]
    try:
        for worker in workers: worker.start()
        for _ in workers: ready.get(timeout=20)
        start.set()
        references = [results.get(timeout=30) for _ in workers]
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
        assert all(status == "ok" for status, _, _ in references), references
        assert len({reference for _, _, reference in references}) == 4
        trail = directory / module("gait").TRAIL_FILE
        events = [json.loads(line) for line in trail.read_text().splitlines()]
        assert {event["protected"]["operation_id"] for event in events} == {r["operation_id"] for r in records}
        assert len(events) == 4
        for _, operation, reference in references:
            committed = subprocess.run(["git", "-C", str(directory), "show", f"{reference}:{trail.name}"],
                capture_output=True, text=True, check=True).stdout.splitlines()
            assert json.loads(committed[-1])["protected"]["operation_id"] == operation
    finally:
        start.set()
        for worker in workers:
            if worker.is_alive():
                worker.terminate(); worker.join(timeout=5)
