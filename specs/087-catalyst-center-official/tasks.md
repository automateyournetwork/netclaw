# Tasks — Catalyst Center official MCP (reconstruction)

**Branch**: `087-catalyst-center-official` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge, from the spec, `VERIFICATION.md` and the delivered code.
> No `tasks.md` existed during the build. Every item below is marked `[X]` because it is a record of
> completed work, not a plan — the ordering reflects dependency, not the order things happened.

---

## Phase 1 — Establish the problem (BLOCKING)

- [X] **T001** Measure the installed community server: 7 tools, unbounded `fastmcp>=0.1.0`,
      untracked, unregistered
- [X] **T002** Measure the upstream default bundle: **515 tools / 64,420 tokens**, 12.9× ceiling
- [X] **T003** Confirm licence is Apache-2.0 (licence-identical to NetClaw — no vendoring question)
- [X] **T004** Locate a curation mechanism without patching upstream —
      `CATALYST_CENTER_BUNDLED_TOOLS_DIR` (`config.py:108`) + `tool_loader.load_tools(root)`

## Phase 2 — Decide the shape (BLOCKING)

- [X] **T005** Build and measure the spec's hand-curated set: ~15 tools / ~4,200 tokens
- [X] **T006** Measure its API coverage: **~3%** — abandon this approach
- [X] **T007** Design grouped dispatchers + `catc_find` + `catc_describe_operation`
- [X] **T008** Measure the delivered set: **10 tools / 1,821 tokens, all 514 read operations**
- [X] **T009** Decide catalogue-not-runtime, avoiding upstream's `fastmcp>=2.0.0`, port-7001 HTTP
      transport and container requirement

## Phase 3 — Read-only posture

- [X] **T010** Enumerate verbs across all 515 upstream tools: 513 GET, 2 mutating
- [X] **T011** Exclude the single POST (`getApplicationPolicy` — misleadingly named)
- [X] **T012** Assert 514 operations exposed, 0 non-GET

## Phase 4 — The attribution chokepoint (this is the safety work)

- [X] **T013** Stamp every response with **which appliance answered**
- [X] **T014** Stamp every response with `observed_at`
- [X] **T015** Distinguish `empty` from `unreachable` — dead endpoint returns "NOT AN EMPTY RESULT"
- [X] **T016** Distinguish `auth_failed` — "state is UNKNOWN, not empty"
- [X] **T017** Caveat empty results and zero counts as describing **the controller, not the network**

## Phase 5 — Retire the old coverage

- [X] **T018** Remove the community `catalyst-center-mcp`
- [X] **T019** Register `catc-mcp` in `config/openclaw.json`
- [X] **T020** Artifact coherence: catalog entry, install step, docs, counts

## Phase 6 — Honest verification (live, both appliances)

- [X] **T021** Empty vs populated appliance, same call and credentials —
      `outcome=ok data=4` vs `outcome=empty` + caveat, naming different hosts
- [X] **T022** `catc_find` returns real operations and states it does not contact the appliance
- [X] **T023** Dispatch returns real data — `api_getSites` → 25 sites
- [X] **T024** `catc_describe_operation` returns uri + method + params
- [X] **T025** Unknown operation refused helpfully, naming `catc_find`
- [X] **T026** Unreachable and auth-failed paths exercised against live endpoints

---

## Dependencies

```
T002 gates everything (515 tools ⇒ adoption as-is is impossible)
T005 → T006 → T007   (the curated approach had to be measured to be rejected)
T007 → T008 → T019
T013–T017 → T021     (attribution must exist before empty-vs-wrong-host can be shown)
T018 ↔ T019          (retire and register together, or callers are orphaned)
```

## Not done (deliberate)

Write operations, the upstream runtime, Assurance deep-dives beyond the dispatchers' reach, and any
attempt to reconcile controller state against live device state — that boundary belongs to pyATS.
