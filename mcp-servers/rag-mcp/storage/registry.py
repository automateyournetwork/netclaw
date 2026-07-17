"""SQLite document registry for rag-mcp.

Tables (specs/062-rag-mcp/data-model.md): documents, retrieval_log,
telemetry_rollup (derived on read for v1), schema_version.

The ingest_status state machine gives per-document atomicity:
pending -> parsing -> chunking -> embedding -> ready | error.
Only 'ready' rows are searchable/listable as indexed. On startup,
rows stuck in a non-terminal state are swept to 'error' and their
partial index entries purged by the caller.
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

NON_TERMINAL_STATES = ("pending", "parsing", "chunking", "embedding")
TERMINAL_STATES = ("ready", "error")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('document', 'snapshot')),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    doc_type TEXT NOT NULL DEFAULT 'other',
    version TEXT,
    content_hash TEXT NOT NULL,
    collection TEXT NOT NULL,
    ingest_ts TEXT NOT NULL,
    page_count INTEGER,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    source_path TEXT,
    ingest_status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    capture_ts TEXT,
    capture_devices TEXT,
    capture_commands TEXT,
    redaction_counts TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_hash_kind
    ON documents (content_hash, kind);

CREATE TABLE IF NOT EXISTS retrieval_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    query TEXT NOT NULL,
    collection TEXT NOT NULL,
    filters TEXT,
    k INTEGER NOT NULL,
    chunk_ids TEXT NOT NULL,
    scores TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    low_confidence INTEGER NOT NULL DEFAULT 0,
    round INTEGER,
    sub_query_id TEXT
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Registry:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)
            cur = self._conn.execute("SELECT version FROM schema_version")
            if cur.fetchone() is None:
                self._conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def new_document(
        self,
        kind: str,
        title: str,
        source: str,
        doc_type: str,
        content_hash: str,
        collection: str,
        version: Optional[str] = None,
        source_path: Optional[str] = None,
        capture_ts: Optional[str] = None,
        capture_devices: Optional[List[str]] = None,
        capture_commands: Optional[List[str]] = None,
    ) -> str:
        prefix = "doc" if kind == "document" else "snap"
        doc_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO documents
                   (id, kind, title, source, doc_type, version, content_hash,
                    collection, ingest_ts, source_path, ingest_status,
                    capture_ts, capture_devices, capture_commands)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (
                    doc_id,
                    kind,
                    title,
                    source,
                    doc_type,
                    version,
                    content_hash,
                    collection,
                    utc_now(),
                    source_path,
                    capture_ts,
                    json.dumps(capture_devices) if capture_devices else None,
                    json.dumps(capture_commands) if capture_commands else None,
                ),
            )
        return doc_id

    def set_source_path(self, doc_id: str, source_path: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE documents SET source_path = ? WHERE id = ?", (source_path, doc_id)
            )

    def set_status(self, doc_id: str, status: str, error: Optional[str] = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE documents SET ingest_status = ?, error = ? WHERE id = ?",
                (status, error, doc_id),
            )

    def finalize(
        self,
        doc_id: str,
        chunk_count: int,
        page_count: Optional[int] = None,
        redaction_counts: Optional[Dict[str, int]] = None,
    ) -> None:
        """Flip a document to 'ready' in one transaction (atomic commit point)."""
        with self._lock, self._conn:
            self._conn.execute(
                """UPDATE documents
                   SET ingest_status = 'ready', chunk_count = ?, page_count = ?,
                       redaction_counts = ?, error = NULL
                   WHERE id = ?""",
                (
                    chunk_count,
                    page_count,
                    json.dumps(redaction_counts) if redaction_counts is not None else None,
                    doc_id,
                ),
            )

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def find_by_hash(self, content_hash: str, kind: str = "document") -> Optional[Dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT * FROM documents WHERE content_hash = ? AND kind = ?",
            (content_hash, kind),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def find_by_title(self, title: str, kind: str = "document") -> Optional[Dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT * FROM documents WHERE title = ? AND kind = ? AND ingest_status = 'ready'",
            (title, kind),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def list_documents(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        if kind:
            cur = self._conn.execute(
                "SELECT * FROM documents WHERE kind = ? ORDER BY ingest_ts DESC", (kind,)
            )
        else:
            cur = self._conn.execute("SELECT * FROM documents ORDER BY ingest_ts DESC")
        return [dict(r) for r in cur.fetchall()]

    def update_metadata(
        self,
        doc_id: str,
        doc_type: Optional[str] = None,
        title: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        sets, params = [], []
        for col, val in (("doc_type", doc_type), ("title", title), ("version", version)):
            if val is not None:
                sets.append(f"{col} = ?")
                params.append(val)
        if sets:
            params.append(doc_id)
            with self._lock, self._conn:
                self._conn.execute(
                    f"UPDATE documents SET {', '.join(sets)} WHERE id = ?", params
                )
        return self.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return cur.rowcount > 0

    def sweep_interrupted(self) -> List[Dict[str, Any]]:
        """Mark non-terminal rows as errored (startup recovery). Returns swept rows
        so the caller can purge their partial Chroma/BM25 entries."""
        placeholders = ",".join("?" for _ in NON_TERMINAL_STATES)
        cur = self._conn.execute(
            f"SELECT * FROM documents WHERE ingest_status IN ({placeholders})",
            NON_TERMINAL_STATES,
        )
        swept = [dict(r) for r in cur.fetchall()]
        if swept:
            with self._lock, self._conn:
                self._conn.execute(
                    f"""UPDATE documents
                        SET ingest_status = 'error',
                            error = 'interrupted — source retained, re-ingest to retry'
                        WHERE ingest_status IN ({placeholders})""",
                    NON_TERMINAL_STATES,
                )
        return swept

    # ------------------------------------------------------------------
    # Retrieval log + telemetry
    # ------------------------------------------------------------------
    def log_retrieval(
        self,
        query: str,
        collection: str,
        filters: Optional[Dict[str, Any]],
        k: int,
        chunk_ids: List[str],
        scores: List[float],
        latency_ms: int,
        low_confidence: int,
        round: Optional[int] = None,
        sub_query_id: Optional[str] = None,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO retrieval_log
                   (ts, query, collection, filters, k, chunk_ids, scores,
                    latency_ms, low_confidence, round, sub_query_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    utc_now(),
                    query,
                    collection,
                    json.dumps(filters) if filters else None,
                    k,
                    json.dumps(chunk_ids),
                    json.dumps(scores),
                    latency_ms,
                    low_confidence,
                    round,
                    sub_query_id,
                ),
            )

    def telemetry(self) -> Dict[str, Any]:
        """Rolling retrieval telemetry derived from retrieval_log (FR-083)."""
        cur = self._conn.execute(
            "SELECT COUNT(*) AS n, AVG(latency_ms) AS mean_latency FROM retrieval_log"
        )
        row = cur.fetchone()
        query_count = row["n"] or 0
        mean_latency = round(row["mean_latency"], 1) if row["mean_latency"] else 0.0

        cur = self._conn.execute(
            """SELECT COUNT(DISTINCT sub_query_id) AS total,
                      COUNT(DISTINCT CASE WHEN round > 1 THEN sub_query_id END) AS refined
               FROM retrieval_log WHERE sub_query_id IS NOT NULL"""
        )
        row = cur.fetchone()
        re_retrieval_rate = (
            round(row["refined"] / row["total"], 3) if row["total"] else 0.0
        )

        cur = self._conn.execute(
            "SELECT COUNT(*) AS lc FROM retrieval_log WHERE low_confidence > 0"
        )
        low_conf_queries = cur.fetchone()["lc"] or 0
        low_confidence_rate = (
            round(low_conf_queries / query_count, 3) if query_count else 0.0
        )

        return {
            "query_count": query_count,
            "mean_latency_ms": mean_latency,
            "re_retrieval_rate": re_retrieval_rate,
            "low_confidence_rate": low_confidence_rate,
        }

    def schema_version(self) -> int:
        cur = self._conn.execute("SELECT version FROM schema_version")
        row = cur.fetchone()
        return row["version"] if row else 0

    def close(self) -> None:
        self._conn.close()
