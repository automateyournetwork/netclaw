# Implementation Plan: Hybrid Memory MCP Server

**Branch**: `033-memory-mcp-server` | **Date**: 2026-05-12 | **Spec**: `specs/033-memory-mcp-server/spec.md`

## Summary

Build a hybrid memory MCP server combining SQLite (structured facts with temporal validity, decisions) and ChromaDB (embedded session summaries for semantic search). Exposes 8 MCP tools for recording, querying, and managing NetClaw's long-term memory. Uses local-only storage and embeddings (no external API dependencies). Complements GAIT (what happened) with structured knowledge (what we know) and semantic recall (what we discussed).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastMCP (MCP framework), sqlite3 (stdlib), chromadb (vector store), sentence-transformers (local embeddings)
**Storage**: SQLite file + ChromaDB persistent directory, volume-mounted at `memory/`
**Target Platform**: Docker container (Linux), stdio transport via `docker run -i`
**Project Type**: MCP server (stdio transport, containerized)
**Performance Goals**: Fact queries <50ms, semantic search <500ms, writes <100ms
**Constraints**: Fully offline (no external API calls), file-based storage, single-writer (stdio MCP = one process), heavy deps isolated in container
**Scale/Scope**: 8 MCP tools, 1 skill, ~500 lines of server code

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | All tools are read/write to local storage only. No device interaction. |
| II. Read-Before-Write | N/A | Memory writes don't modify network state. |
| III. ITSM-Gated Changes | N/A | No network changes. Memory writes are metadata operations. |
| IV. Immutable Audit Trail | PASS | All memory writes logged to GAIT. |
| V. MCP-Native Integration | PASS | Built as FastMCP server with stdio transport. |
| VI. Multi-Vendor Neutrality | N/A | Not vendor-specific. |
| VII. Skill Modularity | PASS | Single `memory-management` skill documents usage patterns. |
| VIII. Verify After Every Change | N/A | No network changes to verify. |
| IX. Security by Default | PASS | Local storage only. No credentials stored in memory DB. No PII in examples. |
| X. Observability | PASS | Logging to stderr, GAIT audit for writes. |
| XI. Artifact Coherence | PASS | README, SKILL.md, .env.example, openclaw.json all updated. |
| XII. Documentation-as-Code | PASS | README with tool inventory and usage examples. |
| XIII. Credential Safety | PASS | Memory DB stores facts about network state, never credentials. |
| XIV. Human-in-the-Loop | N/A | No autonomous external communications. |
| XV. Backwards Compatibility | PASS | New MCP server; no changes to existing servers. |
| XVI. Spec-Driven Development | PASS | Following full SDD workflow. |

**Gate Result**: ALL PASS.

## Project Structure

### Documentation

```text
specs/033-memory-mcp-server/
├── spec.md              # Feature specification
├── data-model.md        # Entity definitions, schema
├── plan.md              # This file
├── tasks.md             # Implementation tasks
├── contracts/           # MCP tool schemas
└── checklists/          # Completion checklists
```

### Source Code

```text
mcp-servers/memory-mcp/
├── server.py                # Main FastMCP server with 8 tool definitions
├── structured_store.py      # SQLite layer (facts, decisions, schema init)
├── semantic_store.py        # ChromaDB layer (embeddings, similarity search)
├── models.py                # Dataclass definitions (Fact, Decision, SessionSummary)
├── requirements.txt         # Python dependencies (fastmcp, chromadb, sentence-transformers)
├── Dockerfile               # Container image (isolates torch/chromadb/model from host)
├── docker-compose.yml       # Dev convenience (docker compose run)
├── __init__.py              # Package marker
└── README.md                # Server documentation with architecture diagram

workspace/skills/memory-management/
└── SKILL.md                 # Skill documentation (when/how agent uses memory tools)
```

### Storage (created at runtime)

```text
memory/
├── netclaw_memory.db        # SQLite database
└── chromadb/                # ChromaDB persistent storage
```

## Tool Inventory (8 tools)

| Tool | Layer | Type | Description |
|------|-------|------|-------------|
| memory_record_fact | SQLite | Write | Store a fact with entity, key, value, metadata. Auto-supersedes previous. |
| memory_get_facts | SQLite | Read | Get current facts for an entity (optionally filtered by key). |
| memory_timeline | SQLite | Read | Get all facts (including invalidated) for an entity in a time range. |
| memory_invalidate | SQLite | Write | Explicitly mark a fact as no longer valid. |
| memory_record_decision | SQLite | Write | Store an operational decision with context/rationale. |
| memory_get_decisions | SQLite | Read | Query decisions by entity, time range, or text search. |
| memory_store_session | ChromaDB | Write | Embed and store a session summary for semantic retrieval. |
| memory_recall | ChromaDB | Read | Semantic search across stored sessions by natural language query. |

## Dependency Strategy

All heavy dependencies are isolated in a Docker container:

- `chromadb` — file-based vector store, no server needed. Bundles its own SQLite for metadata.
- `sentence-transformers` — local embedding model. Downloads `all-MiniLM-L6-v2` on first use (~80MB, cached in container layer).
- `torch` (CPU-only) — required by sentence-transformers. Installed via pip in container.
- `fastmcp` — MCP framework for tool registration and stdio transport.
- Standard library `sqlite3` — no additional install needed.

**Host impact**: Zero new packages on host. Container image ~2GB (torch + chromadb + model).

**openclaw.json transport**: Uses Docker stdio — `docker run --rm -i -v memory:/data netclaw-memory-mcp` instead of bare Python invocation.

## Graceful Degradation

If ChromaDB or sentence-transformers fails to initialize (import error, model download failure):
- `memory_recall` and `memory_store_session` return `{"error": "SEMANTIC_UNAVAILABLE", "message": "..."}`
- All SQLite-based tools (facts, decisions, timeline, invalidate) continue working normally
- Logged as WARNING at startup, not CRITICAL

## Complexity Tracking

No constitution violations. Single-writer model (stdio = one process) eliminates concurrency concerns.
