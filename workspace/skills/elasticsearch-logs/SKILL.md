---
name: elasticsearch-logs
description: Search and analyse logs in an existing Elasticsearch cluster (8.x/9.x) — syslog, application logs, Zeek/Suricata exports, or any indexed event data. Use for "what errors did we see", "how many times did X happen", "show me logs from device Y", "which host logged the most". Read-only. Counting questions MUST go through ESQL or track_total_hits — a bare search total silently caps at 10,000.
---

# Elasticsearch Logs

Read-only log search over an Elasticsearch cluster **you already run**. NetClaw installs no
cluster and indexes nothing — this queries what is already there.

**Server**: `elasticsearch-mcp` (adopted, `docker.elastic.co/mcp/elasticsearch`, Apache-2.0,
digest-pinned) · 5 tools · 1,094 tokens

## The rule that matters most

> **A bare `search` total is capped at 10,000 and reads as if it were exact.**

Elasticsearch stops counting at 10,000 and marks the total `relation: "gte"` — meaning *at
least*. This server discards that qualifier and prints `Total results: 10000`. There is
nothing in the response to tell you the number is a floor.

Measured against 10,075 real documents:

| How you ask | What you get |
|---|---|
| `search` with no guard | `Total results: 10000` — **wrong** |
| `search` with `"track_total_hits": true` | `Total results: 10075` — correct |
| `esql` `STATS COUNT(*)` | `10075` — correct |

On a million-document index a bare search still says 10,000. **The error is unbounded and
invisible.**

**Therefore, for any question of the form "how many", "how often", "which is most", or any
number a human will act on:**

1. Use `esql` with `STATS COUNT(*)`, **or**
2. Use `search` with `"track_total_hits": true` in the `query_body`.

`search` without that guard is for **retrieving example documents only** — never for counting.
If you report a total that came from an unguarded search, you are reporting a number that may
be arbitrarily wrong.

## Tools

| Tool | Use it for | Required arguments |
|---|---|---|
| `list_indices` | what indices exist, and their document counts | `index_pattern` (use `*`) |
| `get_mappings` | field names and types before writing a query | `index` |
| `search` | retrieving matching documents (Query DSL) | `index`, `query_body` |
| `esql` | counting, aggregating, grouping, ranking | `query` |
| `get_shards` | shard health when results look incomplete | — |

Note the argument names are **snake_case** (`query_body`, `index_pattern`). Wrong names fail
loudly with a deserialization error — they are not silently ignored.

## Worked patterns

**How many errors, by device** — a counting question, so ESQL:

```
esql: FROM netclaw-syslog | WHERE severity == "error" | STATS n = COUNT(*) BY device | SORT n DESC
```

**Show me examples of those errors** — a retrieval question, so `search`:

```
search: index=netclaw-syslog
        query_body={"query":{"term":{"severity":"error"}}, "size":20, "track_total_hits":true}
```

**What am I even working with** — always start here on an unfamiliar cluster:

```
list_indices: index_pattern=*
get_mappings: index=<the one you picked>
```

Guessing field names is the most common cause of a query that returns nothing. A `term` query
against a `text` field, or an aggregation on one, will not behave as expected — check the
mapping first. Fields are commonly `foo` (analysed text) plus `foo.keyword` (exact); **use
`.keyword` for grouping, sorting, and exact matches.**

## Empty is not the same as zero

A query returning no hits means **this query found nothing**. It does not establish that the
event did not occur. Before reporting "no errors", confirm:

- the index actually holds data for the time range (`list_indices` doc counts, or an ESQL count
  with no filter)
- the field names came from `get_mappings`, not from a guess
- the time range matches how the data is actually timestamped

Say "no matching events in `<index>` for `<range>`" — not "no errors occurred".

## Boundaries — which backend answers

NetClaw has several log and metric backends. Pick by **where the data lives**, not by question
shape:

| Backend | Use when |
|---|---|
| **this skill** | logs indexed in Elasticsearch / ELK |
| `splunk-search` | logs in Splunk |
| `datadog-logs` | logs in Datadog |
| `gcp-cloud-logging` | Google Cloud audit/platform logs |
| `prometheus-monitoring` / `grafana-observability` | time-series metrics, not logs |
| `duckdb-analysis` | exported files on disk (CSV/Parquet/JSON), not a live store |

If you do not know where the logs live, ask. Do not query every backend hoping one answers —
an empty result from the wrong store is indistinguishable from an absence of events.

## Read-only

All five tools read. There is no index, update, delete, or reindex verb in the manifest, so no
write is reachable regardless of the credential. Prefer an Elasticsearch API key with
`read`/`view_index_metadata` only — the server will happily use a superuser credential, and
nothing in it needs one.

## Configuration

| Variable | Meaning |
|---|---|
| `ES_URL` | cluster URL **as reached from inside the container** — a cluster on this host is `http://host.docker.internal:9200`, not `localhost` |
| `ES_API_KEY` | API key (preferred) |
| `ES_USERNAME` / `ES_PASSWORD` | basic auth alternative |
| `ES_SSL_SKIP_VERIFY` | `true` to skip certificate verification (lab only) |

## Upstream status

This server is **deprecated by Elastic** and receives critical security updates only. It was
adopted deliberately: its replacement, Agent Builder's MCP endpoint, is **Enterprise-tier on
self-managed**, so the supported path is paywalled while this one is Apache-2.0, already
published, and works against a free Basic cluster. The image is digest-pinned so a
security-only update cannot change answers underneath you. See
`specs/096-elastic-logs/spec.md`.
