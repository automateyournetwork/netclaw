"""Async delegated tasks (feature 053, US1).

A delegated task is a long-running remote operation (e.g. rebuild a CML lab)
that must NOT be run inside a single synchronous channel call — that exceeds
timeouts and gets reset by ngrok mid-operation. Instead:

  submit  → create a persisted task row, spawn a background worker, return task_id
            immediately
  status  → short call returning state + progress
  result  → short call returning the stored result once completed
  cancel  → cancel the background worker

Task rows persist in federation.db so a completed result survives a channel
drop/reconnect and a daemon restart (FR-004); a retention sweep discards old rows.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Awaitable, Callable, Optional

logger = logging.getLogger("n2n.tasks")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class TaskManager:
    def __init__(self, manager, audit, retention_s: int = 3600):
        self.manager = manager            # FederationManager (SQLite + result store)
        self.audit = audit
        self.retention_s = retention_s
        self._workers: dict = {}          # task_id -> asyncio.Task (in-process only)

    # ---- creation / execution (inbound: we run it for a peer) ----------

    def create(self, *, direction: str, peer_identity: str, target_type: str,
               target_name: str, input_text: str = "") -> str:
        task_id = str(uuid.uuid4())
        now = _now()
        retain = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               time.gmtime(time.time() + self.retention_s))
        self.manager._conn.execute(
            "INSERT INTO delegated_task (task_id, direction, peer_identity, target_type, "
            "target_name, input_text, state, created_at, updated_at, retention_until) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (task_id, direction, peer_identity, target_type, target_name, input_text,
             "submitted", now, now, retain))
        self.manager._conn.commit()
        return task_id

    def run(self, task_id: str, worker: Callable[[Callable[[str], None]], Awaitable]):
        """Spawn a background worker for task_id. `worker(progress_cb)` awaits the
        actual work and returns (output_text, tokens_used)."""
        async def _run():
            self._set(task_id, state="working")
            try:
                def progress(detail: str):
                    self._set(task_id, progress=detail)
                output, tokens = await worker(progress)
                ref = self.audit.store_result(task_id, {"output_text": output})
                self._set(task_id, state="completed", result_ref=ref,
                          tokens_used=int(tokens or 0), completed_at=_now())
                logger.info("Task %s completed", task_id)
            except asyncio.CancelledError:
                self._set(task_id, state="cancelled", completed_at=_now())
                raise
            except Exception as e:
                ref = self.audit.store_result(task_id, {"error": str(e)})
                self._set(task_id, state="failed", result_ref=ref, completed_at=_now())
                logger.warning("Task %s failed: %s", task_id, e)
            finally:
                self._workers.pop(task_id, None)
        self._workers[task_id] = asyncio.create_task(_run())

    def cancel(self, task_id: str, owner: Optional[str] = None) -> bool:
        if owner is not None and not self._owns(task_id, owner):
            return False
        w = self._workers.get(task_id)
        if w and not w.done():
            w.cancel()
            return True
        return False

    # ---- queries -------------------------------------------------------
    #
    # `owner` binds retrieval to the submitting peer (NCFED -00 §9.2/§14.6):
    # remote-facing handlers pass the authenticated channel identity, and a
    # task the caller did not submit is answered exactly like a task that
    # does not exist, so a leaked/guessed task_id is no longer a bearer
    # capability and cannot even be probed for existence. Local callers
    # (HUD, reconciliation) pass no owner and see everything.

    def _owns(self, task_id: str, owner: str) -> bool:
        row = self.manager._conn.execute(
            "SELECT 1 FROM delegated_task WHERE task_id=? AND direction='inbound' "
            "AND peer_identity=?", (task_id, owner)).fetchone()
        return row is not None

    def status(self, task_id: str, owner: Optional[str] = None) -> dict:
        if owner is not None and not self._owns(task_id, owner):
            return {"task_id": task_id, "state": "unknown"}
        row = self.manager._conn.execute(
            "SELECT state, progress, target_name FROM delegated_task WHERE task_id=?",
            (task_id,)).fetchone()
        if not row:
            return {"task_id": task_id, "state": "unknown"}
        return {"task_id": task_id, "state": row["state"], "progress": row["progress"],
                "target": row["target_name"]}

    def result(self, task_id: str, owner: Optional[str] = None) -> dict:
        if owner is not None and not self._owns(task_id, owner):
            return {"task_id": task_id, "state": "unknown"}
        row = self.manager._conn.execute(
            "SELECT state, result_ref, tokens_used FROM delegated_task WHERE task_id=?",
            (task_id,)).fetchone()
        if not row:
            return {"task_id": task_id, "state": "unknown"}
        out = {"task_id": task_id, "state": row["state"], "tokens_used": row["tokens_used"]}
        if row["result_ref"]:
            try:
                payload = json.loads(open(row["result_ref"]).read())
                out.update({k: v for k, v in payload.items() if k in ("output_text", "error")})
            except Exception:
                pass
        return out

    def record_outbound(self, task_id: str, peer_identity: str, target_type: str,
                        target_name: str) -> None:
        """Track a task we submitted to a peer, so we can retrieve its result
        after a channel drop (FR-004)."""
        now = _now()
        retain = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               time.gmtime(time.time() + self.retention_s))
        self.manager._conn.execute(
            "INSERT OR REPLACE INTO delegated_task (task_id, direction, peer_identity, "
            "target_type, target_name, state, created_at, updated_at, retention_until) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (task_id, "outbound", peer_identity, target_type, target_name,
             "submitted", now, now, retain))
        self.manager._conn.commit()

    def list_recent(self, limit: int = 50) -> list:
        return [dict(r) for r in self.manager._conn.execute(
            "SELECT task_id, direction, peer_identity, target_type, target_name, state, "
            "progress, updated_at FROM delegated_task ORDER BY updated_at DESC LIMIT ?",
            (limit,))]

    # ---- internals -----------------------------------------------------

    def _set(self, task_id: str, **fields):
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k}=?" for k in fields)
        self.manager._conn.execute(
            f"UPDATE delegated_task SET {cols} WHERE task_id=?",
            (*fields.values(), task_id))
        self.manager._conn.commit()

    def sweep(self) -> int:
        cur = self.manager._conn.execute(
            "DELETE FROM delegated_task WHERE retention_until < ?", (_now(),))
        self.manager._conn.commit()
        return cur.rowcount
