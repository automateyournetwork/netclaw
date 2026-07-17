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
    endpoint_updated_at TEXT,
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
-- feature 053: async delegated tasks (persisted so results survive channel
-- drops and daemon restarts, FR-004)
CREATE TABLE IF NOT EXISTS delegated_task (
    task_id         TEXT PRIMARY KEY,
    direction       TEXT NOT NULL,          -- inbound (we run it) | outbound (peer runs it)
    peer_identity   TEXT NOT NULL,          -- eN2N: as<AS>-<rid>; iN2N: <risk>/<member> (member_id)
    target_type     TEXT,                   -- skill | tool
    target_name     TEXT,
    input_text      TEXT,
    state           TEXT NOT NULL DEFAULT 'submitted',  -- submitted|working|completed|failed|cancelled
    progress        TEXT,
    result_ref      TEXT,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT,
    updated_at      TEXT,
    completed_at    TEXT,
    retention_until TEXT
);
-- feature 056: iN2N internal federation — a "risk" of claws.
-- This claw's own role in its risk (singleton row id=1).
CREATE TABLE IF NOT EXISTS risk (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    risk_name       TEXT,
    description     TEXT,
    role            TEXT NOT NULL DEFAULT 'standalone',  -- standalone|border|member
    enabled_stacks  TEXT,                   -- border only: en2n|in2n|both
    border_endpoint TEXT,                   -- member only: host:port it dials outbound
    self_member_id  TEXT,                   -- member only: <risk>/<name>
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
-- The Border's registry of its members (rows exist only on a Border).
CREATE TABLE IF NOT EXISTS member (
    member_id         TEXT PRIMARY KEY,     -- <risk>/<name>, stable across relocation
    display_name      TEXT,
    pinned_key        TEXT,                 -- member's self-signed public key (PEM), pinned TOFU
    key_fingerprint   TEXT,                 -- sha256 of the pinned public key
    profile           TEXT,                 -- cml|pyats|security|custom
    scope             TEXT,                 -- JSON: [{name,type,tier}] tier=base|specialty
    runtime_kind      TEXT,                 -- process|container
    transport_binding TEXT,                 -- loopback|distributed
    state             TEXT NOT NULL DEFAULT 'enrolled', -- enrolled|active|unreachable|quarantined|removed
    health            TEXT,                 -- JSON: last_seen, heartbeat, in_flight
    auth_failures     INTEGER NOT NULL DEFAULT 0,
    enrolled_at       TEXT,
    updated_at        TEXT
);
-- Single-use enrollment tokens issued by a Border (only the hash is stored).
CREATE TABLE IF NOT EXISTS enrollment_token (
    token_hash         TEXT PRIMARY KEY,
    label              TEXT,
    issued_at          TEXT NOT NULL,
    expires_at         TEXT,
    spent_at           TEXT,
    spent_by_member_id TEXT
);
"""


# feature 060: claw-certification tables. Kept separate from SCHEMA so the
# migration path (executescript after column ALTERs) is explicit and idempotent.
SCHEMA_060 = """
CREATE TABLE IF NOT EXISTS credential (
    credential_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    kind             TEXT NOT NULL,       -- acme | host-pinned | risk-ca | hub | member
    subject_identity TEXT NOT NULL,       -- claw domain, as<ASN>-<router-id>, risk name, member_id
    fingerprint      TEXT NOT NULL UNIQUE,-- SHA-256 over DER, hex
    issuer           TEXT,
    not_before       TEXT,
    not_after        TEXT,
    renew_after      TEXT,                -- issued + 2/3 lifetime (NULL for observed-only)
    state            TEXT NOT NULL DEFAULT 'active',  -- active | overlap | retired | failed
    cert_pem         TEXT,                -- PUBLIC cert only; private keys live under keys/
    key_path         TEXT,               -- path for locally-held keys, else NULL
    created_at       TEXT,
    updated_at       TEXT
);
CREATE TABLE IF NOT EXISTS rotation_event (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_identity TEXT,
    credential_id    INTEGER,
    kind             TEXT NOT NULL,       -- renewed|rotated|overlap-opened|overlap-closed|renewal-failed|emergency-rekey|verify-refused
    detail           TEXT,
    at               TEXT
);
CREATE TABLE IF NOT EXISTS auth_failure_bucket (
    source           TEXT PRIMARY KEY,    -- remote addr / channel origin of unauth failures
    member_id        TEXT,                -- asserted identity (informational)
    count            INTEGER NOT NULL DEFAULT 0,
    window_start     TEXT
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
        # Migrate existing DBs: add columns introduced after first release
        # (SQLite has no ADD COLUMN IF NOT EXISTS). Safe/idempotent.
        for table, col, decl in [
            ("federation_peer", "endpoint_updated_at", "TEXT"),
            # feature 056: discriminate internal vs external audit + link them
            ("remote_invocation_record", "channel_kind", "TEXT DEFAULT 'en2n'"),
            ("remote_invocation_record", "linked_record_id", "INTEGER"),
            # feature 056: how the Border cold-starts an on-demand member, and
            # whether it may (local spawnable) vs must wait for a remote member.
            ("member", "launch_cmd", "TEXT"),
            ("member", "on_demand", "INTEGER NOT NULL DEFAULT 0"),
            # feature 057: durable runtime + production enforcement.
            #   managed_by     — 'service' (own durable systemd unit) | 'cold' (spawn on route)
            #   service_unit   — the systemd unit name when managed_by='service'
            #   component_scan — cached DefenseClaw component-scan verdict for this
            #                    member: 'pass' | 'flagged:<what>' | NULL (not scanned)
            ("member", "managed_by", "TEXT NOT NULL DEFAULT 'cold'"),
            ("member", "service_unit", "TEXT"),
            ("member", "component_scan", "TEXT"),
            # feature 060: claw certification — channel trust state.
            #   trust_model     — 'domain-verified' | 'pinned' | 'legacy' (pre-060)
            #   claw_domain     — verified attribute of the unchanged identity key (FR-003a)
            #   pinned_fp       — SHA-256 pin (pinned model); pinned_fp_next during overlap
            #   peer_cred_*     — peer credential health last seen via heartbeat (FR-024)
            #   verify_state    — 'verified' | 'mismatch' | 'refused-pending-patch'
            ("federation_peer", "trust_model", "TEXT NOT NULL DEFAULT 'legacy'"),
            ("federation_peer", "claw_domain", "TEXT"),
            ("federation_peer", "pinned_fp", "TEXT"),
            ("federation_peer", "pinned_fp_next", "TEXT"),
            ("federation_peer", "peer_cred_fp", "TEXT"),
            ("federation_peer", "peer_cred_not_after", "TEXT"),
            ("federation_peer", "peer_renew_state", "TEXT"),
            ("federation_peer", "verify_state", "TEXT"),
            # feature 060: member credential provenance + health.
            #   credential_state — 'authority' (risk-CA-issued) | 'legacy' (pre-060 pin)
            ("member", "credential_state", "TEXT NOT NULL DEFAULT 'legacy'"),
            ("member", "cred_fp", "TEXT"),
            ("member", "cred_not_after", "TEXT"),
            ("member", "renew_state", "TEXT"),
            ("member", "enroll_fingerprint_logged", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            except sqlite3.OperationalError:
                pass  # column already exists
        # feature 060: new tables (credential registry, rotation audit, per-source
        # failed-auth rate limiting). additive + idempotent (data-model.md §1/4/5).
        self._conn.executescript(SCHEMA_060)
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
            # Feature 063 (P1): a written endpoint bumps the freshness signal the
            # reconnect supervisor and operator view read — do it here so every
            # persist path (operator dial, peer endpoint_update) is consistent.
            if endpoint_host is not None or endpoint_port is not None:
                sets.append("endpoint_updated_at=?"); vals.append(now)
            sets.append("updated_at=?"); vals.append(now)
            vals.append(ident)
            self._conn.execute(f"UPDATE federation_peer SET {','.join(sets)} WHERE identity=?", vals)
        else:
            endpoint_updated = now if (endpoint_host is not None or endpoint_port is not None) else None
            self._conn.execute(
                "INSERT INTO federation_peer (identity, peer_as, router_id, display_name, "
                "endpoint_host, endpoint_port, endpoint_updated_at, state, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ident, peer_as, router_id, display_name, endpoint_host, endpoint_port,
                 endpoint_updated, PeerState.NOT_FEDERATED.value, now, now))
        self._conn.commit()
        return ident

    def get_peer(self, ident: str) -> Optional[dict]:
        row = self._conn.execute("SELECT * FROM federation_peer WHERE identity=?", (ident,)).fetchone()
        return dict(row) if row else None

    def list_peers(self) -> list:
        return [dict(r) for r in self._conn.execute("SELECT * FROM federation_peer ORDER BY identity")]

    # ---- feature 060: per-peer channel trust ---------------------------

    def set_peer_pin(self, ident: str, pin_fp: str, *, is_next: bool = False):
        """Record a peer's pinned key fingerprint (pinned trust model). `is_next`
        stores the rotation-overlap successor pin (FR-013) instead of the active."""
        col = "pinned_fp_next" if is_next else "pinned_fp"
        self._conn.execute(
            f"UPDATE federation_peer SET {col}=?, updated_at=? WHERE identity=?",
            (pin_fp, _now(), ident))
        self._conn.commit()

    def set_peer_trust(self, ident: str, trust_model: str,
                       claw_domain: Optional[str] = None, verify_state: Optional[str] = None):
        """Set/upgrade a peer's trust model (local operator action only — FR-007).
        Records the claw_domain as a verified attribute of the unchanged identity."""
        sets, vals = ["trust_model=?"], [trust_model]
        if claw_domain is not None:
            sets.append("claw_domain=?"); vals.append(claw_domain)
        if verify_state is not None:
            sets.append("verify_state=?"); vals.append(verify_state)
        sets.append("updated_at=?"); vals.append(_now())
        vals.append(ident)
        self._conn.execute(
            f"UPDATE federation_peer SET {', '.join(sets)} WHERE identity=?", vals)
        self._conn.commit()

    def set_peer_cred_health(self, ident: str, fp: str, not_after: Optional[str],
                             renew_state: Optional[str]):
        """Store a peer's credential health as last reported via heartbeat (FR-024)."""
        self._conn.execute(
            "UPDATE federation_peer SET peer_cred_fp=?, peer_cred_not_after=?, "
            "peer_renew_state=?, updated_at=? WHERE identity=?",
            (fp, not_after, renew_state, _now(), ident))
        self._conn.commit()

    # ---- feature 060: credential registry (rotation, HUD) --------------

    def upsert_credential(self, *, kind: str, subject_identity: str, fingerprint: str,
                          issuer: Optional[str], not_before: Optional[str],
                          not_after: Optional[str], renew_after: Optional[str],
                          state: str = "active", cert_pem: Optional[str] = None,
                          key_path: Optional[str] = None) -> int:
        """Register/refresh a managed credential (keyed by fingerprint)."""
        now = _now()
        existing = self._conn.execute(
            "SELECT credential_id FROM credential WHERE fingerprint=?", (fingerprint,)).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE credential SET kind=?, subject_identity=?, issuer=?, not_before=?, "
                "not_after=?, renew_after=?, state=?, cert_pem=COALESCE(?,cert_pem), "
                "key_path=COALESCE(?,key_path), updated_at=? WHERE fingerprint=?",
                (kind, subject_identity, issuer, not_before, not_after, renew_after, state,
                 cert_pem, key_path, now, fingerprint))
            self._conn.commit()
            return existing["credential_id"]
        cur = self._conn.execute(
            "INSERT INTO credential (kind, subject_identity, fingerprint, issuer, not_before, "
            "not_after, renew_after, state, cert_pem, key_path, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (kind, subject_identity, fingerprint, issuer, not_before, not_after, renew_after,
             state, cert_pem, key_path, now, now))
        self._conn.commit()
        return cur.lastrowid

    def list_credentials(self) -> list:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM credential WHERE state != 'retired' ORDER BY not_after")]

    def credentials_due(self, now_iso: str) -> list:
        """Active credentials whose renew_after has passed (FR-012)."""
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM credential WHERE state='active' AND renew_after IS NOT NULL "
            "AND renew_after <= ? ORDER BY renew_after", (now_iso,))]

    def set_credential_state(self, fingerprint: str, state: str):
        self._conn.execute(
            "UPDATE credential SET state=?, updated_at=? WHERE fingerprint=?",
            (state, _now(), fingerprint))
        self._conn.commit()

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
