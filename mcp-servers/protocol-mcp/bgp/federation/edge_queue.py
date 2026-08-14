"""Store-and-forward queue for pushes to a disconnected NCFED edge node.

Why this exists: feature 066's delivery model is "live WS if the phone is
connected, platform push notification if it isn't" (FR-011). That leaves a
real gap on iOS when no APNs credentials exist — and an Apple Developer
account is a hard prerequisite for APNs, not something the Border can work
around. Without one, iOS suspends the app's WebSocket the moment it
backgrounds, nothing can wake it, and every push aimed at that device was
simply dropped with `delivered: False`.

So the third tier is this queue: when neither live delivery nor a platform
push can reach the device, the message is persisted instead of discarded and
replayed the next time that member's channel comes up. The phone's existing
MessageFeedStore + local-notification path (features 066/073) then surfaces
the backlog exactly like live traffic, so the operator sees what they missed
on the next app open rather than never.

This is deliberately NOT a general mesh-message queue. It only ever holds
content that already went through `/n2n/edge/push` — the single audited,
explicitly-designated Border-to-phone path — so queueing cannot become a
back door that mirrors ordinary channel traffic to a device.

Bounded by design (a phone can stay off for weeks): per-member depth cap and
a TTL, both enforced on every enqueue, so the table cannot grow without limit
on the shared federation.db.
"""

import json
import logging
import os
import time
from typing import List, Optional

logger = logging.getLogger("n2n.edge_queue")

SCHEMA_EDGE_QUEUE = """
CREATE TABLE IF NOT EXISTS edge_message_queue (
    queue_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id    TEXT NOT NULL,
    payload      TEXT NOT NULL,     -- the exact push dict /n2n/edge/push built
    reason       TEXT,              -- why it could not be delivered live
    enqueued_at  REAL NOT NULL,
    attempts     INTEGER NOT NULL DEFAULT 0,
    delivered_at REAL               -- NULL while pending
);
CREATE INDEX IF NOT EXISTS idx_edge_queue_pending
    ON edge_message_queue (member_id, delivered_at, queue_id);
"""

# A phone that has been off for a month should not replay a month of
# heartbeats on the next open, and must never be able to grow the shared DB
# without bound. Newest-wins on overflow: the most recent status is the one
# worth seeing.
DEFAULT_MAX_PER_MEMBER = 50
DEFAULT_TTL_SECONDS = 7 * 24 * 3600


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


class EdgeQueue:
    """Pending Border-to-phone messages, on the shared FederationManager DB.

    Shares the FederationManager sqlite connection exactly as RiskManager
    does — one DB, one connection, no second store (matching the 060/065
    convention of extending federation.db rather than adding a datastore).
    """

    def __init__(self, manager):
        self.m = manager
        self._conn = manager._conn
        self._conn.executescript(SCHEMA_EDGE_QUEUE)
        self._conn.commit()
        self.max_per_member = _int_env("N2N_EDGE_QUEUE_MAX", DEFAULT_MAX_PER_MEMBER)
        self.ttl_seconds = _int_env("N2N_EDGE_QUEUE_TTL_S", DEFAULT_TTL_SECONDS)

    # ---- write --------------------------------------------------------

    def enqueue(self, member_id: str, payload: dict, reason: str = "") -> int:
        """Persist one undeliverable push. Returns its queue_id.

        Called only from the `/n2n/edge/push` failure path, after both live
        delivery and the platform push fallback have been tried.
        """
        now = time.time()
        cur = self._conn.execute(
            "INSERT INTO edge_message_queue (member_id, payload, reason, enqueued_at) "
            "VALUES (?, ?, ?, ?)",
            (member_id, json.dumps(payload), reason[:500], now))
        self._conn.commit()
        self._prune(member_id, now)
        logger.info("Queued undeliverable push for %s (reason=%s, depth=%d)",
                    member_id, reason or "unknown", self.depth(member_id))
        return cur.lastrowid

    def mark_delivered(self, queue_id: int):
        self._conn.execute(
            "UPDATE edge_message_queue SET delivered_at=? WHERE queue_id=?",
            (time.time(), queue_id))
        self._conn.commit()

    def bump_attempt(self, queue_id: int):
        self._conn.execute(
            "UPDATE edge_message_queue SET attempts=attempts+1 WHERE queue_id=?",
            (queue_id,))
        self._conn.commit()

    def _prune(self, member_id: str, now: float):
        """Enforce the TTL and the per-member depth cap, and drop delivered
        rows — the queue is a delivery buffer, not an audit log (the audit
        trail for every push already lives in `remote_invocation_record` via
        FederationService.push_to_edge)."""
        self._conn.execute(
            "DELETE FROM edge_message_queue WHERE delivered_at IS NOT NULL")
        self._conn.execute(
            "DELETE FROM edge_message_queue WHERE enqueued_at < ?",
            (now - self.ttl_seconds,))
        # Newest-wins overflow: keep the most recent max_per_member pending.
        self._conn.execute(
            "DELETE FROM edge_message_queue WHERE member_id=? AND delivered_at IS NULL "
            "AND queue_id NOT IN ("
            "  SELECT queue_id FROM edge_message_queue"
            "  WHERE member_id=? AND delivered_at IS NULL"
            "  ORDER BY queue_id DESC LIMIT ?)",
            (member_id, member_id, self.max_per_member))
        self._conn.commit()

    # ---- read ---------------------------------------------------------

    def pending(self, member_id: str, limit: Optional[int] = None) -> List[dict]:
        """Oldest-first pending messages for one member, so a replay reads in
        the order the operator would have received them."""
        sql = ("SELECT queue_id, payload, reason, enqueued_at, attempts "
               "FROM edge_message_queue "
               "WHERE member_id=? AND delivered_at IS NULL ORDER BY queue_id ASC")
        params: tuple = (member_id,)
        if limit:
            sql += " LIMIT ?"
            params = (member_id, limit)
        out = []
        for row in self._conn.execute(sql, params).fetchall():
            try:
                payload = json.loads(row[1])
            except (TypeError, ValueError):
                logger.warning("Dropping queue row %s with unparseable payload", row[0])
                continue
            out.append({"queue_id": row[0], "payload": payload, "reason": row[2],
                        "enqueued_at": row[3], "attempts": row[4]})
        return out

    def purge_member(self, member_id: str) -> int:
        """Drop every queued row for a member. Returns how many were removed.

        Called when an enrollment is retired (FR-017). Without this, retiring a
        device leaves its undelivered backlog behind forever: the rows are keyed
        by `member_id`, and a re-enrolled phone gets a *new* member_id, so
        nothing will ever claim them. The TTL would eventually reap them, but a
        retired device's pending content should not linger for days, and the
        operator should not have to reach for sqlite3 to clear it.
        """
        cur = self._conn.execute(
            "DELETE FROM edge_message_queue WHERE member_id=?", (member_id,))
        self._conn.commit()
        removed = cur.rowcount or 0
        if removed:
            logger.info("Purged %d queued message(s) for retired member %s",
                        removed, member_id)
        return removed

    def depth(self, member_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM edge_message_queue "
            "WHERE member_id=? AND delivered_at IS NULL", (member_id,)).fetchone()
        return int(row[0]) if row else 0

    def depths(self) -> dict:
        """Pending depth per member — for /n2n/health and the HUD, so a
        silently-accumulating backlog is visible rather than implicit."""
        return {r[0]: int(r[1]) for r in self._conn.execute(
            "SELECT member_id, COUNT(*) FROM edge_message_queue "
            "WHERE delivered_at IS NULL GROUP BY member_id").fetchall()}
