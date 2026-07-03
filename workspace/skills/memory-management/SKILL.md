---
name: memory-management
description: "Record and recall network facts, decisions, and session context using hybrid structured + semantic memory"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["docker"], "env": [] } } }
---
# Memory Management

## Architecture

The memory MCP server runs as a Docker container (`netclaw-memory-mcp`). Both storage engines are inside the container:
- **SQLite** — structured facts and decisions with temporal validity
- **ChromaDB** — embedded session summaries for semantic search (uses `all-MiniLM-L6-v2` model)

Data persists on the host at `memory/` via volume mount. No deps installed on the host.

## When to Use

- **Record facts** when you discover device state, configuration values, relationship changes, or any information that may be useful in future sessions.
- **Record decisions** when you make or recommend a significant operational decision (shut a peer, change a route policy, quarantine a device, defer a change).
- **Store session summaries** at the end of substantive interactions (troubleshooting sessions, audits, deployments, investigations).
- **Recall facts** when the user asks about a device's history, when you need context from previous sessions, or before making decisions that depend on prior state.
- **Semantic recall** when the user asks fuzzy questions like "what was that issue last week?" or "have we seen this before?"

## Procedure

### Recording Facts (During Operations)

After discovering a noteworthy fact (health check, state change, new peering, version upgrade):

1. Call `memory_record_fact` with:
   - `entity`: device name or qualified name (e.g., "PE2", "Gi0/0/0/1@PE2")
   - `key`: descriptive key (e.g., "bgp_peer_10.0.0.1_state", "os_version", "cpu_5min")
   - `value`: the discovered value
   - `metadata`: JSON with extra context (interface, peer IP, threshold)
   - `source`: which tool discovered it (e.g., "pyats_health_check", "gnmi_get")

### Recording Decisions (After Significant Actions)

After making or recommending a consequential decision:

1. Call `memory_record_decision` with:
   - `context`: what situation prompted the decision
   - `decision`: what was decided
   - `rationale`: why (cite evidence — metrics, logs, thresholds)
   - `entities`: comma-separated related devices/services
   - `cr_number`: if an ITSM change was involved

### Session Summaries (At Session End)

Before a session ends or when a major investigation concludes:

1. Call `memory_store_session` with:
   - `summary`: 2-4 sentence description of what happened and outcome
   - `entities`: key devices/services involved
   - `topics`: relevant tags (e.g., "bgp,flapping,troubleshooting")

### Querying Memory (At Session Start or When Needed)

When context from previous sessions would help:

1. **Specific entity**: `memory_get_facts(entity="PE2")` → current known state
2. **History**: `memory_timeline(entity="PE2", start="2026-05-01")` → what changed over time
3. **Decisions**: `memory_get_decisions(entity="PE2")` → why past decisions were made
4. **Fuzzy recall**: `memory_recall(query="BGP flapping on the route reflectors")` → semantic search

## Key Principles

- **Record early, recall often** — the cost of storing is near-zero; the value of recalling is high
- **Entity naming consistency** — always use the same entity name (e.g., "PE2" not "pe2" or "PE-2")
- **Facts supersede automatically** — recording a new fact with same entity+key invalidates the old one
- **Semantic search is fuzzy** — use it for "what was that thing?" questions, not exact lookups
- **Never store credentials** — memory is for network state, not secrets
