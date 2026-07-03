# Research: Layered Memory Integration

**Feature**: 034-layered-memory-integration
**Date**: 2026-06-20

## Research Questions Resolved

### Q1: How does Memory MCP Server work?

**Decision**: Use existing Memory MCP Server (Feature 033) with 10 MCP tools

**Rationale**: Feature 033 already implemented the complete Memory MCP server with:
- SQLite storage for facts, decisions, and entity links
- ChromaDB with all-MiniLM-L6-v2 embeddings for semantic session search
- Graceful degradation when embeddings unavailable
- 115 tests passing

**Alternatives Considered**:
- Build new memory system → Rejected: Duplicates Feature 033 work
- Use only MEMORY.md → Rejected: No structured queries or semantic search

### Q2: What Memory MCP tools are available?

**Decision**: Use all 10 tools from Memory MCP Server

**Tools Available**:
| Tool | Purpose |
|------|---------|
| `memory_record_fact` | Store fact with temporal validity |
| `memory_get_facts` | Query current facts for entity |
| `memory_invalidate` | Explicitly invalidate a fact |
| `memory_timeline` | View historical facts including invalidated |
| `memory_store_session` | Store session summary for semantic search |
| `memory_recall` | Natural language search across sessions |
| `memory_record_decision` | Log decision with context and rationale |
| `memory_get_decisions` | Query decisions by entity or time |
| `memory_link_entities` | Create relationship between entities |
| `memory_query_graph` | Traverse entity relationships |

### Q3: How should Memory MCP and MEMORY.md interact?

**Decision**: Two-tier architecture with clear separation

**Rationale**: Each system has distinct strengths:
- Memory MCP: Fast structured queries, semantic search, temporal tracking
- MEMORY.md: Human-readable, narrative context, survives database reset

**Interaction Pattern**:
```
STORING:
  Session events → Memory MCP (immediate)
  Patterns/significant decisions → MEMORY.md (session end)

RETRIEVING:
  Specific entity query → Memory MCP first, fallback to MEMORY.md
  "What do you remember about X?" → Semantic search + MEMORY.md
  Historical context → MEMORY.md first, then Memory MCP timeline
```

### Q4: When should consolidation to MEMORY.md occur?

**Decision**: At the end of each session (natural checkpoint)

**Rationale**:
- Provides consistent timing for consolidation
- Aligns with existing session log pattern
- Allows batch processing of patterns
- Doesn't interrupt active troubleshooting

**Trigger Conditions for Consolidation**:
1. Pattern detected: Same issue type 3+ times
2. Significant decision: High-impact configuration change
3. New permanent knowledge: Infrastructure facts unlikely to change

### Q5: How should memory operations be audited?

**Decision**: Log to GAIT audit trail only

**Rationale**:
- Consistent with NetClaw's existing audit pattern
- Non-intrusive to user experience
- Enables post-session review
- Maintains audit trail integrity

**GAIT Log Format**:
```
GAIT: memory_record_fact: {entity}/{key}
GAIT: memory_store_session: {session_id}
GAIT: memory_record_decision: {decision_id}
GAIT: memory_link_entities: {subject} {predicate} {object}
GAIT: memory_invalidate: {fact_id}
GAIT: memory_consolidate: {pattern_summary}
```

### Q6: What should NOT be stored in memory?

**Decision**: Exclude credentials and secrets only

**Rationale**:
- Network IPs, hostnames, configs are operationally valuable
- Only passwords, API keys, tokens, certificates are security-sensitive
- Aligns with principle XIII (Credential Safety)

**Exclusion Patterns**:
- Any value containing "password", "secret", "token", "key", "certificate"
- Values matching API key patterns (sk-, pk-, etc.)
- Environment variable values from .env files

## Technology Decisions

### Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYERED MEMORY                           │
├─────────────────────────────────────────────────────────────┤
│  TIER 1: Working Memory (Memory MCP)                        │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │    SQLite       │  │    ChromaDB     │                   │
│  │  - Facts        │  │  - Sessions     │                   │
│  │  - Decisions    │  │  - Embeddings   │                   │
│  │  - Links        │  │  - Semantic     │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                              │
│  TIER 2: Long-Term Memory (MEMORY.md)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - Consolidated patterns                             │    │
│  │  - Significant decisions                             │    │
│  │  - Infrastructure facts                              │    │
│  │  - Narrative institutional knowledge                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Query Flow

```
User asks about entity
        │
        ▼
┌───────────────────┐
│ Query Memory MCP  │
│ memory_get_facts  │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    │ Results?  │
    └─────┬─────┘
          │
    Yes   │   No
    ▼     │   ▼
┌─────────┐   ┌────────────┐
│ Return  │   │ Search     │
│ facts   │   │ MEMORY.md  │
│ as      │   │ for entity │
│ current │   └──────┬─────┘
│ state   │          │
└────┬────┘          ▼
     │         ┌───────────┐
     │         │ Return as │
     │         │ historical│
     │         │ context   │
     │         └─────┬─────┘
     │               │
     ▼               ▼
┌─────────────────────────┐
│ Combine in response     │
│ MCP = "Current state"   │
│ MEMORY.md = "History"   │
└─────────────────────────┘
```

## Best Practices Identified

1. **Always query Memory MCP first** for entity-specific questions
2. **Use semantic search** for "what do you remember about" questions
3. **Record facts during discovery** not after the session
4. **Record decisions when made** with full context
5. **Consolidate at session end** not during active work
6. **Never store credentials** in any memory tier
7. **Log all operations to GAIT** for audit compliance
