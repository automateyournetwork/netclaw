# Skill: Persistent Memory

**Purpose**: Provide persistent context across NetClaw sessions through structured facts, semantic search, and entity relationships.

## Overview

The Memory skill enables NetClaw to remember information about your network across sessions. Instead of re-explaining your topology, device names, and past issues every time, NetClaw builds a knowledge base that grows smarter with each interaction.

## Capabilities

### 1. Structured Fact Storage
Store precise facts about network entities with temporal validity:
- Device states, configurations, IP addresses
- Maintenance windows, change history
- Performance baselines, thresholds

### 2. Semantic Recall
Search past sessions using natural language:
- "What was that BGP issue last month?"
- "Show me troubleshooting related to MTU"
- "Find sessions about PE2"

### 3. Decision Logging
Record operational decisions with rationale:
- Why a route was changed
- Why a device was quarantined
- Links to ServiceNow change requests

### 4. Entity Relationships
Track network topology and dependencies:
- PE2 peers_with RR1
- Service-X depends_on Device-Y
- Impact analysis for changes

## MCP Tools

| Tool | Purpose |
|------|---------|
| `memory_record_fact` | Store a fact with temporal validity |
| `memory_get_facts` | Query current facts for an entity |
| `memory_invalidate` | Mark a fact as no longer current |
| `memory_timeline` | Query historical facts |
| `memory_store_session` | Store session summary for semantic search |
| `memory_recall` | Semantic search across past sessions |
| `memory_record_decision` | Log a decision with rationale |
| `memory_get_decisions` | Query past decisions |
| `memory_link_entities` | Create relationship between entities |
| `memory_query_graph` | Query entity relationships |

## Usage Examples

### Record a Fact
```
memory_record_fact entity="PE2" key="bgp_state" value="established" metadata={"peer": "10.0.0.1"}
```

### Query Facts
```
memory_get_facts entity="PE2"
```

### Semantic Search
```
memory_recall query="BGP flapping problem" top_k=5
```

### Record a Decision
```
memory_record_decision context="PE2 BGP session flapping" decision="Increased hold timer to 180s" rationale="Reduce flap frequency" entities=["PE2", "RR1"] cr_number="CHG0001234"
```

### Link Entities
```
memory_link_entities subject="PE2" predicate="peers_with" object="RR1"
```

## Data Storage

All memory data persists in `~/.openclaw/memory/`:
- `memory.db` - SQLite database (facts, decisions, links)
- `chroma/` - ChromaDB vector store (session embeddings)

Data is automatically pruned after 1 year.

## Integration

### With GAIT
All memory write operations log to GAIT for audit trail.

### With HEARTBEAT
Memory enables pattern detection in health checks:
> "3rd BGP flap on PE2 this week - want me to investigate?"

### With SOUL
Memory directly fulfills Principle #9: "Get smarter every session."

## Prerequisites

- Memory MCP server enabled (`./scripts/memory-enable.sh`)
- ~500MB disk space for 1 year of data
- First run downloads embedding model (~80MB)

## Troubleshooting

### Server Won't Start
```bash
uvx --from netclaw-memory-mcp memory-mcp-server --help
```

### Check Data Directory
```bash
ls -la ~/.openclaw/memory/
```

### Verify Database
```bash
sqlite3 ~/.openclaw/memory/memory.db "SELECT COUNT(*) FROM facts;"
```
