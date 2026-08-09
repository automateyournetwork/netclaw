# Phase 0 Research — DuckDB analysis surface (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md`, the delivered server and its tests.

---

## R1 — Is R17 buildable yet?

**Decision**: Yes, but **only after 091**, exactly as the roadmap predicted.

Surveyed 2026-08-04: `*.parquet` anywhere = **0 files**, SuzieQ parquet = 0, DuckDB not installed,
and the ClickHouse half of R17's rationale gone with R10's deferral. The roadmap's own conclusion:

> R17 should follow whichever item first produces bulk exports — R13 is now the most likely
> candidate. Building the query layer first would ship a query engine with nothing to point at.

Spec 091 then produced Zeek TSV logs and Suricata `eve.json` per run. The query layer arrives
**after** its data.

---

## R2 — Which engine?

**Decision**: DuckDB only. **ClickHouse is out.**

ClickHouse's rationale arrived with ntopng (R10), which is deferred because ClickHouse flow storage
is Enterprise M+ only. There is nothing to point it at.

---

## R3 — How do you stop SQL reaching NetClaw's own stores?

**Decision**: Use DuckDB's own enforcement. **Do not** try to screen query text.

A general SQL engine is a filesystem client. Blocking `read_csv('/etc/passwd')`,
`ATTACH '…/rag.db'`, `COPY … TO`, `INSTALL httpfs` by pattern-matching is a losing game — SQL has
too many spellings and the one you miss is the one that matters.

Sequence:

```
1. materialise each allowlisted dataset as a TABLE
2. SET enable_external_access=false
3. SET lock_configuration=true
```

**Measured after step 3 — all eight escapes raise:**

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

Materialised tables stay fully queryable throughout.

---

## R4 — What that design forced

**A VIEW does not survive the lockdown.** Views are lazily evaluated, so a view over a CSV reopens
the file at query time and fails once the door is shut. **Found by trying it.**

Therefore datasets must be *materialised*, which bounds memory by the data loaded — hence a per-file
size cap (256 MB) and per-table row cap (2,000,000), both overridable and both reported by
`analysis_status`.

That trade is the price of enforcement that cannot be defeated by an unanticipated spelling.

---

## R5 — Allowlist or denylist?

**Decision**: Allowlist of roots, plus a denylist as a second mechanism.

R17 states its constraint as a denylist, but that is the wrong shape: new stores keep appearing (033
memory, 052 `federation.db`, 062 RAG) and a denylist **fails open** for whatever arrives next.

Allowlisted: NSM runs, workspace output, an operator scratch dir. Additionally denied so a
misconfigured root cannot re-admit them: `~/.openclaw/n2n/` (consent records, pinned keys),
`~/.openclaw/gait/` (immutable audit trail, Principle IV), `.ssh`, `.aws`, `.kube`, `.env`.

Symlinks are resolved with `realpath` **before** the root check, so a link inside a legal root
cannot point out of it.

---

## R6 — Usability findings that became requirements

- **Zeek logs must load with real column names** from the `#fields` header. Otherwise they are
  `column0…columnN` — technically queryable, practically useless, because nobody can guess that
  `column2` is `id.orig_h` (FR-005).
- **A capped result must be reported as `truncated`**, with a gap note saying it is a page and not a
  total (FR-006).
- **An empty file must be skipped**, not loaded as a rowless dataset — which would be
  indistinguishable from a dataset that genuinely has no rows (FR-007).
- **`0 datasets` must read as "no exports exist"**, never as "the network was quiet" (FR-008).

---

## R7 — Timeouts

**Decision**: A watchdog, because DuckDB has no statement timeout.

The watchdog calls `interrupt()`, and this was **verified to actually stop a runaway scan** rather
than being politely ignored (FR-003). One statement per call (FR-002), because a stacked second
statement could carry a form the first-statement check already refused.

---

## R8 — End-to-end proof, against real data

`nsm_analyze` on spec 091's committed pcap produced 5 Zeek logs plus `eve.json`; `analysis-mcp`
discovered and loaded **8 datasets** with header column names applied, and a cross-log join returned
correct rows:

```
ChKVSJ31gdXkrTiS5   10.0.0.5 → 10.0.0.1        dns    —    —            —
Cu5aNv4sjfsBUNI9O6  10.0.0.5 → 93.184.216.34   http   GET  example.com  /index.html
```

**That join is R13's session pivot expressed as SQL** — the composition R17 existed for.
