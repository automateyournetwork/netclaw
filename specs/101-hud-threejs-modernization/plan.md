# Implementation Plan: HUD three.js Modernization

**Branch**: `101-hud-threejs-modernization` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/101-hud-threejs-modernization/spec.md`

## Summary

Fix the eN2N peer inspector (a `setDetail` kind with no branch, silently repainting another
subject's content), make selection and liveness legible from the scene, animate flow on live
federation links, and move the HUD from `three@0.170.0` to `0.185.1`.

**Approach**: everything lands client-side in `ui/netclaw-visual/`, on `WebGLRenderer`. The
renderer migration and the capabilities that need it were split to spec 102 during
clarification. Four of the five stories are pure client work against data `/api/n2n` already
returns; the fifth is a dependency bump verified free at build level (research R2).

**Sequencing is not the same as priority.** US5 (the bump) is P2 by operator value but must land
**first and alone**, because FR-047 gates the upgrade's own frame-time delta between two
baselines and US2/US3/US4 are then measured against the post-bump one. Landing them together
would make any regression unattributable.

## Technical Context

**Language/Version**: JavaScript ES2022 (ESM), Node 22+ for tooling. No TypeScript in this package.
**Primary Dependencies**: `three` 0.170.0 → **0.185.1** (the only dependency change); existing `gsap`, `lil-gui`, `vite` 5.4 unchanged. Addons consumed as-is: `OrbitControls`, `CSS2DRenderer`, `EffectComposer` + `RenderPass`/`UnrealBloomPass`/`ShaderPass`/`OutputPass`/`SMAAPass`/`AfterimagePass`/`FilmPass`/`GlitchPass`, `VignetteShader`, `RGBShiftShader`. **No new package.**
**Storage**: N/A — stateless client. All state from `GET /api/n2n` and `GET /api/graph`; nothing persisted.
**Testing**: `node --test 'src/**/*.test.js'` (built-in runner, no framework — feature 072's choice) for pure logic under `src/orgchart/`. Runtime/visual verification via `chrome-devtools-mcp` (feature 048). **New pure modules are testable; render modules remain untested by design** — see the Testing Strategy gap below.
**Target Platform**: Desktop Chrome/Chromium with WebGL 2, served by `netclaw-hud.service` (Express :3001 + Vite :3000).
**Project Type**: Single frontend package inside an existing monorepo — `ui/netclaw-visual/`.
**Performance Goals**: Median frame time within **110%** of baseline (FR-021, FR-047, SC-005). Two baselines required: at 0.170.0 and post-bump at 0.185.1 (FR-044).
**Constraints**: `server.js` and the `/api/n2n` contract MUST NOT change (FR-039). Chat interface and right-hand info bar untouched (FR-037). Feature 072's layout stability holds — no sibling moves on select/expand (FR-038). No state may be carried by color alone (FR-014). Bundle growth ≤10% of 753 kB (SC-007).
**Scale/Scope**: ~40 nodes (7 peers + 30 members + Border + 2 edge nodes). ~6 files touched, 2–3 new pure modules.

### Resolved during clarification (no open questions remain)

All five ambiguities were closed by `/speckit.clarify` and are recorded in spec.md
Clarifications: poll-failure behavior, the performance metric, selected-peer disappearance,
how SC-002/003 are validated, and which version the baseline is taken against.

One item was **deferred** at quota and is resolved here rather than left open:

**Browser floor** — the spec's Edge Cases ask what happens without adequate WebGL 2.
**Decision: out of scope as a behavior change; document only.** The HUD already fails the same
way today, this feature does not alter renderer initialisation, and inventing a fallback UI
would be new scope justified by no observed incident. Recorded so it is a decision rather than
an oversight. If it ever matters, it belongs with spec 102's renderer work, which touches
initialisation anyway.

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **VIII. Verify After Every Change** | **PASS** | FR-044 mandates two captured baselines; FR-034/035 mandate screenshot + zero-console-error verification per story. This feature's verification is stronger than its predecessor's precisely because research R2 showed the existing test suite cannot see rendering. |
| **X. Observability First-Class** | **PASS** | This *is* HUD work, and the clause "the Three.js HUD MUST be updated to reflect new integrations and their operational status" is the feature's whole point — US3 surfaces operational status the HUD currently fetches and discards. |
| **XI. Full-Stack Artifact Coherence** | **PASS (subset — no new capability)** | Adds **no** MCP server, skill, integration, or installable component, so the catalog/install-steps/SOUL/SKILL/`config/openclaw.json` clauses do not apply. Applicable subset: `ui/netclaw-visual/` (the feature itself), `ui/netclaw-visual/README.md` (record the renderer stack version, FR-026 — analysis found neither README nor THIRD_PARTY_NOTICES currently cites one, so this is an addition), and `scripts/reconcile-mcp.py` must exit 0 (FR-027). No tool counts change. |
| **XII. Documentation-as-Code** | **PASS** | Renderer stack version recorded in the same PR (FR-026). No SKILL.md — no skill added. |
| **XIII. Credential Safety** | **PASS** | No credentials, no new environment variable. |
| **XIV. Human-in-the-Loop (External)** | **PASS** | No external communication. Principle XVII post drafted and offered, never published unprompted. |
| **XV. Backwards Compatibility** | **PASS** | `/api/n2n` consumed unchanged (FR-039); no API, schema or tool contract altered. The three.js bump is internal to the package. |
| **XVI. Spec-Driven Development** | **PASS** | specify → clarify → plan → tasks → analyze → implement. |
| **XVII. Milestone Documentation** | **DEFERRED to completion** | Offered after implementation; publication needs approval (XIV). |

**Principles I, II, III, IV, V, VI, VII, IX**: not applicable — no device interaction, no
configuration written to network devices, no ITSM-gated change, no audit-bearing operation, no
new MCP server, no vendor-specific logic, no new skill, no authentication surface. This is a
read-only visualization of data another component already audits.

**Gate result: PASS.** No violations, nothing to justify in Complexity Tracking.

### One honest weakness, recorded not hidden

Principle VIII is satisfied *procedurally* (baselines, screenshots) but the seven modules that
import three.js have **zero automated coverage**, and this feature adds render code to them.
Feature 072's pure/render split is what makes that tolerable — logic goes in `src/orgchart/`
where it *is* tested — and this plan deliberately maximises what lands on the pure side
(state→channel mapping, staleness formatting, freeze-and-flag decisions) so the untestable
surface stays as thin as possible. That is a mitigation, not a fix.

## Project Structure

### Documentation (this feature)

```text
specs/101-hud-threejs-modernization/
├── spec.md              # Feature specification (5 clarifications integrated)
├── plan.md              # This file
├── research.md          # Phase 0 — R1..R8, empirically verified
├── data-model.md        # Phase 1 — client-side view state, no persistence
├── quickstart.md        # Phase 1 — how to capture baselines and verify each story
├── contracts/
│   └── visual-contract.md   # Phase 1 — the FR-046 declared-channel table + panel contract
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
ui/netclaw-visual/
├── package.json                    # US5: three 0.170.0 -> 0.185.1 (the only dep change)
├── README.md                       # FR-026: record renderer stack version (currently absent)
└── src/
    ├── main.js                     # US1: new 'federation-peer' setDetail branch + FR-006
    │                               #      guard; US2: wire selection treatment; freeze-and-flag
    │                               #      on poll failure (FR-041..043)
    ├── orgchart/                    # PURE — never imports three.js (feature 072 rule)
    │   ├── peer-detail.js          # NEW  US1: /api/n2n peer -> panel view-model
    │   ├── peer-detail.test.js     # NEW
    │   ├── liveness.js             # NEW  US3: state -> declared visual channels (FR-046)
    │   ├── liveness.test.js        # NEW
    │   ├── freshness.js            # NEW  US1/US3: relative-age + stale judgement (FR-004)
    │   ├── freshness.test.js       # NEW
    │   ├── feed-state.js           # NEW  US3: poll outcome -> freeze/flag decision (FR-041..043)
    │   └── feed-state.test.js      # NEW
    └── orgchart-render/            # three.js — no automated coverage (see weakness above)
        ├── nodes.js                # US2 selection treatment, US3 liveness channels
        ├── links.js                # US4 flow animation
        └── index.js                # US1 activateNode -> correct detail kind
```

**Structure Decision**: no new package and no new directory. Everything extends
`ui/netclaw-visual/`, respecting feature 072's hard split — `src/orgchart/` is pure and tested
and must never import three.js; `src/orgchart-render/` owns all three.js contact. Four new pure
modules exist specifically to move decision logic (what state means, how stale is stale, whether
to freeze) out of the untested render layer and into the tested one.

## Phase Sequencing and Risk

Ordered by **measurement dependency**, not by story priority:

1. **Baseline capture at 0.170.0** (FR-044) — blocks everything. SC-005 and FR-047 are
   unverifiable without it, and it cannot be recreated once the bump lands.
2. **US5 — the bump, alone** (FR-022..028, FR-047). Re-baseline at 0.185.1. Ships nothing
   visible; exists so later measurements are attributable.
3. **US1 — peer inspector** (P1). The reported defect. Independent of everything else.
4. **US3 — liveness encoding** (P1) then **US2 — selection** (P1). US3 first: it establishes the
   per-state channel declaration (FR-046) that selection must remain distinguishable *against*.
   Doing selection first risks choosing a treatment that collides with a state channel.
5. **US4 — link flow** (P2). Last, because it is the only story with a real perf risk and it
   should be measured against a scene that already carries US2 and US3's additions.

**Primary risk**: US2 vs US3 channel collision. Both add visual channels to the same nodes, and
the scene already runs seven post-processing passes including bloom. A selection treatment that
reads clearly on a healthy node may vanish on a dimmed stale one. FR-046's declared-channel
table exists to force that conflict to be resolved on paper first — hence US3 before US2, and
hence the contract being a Phase 1 artifact rather than an implementation detail.

**Secondary risk**: the live `netclaw-hud.service` runs Vite from the working tree, so a
dependency change is immediately visible to anyone watching the HUD. FR-028 requires the bump be
verifiable without disturbing it, or the disruption be explicit. Research R2's isolated-probe
technique is the pattern to reuse.

**Non-risk, verified**: the bump itself. Zero deprecated APIs in use, clean build at 0.185.1,
+45.73 kB (research R2/R3). This is why it is sequenced early rather than feared.

## Complexity Tracking

> No Constitution Check violations. Nothing to justify.
