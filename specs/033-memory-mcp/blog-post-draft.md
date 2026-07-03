# NetClaw Now Remembers: Introducing the Memory MCP Server

**TL;DR**: NetClaw can now remember facts about your network, recall past troubleshooting sessions, audit decisions, and track entity relationships — all persisted locally and available across sessions.

---

## The Problem: Groundhog Day Troubleshooting

Every network engineer has experienced it: you troubleshoot an issue, solve it, and three months later face the exact same problem — but you've forgotten the solution. Or worse, a colleague asks why a particular change was made, and nobody remembers the context.

AI assistants made this worse, not better. Each session starts fresh. Every conversation begins with "I don't have any previous context about your network." The assistant that helped you fix BGP flapping last week has no memory of it today.

Until now.

---

## Introducing the Memory MCP Server

The Memory MCP Server brings persistent, structured memory to NetClaw. It's not just a chat history — it's a hybrid storage system designed specifically for network operations:

### 1. Structured Facts with Temporal Validity

Record facts about your network entities with automatic versioning:

```
memory_record_fact entity="pe2" key="bgp_state" value="established"
```

When the state changes, the old fact is automatically superseded — but preserved in the timeline for historical analysis. Query current state or view the full history:

```
memory_get_facts entity="pe2"
memory_timeline entity="pe2" key="bgp_state"
```

### 2. Semantic Search Across Sessions

Store session summaries and find them later with natural language:

```
memory_store_session summary="Fixed BGP flapping on PE2 by adjusting MTU from 1500 to 9000. Root cause was jumbo frame mismatch with upstream provider." entities=["pe2"] topics=["bgp", "mtu"]
```

Three months later:

```
memory_recall query="BGP problems with MTU"
```

The system uses sentence-transformers embeddings (all-MiniLM-L6-v2) to find semantically similar sessions — even if you don't remember the exact words you used.

### 3. Decision Audit Trail

Every operational decision deserves context. Record not just *what* was decided, but *why*:

```
memory_record_decision
  context="PE2 BGP session flapping every 30 seconds during maintenance window"
  decision="Increased BGP hold timer from 90s to 180s"
  rationale="Reduce flap frequency while investigating root cause. Temporary measure until MTU issue resolved."
  entities=["pe2", "rr1"]
  cr_number="CHG0001234"
```

When auditors ask "why was this changed?", you have the answer.

### 4. Entity Relationship Graph

Track how your network entities relate to each other:

```
memory_link_entities subject="pe2" predicate="peers_with" object="rr1"
memory_link_entities subject="web-service" predicate="depends_on" object="pe2"
```

Query relationships to understand impact:

```
memory_query_graph entity="pe2" direction="incoming" depth=2
```

Now you know that taking down PE2 affects not just the BGP peering with RR1, but also the web service that depends on it.

---

## Architecture: Hybrid by Design

We didn't just bolt a database onto an LLM. The Memory MCP Server uses the right storage for each job:

| Data Type | Storage | Why |
|-----------|---------|-----|
| Facts, Decisions, Links | SQLite (WAL mode) | Fast, reliable, queryable, zero dependencies |
| Session Summaries | ChromaDB + embeddings | Semantic similarity search |

Everything is stored locally in `~/.openclaw/memory/`. No cloud. No subscriptions. Your network knowledge stays on your machine.

---

## Graceful Degradation

What if sentence-transformers isn't available? The server keeps working. Structured queries (facts, decisions, links) function normally. Only semantic search degrades — and it tells you why:

```json
{
  "success": true,
  "data": {
    "results": [],
    "count": 0,
    "note": "Semantic search unavailable - embeddings not loaded"
  }
}
```

No crashes. No mysteries. Just honest feedback.

---

## Getting Started

### Enable During Installation

```bash
./scripts/install.sh
# Answer "y" to "Enable Memory MCP (recommended)?"
```

### Or Enable Later

```bash
./scripts/memory-enable.sh
```

### Quick Test

```bash
# Record a fact
memory_record_fact entity="test-router" key="status" value="online"

# Query it back
memory_get_facts entity="test-router"
```

---

## The 10 MCP Tools

| Tool | Purpose |
|------|---------|
| `memory_record_fact` | Store a fact with temporal validity |
| `memory_get_facts` | Query current facts for an entity |
| `memory_invalidate` | Explicitly invalidate a fact |
| `memory_timeline` | View historical facts including invalidated |
| `memory_store_session` | Store session summary for semantic search |
| `memory_recall` | Natural language search across sessions |
| `memory_record_decision` | Log decision with context and rationale |
| `memory_get_decisions` | Query decisions by entity or time |
| `memory_link_entities` | Create relationship between entities |
| `memory_query_graph` | Traverse entity relationships |

---

## What This Enables

With persistent memory, NetClaw can now:

- **Learn from past incidents**: "This looks similar to the BGP issue we fixed on PE2 last month..."
- **Provide audit trails**: "This hold timer was changed in CHG0001234 because of flapping during the March maintenance."
- **Understand impact**: "PE2 has 3 services depending on it — let me check their health before we proceed."
- **Build institutional knowledge**: Every troubleshooting session adds to the knowledge base, available to anyone who works on the network.

---

## Technical Details

- **Storage**: SQLite with WAL mode for concurrent access
- **Embeddings**: all-MiniLM-L6-v2 (384 dimensions, ~80MB)
- **Vector Store**: ChromaDB with cosine similarity
- **Transport**: STDIO MCP protocol
- **Deployment**: uvx package (OpenShell provides container isolation)
- **Data Retention**: Auto-prune after 1 year (configurable)

---

## What's Next

This is v1. On the roadmap:

- **Cross-device pattern detection**: "PE2 and PE3 both had the same issue within 24 hours"
- **Proactive insights**: "Based on past incidents, this configuration change has a 40% chance of causing BGP flaps"
- **Team memory sharing**: Export/import knowledge bases between NetClaw instances

---

## Try It Today

The Memory MCP Server is available now in NetClaw. Enable it, start recording facts, and watch your network assistant get smarter with every session.

Because an AI that forgets everything isn't really an assistant — it's just a very expensive search engine.

---

*Feature 033-memory-mcp | 10 MCP tools | 115 tests passing | Zero cloud dependencies*
