# Tasks: HUD 2.0 — Top-Down Trust Org Chart

**Feature**: `072-hud-2-org-chart` | **Date**: 2026-07-27
**Input**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/layout-contract.md](./contracts/layout-contract.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]** — parallelizable (different file, no incomplete dependency)
- **[US1/US2/US3]** — user story this task serves

## Path Conventions

All paths relative to repo root. Frontend package is `ui/netclaw-visual/`.

## Tests

Test tasks **are** included. Not a default — research R1 makes the pure/render
split an architectural requirement precisely so the spec's numeric claims are
testable, and `contracts/layout-contract.md` names required tests per module.
Tests are written **with** each pure module, not after.

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Add `"test": "node --test src/"` to `scripts` in `ui/netclaw-visual/package.json` (no new dependency — research R2)
- [x] T002 [P] Create directory `ui/netclaw-visual/src/orgchart/` for pure logic (must never import three.js)
- [x] T003 [P] Create directory `ui/netclaw-visual/src/orgchart-render/` for three.js rendering
- [x] T004 Add a **client-side** fixture loader in `ui/netclaw-visual/src/main.js`: `?fixture=<name>` fetches `specs/072-hud-2-org-chart/fixtures/<name>.json` instead of `/api/n2n`

> **T004 note — resolves a conflict between plan.md and research.md.** research R4
> said "the dev server gains a way to serve a fixture", but plan.md marks
> `server.js` UNCHANGED under FR-019. Loading fixtures client-side satisfies both:
> no server change, no new endpoint, no widened API surface.

**Checkpoint**: `npm test` runs (vacuously) and the fixture loader is reachable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ Blocks every user story.** These are the pure modules from
`contracts/layout-contract.md`. Each imports nothing from three.js; each ships
with its tests. All five are independent of one another → all `[P]`.

- [x] T005 [P] Implement `dedupePeers()` and `resolveLabel()` in `ui/netclaw-visual/src/orgchart/normalize.js` per the contract (FR-014, FR-015)
- [x] T006 [P] Write `ui/netclaw-visual/src/orgchart/normalize.test.js`: real duplicated-`Hermes` payload collapses to one peer in `severed`; both edge nodes with `display_name: null` resolve to non-empty labels
- [x] T007 [P] Implement `classifyHealth(member, nowEpochS)` and `WARM_THRESHOLD_S = 900` in `ui/netclaw-visual/src/orgchart/health.js`, precedence HOT → FAULT → WARM → COLD (FR-008, FR-008a)
- [x] T008 [P] Write `ui/netclaw-visual/src/orgchart/health.test.js`: all four states; exact 900 s boundary; `active` but `!live`; `unreachable` with fresh heartbeat still FAULT; **null heartbeat ⇒ COLD not FAULT** (highest-value assertion — conflating COLD and FAULT is the failure this design prevents)
- [x] T009 [P] Implement `categorizeMembers(members, integrationCatalog)` in `ui/netclaw-visual/src/orgchart/categorize.js`, catalog as an argument never an import (FR-006, FR-006a)
- [x] T010 [P] Write `ui/netclaw-visual/src/orgchart/categorize.test.js`: `live-29.json` yields 25 categorised; empty catalog ⇒ all `Uncategorised`; zero-skill member; **an alternate synthetic catalog produces a different correct chart** (proves Constitution VI vendor neutrality)
- [x] T011 [P] Implement `orderCategories()` in `ui/netclaw-visual/src/orgchart/ordering.js` — heat desc, size desc, name; `Uncategorised` always last (FR-006b)
- [x] T012 [P] Write `ui/netclaw-visual/src/orgchart/ordering.test.js`: hot before cold; equal heat falls to size; equal both falls to name; `Uncategorised` last even when it holds a HOT member (true of `ipfabric` in live data)
- [x] T013 Implement `computeLayout()` and `appendMember()` in `ui/netclaw-visual/src/orgchart/layout.js` — three bands + edge lane, category columns with wrap, positions assigned once (R6, FR-034)
- [x] T014 Write `ui/netclaw-visual/src/orgchart/layout.test.js` against all five fixtures: no two nodes share a position; `appendMember` leaves every prior coordinate byte-identical; edge nodes never get a member-column position; bands exist at zero members

**Checkpoint**: `npm test` green. Every falsifiable rule in the spec is now
covered without a browser or GPU.

---

## Phase 3: User Story 1 — Read the trust topology at a glance (P1) 🎯 MVP

**Goal**: First frame answers who is external, who is internal, who is alive, and where the boundary is — without interacting.

**Independent test**: Load with `?fixture=live-29`. Without input, confirm the three bands, the drawn trust boundary, and that HOT members dominate.

- [x] T015 [US1] Implement orthographic camera with `enableRotate = false`, pan/zoom retained, zoom clamped, in `ui/netclaw-visual/src/orgchart-render/camera.js` (FR-012, FR-013, R7)
- [x] T016 [P] [US1] Render the three bands and the **explicitly drawn** trust boundary in `ui/netclaw-visual/src/orgchart-render/bands.js` (FR-001, FR-002)
- [x] T017 [P] [US1] Implement instanced node geometry with four health treatments in `ui/netclaw-visual/src/orgchart-render/nodes.js` — differing in form, colour temperature and motion, never opacity alone (FR-009a, FR-029a)
- [x] T018 [US1] Make FAULT the most salient state after HOT in `ui/netclaw-visual/src/orgchart-render/nodes.js` (FR-009b)
- [x] T019 [P] [US1] Implement the six link styles in `ui/netclaw-visual/src/orgchart-render/links.js`, reusing existing ribbon/tube helpers (FR-010, FR-028)
- [x] T020 [US1] Wire the org chart into `ui/netclaw-visual/src/main.js`: consume `orgchart/` output, place Border on the centre line, peers north, members south (FR-003, FR-004, FR-005)
- [x] T021 [US1] Add the health-state legend to `ui/netclaw-visual/index.html` (FR-009c)
- [x] T022 [US1] Render empty bands with per-band CTAs and keep loading distinct from empty in `ui/netclaw-visual/src/orgchart-render/bands.js`; remove the `role !== 'border'` early return (FR-033, FR-033a, FR-033b, FR-033d)
- [x] T023 [US1] Verify all fixtures in `specs/072-hud-2-org-chart/fixtures/` render via `?fixture=` — no overlap, no blank labels, bands always present (SC-004, SC-012)

**Checkpoint**: MVP. The org chart renders and is readable. Orbit code still
present but unused — deliberately, so the branch is never in a state with
neither layout working.

---

## Phase 4: User Story 2 — Distinguish mobile edges from member claws (P2)

**Goal**: Enrolled phones are instantly identifiable and never mixed into the member chart.

**Independent test**: With `live-29.json` (2 edge nodes, `display_name: null`), confirm both render in their own lane with non-blank labels.

- [x] T024 [US2] Render the edge lane flanking the Border, inside the boundary and outside the member chart, in `ui/netclaw-visual/src/orgchart-render/bands.js` (FR-007)
- [x] T025 [US2] Implement the asymmetric Border→device push link, visually distinct from a member delegation link, in `ui/netclaw-visual/src/orgchart-render/links.js` (FR-011)
- [x] T026 [US2] Surface each edge node's last-seen age on the node in `ui/netclaw-visual/src/orgchart-render/nodes.js`, without opening the detail panel (US2 AC2)
- [x] T027 [US2] Add an edge-lane overflow case to `ui/netclaw-visual/src/orgchart/layout.test.js` — more edges than slots must wrap, never overlap as HUD 1.0's three-slot stacking did (spec Edge Cases)

**Checkpoint**: Phones are unmistakable and the known overflow bug is not carried forward.

---

## Phase 5: User Story 3 — Drill in without losing the map (P2)

**Goal**: Inspect and expand any node while the chart stays put.

**Independent test**: Click a peer, a member and an edge; panel updates exactly as on `main`, camera never moves, layout never reflows.

- [x] T028 [US3] Wire picking so click/tap invokes the existing `setDetail(kind, payload, related)` unchanged in `ui/netclaw-visual/src/main.js` (FR-017, FR-020a, US3 AC1)
- [x] T029 [US3] Implement the always-visible expand affordance (chevron/`+`), separate from the click that selects, in `ui/netclaw-visual/src/orgchart-render/expansion.js` (FR-020, FR-020a, FR-020b)
- [x] T030 [US3] Render an expanded member's tools from `member.skills[]` in `ui/netclaw-visual/src/orgchart-render/expansion.js`, with no new API call (FR-021, FR-030a, SC-008)
- [x] T031 [US3] Guarantee expansion never reflows siblings in `ui/netclaw-visual/src/orgchart-render/expansion.js` — reserve or overlay space, never re-pack (FR-022)
- [x] T032 [P] [US3] Support simultaneous expansion of multiple members in `ui/netclaw-visual/src/orgchart-render/expansion.js` (FR-023)
- [x] T033 [P] [US3] Show tool count on collapsed nodes in `ui/netclaw-visual/src/orgchart-render/nodes.js` (FR-024)
- [x] T034 [P] [US3] Ensure COLD and FAULT members expand too in `ui/netclaw-visual/src/orgchart-render/expansion.js` — what a cold claw *would* bring decides whether to warm it (FR-025)
- [x] T035 [US3] Retarget `#search` in `ui/netclaw-visual/index.html` and `main.js` to members, categories and tool names (FR-031)
- [x] T036 [US3] Implement highlight/dim matching that never hides or re-packs; a tool match makes its collapsed owner discoverable; clearing restores prior state including expansions (FR-031a, FR-031b, FR-031c)
- [x] T037 [US3] Enforce session-stable positions in `ui/netclaw-visual/src/main.js`: the poll path repaints only, never repositions or reorders (FR-034, FR-034a), and mid-session enrolment routes through `appendMember` (FR-034b)

**Checkpoint**: All three user stories complete. Feature is functionally whole.

---

## Phase 6: Accessibility (Cross-Cutting)

Spans all three stories, so it follows them rather than sitting inside one.

- [x] T038 Build the focusable DOM overlay over the canvas, reusing the `CSS2DRenderer` layer, in `ui/netclaw-visual/src/orgchart-render/a11y.js` (FR-032)
- [x] T039 Implement the keyboard model — Tab between bands/categories, arrows between siblings, Enter selects, expand affordance separately reachable (FR-032a)
- [x] T040 Expose accessible name **and health state as text** for every node in `ui/netclaw-visual/src/orgchart-render/a11y.js`; state must never be conveyed by colour or motion alone (FR-032b)
- [x] T041 Honour `prefers-reduced-motion` in `ui/netclaw-visual/src/orgchart-render/nodes.js` and `ui/netclaw-visual/src/orgchart-render/a11y.js`; the four states must stay separable with motion suppressed, since motion is a redundant channel only (FR-032c, R8)

**Checkpoint**: Chart is fully operable without a pointer.

---

## Phase 7: Removal (Only After the Replacement Works)

**⚠️ Deliberately last.** Deleting before Phases 3–6 land would leave the branch
with neither layout functioning.

- [x] T042 Delete orbit positioning (completing the FR-026 hard replace) from `ui/netclaw-visual/src/main.js`: `CORE_POSITIONS`, `CORE_CENTROID`, `RISK_LAYOUT.tierRadius`, per-core orbit animation, and the edge close-orbit slots (FR-027)
- [x] T043 **Verify FR-030d before deleting anything in T044** — confirm which fields of `state.integrations` / `state.devices` `renderSidebar` and `renderMetrics` still read; keep `fetchGraph()` and the `/api/graph` request alive (R5)
- [x] T044 Delete the scene-layer functions `buildIntegrations`, `buildDevices`, `createSkillSprites`, `computeDendritePositions`, `createDendriteMaterial`, `lightIntegration`, `lightDevice`, and the integration/device branches of `applyFilters`, from `ui/netclaw-visual/src/main.js` (FR-030, FR-030c)
- [x] T045 Confirm `renderSidebar`, `renderMetrics` and every renderer named in FR-018 still work after T044, **and that devices remain listed in the right-hand panel**, in `ui/netclaw-visual/src/main.js` (FR-030b, FR-030d)
- [x] T046 Confirm no orbit or integration/device scene code remains: `git grep` for the removed identifiers returns nothing outside history

> **T043 is the single highest-risk task in the feature.** It is the one realistic
> way this work breaks something else, so it is separated from T044 with its own
> verification rather than folded into the deletion.

---

## Phase 8: Polish & Verification

- [x] T047 [P] Update `ui/netclaw-visual/README.md` — new layout, health states, keyboard model, fixture usage (Constitution XI, XII)
- [x] T048 [P] Confirm SC-006: `git grep` over `ui/netclaw-visual/src/orgchart/` finds no hardcoded member name
- [x] T049 Verify SC-005 / SC-008 — `ui/netclaw-visual/src/panels/` and the chat surface behave identically to `main`, by diffing behaviour rather than eyeballing (FR-016, FR-017, FR-018)
- [x] T050 Verify SC-007 / SC-010 via `chrome-devtools-mcp` — four states separable in a greyscale screenshot, and again under emulated `prefers-reduced-motion`
- [x] T051 Verify SC-007a using `specs/072-hud-2-org-chart/fixtures/scale-100.json` — one FAULT among 25 COLD located in under 5 s
- [x] T052 Verify SC-009 against `specs/072-hud-2-org-chart/fixtures/live-29.json` — every node reachable and operable by keyboard alone
- [x] T053 Verify SC-011 against the live Border — node coordinates identical between first frame and 30 minutes of state churn
- [ ] T054 Verify SC-013 — 60 fps on `scale-100.json` with 5 expanded during pan/zoom, and no slower than HUD 1.0 on `live-29.json` (FR-029b, FR-029c)  **[BLOCKED: needs a discrete GPU — headless runs on swiftshader at 3 fps, which measures the software rasteriser, not the FR-029b target]**
- [x] T056 Verify SC-003 against `specs/072-hud-2-org-chart/fixtures/live-29.json` — no drag, scroll or keyboard input can produce a view with the external band below the internal band (FR-012)
- [x] T055 Verify SC-001 / SC-002 — external vs internal identified on first view; HOT members identifiable within 2 s

---

## Dependencies

```
Phase 1 Setup
      ↓
Phase 2 Foundational (T005–T014)   ← blocks everything
      ↓
Phase 3 US1 (P1, MVP) ─────┐
      ↓                    │
Phase 4 US2 (P2)           │ US2 and US3 both depend on US1's
Phase 5 US3 (P2)  ─────────┘ render scaffolding, not on each other
      ↓
Phase 6 A11y (cross-cutting, needs all nodes rendering)
      ↓
Phase 7 Removal (only after the replacement works)
      ↓
Phase 8 Polish & Verification
```

**Story independence**: US2 and US3 are independent of each other and may be
built in either order, or in parallel by two people, once US1 lands. Neither
can precede US1 — both need nodes on screen.

## Parallel execution examples

**Phase 2** — all five pure modules are mutually independent:

```
T005+T006 (normalize) ‖ T007+T008 (health) ‖ T009+T010 (categorize) ‖ T011+T012 (ordering)
then T013+T014 (layout, consumes the others' shapes)
```

**Phase 3** — after T015 (camera):

```
T016 (bands) ‖ T017 (nodes) ‖ T019 (links)   → then T020 wires them together
```

**Phase 5** — after T029 (affordance): `T032 ‖ T033 ‖ T034`

**Phase 8**: `T047 ‖ T048` immediately; the SC verifications are sequential
(one browser).

## Implementation strategy

**MVP = Phases 1–3 (T001–T023).** That delivers the readable top-down chart —
the actual complaint being fixed. US2 and US3 are refinements on a working chart.

**Incremental delivery**: each phase ends in a working state. The branch is
never broken, because removal (Phase 7) is last by construction — the orbit code
sits unused but functional through Phases 3–6.

**Suggested review points**: end of Phase 2 (tests green, logic proven without a
browser), end of Phase 3 (MVP visible — the right moment to confirm the layout
lands before building on it), and after T045 (the riskiest deletion verified).

---

**Total: 56 tasks** — Setup 4 · Foundational 10 · US1 9 · US2 4 · US3 10 ·
A11y 4 · Removal 5 · Polish 10
