---
name: mempalace
description: "MemPalace AI memory — persistent memory across sessions. Search past decisions, store architecture choices, track temporal network facts via knowledge graph, navigate cross-domain connections, maintain specialist agent diaries. Use when recalling past decisions, storing important context, tracking network changes over time, or maintaining operational journals."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["MEMPALACE_MCP_SCRIPT", "MCP_CALL"] } } }
---

# MemPalace — AI Memory System

Persistent, structured, local-only memory across sessions. 19 MCP tools.
Source: https://github.com/milla-jovovich/mempalace

> **Relationship to OpenClaw's built-in memory**: OpenClaw writes raw daily logs to `memory/YYYY-MM-DD.md`. MemPalace adds a **structured, searchable layer** on top — semantic search across all sessions, a temporal knowledge graph for network facts, and per-agent diaries. Use daily logs for "what happened today" and MemPalace for "what did we decide and why."

## How to Call the Tools

All tools use mcp-call with the mempalace MCP server:

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" <tool-name> '<arguments-json>'
```

## Palace Read Tools (7)

### `mempalace_status` — Palace Overview

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_status '{}'
```

Returns total drawers, wing/room counts, palace path, memory protocol instructions, and AAAK dialect spec. **Call this at session start** to load palace context.

### `mempalace_get_aaak_spec` — AAAK Dialect Spec

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_get_aaak_spec '{}'
```

Get the AAAK dialect specification — the compressed memory format MemPalace uses. Call this if you need to read or write AAAK-compressed memories.

### `mempalace_search` — Semantic Search

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_search '{"query":"why did we configure OSPF area 10 as stub","limit":5}'
```

**Parameters:**
- `query` (required): Natural language search
- `limit` (optional, default 5): Max results
- `wing` (optional): Restrict to wing
- `room` (optional): Restrict to room

Semantic search. Returns verbatim drawer content with similarity scores.

### `mempalace_list_wings` — List All Wings

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_list_wings '{}'
```
List all wings with drawer counts.### `mempalace_list_rooms` — List Rooms

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_list_rooms '{"wing":"wing_netclaw"}'
```

List rooms within a wing (or all rooms if no wing given).

**Parameters:** `wing` (optional) — filter by wing.

### `mempalace_get_taxonomy` — Full Taxonomy

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_get_taxonomy '{}'
```

Full taxonomy: wing → room → drawer count.

### `mempalace_check_duplicate` — Check Before Filing

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_check_duplicate '{"content":"R1 upgraded to IOS-XE 17.12.1"}'
```

Check if content already exists in the palace before filing.

**Parameters:** `content` (required), `threshold` (optional, default 0.9).


## Palace Write Tools (2)

### `mempalace_add_drawer` — Store Memory

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_add_drawer '{"wing":"wing_netclaw","room":"architecture-decisions","content":"Campus OSPF design: Area 0 backbone on core switches, Area 10 Building A, Area 20 Building B. Stub areas on access layer."}'
```

File verbatim content into the palace. Checks for duplicates first.

**Parameters:**
- `wing` (required): Wing name (project/person)
- `room` (required): Room name (topic/aspect)
- `content` (required): Verbatim content to store — exact words, never summarized
- `source_file` (optional): Where this came from
- `added_by` (optional, default "mcp")

### `mempalace_delete_drawer` — Delete Memory

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_delete_drawer '{"drawer_id":"drawer_wing_netclaw_decisions_abc123"}'
```

Delete a drawer by ID. Irreversible.

## Knowledge Graph Tools (5)

### `mempalace_kg_add` — Add Temporal Fact

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_kg_add '{"subject":"R1","predicate":"runs_version","object":"IOS-XE 17.12.1","valid_from":"2026-03-15"}'
```

Add a fact to the knowledge graph. Subject → predicate → object with optional time window. E.g. ('Max', 'started_school', 'Year 7', valid_from='2026-09-01').

### `mempalace_kg_query` — Query Entity

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_kg_query '{"entity":"R1"}'
```

Query the knowledge graph for an entity's relationships. Returns typed facts with temporal validity. Filter by date with as_of to see what was true at a point in time.

**Parameters:** `entity` (required), `as_of` (optional, YYYY-MM-DD), `direction` (optional: outgoing/incoming/both).

### `mempalace_kg_invalidate` — Mark Fact Expired

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_kg_invalidate '{"subject":"R1","predicate":"runs_version","object":"IOS-XE 17.9.4a","ended":"2026-03-15"}'
```

Mark a fact as no longer true. E.g. ankle injury resolved, job ended, moved house.

### `mempalace_kg_timeline` — Entity Timeline

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_kg_timeline '{"entity":"R1"}'
```

Chronological timeline of facts. Shows the story of an entity (or everything) in order.

### `mempalace_kg_stats` — KG Overview

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_kg_stats '{}'
```

Knowledge graph overview: entities, triples, current vs expired facts, relationship types.

## Navigation Tools (3)

### `mempalace_traverse` — Walk the Palace Graph

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_traverse '{"start_room":"ospf-design","max_hops":2}'
```

Walk the palace graph from a room. Shows connected ideas across wings — the tunnels. Like following a thread through the palace: start at 'chromadb-setup' in wing_code, discover it connects to wing_myproject (planning).

### `mempalace_find_tunnels` — Cross-Wing Connections

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_find_tunnels '{"wing_a":"wing_campus","wing_b":"wing_datacenter"}'
```

Find rooms that bridge two wings — the hallways connecting different domains. E.g. what topics connect wing_code to wing_team?

### `mempalace_graph_stats` — Graph Overview

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_graph_stats '{}'
```

Palace graph overview: total rooms, tunnel connections, edges between wings.

## Agent Diary Tools (2)

### `mempalace_diary_write` — Write Diary Entry

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_diary_write '{"agent_name":"netclaw","entry":"SESSION:2026-04-08|health.check.R1.R2|CPU.normal|OSPF.adjacency.flap.detected.R1-R3|★★★","topic":"operations"}'
```

Write to your personal agent diary in AAAK format. Your observations, thoughts, what you worked on, what matters. Each agent has their own diary with full history. Write in AAAK for compression — e.g. 'SESSION:2026-04-04|built.palace.graph+diary.tools|ALC.req:agent.diaries.in.aaak|★★★'. Use entity codes from the AAAK spec.

### `mempalace_diary_read` — Read Diary History

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_diary_read '{"agent_name":"netclaw","last_n":10}'
```

Read your recent diary entries (in AAAK). See what past versions of yourself recorded — your journal across sessions.

## When to Use

- **Session start**: Call `mempalace_status` to load palace context
- **Before decisions**: Search past sessions for prior decisions on the same topic
- **After changes**: Store architecture decisions, config rationale in palace drawers
- **Tracking upgrades**: Use knowledge graph to record temporal network facts
- **Cross-session troubleshooting**: Search past sessions for similar symptoms
- **Session end**: Write diary entry summarizing observations and lessons

## Network Operations Workflow

### Step 1: Load Palace Context

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_status '{}'
```

### Step 2: Search for Prior Context

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_search '{"query":"BGP migration campus core"}'
```

### Step 3: Record Network Fact

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_kg_add '{"subject":"R1","predicate":"bgp_peer","object":"R2","valid_from":"2026-04-08"}'
```

### Step 4: Store Decision

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_add_drawer '{"wing":"wing_netclaw","room":"routing-decisions","content":"Migrated campus core from OSPF to eBGP. Reason: multi-vendor support (Arista + Cisco). AS 65001 for core, AS 65010-65020 for distribution."}'
```

### Step 5: Write Diary Entry

```bash
python3 $MCP_CALL "python3 -u $MEMPALACE_MCP_SCRIPT" mempalace_diary_write '{"agent_name":"netclaw","entry":"SESSION:2026-04-08|bgp.migration.campus.core|OSPF→eBGP|AS65001.core|multi.vendor.rationale|★★★★"}'
```

## GAIT Audit Trail

Record memory operations in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"Store BGP migration decision in MemPalace","response":"Added drawer to wing_netclaw/routing-decisions: Campus core OSPF→eBGP migration rationale. Added KG triple: R1 bgp_peer R2 (valid_from 2026-04-08). Diary entry recorded.","artifacts":[]}'
```
