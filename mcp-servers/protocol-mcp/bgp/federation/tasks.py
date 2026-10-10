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
               target_name: str, input_text: str = "", client_request=None, owner_generation=None,client_features=None,request_payload=None) -> str:
        from .execution import digest, Refused
        body=digest([target_type,target_name,input_text,request_payload])
        if client_request:
            if not isinstance(client_request,str) or len(client_request)>200:raise Refused('invalid request id')
            old=self.manager._conn.execute('SELECT task_id,body_digest,owner_generation FROM delegated_task WHERE direction=? AND peer_identity=? AND client_request=?',
                                            (direction,peer_identity,client_request)).fetchone()
            if old:
                if old['owner_generation']!=owner_generation:raise Refused('request belongs to a different enrollment')
                if old['body_digest']!=body:raise Refused('request body conflicts with original admission')
                return old['task_id']
        task_id = str(uuid.uuid4())
        now = _now()
        retain = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               time.gmtime(time.time() + self.retention_s))
        self.manager._conn.execute(
            "INSERT INTO delegated_task (task_id, direction, peer_identity, target_type, "
            "target_name, input_text, state, created_at, updated_at, retention_until,client_request,body_digest,owner_generation,client_features) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_id, direction, peer_identity, target_type, target_name, input_text,
             "submitted", now, now, retain,client_request,body,owner_generation,json.dumps(client_features or [])))
        self.manager._conn.commit()
        return task_id

    def resolve_owned_request(self,owner,request,generation=None):
        row=self.manager._conn.execute('SELECT task_id,owner_generation FROM delegated_task WHERE direction=? AND peer_identity=? AND client_request=?',('inbound',owner,request)).fetchone()
        if not row or row['owner_generation']!=generation:return None
        return row['task_id']

    def generation_matches(self,task_id,owner,generation):
        row=self.manager._conn.execute("SELECT owner_generation FROM delegated_task WHERE task_id=? AND direction='inbound' AND peer_identity=?",(task_id,owner)).fetchone()
        # Existing tasks have no enrollment generation. Their historical owner
        # rule remains for compatibility; all new device tasks bind a generation.
        return bool(row and (row[0] is None or row[0]==generation))

    def project_edge(self,task_id,value):
        row=self.manager._conn.execute('SELECT client_features,cancel_requested FROM delegated_task WHERE task_id=?',(task_id,)).fetchone()
        if not row:return value
        value={**value,'cancel_requested':bool(row['cancel_requested']),'cancellation_confirmed':value.get('state')=='cancelled'}
        if 'task_outcomes_v1' not in json.loads(row['client_features'] or '[]') and value.get('state') in ('outcome_unknown','interrupted'):
            canonical=value['state']
            value.update(state='failed',outcome_state=canonical,error=('Outcome unknown: work may have executed. Do not resubmit; check status with an updated NetClaw Mobile app.' if canonical=='outcome_unknown' else 'Interrupted before execution. No automatic retry was made.'))
        return value

    def run(self, task_id: str, worker: Callable[[Callable[[str], None]], Awaitable]) -> asyncio.Task:
        """Spawn a background worker for task_id. `worker(progress_cb)` awaits the
        actual work and returns (output_text, tokens_used). Returns the spawned
        asyncio.Task so a caller can `await` its completion directly instead of
        polling internal state (feature 067)."""
        if task_id in self._workers:return self._workers[task_id]
        row=self.manager._conn.execute('SELECT state FROM delegated_task WHERE task_id=?',(task_id,)).fetchone()
        if not row or row['state']!='submitted':return None
        async def _run():
            self._set(task_id, state="working")
            try:
                def progress(detail: str):
                    self._set(task_id, progress=detail)
                output, tokens = await worker(progress)
                ref = self.audit.store_result(task_id, {"output_text": output})
                self._set(task_id, state="completed", result_ref=ref,
                          tokens_used=int(tokens or 0), usage_available=int(tokens is not None), completed_at=_now())
                logger.info("Task %s completed", task_id)
            except asyncio.CancelledError:
                self._set(task_id, state="outcome_unknown" if self.dispatched(task_id) else "cancelled", completed_at=_now())
                raise
            except Exception as e:
                from .execution import OutcomeUnknown
                try:
                    ref = self.audit.store_result(task_id, {"error": str(e)})
                except Exception:
                    ref = None
                    logger.warning("Task %s error payload could not be persisted", task_id)
                self._set(task_id, state="outcome_unknown" if isinstance(e,OutcomeUnknown) or self.dispatched(task_id) else "failed", result_ref=ref, completed_at=_now())
                logger.warning("Task %s failed: %s", task_id, e)
            finally:
                self._workers.pop(task_id, None)
        t = asyncio.create_task(_run())
        self._workers[task_id] = t
        return t

    def mark_dispatch(self, task_id, context=None, runtime=None, execution_ref=None):
        self._set(task_id,dispatch_started=1,execution_context=json.dumps(context) if context else None,
                  installation_id=getattr(runtime,'installation',None),runtime_kind=getattr(runtime,'kind',None),execution_ref=execution_ref)

    def dispatched(self,task_id):
        row=self.manager._conn.execute('SELECT dispatch_started FROM delegated_task WHERE task_id=?',(task_id,)).fetchone()
        return bool(row and row[0])

    def recover(self):
        """At owned process startup only. Never replay a worker lost to restart."""
        self.manager._conn.execute("UPDATE delegated_task SET state=CASE WHEN dispatch_started=1 THEN 'outcome_unknown' ELSE 'interrupted' END, updated_at=? WHERE direction='inbound' AND state IN ('submitted','working')",(_now(),))
        self.manager._conn.commit()

    def cancel(self, task_id: str, owner: Optional[str] = None) -> bool:
        if owner is not None and not self._owns(task_id, owner):
            return False
        w = self._workers.get(task_id)
        if w and not w.done():
            self._set(task_id,cancel_requested=1)
            if self.status(task_id)['state']=='submitted' and not self.dispatched(task_id):
                self._set(task_id,state='cancelled',completed_at=_now())
                w.add_done_callback(lambda _:self._workers.pop(task_id,None))
            w.cancel()
            return True
        # No live worker for this task_id in THIS process. Usually that just
        # means it already reached a terminal state -- but if a daemon
        # restart happened while the task was in flight, the in-memory
        # asyncio.Task that would run OR cancel it was destroyed while the
        # DB row is still stuck at "submitted"/"working" forever, with
        # nothing left alive to ever finish or cancel it (found via a real
        # stuck edge_ask task whose phone-side Cancel button silently did
        # nothing). Only a task genuinely still open is fixed up here.
        row = self.manager._conn.execute(
            "SELECT state FROM delegated_task WHERE task_id=?", (task_id,)).fetchone()
        if row and row["state"] in ("submitted", "working"):
            self._set(task_id, state="outcome_unknown" if self.dispatched(task_id) else "cancelled", cancel_requested=1, completed_at=_now())
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
            "SELECT state, progress, target_name,cancel_requested,runtime_kind,installation_id FROM delegated_task WHERE task_id=?",
            (task_id,)).fetchone()
        if not row:
            return {"task_id": task_id, "state": "unknown"}
        return {"task_id": task_id, "state": row["state"], "progress": row["progress"],
                "target": row["target_name"], 'cancel_requested':bool(row['cancel_requested']), 'harness':row['runtime_kind']}

    def result(self, task_id: str, owner: Optional[str] = None) -> dict:
        if owner is not None and not self._owns(task_id, owner):
            return {"task_id": task_id, "state": "unknown"}
        row = self.manager._conn.execute(
            "SELECT state, result_ref, tokens_used,usage_available FROM delegated_task WHERE task_id=?",
            (task_id,)).fetchone()
        if not row:
            return {"task_id": task_id, "state": "unknown"}
        out = {"task_id": task_id, "state": row["state"], "tokens_used": row["tokens_used"] if row['usage_available'] else None, 'usage_available':bool(row['usage_available'])}
        if row['state']=='outcome_unknown':out.update(may_have_executed=True,error='Execution outcome is unknown. Check status; do not resubmit.')
        elif row['state']=='interrupted':out.update(may_have_executed=False,error='Request interrupted before execution.')
        if row["result_ref"]:
            try:
                payload = json.loads(open(row["result_ref"]).read())
                out.update({k: v for k, v in payload.items() if k in ("output_text", "error")})
            except Exception:
                out["result_available"] = False
                out["error"] = "Stored task result is unavailable"
        elif row["state"] in ("completed", "failed"):
            out["result_available"] = False
            out["error"] = "Task result was not persisted"
        return out

    def record_outbound(self, task_id: str, peer_identity: str, target_type: str,
                        target_name: str) -> None:
        """Track a task we submitted to a peer, so we can retrieve its result
        after a channel drop (FR-004)."""
        now = _now()
        existing=self.manager._conn.execute('SELECT direction,peer_identity,target_type,target_name FROM delegated_task WHERE task_id=?',(task_id,)).fetchone()
        if existing and tuple(existing)!=('outbound',peer_identity,target_type,target_name):
            from .execution import OutcomeUnknown
            raise OutcomeUnknown('remote task identifier collides with a different owner; retained outbound intent')
        retain = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               time.gmtime(time.time() + self.retention_s))
        self.manager._conn.execute(
            "INSERT OR IGNORE INTO delegated_task (task_id, direction, peer_identity, "
            "target_type, target_name, state, created_at, updated_at, retention_until) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (task_id, "outbound", peer_identity, target_type, target_name,
             "submitted", now, now, retain))
        self.manager._conn.commit()

    def outbound_intent(self,peer,method,body,request=None):
        """Persist before transport dispatch; old peers need not support dedupe."""
        from .execution import digest
        request=request or body.get('request_id') or str(uuid.uuid4())
        self.manager._conn.execute('CREATE TABLE IF NOT EXISTS outbound_intent (request TEXT PRIMARY KEY,peer TEXT NOT NULL,method TEXT NOT NULL,body_digest TEXT NOT NULL,state TEXT NOT NULL,remote_task TEXT,created TEXT NOT NULL)')
        self.manager._conn.execute('INSERT INTO outbound_intent VALUES (?,?,?,?,?,NULL,?)',(request,peer,method,digest(body),'dispatching',_now()))
        self.manager._conn.commit()
        return request

    def settle_intent(self,request,state,remote_task=None):
        self.manager._conn.execute('UPDATE outbound_intent SET state=?,remote_task=? WHERE request=?',(state,remote_task,request))
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
            "DELETE FROM delegated_task WHERE retention_until < ? AND state IN ('completed','failed','cancelled','interrupted')", (_now(),))
        self.manager._conn.commit()
        return cur.rowcount
