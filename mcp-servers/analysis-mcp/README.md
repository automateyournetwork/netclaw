# analysis-mcp — read-only SQL over exported network data

Roadmap **R17**, spec [092](../../specs/092-duckdb-analysis/spec.md). NetClaw-authored,
**read-only**, DuckDB in-memory.

| | |
|---|---|
| Tools | **3** — `analysis_status`, `analysis_datasets`, `analysis_query` |
| Reads | Zeek TSV logs and Suricata `eve.json` from `nsm-mcp`, workspace reports, `~/.openclaw/analysis` |
| Never reads | `~/.openclaw/{memory,rag,n2n,gait}/`, `.ssh`, `.aws`, `.kube`, `.env` |

## Containment is DuckDB's, not a regex's

R17 requires that a SQL surface not expose the memory or RAG stores. A general SQL engine is a
filesystem client, and blocking `read_csv('/etc/passwd')`, `ATTACH`, `COPY`, `INSTALL httpfs`
by inspecting query strings is a losing game. So:

```
1. materialise allowlisted datasets as TABLEs
2. SET enable_external_access=false
3. SET lock_configuration=true      -- cannot be reopened
```

After step 3, **measured**: `/etc/passwd`, `glob('/home/**')`, `ATTACH` of `rag.db` or the
memory store, `COPY … TO`, `INSTALL`/`LOAD`, HTTP reads, and re-enabling access **all raise**.
The statement screen in `sandbox.py` is defence in depth and better error messages.

**A VIEW does not survive this** — views are lazy and reopen the file. Datasets are
materialised, which is why a 256 MB per-file and 2M-row per-table cap exist.

## Zeek column names

Zeek logs load with their real names (`uid`, `id_orig_h`, `id_resp_p`) lifted from the
`#fields` header. Without that they are `column0…columnN` — queryable but useless.

Every Zeek log shares `uid` with `conn.log`, so a join is the session pivot, aggregated:

```sql
SELECT c.id_orig_h, c.id_resp_h, c.service, h.method, h.host, h.uri
FROM zeek_<run>_conn c LEFT JOIN zeek_<run>_http h USING (uid)
```

## Caveats it inherits

SQL over a Zeek run made with checksum validation on is SQL over **incomplete logs** (see
spec 091). Check the run's posture before trusting an aggregate. And a capped result is
reported as `truncated` — a page, never a total.

## Tests

`bash tests/analysis/run-tests.sh` — 32 assertions. Path-allowlist and statement-screen
assertions are pure stdlib; the DuckDB lockdown assertions skip without the package.
