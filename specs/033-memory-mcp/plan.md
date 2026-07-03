# Implementation Plan: Hybrid Memory MCP Server

**Branch**: `033-memory-mcp` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/033-memory-mcp/spec.md`

## Summary

Implement a hybrid memory MCP server that provides persistent context across NetClaw sessions through three complementary storage layers: structured facts (SQLite with temporal validity), semantic search (ChromaDB with sentence-transformers embeddings), and entity relationship graphs. The server exposes 10 MCP tools enabling the agent to record, query, and reason about network knowledge that survives restarts.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP, sqlite3 (stdlib), chromadb, sentence-transformers, torch (CPU)
**Storage**: SQLite (facts, decisions, links) + ChromaDB (embedded sessions) in ~/.openclaw/memory/
**Testing**: pytest with pytest-asyncio
**Target Platform**: Linux (uvx package with stdio transport, runs inside OpenShell sandbox)
**Project Type**: MCP server (uvx package)
**Performance Goals**: <1s fact retrieval for 100K facts, <30s cold start
**Constraints**: Fully offline after initial model download, ~500MB data for 1 year
**Scale/Scope**: 100K facts, 10K sessions, single-user local deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | N/A | Memory server is read/write to local storage only, no device interaction |
| II. Read-Before-Write | PASS | Fact supersession reads existing state before invalidating |
| III. ITSM-Gated Changes | N/A | No production device changes |
| IV. Immutable Audit Trail | PASS | FR-016 requires GAIT logging for all writes |
| V. MCP-Native Integration | PASS | Built as FastMCP server with 10 tools |
| VI. Multi-Vendor Neutrality | N/A | Vendor-agnostic memory layer |
| VII. Skill Modularity | PASS | Single purpose: persistent memory |
| VIII. Verify After Every Change | PASS | Write operations return confirmation |
| IX. Security by Default | PASS | Local storage with filesystem permissions |
| X. Observability | PASS | GAIT integration for audit |
| XI. Artifact Coherence | PENDING | Checklist in tasks.md |
| XII. Documentation-as-Code | PENDING | SKILL.md to be created |
| XIII. Credential Safety | PASS | No credentials required |
| XIV. Human-in-the-Loop | N/A | No external communications |
| XV. Backwards Compatibility | PASS | New MCP server, no changes to existing |
| XVI. Spec-Driven Development | PASS | Following SDD workflow |
| XVII. Milestone Documentation | PENDING | Blog post at completion |

**Gate Status**: PASS (proceed to Phase 0)

## Project Structure

### Documentation (this feature)

```text
specs/033-memory-mcp/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (MCP tool schemas)
│   └── mcp-tools.md
├── checklists/
│   └── requirements.md  # Specification quality checklist
├── WHY-MEMORY.md        # Motivation document
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
mcp-servers/memory-mcp/
├── memory_mcp_server.py    # Main FastMCP server
├── storage/
│   ├── __init__.py
│   ├── sqlite_store.py     # Structured storage (facts, decisions, links)
│   ├── chroma_store.py     # Semantic storage (sessions)
│   └── schema.sql          # SQLite schema
├── embeddings/
│   ├── __init__.py
│   └── embedder.py         # Sentence-transformers wrapper
├── pyproject.toml          # Python package config (uvx)
└── README.md               # MCP server documentation

scripts/
└── memory-enable.sh        # Enable script for existing users

workspace/skills/memory/
└── SKILL.md                # Skill documentation

tests/
├── unit/
│   ├── test_sqlite_store.py
│   ├── test_chroma_store.py
│   └── test_embedder.py
├── integration/
│   └── test_memory_mcp.py
└── contract/
    └── test_mcp_tools.py
```

**Structure Decision**: Single MCP server project with modular storage backends. Deployed via uvx (consistent with other NetClaw MCP servers). OpenShell provides container isolation at the platform level.

## Complexity Tracking

> No violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
