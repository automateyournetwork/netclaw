# Tasks — DuckDB analysis surface (reconstruction)

**Branch**: `092-duckdb-analysis` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec, the delivered server and its tests. All
> items `[X]`, ordered by dependency rather than chronology.

---

## Phase 1 — Confirm the premise before building (BLOCKING)

- [X] **T001** Re-survey R17: `*.parquet` = 0 files, SuzieQ parquet = 0, DuckDB not installed
- [X] **T002** Confirm ClickHouse's rationale died with R10's deferral — drop it from scope
- [X] **T003** Confirm 091 now produces bulk exports (Zeek TSV + `eve.json`) — the roadmap's stated
      unblock condition

## Phase 2 — Containment (this is the feature)

- [X] **T004** Reject query-text screening as the boundary — SQL has too many spellings
- [X] **T005** Implement the lockdown sequence: materialise tables → `enable_external_access=false`
      → `lock_configuration=true`
- [X] **T006** Measure all eight escapes **after** lockdown — every one raises (FR-004)
- [X] **T007** Confirm materialised tables remain queryable after lockdown
- [X] **T008** Keep the `sandbox.py` statement screen as **defence in depth and good error
      messages**, explicitly not the boundary (FR-001)
- [X] **T009** Discover that a **VIEW does not survive lockdown** — views are lazily evaluated and
      reopen the file at query time
- [X] **T010** Accept the consequence: materialise, and cap — 256 MB per file, 2,000,000 rows per
      table, both overridable and reported by `analysis_status`

## Phase 3 — Allowlist, not denylist

- [X] **T011** Allowlist roots: NSM runs, workspace output, operator scratch
- [X] **T012** Additionally deny `~/.openclaw/n2n/`, `~/.openclaw/gait/`, `.ssh`, `.aws`, `.kube`,
      `.env` — beyond R17's letter
- [X] **T013** Resolve symlinks with `realpath` **before** the root check
- [X] **T014** Assert the allowlist is **not vacuous** — an NSM run dir must NOT be denied

## Phase 4 — Correctness of answers

- [X] **T015** Load Zeek logs with real column names from the `#fields` header (FR-005)
- [X] **T016** Report a capped result as `truncated`, with a gap note saying it is a page not a
      total (FR-006)
- [X] **T017** Skip empty files rather than loading rowless datasets (FR-007)
- [X] **T018** `0 datasets` reads as "no exports exist", never "the network was quiet" (FR-008)
- [X] **T019** One statement per call (FR-002)
- [X] **T020** Watchdog `interrupt()` timeout — verified to actually stop a runaway scan (FR-003)

## Phase 5 — Tests and end-to-end

- [X] **T021** `tests/analysis/run-tests.sh` — **32 assertions, 0 failures** (25 passed / 4 skipped
      with `duckdb` hidden, so CI installs nothing)
- [X] **T022** Assert the loader emits `CREATE TABLE`, never a `VIEW` — the assertion that pins why
      the row cap exists
- [X] **T023** Assert a query *before* lockdown is refused, and loading *after* lockdown is refused
- [X] **T024** Assert all 11 refused statement forms, and that the `ATTACH` refusal **names the
      stores it protects**
- [X] **T025** End-to-end against real data: 8 datasets loaded from 091's pcap output; cross-log
      join returns correct rows — **R13's session pivot expressed as SQL**
- [X] **T026** Reconciliation PASS on all six surfaces; counts 159→160 MCP, 218→219 skills

---

## Dependencies

```
T003 gates everything   (a query engine with nothing to point at is not worth shipping)
T005 → T006 → T007      (escapes can only be measured against a locked connection)
T009 → T010             (the VIEW finding is what forces materialisation and the caps)
T011 → T012 → T013 → T014
T021–T025 → merge
```

## Deliberately not done

ClickHouse (nothing to point it at); writes of any kind, including materialising results to disk;
querying NetClaw's own stores — **not a limitation to lift later, it is the design**; live database
connections (Postgres/MySQL), which need `ATTACH` and network access that the lockdown removes by
design — a separate surface with its own threat model, not a flag on this one.
