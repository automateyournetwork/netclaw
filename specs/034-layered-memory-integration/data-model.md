# Data Model: Layered Memory Integration

**Feature**: 034-layered-memory-integration
**Date**: 2026-06-20

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LAYERED MEMORY SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              TIER 1: MEMORY MCP (Working Memory)             │   │
│  │  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌───────────────┐   │   │
│  │  │  FACT   │  │ DECISION │  │  LINK  │  │    SESSION    │   │   │
│  │  │         │  │          │  │        │  │   (ChromaDB)  │   │   │
│  │  │ entity  │  │ context  │  │subject │  │               │   │   │
│  │  │ key     │  │ decision │  │predicate│ │  summary      │   │   │
│  │  │ value   │  │ rationale│  │object  │  │  entities[]   │   │   │
│  │  │ meta    │  │ entities │  │meta    │  │  topics[]     │   │   │
│  │  │ valid_* │  │ cr_number│  │        │  │  embedding    │   │   │
│  │  └─────────┘  └──────────┘  └────────┘  └───────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              │ consolidation                        │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │            TIER 2: MEMORY.md (Long-Term Memory)              │   │
│  │  ┌─────────────────────────────────────────────────────┐    │   │
│  │  │ ## Patterns                                          │    │   │
│  │  │ - Recurring issue summaries                          │    │   │
│  │  │ - Resolution strategies                              │    │   │
│  │  │                                                      │    │   │
│  │  │ ## Decisions                                         │    │   │
│  │  │ - Significant configuration changes                  │    │   │
│  │  │ - Architectural decisions                            │    │   │
│  │  │                                                      │    │   │
│  │  │ ## Infrastructure                                    │    │   │
│  │  │ - Device roles and locations                         │    │   │
│  │  │ - Network topology facts                             │    │   │
│  │  │ - Operational preferences                            │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Tier 1: Memory MCP Entities

### Fact (SQLite)

Represents a key-value observation about a network entity with temporal validity.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | string | Unique identifier (hex) |
| entity | string | Entity name (lowercase normalized) |
| key | string | Fact type (e.g., "bgp_state", "location") |
| value | string/json | Fact value |
| metadata | json | Optional structured metadata |
| valid_from | timestamp | When fact became valid |
| valid_to | timestamp | When fact was invalidated (null if current) |
| superseded_by | string | ID of fact that replaced this one |
| invalidation_reason | string | Why fact was invalidated |

**Lifecycle**:
```
Created → Current (valid_to=null)
    │
    ├─── Superseded → valid_to set, superseded_by points to new fact
    │
    └─── Invalidated → valid_to set, invalidation_reason recorded
```

### Decision (SQLite)

Represents an operational decision with audit trail.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | string | Unique identifier (dec_xxx) |
| context | string | What situation prompted the decision |
| decision | string | What was decided |
| rationale | string | Why this choice was made |
| created_at | timestamp | When decision was recorded |
| cr_number | string | Optional ServiceNow change request |

**Relationships**:
- Decision → Entity (many-to-many via decision_entities table)

### Entity Link (SQLite)

Represents a relationship between two entities.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | string | Unique identifier (link_xxx) |
| subject | string | Source entity (lowercase) |
| predicate | string | Relationship type |
| object | string | Target entity (lowercase) |
| metadata | json | Optional relationship metadata |
| created_at | timestamp | When link was created |

**Standard Predicates**:
- `peers_with` - BGP/OSPF peering
- `depends_on` - Service dependency
- `connects_to` - Physical/logical connectivity
- `managed_by` - Management relationship
- `caused` - Incident causality
- `fixed_by` - Resolution relationship

### Session (ChromaDB)

Represents a troubleshooting session summary for semantic retrieval.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | string | Unique identifier (sess_xxx) |
| summary | string | Natural language session summary |
| entities | array | Related entity names |
| topics | array | Topic tags (e.g., "bgp", "mtu") |
| embedding | vector | 384-dimension sentence embedding |
| created_at | timestamp | When session was stored |

## Tier 2: MEMORY.md Structure

MEMORY.md is a markdown file with standard sections:

```markdown
# Network Memory

## Patterns

### [Pattern Name]
- **First Observed**: [date]
- **Occurrences**: [count]
- **Entities**: [list]
- **Summary**: [description]
- **Resolution**: [what fixed it]

## Decisions

### [Decision Title] ([CR Number])
- **Date**: [date]
- **Context**: [situation]
- **Decision**: [what was decided]
- **Rationale**: [why]
- **Affected**: [entities]

## Infrastructure

### [Device/System Name]
- **Role**: [function]
- **Location**: [site/rack]
- **Key Facts**: [important attributes]
- **Notes**: [operational knowledge]

## Preferences

- [User/operational preferences discovered during sessions]
```

## Query Patterns

### Entity Lookup

```
1. Query Memory MCP: memory_get_facts(entity="pe2")
2. If results: Return as "Current State"
3. If no results: Search MEMORY.md for "pe2"
4. If found: Return as "Historical Context"
5. If both: Combine with clear labels
```

### Semantic Recall

```
1. Query Memory MCP: memory_recall(query="BGP troubleshooting")
2. Return top 3-5 semantically similar sessions
3. Also grep MEMORY.md for keywords
4. Combine results with relevance scores
```

### Decision Audit

```
1. Query Memory MCP: memory_get_decisions(entity="pe2")
2. Return all decisions affecting pe2
3. Include CR numbers for ServiceNow cross-reference
```

### Impact Analysis

```
1. Query Memory MCP: memory_query_graph(entity="pe2", direction="incoming")
2. Find all entities that depend on pe2
3. Return dependency tree with depth
```

## Consolidation Rules

### Pattern Detection → MEMORY.md

Trigger: Same (entity_type, key, issue_pattern) occurs 3+ times

```python
# Pseudocode
if count(similar_facts) >= 3:
    pattern = {
        "name": generate_pattern_name(facts),
        "first_observed": min(fact.valid_from for fact in facts),
        "occurrences": len(facts),
        "entities": unique(fact.entity for fact in facts),
        "summary": summarize(facts),
        "resolution": extract_resolution(related_decisions)
    }
    append_to_memory_md("## Patterns", pattern)
```

### Decision Consolidation → MEMORY.md

Trigger: Decision with cr_number OR high_impact flag

```python
# Pseudocode
if decision.cr_number or decision.high_impact:
    entry = {
        "title": decision.decision[:50],
        "cr_number": decision.cr_number,
        "date": decision.created_at,
        "context": decision.context,
        "decision": decision.decision,
        "rationale": decision.rationale,
        "affected": decision.entities
    }
    append_to_memory_md("## Decisions", entry)
```

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION LIFECYCLE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SESSION START                                                   │
│  ├── GAIT branch created                                        │
│  ├── memory_get_facts for mentioned entities                    │
│  └── Search MEMORY.md for context                               │
│                                                                  │
│  DURING SESSION                                                  │
│  ├── memory_record_fact when state discovered                   │
│  ├── memory_record_decision when changes made                   │
│  ├── memory_link_entities when relationships found              │
│  └── GAIT: log each memory operation                            │
│                                                                  │
│  SESSION END                                                     │
│  ├── memory_store_session with summary                          │
│  ├── Check for patterns (3+ similar facts)                      │
│  ├── Consolidate patterns → MEMORY.md                           │
│  ├── Consolidate significant decisions → MEMORY.md              │
│  ├── GAIT: log consolidation                                    │
│  └── GAIT commit                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
