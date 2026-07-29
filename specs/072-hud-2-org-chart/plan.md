# Implementation Plan: HUD 2.0 — Top-Down Trust Org Chart

**Branch**: `072-hud-2-org-chart` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/072-hud-2-org-chart/spec.md`

## Summary

Replace the HUD's orbiting-cores scene with a planar, top-down trust org chart:
eN2N peers in an external band north of an explicit trust boundary, the Border
on the centre line, iN2N members below grouped into derived categories, and
mobile edges in their own lane at the boundary. Chat and the right-hand detail
panel are untouched.

The technical approach turns on one decision from Phase 0 (R1): **split pure
layout logic from three.js rendering**. Category derivation, health
classification, ordering, dedup and position maths become dependency-free
modules unit-tested with `node:test`; only genuinely perceptual criteria
(greyscale separability, fault-finding time, frame rate) need a browser. That is
what makes a 64-requirement visual spec falsifiable rather than "looks right".

Two supporting decisions: the camera becomes orthographic with rotation disabled
(R7) — the actual cure for "hard to navigate", more than the theme is — and the
scene sheds two entire populations (integrations, devices) that were being drawn
over the trust topology (FR-030).

## Technical Context

**Language/Version**: JavaScript ES2022 (ESM), Node 22+ for tooling
**Primary Dependencies**: three.js `^0.170.0` (existing), `OrbitControls`,
`CSS2DRenderer`, postprocessing chain, gsap `^3.12.5`, vite `^5.4.0`. **No new
runtime dependencies.**
**Storage**: N/A — stateless client; all state from `/api/n2n` and `/api/graph`
**Testing**: `node:test` (built-in, zero new dependencies) for pure logic;
`chrome-devtools-mcp` (already vendored, feature 048) for perceptual and
performance verification
**Target Platform**: Chromium-family browser, desktop
**Project Type**: Web frontend (single package, `ui/netclaw-visual/`)
**Performance Goals**: 60 fps sustained on a discrete GPU at 100 members /
~25 categories / 5 expanded (FR-029b); never slower than HUD 1.0 on identical
data (FR-029c)
**Constraints**: No new runtime dependency; no server change; no widening of the
HUD's API surface (FR-019); chat and right-hand panel behaviour unchanged
(FR-016/017/018)
**Scale/Scope**: ~100 members, ~25 categories, ~10 peers, ~10 edge nodes, all
simultaneously visible without virtualisation

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1.*

| Principle | Applies? | Assessment |
|---|---|---|
| I. Safety-First Operations | No | Read-only visualisation; issues no device commands |
| II. Read-Before-Write | No | No writes of any kind |
| III. ITSM-Gated Changes | No | Not a production device change |
| IV. Immutable Audit Trail | Partial | The HUD is a viewer, not an operator, and performs no auditable operation. `/api/chat` does, and is explicitly untouched (FR-016) |
| V. MCP-Native Integration | No | No new capability; consumes existing endpoints |
| VI. Multi-Vendor Neutrality | **Yes — PASS** | FR-006 forbids a hardcoded member list; categories derive from the shipped integration catalog, so no vendor is privileged |
| VII. Skill Modularity | Analogous — PASS | R1's pure/render split applies the same decomposition principle to UI code |
| VIII. Verify After Every Change | **Yes — PASS** | SC-001..013; FR-029c is an explicit regression guard |
| IX. Security by Default | **Yes — PASS** | FR-019 forbids widening the API surface. No new endpoint, no new privilege |
| X. Observability | Partial | Client-side; no new signals. Recorded as Deferred during clarify |
| XI. Full-Stack Artifact Coherence | **Yes — PARTIAL** | Not a new MCP/skill/integration, so catalog and installer entries do not apply. `ui/netclaw-visual/README.md` **MUST** be updated |
| XII. Documentation-as-Code | **Yes — PASS** | README update is a tracked task, not an afterthought |
| XIII. Credential Safety | **Yes — see violation below** | This feature adds no credential handling |
| XIV. Human-in-the-Loop | No | No external communication |
| XV. Backwards Compatibility | **Yes — PASS** | Layout-only hard replace. FR-016/017/018 preserve chat and panel; FR-030d keeps `/api/graph` alive for retained renderers; no shared interface changes |
| XVI. Spec-Driven Development | **Yes — PASS** | spec → 2× clarify → plan → tasks → analyze → implement |
| XVII. Milestone Documentation | Deferred | Post-merge decision, not a gate |

**Gate result: PASS.** No unjustified violations.

### Pre-existing constitutional violation (out of scope, recorded)

**Principle XIII (Credential Safety) is currently violated by the HUD**, prior to
and independently of this feature. `ui/netclaw-visual/server.js:1088`
(`GET /api/env/:integrationId`) returns unmasked credential values;
`server.js:17` applies `cors()` with no origin allowlist; `server.js:1789` binds
`0.0.0.0` while logging `localhost`. Confirmed live: device enable passwords, a
NetBox token, a ServiceNow password and a GitHub PAT are all retrievable over
unauthenticated HTTP.

This feature **must not compound it** (FR-019) and does not touch that surface.
The operator has been informed and elected to review it separately; the finding
is written up at `~/netclaw-reports/SECURITY-hud-credential-exposure.md`.

It is recorded here because a constitution check that silently passed over a
live Principle XIII violation *in the very file being edited* would be
dishonest.

## Project Structure

### Documentation (this feature)

```text
specs/072-hud-2-org-chart/
├── plan.md              # This file
├── research.md          # Phase 0 — 8 decisions, all unknowns resolved
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── layout-contract.md    # Phase 1 — pure-layout module contract
├── fixtures/                 # Phase 1 — synthetic /api/n2n payloads (R4)
│   ├── empty.json
│   ├── single.json
│   ├── live-29.json
│   ├── scale-100.json
│   └── uncategorised.json
└── tasks.md             # Phase 2 (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
ui/netclaw-visual/
├── package.json                 # +"test" script only (research R2)
├── server.js                    # UNCHANGED (FR-019; see violation note above)
├── index.html                   # #search retargeted (FR-031); legend added (FR-009c)
└── src/
    ├── main.js                  # Scene wiring. Orbit layout REMOVED (FR-026/027);
    │                            #   materials, ribbons, labels, picking, polling
    │                            #   and every panel renderer PRESERVED (FR-028)
    ├── orgchart/                # NEW — pure logic, imports NOTHING from three.js
    │   ├── categorize.js        #   member -> integration -> category (FR-006/006a)
    │   ├── categorize.test.js
    │   ├── health.js            #   HOT/WARM/COLD/FAULT + 900s threshold (FR-008/008a)
    │   ├── health.test.js
    │   ├── normalize.js         #   peer dedup (FR-014), label fallback (FR-015)
    │   ├── normalize.test.js
    │   ├── ordering.js          #   heat-then-size, computed once (FR-006b/034)
    │   ├── ordering.test.js
    │   ├── layout.js            #   bands, category columns, row packing (R6)
    │   └── layout.test.js
    ├── orgchart-render/         # NEW — three.js only, consumes orgchart/ output
    │   ├── bands.js             #   3 bands + trust boundary (FR-001/002)
    │   ├── nodes.js             #   instanced node geometry (FR-029a)
    │   ├── links.js             #   6 link styles (FR-010/011)
    │   ├── expansion.js         #   tool expand/collapse (FR-020..025)
    │   ├── camera.js            #   orthographic, rotation locked (FR-012/013)
    │   └── a11y.js              #   DOM overlay, keyboard, SR labels (FR-032)
    └── panels/                  # UNCHANGED
```

**Structure decision.** A single web frontend package; no backend change. The
`orgchart/` ÷ `orgchart-render/` split is load-bearing, not cosmetic — it is
what makes R1's testing strategy possible. `orgchart/` must stay importable in
bare Node with no WebGL context, enforced by its tests running under
`node --test` with no DOM.

## Complexity Tracking

| Item | Why it is not over-engineering |
|---|---|
| Two new directories rather than editing `main.js` in place | `main.js` is 132 KB. FR-026 mandates a hard replace of the layout; doing that inside one file makes the diff unreviewable and leaves no seam for tests |
| Five committed fixtures | SC-006 is a product-generality claim ("renders sensibly for a deployment it has never seen"). One deployment cannot evidence it, and 100-member performance cannot be measured on a 29-member Border |
| A11y DOM overlay | FR-032. A WebGL canvas exposes no focusable elements; there is no lighter mechanism. Reuses the `CSS2DRenderer` layer already present |
| `node:test` rather than no tests | The spec makes numeric claims (100 members, 900 s, 60 fps, four states) that rot silently without regression coverage |

**Rejected as unnecessary:** `d3-hierarchy` (the graph is two levels deep),
force-directed layout (non-deterministic, would violate FR-034), vitest (the
code under test imports nothing), Playwright (`chrome-devtools-mcp` already
vendored), any server-side change (FR-019).

## Post-Design Constitution Re-Check

Re-evaluated after Phase 1 artifacts. **Still PASS**, with two observations:

- **Principle VI strengthened by the design.** `categorize.js` takes the
  integration catalog as an *argument* rather than importing it, so the
  vendor-neutrality guarantee is testable — `categorize.test.js` proves the same
  code produces different, correct charts for different catalogs.
- **Principle XV risk concentrated in one place.** The only realistic way this
  feature breaks something else is FR-030d (deleting scene builders whose
  `/api/graph` payload a panel renderer still reads). R5 verified the dependency
  by reading the source rather than assuming; it becomes a discrete task with
  its own verification step rather than a line in a larger deletion.

No new violations introduced by the design.

## Phase 2 preview

`/speckit.tasks` will decompose along the structure above. Expected ordering:
fixtures → pure modules with tests → render modules → camera → a11y → deletion
of the orbit and integration/device populations → README → verification against
SC-001..013. Deletions land **after** the replacement works, so the branch never
sits in a state where neither layout functions.

---

*Phase 0 complete: [research.md](./research.md) — 8 decisions, no NEEDS CLARIFICATION remaining.*
*Phase 1 complete: [data-model.md](./data-model.md), [contracts/layout-contract.md](./contracts/layout-contract.md), [quickstart.md](./quickstart.md).*
