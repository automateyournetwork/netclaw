# Data Model: Hybrid Memory MCP Server

**Feature**: 033-memory-mcp-server | **Date**: 2026-05-12

## Entities

### Fact

A piece of structured knowledge about a network entity with temporal validity.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) | Yes | Unique fact identifier (auto-generated) |
| entity | str | Yes | Network entity name (e.g., "PE2", "RR1", "Gi0/0/0/1@PE2") |
| key | str | Yes | Fact key (e.g., "bgp_peer_state", "interface_status", "os_version") |
| value | str | Yes | Fact value (JSON-serialized for complex values) |
| metadata | dict | No | Additional context (interface name, peer IP, protocol, etc.) |
| valid_from | str (ISO 8601) | Yes | When this fact became true (auto-set to now if not provided) |
| valid_to | str (ISO 8601) | No | When this fact stopped being true (NULL = currently valid) |
| superseded_by | str (UUID) | No | ID of the fact that replaced this one |
| source | str | No | How this fact was learned (e.g., "pyats_health_check", "gnmi_get", "user_stated") |
| session_id | str | No | Session that created this fact |

**Validation Rules**:
- `entity` must be non-empty, max 256 chars
- `key` must be non-empty, max 256 chars, alphanumeric + underscores
- `value` max 10KB
- `metadata` values must be JSON-serializable
- `valid_from` must be a valid ISO 8601 datetime
- `valid_to` must be >= `valid_from` if set

**Indexes**:
- `(entity, key, valid_to)` — fast lookup of current facts for an entity
- `(entity, valid_from)` — timeline queries
- `(valid_from)` — global chronological queries

---

### Decision

A recorded operational decision with context and rationale.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) | Yes | Unique decision identifier (auto-generated) |
| timestamp | str (ISO 8601) | Yes | When the decision was made |
| context | str | Yes | What situation prompted the decision |
| decision | str | Yes | What was decided |
| rationale | str | Yes | Why this decision was made |
| entities | list[str] | No | Related network entities |
| cr_number | str | No | Associated ServiceNow Change Request |
| outcome | str | No | What happened after (can be updated later) |
| session_id | str | No | Session that recorded this decision |

**Validation Rules**:
- `context`, `decision`, `rationale` must be non-empty
- `cr_number` must match `CHG\d+` if provided
- `entities` items must be non-empty strings

**Indexes**:
- `(timestamp)` — chronological queries
- FTS on `context`, `decision`, `rationale` — text search

---

### SessionSummary

An embedded text summary stored in ChromaDB for semantic retrieval.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) | Yes | Unique summary identifier |
| timestamp | str (ISO 8601) | Yes | When the session occurred |
| summary | str | Yes | Natural language summary of the session |
| entities | list[str] | No | Entities mentioned in the session |
| topics | list[str] | No | Topic tags (e.g., "bgp", "troubleshooting", "security") |
| session_id | str | No | OpenClaw session ID |

**Stored in**: ChromaDB collection `netclaw_sessions`
**Embedding model**: `all-MiniLM-L6-v2` (384 dimensions, local)
**Metadata stored alongside embedding**: timestamp, entities (comma-joined), topics (comma-joined), session_id

---

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata TEXT,  -- JSON
    valid_from TEXT NOT NULL,  -- ISO 8601
    valid_to TEXT,  -- ISO 8601, NULL = current
    superseded_by TEXT,  -- FK to facts.id
    source TEXT,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_facts_entity_key_current ON facts(entity, key, valid_to);
CREATE INDEX IF NOT EXISTS idx_facts_entity_timeline ON facts(entity, valid_from);
CREATE INDEX IF NOT EXISTS idx_facts_global_time ON facts(valid_from);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,  -- ISO 8601
    context TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    entities TEXT,  -- JSON array
    cr_number TEXT,
    outcome TEXT,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_decisions_time ON decisions(timestamp);

-- FTS for text search across decisions
CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    context, decision, rationale, content=decisions, content_rowid=rowid
);
```

## Entity Relationships

```
Fact *──1 Entity (via entity field, not a separate table)
Fact 1──? Fact (superseded_by — self-referential)
Decision *──* Entity (via entities JSON array)
SessionSummary *──* Entity (via entities metadata)
```

## ChromaDB Collection Schema

```python
collection = client.get_or_create_collection(
    name="netclaw_sessions",
    metadata={"hnsw:space": "cosine"},
)

# Add document:
collection.add(
    ids=[summary.id],
    documents=[summary.summary],
    metadatas=[{
        "timestamp": summary.timestamp,
        "entities": ",".join(summary.entities),
        "topics": ",".join(summary.topics),
        "session_id": summary.session_id or "",
    }],
)

# Query:
results = collection.query(
    query_texts=[query],
    n_results=top_k,
    where={"timestamp": {"$gte": after}} if after else None,
)
```

## Storage Locations

- **SQLite database**: `memory/netclaw_memory.db` (relative to project root)
- **ChromaDB persistent store**: `memory/chromadb/` (directory, relative to project root)
- **Embedding model cache**: `~/.cache/torch/sentence_transformers/` (standard HF cache)

## Size Estimates

| Component | 10K facts | 50K facts | 100K facts |
|-----------|-----------|-----------|------------|
| SQLite DB | ~5MB | ~25MB | ~50MB |
| ChromaDB (1K sessions) | ~100MB | ~100MB | ~100MB |
| ChromaDB (10K sessions) | ~500MB | ~500MB | ~500MB |
| Embedding model (one-time) | 80MB | 80MB | 80MB |
