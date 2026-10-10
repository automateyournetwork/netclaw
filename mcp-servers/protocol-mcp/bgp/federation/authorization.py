"""N2N authorization: grants, rate limits, per-peer daily budgets, approvals.

Default-deny (FR-012): a peer may invoke only tools/skills the operator has
explicitly allowlisted for that specific peer. Every request is additionally
bounded by a per-minute rate limit and a per-peer daily budget of requests and
tokens (FR-017). Sensitive grants can require human approval with an expiry
window (FR-013).
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("n2n.authz")


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class Decision:
    allowed: bool
    code: str            # allowlisted | approval_required | not_allowlisted | rate_limited | budget_exhausted | severed
    grant: Optional[dict] = None
    reason: str = ""
    approval_id: Optional[int] = None
    request_binding: Optional[str] = None


class Authorizer:
    def __init__(self, manager):
        self.manager = manager
        self.rate_per_min = int(os.environ.get("N2N_RATE_PER_MIN", "10"))
        self.daily_requests = int(os.environ.get("N2N_DAILY_REQUESTS", "200"))
        self.daily_tokens = int(os.environ.get("N2N_DAILY_TOKENS", "500000"))
        self.approval_window_s = int(os.environ.get("N2N_APPROVAL_WINDOW_S", "900"))
        # peer_identity -> list of recent request epoch times (rate window)
        self._recent: dict = {}

    # ---- grants (FR-012) ----------------------------------------------

    def grant(self, peer_identity: str, target_type: str, target_name: str,
              requires_approval: bool = False, timeout_s: Optional[int] = None) -> int:
        cur = self.manager._conn.execute(
            "INSERT INTO invocation_grant (peer_identity, target_type, target_name, "
            "requires_approval, timeout_s, created_at) VALUES (?,?,?,?,?,?)",
            (peer_identity, target_type, target_name, 1 if requires_approval else 0,
             timeout_s, _now()))
        self.manager._conn.commit()
        return cur.lastrowid

    def revoke(self, grant_id: int):
        self.manager._conn.execute(
            "UPDATE invocation_grant SET revoked_at=? WHERE id=?", (_now(), grant_id))
        self.manager._conn.commit()

    def list_grants(self, peer_identity: Optional[str] = None) -> list:
        if peer_identity:
            rows = self.manager._conn.execute(
                "SELECT * FROM invocation_grant WHERE peer_identity=? AND revoked_at IS NULL",
                (peer_identity,))
        else:
            rows = self.manager._conn.execute(
                "SELECT * FROM invocation_grant WHERE revoked_at IS NULL")
        return [dict(r) for r in rows]

    def _find_grant(self, peer_identity: str, target_type: str, target_name: str) -> Optional[dict]:
        row = self.manager._conn.execute(
            "SELECT * FROM invocation_grant WHERE peer_identity=? AND target_type=? "
            "AND target_name=? AND revoked_at IS NULL", (peer_identity, target_type, target_name)).fetchone()
        return dict(row) if row else None

    # ---- rate limit (FR-017) ------------------------------------------

    def _check_rate(self, peer_identity: str) -> bool:
        now = time.time()
        window = [t for t in self._recent.get(peer_identity, []) if now - t < 60]
        if len(window) >= self.rate_per_min:
            self._recent[peer_identity] = window
            return False
        window.append(now)
        self._recent[peer_identity] = window
        return True

    # ---- budget (FR-017) ----------------------------------------------

    def _budget_row(self, peer_identity: str) -> dict:
        day = _today()
        row = self.manager._conn.execute(
            "SELECT requests_used, tokens_used FROM budget_counter WHERE peer_identity=? AND day=?",
            (peer_identity, day)).fetchone()
        if not row:
            self.manager._conn.execute(
                "INSERT INTO budget_counter (peer_identity, day) VALUES (?,?)", (peer_identity, day))
            self.manager._conn.commit()
            return {"requests_used": 0, "tokens_used": 0}
        return {"requests_used": row["requests_used"], "tokens_used": row["tokens_used"]}

    def _check_budget(self, peer_identity: str) -> bool:
        b = self._budget_row(peer_identity)
        return b["requests_used"] < self.daily_requests and b["tokens_used"] < self.daily_tokens

    def debit(self, peer_identity: str, requests: int = 1, tokens: int = 0):
        day = _today()
        self._budget_row(peer_identity)  # ensure row exists
        self.manager._conn.execute(
            "UPDATE budget_counter SET requests_used=requests_used+?, tokens_used=tokens_used+? "
            "WHERE peer_identity=? AND day=?", (requests, tokens or 0, peer_identity, day))
        self.manager._conn.commit()

    def budget_status(self, peer_identity: str) -> dict:
        b = self._budget_row(peer_identity)
        return {"requests_used": b["requests_used"], "requests_limit": self.daily_requests,
                "tokens_used": b["tokens_used"], "tokens_limit": self.daily_tokens}

    # ---- the decision (FR-012/013/017) --------------------------------

    def authorize(self, peer_identity: str, target_type: str, target_name: str,
                  *, already_trusted: bool = False, check_rate: bool = True) -> Decision:
        # spec 121: is_federated() checks the eN2N federation_peer table — a
        # concept that doesn't exist for an iN2N member's own self-referential
        # peer_identity (its one channel to Border, see _in2n_member_submit's
        # comment: peer_identity == this member's own member_id on that
        # channel). Confirmed live: an already fully pinned-key-authenticated,
        # possession-attested internal channel still got "severed"/"peer not
        # federated" here, because there's no federation_peer row for "myself".
        # already_trusted lets an internal-channel caller (invocation.py's
        # handle_tools_call, the only current caller that sets it) skip only
        # this eN2N-specific gate — the grant/rate/budget checks below still
        # run unconditionally for every caller.
        if not already_trusted and not self.manager.is_federated(peer_identity):
            return Decision(False, "severed", reason="peer not federated")
        grant = self._find_grant(peer_identity, target_type, target_name)
        if not grant:
            return Decision(False, "not_allowlisted",
                            reason=f"{target_type} '{target_name}' not allowlisted for {peer_identity}")
        if check_rate and not self._check_rate(peer_identity):
            return Decision(False, "rate_limited", grant, "per-minute rate limit exceeded")
        if not self._check_budget(peer_identity):
            return Decision(False, "budget_exhausted", grant, "daily budget exhausted")
        if grant["requires_approval"]:
            return Decision(False, "approval_required", grant, "human approval required")
        return Decision(True, "allowlisted", grant)

    def admit(self, peer_identity: str, target_type: str, target_name: str,
              original: Decision, *, already_trusted: bool = False) -> Decision:
        """Revalidate after waits, then reserve one request before execution.

        The caller has already completed any approval required by `original`.
        A new/replaced grant cannot inherit that approval. Rate admission was
        consumed by the initial request and is deliberately not charged twice.
        """
        current = self.authorize(peer_identity, target_type, target_name,
                                 already_trusted=already_trusted, check_rate=False)
        if not current.allowed and current.code != "approval_required":
            return current
        if not original.grant or current.grant["id"] != original.grant["id"]:
            return Decision(False, "not_allowlisted", reason="original grant was revoked or replaced")
        if current.code == "approval_required" and original.code != "approval_required":
            return current
        if current.code=='approval_required':
            db=self.manager._conn
            db.execute('BEGIN IMMEDIATE')
            try:
                approved=db.execute("UPDATE approval_request SET consumed_at=? WHERE id=? AND status='approved' AND expires_at>? AND consumed_at IS NULL AND request_binding=?",
                    (_now(),original.approval_id,_now(),original.request_binding))
                if approved.rowcount!=1:
                    db.rollback()
                    return Decision(False,'approval_required',current.grant,'exact unexpired unused approval required')
                reserved=db.execute('UPDATE budget_counter SET requests_used=requests_used+1 WHERE peer_identity=? AND day=? AND requests_used<? AND tokens_used<?',
                    (peer_identity,_today(),self.daily_requests,self.daily_tokens))
                if reserved.rowcount!=1:
                    db.rollback()
                    return Decision(False,'budget_exhausted',current.grant,'daily budget exhausted')
                db.commit()
            except BaseException:db.rollback();raise
        elif not self.reserve_request(peer_identity):
            return Decision(False, "budget_exhausted", current.grant, "daily budget exhausted")
        return Decision(True, "allowlisted", current.grant)

    def still_authorized(self,peer,target_type,target,original,*,already_trusted=False):
        """Recheck an already reserved request without charging or reapproving it."""
        if not already_trusted and not self.manager.is_federated(peer):return False
        grant=self._find_grant(peer,target_type,target)
        if not grant or not original.grant or grant['id']!=original.grant['id']:return False
        if self._budget_row(peer)['tokens_used']>=self.daily_tokens:return False
        if grant['requires_approval']:
            row=self.manager._conn.execute('SELECT request_binding,consumed_at,status FROM approval_request WHERE id=?',(original.approval_id,)).fetchone()
            return bool(row and row['request_binding']==original.request_binding and row['consumed_at'] and row['status']=='approved')
        return True

    def reserve_request(self, peer_identity: str) -> bool:
        """Reserve a request before asynchronous execution, including chat."""
        if not self._check_budget(peer_identity):
            return False
        cur = self.manager._conn.execute(
            "UPDATE budget_counter SET requests_used=requests_used+1 "
            "WHERE peer_identity=? AND day=? AND requests_used<? AND tokens_used<?",
            (peer_identity, _today(), self.daily_requests, self.daily_tokens))
        self.manager._conn.commit()
        return cur.rowcount == 1

    # ---- approvals (FR-013) -------------------------------------------

    def create_approval(self, invocation_id: int, request_binding=None) -> dict:
        expires = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                time.gmtime(time.time() + self.approval_window_s))
        cur = self.manager._conn.execute(
            "INSERT INTO approval_request (invocation_id, status, requested_at, expires_at,request_binding) "
            "VALUES (?,?,?,?,?)", (invocation_id, "pending", _now(), expires,request_binding))
        self.manager._conn.commit()
        return {"approval_id": cur.lastrowid, "expires_at": expires}

    def resolve_approval(self, approval_id: int, action: str, via: str = "cli") -> dict:
        """Idempotent: a repeat call for an already-resolved approval_id matches
        zero rows below and has no effect. `already_resolved` distinguishes that
        no-op from an actual first-time resolution (073/FR-005, research D6) --
        existing callers that only used the old always-True boolean return see
        no behavior change, since `resolve_approval(...)` truthy-checked as a
        dict is still truthy either way.
        """
        if action not in ("approve", "deny"):
            raise ValueError("Approval action must be approve or deny")
        self._expire_pending()
        if self.approval_status(approval_id) in ("expired", "unknown"):
            return {"resolved": False, "already_resolved": False,
                    "expired": self.approval_status(approval_id) == "expired"}
        status = "approved" if action == "approve" else "denied"
        cur = self.manager._conn.execute(
            "UPDATE approval_request SET status=?, resolved_at=?, resolved_via=? "
            "WHERE id=? AND status='pending' AND expires_at>?", (status, _now(), via, approval_id, _now()))
        self.manager._conn.commit()
        if cur.rowcount == 0 and self.approval_status(approval_id) in ("expired", "unknown"):
            return {"resolved": False, "already_resolved": False,
                    "expired": self.approval_status(approval_id) == "expired"}
        return {"resolved": True, "already_resolved": cur.rowcount == 0}

    def approval_status(self, approval_id: int) -> str:
        row = self.manager._conn.execute(
            "SELECT status, expires_at,consumed_at FROM approval_request WHERE id=?", (approval_id,)).fetchone()
        if not row:
            return "unknown"
        if row["status"] in ('pending','approved') and not row['consumed_at'] and row["expires_at"] <= _now():
            self.manager._conn.execute(
                "UPDATE approval_request SET status='expired' WHERE id=?", (approval_id,))
            self.manager._conn.commit()
            return "expired"
        return row["status"]

    def _expire_pending(self):
        self.manager._conn.execute(
            "UPDATE approval_request SET status='expired' WHERE status IN ('pending','approved') AND consumed_at IS NULL AND expires_at<=?", (_now(),))
        self.manager._conn.commit()

    def pending_approvals(self) -> list:
        self._expire_pending()
        rows = self.manager._conn.execute(
            "SELECT a.*, r.peer_identity, r.target_type, r.target_name "
            "FROM approval_request a LEFT JOIN remote_invocation_record r ON a.invocation_id=r.id "
            "WHERE a.status='pending' ORDER BY a.id DESC")
        return [dict(r) for r in rows]
