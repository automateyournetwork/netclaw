"""
SQLite Storage Backend for Memory MCP Server.

Provides structured storage for facts, decisions, and graph links with:
- WAL mode for concurrent access
- Entity name normalization (lowercase)
- Temporal validity for facts
- Write serialization via threading lock
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("MemoryMCP.SQLite")

# Validation constants
MAX_ENTITY_LENGTH = 255
MAX_KEY_LENGTH = 255
MAX_VALUE_LENGTH = 10000
MAX_CONTEXT_LENGTH = 5000
MAX_DECISION_LENGTH = 2000
MAX_RATIONALE_LENGTH = 5000
MAX_PREDICATE_LENGTH = 100

# CR number pattern
CR_PATTERN = re.compile(r"^CHG\d+$")

# Predicate pattern (lowercase alphanumeric + underscore)
PREDICATE_PATTERN = re.compile(r"^[a-z0-9_]+$")


def normalize_entity(entity: str) -> str:
    """Normalize entity name to lowercase for consistent matching."""
    return entity.strip().lower()


def validate_entity(entity: str) -> Tuple[bool, Optional[str]]:
    """Validate entity name. Returns (is_valid, error_message)."""
    if not entity or not entity.strip():
        return False, "Entity name cannot be empty"
    if len(entity) > MAX_ENTITY_LENGTH:
        return False, f"Entity name exceeds {MAX_ENTITY_LENGTH} characters"
    return True, None


def validate_key(key: str) -> Tuple[bool, Optional[str]]:
    """Validate fact key. Returns (is_valid, error_message)."""
    if not key or not key.strip():
        return False, "Key cannot be empty"
    if len(key) > MAX_KEY_LENGTH:
        return False, f"Key exceeds {MAX_KEY_LENGTH} characters"
    return True, None


def validate_value(value: str) -> Tuple[bool, Optional[str]]:
    """Validate fact value. Returns (is_valid, error_message)."""
    if not value:
        return False, "Value cannot be empty"
    if len(value) > MAX_VALUE_LENGTH:
        return False, f"Value exceeds {MAX_VALUE_LENGTH} characters"
    return True, None


def validate_metadata(metadata: Optional[Dict]) -> Tuple[bool, Optional[str]]:
    """Validate metadata is valid JSON-serializable dict."""
    if metadata is None:
        return True, None
    if not isinstance(metadata, dict):
        return False, "Metadata must be a dictionary"
    try:
        json.dumps(metadata)
        return True, None
    except (TypeError, ValueError) as e:
        return False, f"Metadata is not valid JSON: {e}"


def validate_timestamp(ts: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate ISO timestamp format."""
    if ts is None:
        return True, None
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return True, None
    except ValueError:
        return False, f"Invalid ISO timestamp format: {ts}"


def validate_predicate(predicate: str) -> Tuple[bool, Optional[str]]:
    """Validate predicate format (lowercase alphanumeric + underscore)."""
    if not predicate or not predicate.strip():
        return False, "Predicate cannot be empty"
    if len(predicate) > MAX_PREDICATE_LENGTH:
        return False, f"Predicate exceeds {MAX_PREDICATE_LENGTH} characters"
    if not PREDICATE_PATTERN.match(predicate):
        return False, "Predicate must be lowercase alphanumeric with underscores only"
    return True, None


def validate_cr_number(cr_number: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate ServiceNow CR number format (CHG followed by digits)."""
    if cr_number is None:
        return True, None
    if not CR_PATTERN.match(cr_number):
        return False, "CR number must match pattern CHG followed by digits (e.g., CHG0001234)"
    return True, None


def utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_id() -> str:
    """Generate a random hex ID."""
    return os.urandom(8).hex()


class SQLiteStore:
    """SQLite storage backend with write serialization."""

    def __init__(self, db_path: str):
        """Initialize SQLite store with database path."""
        self.db_path = db_path
        self._write_lock = threading.Lock()
        self._local = threading.local()
        self._ensure_directory()
        self._init_schema()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode
            )
            self._local.conn.row_factory = sqlite3.Row
            # Enable WAL mode
            self._local.conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn.execute("PRAGMA synchronous = NORMAL")
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Context manager for write transactions with lock."""
        with self._write_lock:
            conn = self._get_connection()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def _init_schema(self) -> None:
        """Initialize database schema."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            schema_sql = schema_path.read_text()
        else:
            # Inline schema as fallback (simpler version without DEFAULT expressions)
            schema_sql = """
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                entity TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                metadata TEXT,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(entity, key, valid_from)
            );

            CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity);
            CREATE INDEX IF NOT EXISTS idx_facts_entity_key ON facts(entity, key);
            CREATE INDEX IF NOT EXISTS idx_facts_valid ON facts(valid_from, valid_to);

            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                context TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT NOT NULL,
                entities TEXT NOT NULL,
                cr_number TEXT,
                gait_ref TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at);

            CREATE TABLE IF NOT EXISTS graph_links (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(subject, predicate, object)
            );

            CREATE INDEX IF NOT EXISTS idx_links_subject ON graph_links(subject);
            CREATE INDEX IF NOT EXISTS idx_links_object ON graph_links(object);
            CREATE INDEX IF NOT EXISTS idx_links_predicate ON graph_links(predicate);
            """

        conn = self._get_connection()
        try:
            # Use executescript() to properly handle multiple statements
            # (split by semicolon doesn't work with DEFAULT expressions containing parens)
            conn.executescript(schema_sql)
        except sqlite3.Error as e:
            log.warning(f"Schema initialization failed: {e}")

    def check_integrity(self) -> Tuple[bool, str]:
        """Run integrity check on database."""
        conn = self._get_connection()
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] == "ok":
            return True, "Database integrity check passed"
        return False, f"Database integrity check failed: {result[0]}"

    # -------------------------------------------------------------------------
    # Facts
    # -------------------------------------------------------------------------

    def insert_fact(
        self,
        entity: str,
        key: str,
        value: str,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new fact, superseding any existing fact with same entity+key.

        Returns dict with id, entity, key, value, metadata, valid_from, valid_to, superseded_id.
        """
        # Validate inputs
        valid, err = validate_entity(entity)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_ENTITY", "message": err}}

        valid, err = validate_key(key)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_KEY", "message": err}}

        valid, err = validate_value(value)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_VALUE", "message": err}}

        valid, err = validate_metadata(metadata)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_METADATA", "message": err}}

        normalized_entity = normalize_entity(entity)
        now = utc_now()
        new_id = generate_id()
        metadata_json = json.dumps(metadata) if metadata else None
        superseded_id = None

        with self._transaction() as conn:
            # Check for existing current fact
            existing = conn.execute(
                """
                SELECT id FROM facts
                WHERE entity = ? AND key = ? AND valid_to IS NULL
                """,
                (normalized_entity, key),
            ).fetchone()

            if existing:
                # Supersede the existing fact
                superseded_id = existing["id"]
                conn.execute(
                    "UPDATE facts SET valid_to = ? WHERE id = ?",
                    (now, superseded_id),
                )

            # Insert new fact
            conn.execute(
                """
                INSERT INTO facts (id, entity, key, value, metadata, valid_from, valid_to, created_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (new_id, normalized_entity, key, value, metadata_json, now, now),
            )

        return {
            "success": True,
            "data": {
                "id": new_id,
                "entity": normalized_entity,
                "key": key,
                "value": value,
                "metadata": metadata,
                "valid_from": now,
                "valid_to": None,
                "superseded_id": superseded_id,
            },
        }

    def get_current_facts(
        self, entity: str, key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current (non-invalidated) facts for an entity.

        Returns dict with entity, facts list, count.
        """
        valid, err = validate_entity(entity)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_ENTITY", "message": err}}

        normalized_entity = normalize_entity(entity)
        conn = self._get_connection()

        if key:
            rows = conn.execute(
                """
                SELECT id, key, value, metadata, valid_from
                FROM facts
                WHERE entity = ? AND key = ? AND valid_to IS NULL
                ORDER BY created_at DESC
                """,
                (normalized_entity, key),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, key, value, metadata, valid_from
                FROM facts
                WHERE entity = ? AND valid_to IS NULL
                ORDER BY created_at DESC
                """,
                (normalized_entity,),
            ).fetchall()

        facts = []
        for row in rows:
            metadata = json.loads(row["metadata"]) if row["metadata"] else None
            facts.append({
                "id": row["id"],
                "key": row["key"],
                "value": row["value"],
                "metadata": metadata,
                "valid_from": row["valid_from"],
            })

        return {
            "success": True,
            "data": {
                "entity": normalized_entity,
                "facts": facts,
                "count": len(facts),
            },
        }

    def invalidate_fact(self, fact_id: str, reason: str) -> Dict[str, Any]:
        """
        Explicitly invalidate a fact with a reason.

        Returns dict with id, entity, key, valid_to, invalidation_reason.
        """
        if not reason or not reason.strip():
            return {"success": False, "error": {"code": "INVALID_REASON", "message": "Reason cannot be empty"}}

        conn = self._get_connection()

        # Check if fact exists
        row = conn.execute(
            "SELECT id, entity, key, valid_to, metadata FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()

        if not row:
            return {"success": False, "error": {"code": "FACT_NOT_FOUND", "message": f"No fact with ID {fact_id}"}}

        if row["valid_to"] is not None:
            return {"success": False, "error": {"code": "ALREADY_INVALIDATED", "message": "Fact already invalidated"}}

        now = utc_now()

        # Update metadata with invalidation reason
        existing_metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        existing_metadata["invalidation_reason"] = reason
        new_metadata = json.dumps(existing_metadata)

        with self._transaction() as conn:
            conn.execute(
                "UPDATE facts SET valid_to = ?, metadata = ? WHERE id = ?",
                (now, new_metadata, fact_id),
            )

        return {
            "success": True,
            "data": {
                "id": fact_id,
                "entity": row["entity"],
                "key": row["key"],
                "valid_to": now,
                "invalidation_reason": reason,
            },
        }

    def get_timeline(
        self,
        entity: str,
        after: Optional[str] = None,
        before: Optional[str] = None,
        key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get historical facts including invalidated ones within a time range.

        Returns dict with entity, timeline list, count.
        """
        valid, err = validate_entity(entity)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_ENTITY", "message": err}}

        if after:
            valid, err = validate_timestamp(after)
            if not valid:
                return {"success": False, "error": {"code": "INVALID_TIMESTAMP", "message": err}}

        if before:
            valid, err = validate_timestamp(before)
            if not valid:
                return {"success": False, "error": {"code": "INVALID_TIMESTAMP", "message": err}}

        if after and before:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
            before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
            if after_dt > before_dt:
                return {"success": False, "error": {"code": "INVALID_RANGE", "message": "after must be before before"}}

        normalized_entity = normalize_entity(entity)
        conn = self._get_connection()

        # Build query
        query = "SELECT id, key, value, metadata, valid_from, valid_to FROM facts WHERE entity = ?"
        params: List[Any] = [normalized_entity]

        if key:
            query += " AND key = ?"
            params.append(key)

        if after:
            query += " AND valid_from >= ?"
            params.append(after)

        if before:
            query += " AND (valid_to IS NULL OR valid_to <= ?)"
            params.append(before)

        # Default to last 30 days if no range specified
        if not after and not before:
            default_after = datetime.now(timezone.utc).replace(day=1).isoformat().replace("+00:00", "Z")
            # Actually, let's just return all for simplicity in timeline
            pass

        query += " ORDER BY valid_from ASC"

        rows = conn.execute(query, params).fetchall()

        # Build timeline with superseded_by links
        timeline = []
        for row in rows:
            metadata = json.loads(row["metadata"]) if row["metadata"] else None

            # Find what superseded this fact (if anything)
            superseded_by = None
            if row["valid_to"]:
                next_fact = conn.execute(
                    """
                    SELECT id FROM facts
                    WHERE entity = ? AND key = ? AND valid_from = ?
                    """,
                    (normalized_entity, row["key"], row["valid_to"]),
                ).fetchone()
                if next_fact:
                    superseded_by = next_fact["id"]

            timeline.append({
                "id": row["id"],
                "key": row["key"],
                "value": row["value"],
                "metadata": metadata,
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
                "superseded_by": superseded_by,
            })

        return {
            "success": True,
            "data": {
                "entity": normalized_entity,
                "timeline": timeline,
                "count": len(timeline),
            },
        }

    # -------------------------------------------------------------------------
    # Decisions
    # -------------------------------------------------------------------------

    def insert_decision(
        self,
        context: str,
        decision: str,
        rationale: str,
        entities: List[str],
        cr_number: Optional[str] = None,
        gait_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new decision with context and rationale.

        Returns dict with id, context, decision, rationale, entities, cr_number, created_at.
        """
        # Validate inputs
        if not context or not context.strip():
            return {"success": False, "error": {"code": "INVALID_CONTEXT", "message": "Context cannot be empty"}}
        if len(context) > MAX_CONTEXT_LENGTH:
            return {"success": False, "error": {"code": "INVALID_CONTEXT", "message": f"Context exceeds {MAX_CONTEXT_LENGTH} characters"}}

        if not decision or not decision.strip():
            return {"success": False, "error": {"code": "INVALID_DECISION", "message": "Decision cannot be empty"}}
        if len(decision) > MAX_DECISION_LENGTH:
            return {"success": False, "error": {"code": "INVALID_DECISION", "message": f"Decision exceeds {MAX_DECISION_LENGTH} characters"}}

        if not rationale or not rationale.strip():
            return {"success": False, "error": {"code": "INVALID_RATIONALE", "message": "Rationale cannot be empty"}}
        if len(rationale) > MAX_RATIONALE_LENGTH:
            return {"success": False, "error": {"code": "INVALID_RATIONALE", "message": f"Rationale exceeds {MAX_RATIONALE_LENGTH} characters"}}

        if not entities or len(entities) == 0:
            return {"success": False, "error": {"code": "INVALID_ENTITIES", "message": "At least one entity required"}}

        valid, err = validate_cr_number(cr_number)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_CR_NUMBER", "message": err}}

        # Normalize entity names
        normalized_entities = [normalize_entity(e) for e in entities]
        entities_json = json.dumps(normalized_entities)
        now = utc_now()
        new_id = generate_id()

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO decisions (id, context, decision, rationale, entities, cr_number, gait_ref, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id, context, decision, rationale, entities_json, cr_number, gait_ref, now),
            )

        return {
            "success": True,
            "data": {
                "id": new_id,
                "context": context,
                "decision": decision,
                "rationale": rationale,
                "entities": normalized_entities,
                "cr_number": cr_number,
                "gait_ref": gait_ref,
                "created_at": now,
            },
        }

    def query_decisions(
        self,
        entity: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Query decisions by entity and/or time range.

        Returns dict with decisions list, count.
        """
        if not entity and not after:
            return {"success": False, "error": {"code": "INVALID_QUERY", "message": "Either entity or after required"}}

        if after:
            valid, err = validate_timestamp(after)
            if not valid:
                return {"success": False, "error": {"code": "INVALID_TIMESTAMP", "message": err}}

        if before:
            valid, err = validate_timestamp(before)
            if not valid:
                return {"success": False, "error": {"code": "INVALID_TIMESTAMP", "message": err}}

        limit = min(limit, 200)  # Cap at 200
        conn = self._get_connection()

        query = "SELECT id, context, decision, rationale, entities, cr_number, gait_ref, created_at FROM decisions WHERE 1=1"
        params: List[Any] = []

        if entity:
            normalized_entity = normalize_entity(entity)
            # Search in JSON array - SQLite JSON support
            query += " AND entities LIKE ?"
            params.append(f'%"{normalized_entity}"%')

        if after:
            query += " AND created_at >= ?"
            params.append(after)

        if before:
            query += " AND created_at <= ?"
            params.append(before)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        decisions = []
        for row in rows:
            decisions.append({
                "id": row["id"],
                "context": row["context"],
                "decision": row["decision"],
                "rationale": row["rationale"],
                "entities": json.loads(row["entities"]),
                "cr_number": row["cr_number"],
                "gait_ref": row["gait_ref"],
                "created_at": row["created_at"],
            })

        return {
            "success": True,
            "data": {
                "decisions": decisions,
                "count": len(decisions),
            },
        }

    # -------------------------------------------------------------------------
    # Graph Links
    # -------------------------------------------------------------------------

    def insert_link(
        self,
        subject: str,
        predicate: str,
        obj: str,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Insert a relationship link between two entities.

        Returns dict with id, subject, predicate, object, metadata, created_at.
        Returns existing link if duplicate.
        """
        # Validate inputs
        valid, err = validate_entity(subject)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_SUBJECT", "message": err}}

        valid, err = validate_predicate(predicate)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_PREDICATE", "message": err}}

        valid, err = validate_entity(obj)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_OBJECT", "message": err}}

        valid, err = validate_metadata(metadata)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_METADATA", "message": err}}

        normalized_subject = normalize_entity(subject)
        normalized_object = normalize_entity(obj)

        if normalized_subject == normalized_object:
            return {"success": False, "error": {"code": "SELF_LINK", "message": "Subject and object cannot be the same"}}

        conn = self._get_connection()

        # Check for existing link
        existing = conn.execute(
            """
            SELECT id, metadata, created_at FROM graph_links
            WHERE subject = ? AND predicate = ? AND object = ?
            """,
            (normalized_subject, predicate, normalized_object),
        ).fetchone()

        if existing:
            existing_metadata = json.loads(existing["metadata"]) if existing["metadata"] else None
            return {
                "success": True,
                "data": {
                    "id": existing["id"],
                    "subject": normalized_subject,
                    "predicate": predicate,
                    "object": normalized_object,
                    "metadata": existing_metadata,
                    "created_at": existing["created_at"],
                    "existing": True,
                },
            }

        now = utc_now()
        new_id = generate_id()
        metadata_json = json.dumps(metadata) if metadata else None

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO graph_links (id, subject, predicate, object, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (new_id, normalized_subject, predicate, normalized_object, metadata_json, now),
            )

        return {
            "success": True,
            "data": {
                "id": new_id,
                "subject": normalized_subject,
                "predicate": predicate,
                "object": normalized_object,
                "metadata": metadata,
                "created_at": now,
            },
        }

    def query_graph(
        self,
        entity: str,
        direction: str = "both",
        predicate: Optional[str] = None,
        depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Query entity relationships with optional depth traversal.

        Returns dict with entity, relationships, neighbors_at_depth_N.
        """
        valid, err = validate_entity(entity)
        if not valid:
            return {"success": False, "error": {"code": "INVALID_ENTITY", "message": err}}

        if direction not in ("outgoing", "incoming", "both"):
            return {"success": False, "error": {"code": "INVALID_DIRECTION", "message": "Direction must be outgoing, incoming, or both"}}

        if depth < 1 or depth > 3:
            return {"success": False, "error": {"code": "INVALID_DEPTH", "message": "Depth must be between 1 and 3"}}

        normalized_entity = normalize_entity(entity)
        conn = self._get_connection()

        outgoing = []
        incoming = []

        # Get outgoing relationships (entity as subject)
        if direction in ("outgoing", "both"):
            query = "SELECT predicate, object, metadata FROM graph_links WHERE subject = ?"
            params: List[Any] = [normalized_entity]
            if predicate:
                query += " AND predicate = ?"
                params.append(predicate)

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                metadata = json.loads(row["metadata"]) if row["metadata"] else None
                outgoing.append({
                    "predicate": row["predicate"],
                    "target": row["object"],
                    "metadata": metadata,
                })

        # Get incoming relationships (entity as object)
        if direction in ("incoming", "both"):
            query = "SELECT subject, predicate, metadata FROM graph_links WHERE object = ?"
            params = [normalized_entity]
            if predicate:
                query += " AND predicate = ?"
                params.append(predicate)

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                metadata = json.loads(row["metadata"]) if row["metadata"] else None
                incoming.append({
                    "predicate": row["predicate"],
                    "source": row["subject"],
                    "metadata": metadata,
                })

        result: Dict[str, Any] = {
            "success": True,
            "data": {
                "entity": normalized_entity,
                "relationships": {
                    "outgoing": outgoing,
                    "incoming": incoming,
                },
            },
        }

        # Depth traversal
        if depth > 1:
            visited = {normalized_entity}
            current_level = set()

            # Collect first-level neighbors
            for rel in outgoing:
                current_level.add(rel["target"])
            for rel in incoming:
                current_level.add(rel["source"])

            for d in range(2, depth + 1):
                next_level = set()
                for neighbor in current_level:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        # Get neighbors of this neighbor
                        rows = conn.execute(
                            "SELECT object FROM graph_links WHERE subject = ?",
                            (neighbor,),
                        ).fetchall()
                        for row in rows:
                            if row["object"] not in visited:
                                next_level.add(row["object"])

                        rows = conn.execute(
                            "SELECT subject FROM graph_links WHERE object = ?",
                            (neighbor,),
                        ).fetchall()
                        for row in rows:
                            if row["subject"] not in visited:
                                next_level.add(row["subject"])

                result["data"][f"neighbors_at_depth_{d}"] = list(next_level)
                current_level = next_level

        return result

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def prune_old_data(self, days: int = 365) -> Dict[str, Any]:
        """
        Remove data older than specified days.

        Returns dict with counts of pruned records.
        """
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Subtract days manually
        import datetime as dt
        cutoff = cutoff - dt.timedelta(days=days)
        cutoff_str = cutoff.isoformat().replace("+00:00", "Z")

        with self._transaction() as conn:
            facts_deleted = conn.execute(
                "DELETE FROM facts WHERE created_at < ?", (cutoff_str,)
            ).rowcount
            decisions_deleted = conn.execute(
                "DELETE FROM decisions WHERE created_at < ?", (cutoff_str,)
            ).rowcount
            links_deleted = conn.execute(
                "DELETE FROM graph_links WHERE created_at < ?", (cutoff_str,)
            ).rowcount

        return {
            "success": True,
            "data": {
                "facts_pruned": facts_deleted,
                "decisions_pruned": decisions_deleted,
                "links_pruned": links_deleted,
                "cutoff_date": cutoff_str,
            },
        }

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
