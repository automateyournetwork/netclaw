# Implementation Plan: DuckDB analysis surface over exported network data (R17)

**Branch**: `092-duckdb-analysis` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)
**Unblocked by**: [091](../091-nsm-zeek-suricata/spec.md) — which produced the exports

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, the delivered server and tests, and the git
> history. No `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096
> drift.

## Summary

`analysis-mcp`: **3 tools**, read-only DuckDB over an allowlist of roots, giving SQL analysis of
exported network data.

Built **after** its data existed, in the order the roadmap asked for. R17 was surveyed the same week
and found premise-weakened — `*.parquet` anywhere = 0 files, DuckDB not installed, and the
ClickHouse half of its rationale gone with R10's deferral. Spec 091 then shipped Zeek TSV logs and
Suricata `eve.json` per analysis run. **Building the query layer first would have shipped a query
engine with nothing to point at.**

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `duckdb`
**Storage**: None of its own — reads exports from allowlisted roots; materialises them in-process
**Testing**: `bash tests/analysis/run-tests.sh` — **32 assertions** (25 passed / 4 skipped with
`duckdb` hidden, so it is useful in CI, which installs nothing)
**Target Platform**: Linux
**Project Type**: MCP integration — built
**Performance Goals**: Bounded memory — per-file cap 256 MB, per-table row cap 2,000,000, both
overridable and both reported by `analysis_status`
**Constraints**: **NetClaw's own memory, RAG, federation and audit stores must be unreachable** —
enforced structurally, not by inspecting query text
**Scale/Scope**: 3 tools

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **II. Read-Before-Write** | No writes | **PASS** — `COPY` refused and impossible after lockdown |
| **IV. Immutable Audit Trail** | GAIT must be unreachable | **PASS** — `~/.openclaw/gait/` denied beyond R17's letter |
| **IX. Security by Default** | Containment must not depend on a blocklist author's imagination | **PASS** — enforcement is DuckDB's own; see below |
| **XI. Artifact Coherence** | All touchpoints | **PASS** — counts 159→160 MCP, 218→219 skills |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## The design centre: containment that does not depend on a regex

A general SQL engine is a filesystem client — `read_csv('/etc/passwd')`, `ATTACH '…/rag.db'`,
`COPY … TO '/tmp/exfil'`, `INSTALL httpfs` then read over HTTP. **Blocking those by inspecting query
strings is a losing game**: SQL has too many spellings, and the one you miss is the one that matters.

So enforcement is DuckDB's own:

```
1. materialise each allowlisted dataset as a TABLE
2. SET enable_external_access=false     -- filesystem and network close
3. SET lock_configuration=true          -- and cannot be reopened
```

Eight escape attempts were measured **after** step 3; every one raises. The statement screen in
`sandbox.py` is therefore **defence in depth and a source of good error messages, not the boundary**.

## Project Structure

```text
mcp-servers/analysis-mcp/
├── loader.py      # allowlist of roots + realpath resolution + Zeek #fields header
└── sandbox.py     # statement screen (defence in depth), lockdown sequence
tests/analysis/run-tests.sh   # 32 assertions
```

**Structure Decision**: Allowlist of roots, **not** a denylist. R17 states its constraint as a
denylist, but that is the wrong *shape*: new stores keep appearing (033 memory, 052
`federation.db`, 062 RAG), and a denylist fails open for whatever arrives next. The allowlist
additionally denies known-sensitive paths, so a misconfigured root cannot quietly re-admit them —
two mechanisms, because the consequence of getting it wrong is a backdoor onto NetClaw's own memory.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a recurrence gate |
| **Materialising tables instead of views, with size and row caps** | **A VIEW does not survive the lockdown** — views are lazily evaluated, so a view over a CSV reopens the file at query time and fails once the door is shut. Found by trying it | Views would be cheaper in memory but incompatible with the enforcement mechanism. The caps are the price of containment that cannot be defeated by a spelling nobody anticipated |
| **Denying more than R17's letter** (`n2n/`, `gait/`, `.ssh`, `.aws`, `.kube`, `.env`) | Consent records, pinned keys and the immutable audit trail are as sensitive as memory and RAG | Following the spec's literal list would leave real backdoors open |
