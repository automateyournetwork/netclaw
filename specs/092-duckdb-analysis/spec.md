# Spec 092 — DuckDB analysis surface over exported network data (R17)

**Status**: implemented
**Branch**: `092-duckdb-analysis`
**Date**: 2026-08-04
**Unblocked by**: [091](../091-nsm-zeek-suricata/spec.md) (R13) — which produced the exports

## Why this could be built now, and not before

R17 was surveyed on 2026-08-04 and found **premise-weakened**: `*.parquet` anywhere = **0
files**, SuzieQ parquet = 0, DuckDB not installed, and the ClickHouse half of its rationale
gone with R10's deferral. The roadmap's own conclusion was explicit:

> **Sequencing conclusion: R17 should follow whichever item first produces bulk exports** —
> R13 (Zeek/Suricata logs) is now the most likely candidate. Building the query layer first
> would ship a query engine with nothing to point at.

Spec 091 shipped R13 and produces exactly that: Zeek TSV logs and Suricata `eve.json` per
analysis run. So this spec is the query layer arriving *after* its data, in the order the
roadmap asked for.

`analysis-mcp`: **3 tools**, read-only DuckDB over an allowlist of roots.

## The substance: containment that does not depend on my regex

R17 carries a hard constraint — a SQL surface **must not** expose `~/.openclaw/memory/` or
`~/.openclaw/rag/rag.db`. That is harder than it sounds, because a general SQL engine is a
filesystem client: `read_csv('/etc/passwd')`, `ATTACH '…/rag.db'`, `COPY … TO '/tmp/exfil'`,
`INSTALL httpfs` then read over HTTP. **Blocking those by inspecting query strings is a losing
game** — SQL has too many spellings and the one you miss is the one that matters.

So enforcement is DuckDB's own:

```
1. materialise each allowlisted dataset as a TABLE
2. SET enable_external_access=false     -- filesystem and network close
3. SET lock_configuration=true          -- and cannot be reopened
```

**Measured after step 3** — every one of these raises:

| Attempt | Result |
|---|---|
| `read_csv('/etc/passwd')` | `PermissionException` |
| `glob('/home/**')` | `PermissionException` |
| `ATTACH '~/.openclaw/rag/rag.db'` | `PermissionException` |
| `ATTACH` the memory store | `PermissionException` |
| `COPY (SELECT 1) TO '/tmp/exfil.csv'` | `PermissionException` |
| `SET enable_external_access=true` | `InvalidInputException` |
| `SET lock_configuration=false` | `InvalidInputException` |
| `INSTALL httpfs` / `LOAD httpfs` | `PermissionException` |
| `read_csv('https://…')` | `PermissionException` |

Materialised tables stay fully queryable throughout. The statement screen in `sandbox.py` is
therefore **defence in depth and a source of good error messages**, not the boundary.

### What that design forced, stated plainly

**A VIEW does not survive the lockdown.** Views are lazily evaluated, so a view over a CSV
reopens the file at query time and fails once the door is shut — found by trying it. Datasets
must be *materialised*, which bounds memory by the data loaded. Hence a per-file size cap
(256 MB) and a per-table row cap (2,000,000), both overridable and both reported by
`analysis_status`. That trade is the price of enforcement that cannot be defeated by a
spelling I did not anticipate.

### Allowlist, not denylist

R17 states its constraint as a denylist, but a denylist is the wrong *shape*: new stores keep
appearing (033 added memory, 052 `federation.db`, 062 RAG), and a denylist fails open for
whatever arrives next. So `loader.py` uses an **allowlist of roots** — NSM runs, workspace
output, and an operator scratch dir — *and* additionally denies the known-sensitive paths so a
misconfigured root cannot quietly re-admit them. Two mechanisms, because the consequence of
getting it wrong is a backdoor onto NetClaw's own memory.

Denied beyond R17's letter: `~/.openclaw/n2n/` (consent records, pinned keys) and
`~/.openclaw/gait/` (the immutable audit trail, Principle IV), plus `.ssh`, `.aws`, `.kube`,
`.env`. Symlinks are resolved with `realpath` before the root check, so a link inside a legal
root cannot point out of it.

## Requirements

- **FR-001** Read-only analyst access. Writes, `ATTACH`, `COPY`, `INSTALL`/`LOAD`, `SET` and
  `PRAGMA` are refused, and independently impossible after lockdown.
- **FR-002** One statement per call — a stacked second statement could carry a form the
  first-statement check already refused.
- **FR-003** Query timeout, enforced. DuckDB has no statement timeout, so a watchdog calls
  `interrupt()`; verified to actually stop a runaway scan rather than being ignored.
- **FR-004** NetClaw's memory, RAG, federation and audit stores MUST be unreachable, enforced
  structurally.
- **FR-005** Zeek logs MUST load with their **real column names** from the `#fields` header.
  Otherwise they are `column0…columnN` — technically queryable, practically useless, since
  nobody can guess that `column2` is `id.orig_h`.
- **FR-006** A capped result MUST be reported as `truncated`, with a gap note saying it is a
  page and not a total.
- **FR-007** An empty file MUST be skipped rather than loaded as a rowless dataset, which
  would be indistinguishable from a dataset that genuinely has no rows.
- **FR-008** `0 datasets` MUST read as "no exports exist", never as "the network was quiet".

## Verification

`bash tests/analysis/run-tests.sh` — **32 assertions, 0 failures** (25 passed / 4 skipped with
`duckdb` hidden, so it is useful in CI, which installs nothing per SC-013).

Coverage that matters:

- memory, RAG, federation, GAIT, `.ssh`, `.aws`, `.kube`, `.env` all denied; an NSM run dir is
  **not** denied (the allowlist must not be vacuous)
- **after lockdown DuckDB refuses all eight escapes** in one assertion
- a materialised table is still queryable after lockdown
- the loader emits `CREATE TABLE`, never a `VIEW` — the assertion that pins why the row cap exists
- a runaway query is interrupted in under 20s
- truncation is reported rather than hidden
- a query *before* lockdown is refused; loading *after* lockdown is refused
- all 11 refused statement forms, and the `ATTACH` refusal names the stores it protects

**End-to-end against real data**, not a fixture: `nsm_analyze` on spec 091's committed pcap
produced 5 Zeek logs plus `eve.json`; `analysis-mcp` discovered and loaded **8 datasets** with
Zeek header column names applied, and this cross-log join returned correct rows —

```sql
SELECT c.uid, c.id_orig_h, c.id_resp_h, c.service, h.method, h.host, h.uri
FROM zeek_<run>_conn c LEFT JOIN zeek_<run>_http h USING (uid) ORDER BY c.ts
```

```
ChKVSJ31gdXkrTiS5   10.0.0.5 → 10.0.0.1        dns    —    —            —
Cu5aNv4sjfsBUNI9O6  10.0.0.5 → 93.184.216.34   http   GET  example.com  /index.html
```

That join *is* R13's session pivot expressed as SQL, which is the composition R17 existed for.

Reconciliation: **PASS on all six surfaces.** Counts 159→160 MCP, 218→219 skills.

## Out of scope

- **ClickHouse.** Its rationale arrived with ntopng (R10), which is deferred because
  ClickHouse flow storage is Enterprise M+ only. Nothing to point it at.
- **Writes of any kind**, including materialising query results to disk. `COPY` is refused.
- **Querying NetClaw's own stores.** Not a limitation to lift later — it is the design.
- **Live database connections** (Postgres/MySQL). Those need `ATTACH` and network access, both
  of which the lockdown removes by design. A separate surface with its own threat model, not a
  flag on this one.
