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
            "WHERE peer_identity=? AND day=?", (requests, tokens, peer_identity, day))
        self.manager._conn.commit()

    def budget_status(self, peer_identity: str) -> dict:
        b = self._budget_row(peer_identity)
        return {"requests_used": b["requests_used"], "requests_limit": self.daily_requests,
                "tokens_used": b["tokens_used"], "tokens_limit": self.daily_tokens}

    # ---- the decision (FR-012/013/017) --------------------------------

    def authorize(self, peer_identity: str, target_type: str, target_name: str) -> Decision:
        if not self.manager.is_federated(peer_identity):
            return Decision(False, "severed", reason="peer not federated")
        grant = self._find_grant(peer_identity, target_type, target_name)
        if not grant:
            return Decision(False, "not_allowlisted",
                            reason=f"{target_type} '{target_name}' not allowlisted for {peer_identity}")
        if not self._check_rate(peer_identity):
            return Decision(False, "rate_limited", grant, "per-minute rate limit exceeded")
        if not self._check_budget(peer_identity):
            return Decision(False, "budget_exhausted", grant, "daily budget exhausted")
        if grant["requires_approval"]:
            return Decision(False, "approval_required", grant, "human approval required")
        return Decision(True, "allowlisted", grant)

    # ---- approvals (FR-013) -------------------------------------------

    def create_approval(self, invocation_id: int) -> dict:
        expires = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                time.gmtime(time.time() + self.approval_window_s))
        cur = self.manager._conn.execute(
            "INSERT INTO approval_request (invocation_id, status, requested_at, expires_at) "
            "VALUES (?,?,?,?)", (invocation_id, "pending", _now(), expires))
        self.manager._conn.commit()
        return {"approval_id": cur.lastrowid, "expires_at": expires}

    def resolve_approval(self, approval_id: int, action: str, via: str = "cli") -> bool:
        status = "approved" if action == "approve" else "denied"
        self.manager._conn.execute(
            "UPDATE approval_request SET status=?, resolved_at=?, resolved_via=? "
            "WHERE id=? AND status='pending'", (status, _now(), via, approval_id))
        self.manager._conn.commit()
        return True

    def approval_status(self, approval_id: int) -> str:
        row = self.manager._conn.execute(
            "SELECT status, expires_at FROM approval_request WHERE id=?", (approval_id,)).fetchone()
        if not row:
            return "unknown"
        if row["status"] == "pending" and row["expires_at"] < _now():
            self.manager._conn.execute(
                "UPDATE approval_request SET status='expired' WHERE id=?", (approval_id,))
            self.manager._conn.commit()
            return "expired"
        return row["status"]

    def pending_approvals(self) -> list:
        rows = self.manager._conn.execute(
            "SELECT a.*, r.peer_identity, r.target_type, r.target_name "
            "FROM approval_request a LEFT JOIN remote_invocation_record r ON a.invocation_id=r.id "
            "WHERE a.status='pending' ORDER BY a.id DESC")
        return [dict(r) for r in rows]
