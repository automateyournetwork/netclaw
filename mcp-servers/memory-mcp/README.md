# Memory MCP Server

Hybrid persistent memory for NetClaw combining structured storage (SQLite), semantic search (ChromaDB), and entity relationships.

## Features

- **Structured Facts**: Key-value storage with temporal validity and automatic supersession
- **Semantic Search**: Natural language queries over stored session summaries
- **Decision Log**: Audit trail with context, rationale, and CR references
- **Entity Graph**: Track relationships between network entities
- **Graceful Degradation**: Works without embeddings (semantic search disabled)

## Installation

```bash
# Install as uvx tool
uvx install netclaw-memory-mcp

# Or install from source
cd mcp-servers/memory-mcp
pip install -e .
```

## Configuration

Add to your MCP configuration (e.g., `~/.openclaw/mcp.json`):

```json
{
  "mcpServers": {
    "memory": {
      "command": "uvx",
      "args": ["netclaw-memory-mcp"],
      "env": {
        "MEMORY_DATA_DIR": "~/.openclaw/memory"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_DATA_DIR` | `~/.openclaw/memory` | Data directory for SQLite and ChromaDB |

## MCP Tools

### Facts (User Story 1)

#### `memory_record_fact`
Record a fact about a network entity with temporal validity.

```json
{
  "entity": "pe2",
  "key": "bgp_state",
  "value": "established",
  "metadata": {"peer_ip": "10.0.0.1", "asn": 65000}
}
```

#### `memory_get_facts`
Query current (non-invalidated) facts for an entity.

```json
{
  "entity": "pe2",
  "key": "bgp_state"  // optional
}
```

### Semantic Search (User Story 2)

#### `memory_store_session`
Store a session summary for semantic retrieval.

```json
{
  "summary": "Troubleshot BGP flapping on PE2 by adjusting MTU settings",
  "entities": ["pe2", "rr1"],
  "topics": ["bgp", "mtu", "troubleshooting"]
}
```

#### `memory_recall`
Semantic search across stored sessions.

```json
{
  "query": "BGP problems with PE routers",
  "top_k": 5,
  "min_score": 0.5
}
```

### Decision Log (User Story 3)

#### `memory_record_decision`
Record an operational decision with context and rationale.

```json
{
  "context": "BGP session to RR1 was flapping every 30 seconds",
  "decision": "Increased BGP hold timer from 90s to 180s",
  "rationale": "Reduce flap frequency while investigating root cause",
  "entities": ["pe2", "rr1"],
  "cr_number": "CHG0001234"
}
```

#### `memory_get_decisions`
Query past decisions by entity and/or time range.

```json
{
  "entity": "pe2",
  "after": "2024-01-01T00:00:00Z",
  "limit": 50
}
```

### Entity Graph (User Story 4)

#### `memory_link_entities`
Create a relationship between two entities.

Standard predicates:
- `peers_with` - BGP/OSPF peering
- `depends_on` - Service dependency
- `connects_to` - Physical/logical connectivity
- `managed_by` - Management relationship
- `caused` - Incident causality
- `fixed_by` - Resolution relationship
- `learned_from` - Knowledge provenance

```json
{
  "subject": "pe2",
  "predicate": "peers_with",
  "object": "rr1"
}
```

#### `memory_query_graph`
Query entity relationships with optional depth traversal.

```json
{
  "entity": "pe2",
  "direction": "both",  // "outgoing", "incoming", or "both"
  "predicate": "peers_with",  // optional filter
  "depth": 2  // 1-3
}
```

### Fact Lifecycle (User Story 5)

#### `memory_invalidate`
Explicitly invalidate a fact with a reason.

```json
{
  "fact_id": "abc123",
  "reason": "Device decommissioned"
}
```

#### `memory_timeline`
Query historical facts including invalidated ones.

```json
{
  "entity": "pe2",
  "after": "2024-01-01T00:00:00Z",
  "before": "2024-12-31T23:59:59Z",
  "key": "bgp_state"
}
```

## Architecture

```
memory-mcp/
├── memory_mcp_server.py    # FastMCP server with 10 tools
├── storage/
│   ├── sqlite_store.py     # Structured storage (facts, decisions, links)
│   ├── chroma_store.py     # Semantic storage (sessions)
│   └── schema.sql          # SQLite schema
└── embeddings/
    └── embedder.py         # Sentence-transformers wrapper
```

### Storage Backends

- **SQLite**: Facts, decisions, and graph links with WAL mode for concurrent access
- **ChromaDB**: Session summaries with sentence-transformers embeddings (all-MiniLM-L6-v2, 384 dimensions)

### Data Location

```
~/.openclaw/memory/
├── memory.db              # SQLite database
├── memory.db-wal          # Write-ahead log
├── memory.db-shm          # Shared memory
└── chroma/                # ChromaDB vector store
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/test_sqlite_store.py -v
pytest tests/contract/test_mcp_tools.py -v
pytest tests/integration/test_memory_mcp.py -v
```

## GAIT Integration

Write operations are logged to GAIT for audit trail:
- `memory_record_fact` → `GAIT: memory_record_fact: {entity}/{key}`
- `memory_store_session` → `GAIT: memory_store_session: {session_id}`
- `memory_record_decision` → `GAIT: memory_record_decision: {decision_id}`
- `memory_link_entities` → `GAIT: memory_link_entities: {subject} {predicate} {object}`
- `memory_invalidate` → `GAIT: memory_invalidate: {fact_id}`

## Data Retention

By default, data older than 1 year is automatically pruned. Use the `prune_old_data()` method to manually trigger cleanup.

## Graceful Degradation

If sentence-transformers is unavailable:
- `memory_store_session` will fail with `EMBEDDINGS_UNAVAILABLE` error
- `memory_recall` returns empty results with a note explaining unavailability
- All SQLite-based tools (facts, decisions, links) continue to work normally
