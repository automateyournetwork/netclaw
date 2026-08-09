# Contract — Tool surface

**Server**: `elasticsearch-mcp` · image `docker.elastic.co/mcp/elasticsearch@sha256:d57ea11d…eb003`
**Reports**: `elasticsearch_core_mcp_server` 0.4.6 · MCP framework `rmcp` 0.2.1 · protocol `2025-03-26`
**Manifest**: 5 tools, 1,089 tokens + 5 tokens `instructions` = **1,094 / 5,000**

All five tools were exercised live against Elasticsearch 9.2.0 with 25,000 documents.

---

## Tools

| Tool | Required args | Returns | Cost |
|---|---|---|---|
| `list_indices` | `index_pattern` | index name, status, `docs.count` | 596 |
| `get_mappings` | `index` | field names and types | 601 |
| `search` | `index`, `query_body` | `Total results: N, showing M.` + documents (+ `Aggregations results:` when aggs are present) | 683 |
| `esql` | `query` | `Results` + rows | 596 |
| `get_shards` | — | shard allocation and health | 597 |

**Argument names are snake_case** — `query_body`, `index_pattern`. Wrong names fail loudly:

```
failed to deserialize parameters: missing field `query_body`
```

This is a JSON-RPC error, not a silent drop. (Contrast spec 095, where Juniper's Mist server
silently discarded a top-level `query_type` and then reported it missing.)

---

## Read-only guarantee

The manifest contains **no** index, update, delete, reindex, or ILM verb. No write is reachable
regardless of the credential supplied — this is a property of the tool surface, not of the token.

The skill nonetheless requires an API key scoped to `read` + `view_index_metadata`. The server will
use a superuser credential if given one; nothing here needs it.

---

## Error behaviour (verified)

| Condition | Response |
|---|---|
| Wrong argument name | JSON-RPC error naming the missing field |
| Aggregation on a `text` field | JSON-RPC error (Elasticsearch's own HTTP 400, surfaced) |
| Valid aggregation | `Aggregations results:` + buckets matching raw `_search` exactly |
| Query matching nothing | `Total results: 0` — a real answer, not an error |
| `ES_URL` unreachable | tool call fails; the server still starts (so absence of data ≠ absence of server) |

Two behaviours were suspected defects and **cleared**: aggregations are not dropped, and errors are
not swallowed. See `../research.md` R8.

---

## The exception to "the tools are trustworthy"

`search`'s total is **not** trustworthy without a guard. See
[counting-invariant.md](counting-invariant.md) — that contract governs every numeric answer this
server produces.

---

## Configuration contract

| Variable | Required | Meaning |
|---|---|---|
| `ES_URL` | yes | cluster URL **as resolved inside the container** — a host cluster is `http://host.docker.internal:9200`, never `localhost` |
| `ES_API_KEY` | one of | API key (preferred) |
| `ES_USERNAME` + `ES_PASSWORD` | one of | basic auth |
| `ES_SSL_SKIP_VERIFY` | no | `true` for lab self-signed certs only |

The registration passes `--add-host=host.docker.internal:host-gateway` so the local-cluster case
works without `--network host`, which would be Linux-only.
