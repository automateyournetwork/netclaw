# Quickstart: Memory MCP Server

## Prerequisites

- Docker installed and running
- NetClaw repo cloned (referred to as `<project>` below — your repo root)

## Build

```bash
cd <project>/mcp-servers/memory-mcp
docker build -t netclaw-memory-mcp .
```

First build downloads ~2GB of deps (torch CPU, chromadb, sentence-transformers, embedding model). Subsequent builds are cached.

## Verify

```bash
mkdir -p <project>/memory
docker run --rm -i -v <project>/memory:/data netclaw-memory-mcp
```

Expected: FastMCP startup banner. Ctrl+C to stop.

## Use with OpenClaw

Already registered in `config/openclaw.json`. Start OpenClaw normally:

```bash
openclaw gateway    # terminal 1
openclaw tui        # terminal 2
```

Then in chat:
```
Remember that PE2's BGP peer 10.0.0.1 went down at 14:30 today.
```

The agent will call `memory_record_fact(entity="PE2", key="bgp_peer_10.0.0.1_state", value="down", ...)`.

Later (even in a different session):
```
What do we know about PE2?
```

The agent calls `memory_get_facts(entity="PE2")` and returns the stored facts.

## Test End-to-End (Without OpenClaw)

```bash
docker run --rm --entrypoint python3 \
  -v <project>/memory:/data \
  netclaw-memory-mcp -c "
from structured_store import StructuredStore
from semantic_store import SemanticStore
from models import Fact, SessionSummary

# Structured
store = StructuredStore('/data/netclaw_memory.db')
store.record_fact(Fact(entity='PE2', key='bgp_state', value='Established'))
print(store.get_facts('PE2'))
store.close()

# Semantic
sem = SemanticStore('/data/chromadb')
if sem.available:
    s = SessionSummary(summary='Fixed BGP flapping on PE2 caused by MTU mismatch')
    sem.store_session(s.id, s.summary, s.timestamp, ['PE2'], ['bgp','mtu'])
    print(sem.recall('BGP issue on PE2'))
"
```

## Data Location

All persistent data lives on the host at:
```
<project>/memory/
├── netclaw_memory.db    ← SQLite (facts + decisions)
└── chromadb/            ← Embeddings (session summaries)
```

This directory is gitignored. Back it up if you want to preserve memory across rebuilds.

## Wipe Memory (Start Fresh)

```bash
rm -rf <project>/memory/netclaw_memory.db
rm -rf <project>/memory/chromadb/
```

Next container start will recreate empty stores automatically.
