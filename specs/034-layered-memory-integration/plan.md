# Implementation Plan: Layered Memory Integration

**Branch**: `034-layered-memory-integration` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/034-layered-memory-integration/spec.md`

## Summary

Integrate Memory MCP Server (Feature 033) with existing MEMORY.md system in SOUL.md as a layered memory architecture. The system mimics human brain organization with two tiers:

1. **Working Memory (Memory MCP)**: SQLite for structured facts/decisions/links, ChromaDB for semantic session search
2. **Long-Term Memory (MEMORY.md)**: Consolidated knowledge distilled from patterns and significant events

All operations logged to GAIT audit trail with timestamps. SOUL.md updated with clear instructions for when to use each system.

## Technical Context

**Language/Version**: Markdown (SOUL.md), Python 3.10+ (Memory MCP already implemented)
**Primary Dependencies**: Memory MCP Server (Feature 033), GAIT, OpenClaw workspace
**Storage**: SQLite (facts, decisions, links), ChromaDB (session embeddings), MEMORY.md (long-term)
**Testing**: Manual verification via 10 representative scenarios
**Target Platform**: OpenClaw/NetClaw agent running via Slack or CLI
**Project Type**: Agent behavior configuration (SOUL.md update)
**Performance Goals**: Memory MCP queries < 2 seconds in 95% of cases
**Constraints**: No credentials/secrets in memory storage, graceful degradation if Memory MCP unavailable
**Scale/Scope**: Single SOUL.md file update, affects all NetClaw sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | ✅ PASS | Memory operations are read/write to local storage only |
| II. Read-Before-Write | ✅ PASS | Memory MCP queries before MEMORY.md updates |
| III. ITSM-Gated Changes | N/A | No device changes involved |
| IV. Immutable Audit Trail | ✅ PASS | FR-011 requires GAIT logging for all memory ops |
| V. MCP-Native Integration | ✅ PASS | Uses Memory MCP Server (Feature 033) |
| VII. Skill Modularity | ✅ PASS | Memory skills compose with existing skills |
| IX. Security by Default | ✅ PASS | FR-012 excludes credentials from memory storage |
| XI. Full-Stack Artifact Coherence | ⚠️ REQUIRES | SOUL.md, TOOLS.md updates needed |
| XII. Documentation-as-Code | ✅ PASS | Quickstart and spec docs included |
| XIII. Credential Safety | ✅ PASS | FR-012 explicitly forbids credential storage |
| XVI. Spec-Driven Development | ✅ PASS | Following SDD workflow |

**Gate Result**: PASS - All applicable principles satisfied or planned for.

## Project Structure

### Documentation (this feature)

```text
specs/034-layered-memory-integration/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── soul-memory-section.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
# Primary deliverables - SOUL.md integration
~/.openclaw/workspace/
├── SOUL.md              # UPDATED: Add layered memory instructions
├── MEMORY.md            # EXISTING: Long-term memory file
└── memory/              # EXISTING: Session logs (YYYY-MM-DD.md)

# Memory MCP Server (Feature 033 - already exists)
mcp-servers/memory-mcp/
├── memory_mcp_server.py # 10 MCP tools
├── storage/
│   ├── sqlite_store.py  # Facts, decisions, links
│   └── chroma_store.py  # Semantic session search
└── embeddings/
    └── embedder.py      # all-MiniLM-L6-v2

# Data storage
~/.openclaw/memory/
├── memory.db            # SQLite database
└── chroma/              # ChromaDB vector store
```

**Structure Decision**: This is primarily a documentation/configuration update. The Memory MCP server already exists from Feature 033. Main deliverable is SOUL.md section updates.

## Complexity Tracking

No violations requiring justification. Implementation is straightforward SOUL.md update.
