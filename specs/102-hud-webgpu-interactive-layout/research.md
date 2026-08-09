# Phase 0 Research: HUD WebGPU Showcase + Interactive Layout

**Feature**: 102-hud-webgpu-interactive-layout
**Date**: 2026-08-07

Verified against the **installed `three@0.185.1`** in `ui/netclaw-visual/node_modules/` and the
repo's own source — not against articles. Spec 101 was misled twice by secondary sources giving
three different "current" versions, so the installed package is the authority here.

---

## R1 — The 7-pass mapping: 5 have node equivalents, 2 do not

**Decision**: port 5 passes to their node counterparts, hand-write vignette in TSL, and drop
GlitchPass as a recorded decision.

**Evidence** — `three/examples/jsm/tsl/display/` contains 45 modules:

| Current pass | Node equivalent | Action |
|---|---|---|
`RenderPass` | built into `PostProcessing` | absorbed, no port |
`UnrealBloomPass` | **`BloomNode.js`** | direct port |
`ShaderPass(RGBShiftShader)` | **`RGBShiftNode.js`** | direct port |
`SMAAPass` | **`SMAANode.js`** | direct port |
`AfterimagePass` | **`AfterImageNode.js`** | direct port |
`FilmPass` | **`FilmNode.js`** | direct port |
`OutputPass` | built into `PostProcessing` | absorbed, no port |
`ShaderPass(VignetteShader)` | **none** | hand-write in TSL |
`GlitchPass` | **none** | **drop** — see below |

**Vignette is trivial to hand-write** — radial darkening from UV distance, a handful of TSL nodes.
It stays.

**GlitchPass is proposed for removal, not reimplementation.** FR-021 requires any drop be a
recorded decision rather than a silent loss, so: it is a *decorative* effect that fires
periodically and displaces the image. Spec 101 established that every visual channel must encode
real state (FR-025 here), and a random periodic glitch encodes nothing — worse, on an operations
display it can read as a rendering fault or a data problem. Reimplementing it in TSL would be
effort spent restoring the one effect that actively works against the feature's own rule.
**Recommend dropping; flagging because it is a visible change the operator did not ask for.**

**Alternatives rejected**: keeping `EffectComposer` alongside (FR-036 forbids two paths);
`ChromaticAberrationNode` as an RGBShift substitute (a real `RGBShiftNode` exists, no need to
approximate).

---

## R2 — `ClusteredLighting` is real, addon-shipped, and one line to install

**Decision**: use `three/addons/lighting/ClusteredLighting.js`, assigned to `renderer.lighting`.

**Evidence** — the addon's own docblock:

```js
import { ClusteredLighting } from 'three/addons/lighting/ClusteredLighting.js';
const lighting = new ClusteredLighting();
renderer.lighting = lighting;   // overwrites the default lighting system
```

Constructor: `(maxLights = 1024, tileSize = 32, zSlices = 24, maxLightsPerCluster = 64)`.

**Rationale**: it *overwrites* `WebGPURenderer`'s lighting system rather than layering on it,
which is why spec 101 flagged it as an either/or. Defaults are far above this feature's needs —
one light per live claw is ~4–10 lights against a 1024 ceiling — so no tuning is expected, and
`maxLights` can be lowered to keep cluster memory small.

**Consequence for FR-024**: this is WebGPU-only. On the WebGL 2 backend the lighting system is the
default one and the per-claw lights simply do not cluster. Scene must still read correctly there.

---

## R3 — Import surface: `three/webgpu` and `three/tsl` are first-class exports

**Decision**: import the renderer and node classes from the package's declared export paths.

**Evidence** — `package.json` `exports`: `.`, `./addons`, `./addons/*`, `./examples/jsm/*`,
`./src/*`, **`./webgpu`**, **`./tsl`**. Build artifacts confirm it:
`three.webgpu.js`, `three.webgpu.nodes.js`, `three.tsl.js`.

**Consequence**: this is a genuine second entry point, not a deep import. `WebGPURenderer`,
`Lighting`, `PostProcessing` come from `three/webgpu`; TSL node functions from `three/tsl`.
Bundle impact is real — the webgpu build is a different, larger graph than `three.module.js` —
and must be measured against 101's 798.80 kB rather than assumed (SC-005's sibling concern).

---

## R4 — Force-directed determinism: no library, seed from node identity

**Decision**: implement a small deterministic solver in `src/orgchart/` (pure, tested). Do **not**
add `d3-force` or similar.

**Rationale**: FR-039 requires the same topology to produce the same arrangement every run. Most
force libraries seed initial positions with `Math.random()`, which defeats that immediately, and
they simulate continuously — which FR-040 forbids. Adding a dependency and then fighting both of
its defaults is worse than ~100 lines of Verlet integration seeded from a hash of the node
identity string.

**Consequences**:
- Seeding is from `identity`/`member_id`, which are stable across restarts (the same property
  spec 101 relied on for peer disambiguation).
- Fixed iteration count rather than an energy threshold — a threshold is data-dependent and can
  fail to converge, whereas a fixed count is bounded by construction and satisfies FR-040's
  "bounded time" directly.
- Solving happens once, off the render loop, producing a position map. The render layer consumes
  positions exactly as it does for every other preset — the solver never touches three.js.

**Alternatives rejected**: `d3-force` (random seeding, continuous ticking, new dependency);
running the sim in the render loop (violates FR-040, competes with SC-005).

---

## R5 — The server already has write endpoints; follow them, don't invent

**Decision**: add `GET`/`PUT /api/layout` to `server.js`, matching the existing style.

**Evidence** — `server.js` (1862 lines) already exposes writes: `PUT /api/env` (:1172),
`PUT /api/testbed/raw` (:1193), `POST /api/rag/upload` (:1728). It writes files with
`fs.writeFileSync` (:568, :1199), and `express.json({ limit: '4mb' })` is already configured
(:21).

**Rationale**: the "HUD gains write state it has never had" framing in the spec's clarification is
*half* right and worth correcting here — the HUD already accepts writes. What is new is that the
HUD's own *client* now persists state, which is a different claim and a smaller one. FR-033's
payload bound and FR-034's fixed path remain correct precautions, but this is not unprecedented
surface.

**Consequence**: the global 4 MB JSON limit is far too generous for a layout. FR-033's bound
should be enforced per-route (entry count and coordinate sanity), not left to the global limit.

**Alternatives rejected**: a new server (absurd for one file); reusing `/api/testbed/raw`'s
free-text write (no schema, and FR-033 requires validation).

---

## R6 — Dragging against `OrbitControls`: `enabled` toggle plus pointer capture

**Decision**: raycast on `pointerdown`; on hit, set `controls.enabled = false`, capture the
pointer, and restore on every termination path.

**Evidence**: `main.js` already owns a `THREE.Raycaster` and a `pickableObjects()` set from spec
101's selection work, and `camera.js` exposes the controls instance. Spec 101 also already
distinguishes hover from click through the same raycast.

**The failure mode FR-045 exists for**: `controls.enabled = false` is a persistent flag. If the
drag ends via `pointercancel`, the pointer leaving the window, or an exception mid-drag, and the
restore is only wired to `pointerup`, the camera stays dead permanently with no visible cause.
`setPointerCapture` + handling `pointerup`, `pointercancel` and `lostpointercapture` together is
what closes it — one handler is not enough.

**FR-044's threshold**: compare against the existing click path, which currently treats any
`pointerup` on a node as a select. A few pixels of movement is the discriminator.

---

## R7 — WebGPU availability and what "fallback" actually means

**Decision**: construct `WebGPURenderer` unconditionally and let it choose its backend; gate only
the *showcase features* on the backend actually in use.

**Rationale**: the spec's Q2 answer already records that `WebGPURenderer` has an automatic WebGL 2
backend, so "hard switch" does not exclude WebGL viewers. The practical consequence for
implementation is that there is no renderer branch — there is a **capability check** for
ClusteredLighting and compute particles.

**Open item for Phase 1**: the exact capability probe (`renderer.backend.isWebGPUBackend` or
equivalent on 0.185.1) needs confirming against the installed build rather than assumed. Recorded
here rather than guessed.

---

## R8 — Constitution applicability

| Artifact | Applies? | Why |
|---|---|---|
`ui/netclaw-visual/` | **Yes** | The feature itself |
`ui/netclaw-visual/server.js` | **Yes — scoped exception** | FR-032; the first HUD spec to change it, deliberately and narrowly |
Principle X (HUD first-class) | **Yes** | HUD work |
Principle XI | **Partial** | No MCP server, skill, integration or installable component. No tool counts change. |
`ui/netclaw-visual/README.md` | **Yes** | Renderer stack table added by 101 becomes wrong the moment `WebGPURenderer` lands |
`scripts/reconcile-mcp.py` | **Yes — must run** | CI gate |
Principle XV (backwards compat) | **Watch** | `/api/n2n` and `/api/graph` unchanged (FR-032), but a *new* route is added — additive, not breaking |
Principle XVII | Deferred | Offered at completion, never published unprompted |

**Not applicable**: I–IX (no device interaction, no vendor logic, no new MCP server, no
credentials).
