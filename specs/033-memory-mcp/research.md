# Research: Hybrid Memory MCP Server

**Feature**: 033-memory-mcp
**Date**: 2026-06-20

## Technology Decisions

### 1. Structured Storage: SQLite

**Decision**: Use SQLite with WAL mode for structured data (facts, decisions, graph links).

**Rationale**:
- Zero-config, file-based database perfect for local deployment
- WAL mode enables concurrent reads with safe writes
- Built into Python stdlib (sqlite3)
- Handles 100K+ records easily with proper indexing
- Survives process crashes without data loss

**Alternatives Considered**:
- PostgreSQL: Overkill for single-user local deployment, adds ops burden
- LevelDB/RocksDB: Good for key-value, but lacks relational queries for graph links
- JSON files: No query capability, poor performance at scale

### 2. Semantic Storage: ChromaDB

**Decision**: Use ChromaDB with PersistentClient for semantic search.

**Rationale**:
- Purpose-built for embedding storage and similarity search
- File-based persistence (no server process)
- Native Python integration
- Handles metadata filtering (time, topics, entities)
- Actively maintained, good documentation

**Alternatives Considered**:
- pgvector: Requires PostgreSQL, adds complexity
- FAISS: Lower-level, no built-in persistence or metadata
- Pinecone/Weaviate: Cloud-based, violates offline requirement
- Qdrant: Good but heavier than needed for local use

### 3. Embedding Model: all-MiniLM-L6-v2

**Decision**: Use sentence-transformers with all-MiniLM-L6-v2 model.

**Rationale**:
- 80MB size fits in container without bloat
- 384-dimension embeddings balance quality vs. storage
- 14K sentences/sec on CPU (fast enough)
- Apache 2.0 license (free, open source)
- Fully offline after initial download
- Well-tested, most popular sentence-transformers model

**Alternatives Considered**:
- nomic-embed-text via Ollama: Larger (768-dim), requires Ollama running
- OpenAI embeddings: Violates offline requirement, adds cost
- all-mpnet-base-v2: Better quality but 420MB (too large)
- text-embedding-3-small: Cloud-based, violates offline requirement

### 4. Deployment Strategy: uvx (uv tool)

**Decision**: Package as uvx-installable Python package, consistent with other NetClaw MCP servers.

**Rationale**:
- Consistent with existing NetClaw MCP servers (IP Fabric, GNS3, SuzieQ)
- OpenShell already provides Docker-based container isolation at the platform level
- Simpler deployment - no separate Dockerfile to maintain
- uv cache handles dependency isolation naturally
- Standard stdio transport for MCP

**Alternatives Considered**:
- Docker container: Redundant with OpenShell sandbox, adds complexity
- Native Python venv: Less portable than uvx
- Snap/Flatpak: Less common in NetClaw ecosystem

**Note**: The embedding model (~80MB) downloads on first use and caches locally. Subsequent starts are fast.

### 5. Concurrency: Write Queue

**Decision**: Serialize all write operations through an internal queue.

**Rationale**:
- Simplest approach that guarantees consistency
- SQLite WAL handles read concurrency natively
- MCP tool calls are sequential in practice
- No complex locking logic needed

**Alternatives Considered**:
- Optimistic locking: Adds complexity, retry logic
- Last-write-wins: Risk of lost updates
- Row-level locks: SQLite doesn't support well

### 6. Data Retention: 1-Year Auto-Prune

**Decision**: Automatically prune facts, sessions, and decisions older than 1 year.

**Rationale**:
- Bounds storage growth predictably
- 1 year provides sufficient historical context
- Aligns with typical audit retention periods
- User can backup before prune if needed

**Alternatives Considered**:
- No pruning: Unbounded growth
- 90-day retention: Too short for pattern analysis
- Manual archival only: Requires user discipline

## Best Practices Applied

### FastMCP Server Pattern

Following existing NetClaw MCP servers:
- Use `@mcp.tool()` decorators for tool registration
- Async tool handlers for non-blocking operation
- Structured JSON responses (not prose)
- Error objects returned, not exceptions thrown

### SQLite Best Practices

- WAL mode for concurrent access
- Prepared statements to prevent injection
- Indexes on frequently queried columns (entity, valid_from)
- PRAGMA integrity_check on startup
- Connection pooling via contextmanager

### ChromaDB Best Practices

- PersistentClient for durability
- Collection naming: `session_summaries`
- Metadata for filtering (timestamp, entities, topics)
- Batch operations for efficiency
- Graceful degradation if unavailable

### Embedding Best Practices

- Cache model in container image
- Lazy loading on first use
- Batch embedding for multiple texts
- Fallback to keyword storage if model fails

## Integration Patterns

### GAIT Integration

All write operations log to GAIT:
```python
# Pattern for GAIT logging
async def record_fact(...):
    result = await store.insert_fact(...)
    await gait_log(f"memory_record_fact: {entity}/{key}")
    return result
```

### Existing File Integration

Memory complements but doesn't replace:
- **GAIT**: Memory adds "what it means" to GAIT's "what happened"
- **SOUL-*.md**: Memory adds environmental knowledge to static reference
- **HEARTBEAT.md**: Memory enables pattern detection in health checks

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Data retention period | 1 year with auto-prune |
| Concurrent access handling | Serialize writes via queue |
| Observability level | GAIT logging for writes only |
| Entity name matching | Case-insensitive (normalize to lowercase) |
| Data encryption | None (filesystem permissions) |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ChromaDB corruption | Graceful degradation to SQLite-only |
| Model download fails | Container ships pre-downloaded model |
| SQLite corruption | PRAGMA integrity_check + backup strategy |
| Container too large | Use slim base, multi-stage build |
| Cold start too slow | Pre-load model in container entrypoint |
