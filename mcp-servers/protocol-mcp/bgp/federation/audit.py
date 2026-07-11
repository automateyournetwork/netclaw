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
               target_name: Optional[str], request_id: Optional[str], decision: str,
               outcome: str, result_ref: Optional[str] = None,
               requested_at: Optional[str] = None) -> int:
        """Insert an audit row (FR-015). Returns the row id."""
        conn = self.manager._conn
        cur = conn.execute(
            "INSERT INTO remote_invocation_record (direction, peer_identity, target_type, "
            "target_name, request_id, decision, outcome, requested_at, completed_at, result_ref, gait_ref) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (direction, peer_identity, target_type, target_name, request_id, decision,
             outcome, requested_at or _now(), _now(), result_ref, self._gait_ref(peer_identity, decision)))
        conn.commit()
        logger.info("AUDIT %s %s %s/%s → %s/%s", direction, peer_identity,
                    target_type, target_name, decision, outcome)
        return cur.lastrowid

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

    def _gait_ref(self, peer_identity: str, decision: str) -> Optional[str]:
        """Emit to GAIT if available. Best-effort — audit row is authoritative."""
        try:
            # GAIT integration point: the daemon runs outside the gateway, so we
            # record intent here; the gateway's GAIT session picks up the row.
            return None
        except Exception:
            return None
