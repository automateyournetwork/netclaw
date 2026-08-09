# Tasks: HUD three.js Modernization

**Feature**: `101-hud-threejs-modernization` | **Date**: 2026-08-06
**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/visual-contract.md](./contracts/visual-contract.md), [quickstart.md](./quickstart.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]** — parallelizable (different file, no incomplete dependency)
- **[US1..US5]** — user story this task serves

## Path Conventions

All paths relative to repo root. The frontend package is `ui/netclaw-visual/`.
`src/orgchart/` is **pure** and must never import three.js (feature 072's rule);
`src/orgchart-render/` owns all three.js contact.

## Tests

Test tasks **are** included — required by FR-036 and FR-046, not a default. Two specific reasons:

1. **The existing suite cannot see rendering.** No test file imports three.js, and the 7 modules
   that do have zero coverage (research R2). Every requirement about *what a state means* must be
   testable on the pure side or it is untested entirely.
2. **FR-046's separability rules are properties of design constants, not of one frame.** Feature
   072 proved this matters: its `treatments.test.js` caught a real collision where COLD landed
   within 10 luminance of FAULT. A screenshot would have passed.

## Ordering rationale — measurement, not priority

plan.md sequences by **measurement dependency**. US5 is P2 by operator value but runs early
because FR-047 gates the upgrade's own frame-time delta between two baselines, and US2/US3/US4 are
measured against the post-bump one. US3 precedes US2 so the per-state channel declaration exists
before a selection treatment must stay distinguishable against it.

---

## Phase 1: Setup

- [x] T001 Capture the **pre-bump** performance baseline at `three@0.170.0` per [quickstart.md](./quickstart.md) §0 — machine, browser + version, scene composition from `/api/n2n`, quality mode, median frame time over a sustained window. **This cannot be recreated once the bump lands** and FR-047/SC-005 are unverifiable without it. Record verbatim in the PR.
- [x] T002 [P] Confirm the current suite is green before any change (attribution baseline for FR-036): `cd ui/netclaw-visual && npm test >/dev/null 2>&1; echo $?` → `0`, so later failures are attributable to this work.
- [x] T003 [P] Record the live peer-state distribution as the fixture basis for US3, confirming data-model §1's finding that 5 of 7 peers hit `colorForStructural`'s healthy default: `curl -s localhost:3001/api/n2n | python3 -c "import json,sys;d=json.load(sys.stdin);[print(p['display_name'], p['state'], p['channel_state'], p['stale'], p['inventory_received_at']) for p in d['peers']]"`

**Checkpoint**: baseline captured and unreproducible-later data secured; suite green.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ Blocks US1, US3, US4.** These are the pure modules that hold every decision the render layer
must not make. All eight tasks are independent of one another → all `[P]`.

- [x] T004 [P] Create `ui/netclaw-visual/src/orgchart/freshness.js` implementing `FreshnessView` per [data-model.md](./data-model.md) §3: `receivedAt`, `ageSeconds`, `ageText`, `judgement` (`fresh`/`aging`/`stale`/`never`). `ageSeconds === null` (never received) MUST NOT render as `0` (just now) — that conflation is the FR-004 defect.
- [x] T005 [P] Create `ui/netclaw-visual/src/orgchart/freshness.test.js` (FR-004, FR-036): never-received yields `never` and `null` age, not `0`; `judgement` derives from age AND honors the API `stale` flag with the pessimistic reading winning; `ageText` renders minutes/hours/days in operator terms.
- [x] T006 [P] Create `ui/netclaw-visual/src/orgchart/liveness.js` implementing `PeerViewState` per data-model §2 — six states with top-down precedence, `LIVE` checked first. Must read `stale` and treat `channel_state: "unknown"` as its own case, which `colorForStructural` never does.
- [x] T007 [P] Create `ui/netclaw-visual/src/orgchart/liveness.test.js` driven by T003's real distribution: Nate → `LIVE`; Byrn/Nicholas/Hermes(`as65008`) → `STALE` and **not** the same state as Nate (the defect); AB/Carapace → `UNKNOWN`, distinct from both healthy and dead (FR-016, FR-017); Hermes(`as65007`) → `SEVERED`; precedence means a severed peer is never `LIVE` regardless of other fields (FR-017).
- [x] T008 [P] Create `ui/netclaw-visual/src/orgchart/feed-state.js` implementing `FeedState` per data-model §5 — freeze-and-flag: retain `lastGood`, never recompute liveness on a failed poll (FR-041), expose `degraded` + age of `lastGoodAt` (FR-042), clear on next success with no reload (FR-043).
- [x] T009 [P] Create `ui/netclaw-visual/src/orgchart/feed-state.test.js` (FR-041, FR-042, FR-043, FR-036): a throw, a non-2xx, and unparseable JSON are each failures that leave `lastGood` untouched; **a successful poll with zero peers is NOT a failure** but a renderable empty state; recovery clears `degraded` without acknowledgement. This is the test that stops the HUD fabricating an outage.
- [x] T010 [P] Create `ui/netclaw-visual/src/orgchart/peer-detail.js` (FR-002, FR-003) mapping a `/api/n2n` peer row to the panel view-model per [contracts/visual-contract.md](./contracts/visual-contract.md) §6, including `identity` (not just `label`) and `presentInFeed`.
- [x] T011 [P] Create `ui/netclaw-visual/src/orgchart/peer-detail.test.js`: every row either has a value or an explicit placeholder — **never `undefined`** (P2); both Hermes rows produce distinguishable view-models because `identity` is present; empty `in_flight_tasks` yields an explicit "none".

**Checkpoint**: every state/staleness/failure decision is implemented and unit-tested on the pure side, before any three.js file is touched.

---

## Phase 3: User Story 5 — Upgrade to 0.185.1 (Priority: P2) ⏱️ RUNS FIRST

**Goal**: the HUD runs on `three@0.185.1`, visually unchanged, with its own frame-time cost measured.

**Independent test**: bump, build, load the HUD, confirm zero console errors and an unchanged scene.

> Runs before the P1 stories for measurement reasons only (plan.md). It ships no visible value.

- [x] T012 [US5] Decide and record the verification route per FR-028 **before** bumping: either the isolated-probe technique (research R2 — copy `src/`, `index.html`, `canvas.html`, `vite.config.js` to a scratch dir with its own `node_modules`, mirroring the `<project>/../../specs/...` fixture path) or an explicit, confirmed `systemctl --user restart netclaw-hud.service`. `netclaw-hud.service` runs Vite from the working tree, so a dependency change is immediately visible to anyone watching the HUD. Then bump `three` to `0.185.1` in `ui/netclaw-visual/package.json`. **No source change is required** (FR-022, FR-023) — verified by isolated probe (research R2/R3), which found zero of the r171–r185 deprecated APIs in use.
- [x] T013 [US5] Build and test (FR-022, FR-023, SC-004, SC-007): `cd ui/netclaw-visual && npm run build >/dev/null 2>&1; echo $?` → `0`; `npm test >/dev/null 2>&1; echo $?` → `0`. Confirm bundle within ~10% of 753 kB (SC-007; expect ~799 kB).
- [x] T014 [US5] Capture the **post-bump** baseline at `0.185.1` (FR-044) and assert the delta from T001 is **≤10%** (FR-047). Same machine, browser, scene and quality mode, or the comparison is void.
- [x] T015 [US5] Verify visually via `chrome-devtools-mcp` (FR-024, FR-034, FR-035, SC-004): HUD loads with **zero console errors** and no three.js deprecation warnings; screenshot confirms bands, labels, links, camera framing and all seven post-processing passes intact (FR-025).
- [x] T016 [P] [US5] Record the renderer stack version (`three@0.185.1`, `WebGLRenderer`) in `ui/netclaw-visual/README.md` (FR-026, Principle XII). **Analysis found neither `README.md` nor `THIRD_PARTY_NOTICES.md` cites a three.js version today**, so this is an addition rather than an edit — do not "update" a string that is not there. `THIRD_PARTY_NOTICES.md` is deliberately untouched: it documents adapted third-party *source* (Jack Rabbit), not dependency versions.

**Checkpoint**: HUD on 0.185.1, visually identical, upgrade cost measured and gated. All later measurements now have a valid reference.

---

## Phase 4: User Story 1 — Inspect a federated peer (Priority: P1) 🎯 MVP

**Goal**: clicking any eN2N peer shows that peer's own federation detail.

**Independent test**: click each of the 7 peers; each shows its own detail. Needs no other story.

- [x] T017 [US1] Add the `federation-peer` branch to `setDetail` (FR-001, FR-002, FR-003) in `ui/netclaw-visual/src/main.js`, rendering from T010's view-model per visual-contract §6. This is the missing seventh branch — the click path at `main.js:2180` and `:2765` already passes this kind and it currently falls through to the default overview.
- [x] T018 [US1] Add the FR-006 guard (also SC-006) in `ui/netclaw-visual/src/main.js`: an unrecognised `setDetail` kind MUST NOT reach the default overview branch and MUST fail loudly in development. **The silent fallthrough is the defect** — it repaints with a different subject's content, which is why it read as "not clickable" while the mesh was pickable and hover-scaling.
- [x] T019 [US1] Verify both activation paths reach the new branch (FR-005): pointer (`main.js:2180`) and keyboard/a11y (`main.js:2765`). Both were broken.
- [x] T020 [US1] Implement the not-in-feed behaviour (FR-045) in `ui/netclaw-visual/src/main.js`: a selected peer that disappears retains its last known detail with an explicit banner, and the scene drops its selected treatment. Neither blank the panel nor let it read as current.
- [x] T021 [US1] Walk [quickstart.md](./quickstart.md) §3 against the running HUD: all 7 peers, both Hermes rows distinguishable, AB/Carapace show "never seen" not "0s ago", severed not presented as reachable, no row renders `undefined`, and the FR-045 case verified with spec 100's `forget_peer_endpoint`.

**Checkpoint**: SC-001 met — 7/7 peers inspectable, where today it is 0/7. This alone is a shippable MVP that fixes the reported defect.

---

## Phase 5: User Story 3 — Liveness and staleness readable (Priority: P1)

**Goal**: an operator can sort peers into live / stale / severed without clicking anything.

**Independent test**: one live, one stale, one severed peer in the feed all read differently in a screenshot.

> Precedes US2 so the declared channels exist before selection must stay distinct against them.

- [x] T022 [US3] Extend `ui/netclaw-visual/src/orgchart-render/nodes.js` (FR-012) with a peer-state treatment table per visual-contract §3, consuming T006's `PeerViewState`. Replaces `colorForStructural`'s two-branch logic, which never reads `stale` and lets `channel_state: "unknown"` reach the healthy default — the reason 5 of 7 peers look identical to Nate.
- [x] T023 [US3] In `ui/netclaw-visual/src/orgchart-render/nodes.js`, keep peers recognisable as peers (R4): state MUST modulate the existing `geometries.peer` octahedron silhouette, never substitute a member shape from `TREATMENTS`, so band membership still reads at a glance.
- [x] T024 [US3] Add label affixes as channel 4 (FR-014) per visual-contract §3 (`· stale 12d`, `· never seen`, `· unreachable`, `· severed`), extending — never replacing — the label from `resolveLabel`/`disambiguateLabels` (R5). This is the channel that survives greyscale, reduced-motion and colour-blindness simultaneously.
- [x] T025 [US3] Create `ui/netclaw-visual/src/orgchart-render/peer-treatments.test.js` asserting visual-contract R1/R2/R3 on the declared constants: every pair of the six peer states differs by **≥18** ITU-R BT.709 luminance (reusing `treatments.test.js`'s exact metric and threshold); `LIVE`/`IDLE` vs `STALE` checked explicitly; `UNKNOWN` is **not** in the alarm hue family.
- [x] T026 [US3] Wire freeze-and-flag into the poll path in `ui/netclaw-visual/src/main.js` using T008's `FeedState` (FR-041, FR-042, FR-043): a failed poll must not mutate any liveness, and the scene shows a stale-data indicator with the age of the last good poll.
- [x] T027 [US3] Verify liveness is **live**, not one-shot (FR-015): a peer's state change is reflected on the next successful poll with no reload. Test by flipping a real peer — retire an endpoint with spec 100's `n2n_forget_endpoint`, or stop and restart a member — and confirm the treatment changes within one poll interval. **Analysis found FR-015 had zero task coverage**; without this, US3 could ship as a static picture that is correct only at page load.
- [x] T028 [US3] Confirm members are untouched (FR-013): `HOT`/`WARM`/`COLD`/`FAULT` render exactly as before and `treatments.test.js` still passes unmodified.
- [x] T029 [US3] Walk [quickstart.md](./quickstart.md) §4 with screenshots covering **all six** peer states, not just live/stale/severed (SC-003 as widened by analysis): plus greyscale (FR-014), reduced-motion, and the zero-peers empty state. `UNKNOWN` needs explicit visual proof it is distinct from both healthy and dead (FR-016, FR-017) — it is the state five of seven live peers occupy. Then verify SC-010 by stopping `netclaw-mesh.service` with the HUD open — **no peer may change to a failure appearance**.

**Checkpoint**: SC-003 and SC-010 met. Byrn and Nicholas no longer masquerade as healthy.

---

## Phase 6: User Story 2 — Selection is unmistakable (Priority: P1)

**Goal**: the selected node is always identifiable, at any zoom, against a bloom-heavy scene.

**Independent test**: select nodes across bands; the treatment is visible in a screenshot without the panel disambiguating.

- [x] T030 [US2] Implement selection as **channel 5 only** in `ui/netclaw-visual/src/orgchart-render/nodes.js` per visual-contract §2 — an outline or rim outside the silhouette. It MUST NOT raise `emissiveIntensity`, or change colour, form or scale.
- [x] T031 [US2] Remove the old treatment (`emissiveIntensity = 1.8` + scale bump) from `ui/netclaw-visual/src/main.js`. It reuses **state** channels, so selecting a dim node brightens it toward the healthy treatment — the concrete FR-007 failure mode.
- [x] T032 [US2] In `ui/netclaw-visual/src/main.js`, enforce the single-selection invariant (FR-009) via `clearSelection()` and guarantee full restoration on deselect with no residue (FR-008) — the current `scale.setScalar(1)` hover-reset pattern is the precedent to follow.
- [x] T033 [US2] Respect `prefers-reduced-motion` (FR-010): the treatment is static, not animated.
- [x] T034 [US2] Verify against the **bloom-enabled** scene, not a bare one — additive glow can wash out an outline. Check both extremes of the camera's configured zoom range (FR-011).
- [x] T035 [US2] Walk [quickstart.md](./quickstart.md) §5, including the collision case plan.md names as the primary risk: select a `STALE` peer and a `COLD` member and confirm selection is legible on dim nodes **without** the node reading as healthy.

**Checkpoint**: SC-002 met, and selection is provably orthogonal to state.

---

## Phase 7: User Story 4 — Federation links show flow (Priority: P2)

**Goal**: live links visibly carry traffic; stale and dead links are visibly static.

**Independent test**: one live and one stale peer — the live link animates, the stale one does not.

> Last, because it is the only story with real perf risk and should be measured against a scene already carrying US2 and US3.

- [x] T036 [US4] Add flow animation to `ui/netclaw-visual/src/orgchart-render/links.js` (FR-018), gated on `PeerViewState === LIVE` per visual-contract §5. Only `LIVE` flows; `IDLE`, `STALE`, `UNKNOWN`, `UNREACHABLE`, `SEVERED` do not.
- [x] T037 [US4] Record the direction decision in code (FR-019): absent a real per-link direction signal in `/api/n2n`, flow renders Border-ward to represent inbound capability availability. Do not imply a direction the data does not support.
- [x] T038 [US4] Respect `prefers-reduced-motion` (FR-020): the live/not-live distinction must survive with motion suppressed, since flow is redundant with US3's channels.
- [x] T039 [US4] Measure median frame time against the **post-bump** T014 baseline and assert **≤110%** (FR-021, SC-005), same machine/browser/scene/quality mode.

**Checkpoint**: all five stories independently functional; SC-005 satisfied with all three numbers recorded.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T040 [P] Verify preservation constraints per [quickstart.md](./quickstart.md) §7: chat interface untouched (FR-037), right-hand info bar untouched (FR-037), no sibling moves on select/expand (FR-038), `git diff --stat -- ui/netclaw-visual/server.js` **empty** (FR-039), a11y tree and keyboard nav functional with `aria-expanded` in step (FR-040).
- [x] T041 [P] Run `python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo $?` → `0` (FR-027). CI runs the same command and fails the merge on non-zero. **Never read this exit code through a pipe** (CLAUDE.md).
- [x] T042 [P] Confirm `tests/n2n/` is unaffected: `/usr/bin/python3 -m pytest tests/n2n/ -q` stays green — this feature touches no Python.
- [x] T043 Confirm every requirement has evidence (SC-009): a build result, a screenshot, or a test — never inspection alone. Any requirement without evidence is not done.
- [ ] T044 Draft the Principle XVII milestone blog post as `docs/blog/2026-08-XX-hud-threejs-modernization.md`, following the existing `docs/blog/` convention. **Offer it — never publish unprompted** (Principle XIV).
- [x] T045 Verify the branch is still `101-hud-threejs-modernization` before committing — other agents switch branches in this shared checkout. Then commit and open the PR including all three frame-time numbers so SC-005 is evidenced, not claimed.

---

## Dependencies

### Phase dependencies

```
Phase 1 (setup) ──► Phase 2 (pure modules) ──┬──► Phase 4 (US1)  needs T010/T011
                                             ├──► Phase 5 (US3)  needs T004/T006/T008
                                             └──► Phase 7 (US4)  needs T006
        │
        └──► Phase 3 (US5, the bump) ──► valid baseline for Phases 5-7

Phase 5 (US3) ──► Phase 6 (US2)      channels declared before selection must contrast
Phase 6 (US2) ──► Phase 7 (US4)      perf measured on the fully-loaded scene
Phases 3-7 ──► Phase 8 (polish)
```

### Critical orderings

- **T001 blocks everything.** The pre-bump baseline cannot be recreated after T012.
- **T012 (bump) before T014, and T014 before T039.** US2/US3/US4 measure against the post-bump baseline.
- **T006 blocks T022, T036.** The render layer consumes `PeerViewState`; it must not re-derive it.
- **T022/T024 block T030.** Selection must be shown distinct from the declared state channels.
- **T008 blocks T026.** Freeze-and-flag logic before wiring it to the poll.
- **T017 blocks T018, T020, T021.**

### Story independence

| Story | Depends on | Independently shippable? |
|---|---|---|
US5 (bump) | Phase 1 only | Yes — ships nothing visible, but is complete and verifiable |
US1 (peer inspector) | Phase 2 (T010/T011) | **Yes — this is the MVP** |
US3 (liveness) | Phase 2 (T004/T006/T008) | Yes |
US2 (selection) | US3 (channel declaration) | Only after US3, to avoid channel collision |
US4 (link flow) | Phase 2 (T006), US5 (baseline) | Yes |

## Parallel opportunities

- **T004–T011** — all eight Phase 2 tasks are different files with no interdependency. The largest parallel block in the feature.
- **T002, T003** alongside T001.
- **T016** alongside any Phase 3 task (docs only).
- **T040, T041, T042** all parallel in Phase 8.
- **Phase 4 (US1) and Phase 5 (US3) can run in parallel** once Phase 2 is done — US1 touches `main.js`'s `setDetail`, US3 touches `nodes.js` treatments. Only their `main.js` edits (T020, T026) need coordinating.

## Implementation strategy

**MVP = Phase 1 + Phase 2 + Phase 4 (US1).** That fixes the reported defect — the one thing the
operator actually complained about — and delivers 7/7 peer inspection where today it is 0/7.
Everything after it is improvement rather than repair.

**Incremental delivery**: US5 → US1 → US3 → US2 → US4, which is the measurement order, not the
value order. If work stops after any story, the HUD is in a coherent state: the bump alone is
invisible-but-correct, US1 alone fixes the bug, US3 alone makes the scene honest.

**Do not reorder US3 and US2.** Selection and state both add channels to the same nodes on a scene
already running seven post-processing passes. Choosing a selection treatment before the state
channels are declared is how the two collide, and the collision is invisible until you select a
dim node (plan.md primary risk).
