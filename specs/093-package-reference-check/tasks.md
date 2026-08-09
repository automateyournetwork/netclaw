# Tasks — Package-reference verification (reconstruction)

**Branch**: `093-package-reference-check` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec, `FINDINGS.md`, `contracts/` and the
> delivered change. All items `[X]`, ordered by dependency rather than chronology.

---

## Phase 1 — Test the R22 premise before building it (BLOCKING)

- [X] **T001** Inventory existing diagram capability across the repo
- [X] **T002** Confirm `drawio-diagram` ships native `.drawio` with CLI export to PNG/SVG/PDF
- [X] **T003** Confirm `uml-diagram` covers **27+ types** via Kroki
- [X] **T004** Conclude Excalidraw adds an **aesthetic, not a capability** — close R22 as already
      satisfied rather than building motion

## Phase 2 — The defect the audit surfaced

- [X] **T005** Find `npx -y @anthropic-ai/microsoft-graph-mcp` in three skills
- [X] **T006** Confirm the package **404s** on npm
- [X] **T007** Quantify: **17 invocations, 14 distinct `graph_*` names**, none able to run
- [X] **T008** Explain why nothing caught it — an on-demand `npx` call in a skill is neither counted
      nor registered, so it falls between every existing surface
- [X] **T009** Check **every** `npx`/`uvx` reference in every skill — **16 packages, one missing**.
      State explicitly that this is narrow, not systemic

## Phase 3 — Evaluate the real replacement

- [X] **T010** Enumerate `@softeria/ms-365-mcp-server` (MIT, v0.136.0) live over stdio — it lists
      tools without credentials
- [X] **T011** Measure: **188 tools, ~225,355 tokens — 45× the ceiling**, the worst measured
      (previous record 5,716, spec 084)
- [X] **T012** Find a filter that fits: `--read-only --enabled-tools 'drive-item|folder-files'` →
      12 tools, ~4,599 tokens
- [X] **T013** Confirm **zero of 188 tools are named `graph_*`** — the 14 names were invented, not
      misrouted
- [X] **T014** Probe the Teams surface: filtering `chat|team|channel|upload-file` without
      `--read-only` yields 8 tools, of which `parse-teams-url` is the only Teams-related one

## Phase 4 — Resolve the three skills honestly

- [X] **T015** `msgraph-files` — rewire to read-only file tools with real names
- [X] **T016** `msgraph-visio` — rewire; omit `--read-only` deliberately because
      `upload-file-content` is required, and **CR-gate the write** per Principle III
- [X] **T017** `msgraph-teams` — **remove**. Not satisfiable at any filter setting
- [X] **T018** Record Teams as a **gap**, not a silent drop — Graph supports `chatMessage`, so the
      capability is unserved by this package rather than impossible

## Phase 5 — The permanent guard (seventh surface)

- [X] **T019** `scripts/check-package-references.py`, wired into reconcile
- [X] **T020** Offline by default against `contracts/verified-packages.json` (16 entries) — the
      reconcile gate has no network access by design (075 SC-013)
- [X] **T021** `--refresh` as a separate, network-using mode that rewrites the manifest — **a human
      runs it, CI never does**
- [X] **T022** **An unverified reference is a finding, not a pass** — unknown must not be acceptable,
      since that is exactly the state the 404 package was in
- [X] **T023** Reconciliation PASS with the seventh surface active

---

## Dependencies

```
T001–T004 gate everything  (if R22 had been unsatisfied, this would be a different feature)
T005 → T006 → T007 → T009  (scope the defect before generalising)
T010 → T011 → T012         (a 45x manifest must be filtered before it can be adopted)
T014 → T017                (removal requires proving the capability is absent, not just missing)
T019 → T020 → T022
```

## Deliberately not done

Building Excalidraw (aesthetic, not capability); adopting `@softeria/ms-365-mcp-server` beyond the
filtered file/Visio surface; serving Teams by another route — recorded as an open gap.
