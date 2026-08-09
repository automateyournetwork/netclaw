# Feature Specification: HUD WebGPU Showcase + Interactive Layout

**Feature Branch**: `102-hud-webgpu-interactive-layout`
**Created**: 2026-08-07
**Status**: **Layout half implemented and merged** (US1 drag, US2 presets, US3 save/restore).
**US4 renderer migration and US5 showcase are DEFERRED to a follow-on spec** — see "Scope split"
below. The deferral is a verification constraint, not a change of mind.
**Input**: Operator request, 2026-08-07 — "work on 102 - the amazing show off polish - also for 102 ADD the ability to click / drag / reposition the layouts maybe offer a drop down default layout; some layout options; free-form; SAVE layout?"

## Scope split (2026-08-08)

US1–US3 shipped. US4 (WebGPU migration) and US5 (ClusteredLighting + compute particles) were cut
from this feature after a measurement, not a preference.

**WebGPU has no adapter on the verification host.** Probed directly against the running HUD:

```json
{"webgpu": false, "reason": "no adapter"}
```

`navigator.gpu` exists but `requestAdapter()` returns null — WSL2, no `/dev/dri`, and the HUD
renders through `ANGLE (SwiftShader driver)`. Two consequences made proceeding unwise:

- **US5 is unverifiable here at all.** ClusteredLighting and compute particles need the WebGPU
  backend, so FR-024's "present on WebGPU, absent on WebGL" cannot be exercised, and T042's
  backend-detection API cannot be confirmed rather than guessed.
- **US4 would have been a rewrite with two blindfolds.** The hard-switch decision (FR-036) already
  removed the live WebGL build that would otherwise be the A/B reference — an accepted risk. What
  was not known at decision time is that this host also cannot run the *target* backend. Replacing
  a working 7-pass chain and 4 shaders under both constraints, judged only against screenshots, is
  how a subtly broken HUD ships unnoticed.

The operator's own browser may well support WebGPU; the blocker is that **the implementer cannot be
the verifier**. The follow-on spec should establish who verifies before any porting begins.

Everything US4/US5 needs is already researched and survives the deferral: the 5-of-7 node-equivalent
port map, `ClusteredLighting`'s one-line install, the `three/webgpu` + `three/tsl` export surface,
and the GlitchPass drop decision (research R1–R3, contracts §3).

## Problem Statement

Two things, and they pull in different directions — which is the interesting part of this feature.

1. **The HUD can't do the impressive things r185 makes possible.** Spec 101 landed the version bump but stayed on `WebGLRenderer`, deferring `ClusteredLighting`, compute-shader particles and node-based post-processing here. These need `WebGPURenderer`, which supports neither raw-GLSL `ShaderMaterial` nor `EffectComposer` — so it is an either/or migration, not an upgrade.
2. **The layout is fixed and the operator wants to arrange it.** Nodes sit exactly where `computeLayout()` puts them, with no way to drag, rearrange, choose a different arrangement, or keep one.

**The tension worth naming up front**: feature 072's core premise is that *fixed* positions build spatial memory, and its FR-022/FR-038 explicitly guarantee no node ever moves as a result of selection or expansion — "a claw that fails changes how it looks, never where it is." Spec 101 carried that guarantee forward. Free-form dragging deliberately moves nodes.

That is not a contradiction to wave away. The resolution this spec proposes: **072 forbade the *system* moving nodes behind the operator's back; it did not forbid the operator moving them deliberately.** Spatial memory is preserved when position changes are operator-initiated, persistent, and reversible — and destroyed when they are algorithmic and surprising. Every layout requirement below is written to keep that distinction intact, and FR-038's original guarantee survives verbatim for system-initiated changes.

## Inherited from spec 101 (measured, not re-derived)

| Fact | Value |
|---|---|
`three` version | `0.185.1` (already landed) |
`ShaderMaterial` instances needing TSL port | **4** |
`onBeforeCompile` hooks | **0** — the usual worst part of a WebGPU port is absent |
`EffectComposer` passes to rebuild on the node stack | **7** |
WebGL fallback | automatic, but does **not** restore WebGPU-only capabilities |
Scene scale | ~40 nodes (7 peers + 30 members + Border + edges) |
Visual baseline to preserve | 101's six peer states, selection ring, link flow |
Test split | `src/orgchart/` pure and tested; `src/orgchart-render/` has no coverage |

`ClusteredLighting` overrides the WebGPU lighting system rather than layering on it.

## Clarifications

### Session 2026-08-07

- Q: Where do saved layouts persist? → **A: Server-side.** A new `server.js` endpoint backed by an
  on-disk file, so a layout follows the operator across browsers and survives a cache clear.
  **This makes 102 the first HUD spec to change `server.js`**, which 072 and 101 both explicitly
  forbade — now a *scoped, deliberate exception* rather than drift, narrowed to layout persistence
  with `/api/n2n` and `/api/graph` untouched (FR-032). Consequences accepted: the HUD gains write
  state it has never had, bringing a small attack surface (FR-033/034) and a "whose layout" question
  resolved by the single-operator assumption, not by building multi-user support.

- Q: Hard renderer switch, or runtime toggle? → **A: Hard switch to `WebGPURenderer`.** One
  maintained path: 4 shaders ported to TSL with no GLSL kept, 7-pass chain rebuilt on the node stack
  with no `EffectComposer` kept. **This does NOT abandon WebGL users** — `WebGPURenderer` has its own
  automatic WebGL 2 backend, so such browsers still render, just without the WebGPU-only showcase
  features already specified as progressive enhancements (FR-024). "Hard switch" is about how many
  code paths *we* maintain, not who can view. Real cost accepted: no second renderer to A/B against
  when a regression appears — mitigated by 101's committed baselines in `specs/101-*/evidence/`,
  which is exactly why they were committed. They are the reference implementation now.


- Q: Which layout presets ship? → **A: Five — Org chart (default), Ring, Grid, Force-directed,
  Free-form.**

  **Naming convention, fixed here because one of these is a wire value.** The `PresetId`
  identifiers are the literal strings `'orgchart'`, `'ring'`, `'grid'`, `'force'`, `'freeform'` —
  they are persisted verbatim as JSON keys in the saved layout. Prose in this spec writes
  "free-form" and "org chart" for readability, but **the hyphenated forms are never valid
  identifiers**. Writing `'free-form'` as a key is a bug, not a style choice. Ring places peers and members on concentric circles around the Border; Grid is
  uniform rows ignoring bands; Force-directed positions by link topology; Free-form is a blank
  slate the operator arranges.

  **Force-directed is the one that needs guarding, and it is guarded rather than dropped.** A
  running simulation moves nodes continuously, which is exactly what FR-027 forbids the system
  doing. Three constraints reconcile them (FR-038..041): it must be **deterministic** (same data →
  same layout, or the HUD looks different on every load and spatial memory is impossible), it must
  **settle and then stop** rather than simulate forever, and a node the operator drags is **pinned**
  and excluded from further solving. With those, force-directed is a one-shot arrangement the
  operator asked for — not the system rearranging things behind them.

  Recorded honestly: this is the only preset requiring a solver, and it carries tuning, stability
  and settling-time risk the other four do not. It is scoped to P2 alongside its siblings rather
  than promoted for being impressive.

- Q: How is a node drag disambiguated from a camera orbit? → **A: Raycast decides.** Pointer-down
  that hits a node begins a drag and suspends `OrbitControls` for its duration; pointer-down on
  empty space orbits exactly as today. No modifier, no mode toggle.

  Chosen because it needs no new UI and nothing to remember, and it degrades safely — a missed
  raycast simply yields today's camera behaviour. It also matches how 3D editors already behave,
  so it needs no explaining.

  Two failure modes this creates, and the requirements that close them: a drag that ends outside
  the canvas or is interrupted must still re-enable the camera, or the camera locks up permanently
  (FR-045); and since select and drag now share one gesture, a movement threshold is what separates
  them (FR-044).

  Recorded limitation: rearranging becomes **pointer-only**. Keyboard and screen-reader users keep
  full navigation and inspection (FR-029) but cannot reposition nodes. Accepted rather than
  hidden — the arrangement is presentation, and every state it conveys remains available through
  the a11y tree and the detail panel.

- Q: Does a saved layout include the camera? → **A: Yes — position, target and zoom are saved and
  restored with the arrangement.** In practice the arrangement and the viewpoint are one thing:
  restoring positions without the framing they were designed for delivers half the feature, and the
  Ring and Grid presets each want a different camera than the org chart does.

  Still only geometry, so FR-018's "no federation state, no credentials" guarantee is untouched. But
  it adds a way to strand yourself: a saved camera outside the constrained pan/zoom range, or aimed
  at nothing, would restore to an empty view with no obvious recovery. FR-047/048 close that.

- Q: What happens to manual positions when switching presets? → **A: Remembered per preset.**
  Dragged positions are stored against the preset they were made in; switching away and back
  restores them, and Free-form keeps its own set.

  Chosen because it makes a five-item dropdown safe to explore, which is what it has to be to earn
  its place. Nothing is ever destroyed, so FR-014's unresolved "warned about **or** undoable"
  either/or disappears — neither a confirm dialog nor an undo stack is needed, because there is no
  destructive act to guard.

  It also gives "Org chart" a second job: it is the reset, without being a reset that costs you
  anything. And it composes with FR-041's pinning — a node pinned in Force-directed stays pinned
  in Force-directed, not everywhere.

- Q: What triggers a save? → **A: Explicit save control, plus a browser warning on unload when
  there are unsaved changes.** Nothing is written until the operator asks for it.

  Keeps writes predictable and rare — one request per deliberate save rather than one per drag —
  and keeps the operator in control of what gets persisted, which matters more now that persistence
  is server-side and shared across browsers.

  **Recorded honestly: the unload warning is a mitigation, not a guarantee.** Browsers ignore custom
  text, require prior interaction with the page, and suppress the dialog in several cases (tab
  discard, crash, OS shutdown, mobile background-kill). Work *can* still be lost. That is accepted
  rather than papered over, and it is why FR-052 requires the unsaved state to be *visible* on
  screen — a dirty indicator an operator can see beats a dialog they may never get.

  A warning that fires when nothing has changed trains people to dismiss it reflexively, which
  would destroy the value of the one that matters — hence FR-051's requirement that it fire only
  on genuine unsaved change.

- Q: GlitchPass has no node equivalent — reimplement or drop? → **A: DROP** (operator delegated the
  call, 2026-08-07). It is decorative, encodes no state, and fires periodically; on an operations
  display a random image displacement can read as a rendering fault or a data problem. FR-025
  requires every visual channel to encode real state, so reimplementing the one effect that
  violates that rule is effort spent against the feature.

  **This is a visible change nobody asked for**, so it is recorded as a decision rather than
  absorbed: the HUD will no longer glitch. All six other effects survive the port.

### Decisions taken without asking (reasonable defaults, recorded)

- **Dragging moves a node, never its band membership or its edges.** A peer dragged below the
  trust boundary is still a peer. Position is presentation; topology is data.
- **Layout changes never alter `/api/n2n` state.** Nothing an operator does to the arrangement
  can affect federation, and nothing about the arrangement is reported as network state.
- **The computed layout stays the default.** Presets and free-form are opt-in; a fresh browser
  sees exactly what 072/101 produce today.
- **Showcase features remain progressive enhancements** (carried from 101): the HUD must be fully
  correct and readable without them, because the WebGL fallback cannot provide them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Drag a node and have it stay put (Priority: P1)

An operator drags a node to a position that suits how they think about the topology, and it stays
there — through selection, expansion, poll refreshes and member enrollment.

**Why this priority**: it is the concrete request, it is independently useful with nothing else
built, and it is where the 072 tension is resolved or broken. Getting this right makes the rest
safe; getting it wrong quietly destroys the spatial-memory property two specs paid for.

**Independent Test**: drag three nodes, then select, expand, wait out a poll, and confirm all
three are still exactly where they were put.

**Acceptance Scenarios**:

1. **Given** the operator drags a member node, **When** released, **Then** it stays at the new
   position and its links follow it.
2. **Given** a node has been moved, **When** the 30-second poll refreshes, **Then** it does not
   snap back — and this is the case most likely to regress, because `updateOrgChart` repaints on
   every poll.
3. **Given** a node has been moved, **When** a new member enrolls, **Then** the moved node does
   not shift and the new member is appended without disturbing it (072's FR-034b).
4. **Given** a node is dragged, **When** the pointer moves, **Then** the camera does not orbit —
   drag and orbit must not fight over the same gesture.
5. **Given** a node is dragged onto another node, **Then** nothing merges, snaps or reorders;
   overlap is the operator's business.
6. **Given** a moved node, **When** it is selected, **Then** 101's selection ring appears at its
   *current* position, not its computed one.

---

### User Story 2 — Choose a layout preset (Priority: P1)

An operator picks from five named arrangements — **Org chart** (today's computed default), **Ring**,
**Grid**, **Force-directed**, **Free-form** — and the scene rearranges to it.

**Why this priority**: the operator asked for a dropdown, and presets are what make free-form
recoverable. Without "reset to computed", a dragged-apart scene is unrecoverable, which would
make US1 dangerous rather than useful.

**Independent Test**: switch between every preset and back to the default; each produces a
distinct, readable arrangement and the default is byte-identical to today's.

**Acceptance Scenarios**:

1. **Given** the preset dropdown, **When** the operator selects the default, **Then** the scene
   is identical to what 072/101 compute today.
2. **Given** any preset, **Then** band membership, health treatments, peer states and link
   topology are unchanged — only positions differ.
3. **Given** nodes dragged in one preset, **When** the operator switches to another preset and back,
   **Then** those positions are exactly as left — switching is non-destructive.
3a. **Given** nodes have been dragged, **When** a preset is chosen, **Then** the manual positions
   are replaced, and the operator was warned first or can undo it.
4. **Given** a preset, **Then** labels do not collide at the default zoom. (Spec 101 shipped a
   label-collision regression that only a screenshot caught; presets multiply that risk.)
5. **Given** ~40 nodes, **When** switching presets, **Then** the transition does not drop frames
   below the established budget.
6. **Given** the Force-directed preset, **When** selected twice on unchanged data, **Then** it
   produces the **same** arrangement both times — a layout that differs every load cannot build
   spatial memory, which is the whole point of the fixed-position premise.
7. **Given** the Force-directed preset, **When** it has settled, **Then** the simulation **stops**
   and nodes hold still. Perpetual motion would violate FR-027 and burn frame budget forever.
8. **Given** a node dragged after a Force-directed solve, **Then** it stays where placed and is
   excluded from any later solve.

---

### User Story 3 — Save and restore a layout (Priority: P2)

An operator keeps an arrangement they like and returns to it later.

**Why this priority**: P2 because US1 and US2 are useful without it — but it is what makes the
effort of arranging worth spending. Gated on Q1.

**Acceptance Scenarios**:

1. **Given** an arrangement, **When** saved and the page reloaded, **Then** both the node positions
   and the camera view are restored as saved.
2. **Given** a saved camera pose outside the configured pan/zoom constraints, **When** restored,
   **Then** it is clamped into range rather than honoured, and the chart remains readable.
2. **Given** a saved layout, **When** a member that did not exist at save time has enrolled,
   **Then** it appears at its computed position rather than being hidden or crashing the restore.
3. **Given** a saved layout, **When** a member in it no longer exists, **Then** the stale entry
   is ignored silently.
3a. **Given** unsaved arranging, **When** the operator attempts to leave the page, **Then** the
   browser warns. **Given** no unsaved changes, **Then** it does not.
3b. **Given** unsaved arranging, **Then** that fact is visible on screen without leaving the page.
3c. **Given** a save that fails, **Then** the arrangement is retained in memory and still shows as
   unsaved — a failed write must never present as a successful one.
4. **Given** a saved layout, **Then** the operator can discard it and return to computed.
5. **Given** saved layout data, **Then** it contains only node identifiers and positions — never
   federation state, never credentials.

---

### User Story 4 — Node-based post-processing on WebGPU (Priority: P2)

The post-processing chain runs on the modern node stack, enabling per-object selective bloom.

**Why this priority**: enabling work for US5 and a real improvement to 101's selection ring
(which currently has to avoid additive blending precisely because `UnrealBloomPass` washes it
out). Ships little visible value alone.

**Acceptance Scenarios**:

1. **Given** `WebGPURenderer`, **Then** all four ported materials render as they do today.
2. **Given** the node stack, **Then** every one of the 7 current effects is present or its
   omission is a recorded decision.
3. **Given** selective bloom, **Then** a selected node can bloom without its neighbours doing so.
4. **Given** a WebGL-only browser, **Then** the HUD still renders correctly.

---

### User Story 5 — The showcase (Priority: P3)

Capabilities impossible at 0.170: a light per live claw via `ClusteredLighting`, and
compute-shader particle flow on federation links.

**Why this priority**: P3 and honest about it. Most visually impressive, least operationally
necessary, and unavailable to any WebGL fallback viewer.

**Acceptance Scenarios**:

1. **Given** `ClusteredLighting` with one light per live claw, **Then** dozens of dynamic lights
   render without the frame collapse this would cause at 0.170.
2. **Given** compute-shader flow, **Then** it replaces 101's three-dot approximation with real
   particle density on live links only.
3. **Given** a WebGL-only browser, **Then** these degrade to 101's treatments with nothing broken
   or empty.
4. **Given** any showcase channel, **Then** it encodes real state — never decoration that could
   be misread as liveness.

---

### Edge Cases

- What happens when a node is dragged outside the camera's constrained pan/zoom range?
- What happens to a moved node when the operator switches to a preset and back — is the manual
  position remembered or gone?
- What happens on a touch device, where drag and pan are the same gesture?
- What happens if a saved layout was produced by an older version with different node ids?
- What happens to `mountA11y`'s keyboard tree when positions become arbitrary? Its ordering
  currently derives from computed layout order.
- What happens when a peer is dragged across the trust boundary line — does the boundary still
  mean anything visually?
- What happens if WebGPU is available but the driver crashes mid-session?

## Requirements *(mandatory)*

### Dragging (US1)

- **FR-001**: Any node MUST be draggable to a new position with a pointer.
- **FR-002**: A moved node MUST retain its position across poll refreshes, selection, expansion,
  search and member enrollment.
- **FR-003**: Dragging MUST NOT alter band membership, category, health, peer state, or link
  topology. Position is presentation only.
- **FR-004**: Dragging MUST NOT orbit or pan the camera, and camera control MUST remain available
  when not dragging a node.
- **FR-005**: Links MUST follow a moved node, including the member elbow routing through category
  headers.
- **FR-006**: 101's selection ring and label MUST track the node's current position.
- **FR-007**: Overlapping nodes MUST NOT snap, merge, or reorder.
- **FR-008**: A drag MUST be distinguishable from a click, so dragging does not also select.
- **FR-043**: Drag initiation MUST be decided by raycast: a pointer-down that hits a pickable node
  begins a drag and suspends camera control; a pointer-down that hits nothing MUST fall through to
  `OrbitControls` unchanged. No modifier key and no mode toggle.
- **FR-044**: Select and drag share one gesture, so a **movement threshold** MUST separate them:
  below it the interaction resolves as a click (select), at or above it as a drag. A node MUST NOT
  be both selected and repositioned by one gesture.
- **FR-045**: Camera control MUST be restored on **every** drag termination — normal release,
  pointer leaving the canvas or window, loss of pointer capture, or an interrupted/cancelled drag.
  A drag that ends abnormally MUST NOT leave the camera permanently frozen, which is the worst
  outcome available here: the operator loses navigation with no visible cause and no way back
  except a reload.
- **FR-046**: Hover feedback MUST continue to work for pickable nodes, and MUST NOT be left stuck
  on a node after a drag begins or ends.

### Presets (US2)

- **FR-009**: The HUD MUST offer a named set of layout presets, including the current computed
  layout as the default.
- **FR-010**: The default preset MUST reproduce today's computed layout exactly.
- **FR-011**: Switching presets MUST NOT change any data-derived property — only positions.
- **FR-012**: There MUST be a way back to the computed layout from any arranged state.
- **FR-013**: No preset may produce colliding labels at the default zoom.
- **FR-038**: The preset set MUST be exactly: Org chart (default), Ring, Grid, Force-directed,
  Free-form.
- **FR-039**: Force-directed MUST be **deterministic** — the same topology and node set MUST
  produce the same arrangement on every run. Any randomness MUST be seeded from stable node
  identity, never from a clock or `Math.random()`.
- **FR-040**: Force-directed MUST reach a stable state and **stop simulating**, within a bounded
  time. It MUST NOT run continuously, both because FR-027 forbids ongoing system-initiated
  movement and because a permanent solver competes with the render budget SC-005 caps.
- **FR-041**: A node the operator has dragged MUST be **pinned** — excluded from force-directed
  solving, and left where placed. Operator intent outranks the solver.
- **FR-042**: Ring and Grid MUST be derived from the data `computeLayout` already produces (bands,
  categories, ordering). Neither may introduce a second source of truth for grouping.
- **FR-014**: Switching presets MUST NOT destroy manual positions. Each preset MUST retain its own
  set of operator-placed positions, restored when that preset is next selected. Because nothing is
  destroyed, no confirmation prompt and no undo stack are required.
- **FR-049**: Manual positions MUST be scoped **per preset**, not globally. A node dragged in
  Free-form MUST NOT move in Org chart, and a node pinned under Force-directed (FR-041) MUST be
  pinned only there.
- **FR-050**: Selecting the Org chart preset MUST restore the computed layout for any node not
  manually placed **within that preset**, giving the operator a non-destructive way back to the
  default from any arranged state (satisfying FR-012 without discarding work).

### Save / restore (US3)

- **FR-015**: An operator MUST be able to save the current arrangement through an explicit control,
  and have it restored later. Arrangements MUST NOT be written automatically.
- **FR-051**: The HUD MUST track unsaved changes and warn on page unload **only when changes are
  genuinely unsaved**. A warning that fires spuriously trains the operator to dismiss it, which
  destroys the value of the one that matters.
- **FR-052**: Unsaved state MUST be visible on screen, not only at unload. Browsers suppress unload
  dialogs in several cases (tab discard, crash, OS shutdown, no prior interaction), so a visible
  indicator is the primary signal and the dialog is a backstop.
- **FR-053**: A successful save MUST clear the unsaved-change state; a failed save MUST NOT
  (reinforcing FR-035 — a failed write must not look like a successful one).
- **FR-016**: A saved layout MUST tolerate nodes added since it was saved (place at computed
  position) and nodes removed since (ignore silently). It MUST NOT fail closed on either.
- **FR-017**: A saved layout MUST be discardable.
- **FR-018**: Saved data MUST contain only node identifiers, positions, and the camera pose
  (position, target, zoom) — no federation state,
  no credentials, no inventory.
- **FR-019**: A corrupt or unreadable saved layout MUST fall back to computed and say so, never
  render a broken scene.
- **FR-047**: A restored camera pose MUST be clamped to the camera's existing configured pan and
  zoom constraints. A pose outside them MUST be corrected, not honoured — spec 072 constrained the
  camera deliberately so the hierarchy always reads, and a saved layout must not be a way around it.
- **FR-048**: If a restored camera would show nothing (empty view, or a target no longer near any
  node), the HUD MUST fall back to framing the chart. Restoring into a blank screen with no visible
  cause is worse than ignoring the saved viewpoint.
- **FR-032**: Layout persistence MUST be the ONLY addition to `server.js`. `/api/n2n` and
  `/api/graph` MUST NOT change. A scoped exception, not a general licence.
- **FR-033**: The endpoint MUST reject any payload that is not node identifiers plus numeric
  positions, and MUST bound entry count and request size. The HUD has never accepted a write; an
  unbounded one is a new failure mode.
- **FR-034**: The layout file MUST be written to a fixed, non-configurable path under the HUD's own
  data directory. No path component may come from the request.
- **FR-035**: A write failure MUST surface to the operator and MUST NOT discard the in-memory
  arrangement — a failed save must not also lose what it failed to save.

### WebGPU migration (US4)

- **FR-020**: All four `ShaderMaterial`s MUST be ported to node materials/TSL with no visual
  regression against 101's baseline screenshots.
- **FR-021**: The 7-pass chain MUST be rebuilt on the node stack; any effect dropped MUST be a
  recorded decision, not a silent loss.
- **FR-022**: The HUD MUST render correctly on a browser without WebGPU, via `WebGPURenderer`'s own
  WebGL 2 backend. Showcase features are absent there, never broken (FR-024).
- **FR-036**: Exactly ONE renderer path ships. No GLSL `ShaderMaterial` and no `EffectComposer`
  usage may remain — a dormant second path would rot unnoticed, since nothing would exercise it.
- **FR-037**: With no live fallback to compare against, every visual claim MUST be verified against
  spec 101's committed baseline screenshots, not a running WebGL build.
- **FR-023**: 101's six peer states, selection ring and link-flow gating MUST be preserved
  exactly — they are the visual baseline this migration must not disturb.

### Showcase (US5)

- **FR-024**: WebGPU-only capabilities MUST be progressive enhancements. The HUD MUST NOT depend
  on them to convey any operational state.
- **FR-025**: Every new visual channel MUST encode real state.
- **FR-026**: A WebGPU driver failure mid-session MUST degrade rather than blank the scene.

### Preservation

- **FR-027**: 072's FR-038 guarantee survives **for system-initiated changes**: no node moves as
  a result of selection, expansion, search, poll refresh or enrollment. Only the operator moves
  nodes.
- **FR-028**: The chat interface and right-hand information bar MUST NOT be altered.
- **FR-029**: The a11y tree and keyboard navigation MUST remain functional with arbitrary
  positions.
- **FR-030**: `scripts/reconcile-mcp.py` MUST exit 0.
- **FR-031**: Any new pure logic MUST be unit-tested under `src/orgchart/`, which must never
  import three.js.

## Success Criteria *(mandatory)*

- **SC-001**: Three dragged nodes remain exactly where placed after selection, expansion, a poll
  refresh, and a member enrollment.
- **SC-002**: The default preset is visually identical to the pre-102 HUD.
- **SC-003**: A saved layout survives a page reload, and survives one member being added and one
  removed.
- **SC-004**: On a WebGL-only browser the HUD renders correctly with showcase features absent
  rather than broken.
- **SC-005**: Median frame time stays within 110% of 101's recorded post-bump baseline, measured
  the same way on the same host.
- **SC-006**: 101's six peer states remain mutually distinguishable after the renderer migration,
  checked against the same declared-channel table.
- **SC-007**: No preset or dragged arrangement produces colliding labels at default zoom.
- **SC-008**: Saved layout data contains no federation state or credentials, verified by
  inspecting what is written.
- **SC-009**: Every requirement has evidence — a test, a build result, or a screenshot.

## Assumptions

- The operator's browser supports WebGL 2; WebGPU availability is not assumed.
- 101's `evidence/` baselines and probe script are the comparison point for SC-005/SC-006.
- Chrome DevTools (spec 048) is now provisioned, so visual verification is available — it was not
  when 101 began.
- ~40 nodes remains the scale. Nothing here targets thousands.
- `/api/n2n` remains unchanged as the source of topology and state.
- **Single operator.** The HUD is served on loopback to one person, so a server-side layout needs no
  identity, scoping or conflict resolution. Concurrent use is last-write-wins — a recorded limit.
- `WebGPURenderer`'s automatic WebGL 2 backend is the fallback; no separate fallback is maintained.

## Out of Scope

- **WebXR / VR walkthrough.** Newly possible with WebGPU in r185, but a distinct feature.
- **Hierarchical / orthogonal layout solvers** (Sugiyama, tree routing, edge-crossing
  minimisation). Force-directed is in scope as one bounded, deterministic, stop-when-settled
  preset; general graph drawing is not.
- **Collaborative or shared layouts** — multiple operators seeing each other's arrangements.
- **Changing `/api/n2n` or `/api/graph`.** Still forbidden (FR-032); the `server.js` exception
  covers layout persistence and nothing else.
- **Multi-operator / shared layouts.** Server-side storage makes this look free; it is not — it
  needs identity, conflict resolution and per-user scoping.
- **Maintaining a WebGL renderer path.** Removed by the hard switch.
- **Rendering thousands of nodes.**
- **The chat interface and right-hand info bar.**

## Dependencies

- Spec 101 (merged): `three@0.185.1`, the six-state peer encoding, the selection channel, link
  flow, and the recorded baselines.
- Spec 072: band layout, camera constraints, pure/render split, a11y tree.
- Spec 048 (now provisioned): Chrome DevTools for visual verification.
