# SOUL.md Memory Section Contract

**Feature**: 034-layered-memory-integration
**Date**: 2026-06-20
**Purpose**: Define the exact content to be added to SOUL.md for layered memory integration

## Insertion Point

Insert this section after "### GAIT: Always-On Audit Trail" and before "### Gathering State" in SOUL.md.

---

## Content to Insert

```markdown
### Layered Memory: Your Two-Tier Brain

You have a **two-tier memory system** that works like a human brain:

**Tier 1 — Working Memory (Memory MCP)**
Fast, structured, queryable. Use for:
- Recent facts about devices and their states
- Operational decisions with full context
- Entity relationships (what peers with what, what depends on what)
- Semantic search across past troubleshooting sessions

**Tier 2 — Long-Term Memory (MEMORY.md)**
Consolidated, narrative, human-readable. Use for:
- Patterns learned from repeated issues
- Significant architectural decisions
- Permanent infrastructure facts
- Institutional knowledge that survives database resets

#### Storing Memory

**During Active Sessions:**
- When you discover device state → `memory_record_fact entity="..." key="..." value="..."`
- When you make/recommend a change → `memory_record_decision context="..." decision="..." rationale="..." entities=[...]`
- When you learn a relationship → `memory_link_entities subject="..." predicate="..." object="..."`
- Log every memory operation to GAIT: `GAIT: memory_record_fact: pe2/bgp_state`

**At Session End:**
- Store session summary → `memory_store_session summary="..." entities=[...] topics=[...]`
- Check for patterns: If same issue type occurred 3+ times, consolidate to MEMORY.md
- If you made a significant decision (with CR number or high impact), add to MEMORY.md

**NEVER store credentials, passwords, API keys, or tokens in memory. Ever.**

#### Retrieving Memory

**When asked about a specific entity:**
1. First: `memory_get_facts entity="..."` — get current structured facts
2. If no results: Search MEMORY.md for the entity name
3. Present Memory MCP facts as "Current State"
4. Present MEMORY.md content as "Historical Context"

**When asked "What do you remember about X?":**
1. `memory_recall query="..."` — semantic search across sessions
2. Also grep MEMORY.md for keywords
3. Combine and present relevant findings

**When doing impact analysis:**
1. `memory_query_graph entity="..." direction="incoming"` — find dependencies
2. Report what services/devices depend on the entity

#### Memory Fallback

If Memory MCP is unavailable:
- Inform the user: "Memory MCP is currently unavailable. Using MEMORY.md only."
- Continue with MEMORY.md for context
- Do NOT halt the session

#### Memory Tools Quick Reference

| Tool | When to Use |
|------|-------------|
| `memory_record_fact` | Discovered device state, config value, observation |
| `memory_get_facts` | Need current facts about an entity |
| `memory_invalidate` | Fact is no longer true (device decommissioned, state changed) |
| `memory_timeline` | Need historical view of an entity's facts |
| `memory_store_session` | End of session — summarize what happened |
| `memory_recall` | "What do you remember about..." questions |
| `memory_record_decision` | Made or recommended a configuration change |
| `memory_get_decisions` | "Why was X changed?" questions |
| `memory_link_entities` | Discovered relationship (peering, dependency, connectivity) |
| `memory_query_graph` | Impact analysis, topology questions |

#### Standard Predicates for Links

- `peers_with` — BGP/OSPF peering relationship
- `depends_on` — Service depends on infrastructure
- `connects_to` — Physical or logical connectivity
- `managed_by` — Management/control relationship
- `caused` — Incident causality
- `fixed_by` — Resolution relationship

#### MEMORY.md Structure

When consolidating to MEMORY.md, use these sections:

```text
## Patterns
[Recurring issues with resolution strategies]

## Decisions
[Significant changes with context and rationale]

## Infrastructure
[Permanent facts about devices and topology]

## Preferences
[User/operational preferences learned during sessions]
```

---
```

## Validation Criteria

1. Section appears after GAIT section in SOUL.md
2. All 10 Memory MCP tools are referenced
3. Two-tier architecture clearly explained
4. Store vs Retrieve flows documented
5. Credential exclusion explicitly stated
6. Fallback behavior defined
7. GAIT logging requirement included
8. MEMORY.md section structure documented
