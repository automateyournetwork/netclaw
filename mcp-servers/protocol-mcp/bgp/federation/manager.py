"""Federation state: SQLite persistence, consent state machine, peer registry.

The FederationManager owns federation.db and the per-peer state transitions. It
is transport-agnostic — the channel layer calls into it for consent decisions
and lifecycle, and the daemon HTTP API calls into it for operator actions.

Identity is the BGP identity `as<AS>-<router-id>` (spec FR-002), so federation
state survives endpoint changes (FR-028). Persistence is SQLite so it survives
restarts.
"""

import json
import logging
import os
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("n2n.manager")


def peer_identity(peer_as: int, router_id: str) -> str:
    """Stable federation identity from BGP identity (FR-002)."""
    return f"as{peer_as}-{router_id}"


class PeerState(str, Enum):
    NOT_FEDERATED = "not_federated"
    CONSENT_PENDING_LOCAL = "consent_pending_local"    # remote consented; awaiting us
    CONSENT_PENDING_REMOTE = "consent_pending_remote"  # we consented; awaiting them
    FEDERATED = "federated"
    SEVERED = "severed"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


SCHEMA = """
CREATE TABLE IF NOT EXISTS federation_peer (
    identity      TEXT PRIMARY KEY,
    peer_as       INTEGER NOT NULL,
    router_id     TEXT NOT NULL,
    display_name  TEXT,
    endpoint_host TEXT,
    endpoint_port INTEGER,
    state         TEXT NOT NULL DEFAULT 'not_federated',
    chat_enabled  INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consent_record (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_identity TEXT NOT NULL,
    direction     TEXT NOT NULL,            -- local_grant | remote_grant
    granted_at    TEXT NOT NULL,
    revoked_at    TEXT
);
CREATE TABLE IF NOT EXISTS visibility_setting (
    item_type  TEXT NOT NULL,               -- skill | mcp_server
    item_name  TEXT NOT NULL,
    visibility TEXT NOT NULL,               -- all_federated | selected_peers | hidden
    peer_list  TEXT,                        -- JSON array when selected_peers
    PRIMARY KEY (item_type, item_name)
);
CREATE TABLE IF NOT EXISTS invocation_grant (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_identity    TEXT NOT NULL,
    target_type      TEXT NOT NULL,         -- tool | skill
    target_name      TEXT NOT NULL,
    requires_approval INTEGER NOT NULL DEFAULT 0,
    timeout_s        INTEGER,
    created_at       TEXT NOT NULL,
    revoked_at       TEXT
);
CREATE TABLE IF NOT EXISTS budget_counter (
    peer_identity TEXT NOT NULL,
    day           TEXT NOT NULL,            -- YYYY-MM-DD UTC
    requests_used INTEGER NOT NULL DEFAULT 0,
    tokens_used   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (peer_identity, day)
);
CREATE TABLE IF NOT EXISTS remote_invocation_record (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    direction     TEXT NOT NULL,            -- inbound | outbound
    peer_identity TEXT NOT NULL,
    target_type   TEXT,
    target_name   TEXT,
    request_id    TEXT,
    decision      TEXT,
    outcome       TEXT,
    requested_at  TEXT,
    completed_at  TEXT,
    result_ref    TEXT,
    gait_ref      TEXT
);
CREATE TABLE IF NOT EXISTS approval_request (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    invocation_id INTEGER,
    status        TEXT NOT NULL DEFAULT 'pending',   -- pending|approved|denied|expired
    requested_at  TEXT,
    resolved_at   TEXT,
    expires_at    TEXT,
    resolved_via  TEXT
);
CREATE TABLE IF NOT EXISTS n2n_chat_session (
    id               TEXT PRIMARY KEY,
    peer_identity    TEXT NOT NULL,
    direction        TEXT NOT NULL,         -- initiated | received
    started_at       TEXT,
    last_activity_at TEXT,
    message_count    INTEGER NOT NULL DEFAULT 0,
    transcript_ref   TEXT
);
"""


class FederationManager:
    def __init__(self, db_path: Optional[str] = None, base_dir: Optional[str] = None):
        base = Path(base_dir or os.path.expanduser("~/.openclaw/n2n"))
        base.mkdir(parents=True, exist_ok=True)
        (base / "inventories").mkdir(exist_ok=True)
        (base / "results").mkdir(exist_ok=True)
        (base / "chats").mkdir(exist_ok=True)
        self.base_dir = base
        self.db_path = db_path or str(base / "federation.db")
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        logger.info("FederationManager ready (db=%s)", self.db_path)

    # ---- peer registry ------------------------------------------------

    def upsert_peer(self, peer_as: int, router_id: str, display_name: Optional[str] = None,
                    endpoint_host: Optional[str] = None, endpoint_port: Optional[int] = None):
        ident = peer_identity(peer_as, router_id)
        now = _now()
        row = self._conn.execute("SELECT identity FROM federation_peer WHERE identity=?", (ident,)).fetchone()
        if row:
            sets, vals = [], []
            for col, val in (("display_name", display_name), ("endpoint_host", endpoint_host),
                             ("endpoint_port", endpoint_port)):
                if val is not None:
                    sets.append(f"{col}=?"); vals.append(val)
            sets.append("updated_at=?"); vals.append(now)
            vals.append(ident)
            self._conn.execute(f"UPDATE federation_peer SET {','.join(sets)} WHERE identity=?", vals)
        else:
            self._conn.execute(
                "INSERT INTO federation_peer (identity, peer_as, router_id, display_name, "
                "endpoint_host, endpoint_port, state, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (ident, peer_as, router_id, display_name, endpoint_host, endpoint_port,
                 PeerState.NOT_FEDERATED.value, now, now))
        self._conn.commit()
        return ident

    def get_peer(self, ident: str) -> Optional[dict]:
        row = self._conn.execute("SELECT * FROM federation_peer WHERE identity=?", (ident,)).fetchone()
        return dict(row) if row else None

    def list_peers(self) -> list:
        return [dict(r) for r in self._conn.execute("SELECT * FROM federation_peer ORDER BY identity")]

    def _set_state(self, ident: str, state: PeerState):
        self._conn.execute("UPDATE federation_peer SET state=?, updated_at=? WHERE identity=?",
                           (state.value, _now(), ident))
        self._conn.commit()

    # ---- consent state machine (FR-001) --------------------------------

    def _has_consent(self, ident: str, direction: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM consent_record WHERE peer_identity=? AND direction=? AND revoked_at IS NULL",
            (ident, direction)).fetchone()
        return row is not None

    def _record_consent(self, ident: str, direction: str):
        if not self._has_consent(ident, direction):
            self._conn.execute(
                "INSERT INTO consent_record (peer_identity, direction, granted_at) VALUES (?,?,?)",
                (ident, direction, _now()))
            self._conn.commit()

    def _recompute_state(self, ident: str) -> PeerState:
        """Derive state from consent records. Federated requires both directions."""
        local = self._has_consent(ident, "local_grant")
        remote = self._has_consent(ident, "remote_grant")
        peer = self.get_peer(ident)
        if peer and peer["state"] == PeerState.SEVERED.value and not local:
            state = PeerState.SEVERED
        elif local and remote:
            state = PeerState.FEDERATED
        elif local and not remote:
            state = PeerState.CONSENT_PENDING_REMOTE
        elif remote and not local:
            state = PeerState.CONSENT_PENDING_LOCAL
        else:
            state = PeerState.NOT_FEDERATED
        self._set_state(ident, state)
        return state

    def local_consent(self, peer_as: int, router_id: str, display_name: Optional[str] = None) -> PeerState:
        """Operator consents to federate with a peer (FR-001)."""
        ident = self.upsert_peer(peer_as, router_id, display_name)
        # Re-consent after sever clears the severed marker
        self._conn.execute("UPDATE federation_peer SET state=? WHERE identity=? AND state=?",
                           (PeerState.NOT_FEDERATED.value, ident, PeerState.SEVERED.value))
        self._record_consent(ident, "local_grant")
        return self._recompute_state(ident)

    def remote_consent(self, peer_as: int, router_id: str) -> PeerState:
        """Record that the peer has consented to us (learned over the channel)."""
        ident = self.upsert_peer(peer_as, router_id)
        self._record_consent(ident, "remote_grant")
        return self._recompute_state(ident)

    def is_federated(self, ident: str) -> bool:
        peer = self.get_peer(ident)
        return bool(peer and peer["state"] == PeerState.FEDERATED.value)

    def sever(self, ident: str) -> bool:
        """Kill switch (FR-004): revoke local consent, purge cached inventory,
        mark severed. Does NOT touch BGP — caller drops only the NCFED channel."""
        peer = self.get_peer(ident)
        if not peer:
            return False
        now = _now()
        self._conn.execute(
            "UPDATE consent_record SET revoked_at=? WHERE peer_identity=? AND revoked_at IS NULL",
            (now, ident))
        self._set_state(ident, PeerState.SEVERED)
        # Purge cached remote inventory
        inv = self.base_dir / "inventories" / f"{ident}.json"
        inv.unlink(missing_ok=True)
        (self.base_dir / "inventories" / f"{ident}.meta.json").unlink(missing_ok=True)
        logger.info("Severed federation with %s (BGP untouched)", ident)
        return True

    # ---- chat enablement (FR-018) --------------------------------------

    def set_chat_enabled(self, ident: str, enabled: bool):
        self._conn.execute("UPDATE federation_peer SET chat_enabled=?, updated_at=? WHERE identity=?",
                           (1 if enabled else 0, _now(), ident))
        self._conn.commit()

    def close(self):
        self._conn.close()
