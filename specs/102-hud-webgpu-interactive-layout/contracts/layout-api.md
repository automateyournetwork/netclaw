# Phase 1 Contract: Layout Persistence API + Renderer Port Map

**Feature**: 102-hud-webgpu-interactive-layout
**Date**: 2026-08-07
**Input**: [spec.md](../spec.md) FR-015..019, FR-032..035 · [data-model.md](../data-model.md) · [research.md](../research.md) R1, R5

Two contracts: the server route (the scoped `server.js` exception) and the pass-by-pass renderer
port map (which decides what visibly changes).

---

## 1. `GET /api/layout`

Returns the saved layout, or an explicit empty state. **Never 404s for "no layout yet"** — absence
is a normal first-run condition, not an error, and making the client distinguish 404-means-none
from 404-means-broken is a needless trap.

| Response | Body |
|---|---|
`200` (saved layout exists) | the `SavedLayout` object (data-model §3) |
`200` (none saved) | `{ "version": 1, "empty": true }` |
`200` (file corrupt / unknown version) | `{ "version": 1, "empty": true, "warning": "<reason>" }` |

**Corrupt reads return 200 with a warning, not 500.** FR-019 requires the HUD fall back to computed
*and say so*; a 500 would be indistinguishable from the server being down, and the HUD would
render identically either way. The `warning` string is what the operator sees.

---

## 2. `PUT /api/layout`

Writes the layout. Explicit-save only — nothing else calls this (FR-015).

**Request**: a `SavedLayout` object (data-model §3).

| Response | Body | When |
|---|---|---|
`200` | `{ "saved": true, "savedAt": "<iso>" }` | validated and written |
`400` | `{ "error": "<specific reason>" }` | any validation failure (data-model §4) |
`507` | `{ "error": "write failed: <reason>" }` | disk write failed |

### Binding rules

- **V1 — Validate before touching disk.** A rejected payload writes nothing. There is no partial
  write and no truncate-then-fail: a half-applied layout is worse than a rejected one.
- **V2 — Reject unknown top-level keys** rather than ignoring them. Silent acceptance of junk is
  how a schema rots, and it is also how unexpected data ends up persisted.
- **V3 — Per-route size and count bounds** (256 KB, ≤500 entries/preset). The global
  `express.json({ limit: '4mb' })` at `server.js:21` is far too permissive for this route
  (research R5) and MUST NOT be relied on as the bound.
- **V4 — The write path is a module constant.** No path component may derive from the request
  (FR-034). Node ids are map keys only and are never used to build a filename — enforced by the
  id charset check, so it is structural rather than a convention.
- **V5 — Write atomically** (temp file + rename), so a crash mid-write cannot leave a truncated
  file that then fails every subsequent read.
- **V6 — Errors are specific.** `"positions.ring: 812 entries exceeds 500"` beats
  `"invalid payload"` — the operator has to be able to act on it.
- **V7 — Nothing else in `server.js` changes** (FR-032). `/api/n2n` and `/api/graph` keep their
  exact shapes.

### What is deliberately absent

No auth, no per-user scoping, no conflict resolution, no `If-Match`. The single-operator
assumption (spec Assumptions) makes last-write-wins correct rather than lazy. **If a second
operator ever uses the HUD concurrently, this contract is wrong** — recorded here so that is a
known limit rather than a surprise.

---

## 3. Renderer port map (FR-021, FR-036)

Verified against the installed `three@0.185.1` (research R1). Five of seven passes have direct
node equivalents.

| Current | Node replacement | Status |
|---|---|---|
`RenderPass` | absorbed by `PostProcessing` | no port needed |
`UnrealBloomPass` | `BloomNode.js` | direct |
`ShaderPass(RGBShiftShader)` | `RGBShiftNode.js` | direct |
`SMAAPass` | `SMAANode.js` | direct |
`AfterimagePass` | `AfterImageNode.js` | direct |
`FilmPass` | `FilmNode.js` | direct |
`OutputPass` | absorbed by `PostProcessing` | no port needed |
`ShaderPass(VignetteShader)` | **none** | **hand-write in TSL** — radial darkening, a handful of nodes |
`GlitchPass` | **none** | **DROP — needs operator sign-off** |

### The GlitchPass decision (FR-021 requires this be recorded, not silent)

**Recommendation: drop it.** It is decorative, encodes no state, and fires periodically — on an
operations display a random image displacement can read as a rendering fault or a data problem.
FR-025 requires every visual channel to encode real state, so reimplementing the one effect that
violates that rule is effort spent working against the feature.

**But it is a visible change the operator did not ask for**, so it is surfaced rather than
absorbed. If the answer is "keep it", it is a hand-written TSL node like vignette, not a blocker.

### Material port (FR-020)

The 4 `ShaderMaterial` instances become node materials. **No GLSL may remain** (FR-036) — a dormant
second path would rot unnoticed because nothing would exercise it.

Verification is against spec 101's committed baseline screenshots (FR-037), since the hard switch
leaves no live WebGL build to A/B against. That is the weakest link in this feature and the reason
the layout work is sequenced first.

---

## 4. Showcase capability gate (FR-024, FR-026)

`ClusteredLighting` and compute particles are **WebGPU-backend only**. `WebGPURenderer` chooses its
backend automatically, so there is **no renderer branch** — only a capability check.

```js
const lighting = new ClusteredLighting();
renderer.lighting = lighting;          // research R2, one line
```

| Rule | Requirement |
|---|---|
Showcase features apply only on the WebGPU backend | FR-024 |
On the WebGL 2 backend they are **absent, not broken** — no empty overlays, no error state | FR-024, SC-004 |
A driver failure mid-session degrades rather than blanking the scene | FR-026 |
101's six peer states, selection ring and link-flow gating survive both paths | FR-023, SC-006 |

**Open item, flagged not guessed** (research R7): the exact backend-detection API on 0.185.1
(`renderer.backend.isWebGPUBackend` or equivalent) is confirmed empirically during implementation.
It gates only this check.

---

## 5. Verification mapping

| Criterion | Checked by |
|---|---|
SC-001 (dragged nodes persist) | Drag 3 nodes; select, expand, wait a poll, enroll a member |
SC-002 (default identical) | Screenshot vs 101's committed baseline |
SC-003 (save survives reload + membership change) | Save, reload, add/remove a member |
SC-004 (WebGL backend correct) | Force the WebGL backend; showcase absent, scene intact |
SC-005 (frame time ≤110%) | `specs/101-*/evidence/hud-probe.mjs`, same host |
SC-006 (six peer states survive) | 101's `peer-treatments.test.js` unchanged + screenshot |
SC-007 (no label collision) | **A screenshot per preset** — 101 shipped a collision that only a screenshot caught, and five presets multiply that surface |
SC-008 (no secrets persisted) | Assert on the **emitted payload**, not the serializer |
FR-039 (determinism) | Solve twice, assert deep equality — pure function, trivially testable |
FR-045 (camera restored) | Abort a drag via `pointercancel` and by leaving the window; camera still orbits |
