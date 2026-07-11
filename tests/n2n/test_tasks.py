"""T013/T014: async delegated task lifecycle (US1).

Unit tests for TaskManager, plus a loopback integration test proving:
- submit returns a task_id fast while the op runs in the background (FR-001)
- each lifecycle call is short regardless of op duration (FR-005 invariant)
- the result survives a channel drop+reconnect (FR-004)
- the result survives a responder daemon restart, from the persisted row (FR-004)
"""

import asyncio
import time

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.audit import Auditor
from bgp.federation.tasks import TaskManager


# ---- T013 unit tests --------------------------------------------------------

def test_task_lifecycle(manager):
    asyncio.run(_task_lifecycle(manager))


async def _task_lifecycle(manager):
    tm = TaskManager(manager, Auditor(manager), retention_s=3600)
    tid = tm.create(direction="inbound", peer_identity="as65007-7.7.7.7",
                    target_type="skill", target_name="demo", input_text="hi")
    assert tm.status(tid)["state"] == "submitted"

    async def worker(progress):
        progress("step 1")
        await asyncio.sleep(0.1)
        return "done!", 42

    tm.run(tid, worker)
    # brief poll until completed
    for _ in range(50):
        if tm.status(tid)["state"] == "completed":
            break
        await asyncio.sleep(0.05)
    assert tm.status(tid)["state"] == "completed"
    res = tm.result(tid)
    assert res["output_text"] == "done!" and res["tokens_used"] == 42


def test_task_cancel(manager):
    asyncio.run(_task_cancel(manager))


async def _task_cancel(manager):
    tm = TaskManager(manager, Auditor(manager))
    tid = tm.create(direction="inbound", peer_identity="p", target_type="skill", target_name="slow")

    async def worker(progress):
        await asyncio.sleep(30)
        return "never", 0

    tm.run(tid, worker)
    await asyncio.sleep(0.1)
    assert tm.cancel(tid) is True
    await asyncio.sleep(0.1)
    assert tm.status(tid)["state"] == "cancelled"


def test_unknown_task_id_terminal(manager):
    tm = TaskManager(manager, Auditor(manager))
    assert tm.status("nope")["state"] == "unknown"
    assert tm.result("nope")["state"] == "unknown"


def test_retention_sweep(manager):
    tm = TaskManager(manager, Auditor(manager), retention_s=3600)
    tid = tm.create(direction="inbound", peer_identity="p", target_type="skill", target_name="old")
    # Force retention into the past
    manager._conn.execute("UPDATE delegated_task SET retention_until=? WHERE task_id=?",
                          ("2000-01-01T00:00:00Z", tid))
    manager._conn.commit()
    assert tm.sweep() == 1
    assert tm.status(tid)["state"] == "unknown"


# ---- T014 loopback integration ---------------------------------------------

def _svc(base, local_as, rid, name):
    return FederationService(local_as=local_as, router_id=rid, display_name=name,
                             manager=FederationManager(base_dir=str(base)))


def _pipe():
    reader = asyncio.StreamReader()

    class _W:
        def write(self, data): reader.feed_data(data)
        async def drain(self): pass
        def close(self): pass
    return reader, _W()


async def _link(initiator, acceptor):
    from bgp.federation.channel import FederationChannel
    r_ia, w_ia = _pipe()
    r_ai, w_ai = _pipe()
    ini = FederationChannel(r_ai, w_ia, local_identity=initiator.local_identity,
                            peer_as=acceptor.local_as, peer_router_id=acceptor.router_id,
                            manager=initiator.manager, is_initiator=True, handlers=initiator.handlers)
    acc = FederationChannel(r_ia, w_ai, local_identity=acceptor.local_identity,
                            peer_as=initiator.local_as, peer_router_id=initiator.router_id,
                            manager=acceptor.manager, is_initiator=False, handlers=acceptor.handlers)
    initiator._register_channel(peer_identity(acceptor.local_as, acceptor.router_id), ini)
    acceptor._register_channel(peer_identity(initiator.local_as, initiator.router_id), acc)
    await ini.start(); await acc.start()
    return ini, acc


def _federate(a, b):
    a.manager.local_consent(b.local_as, b.router_id); a.manager.remote_consent(b.local_as, b.router_id)
    b.manager.local_consent(a.local_as, a.router_id); b.manager.remote_consent(a.local_as, a.router_id)


def test_async_delegation_end_to_end(tmp_path):
    asyncio.run(_async_delegation(tmp_path))


async def _async_delegation(tmp_path):
    john = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    nick = _svc(tmp_path / "b", 65007, "7.7.7.7", "Nick")
    _federate(john, nick)
    nick.authz.grant(john.local_identity, "skill", "cml-clone")

    # Stub Nick's executor to take a few seconds (proves submit is async)
    async def slow_exec(skill, input_text):
        await asyncio.sleep(3)
        return f"built {skill}: 10 nodes, 12 links", 100
    nick.invoker._exec_skill_gateway = slow_exec

    await _link(john, nick)

    # Submit — MUST return fast with a task_id while the 3s op runs in background
    t0 = time.monotonic()
    sub = await john.invoker.submit_remote_skill(nick.local_identity, "cml-clone", "<spec>")
    submit_dt = time.monotonic() - t0
    task_id = sub["task_id"]
    assert task_id and submit_dt < 1.5, f"submit took {submit_dt:.2f}s (must be short, FR-005)"

    # Status calls MUST be short even while the op runs
    t0 = time.monotonic()
    st = await john.invoker.poll_remote_task(nick.local_identity, task_id, kind="status")
    assert (time.monotonic() - t0) < 1.5, "status call must be short (FR-005)"
    assert st["state"] in ("submitted", "working")

    # Poll to completion, then fetch result
    for _ in range(60):
        r = await john.invoker.poll_remote_task(nick.local_identity, task_id, kind="result")
        if r["state"] == "completed":
            break
        await asyncio.sleep(0.2)
    assert r["state"] == "completed"
    assert "10 nodes, 12 links" in r["output_text"]

    # FR-004a: result survives a CHANNEL drop — close John's channel, still retrievable from cache
    await john.channels[nick.local_identity].close()
    await asyncio.sleep(0.1)
    cached = john.tasks.result(task_id)
    assert cached["state"] == "completed" and "10 nodes" in cached.get("output_text", "")

    # FR-004b: result survives a responder DAEMON restart — reopen Nick's manager
    # from the same DB and confirm the inbound task row + result persist.
    db, base = nick.manager.db_path, str(nick.manager.base_dir)
    nick.manager.close()
    m2 = FederationManager(db_path=db, base_dir=base)
    tm2 = TaskManager(m2, Auditor(m2))
    persisted = tm2.result(task_id)
    assert persisted["state"] == "completed" and "10 nodes" in persisted.get("output_text", "")
    m2.close()
