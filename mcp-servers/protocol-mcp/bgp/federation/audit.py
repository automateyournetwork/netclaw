"""Dual-side audit records for N2N invocations and chat (FR-015, FR-022).

Writes remote_invocation_record rows to federation.db and stores result payloads
under ~/.openclaw/n2n/results/. Emits a GAIT reference per Constitution IV when
a GAIT hook is available; otherwise records the intent in the row for later
reconciliation.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("n2n.audit")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Auditor:
    def __init__(self, manager):
        self.manager = manager
        self.results_dir = manager.base_dir / "results"
        # GAIT trail lives beside the SQLite DB (per-manager), so it is isolated
        # in tests and equals ~/.openclaw/n2n/gait for a live Border (feature 057).
        self.gait_dir = manager.base_dir / "gait"

    def store_result(self, request_id: str, payload) -> str:
        """Persist a result payload, return its file reference."""
        safe = request_id.replace("/", "_").replace(":", "_")
        path = self.results_dir / f"{safe}.json"
        try:
            path.write_text(json.dumps(payload, default=str, indent=2))
        except Exception as e:
            logger.warning("Could not store result %s: %s", request_id, e)
        return str(path)

    def record(self, *, direction: str, peer_identity: str, target_type: Optional[str],
               target_name: Optional[str], request_id: Optional[str] = None, decision: str,
               outcome: str, result_ref: Optional[str] = None,
               requested_at: Optional[str] = None, channel_kind: str = "en2n",
               linked_record_id: Optional[int] = None,
               event: Optional[str] = None, actor: Optional[str] = None) -> int:
        """Insert an audit row (FR-015; feature 056 adds channel_kind + linking).

        `channel_kind` discriminates eN2N vs iN2N so the Border's one audit query
        covers both tiers (FR-024). `linked_record_id` joins an external request
        to the internal delegation it triggered (FR-025).

        Feature 057 (C2): `event` (delegation|enrollment|removal|quarantine) and
        `actor` thread through to the GAIT git immutable trail. When omitted, the
        event type is inferred from the decision so existing 056 callers keep
        working without a git commit being mislabeled."""
        conn = self.manager._conn
        row_id = None
        # Insert first (SQLite is authoritative) so we can cross-reference the row id.
        cur = conn.execute(
            "INSERT INTO remote_invocation_record (direction, peer_identity, target_type, "
            "target_name, request_id, decision, outcome, requested_at, completed_at, "
            "result_ref, gait_ref, channel_kind, linked_record_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (direction, peer_identity, target_type, target_name, request_id, decision,
             outcome, requested_at or _now(), _now(), result_ref,
             None, channel_kind, linked_record_id))
        row_id = cur.lastrowid
        conn.commit()
        # Best-effort immutable GAIT commit (Constitution IV); never blocks the row.
        gait_ref = self._gait_ref(
            peer_identity=peer_identity, decision=decision, event=event, actor=actor,
            target=target_name, channel_kind=channel_kind, row_id=row_id)
        if gait_ref:
            conn.execute("UPDATE remote_invocation_record SET gait_ref=? WHERE id=?",
                         (gait_ref, row_id))
            conn.commit()
        logger.info("AUDIT[%s] %s %s %s/%s → %s/%s%s", channel_kind, direction, peer_identity,
                    target_type, target_name, decision, outcome,
                    f" gait={gait_ref[:10]}" if gait_ref else "")
        return row_id

    def recent(self, peer_identity: Optional[str] = None, limit: int = 50) -> list:
        conn = self.manager._conn
        if peer_identity:
            rows = conn.execute(
                "SELECT * FROM remote_invocation_record WHERE peer_identity=? "
                "ORDER BY id DESC LIMIT ?", (peer_identity, limit))
        else:
            rows = conn.execute(
                "SELECT * FROM remote_invocation_record ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    # Map an audit decision to a GAIT event type when the caller didn't specify.
    _DECISION_EVENT = {
        "enrolled": "enrollment", "enroll": "enrollment",
        "removed": "removal", "remove": "removal",
        "quarantined": "quarantine", "quarantine": "quarantine",
    }

    def _gait_ref(self, *, peer_identity: str, decision: str, event: Optional[str] = None,
                  actor: Optional[str] = None, target: Optional[str] = None,
                  channel_kind: str = "en2n", row_id: Optional[int] = None) -> Optional[str]:
        """Emit an immutable GAIT git commit for this federation event and return
        its SHA (stored in the gait_ref column). Best-effort — the SQLite row is
        authoritative and a GAIT failure only drives posture degraded in
        production (feature 057, Constitution IV / FR-010..012)."""
        try:
            from . import gait
            ev = event or self._DECISION_EVENT.get(decision, "delegation")
            return gait.emit(ev, actor=actor or "border", subject=peer_identity,
                             target=target, channel_kind=channel_kind, sqlite_row_id=row_id,
                             gait_dir=self.gait_dir)
        except Exception:
            return None
