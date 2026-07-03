# Quickstart: Layered Memory Integration

**Feature**: 034-layered-memory-integration
**Date**: 2026-06-20

## Overview

NetClaw now has a two-tier memory system that works like a human brain:

| Tier | System | Purpose | Speed |
|------|--------|---------|-------|
| 1 | Memory MCP | Working memory - facts, decisions, relationships, semantic search | Fast (< 2s) |
| 2 | MEMORY.md | Long-term memory - consolidated patterns and institutional knowledge | File read |

## Prerequisites

- Memory MCP Server (Feature 033) installed and configured
- SOUL.md updated with layered memory section
- GAIT enabled for audit logging

## How It Works

### Storing Memory

**During your session**, NetClaw automatically:
1. Records facts when discovering device states
2. Logs decisions when making configuration changes
3. Tracks relationships when learning about topology
4. Logs all operations to GAIT

**At session end**, NetClaw:
1. Stores a session summary for semantic search
2. Checks for recurring patterns (3+ similar issues)
3. Consolidates important patterns/decisions to MEMORY.md

### Retrieving Memory

**When you ask about a device**:
```
You: What do you know about PE2?

NetClaw:
1. Queries Memory MCP for facts about PE2
2. If found: Returns as "Current State"
3. If not found: Searches MEMORY.md
4. Returns as "Historical Context"
```

**When you ask about past work**:
```
You: What do you remember about BGP troubleshooting?

NetClaw:
1. Performs semantic search via memory_recall
2. Returns top matching sessions
3. Also searches MEMORY.md for keywords
```

**When you ask about impact**:
```
You: What depends on PE2?

NetClaw:
1. Queries entity graph for incoming relationships
2. Returns services/devices that depend on PE2
```

## Example Session

```
Session Start
├── GAIT: branch created
├── NetClaw queries memory for mentioned entities
│
├── You: Check BGP status on PE2
│   └── NetClaw: memory_record_fact entity="pe2" key="bgp_state" value="established"
│       GAIT: memory_record_fact: pe2/bgp_state
│
├── You: PE2 peers with RR1, right?
│   └── NetClaw: memory_link_entities subject="pe2" predicate="peers_with" object="rr1"
│       GAIT: memory_link_entities: pe2 peers_with rr1
│
├── You: Increase the hold timer to 180s
│   └── NetClaw: memory_record_decision
│       context="BGP session flapping during maintenance"
│       decision="Increased hold timer from 90s to 180s"
│       rationale="Reduce flap frequency"
│       entities=["pe2", "rr1"]
│       GAIT: memory_record_decision: dec_abc123
│
Session End
├── NetClaw: memory_store_session
│   summary="Troubleshot BGP on PE2. Increased hold timer to 180s to reduce flapping."
│   entities=["pe2", "rr1"]
│   topics=["bgp", "hold-timer", "troubleshooting"]
│   GAIT: memory_store_session: sess_xyz789
│
├── Pattern check: Is this the 3rd+ BGP flapping issue?
│   └── If yes: Consolidate pattern to MEMORY.md
│
└── GAIT: commit
```

## Testing the Integration

### Test 1: Record and Retrieve a Fact

```
You: Remember that R1's status is online

NetClaw: [Records fact to Memory MCP]

You: What do you know about R1?

NetClaw:
Current State (Memory MCP):
- status: online (recorded just now)
```

### Test 2: Semantic Session Recall

```
You: What do you remember about BGP problems?

NetClaw: [Performs semantic search]
Found 2 relevant sessions:
1. "Troubleshot BGP flapping on PE2..." (0.89 similarity)
2. "Fixed BGP convergence issue..." (0.75 similarity)
```

### Test 3: Entity Relationships

```
You: Record that web-service depends on PE2

NetClaw: [Creates link]

You: What would be affected if we take down PE2?

NetClaw: [Queries graph]
Entities depending on PE2:
- web-service (depends_on)
- rr1 (peers_with - bidirectional)
```

### Test 4: Fallback Behavior

```
[Memory MCP unavailable]

You: What do you know about R1?

NetClaw:
⚠️ Memory MCP is currently unavailable. Using MEMORY.md only.

Historical Context (MEMORY.md):
- R1 is a PE router in DC-East
- Last known issue: collision errors on Eth0/2 (2026-03-14)
```

## Memory Tool Reference

| Tool | Example |
|------|---------|
| Record a fact | `memory_record_fact entity="pe2" key="bgp_state" value="established"` |
| Get facts | `memory_get_facts entity="pe2"` |
| Invalidate fact | `memory_invalidate fact_id="abc123" reason="Device decommissioned"` |
| View timeline | `memory_timeline entity="pe2" key="bgp_state"` |
| Store session | `memory_store_session summary="..." entities=["pe2"] topics=["bgp"]` |
| Semantic search | `memory_recall query="BGP troubleshooting" top_k=5` |
| Record decision | `memory_record_decision context="..." decision="..." rationale="..."` |
| Query decisions | `memory_get_decisions entity="pe2"` |
| Link entities | `memory_link_entities subject="pe2" predicate="peers_with" object="rr1"` |
| Query graph | `memory_query_graph entity="pe2" direction="both" depth=2` |

## Troubleshooting

### Memory MCP Not Responding

1. Check if memory-mcp is in `~/.openclaw/config/openclaw.json`
2. Verify the server path is correct
3. Restart the OpenClaw gateway

### Facts Not Being Recorded

1. Check GAIT log for memory operations
2. Verify Memory MCP tools are available to the agent
3. Ensure fact doesn't contain credentials (filtered)

### Semantic Search Returns Empty

1. First session? No sessions stored yet
2. Check ChromaDB directory exists: `~/.openclaw/memory/chroma/`
3. Embeddings may still be loading (cold start)

### MEMORY.md Not Being Updated

1. Consolidation happens at session end, not during
2. Pattern threshold is 3+ similar issues
3. Check GAIT log for consolidation entries
