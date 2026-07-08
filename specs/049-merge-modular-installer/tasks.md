# Tasks: Merge Modular TUI Installer with Full Component-Coverage Parity

**Input**: Design documents from `/specs/049-merge-modular-installer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/catalog-entry-format.md, quickstart.md

**Tests**: Not explicitly requested beyond `bash -n` syntax checks (matches PR #96's own stated test plan) and the coverage-check script itself, which functions as the acceptance test for User Story 1.

**Organization**: Work happens directly on `pr-96-review` (local branch tracking PR #96's `refs/pull/96/head`), not a fresh reimplementation. Tasks are grouped by user story per spec.md's priorities.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Get PR #96's branch conflict-free against current main before any new content is added

- [X] T001 On `pr-96-review`, merge current `main` into the branch; resolve the `scripts/install.sh` and `README.md` conflicts by taking PR #96's version of both wholesale (a clean file replacement, not a line-by-line merge — see research.md R1)
- [X] T002 [P] Run `bash -n` on `scripts/install.sh` and every file under `scripts/lib/` post-merge to confirm the baseline (before any new entries) is syntactically valid

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The coverage-check tool that both validates the backfill work (US1) and prevents this exact drift from recurring (FR-008)

**CRITICAL**: No user story work can be marked done until this phase's script exists and runs (even reporting known gaps) — it's the acceptance mechanism for US1

- [X] T003 Create `scripts/verify-catalog-coverage.py`: enumerate `config/openclaw.json`'s `mcpServers` keys, enumerate `scripts/lib/catalog.sh`'s catalog ids, apply the `GROUPED_COVERAGE` allow-list (per contracts/catalog-entry-format.md) for existing intentional groupings (`checkpoint` → 15 `chkp-*` servers, `aws` → its 6 servers, `gcp` → its 4, `aap` → its 4), report any registered server not reachable via a direct or grouped match as a gap, and exit non-zero if any gap is unexplained
- [X] T004 [P] Run `scripts/verify-catalog-coverage.py` against the post-merge, pre-backfill state and confirm it correctly reports the 9 known gaps from research.md R2 (proves the script itself works before it's used to prove the backfill worked)

**Checkpoint**: Coverage-check tool exists and correctly identifies the known gaps. Backfill work (US1) can now proceed and be verified.

---

## Phase 3: User Story 1 — No Regression: Every Installable Capability Survives the Merge (Priority: P1) 🎯 MVP

**Goal**: Close all 9 confirmed catalog gaps so the merged installer has zero regression versus current main.

**Independent Test**: `scripts/verify-catalog-coverage.py` exits 0 with no unexplained gaps.

### Implementation for User Story 1

- [X] T005 [P] [US1] Add `gns3` catalog entry to `scripts/lib/catalog.sh` (category: Labs & Simulation) and `component_install_gns3()` to `scripts/lib/install-steps.sh`, per contracts/catalog-entry-format.md
- [X] T006 [P] [US1] Add `devnet-search` catalog entry (category: ITSM & DevOps or Analysis & Diagrams, whichever existing category fits DevNet Content Search's remote-HTTP no-auth nature) and `component_install_devnet_search()`
- [X] T007 [P] [US1] Add `memory-mcp` catalog entry (category: Platform Services, alongside `mempalace`) and `component_install_memory_mcp()`, clearly distinguishing its description from `mempalace`'s
- [X] T008 [P] [US1] Add `ollama` catalog entry (category: Platform Services) and `component_install_ollama()`
- [X] T009 [P] [US1] Add `telemetry-receivers` catalog entry (category: Observability) covering SNMP trap, syslog, and IPFIX/NetFlow together, and `component_install_telemetry_receivers()` registering all three (`snmptrap-mcp`, `syslog-mcp`, `ipfix-mcp`)
- [X] T010 [P] [US1] Add `nautobot-golden-config` catalog entry (category: Source of Truth) and `component_install_nautobot_golden_config()`
- [X] T011 [P] [US1] Add `nautobot-routing` catalog entry (category: Source of Truth) and `component_install_nautobot_routing()`
- [X] T012 [P] [US1] Expand catalog coverage for base Twilio: either broaden the existing `twilio` entry's description/install function to also register `twilio-mcp` alongside `twilio-voice-mcp`, or add a distinct `twilio-core` entry — whichever keeps the description accurate; update `component_install_twilio()` accordingly
- [X] T013 [P] [US1] Add `threejs-viz` catalog entry (category: Analysis & Diagrams, alongside `blender`/`ue5`) and `component_install_threejs_viz()` covering `threejs-network-viz` plus the optional vendored `sketchfab-mcp` real-stencil mode
- [X] T014 [US1] Update `GROUPED_COVERAGE` in `scripts/verify-catalog-coverage.py` for any of T005-T013 that cover more than one registered server (at minimum `telemetry-receivers` and the Twilio entry from T012)
- [X] T015 [US1] Run `scripts/verify-catalog-coverage.py` and confirm zero unexplained gaps remain for every registered server that existed prior to spec 048 (chrome-devtools itself is still an expected, separate gap at this point — closed in Phase 4)

**Checkpoint**: Every pre-048 capability on main is installable through the new installer. This alone is mergeable as a non-regressive improvement over PR #96's original submission.

---

## Phase 4: User Story 2 — Chrome DevTools Is a First-Class Component (Priority: P2)

**Goal**: Add spec 048's chrome-devtools-mcp integration as a proper catalog entry + install function, replacing the deleted monolithic Step 52b.

**Independent Test**: Selecting the Chrome DevTools component through the new installer (TUI or `--components chrome-devtools`) results in both MCP registrations configured with a working, explicit browser-binary reference, no sudo required, no credential requested.

### Implementation for User Story 2

- [X] T016 [US2] Add `chrome-devtools` catalog entry to `scripts/lib/catalog.sh` (category: Analysis & Diagrams, per research.md R4 — one entry covering both registrations) per contracts/catalog-entry-format.md
- [X] T017 [US2] Write `component_install_chrome_devtools()` in `scripts/lib/install-steps.sh`, self-contained (per research.md R5 — inline, not delegating to `scripts/chrome-devtools-enable.sh`): find a system Chrome/Chromium binary or provision one via `npx @puppeteer/browsers install chrome@stable`, then register both `chrome-devtools-mcp` (`--headless=true`) and `chrome-devtools-mcp-visible` (`--headless=false`) with the resolved `--executablePath`
- [X] T018 [US2] Add `chrome-devtools` to the `recommended` profile in `scripts/lib/catalog.sh` (it now underpins visualization-QA workflows already represented in that profile)
- [X] T019 [US2] Update `GROUPED_COVERAGE` in `scripts/verify-catalog-coverage.py`: `"chrome-devtools": ["chrome-devtools-mcp", "chrome-devtools-mcp-visible"]`
- [X] T020 [US2] Update `mcp-servers/chrome-devtools-mcp/README.md`, `quickstart.md` (spec 048), and both `SKILL.md` files with a short note that the component is now also installable via `./scripts/install.sh --components chrome-devtools` (in addition to the standalone `scripts/chrome-devtools-enable.sh`, which remains supported per research.md R5)
- [X] T021 [US2] Run `scripts/verify-catalog-coverage.py` and confirm zero unexplained gaps remain for chrome-devtools-mcp and chrome-devtools-mcp-visible

**Checkpoint**: Chrome DevTools is fully represented in the new installer with no behavior regression from spec 048's validated design.

---

## Phase 5: User Story 3 — The Constitution Reflects Reality (Priority: P3)

**Goal**: Amend Constitution Principle XI so future contributors know the real artifact-coherence touchpoint for installer support.

**Independent Test**: A person unfamiliar with the installer's history reads the amended constitution and correctly identifies `scripts/lib/catalog.sh` and `scripts/lib/install-steps.sh` (not `scripts/install.sh` directly) as the files to touch.

### Implementation for User Story 3

- [X] T022 [US3] In `.specify/memory/constitution.md`, update Principle XI's body text and the Artifact Coherence Checklist line that currently reads `scripts/install.sh — installation steps for new dependencies` to instead describe adding a `CatalogEntry` to `scripts/lib/catalog.sh` and a `component_install_<id>()` function to `scripts/lib/install-steps.sh`, and note that `scripts/verify-catalog-coverage.py` is how compliance is verified
- [X] T023 [US3] Add a Sync Impact Report comment block at the top of `.specify/memory/constitution.md` (matching the existing 1.0.0→1.1.0 style) documenting this amendment, and bump the version per its MINOR-bump rule (clarifying/extending existing principle text, not redefining a principle)

**Checkpoint**: Constitution accurately describes the merged installer's real structure.

---

## Phase 6: Polish & Merge

**Purpose**: Final validation and landing the work under the contributor's own PR

- [X] T024 [P] Run `bash -n` on every modified/added file: `scripts/install.sh`, all of `scripts/lib/*.sh`, `scripts/chrome-devtools-enable.sh`, `scripts/setup.sh`
- [X] T025 [P] Run `./scripts/install.sh --list` and visually confirm all ~81 components appear, correctly grouped, with no shell errors
- [X] T026 Reconcile `README.md`'s installer section (PR #96's rewrite) with any current-main content it doesn't yet account for (e.g. mentions of newly-backfilled components in the Quick Start narrative, if warranted)
- [X] T027 Push the completed branch to the contributor's fork: `git push git@github.com:calcuttin/netclaw.git pr-96-review:feat/installer-tui-refactor` (confirmed viable — `maintainerCanModify: true`)
- [X] T028 Post a comment on PR #96 explaining what changed (conflict resolution + 9 coverage-gap backfills + chrome-devtools retrofit + constitution amendment) and crediting the contributor's original work, per the conversation with the operator
- [X] T029 Confirm via `gh pr view 96` that `mergeable` now reports `MERGEABLE`, not `CONFLICTING`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — must complete first (nothing else can be verified against a still-conflicting branch)
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (US1's acceptance test doesn't exist without it)
- **User Stories (Phases 3-5)**: All depend on Foundational
  - US1 (Phase 3): No dependencies on US2/US3 — MVP target
  - US2 (Phase 4): Independent of US1's specific entries, but conventionally done after US1 closes the bulk of the gap list
  - US3 (Phase 5): Fully independent of US1/US2 — could be done in parallel by a different contributor
- **Polish (Phase 6)**: Depends on all three user stories being complete (the push in T027 should carry the whole, complete result)

### Within Each User Story

- Each catalog-entry-plus-install-function pair (T005-T013, T016-T017) is a self-contained unit — implement, then move to the next
- Coverage-check re-runs (T015, T021) happen after their story's entries are all in place, not after each individual one

### Parallel Opportunities

- T005 through T013 (all nine US1 backfill entries) touch the same two files (`catalog.sh`, `install-steps.sh`) but are logically independent — implement sequentially within one working session to avoid edit conflicts on the same files, even though they're marked [P] for conceptual independence
- T022 and T023 (US3) can proceed in parallel with Phase 3/4 work, since the constitution file is untouched by either
- T024 and T025 (Phase 6) can run in parallel — different concerns, no shared state

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T015)
4. **STOP and VALIDATE**: `scripts/verify-catalog-coverage.py` reports zero gaps for everything that predates spec 048
5. This alone is already a strictly better, mergeable state than PR #96's original submission — it fixes the regression risk even before chrome-devtools or the constitution are touched

### Incremental Delivery

1. Setup + Foundational → coverage tool exists, ready to measure progress
2. Add US1 (9-gap backfill) → verify → no-regression baseline established
3. Add US2 (chrome-devtools retrofit) → verify → spec 048 fully represented in the new installer
4. Add US3 (constitution amendment) → future contributors have accurate guidance
5. Phase 6 (Polish + Push) → PR #96 becomes mergeable, contributor gets full credit

### Suggested MVP Scope

User Story 1 is the MVP — it's the one that turns "a great PR that would silently regress the installer" into "a great PR that's actually safe to merge." US2 and US3 are important but the project would not be worse off shipping US1 alone first if time were constrained.

---

## Notes

- [P] tasks = different files, or independent conceptual units within the same two files (see Parallel Opportunities caveat above)
- [Story] label maps task to specific user story for traceability
- This is a merge-and-extend effort on top of a community contribution, not new application code — no new runtime dependency is introduced beyond what PR #96 and spec 048 already established
- The coverage-check script (T003) is itself a durable project asset — it should keep working after this feature ships, catching the next contributor's version of this same drift
- Every new catalog entry and install function must match `contracts/catalog-entry-format.md` exactly, since the whole point of this exercise is that the merged installer reads as one coherent system, not "PR #96's style" plus "NetClaw's bolted-on style"

## Completion Record

All 29 tasks completed 2026-07-08. The actual `scripts/lib/catalog.sh` / `scripts/lib/install-steps.sh` / `scripts/verify-catalog-coverage.py` / constitution changes were implemented directly on a local copy of PR #96's branch (`refs/pull/96/head`) and pushed to `calcuttin:feat/installer-tui-refactor` to preserve contributor attribution — see PR #96 for that diff and its own commit history. PR #96 went from `mergeStateStatus: DIRTY` / `mergeable: CONFLICTING` to `CLEAN` / `MERGEABLE` as a direct result. An explanatory comment was posted on PR #96 crediting the original contribution. This branch's job was the spec/plan/tasks record of that work, not the implementation itself.

One unrelated, pre-existing bug was found and fixed along the way (separate commit on `main`, `dc5e411`): `.gitignore`'s `mcp-servers/*` rule had no exception for `atlassian-mcp/` or `chrome-devtools-mcp/`, so both directories' READMEs were silently never committed despite being referenced throughout the docs. Restored.
