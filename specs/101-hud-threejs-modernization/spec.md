# Feature Specification: HUD three.js Modernization — 0.170 → 0.185.1, plus legibility and selection work

**Feature Branch**: `101-hud-threejs-modernization`
**Created**: 2026-08-06
**Status**: **Merged** (PR #233, 2026-08-07). All five stories shipped. Closeout: FR-024 now met
(a favicon was declared — the 404 that kept the console non-empty was simply an undeclared icon).
Remaining open: T044 milestone blog post (offered, never published unprompted), and a cosmetic
residual where the two longest peer labels can still overlap at default zoom.
**Input**: Operator request, 2026-08-06 — "I can't click on Nate / eN2N netclaws in the HUD for details, they are not clickable"; then "anything else you think the HUD needs work on especially using three.js latest and greatest stuff"; then "proceed with fix, and 2-5; and bring in some really showboat three.js stuff we couldn't do in .170 with .185.1".

## Problem Statement

Three separate things are wrong with the HUD, and only one of them is about three.js.

1. **A federated peer cannot be inspected.** Clicking "Nate" repaints the detail panel with
   the generic overview instead of peer detail, because the click path passes a `setDetail`
   kind that has no branch. Root-caused in [research.md](./research.md) R7.
2. **The HUD ignores data it already has.** `/api/n2n` carries `channel_state`, `stale`, and
   `inventory_received_at` per peer. Nate (live channel, fresh inventory) and Byrn (stale
   since 2026-07-25) render essentially alike. Selection is `emissiveIntensity = 1.8` plus a
   scale bump, which is easy to miss in a bloom-heavy scene — there is no `OutlinePass` at all.
3. **The renderer is eighteen months behind.** `three@^0.170.0` against a current `0.185.1`,
   fifteen releases. This is the *least* urgent of the three, and the research shows it is
   also the cheapest to fix.

The framing that matters: the two improvements with the highest payoff need **no upgrade at
all**, and the two most impressive capabilities need a **renderer migration** that the version
bump alone does not deliver. Conflating "upgrade three.js" with "get the new toys" is the main
way this work could go wrong.

## Measured state (2026-08-06, verified — see research.md)

| Quantity | Value |
|---|---|
Installed three.js | `0.170.0` |
Latest three.js | **`0.185.1`** (2026-07-01), 15 releases ahead |
r171–r185 breaking changes affecting this HUD | **0** (grepped every deprecated/removed API) |
Build at `0.185.1` with zero code changes | **passes** (exit 0) |
Bundle delta | 753.22 kB → 798.95 kB, **+45.73 kB (+6.1%)** |
Test files importing three.js | **0** — the 85 passing tests prove nothing about rendering |
Modules importing three.js | **7**, all with **zero** test coverage |
`ShaderMaterial` instances (GLSL, would need TSL port) | **4** |
`onBeforeCompile` hooks (worst part of a WebGPU port) | **0** |
`EffectComposer` passes in the chain | **7** |
Scene size | ~40 nodes (7 peers + 30 members + Border + edges) |

## Clarifications

### Session 2026-08-06

- **Q: Migrate to `WebGPURenderer`, or stay on `WebGLRenderer`?** → **A: Staged. This feature
  stays on `WebGLRenderer`.** The WebGPU migration and the capabilities that depend on it
  become a **follow-on spec (102)** with its own risk budget.

  Rationale, recorded because it is the load-bearing decision of this feature: adopting
  `WebGPURenderer` requires porting 4 `ShaderMaterial`s to TSL *and* rebuilding a 7-pass
  `EffectComposer` chain, because it supports neither raw GLSL shaders nor `EffectComposer`
  (research R4). Bundling that with the peer-detail bug fix and the 0.185.1 bump — both
  proven-safe — would make a zero-risk change hostage to a large one. Staging also means the
  two highest-payoff improvements (selection legibility, liveness encoding) ship without
  waiting on a renderer rewrite that, per research R5, does not itself improve them.

  **Consequence for this spec**: US6 and US7 are removed and moved to Out of Scope; FR-029
  through FR-033 and SC-008 go with them. US1–US5 are unchanged and were written to be
  renderer-agnostic, so nothing else shifts.

- Q: What should the liveness encoding do when the `/api/n2n` poll itself fails (network
  error, daemon down, malformed response)? → A: **Freeze and flag.** Retain the last known
  good state, mark the whole scene as stale-data with the age of the last successful poll, and
  never mutate per-peer liveness on a failed fetch. A failed poll is not evidence about peers;
  conflating "I cannot see" with "they are down" would fabricate a total outage and send an
  operator chasing it.

- Q: How should the performance target be quantified, given FR-021's unfalsifiable
  "measurably"? → A: **Relative budget — frame time may not increase more than 10% versus a
  captured pre-change baseline on the same machine and the same scene.**

  Because a relative budget is only as good as its baseline, the baseline capture is itself
  constrained (FR-044): same machine, same scene composition, same quality mode, same browser,
  measured over a sustained window rather than an instant, and recorded in the PR so the
  comparison is reproducible rather than asserted. Without that, a noisy baseline run makes any
  later regression pass.

- Q: What happens when a peer is selected and then disappears from the `/api/n2n` feed? → A:
  **Retain and mark as gone.** Keep the panel showing that peer's last known detail, explicitly
  flagged as no longer present in the feed, and drop the node's selected treatment in the scene.
  This is Q1's principle one level down: blanking the panel discards what the operator was
  reading mid-investigation, while keeping it live and unlabelled is the FR-006 defect in a new
  place. Peers genuinely do leave the feed — Hermes was re-enrolled under a new AS on
  2026-07-23, and spec 100's `forget_peer_endpoint` mutates rows under a running HUD.

- Q: How do SC-002 and SC-003 pass or fail, given "an observer can correctly identify/sort" is
  self-graded? → A: **Declared channels plus screenshot evidence.** The design must name the
  specific visual channels carrying each state (e.g. outline, rim, opacity, badge, label
  affix), and acceptance is a screenshot in which each declared channel is present and distinct
  per state. Self-checkable with the `chrome-devtools-mcp` already in use, needs no second
  observer, and converts a judgement into a check. A pixel-diff fixture harness (the fully
  objective option) was rejected as tooling this repo has never had and does not need for four
  states.

- Q: Which three.js version is the FR-044 performance baseline captured against, given US5
  bumps mid-feature? → A: **Two baselines.** Capture at `0.170.0`; land the bump alone and
  re-measure, gating its own frame-time delta at 10%; then measure US2/US3/US4 against the
  post-bump baseline.

  Without this, a baseline at 0.170 followed by both a bump and new animation makes a
  regression unattributable, defeating the falsifiability Q2 was chosen to create. It also
  gives US5 a performance gate it otherwise lacks entirely — FR-025 only required the upgrade
  preserve *visual* behavior, so nothing checked whether it cost frame time.

  **Sequencing consequence**: US5 must land **alone and before** US2/US3/US4 are measured, even
  though it is P2 by operator value. Priority orders *value*; this orders *measurement*.

### Decisions taken without asking (reasonable defaults, recorded)

- **The version bump is decoupled from the renderer choice.** Verified free at build level
  (research R2), so it lands first and alone regardless of how the renderer question resolves.
  Bundling them would make a zero-risk change hostage to a large one.
- **Verification is visual, via the already-integrated `chrome-devtools-mcp`** (feature 048),
  not a new headless-GL harness. The seven three.js modules have no tests and a rendering
  regression is visual by nature (research R6). No new dependency.
- **The peer inspector is written against the `/api/n2n` shape, not `/api/graph`.** It is the
  richer source and already carries the staleness fields US3 needs (research R7).
- **Compute-shader particles are scoped to link flow only.** The >1M-unit headline is
  irrelevant at 40 nodes; as packet flow along federation links it is informative rather than
  decorative (research R5).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Inspect a federated peer (Priority: P1)

An operator clicks an eN2N peer in the org chart and sees that peer's federation detail:
identity, channel state, inventory freshness, chat enablement, and in-flight delegated tasks.

**Why this priority**: it is the reported defect, it is a genuine bug rather than an
enhancement, and it is currently misleading — the panel repaints with plausible-looking
content for a *different* subject, which is worse than doing nothing visible.

**Independent Test**: click each of the 7 peers; each shows its own detail. Fully testable
with no other story implemented.

**Acceptance Scenarios**:

1. **Given** the HUD is loaded with live `/api/n2n` data, **When** the operator clicks the
   peer node "Nate", **Then** the detail panel shows Nate's identity, state, channel state
   and inventory freshness — not the generic "This NetClaw" overview.
2. **Given** a peer with `stale: true` and an inventory from 12 days ago, **When** it is
   selected, **Then** the panel states the staleness explicitly rather than showing a bare
   timestamp the operator must date-arithmetic themselves.
3. **Given** a `severed` peer, **When** it is selected, **Then** the panel shows the severed
   state and does not present it as reachable.
4. **Given** keyboard navigation to a peer node, **When** it is activated, **Then** the same
   detail renders — both entry points are affected by the defect and both must be fixed.
5. **Given** a peer with in-flight delegated tasks, **When** it is selected, **Then** those
   tasks are listed.
6. **Given** a peer is selected, **When** it disappears from `/api/n2n` on the next poll,
   **Then** the panel still shows its last known detail marked as no longer present, and the
   node is no longer drawn as selected.

---

### User Story 2 — Selection is unmistakable (Priority: P1)

An operator can always tell which node is currently selected, at any zoom, against a
bloom-heavy scene.

**Why this priority**: cheapest meaningful improvement in the whole feature, needs no upgrade
and no renderer decision, and it compounds with US1 — a detail panel is only useful if the
operator is confident *which* node it describes.

**Independent Test**: select nodes across bands and confirm the treatment is visible in a
screenshot without needing the panel to disambiguate.

**Acceptance Scenarios**:

1. **Given** any node is selected, **When** the operator looks at the scene, **Then** the
   selected node is distinguishable from every unselected node by a treatment that does not
   rely on emissive intensity alone.
2. **Given** a selected node in a cluster of cold members, **When** bloom is at its
   configured strength, **Then** the selection is still legible.
3. **Given** the selection changes, **Then** the previous node returns fully to its
   unselected appearance with no residue.
4. **Given** reduced-motion is preferred, **Then** the treatment is static rather than animated.

---

### User Story 3 — Liveness and staleness are readable from the scene (Priority: P1)

An operator can tell, without clicking anything, which peers and members are actually live and
which are stale or unreachable.

**Why this priority**: the biggest legibility win available, and it needs no upgrade. The data
is already fetched and already ignored. This is the difference between a topology picture and
an operational display.

**Independent Test**: with one live peer, one stale peer and one severed peer in the feed, all
three read differently in a screenshot.

**Acceptance Scenarios**:

1. **Given** Nate (`channel_state: "up"`, fresh inventory) and Byrn (`channel_state:
   "unknown"`, `stale: true`), **When** both render, **Then** they are visually distinct.
2. **Given** a peer whose inventory has never arrived (`inventory_received_at: null`),
   **Then** it is distinguishable from one with fresh inventory.
3. **Given** a member with `live: false` and `state: "provisioned"`, **Then** it is demoted
   relative to a live member, consistent with feature 072's existing visual-weight rules.
4. **Given** a peer transitions from live to stale while the HUD is open, **Then** the change
   is reflected on the next poll without a reload.
5. **Given** the encoding, **Then** it does not rely on color alone (accessibility — feature
   072 established an a11y tree that must stay coherent).

---

### User Story 4 — Federation links show flow (Priority: P2)

Links to live peers visibly carry traffic; links to stale or dead peers are visibly static.

**Why this priority**: this is where the "showboat" quality and genuine information coincide.
Deliberately P2 rather than P1 because it is an *addition* to US3's encoding rather than a
prerequisite for reading the scene. Achievable in the existing GLSL — no renderer decision.

**Independent Test**: one live and one stale peer; the live link animates, the stale one does not.

**Acceptance Scenarios**:

1. **Given** a peer with a live channel, **Then** its link to the Border shows directional flow.
2. **Given** a stale or severed peer, **Then** its link shows no flow.
3. **Given** reduced-motion is preferred, **Then** flow is conveyed without continuous animation.
4. **Given** ~40 nodes and their links, **Then** frame rate does not regress measurably.

---

### User Story 5 — Upgrade to 0.185.1 without regression (Priority: P2)

The HUD runs on `three@0.185.1` and looks and behaves exactly as it does today.

**Why this priority**: verified free at build level, so it is low-risk — but it delivers **no
visible operator value on its own**, which is precisely why it is P2 and not P1. It is
enabling work and honesty requires labelling it as such.

**Independent Test**: bump, build, load the HUD, confirm zero console errors and a visually
unchanged scene.

**Acceptance Scenarios**:

1. **Given** the dependency is `0.185.1`, **When** the project builds, **Then** it succeeds
   with no source change (already verified in an isolated probe — research R2).
2. **Given** the HUD is loaded in a browser, **Then** the console shows no errors and no
   three.js deprecation warnings.
3. **Given** the upgraded HUD, **Then** the org-chart bands, labels, links, selection and the
   full post-processing chain are visually intact.
4. **Given** the bundle grows ~6%, **Then** initial load remains acceptable on the operator's
   normal access path.
5. **Given** `THIRD_PARTY_NOTICES.md` or the HUD README cites a three.js version, **Then**
   they are updated (Principle XII).
6. **Given** the pre-bump and post-bump FR-044 baselines, **When** they are compared, **Then**
   the upgrade's own median frame-time increase is within 10% — the bump is gated on cost, not
   only on looking unchanged.

---

### Edge Cases

- What happens when `/api/n2n` returns zero peers (fresh install)? US3's encoding must have an
  empty state — feature 072 already defines first-run behavior that must not regress.
- What happens when two peers share a `display_name` (the live "Hermes" case, two identities)?
  Feature 072's `disambiguateLabels` handles the label; US1's inspector must show the
  *identity*, not just the label, or the panel is ambiguous.
- What happens if `channel_state` is `"unknown"` — genuinely unknown, or not yet polled? US3
  must not render "unknown" as "dead".
- **Resolved (Clarifications):** what happens when the `/api/n2n` poll fails outright? The
  scene freezes on last known good state and is flagged stale with the age of the last
  successful poll (FR-041/042/043). Per-peer liveness is never mutated by a failed fetch.
- What happens on a browser without adequate WebGL 2? (The WebGPU variant of this question was
  removed with the renderer clarification — this feature stays on `WebGLRenderer`.)
- **Resolved (Clarifications):** a selected peer disappearing from the feed retains its last
  known detail in the panel, explicitly flagged as no longer present, and loses its selected
  treatment in the scene (FR-045).

## Requirements *(mandatory)*

### Peer inspection (US1)

- **FR-001**: Clicking or keyboard-activating any eN2N peer node MUST render that peer's own
  federation detail.
- **FR-002**: The inspector MUST be driven by the `/api/n2n` peer shape, and MUST NOT be
  implemented by routing peers to the existing BGP-session renderer, whose payload contract
  differs and would render undefined fields.
- **FR-003**: The inspector MUST show, at minimum: identity, display name, state, channel
  state, inventory freshness, chat enablement, and in-flight delegated tasks.
- **FR-004**: Inventory freshness MUST be expressed in operator terms (relative age and an
  explicit stale/fresh judgement), not as a raw timestamp alone.
- **FR-005**: Both the pointer and the keyboard/accessibility activation paths MUST be fixed.
- **FR-006**: No `setDetail` kind may fall through to the default overview branch. An
  unrecognised kind MUST fail loudly in development rather than silently rendering another
  subject's content — this silent fallthrough *is* the defect.
- **FR-045**: If the selected peer disappears from the feed, the inspector MUST retain that
  peer's last known detail and MUST label it as no longer present, and the scene MUST drop that
  node's selected treatment. The panel MUST NOT silently continue to read as current, and MUST
  NOT be blanked — the operator may be mid-investigation.

### Selection (US2)

- **FR-007**: The selected node MUST be distinguishable by a treatment that does not depend on
  emissive intensity alone.
- **FR-008**: Deselection MUST fully restore the prior appearance.
- **FR-009**: Exactly one node MUST read as selected at a time.
- **FR-010**: The selection treatment MUST respect reduced-motion preference.
- **FR-011**: Selection MUST remain legible at the extremes of the existing camera's
  configured zoom range.

### Liveness encoding (US3)

- **FR-012**: Peers MUST be visually differentiated by channel state and inventory staleness.
- **FR-013**: Members MUST be visually differentiated by `live` state, consistent with feature
  072's existing visual-weight rules rather than inventing a competing scheme.
- **FR-014**: The encoding MUST NOT rely on color alone, and MUST remain coherent with the
  existing a11y tree.
- **FR-015**: A state change MUST be reflected on the next poll without a reload.
- **FR-016**: `unknown` state MUST be rendered as distinct from both healthy and dead.
- **FR-017**: The encoding MUST NOT overstate confidence — a peer that is merely unpolled must
  not read as failed.
- **FR-041**: A failed, errored, or unparseable `/api/n2n` poll MUST NOT mutate any peer's or
  member's liveness encoding. The last known good state MUST be retained. Absence of data is
  not evidence of failure, and rendering it as failure would fabricate an outage.
- **FR-042**: While the last poll is failing, the HUD MUST indicate at scene level that the
  data is stale, including the age of the last successful poll, so the operator can distinguish
  "this is current" from "this is what I last knew."
- **FR-043**: On recovery, the scene MUST return to normal indication on the next successful
  poll with no reload and no manual acknowledgement.

### Link flow (US4)

- **FR-018**: Links to live-channel peers MUST show directional flow; links to stale or severed
  peers MUST NOT.
- **FR-019**: Flow direction MUST correspond to something real, or MUST be non-directional.
- **FR-020**: Flow MUST respect reduced-motion preference.
- **FR-021**: Flow MUST NOT increase median frame time by more than **10%** versus the
  pre-change baseline captured per FR-044, at current scene scale with all effects enabled.

### Version upgrade (US5)

- **FR-022**: The HUD MUST run on `three@0.185.1`.
- **FR-023**: The upgrade MUST NOT require changes to HUD source (verified at build level;
  runtime is what US5's acceptance covers).
- **FR-024**: After upgrade the HUD MUST load with zero console errors and zero three.js
  deprecation warnings.
- **FR-025**: All existing visual behavior MUST be preserved — bands, labels, links,
  selection, camera, and every post-processing pass.
- **FR-026**: The renderer stack version MUST be recorded in `ui/netclaw-visual/README.md`
  (Principle XII — documentation must accurately reflect current state). **Verified during
  analysis: neither `README.md` nor `THIRD_PARTY_NOTICES.md` currently cites a three.js
  version at all**, so this is an addition, not an edit. `THIRD_PARTY_NOTICES.md` is out of
  scope — it covers adapted third-party *source* (Jack Rabbit), not dependency versions.
- **FR-027**: `scripts/reconcile-mcp.py` MUST exit 0 (CLAUDE.md; CI gate).
- **FR-028**: The upgrade MUST be verifiable without disturbing the running
  `netclaw-hud.service`, or the disruption MUST be an explicit confirmed step.

### Verification

- **FR-034**: Runtime verification MUST be visual, using the existing `chrome-devtools-mcp`
  integration, and MUST NOT introduce a new test dependency.
- **FR-035**: Verification MUST cover zero console errors plus a screenshot confirming the
  scene renders.
- **FR-036**: Any new pure logic MUST be unit-tested on the `src/orgchart/` side of feature
  072's pure/render split, which forbids importing three.js.
- **FR-046**: The design MUST declare, per state, which visual channels carry it — selected vs
  unselected, and live vs unknown vs stale vs severed. Each state MUST map to a combination
  distinct from every other state's, and no state may be carried by color alone (FR-014).
  SC-002 and SC-003 are checked against this declaration, so an undeclared channel set makes
  them unverifiable.
- **FR-044**: **Two** performance baselines MUST be captured and recorded in the PR: one at
  `three@0.170.0` before any change, and one at `three@0.185.1` after the bump lands alone.
  Each MUST state machine, browser, scene composition (node counts by band), quality mode, and
  median frame time over a sustained window — not an instantaneous reading. An uncaptured or
  unreproducible baseline makes FR-021, FR-047 and SC-005 unverifiable and blocks their
  acceptance.
- **FR-047**: The version bump's own frame-time delta MUST be measured between the two FR-044
  baselines and MUST NOT exceed 10%. US2/US3/US4 are then measured against the **post-bump**
  baseline, so a regression is attributable to the upgrade or to the feature work, never
  ambiguous between them.

### Preservation

- **FR-037**: The chat interface and the right-hand information bar MUST NOT be altered —
  carried forward from feature 072's explicit operator constraint.
- **FR-038**: Feature 072's layout stability guarantees MUST hold: no sibling node moves as a
  result of selection or expansion.
- **FR-039**: `server.js` and the `/api/n2n` contract MUST NOT change. This is a client-side feature.
- **FR-040**: The existing a11y tree and keyboard navigation MUST remain functional.

## Success Criteria *(mandatory)*

- **SC-001**: An operator can click any of the 7 peers and see that peer's own detail — 7/7,
  where today it is 0/7.
- **SC-002**: A screenshot with no panel visible shows the selected node carrying every
  channel declared for selection (FR-046), each visibly distinct from the unselected treatment
  of the same node type.
- **SC-003**: A screenshot set covering **all six** declared peer states (`LIVE`, `IDLE`,
  `STALE`, `UNKNOWN`, `UNREACHABLE`, `SEVERED`) shows six mutually distinct combinations of
  the declared channels (FR-046) — no two states share an identical rendering. Covering only
  live/stale/severed would leave FR-016's `UNKNOWN`-is-distinct requirement unverified
  visually, which is exactly the state five of seven live peers occupy.
- **SC-004**: The HUD runs on `0.185.1` with zero console errors and no visual regression.
- **SC-005**: Median frame time at current scene scale is within **110%** of the **post-bump**
  FR-044 baseline, and the bump's own delta from the pre-bump baseline is also within 110%
  (FR-047). All three numbers are recorded in the PR. A run that cannot produce them fails this
  criterion rather than passing by default.
- **SC-006**: No `setDetail` call can silently render the wrong subject — an unhandled kind is
  detectable rather than plausible.
- **SC-007**: Bundle growth from the upgrade stays within ~10% of today's 753 kB.
  the WebGPU-only capabilities absent rather than broken.
- **SC-009**: Every claim of "verified" in this feature is backed by a build result, a
  screenshot, or a test — not by inspection alone.
- **SC-010**: With the mesh daemon stopped, no peer's appearance changes to indicate failure,
  and the scene reports stale data with the age of the last successful poll. Directly testable
  by stopping `netclaw-mesh.service` with the HUD open.

## Assumptions

- The operator's browser supports WebGL 2 today; WebGPU availability is not assumed.
- `/api/n2n` remains the source of truth for federation state, unchanged by this work.
- Feature 072's pure/render split, band layout, camera constraints and a11y tree are the
  foundation to build on, not to revisit.
- The ~40-node scale holds. Nothing here is designed for thousands of nodes, and the research
  explicitly rejects capabilities justified only at that scale.
- `chrome-devtools-mcp` (feature 048) is installed and usable against `localhost:3000`.
- `netclaw-hud.service` runs a live Vite dev server from the working tree, so dependency
  changes are operationally visible and must be sequenced deliberately.
- The 4 `ShaderMaterial`s and 0 `onBeforeCompile` hooks measured in research R4 are the
  complete custom-shader surface.

## Out of Scope

- **The `WebGPURenderer` migration and everything gated on it — deferred to spec 102.**
  Resolved in Clarifications, not dropped. Specifically deferred: porting the 4
  `ShaderMaterial`s to node materials/TSL, rebuilding the 7-pass `EffectComposer` chain on the
  node post-processing stack, `ClusteredLighting` (new in r185 — a light per live claw),
  compute-shader particle flow, and per-object selective bloom.

  Spec 102 inherits three constraints already established here, so it need not re-derive them:
  the migration cost is **4 shaders and 0 `onBeforeCompile` hooks** (research R4); the WebGL
  fallback keeps the scene rendering but does **not** restore WebGPU-only capabilities, making
  every such capability a progressive enhancement the HUD must be correct without; and
  `ClusteredLighting` overrides the WebGPU lighting system rather than layering on it.

  It should be sequenced **after** 101 lands, because 101 establishes the visual baseline
  (selection treatment, liveness encoding) that 102's post-processing rewrite must preserve —
  attempting them together would leave no known-good reference to regress against.
- **WebXR / VR walkthrough of the mesh.** Newly possible with WebGPU in r185 and genuinely
  interesting, but a distinct feature with its own interaction design.
- **Rendering thousands of nodes.** Compute particles and instancing headlines target a scale
  this HUD does not have; scoped in R5 to link flow only.
- **Replacing CSS2D labels with SDF text** (`troika-three-text`). Current labels are crisp and
  selectable; the only gain is depth-correct occlusion, which has not been reported as a problem.
- **Changing `server.js`, `/api/n2n`, or any MCP server.** Client-side only.
- **The chat interface and right-hand info bar** (FR-037).
- **Revisiting feature 072's layout algorithm.**
- **Upgrading to r186+.** Unreleased at spec time; its `Object3D.dispose()` change is noted in
  research R3 as a future consideration.

## Dependencies

- `three@0.185.1` from npm.
- Feature 072's org-chart modules (`src/orgchart/`, `src/orgchart-render/`).
- Feature 048's `chrome-devtools-mcp` for runtime verification.
- The `/api/n2n` endpoint as it exists today.
