# Why Memory Changes Everything for NetClaw

**A Plain-Language Guide to the Hybrid Memory System**

---

## The Problem: NetClaw Has Amnesia

Every time you start a new session with NetClaw, it's like meeting a new coworker who:

- Doesn't know your network topology
- Has never heard of "PE2" or "the DC-East core"
- Forgot that you fixed an MTU issue last week
- Doesn't remember that you prefer detailed BGP output
- Can't recall why you made that routing change last month

You end up repeating yourself. A lot.

```
Monday:  "PE2's BGP to RR1 is flapping"
         NetClaw investigates, finds MTU mismatch, fixes it.

Friday:  "PE2 is having issues again"
         NetClaw: "What is PE2? Can you describe your topology?"
         You: *sighs heavily*
```

---

## The Solution: Give NetClaw a Memory

Imagine if instead, Friday went like this:

```
Friday:  "PE2 is having issues again"
         NetClaw: "PE2 - your core PE router in DC-East, right?
                  Last Monday we fixed an MTU mismatch on the BGP
                  session to RR1. Is it the same peer flapping, or
                  something different? I can check current state
                  and compare to what I recorded last time."
         You: *chef's kiss*
```

That's what the Memory MCP gives NetClaw.

---

## Three Types of Memory Working Together

### 1. Structured Memory (The Filing Cabinet)

**What it stores**: Facts with timestamps

```
Entity: PE2
  - bgp_peer_rr1_state: "established" (since 2026-06-15)
  - last_config_change: "2026-06-10" (MTU adjustment)
  - management_ip: "10.1.1.2"
  - location: "DC-East, Rack 14"
```

**What you can ask**:
- "What's PE2's BGP state?"
- "When was PE2 last changed?"
- "Show me PE2's history this month"

This is precise, fast, and exactly right.

### 2. Semantic Memory (The Searchable Journal)

**What it stores**: Summaries of past sessions, embedded for similarity search

```
Session 2026-06-15:
  "Troubleshot BGP flapping between PE2 and RR1. Root cause was
  MTU mismatch - PE2 had 1500, path required 9000 for jumbo frames.
  Adjusted PE2's interface MTU. BGP came up stable after 30 seconds."
```

**What you can ask**:
- "What was that BGP issue we fixed last week?"
- "Have we seen MTU problems before?"
- "What troubleshooting have we done on the DC routers?"

This is fuzzy, contextual, and finds things even when you don't remember exact names.

### 3. Graph Memory (The Relationship Map)

**What it stores**: How entities relate to each other

```
PE2 --[peers_with]--> RR1
PE2 --[connects_to]--> SW1
PE2 --[depends_on]--> DC-East-Power
RR1 --[serves]--> PE1, PE2, PE3, PE4
```

**What you can ask**:
- "What devices depend on RR1?"
- "If DC-East-Power fails, what's affected?"
- "Show me PE2's relationships"

This enables impact analysis and topology awareness.

---

## How It Makes NetClaw Smarter

| Situation | Without Memory | With Memory |
|-----------|----------------|-------------|
| "Check PE2" | "What is PE2? What's its IP?" | "PE2 at 10.1.1.2, checking BGP state..." |
| "That BGP thing" | "I don't have context for that" | "Found 3 BGP sessions. The June 15th MTU fix?" |
| "Why did we do X?" | "I have no record of that decision" | "Decision log: 'Reduced BGP timers for faster convergence'" |
| "Is this a pattern?" | "I can only see this session" | "3rd BGP flap on PE2 this month. Pattern detected." |

---

## Integration with Existing NetClaw Files

### SOUL.md

Memory directly fulfills **Principle #9**: *"Every time you learn something about how I work or what I need, update the relevant file immediately. Don't ask. Just write it down. Get smarter every session."*

### SOUL-EXPERTISE.md

SOUL-EXPERTISE is static reference knowledge. Memory adds an environmental layer:

| SOUL-EXPERTISE (Static) | Memory (Dynamic) |
|-------------------------|------------------|
| "BGP uses TCP port 179" | "PE2's BGP uses MD5 auth, key rotates quarterly" |
| "OSPF areas should be contiguous" | "This network has discontiguous area 0 - documented exception" |

### HEARTBEAT.md

Memory enhances heartbeats with pattern detection:

> "CML is up. IP Fabric shows 154 devices. Memory shows 3 BGP flaps on PE2 this week - want me to investigate the pattern?"

### GAIT

GAIT records *what happened*. Memory records *what it means*. They complement each other.

---

## Persistence: Survives Restarts

All data lives in `~/.openclaw/memory/` and survives restarts:
- Structured facts in a local database
- Embedded sessions in a vector store
- Graph relationships alongside facts

No cloud dependencies. Fully offline after initial setup.

---

## The 10 Memory Tools

| Tool | Purpose |
|------|---------|
| `memory_record_fact` | Store a fact with temporal validity |
| `memory_get_facts` | Query current facts for an entity |
| `memory_invalidate` | Mark a fact as no longer current |
| `memory_timeline` | Query historical facts including invalidated |
| `memory_store_session` | Store session summary for semantic search |
| `memory_recall` | Semantic search across past sessions |
| `memory_record_decision` | Log a decision with rationale |
| `memory_get_decisions` | Query past decisions |
| `memory_link_entities` | Create relationship between entities |
| `memory_query_graph` | Query entity relationships |

---

## Summary

**Memory transforms NetClaw from a capable tool into a true digital coworker that knows your network.**

No more repeating yourself. No more lost context. No more "what is PE2?"

Just an agent that gets smarter every session.
