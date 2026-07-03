-- Memory MCP Server SQLite Schema
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
