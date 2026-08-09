# Tasks — Elasticsearch log search (R12)

**Branch**: `096-elastic-logs` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Ordering note.** Tasks T001–T012 were executed **before** this file existed — a breach of
> Principle XVI recorded in the plan's Complexity Tracking. They are listed in the order the work
> actually happened, not reordered to imply a discipline that was not followed. T013 onward were
> planned here first.

**Legend**: `[X]` done · `[ ]` outstanding · `[P]` parallelisable

---

## Phase 0 — Research (all complete, see research.md)

- [X] **T001** Scope R12 to Elastic only; record why Dynatrace/New Relic are out (R1)
- [X] **T002** Audit existing log backends; correct the "no log search at all" claim (R2)
- [X] **T003** Evaluate four candidate servers; choose Elastic's own (R3)
- [X] **T004** Establish whether the supported successor is reachable on a free licence — it is not,
      Agent Builder is Enterprise-tier (R4)
- [X] **T005** Decide adopt-vs-build on measured manifest cost (R5)

## Phase 1 — Measurement gate

- [X] **T006** Stand up Elasticsearch 9.2.0, confirm licence `basic`/`active`
- [X] **T007** Measure the manifest with `count_tokens`: **1,094 / 5,000** (R6)
      *Gate: over ceiling ⇒ stop and reconsider, as spec 095 did at 11,783*
- [X] **T008** Seed 25,000 realistic syslog documents (10,075 matching `severity: error`)
- [X] **T009** Exercise all five tools against real data
- [X] **T010** Hunt silent wrong answers — **found the 10,000-cap total** (R7)
- [X] **T011** Verify both mitigations return 10,075 (`track_total_hits`, `esql`)
- [X] **T012** Clear two suspected defects that did not survive checking (R8)

## Phase 2 — Integration artifacts

- [X] **T013** Register `elasticsearch-mcp` in `config/openclaw.json` — `command: docker`,
      digest-pinned, `--add-host=host.docker.internal:host-gateway` (R9)
- [X] **T014** `scripts/lib/catalog.sh` — catalog entry under Observability & Telemetry
- [X] **T015** `scripts/lib/catalog.sh` — add `elastic` to `PROFILE_OBSERVABILITY`
- [X] **T016** `scripts/lib/install-steps.sh` — `component_install_elastic()` with the digest pull,
      the `ES_URL`-inside-the-container warning, and the counting rule
- [X] **T017** `workspace/skills/elasticsearch-logs/SKILL.md` — the skill, carrying the counting
      invariant and the backend-boundary table
- [X] **T018** `.env.example` — five variable names, no values
- [ ] **T019** `scripts/verify-catalog-coverage.py` — alias `elasticsearch-mcp` → `elastic`
      *(server key does not reduce to the catalog id by stripping `-mcp`)*
- [ ] **T020** `TOOLS.md` — infrastructure reference entry
- [ ] **T021** [P] `README.md` — counts at lines 7, 242, 521, 675 (219→220 skills, 161→162 MCP)
- [ ] **T022** [P] `SOUL.md` — counts at lines 15, 669, plus a capability paragraph describing what
      NetClaw can now do and its routing boundary *(per ADDING-AN-MCP: the count alone does not tell
      the agent what it can do)*
- [ ] **T023** [P] HUD — `ui/netclaw-visual/server.js` needs **two** entries, a node-list entry and
      an annotation-map entry; one without the other renders nothing

## Phase 3 — Verification gates

- [ ] **T024** `python3 scripts/check-server-startup.py --only elasticsearch-mcp`
      *(timeout is success; only a fatal import error is a finding)*
- [ ] **T025** `python3 scripts/reconcile-mcp.py` exits **0** across all seven surfaces
- [ ] **T026** `python3 scripts/trace-skill.py elasticsearch-logs` resolves
- [ ] **T027** Confirm no credential reached the repo (direct unpiped grep)

## Phase 4 — Close-out

- [ ] **T028** `docs/COVERAGE-ROADMAP.md` — R12 → `DONE (Elastic only)` with the manifest number,
      the deprecation trade, and the counting trap; state that Dynatrace/New Relic remain open
- [ ] **T029** Commit and open PR
- [ ] **T030** Tear down the throwaway `netclaw-es` container and its 25,000 test documents

---

## Dependencies

```
T007 gates everything after it (over ceiling ⇒ abandon adoption)
T010 → T011 → T017   (the trap must be found and mitigated before the skill can state the rule)
T013 → T019 → T025   (registration must exist before the alias, alias before reconcile passes)
T014 → T019
T019, T020, T021, T022 → T025
T024, T025, T026, T027 → T029
```

`[P]` tasks T021, T022, T023 touch different files and may run together.

## Out of scope (not tasks)

Dynatrace, New Relic, Agent Builder, any write path, standing up a cluster for the operator, and
changes to the Splunk/Datadog/GCP Logging skills.
