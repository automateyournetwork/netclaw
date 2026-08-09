# Quickstart — Elasticsearch log search

**Feature**: 096 (R12) | **Server**: `elasticsearch-mcp` | **Read-only**

NetClaw installs no Elasticsearch. You bring a cluster; this connects to it.

---

## 1. Point at your cluster

Add to `~/.openclaw/.env`:

```bash
# A cluster on THIS host is host.docker.internal, not localhost --
# ES_URL is resolved inside the MCP container.
ES_URL=http://host.docker.internal:9200
ES_API_KEY=your_read_only_api_key      # or ES_USERNAME + ES_PASSWORD
```

Grant the key `read` + `view_index_metadata` only. Nothing here needs more.

For a remote cluster: `ES_URL=https://your-host:9243` and drop the `host.docker.internal` concern.

## 2. Install

```bash
./scripts/install.sh          # select "Elasticsearch Logs", or the observability profile
```

This pulls the digest-pinned image. Requires Docker.

## 3. Verify

```bash
python3 scripts/check-server-startup.py --only elasticsearch-mcp
```

A **timeout is success** — a server that imports cleanly then blocks on stdio is behaving correctly.

## 4. First real query

Always start by finding out what you have:

```
list_indices: index_pattern=*
```

Then read the mapping before composing anything — guessed field names are the most common cause of
a false empty result:

```
get_mappings: index=<your-index>
```

## 5. Counting — read this before you report a number

```
esql: FROM your-index | WHERE severity == "error" | STATS n = COUNT(*)
```

**Do not count with a bare `search`.** Elasticsearch caps totals at 10,000 and this server discards
the marker that says so, printing `Total results: 10000` whether the true figure is 10,000 or
1,000,000.

If you need documents *and* a true total:

```
search: index=your-index
        query_body={"query":{"term":{"severity":"error"}}, "size":20, "track_total_hits":true}
```

Measured: 10,075 real documents reported as **10,000** without the guard, **10,075** with it.
Full detail in [contracts/counting-invariant.md](contracts/counting-invariant.md).

## 6. Grouping and sorting

Use the `.keyword` sibling of a `text` field. A `terms` aggregation on a bare `text` field is
rejected by Elasticsearch:

```
esql: FROM your-index | STATS n = COUNT(*) BY device | SORT n DESC | LIMIT 10
```

---

## Try it with throwaway data

To see the trap for yourself:

```bash
docker run -d --name netclaw-es -p 9200:9200 \
  -e discovery.type=single-node -e xpack.security.enabled=false \
  -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" \
  docker.elastic.co/elasticsearch/elasticsearch:9.2.0
```

Index more than 10,000 matching documents, then ask the same question through `search` (unguarded)
and through `esql`. The two answers differ, and only one is right.

Clean up: `docker rm -f netclaw-es`

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Every tool call fails, server starts fine | `ES_URL` unset or unreachable *from inside the container* — `localhost` will not work |
| `missing field 'query_body'` | argument names are snake_case (`query_body`, `index_pattern`) |
| Aggregation rejected, *"Fielddata is disabled"* | aggregating a `text` field — use `field.keyword` |
| Query returns nothing | check field names with `get_mappings`, and `docs.count` with `list_indices`, before concluding the events did not occur |
| A total that looks suspiciously round | it is 10,000, and it is wrong. See step 5 |
