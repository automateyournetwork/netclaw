# Tasks: HUD WebGPU Showcase + Interactive Layout

**Feature**: `102-hud-webgpu-interactive-layout` | **Date**: 2026-08-07
**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/layout-api.md](./contracts/layout-api.md), [quickstart.md](./quickstart.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]** — parallelizable (different file, no incomplete dependency)
- **[US1..US5]** — user story this task serves

## Path Conventions

All paths relative to repo root. Frontend package is `ui/netclaw-visual/`.
`src/orgchart/` is **pure** and must never import three.js (feature 072's rule);
`src/orgchart-render/` owns all three.js contact.

## Tests

Test tasks **are** included — FR-031 requires it, and two requirements are *only* provable this way:

1. **FR-039 determinism** — "the same topology produces the same arrangement every run" is a
   property of a pure function. Solve twice, assert deep equality. No screenshot can show it.
2. **FR-033 validation** — every rejection path (NaN, ∞, oversized, unknown preset, unknown key)
   must be exercised, and doing that through a running Express server is slower and less thorough
   than testing the pure validator both sides share.

Spec 101's evidence also stands as a warning: its 145 tests could not see a label collision, and
its render modules still have zero coverage. Everything that *can* be a tested decision is pushed
to the pure side here for exactly that reason.

## Ordering — layout before renderer, inverting the spec's story order

plan.md sequences by **reference availability**, not story number. US4/US5 rewrite the entire render
path; landing layout after that makes every layout bug ambiguous between the drag code and the new
renderer. Layout therefore lands on the known-good 101 renderer, and the showcase — the only part
that can be cut without stranding anything — goes last.

---

## Phase 1: Setup

- [x] T001 Capture the pre-102 baseline with spec 101's committed probe: `CHROME_BIN=~/.cache/chrome-devtools-mcp/browsers/chrome/*/chrome-linux64/chrome OUT_DIR=$PWD/evidence-102 LABEL=pre-102 node specs/101-hud-threejs-modernization/evidence/hud-probe.mjs`. Reuse 101's tool rather than writing a new one, so SC-005's comparison is apples to apples.
- [x] T002 [P] Confirm the suite is green before any change: `cd ui/netclaw-visual && node --test 'src/**/*.test.js' >/dev/null 2>&1; echo $?` → `0` (145 tests today), so later failures are attributable to this work.
- [x] T003 [P] Confirm the pre-102 screenshot matches spec 101's committed baseline in `specs/101-hud-threejs-modernization/evidence/` — this is the reference the renderer port will be judged against (FR-037), so establish now that it still holds.
- [x] T004 **Get operator sign-off on dropping GlitchPass** (FR-021, contracts §3). It has no node equivalent; the plan recommends dropping rather than reimplementing because it is decorative, encodes no state, and can read as a rendering fault on an operations display. This is a visible change nobody requested — do not absorb it silently, and do not start Phase 6 until answered.

**Checkpoint**: baseline captured, suite green, GlitchPass decided.

---

## Phase 2: Foundational — the pure layout core

**⚠️ Blocks US1, US2, US3.** Four modules and their tests, all independent → all `[P]`.
Nothing here imports three.js or touches the DOM.

- [x] T005 [P] Create `ui/netclaw-visual/src/orgchart/presets.js` — Ring and Grid geometry derived from the band/category data `computeLayout` already produces (FR-042). Must not introduce a second source of truth for grouping.
- [x] T006 [P] Create `ui/netclaw-visual/src/orgchart/presets.test.js` (FR-042, FR-038): both presets return a position per node; Ring is concentric about the Border; Grid ignores bands; neither invents membership.
- [x] T007 [P] Create `ui/netclaw-visual/src/orgchart/force-layout.js` — deterministic seeded solver per [data-model.md](./data-model.md) §6. Initial positions seeded from a hash of the node's stable identity; **no `Math.random()`, no clock**; fixed iteration count, not an energy threshold; returns a position map and stops (FR-039, FR-040, FR-041).
- [x] T008 [P] Create `ui/netclaw-visual/src/orgchart/force-layout.test.js` (FR-039, FR-040, FR-041): **solve twice on identical input → deep-equal** (this assertion *is* FR-039); pinned nodes end at their pinned positions; the function returns rather than scheduling work; no `Math.random`/`Date` reachable from the module.
- [x] T009 [P] Create `ui/netclaw-visual/src/orgchart/layout-store.js` — per-preset sparse position maps, per-preset pin sets, camera pose, dirty flag, per [data-model.md](./data-model.md) §2 (FR-014, FR-049, FR-050, FR-051, FR-053).
- [x] T010 [P] Create `ui/netclaw-visual/src/orgchart/layout-store.test.js`: a node moved in `freeform` is unmoved in `orgchart` (FR-049); switching preset and back preserves positions exactly (FR-014); maps stay **sparse** so absent means computed (FR-050); any change sets dirty and only a successful save clears it (FR-051, FR-053).
- [x] T011 [P] Create `ui/netclaw-visual/src/orgchart/layout-payload.js` — save/restore shape, validation and camera clamping per [data-model.md](./data-model.md) §4. **Shared by client and server** so one implementation defines the contract (FR-018, FR-033, FR-047).
- [x] T012 [P] Create `ui/netclaw-visual/src/orgchart/layout-payload.test.js`: rejects `NaN`, `Infinity`, coordinates beyond ±10000, >500 entries/preset, >256 KB, unknown preset names, and **unknown top-level keys** (rejected, not ignored — silent acceptance of junk is how a schema rots); clamps camera zoom to 072's `MIN_ZOOM`/`MAX_ZOOM` (FR-047); tolerates unknown and missing node ids (FR-016); **asserts the emitted payload contains no federation state** (SC-008).

**Checkpoint**: every layout decision is implemented and unit-tested before any renderer or pointer code exists.

---

## Phase 3: User Story 1 — Drag a node and have it stay put (Priority: P1) 🎯 MVP

**Goal**: drag a node; it stays put through selection, expansion, polls and enrollment.

**Independent test**: drag three nodes, then select, expand, wait a full poll, enroll a member — all three still exactly where placed.

- [x] T013 [US1] Create `ui/netclaw-visual/src/orgchart-render/drag.js` (FR-001, FR-004) — raycast on `pointerdown` against `pickableObjects()`; on hit set `controls.enabled = false` and `setPointerCapture`; on miss fall through to `OrbitControls` untouched (FR-043).
- [x] T014 [US1] Implement the FR-044 movement threshold (satisfying FR-008) in `drag.js`: below it the gesture resolves as a click (select, 101's existing path), at or above it as a drag. A node must never be both selected and repositioned by one gesture.
- [x] T015 [US1] **Restore camera control on every termination path** in `drag.js` — `pointerup`, `pointercancel`, `lostpointercapture`, and an exception thrown mid-move (FR-045). Wiring only `pointerup` leaves the camera permanently dead after any abnormal end, with no visible cause and no recovery but a reload. This is the worst failure available in this feature.
- [x] T016 [US1] Write dragged positions into the `layout-store` (T009), keyed to the active preset, and keep hover feedback working and unstuck across drag start/end (FR-046).
- [x] T017 [US1] In `ui/netclaw-visual/src/orgchart-render/index.js`, make node placement consult the store **before** falling back to `computeLayout` output — and verify the 30-second `updateOrgChart` repaint does not overwrite stored positions (FR-002). **This is the single most likely regression in the feature**; US1 acceptance scenario 2 exists for it.
- [x] T018 [US1] Ensure links follow moved nodes (FR-003 — position is presentation, topology is data; dragging must not alter band membership or edges), including the member elbow routing through category headers, in `ui/netclaw-visual/src/orgchart-render/links.js` (FR-005), and that 101's selection ring and label track current position (FR-006).
- [x] T019 [US1] Walk [quickstart.md](./quickstart.md) §2 (FR-007 — overlapping nodes must not snap, merge or reorder) including **all four** camera-restore termination paths, a full poll cycle, and a simulated member enrollment.

**Checkpoint**: SC-001 met. This alone delivers the operator's request and is shippable.

---

## Phase 4: User Story 2 — Choose a layout preset (Priority: P1)

**Goal**: five named arrangements, switchable without destroying anything.

**Independent test**: cycle every preset and back; each is distinct and readable, and the default matches 101's baseline.

- [x] T020 [US2] Add the preset dropdown (FR-009) to `ui/netclaw-visual/src/main.js` with exactly the five `PresetId` values — org chart, ring, grid, force, free-form (FR-038). Must not alter the chat interface or right-hand bar (FR-028).
- [x] T021 [US2] Wire preset switching to the store so each preset retains its own positions and pins, restored on return (FR-014, FR-049). Nothing is destroyed, so no confirm dialog and no undo stack.
- [x] T022 [US2] Make the org-chart preset restore computed positions (FR-010 — the default must reproduce today's computed layout exactly) for any node not manually placed **within that preset**, giving a non-destructive way back from any arranged state (FR-012, FR-050).
- [x] T023 [US2] Run the force solver **off the render loop**, once per selection, applying its result as positions (FR-040). It must not tick continuously — that would be system-initiated movement (FR-027) and a permanent frame cost.
- [x] T024 [US2] Verify only positions change across presets — band membership, health treatments, peer states and link topology identical (FR-011).
- [x] T025 [US2] **Screenshot every preset** and check for label collision at default zoom (FR-013, SC-007). Spec 101 shipped a collision that only a screenshot caught; Grid and Ring both change inter-node spacing wholesale, so the default alone is not sufficient evidence.

**Checkpoint**: SC-002 and SC-007 met; free-form is recoverable, which is what makes US1 safe.

---

## Phase 5: User Story 3 — Save and restore (Priority: P2)

**Goal**: keep an arrangement and its viewpoint; get it back later.

**Independent test**: save, reload, confirm positions and camera; then add and remove a member and confirm both are tolerated.

- [x] T026 [US3] Add `GET /api/layout` to `ui/netclaw-visual/server.js` per [contracts/layout-api.md](./contracts/layout-api.md) §1. **Absence returns `200 {empty:true}`, never 404** — first-run is normal, and forcing the client to distinguish 404-means-none from 404-means-broken is a needless trap. A corrupt file returns `200` with a `warning`, not `500` (FR-019).
- [x] T027 [US3] Add `PUT /api/layout` to `ui/netclaw-visual/server.js` per contracts §2: validate with the shared `layout-payload` module **before touching disk** (no partial writes), enforce per-route size/count bounds rather than relying on the global `express.json({limit:'4mb'})`, write to a module-constant path with no request-derived component, and write atomically via temp-file + rename (FR-032, FR-033, FR-034).
- [x] T028 [US3] Return specific errors — `"positions.ring: 812 entries exceeds 500"`, not `"invalid payload"` (contracts V6). The operator has to be able to act on it.
- [x] T029 [US3] Add the explicit save control to `ui/netclaw-visual/src/main.js` (FR-015). **No autosave** — nothing writes unless the operator asks.
- [x] T030 [US3] Add the on-screen unsaved indicator (FR-052) and the `beforeunload` warning that fires **only** when genuinely dirty (FR-051). A warning that cries wolf trains the operator to dismiss the one that matters; the on-screen indicator is the primary signal because browsers suppress unload dialogs on tab discard, crash and OS shutdown.
- [x] T031 [US3] On load, fetch and apply the saved layout (restore only — discarding a saved layout is handled separately, FR-017): clamp the camera to 072's constraints (FR-047), fall back to framing the chart if the restored view would show nothing (FR-048), place unknown ids nowhere and missing ids at computed positions (FR-016).
- [x] T032 [US3] Add a **discard saved layout** control (FR-017) — `DELETE`/reset via the same route, returning the HUD to computed positions and clearing the store. **Analysis of this task list found FR-017 had no task at all**: without it a bad saved layout is unremovable from the UI, and "reset to computed" only covers the current session.
- [x] T033 [US3] Ensure a failed save retains the in-memory arrangement **and** leaves it marked unsaved (FR-035, FR-053) — a failed write must never present as a successful one.
- [x] T034 [US3] Walk [quickstart.md](./quickstart.md) §4–§5, including the four rejection payloads, the corrupt-file path, and `grep -ciE 'channel_state|inventory|pinned_key|token|secret|endpoint_host'` over the written file returning `0` (SC-008).

**Checkpoint**: SC-003 and SC-008 met. `server.js` diff contains only the two routes.

---

## Phase 6: User Story 4 — Renderer migration (Priority: P2) ⚠️ NO A/B REFERENCE

**Goal**: one renderer path, on `WebGPURenderer`, visually indistinguishable from 101.

**Independent test**: screenshot against 101's committed baseline; no `EffectComposer` or `ShaderMaterial` remains.

> **Blocked on T004** (GlitchPass decision). The largest risk in the feature: FR-036 forbids keeping WebGL, so there is nothing live to A/B against — 101's committed baselines are the only reference (FR-037).

- [ ] T035 [US4] Create `ui/netclaw-visual/src/orgchart-render/renderer.js` — `WebGPURenderer` from `three/webgpu`, replacing the `WebGLRenderer` in `main.js`. Let it choose its own backend; do **not** branch on renderer type (research R7).
- [ ] T036 [US4] Port the 4 `ShaderMaterial` instances in `ui/netclaw-visual/src/orgchart-render/nodes.js` to node materials with TSL from `three/tsl` (FR-020). Verify against 101's baseline screenshots, not against a running WebGL build — there is none.
- [ ] T037 [US4] Rebuild the post-processing chain in `renderer.js` using `PostProcessing` plus `BloomNode`, `RGBShiftNode`, `SMAANode`, `AfterImageNode`, `FilmNode` from `three/examples/jsm/tsl/display/` (research R1 — 5 of 7 are direct ports; `RenderPass`/`OutputPass` are absorbed).
- [ ] T038 [US4] Hand-write the vignette as a TSL node — radial darkening from UV distance. It has no shipped equivalent (research R1) and is the one effect that must be re-authored rather than re-wired.
- [ ] T039 [US4] Apply the T004 GlitchPass decision: drop it, or hand-write it as a TSL node. Either way record which, so FR-021's "no silent loss" holds.
- [ ] T040 [US4] Delete every remaining `EffectComposer` import and GLSL `ShaderMaterial` (FR-036). Verify with `grep -rE "EffectComposer|ShaderMaterial" src/` returning **nothing** — a dormant second path would rot unnoticed because nothing exercises it.
- [ ] T041 [US4] Confirm 101's `peer-treatments.test.js` still passes **unmodified** (FR-023, SC-006) — the six-state peer encoding is data, not rendering, and must survive the port untouched.
- [ ] T042 [US4] Re-measure frame time against T001 and assert ≤110% (SC-005); update the renderer table in `ui/netclaw-visual/README.md`, which 101 wrote and which becomes wrong the moment `WebGPURenderer` lands (FR-030 adjacent, Principle XII).

**Checkpoint**: SC-006 met, one renderer path, bundle and frame time recorded.

---

## Phase 7: User Story 5 — The showcase (Priority: P3)

**Goal**: `ClusteredLighting` and compute-particle flow, as progressive enhancements.

**Independent test**: on WebGPU both are present; on the WebGL 2 backend both are absent and nothing is broken.

> The only phase that can be cut without stranding anything. That is why it is last.

- [ ] T043 [US5] Confirm empirically how to detect which backend `WebGPURenderer` chose on 0.185.1 (`renderer.backend.isWebGPUBackend` or equivalent) — recorded as an open item in research R7 rather than guessed. Everything below gates on it.
- [ ] T044 [US5] Add `ClusteredLighting` from `three/addons/lighting/ClusteredLighting.js` in `renderer.js`, assigned via `renderer.lighting` (research R2, one line). Lower `maxLights` from the 1024 default — this scene needs ~10.
- [ ] T045 [US5] Add one point light per **live** claw, gated on the WebGPU backend (FR-024). Must encode real state, never decoration (FR-025).
- [ ] T046 [US5] Replace 101's three-dot link-flow approximation with compute-shader particles on live links only, gated on the WebGPU backend (FR-025).
- [ ] T047 [US5] Verify degradation (FR-022): force the WebGL 2 backend → showcase features **absent, not broken**; no empty overlays, no error state (FR-024, SC-004). Simulate a device-lost event → scene degrades rather than blanking (FR-026).

**Checkpoint**: SC-004 met; the HUD is correct with and without the showcase.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T048 [P] Verify preservation per [quickstart.md](./quickstart.md) §8: chat interface and right-hand bar untouched (FR-028); a11y tree and keyboard navigation still functional with arbitrary positions (FR-029); `git diff --stat -- ui/netclaw-visual/server.js` shows **only** the two layout routes (FR-032).
- [ ] T049 [P] Run `python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo $?` → `0` (FR-030). CI runs the same command. Never read this exit code through a pipe.
- [ ] T050 [P] Confirm `tests/n2n/` is unaffected: `/usr/bin/python3 -m pytest tests/n2n/ -q` stays green — this feature touches no Python.
- [ ] T051 Confirm every requirement has evidence (SC-009): a test, a build result, or a screenshot. Any requirement without evidence is not done — spec 101 established this by failing FR-024 on a pre-existing favicon 404 rather than claiming it.
- [ ] T052 Draft the Principle XVII milestone blog post as `docs/blog/2026-08-XX-hud-webgpu-interactive-layout.md`. **Offer it — never publish unprompted** (Principle XIV).
- [ ] T053 Verify the branch is still `102-hud-webgpu-interactive-layout` before committing — other agents switch branches in this shared checkout. Then commit and open the PR with the T001 and T042 frame-time numbers, and a screenshot per preset.

---

## Dependencies

```
Phase 1 (setup) ──► Phase 2 (pure core) ──┬──► Phase 3 (US1 drag)
                                          ├──► Phase 4 (US2 presets)   needs T005/T007/T009
                                          └──► Phase 5 (US3 save)      needs T011
        │
        └── T004 (GlitchPass sign-off) ──► Phase 6 (US4 renderer) ──► Phase 7 (US5 showcase)

Phase 3 ──► Phase 4   (presets make free-form recoverable; drag must exist to be remembered)
Phases 3-5 ──► Phase 6  (layout proven on the known-good renderer BEFORE the port)
Phases 3-7 ──► Phase 8
```

### Critical orderings

- **T001 blocks everything measurable.** SC-005 has no reference without it.
- **T004 blocks Phase 6.** Do not start the port with an undecided visible change in it.
- **T009 blocks T016, T021, T031** — the store is where every position lives.
- **T011 blocks T027** — server and client share one validator.
- **T017 is the highest-risk single task**: the poll repaint is where dragged positions silently snap back.
- **Phases 3–5 before Phase 6** — this is the whole sequencing argument. Layout must be known-good before the renderer changes underneath it.

## Parallel opportunities

- **T005–T012** — eight pure tasks, four modules and four test files, no interdependencies. Largest parallel block.
- **T002, T003** alongside T001.
- **T026–T028** (server) parallel with **T029–T030** (client UI) once T011 exists.
- **T048, T049, T050** all parallel in Phase 8.
- Phase 3 (US1) and Phase 5 (US3) can overlap once Phase 2 is done — different files, coordinated only where both touch `main.js`.

## Independent test criteria per story

| Story | Independently verifiable by |
|---|---|
US1 (P1) | Drag 3 nodes; survive selection, expansion, a full poll, an enrollment |
US2 (P1) | Cycle all five presets and back; default matches 101's baseline; screenshot each |
US3 (P2) | Save, reload, add a member, remove a member; four rejection payloads all 400 |
US4 (P2) | Screenshot vs 101 baseline; `grep` finds no `EffectComposer`/`ShaderMaterial` |
US5 (P3) | WebGPU: present. WebGL 2 backend: absent, nothing broken |

## Implementation strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1).** That delivers the drag-and-reposition the operator
asked for, on a renderer already known to work. Everything after is enhancement.

**Incremental delivery**: US1 → US2 → US3 → US4 → US5. Each is a coherent stopping point. Stopping
after US3 leaves a fully working arrangeable HUD with persistence and no renderer risk taken at all
— which is a legitimate place to stop if the showcase turns out not to be worth it.

**Do not start Phase 6 before Phases 3–5 are verified.** The renderer port has no A/B reference by
construction (FR-036), so the only way to keep its failures attributable is to have everything else
already proven on the known-good renderer.
