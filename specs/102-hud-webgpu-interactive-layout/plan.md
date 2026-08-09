# Implementation Plan: HUD WebGPU Showcase + Interactive Layout

**Branch**: `102-hud-webgpu-interactive-layout` | **Date**: 2026-08-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/102-hud-webgpu-interactive-layout/spec.md`

## Summary

Two independent bodies of work in one feature: migrate the HUD to `WebGPURenderer` (unlocking
`ClusteredLighting` and compute particles), and make the layout arrangeable — drag, five presets,
per-preset position memory, and server-side save/restore including camera pose.

**Approach**: they share almost nothing. The layout work is pure logic plus pointer handling and
one server route; the renderer work is a shader/post-processing port. The plan below sequences the
**layout half first**, which is the opposite of how the spec reads.

**Why layout first, against the spec's own story order**: US4/US5 (WebGPU) rewrite the entire
render path. If the layout work lands after that rewrite, every layout bug is ambiguous — is it the
drag code or the new renderer? Landing layout on the *known-good* 101 renderer means each half has
a working reference. It also front-loads the thing the operator actually asked for, and leaves the
optional-by-definition showcase last, where it can be cut without stranding anything.

## Technical Context

**Language/Version**: JavaScript ES2022 (ESM), Node 22+ for tooling. No TypeScript.
**Primary Dependencies**: `three@0.185.1` — **no new package**. New import surfaces: `three/webgpu` (`WebGPURenderer`, `PostProcessing`, `Lighting`), `three/tsl` (node functions), `three/addons/lighting/ClusteredLighting.js`, and `three/examples/jsm/tsl/display/*` (`BloomNode`, `RGBShiftNode`, `SMAANode`, `AfterImageNode`, `FilmNode`). Force-directed solver is hand-written, not a dependency (research R4).
**Storage**: **NEW** — a single JSON file written by `server.js` at a fixed path, holding per-preset node positions and camera pose. First persistent state the HUD client has ever had. `/api/n2n` and `/api/graph` unchanged (FR-032).
**Testing**: `node --test 'src/**/*.test.js'` for pure logic under `src/orgchart/` (145 tests today). Visual verification via Chrome DevTools, now provisioned. Server route tested through its pure validator, not by booting Express.
**Target Platform**: Desktop Chrome/Chromium. WebGPU where available; `WebGPURenderer`'s own WebGL 2 backend otherwise.
**Project Type**: Single frontend package plus a scoped server change — `ui/netclaw-visual/`.
**Performance Goals**: Median frame time within **110%** of spec 101's post-bump baseline (SC-005), measured with `specs/101-*/evidence/hud-probe.mjs` on the same host. Force-directed solve must be bounded and off the render loop (FR-040).
**Constraints**: Exactly one renderer path (FR-036). `/api/n2n`, `/api/graph`, chat interface and right-hand bar unchanged. 072's camera constraints hold even for restored poses (FR-047). 101's six peer states, selection ring and link-flow gating must survive the port (FR-023).
**Scale/Scope**: ~40 nodes. ~8 files touched, 4–5 new pure modules, 1 server route.

### Resolved during clarification (no open questions remain)

Five closed by `/speckit.clarify`: preset set, drag-vs-orbit disambiguation, camera in saved
layouts, per-preset position memory, and explicit-save-plus-unload-warning.

One item from research is **flagged rather than silently decided**:

**GlitchPass has no node equivalent** and research R1 recommends **dropping it** rather than
reimplementing. It is decorative, encodes no state, and on an operations display can read as a
rendering fault — which works against FR-025's own rule that every visual channel encode real
state. This is a visible change the operator did not request, so it is surfaced here for a
decision rather than buried in a task.

**One genuine unknown remains**, recorded rather than guessed (research R7): the exact API for
detecting which backend `WebGPURenderer` chose (`renderer.backend.isWebGPUBackend` or equivalent
on 0.185.1). It gates only the showcase capability check, and it is confirmed empirically in
Phase 3 rather than assumed now.

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **VIII. Verify After Every Change** | **PASS** | 101's committed baselines and probe script are the reference (FR-037), which is exactly why they were committed. Each half verified before the next lands. |
| **X. Observability First-Class** | **PASS** | HUD work. The layout half changes presentation only; no operational state is added, removed, or reinterpreted. |
| **XI. Full-Stack Artifact Coherence** | **PASS (subset)** | No MCP server, skill, integration or installable component; no tool counts change. Applicable: `ui/netclaw-visual/`, its `README.md` (101's renderer table becomes wrong on migration), and `reconcile-mcp.py` exit 0. |
| **XII. Documentation-as-Code** | **PASS** | README renderer table updated in the same PR. |
| **XIII. Credential Safety** | **PASS** | No credentials. Saved layouts are geometry only (FR-018), asserted by test (SC-008). |
| **XIV. Human-in-the-Loop (External)** | **PASS** | No external communication. |
| **XV. Backwards Compatibility** | **PASS (additive)** | `/api/layout` is a **new** route; no existing endpoint's shape or meaning changes (FR-032). A HUD without a saved layout behaves exactly as today. |
| **XVI. Spec-Driven Development** | **PASS** | specify → clarify → plan → tasks → analyze → implement. |
| **XVII. Milestone Documentation** | **DEFERRED** | Offered at completion; publication needs approval (XIV). |

**Principles I–VII, IX**: not applicable — no device interaction, no network configuration, no
ITSM-gated change, no audit-bearing operation, no new MCP server, no vendor logic, no skill, no
authentication surface.

**Gate result: PASS.** One deviation recorded and justified: `server.js` changes, which 072 and
101 both forbade. It is scoped by FR-032 to layout persistence, bounded by FR-033/034, and
research R5 established the HUD server *already* accepts writes (`PUT /api/env`,
`PUT /api/testbed/raw`) — so this is a new route in an existing pattern, not a new class of risk.

### Two honest weaknesses, recorded not hidden

**1. The render layer still has no automated coverage**, and this feature rewrites it entirely.
101's mitigation applies and is pushed harder here: the solver, preset geometry, position memory,
save-payload validation and camera clamping all live in `src/orgchart/` where they are tested. What
remains untested is the *drawing* — which is what the screenshots are for.

**2. The renderer port has no A/B reference by construction** (FR-036 forbids keeping WebGL). 101's
committed baseline screenshots are the substitute. That is weaker than a live comparison and it is
the single largest risk in this feature — hence the sequencing that keeps the layout work off it.

## Project Structure

### Documentation (this feature)

```text
specs/102-hud-webgpu-interactive-layout/
├── spec.md              # 53 FRs, 9 SCs, 5 clarifications
├── plan.md              # This file
├── research.md          # Phase 0 — R1..R8, verified against installed three@0.185.1
├── data-model.md        # Phase 1 — layout state, preset memory, save payload
├── quickstart.md        # Phase 1 — how to verify each half
├── contracts/
│   └── layout-api.md    # Phase 1 — GET/PUT /api/layout, validation, renderer port map,
│                        #           preset/solver constraints
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
ui/netclaw-visual/
├── server.js                       # SCOPED EXCEPTION: GET/PUT /api/layout only
├── README.md                       # renderer table (101) becomes wrong on migration
└── src/
    ├── main.js                     # drag handling, preset dropdown, save control,
    │                               # unsaved indicator + unload warning
    ├── orgchart/                    # PURE — never imports three.js
    │   ├── presets.js              # NEW  Ring + Grid geometry from existing band data
    │   ├── presets.test.js         # NEW
    │   ├── force-layout.js         # NEW  deterministic, seeded, fixed-iteration solver
    │   ├── force-layout.test.js    # NEW
    │   ├── layout-store.js         # NEW  per-preset position memory + dirty tracking
    │   ├── layout-store.test.js    # NEW
    │   ├── layout-payload.js       # NEW  save/restore shape + validation + camera clamp
    │   └── layout-payload.test.js  # NEW
    └── orgchart-render/            # three.js — no automated coverage
        ├── index.js                # apply positions from the store, not computeLayout alone
        ├── drag.js                 # NEW  raycast drag, pointer capture, camera restore
        ├── links.js                # US1: links follow moved nodes, incl. member elbow routing
        ├── renderer.js             # NEW  WebGPURenderer + node post-processing chain
        └── nodes.js                # 4 ShaderMaterials -> TSL node materials
```

**Structure Decision**: no new package. The pure/render split from 072 is followed strictly, and
deliberately exploited — four of the five new modules are pure and tested, leaving only drawing and
pointer plumbing in the untested layer.

## Phase Sequencing and Risk

Ordered so each half has a working reference, which the spec's story order does not provide:

1. **Layout foundations** (pure): presets, solver, position memory, payload validation. All
   testable with no renderer involvement at all.
2. **US1 drag + US2 presets** on the existing 101 renderer. The operator gets the requested
   feature here, on a known-good render path.
3. **US3 save/restore**, including the `server.js` route. Independent of the renderer.
4. **US4 renderer migration** — the 4 TSL ports and the node post-processing chain. Verified
   against 101's baseline screenshots *and* against the layout work already known to be correct.
5. **US5 showcase** — ClusteredLighting and compute particles. Last, and the only part that can be
   dropped without stranding anything.

**Primary risk: the renderer port has no live A/B.** Mitigated by sequencing (steps 1–3 are proven
before the render path changes), by 101's committed baselines, and by the fact that 5 of 7 passes
have direct node equivalents (research R1) so most of the port is re-wiring rather than
re-authoring.

**Second risk: the 30-second poll repaint.** `updateOrgChart` runs on every poll and recomputes
positions. It is the single most likely place a dragged node silently snaps back (US1 acceptance
scenario 2 exists specifically for this), and it must consult the position store rather than
`computeLayout` alone.

**Third risk: label collision, again.** Spec 101 shipped a collision that only a screenshot caught.
Five presets multiply that surface — Grid and Ring both change inter-node spacing wholesale. FR-013
applies per preset, and every preset needs a screenshot, not just the default.

**Non-risk, verified**: `ClusteredLighting` exists as a shipped addon and installs in one line
(research R2); `three/webgpu` and `three/tsl` are declared package exports, not deep imports
(research R3).

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|---|---|---|
| `server.js` changes, forbidden by 072 and 101 | Operator chose server-side persistence so a layout follows them across browsers | `localStorage` was the simpler option and was explicitly declined; scoped by FR-032 to one additive route, and research R5 shows the server already accepts writes |
| Hand-written force solver instead of a library | FR-039/040 require determinism and a bounded stop; libraries seed with `Math.random()` and tick forever | Adding `d3-force` then fighting both of its defaults is more code and more risk than ~100 lines of seeded Verlet |
