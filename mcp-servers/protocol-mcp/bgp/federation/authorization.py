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
    teardown: bool = False   # spec 189: this refusal started a limit teardown (informational)


LIMIT_ACTIONS = ("refuse", "warn", "teardown")   # spec 189 (default: refuse)
GLOBAL = "*"                                      # peer_limit_policy / budget_counter row for node-wide scope
_POLICY_INT_FIELDS = ("rate_per_min", "daily_requests", "daily_tokens", "restart_timer_s")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


class Authorizer:
    def __init__(self, manager):
        self.manager = manager
        self.rate_per_min = int(os.environ.get("N2N_RATE_PER_MIN", "10"))
        self.daily_requests = int(os.environ.get("N2N_DAILY_REQUESTS", "200"))
        self.daily_tokens = int(os.environ.get("N2N_DAILY_TOKENS", "500000"))
        self.approval_window_s = int(os.environ.get("N2N_APPROVAL_WINDOW_S", "900"))
        # spec 189: exceed policy defaults (refuse == pre-189 behavior)
        self.limit_action = os.environ.get("N2N_LIMIT_ACTION", "refuse")
        if self.limit_action not in LIMIT_ACTIONS:
            self.limit_action = "refuse"
        self.warn_threshold = _env_float("N2N_LIMIT_WARN_THRESHOLD", 0.8)
        if not 0 < self.warn_threshold <= 1:
            self.warn_threshold = 0.8
        self.restart_timer_s = int(_env_float("N2N_LIMIT_RESTART_S", 300))
        # optional aggregate caps (None = off); a '*' policy row takes precedence
        self.global_daily_requests = self._env_opt_int("N2N_GLOBAL_DAILY_REQUESTS")
        self.global_daily_tokens = self._env_opt_int("N2N_GLOBAL_DAILY_TOKENS")
        # set by FederationService: Auditor (limit events) and channel-close hook
        self.audit = None
        self.teardown_hook = None   # callable(peer_identity, reason)
        # peer_identity -> list of recent request epoch times (rate window)
        self._recent: dict = {}
        self._last_warned: dict = {}

    @staticmethod
    def _env_opt_int(name: str) -> Optional[int]:
        v = os.environ.get(name)
        try:
            return int(v) if v not in (None, "") else None
        except ValueError:
            return None

    # ---- limit policy (spec 189) --------------------------------------

    def _policy_row(self, peer_identity: str) -> dict:
        row = self.manager._conn.execute(
            "SELECT * FROM peer_limit_policy WHERE peer_identity=?", (peer_identity,)).fetchone()
        return dict(row) if row else {}

    def set_policy(self, peer_identity: str, **fields) -> dict:
        """Persist per-peer overrides (or node-wide for peer_identity='*').
        A value of None clears that field (inherit). Raises ValueError, changing nothing,
        on an invalid value."""
        allowed = set(_POLICY_INT_FIELDS) | {"action", "warn_threshold"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unknown limit field(s): {sorted(unknown)}")
        clean = {}
        for k, v in fields.items():
            if v is None:
                clean[k] = None
            elif k in _POLICY_INT_FIELDS:
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    raise ValueError(f"{k} must be a non-negative integer")
                clean[k] = v
            elif k == "action":
                if v not in LIMIT_ACTIONS:
                    raise ValueError(f"action must be one of {LIMIT_ACTIONS}")
                clean[k] = v
            elif k == "warn_threshold":
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v <= 1:
                    raise ValueError("warn_threshold must be in (0, 1]")
                clean[k] = float(v)
        cur = self._policy_row(peer_identity)
        cur.update(clean)
        cols = list(_POLICY_INT_FIELDS) + ["action", "warn_threshold"]
        self.manager._conn.execute(
            "INSERT OR REPLACE INTO peer_limit_policy (peer_identity, rate_per_min, daily_requests, "
            "daily_tokens, action, warn_threshold, restart_timer_s, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (peer_identity, cur.get("rate_per_min"), cur.get("daily_requests"), cur.get("daily_tokens"),
             cur.get("action"), cur.get("warn_threshold"), cur.get("restart_timer_s"), _now()))
        self.manager._conn.commit()
        self._limit_event(peer_identity, "limit_config", "policy", self._scope(peer_identity),
                          "success", detail=",".join(sorted(clean)))
        return self.get_policy(peer_identity)

    def clear_policy(self, peer_identity: str):
        self.manager._conn.execute("DELETE FROM peer_limit_policy WHERE peer_identity=?", (peer_identity,))
        self.manager._conn.commit()
        self._limit_event(peer_identity, "limit_config", "policy", self._scope(peer_identity), "cleared")

    @staticmethod
    def _scope(peer_identity: str) -> str:
        return "global" if peer_identity == GLOBAL else "peer"

    def get_policy(self, peer_identity: str) -> dict:
        """Effective policy: per-peer row > node-wide '*' row (action/threshold/restart only)
        > env/instance defaults. Global aggregate caps come from the '*' row, else env."""
        row = self._policy_row(peer_identity)
        node = self._policy_row(GLOBAL)

        def pick(field, base):
            for r in (row, node if field in ("action", "warn_threshold", "restart_timer_s") else {}):
                if r.get(field) is not None:
                    return r[field]
            return base
        return {
            "rate_per_min": pick("rate_per_min", self.rate_per_min),
            "daily_requests": pick("daily_requests", self.daily_requests),
            "daily_tokens": pick("daily_tokens", self.daily_tokens),
            "action": pick("action", self.limit_action),
            "warn_threshold": pick("warn_threshold", self.warn_threshold),
            "restart_timer_s": pick("restart_timer_s", self.restart_timer_s),
        }

    def global_caps(self) -> dict:
        node = self._policy_row(GLOBAL)
        return {"daily_requests": node["daily_requests"] if node.get("daily_requests") is not None
                else self.global_daily_requests,
                "daily_tokens": node["daily_tokens"] if node.get("daily_tokens") is not None
                else self.global_daily_tokens}

    def _limit_event(self, peer_identity, decision, limit, scope, outcome, detail=""):
        logger.warning("limit %s peer=%s limit=%s scope=%s outcome=%s %s",
                       decision, peer_identity, limit, scope, outcome, detail)
        if self.audit is None:
            return
        try:
            self.audit.record(direction="inbound", peer_identity=peer_identity, target_type="limit",
                              target_name=f"{limit}:{scope}", request_id=None,
                              decision=decision, outcome=outcome)
        except Exception:  # audit must never break admission
            logger.exception("limit audit write failed")

    # ---- hold-down (teardown restart timer) ---------------------------

    def hold_down_remaining(self, peer_identity: str) -> float:
        row = self.manager._conn.execute(
            "SELECT until_epoch FROM limit_hold_down WHERE peer_identity=?", (peer_identity,)).fetchone()
        if not row:
            return 0.0
        left = row["until_epoch"] - time.time()
        if left <= 0:
            self.manager._conn.execute("DELETE FROM limit_hold_down WHERE peer_identity=?", (peer_identity,))
            self.manager._conn.commit()
            return 0.0
        return left

    def clear_hold_down(self, peer_identity: str, actor: str = "operator"):
        self.manager._conn.execute("DELETE FROM limit_hold_down WHERE peer_identity=?", (peer_identity,))
        self.manager._conn.commit()
        self._limit_event(peer_identity, "limit_config", "hold_down", "peer", "cleared", detail=actor)

    def _teardown(self, peer_identity: str, pol: dict, limit: str):
        until = time.time() + pol["restart_timer_s"]
        self.manager._conn.execute(
            "INSERT OR REPLACE INTO limit_hold_down (peer_identity, until_epoch, reason, started_at) "
            "VALUES (?,?,?,?)", (peer_identity, until, f"limit:{limit}", _now()))
        self.manager._conn.commit()
        self._limit_event(peer_identity, "limit_teardown", limit, "peer", "teardown",
                          detail=f"hold_down_s={pol['restart_timer_s']}")
        if self.teardown_hook:
            try:
                self.teardown_hook(peer_identity, f"limit:{limit}")
            except Exception:
                logger.exception("teardown hook failed")

    def _exceed(self, peer_identity: str, limit: str, scope: str, reason: str,
                grant: Optional[dict], already_trusted: bool) -> Optional[Decision]:
        """Apply the peer's exceed action. Returns None when the request may proceed
        (warn) or the refusal Decision. `refuse` writes nothing extra: the caller's
        existing denied-audit row is the record (pre-189 behavior)."""
        pol = self.get_policy(peer_identity)
        code = "rate_limited" if limit == "rate" else "budget_exhausted"
        if pol["action"] == "warn":
            key = (peer_identity, limit)
            now = time.time()
            if now - self._last_warned.get(key, 0) > 5:   # one request can pass several gates
                self._last_warned[key] = now
                self._limit_event(peer_identity, "limit_exceeded_warned", limit, scope, "allowed")
            return None
        d = Decision(False, code, grant, reason)
        if pol["action"] == "teardown" and not already_trusted:
            d.teardown = True
            self._teardown(peer_identity, pol, limit)
        return d

    def _check_warning(self, peer_identity: str):
        """Edge-triggered per limit per UTC day warning at the configured threshold."""
        pol = self.get_policy(peer_identity)
        day = _today()
        b = self._budget_row(peer_identity)
        checks = [("requests", b["requests_used"], pol["daily_requests"], peer_identity),
                  ("tokens", b["tokens_used"], pol["daily_tokens"], peer_identity)]
        caps = self.global_caps()
        if caps["daily_requests"] is not None or caps["daily_tokens"] is not None:
            g = self._budget_row(GLOBAL)
            checks += [("global_requests", g["requests_used"], caps["daily_requests"], GLOBAL),
                       ("global_tokens", g["tokens_used"], caps["daily_tokens"], GLOBAL)]
        for name, used, limit, owner in checks:
            if not limit or used < limit * pol["warn_threshold"]:
                continue
            cur = self.manager._conn.execute(
                "INSERT OR IGNORE INTO limit_warning (peer_identity, day, limit_name, warned_at) "
                "VALUES (?,?,?,?)", (owner, day, name, _now()))
            self.manager._conn.commit()
            if cur.rowcount == 1:
                self._limit_event(peer_identity, "limit_warning", name,
                                  "global" if owner == GLOBAL else "peer", "warning",
                                  detail=f"used={used} limit={limit}")

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
        limit = self.get_policy(peer_identity)["rate_per_min"]
        window = [t for t in self._recent.get(peer_identity, []) if now - t < 60]
        if len(window) >= limit:
            self._recent[peer_identity] = window
            return False
        window.append(now)
        self._recent[peer_identity] = window
        return True

    def _note_rate_use(self, peer_identity: str):
        self._recent.setdefault(peer_identity, []).append(time.time())

    # ---- budget (FR-017) ----------------------------------------------

    def _budget_row(self, peer_identity: str) -> dict:
        day = _today()
        row = self.manager._conn.execute(
            "SELECT requests_used, tokens_used FROM budget_counter WHERE peer_identity=? AND day=?",
            (peer_identity, day)).fetchone()
        if not row:
            self.manager._conn.execute(
                "INSERT OR IGNORE INTO budget_counter (peer_identity, day) VALUES (?,?)", (peer_identity, day))
            self.manager._conn.commit()
            return {"requests_used": 0, "tokens_used": 0}
        return {"requests_used": row["requests_used"], "tokens_used": row["tokens_used"]}

    def _budget_breach(self, peer_identity: str) -> Optional[tuple]:
        """(limit_name, scope) of the first exhausted budget, or None. Peer first, then global."""
        pol = self.get_policy(peer_identity)
        b = self._budget_row(peer_identity)
        if b["requests_used"] >= pol["daily_requests"]:
            return ("requests", "peer")
        if b["tokens_used"] >= pol["daily_tokens"]:
            return ("tokens", "peer")
        caps = self.global_caps()
        if caps["daily_requests"] is not None or caps["daily_tokens"] is not None:
            g = self._budget_row(GLOBAL)
            if caps["daily_requests"] is not None and g["requests_used"] >= caps["daily_requests"]:
                return ("global_requests", "global")
            if caps["daily_tokens"] is not None and g["tokens_used"] >= caps["daily_tokens"]:
                return ("global_tokens", "global")
        return None

    def _check_budget(self, peer_identity: str) -> bool:
        return self._budget_breach(peer_identity) is None

    def _global_active(self) -> bool:
        caps = self.global_caps()
        return caps["daily_requests"] is not None or caps["daily_tokens"] is not None

    def debit(self, peer_identity: str, requests: int = 1, tokens: int = 0):
        day = _today()
        self._budget_row(peer_identity)  # ensure row exists
        self.manager._conn.execute(
            "UPDATE budget_counter SET requests_used=requests_used+?, tokens_used=tokens_used+? "
            "WHERE peer_identity=? AND day=?", (requests, tokens or 0, peer_identity, day))
        if self._global_active():
            self.manager._conn.execute(
                "INSERT OR IGNORE INTO budget_counter (peer_identity, day) VALUES (?,?)", (GLOBAL, day))
            self.manager._conn.execute(
                "UPDATE budget_counter SET requests_used=requests_used+?, tokens_used=tokens_used+? "
                "WHERE peer_identity=? AND day=?", (requests, tokens or 0, GLOBAL, day))
        self.manager._conn.commit()
        self._check_warning(peer_identity)

    def budget_status(self, peer_identity: str) -> dict:
        b = self._budget_row(peer_identity)
        pol = self.get_policy(peer_identity)
        return {"requests_used": b["requests_used"], "requests_limit": pol["daily_requests"],
                "tokens_used": b["tokens_used"], "tokens_limit": pol["daily_tokens"]}

    def limit_status(self, peer_identity: str) -> dict:
        """Operator/HUD view (spec 189 FR-012)."""
        pol = self.get_policy(peer_identity)
        b = self._budget_row(peer_identity)
        now = time.time()
        rate_used = len([t for t in self._recent.get(peer_identity, []) if now - t < 60])
        warned = [r["limit_name"] for r in self.manager._conn.execute(
            "SELECT limit_name FROM limit_warning WHERE peer_identity=? AND day=?",
            (peer_identity, _today()))]
        out = {"policy": pol, "has_override": bool(self._policy_row(peer_identity)),
               "requests_used": b["requests_used"], "tokens_used": b["tokens_used"],
               "rate_used": rate_used, "warned": sorted(warned),
               "hold_down_remaining_s": round(self.hold_down_remaining(peer_identity), 1)}
        if self._global_active():
            g = self._budget_row(GLOBAL)
            out["global"] = {"caps": self.global_caps(), "requests_used": g["requests_used"],
                             "tokens_used": g["tokens_used"]}
        return out

    def reset_limits(self, peer_identity: str, actor: str = "operator"):
        """Operator reset: today's counters, rate window, warning latch, hold-down."""
        c = self.manager._conn
        c.execute("DELETE FROM budget_counter WHERE peer_identity=? AND day=?", (peer_identity, _today()))
        c.execute("DELETE FROM limit_warning WHERE peer_identity=? AND day=?", (peer_identity, _today()))
        c.execute("DELETE FROM limit_hold_down WHERE peer_identity=?", (peer_identity,))
        c.commit()
        self._recent.pop(peer_identity, None)
        self._limit_event(peer_identity, "limit_reset", "all", self._scope(peer_identity), "reset", detail=actor)

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
        if not already_trusted and self.hold_down_remaining(peer_identity) > 0:
            self._limit_event(peer_identity, "limit_hold_down_refused", "hold_down", "peer", "denied")
            return Decision(False, "severed", reason="peer in limit hold-down")
        if not already_trusted and not self.manager.is_federated(peer_identity):
            return Decision(False, "severed", reason="peer not federated")
        grant = self._find_grant(peer_identity, target_type, target_name)
        if not grant:
            return Decision(False, "not_allowlisted",
                            reason=f"{target_type} '{target_name}' not allowlisted for {peer_identity}")
        if check_rate and not self._check_rate(peer_identity):
            refused = self._exceed(peer_identity, "rate", "peer", "per-minute rate limit exceeded",
                                   grant, already_trusted)
            if refused:
                return refused
            self._note_rate_use(peer_identity)   # warn: usage stays truthful
        breach = self._budget_breach(peer_identity)
        if breach:
            name, scope = breach
            refused = self._exceed(peer_identity, name, scope,
                                   "global daily budget exhausted" if scope == "global"
                                   else "daily budget exhausted", grant, already_trusted)
            if refused:
                return refused
        if grant["requires_approval"]:
            return Decision(False, "approval_required", grant, "human approval required")
        return Decision(True, "allowlisted", grant)

    def _try_reserve(self, peer_identity: str, pol: dict, unconditional: bool) -> bool:
        """One request unit against the peer (and global) counters, no commit."""
        db = self.manager._conn
        day = _today()
        db.execute("INSERT OR IGNORE INTO budget_counter (peer_identity, day) VALUES (?,?)", (peer_identity, day))
        if unconditional:
            cur = db.execute("UPDATE budget_counter SET requests_used=requests_used+1 "
                             "WHERE peer_identity=? AND day=?", (peer_identity, day))
        else:
            cur = db.execute(
                "UPDATE budget_counter SET requests_used=requests_used+1 "
                "WHERE peer_identity=? AND day=? AND requests_used<? AND tokens_used<?",
                (peer_identity, day, pol["daily_requests"], pol["daily_tokens"]))
        if cur.rowcount != 1:
            return False
        if self._global_active():
            db.execute("INSERT OR IGNORE INTO budget_counter (peer_identity, day) VALUES (?,?)", (GLOBAL, day))
            db.execute("UPDATE budget_counter SET requests_used=requests_used+1 WHERE peer_identity=? AND day=?",
                       (GLOBAL, day))
        return True

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
        pol = self.get_policy(peer_identity)
        if current.code=='approval_required':
            db=self.manager._conn
            db.execute('BEGIN IMMEDIATE')
            try:
                approved=db.execute("UPDATE approval_request SET consumed_at=? WHERE id=? AND status='approved' AND expires_at>? AND consumed_at IS NULL AND request_binding=?",
                    (_now(),original.approval_id,_now(),original.request_binding))
                if approved.rowcount!=1:
                    db.rollback()
                    return Decision(False,'approval_required',current.grant,'exact unexpired unused approval required')
                if not self._try_reserve(peer_identity, pol, pol["action"] == "warn"):
                    db.rollback()
                    breach = self._budget_breach(peer_identity) or ("requests", "peer")
                    return (self._exceed(peer_identity, breach[0], breach[1], "daily budget exhausted",
                                         current.grant, already_trusted)
                            or Decision(False,'budget_exhausted',current.grant,'daily budget exhausted'))
                db.commit()
            except BaseException:db.rollback();raise
            self._check_warning(peer_identity)
        elif not self.reserve_request(peer_identity, already_trusted=already_trusted):
            return Decision(False, "budget_exhausted", current.grant, "daily budget exhausted")
        return Decision(True, "allowlisted", current.grant)

    def still_authorized(self,peer,target_type,target,original,*,already_trusted=False):
        """Recheck an already reserved request without charging or reapproving it."""
        if not already_trusted and not self.manager.is_federated(peer):return False
        grant=self._find_grant(peer,target_type,target)
        if not grant or not original.grant or grant['id']!=original.grant['id']:return False
        pol=self.get_policy(peer)
        if pol["action"]!="warn" and self._budget_row(peer)['tokens_used']>=pol["daily_tokens"]:return False
        if grant['requires_approval']:
            row=self.manager._conn.execute('SELECT request_binding,consumed_at,status FROM approval_request WHERE id=?',(original.approval_id,)).fetchone()
            return bool(row and row['request_binding']==original.request_binding and row['consumed_at'] and row['status']=='approved')
        return True

    def reserve_request(self, peer_identity: str, *, already_trusted: bool = False) -> bool:
        """Reserve a request before asynchronous execution, including chat."""
        pol = self.get_policy(peer_identity)
        breach = self._budget_breach(peer_identity)
        unconditional = False
        if breach:
            name, scope = breach
            refused = self._exceed(peer_identity, name, scope, "daily budget exhausted",
                                   None, already_trusted)
            if refused:
                return False
            unconditional = True   # warn: let it through, keep counting
        ok = self._try_reserve(peer_identity, pol, unconditional)
        self.manager._conn.commit()
        if ok:
            self._check_warning(peer_identity)
        else:
            self._exceed(peer_identity, "requests", "peer", "daily budget exhausted", None, already_trusted)
        return ok

    def admit_chat(self, peer_identity: str) -> Decision:
        """Chat message admission: hold-down, rate, then one request unit (spec 189)."""
        if self.hold_down_remaining(peer_identity) > 0:
            self._limit_event(peer_identity, "limit_hold_down_refused", "hold_down", "peer", "denied")
            return Decision(False, "severed", reason="peer in limit hold-down")
        if not self._check_rate(peer_identity):
            refused = self._exceed(peer_identity, "rate", "peer", "chat rate limit exceeded", None, False)
            if refused:
                return refused
            self._note_rate_use(peer_identity)
        if not self.reserve_request(peer_identity):
            return Decision(False, "budget_exhausted", reason="daily budget exhausted")
        return Decision(True, "allowlisted")

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
