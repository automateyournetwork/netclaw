"""H23: the Border closes out finished iN2N member tasks on its own.

iN2N task status is pull-only — a member never announces completion — so the
Border's outbound delegated_task row stayed 'submitted' unless an operator
polled it. reconcile_member_tasks() pulls results from connected members; it
runs when a member channel (re)registers and on a periodic loop.
"""

import asyncio

from test_member_delegation import _stand_up_risk


def _row(svc, task_id):
    r = svc.manager._conn.execute(
        "SELECT state, completed_at, result_ref FROM delegated_task "
        "WHERE task_id=? AND direction='outbound'", (task_id,)).fetchone()
    return dict(zip(("state", "completed_at", "result_ref"), r))


async def _delegate_and_finish(border, member):
    out = await border.route_and_delegate("cml-lab-lifecycle", "build my lab")
    task_id = out["task_id"]
    for _ in range(50):
        if member.tasks.status(task_id)["state"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.05)
    assert member.tasks.status(task_id)["state"] == "completed"
    # Nobody polled: this is the stuck state H23 found in production.
    assert _row(border, task_id)["state"] == "submitted"
    return task_id


def test_reconcile_closes_completed_member_task(tmp_path, monkeypatch):
    async def run():
        border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"], monkeypatch)
        try:
            task_id = await _delegate_and_finish(border, member)
            out = await border.reconcile_member_tasks()
            assert out["reconciled"] == [task_id]
            row = _row(border, task_id)
            assert row["state"] == "completed"
            assert row["completed_at"]          # never None (H23 second defect)
            assert row["result_ref"]
            res = border.tasks.result(task_id)
            assert res["state"] == "completed"
            # Idempotent: nothing left to close.
            assert (await border.reconcile_member_tasks())["reconciled"] == []
        finally:
            server.close()
        border.manager.close(); member.manager.close()
    asyncio.run(run())


def test_reconcile_skips_unconnected_member(tmp_path, monkeypatch):
    async def run():
        border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"], monkeypatch)
        try:
            task_id = await _delegate_and_finish(border, member)
            ch = border.member_channels.pop("risk/cml")
            called = []
            async def _no_cold_start(*a, **k):
                called.append(a)
            monkeypatch.setattr(border, "ensure_member_up", _no_cold_start)
            out = await border.reconcile_member_tasks()
            assert out == {"checked": 0, "reconciled": []}
            assert called == []                       # never cold-starts a member
            assert _row(border, task_id)["state"] == "submitted"
            border.member_channels["risk/cml"] = ch
        finally:
            server.close()
        border.manager.close(); member.manager.close()
    asyncio.run(run())


def test_member_reconnect_triggers_reconcile(tmp_path, monkeypatch):
    async def run():
        border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"], monkeypatch)
        try:
            task_id = await _delegate_and_finish(border, member)
            # Re-registering the member channel is what a reconnect does.
            border._register_member_channel("risk/cml", border.member_channels["risk/cml"])
            for _ in range(50):
                if _row(border, task_id)["state"] == "completed":
                    break
                await asyncio.sleep(0.05)
            assert _row(border, task_id)["state"] == "completed"
        finally:
            server.close()
        border.manager.close(); member.manager.close()
    asyncio.run(run())


def test_periodic_loop_reconciles(tmp_path, monkeypatch):
    async def run():
        border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"], monkeypatch)
        try:
            task_id = await _delegate_and_finish(border, member)
            border._member_reconcile_s = 0.05
            loop_task = asyncio.create_task(border._member_reconcile_loop())
            try:
                for _ in range(50):
                    if _row(border, task_id)["state"] == "completed":
                        break
                    await asyncio.sleep(0.05)
            finally:
                loop_task.cancel()
            assert _row(border, task_id)["state"] == "completed"
        finally:
            server.close()
        border.manager.close(); member.manager.close()
    asyncio.run(run())


def test_reconcile_keeps_member_completion_time(tmp_path, monkeypatch):
    """The Border records when the member finished, not when it noticed."""
    async def run():
        border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"], monkeypatch)
        try:
            task_id = await _delegate_and_finish(border, member)
            member.manager._conn.execute(
                "UPDATE delegated_task SET completed_at='2026-07-21T10:00:00Z' WHERE task_id=?",
                (task_id,))
            assert member.tasks.result(task_id)["completed_at"] == "2026-07-21T10:00:00Z"
            await border.reconcile_member_tasks()
            assert _row(border, task_id)["completed_at"] == "2026-07-21T10:00:00Z"
        finally:
            server.close()
        border.manager.close(); member.manager.close()
    asyncio.run(run())


def test_interrupted_member_row_reports_updated_at(tmp_path, monkeypatch):
    async def run():
        border, member, server = await _stand_up_risk(tmp_path, ["cml-lab-lifecycle"], monkeypatch)
        try:
            task_id = await _delegate_and_finish(border, member)
            member.manager._conn.execute(
                "UPDATE delegated_task SET state='interrupted', completed_at=NULL, "
                "updated_at='2026-08-02T03:04:05Z' WHERE task_id=?", (task_id,))
            await border.reconcile_member_tasks()
            row = _row(border, task_id)
            assert row["state"] == "interrupted"
            assert row["completed_at"] == "2026-08-02T03:04:05Z"
        finally:
            server.close()
        border.manager.close(); member.manager.close()
    asyncio.run(run())


def test_member_completed_at_validation():
    from bgp.federation.service import _member_completed_at, _tasks_now
    assert _member_completed_at({"completed_at": "2026-07-21T10:00:00Z"}) == "2026-07-21T10:00:00Z"
    for bad in (None, "", "yesterday", "2026-07-21 10:00:00", "2026-07-21T10:00:00Z; DROP",
                "9999-01-01T00:00:00Z", 12345):
        got = _member_completed_at({"completed_at": bad})
        assert got != bad and got <= _tasks_now()
    assert _member_completed_at({}) and _member_completed_at(None)
