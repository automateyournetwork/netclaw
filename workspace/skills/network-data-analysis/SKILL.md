---
name: network-data-analysis
description: "Ad-hoc read-only SQL analysis over exported network data (Zeek logs, Suricata eve.json, generated reports) using DuckDB. Use when aggregating across a packet capture's sessions, correlating IDS alerts with connection metadata, or answering counting and grouping questions that a per-log view cannot"
version: 1.0.0
license: Apache-2.0
tags: [analysis, sql, duckdb, zeek, suricata, forensics, read-only]
---

# Network Data Analysis (read-only SQL)

## MCP Server

- **Server**: `analysis-mcp` (NetClaw-authored, spec 092)
- **Tools**: `analysis_status`, `analysis_datasets`, `analysis_query`
- **Engine**: DuckDB, in-memory, **sandboxed and locked**

## What this reads, and what it can never read

Loads files from an **allowlist of roots** — `~/.openclaw/nsm/runs` (Zeek/Suricata output
from `nsm-mcp`), the workspace output directory, and `~/.openclaw/analysis` for your own
exports.

**NetClaw's own stores are permanently unreachable**: `~/.openclaw/memory/`,
`~/.openclaw/rag/`, `~/.openclaw/n2n/` and `~/.openclaw/gait/`, plus `.ssh`, `.aws`, `.kube`
and `.env`. A generic SQL surface over those would be a backdoor, not an analysis tool.

That is not enforced by pattern matching. Datasets are materialised, then DuckDB's own
`enable_external_access=false` and `lock_configuration=true` close every filesystem and
network path **irreversibly** for the life of the process. Verified: `read_csv('/etc/passwd')`,
`glob('/home/**')`, `ATTACH` of the memory or RAG stores, `COPY … TO`, `INSTALL`/`LOAD`, and
re-enabling access all raise.

If you need a file analysed, put it under `~/.openclaw/analysis` — do not try to reach it in
SQL, because you cannot.

## Workflow: analyse a capture

1. **Produce the data first.** `nsm_analyze` (skill `nsm-session-pivot`) writes Zeek logs and
   Suricata `eve.json`. Without a run, this surface has nothing to read and says so.
2. `analysis_status` — is the sandbox locked, how many datasets loaded, what are the caps?
3. `analysis_datasets` — table names, row counts, columns. **Read the columns before writing
   SQL**; guessing column names wastes a round trip.
4. `analysis_query` — one read statement per call.

Zeek tables carry their **real column names** (`id_orig_h`, `id_resp_p`, `uid`), lifted from
the log's `#fields` header. Without that they would be `column0…columnN` and unusable.

## The pivot that makes this worth using

Every Zeek log shares `uid` with `conn.log`, so a join *is* the session pivot — and unlike
walking logs one at a time, it aggregates:

```sql
SELECT c.id_orig_h, c.id_resp_h, c.service, h.method, h.host, h.uri
FROM zeek_<run>_conn c
LEFT JOIN zeek_<run>_http h USING (uid)
ORDER BY c.ts
```

Counting questions a per-log view cannot answer:

```sql
-- top talkers by connection count
SELECT id_orig_h, count(*) AS conns FROM zeek_<run>_conn
GROUP BY 1 ORDER BY conns DESC LIMIT 20

-- which services appeared at all
SELECT service, count(*) FROM zeek_<run>_conn GROUP BY 1 ORDER BY 2 DESC

-- Suricata alert signatures by frequency
SELECT json_extract_string(alert, '$.signature') AS sig, count(*)
FROM suricata_<run>_eve WHERE event_type = 'alert' GROUP BY 1 ORDER BY 2 DESC
```

## Reading results honestly

- **`truncated: true` means you are looking at a page.** Never present a capped result as a
  total — run `COUNT(*)` for the real number. The tool reports this in `gaps`.
- **Zeek columns are all text.** Datasets load as varchar so a malformed field cannot abort
  the load; cast explicitly (`CAST(duration AS DOUBLE)`) and say that you did.
- **A row count reflects what was LOADED, not what existed.** Files above the size cap are
  skipped and listed in `notes`; a per-table row cap applies. Check `analysis_status` before
  claiming completeness.
- **`0 datasets` means no exports exist**, never "the network was quiet."
- **This inherits every caveat of its source.** A Zeek run made with checksum validation on
  may be missing whole protocol logs (see `nsm-session-pivot`) — and SQL over an incomplete
  log is confidently wrong. Check the posture of the run you are querying.

## Important Rules

- **Read-only.** `INSERT`/`UPDATE`/`DELETE`/`DROP`/`CREATE`/`ATTACH`/`COPY`/`INSTALL`/`SET`
  are refused, and independently impossible after lockdown.
- **One statement per call.** A stacked second statement is refused.
- **Queries time out** (default 30s) and are interrupted, not left running.
- **Record in GAIT** — log the query and the dataset it ran against, not just the answer.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `nsm-session-pivot` | Produces the Zeek logs this queries; use it for single-session detail |
| `nsm-ids-triage` | Produces `eve.json`; use SQL here to aggregate alerts across a capture |
| `packet-analysis` | Drop to individual packet decode once SQL narrows the field |
| `document-generation` | Turn a query result into a report table |
| `gait-session-tracking` | Record all analysis runs |

## Environment Variables

- `ANALYSIS_QUERY_TIMEOUT` — per-query seconds (default 30)
- `ANALYSIS_MAX_RESULT_ROWS` — result cap (default 500)
- `ANALYSIS_EXTRA_ROOTS` — extra allowlisted roots, `os.pathsep`-separated
- `ANALYSIS_MAX_FILE_BYTES` / `ANALYSIS_MAX_ROWS` — load caps
