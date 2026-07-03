# Data Model: Hybrid Memory MCP Server

**Feature**: 033-memory-mcp
**Date**: 2026-06-20

## Entity Relationship Diagram

```
┌─────────────────┐         ┌─────────────────┐
│      Fact       │         │    Decision     │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ entity          │◄───────►│ entities[]      │
│ key             │         │ context         │
│ value           │         │ decision        │
│ metadata (JSON) │         │ rationale       │
│ valid_from      │         │ cr_number       │
│ valid_to        │         │ gait_ref        │
│ created_at      │         │ created_at      │
└─────────────────┘         └─────────────────┘
        │                           │
        │                           │
        ▼                           ▼
┌─────────────────────────────────────────────┐
│                  Entity                      │
│  (implicit - derived from fact/decision/link │
│   entity fields, normalized to lowercase)    │
└─────────────────────────────────────────────┘
        │
        │
        ▼
┌─────────────────┐         ┌─────────────────┐
│   GraphLink     │         │ SessionSummary  │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ subject         │         │ summary (text)  │
│ predicate       │         │ embedding (vec) │
│ object          │         │ entities[]      │
│ metadata (JSON) │         │ topics[]        │
│ created_at      │         │ session_id      │
└─────────────────┘         │ created_at      │
                            └─────────────────┘
                            (ChromaDB collection)
```

## Entities

### Fact (SQLite: `facts` table)

A piece of knowledge about a network entity with temporal validity.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | TEXT | PK, auto-generated | Unique identifier (hex random) |
| entity | TEXT | NOT NULL, indexed | Network entity name (normalized lowercase for matching) |
| key | TEXT | NOT NULL | Fact type/attribute name |
| value | TEXT | NOT NULL | Fact value |
| metadata | TEXT | NULL | JSON object with additional context |
| valid_from | TEXT | NOT NULL, default NOW | ISO timestamp when fact became valid |
| valid_to | TEXT | NULL | ISO timestamp when fact was invalidated (NULL = current) |
| created_at | TEXT | NOT NULL, default NOW | Record creation timestamp |

**Uniqueness**: (entity, key, valid_from) - same entity+key can have multiple historical values

**Indexes**:
- `idx_facts_entity` on (entity)
- `idx_facts_entity_key` on (entity, key)
- `idx_facts_valid` on (valid_from, valid_to)

**State Transitions**:
```
Created → Current (valid_to = NULL)
Current → Superseded (new fact with same entity+key recorded)
Current → Invalidated (explicit invalidation with reason)
Superseded/Invalidated → [terminal, immutable]
```

### Decision (SQLite: `decisions` table)

A recorded operational decision with context and rationale.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | TEXT | PK, auto-generated | Unique identifier (hex random) |
| context | TEXT | NOT NULL | What was happening when decision was made |
| decision | TEXT | NOT NULL | What was decided |
| rationale | TEXT | NOT NULL | Why this decision was made |
| entities | TEXT | NOT NULL | JSON array of related entity names |
| cr_number | TEXT | NULL | ServiceNow Change Request reference |
| gait_ref | TEXT | NULL | GAIT commit reference |
| created_at | TEXT | NOT NULL, default NOW | Decision timestamp |

**Indexes**:
- `idx_decisions_created` on (created_at)

### GraphLink (SQLite: `graph_links` table)

A relationship between two entities expressed as subject-predicate-object.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | TEXT | PK, auto-generated | Unique identifier (hex random) |
| subject | TEXT | NOT NULL, indexed | Source entity (normalized lowercase) |
| predicate | TEXT | NOT NULL, indexed | Relationship type |
| object | TEXT | NOT NULL, indexed | Target entity (normalized lowercase) |
| metadata | TEXT | NULL | JSON object with relationship context |
| created_at | TEXT | NOT NULL, default NOW | Link creation timestamp |

**Uniqueness**: (subject, predicate, object) - prevent duplicate relationships

**Indexes**:
- `idx_links_subject` on (subject)
- `idx_links_object` on (object)
- `idx_links_predicate` on (predicate)

**Standard Predicates**:
- `peers_with` — BGP/OSPF peering relationship
- `depends_on` — Service dependency
- `connects_to` — Physical/logical connectivity
- `managed_by` — Management relationship
- `caused` — Incident causality
- `fixed_by` — Resolution relationship
- `learned_from` — Knowledge provenance

### SessionSummary (ChromaDB: `session_summaries` collection)

An embedded text summary of a past interaction stored for semantic retrieval.

| Field | Type | Storage | Description |
|-------|------|---------|-------------|
| id | TEXT | Document ID | Unique identifier |
| summary | TEXT | Document content | Session summary text |
| embedding | VECTOR(384) | Embedding | all-MiniLM-L6-v2 vector |
| entities | TEXT | Metadata | Comma-separated entity names |
| topics | TEXT | Metadata | Comma-separated topic tags |
| session_id | TEXT | Metadata | Optional GAIT session reference |
| created_at | TEXT | Metadata | ISO timestamp |

## SQLite Schema

```sql
-- Enable WAL mode for concurrent access
PRAGMA journal_mode = WAL;

-- Facts table: temporal key-value store
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    entity TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata TEXT,
    valid_from TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(entity, key, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity);
CREATE INDEX IF NOT EXISTS idx_facts_entity_key ON facts(entity, key);
CREATE INDEX IF NOT EXISTS idx_facts_valid ON facts(valid_from, valid_to);

-- Decisions table
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    context TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    entities TEXT NOT NULL,
    cr_number TEXT,
    gait_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at);

-- Graph links table
CREATE TABLE IF NOT EXISTS graph_links (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(subject, predicate, object)
);

CREATE INDEX IF NOT EXISTS idx_links_subject ON graph_links(subject);
CREATE INDEX IF NOT EXISTS idx_links_object ON graph_links(object);
CREATE INDEX IF NOT EXISTS idx_links_predicate ON graph_links(predicate);

-- Pruning: Remove records older than 1 year
-- Run periodically via maintenance task
-- DELETE FROM facts WHERE created_at < datetime('now', '-1 year');
-- DELETE FROM decisions WHERE created_at < datetime('now', '-1 year');
-- DELETE FROM graph_links WHERE created_at < datetime('now', '-1 year');
```

## Validation Rules

### Fact Validation
- `entity`: Required, max 255 chars, normalized to lowercase for storage
- `key`: Required, max 255 chars
- `value`: Required, max 10000 chars
- `metadata`: Optional, must be valid JSON if provided

### Decision Validation
- `context`: Required, max 5000 chars
- `decision`: Required, max 2000 chars
- `rationale`: Required, max 5000 chars
- `entities`: Required, JSON array with at least one entity
- `cr_number`: Optional, pattern CHG[0-9]+
- `gait_ref`: Optional, pattern gait_[a-z0-9_]+

### GraphLink Validation
- `subject`: Required, max 255 chars, normalized to lowercase
- `predicate`: Required, max 100 chars, lowercase alphanumeric + underscore
- `object`: Required, max 255 chars, normalized to lowercase
- `metadata`: Optional, must be valid JSON if provided

### SessionSummary Validation
- `summary`: Required, max 10000 chars
- `entities`: Optional, list of entity names
- `topics`: Optional, list of topic tags
- `session_id`: Optional, reference to GAIT session

## Query Patterns

### Get Current Facts for Entity
```sql
SELECT * FROM facts
WHERE entity = ? AND valid_to IS NULL
ORDER BY created_at DESC;
```

### Get Fact Timeline
```sql
SELECT * FROM facts
WHERE entity = ?
  AND valid_from >= ?
  AND (valid_to IS NULL OR valid_to <= ?)
ORDER BY valid_from ASC;
```

### Supersede Existing Fact
```sql
-- Transaction:
UPDATE facts SET valid_to = datetime('now')
WHERE entity = ? AND key = ? AND valid_to IS NULL;

INSERT INTO facts (entity, key, value, metadata)
VALUES (?, ?, ?, ?);
```

### Query Graph (Incoming Links)
```sql
SELECT * FROM graph_links
WHERE object = ?
ORDER BY created_at DESC;
```

### Query Graph (N-Hop Traversal)
```sql
-- Recursive CTE for depth traversal
WITH RECURSIVE traversal AS (
    SELECT subject, predicate, object, 1 as depth
    FROM graph_links WHERE subject = ?

    UNION ALL

    SELECT g.subject, g.predicate, g.object, t.depth + 1
    FROM graph_links g
    JOIN traversal t ON g.subject = t.object
    WHERE t.depth < ?
)
SELECT DISTINCT * FROM traversal;
```

### Semantic Recall
```python
# ChromaDB query
results = collection.query(
    query_embeddings=[embed(query_text)],
    n_results=top_k,
    where={
        "$and": [
            {"created_at": {"$gte": after_date}},
            {"topics": {"$contains": topic}}
        ]
    }
)
```
