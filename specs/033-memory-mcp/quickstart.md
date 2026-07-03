# Quickstart: Hybrid Memory MCP Server

**Feature**: 033-memory-mcp
**Date**: 2026-06-20

## Prerequisites

- Python 3.11+ with uv installed
- NetClaw/OpenClaw workspace at `~/.openclaw/`
- At least 500MB free disk space for model cache and data

## Installation

### Option 1: Enable During NetClaw Install

```bash
# During initial installation
./scripts/install.sh
# Answer "y" to "Enable Memory MCP (recommended)?"
```

### Option 2: Enable for Existing Installation

```bash
# Run the enable script
./scripts/memory-enable.sh

# Verify installation
uvx --from netclaw-memory-mcp memory-mcp-server --version
```

## Configuration

The Memory MCP server is configured via environment or MCP config:

### MCP Configuration (~/.openclaw/mcp.json)

```json
{
  "mcpServers": {
    "memory": {
      "command": "uvx",
      "args": ["--from", "netclaw-memory-mcp", "memory-mcp-server"],
      "env": {
        "MEMORY_DATA_DIR": "${HOME}/.openclaw/memory"
      }
    }
  }
}
```

### Data Location

All persistent data stored in `~/.openclaw/memory/`:

```
~/.openclaw/memory/
├── memory.db          # SQLite database (facts, decisions, links)
├── chroma/            # ChromaDB vector store (session embeddings)
└── memory.db-wal      # SQLite WAL file (concurrent access)
```

## Quick Test

After installation, verify the Memory MCP is working:

```bash
# Via Claude Code or NetClaw CLI
> memory_get_facts entity="test"
# Should return: {"success": true, "data": {"entity": "test", "facts": [], "count": 0}}
```

## Basic Usage Examples

### Record a Fact

```
memory_record_fact entity="pe2" key="bgp_state" value="established" metadata={"peer": "10.0.0.1"}
```

### Query Facts

```
memory_get_facts entity="pe2"
```

### Record a Decision

```
memory_record_decision context="BGP flapping on PE2" decision="Increased hold timer to 180s" rationale="Reduce flap frequency during maintenance" entities=["pe2", "rr1"]
```

### Store Session Summary

```
memory_store_session summary="Troubleshot PE2 BGP issue. Root cause: MTU mismatch. Fixed by adjusting PE2 interface MTU to 9000." entities=["pe2", "rr1"] topics=["bgp", "mtu", "troubleshooting"]
```

### Semantic Recall

```
memory_recall query="BGP flapping problem" top_k=3
```

### Link Entities

```
memory_link_entities subject="pe2" predicate="peers_with" object="rr1" metadata={"protocol": "bgp"}
```

### Query Graph

```
memory_query_graph entity="pe2" direction="both" depth=2
```

## Integration with Existing Files

### SOUL.md

Memory directly fulfills Principle #9: *"Get smarter every session."*

The agent automatically records facts and decisions during operation.

### HEARTBEAT.md

Memory enables pattern detection in health checks:

```markdown
### Memory Health
- [ ] **Memory MCP Connected** — memory_get_facts returns successfully
- [ ] **Fact Count** — Track total facts; note growth rate
- [ ] **Pattern Detection** — Flag repeated issues (e.g., "3rd BGP flap this week")
```

### GAIT

All memory write operations log to GAIT for audit:
- `memory_record_fact: pe2/bgp_state`
- `memory_record_decision: dec_xyz789`
- `memory_link_entities: pe2 peers_with rr1`

## Troubleshooting

### Server Won't Start

```bash
# Check if uvx can find the package
uvx --from netclaw-memory-mcp memory-mcp-server --help

# Check uv cache
uv cache list | grep memory

# Clear and reinstall
uv cache clean netclaw-memory-mcp
```

### Database Corruption

```bash
# Backup existing data
cp -r ~/.openclaw/memory ~/.openclaw/memory-backup-$(date +%Y%m%d)

# Check integrity
sqlite3 ~/.openclaw/memory/memory.db "PRAGMA integrity_check;"

# If corrupted, restore from backup or reinitialize
```

### Semantic Search Not Working

If semantic search returns no results but facts work:

1. Check ChromaDB directory exists: `ls ~/.openclaw/memory/chroma/`
2. Verify embedding model downloaded: `ls ~/.cache/huggingface/hub/ | grep MiniLM`
3. The system gracefully degrades — structured queries still work

### Cold Start Slow (>30s)

The embedding model downloads on first use (~80MB) and loads into memory. Subsequent calls are fast.

To pre-warm:
```bash
# Run a dummy query after server starts
memory_recall query="warmup" top_k=1
```

## Data Management

### View Statistics

```bash
# Fact count
sqlite3 ~/.openclaw/memory/memory.db "SELECT COUNT(*) FROM facts;"

# Decision count
sqlite3 ~/.openclaw/memory/memory.db "SELECT COUNT(*) FROM decisions;"

# Link count
sqlite3 ~/.openclaw/memory/memory.db "SELECT COUNT(*) FROM graph_links;"
```

### Manual Backup

```bash
# Stop writes first (or accept point-in-time snapshot)
cp -r ~/.openclaw/memory ~/.openclaw/memory-backup-$(date +%Y%m%d)
```

### Auto-Pruning

Data older than 1 year is automatically pruned. No action needed.

To manually prune older data:
```bash
sqlite3 ~/.openclaw/memory/memory.db "DELETE FROM facts WHERE created_at < datetime('now', '-1 year');"
```

## Next Steps

- Read [WHY-MEMORY.md](./WHY-MEMORY.md) for the motivation behind this feature
- Review [contracts/mcp-tools.md](./contracts/mcp-tools.md) for full API documentation
- See [data-model.md](./data-model.md) for storage schema details
