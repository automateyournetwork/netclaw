# Phase 0 Research: HUD three.js Modernization (0.170 → 0.185.1)

**Feature**: 101-hud-threejs-modernization
**Date**: 2026-08-06

Every finding below was verified against the migration guide, the official docs, or an
**isolated empirical build** — not inferred. Where a claim rests only on the build and
not on runtime behavior, that limit is stated explicitly.

---

## R1 — Version delta: 0.170.0 → 0.185.1, fifteen releases

**Ground truth from the npm registry** (`registry.npmjs.org/three`, `dist-tags.latest`),
not from secondary articles — three of which gave three different "current" versions
(r182, r184, r185):

| | |
|---|---|
Installed (`ui/netclaw-visual/package.json`) | `three@^0.170.0`, resolved `0.170.0` |
Latest | **`0.185.1`**, published **2026-07-01** |
Releases in between | 15 (`0.171` … `0.185.1`) |

Recent publish cadence: `0.183.0` 2026-02-18, `0.184.0` 2026-04-16, `0.185.0` 2026-06-25,
`0.185.1` 2026-07-01. Roughly one minor every 6–8 weeks, so a 15-release gap is ~18 months
of drift.

---

## R2 — The upgrade is empirically free for THIS codebase (build-level)

**Decision**: bump the dependency with **zero code changes**.

**Method** — an isolated probe, because `netclaw-hud.service` is running a live Vite dev
server out of `ui/netclaw-visual/` and swapping `node_modules` under it would break the
running HUD:

1. Copied `src/`, `index.html`, `canvas.html`, `vite.config.js` to a scratch dir.
2. Minimal `package.json` with the real dependency set (`three`, `gsap`, `react`,
   `react-dom`, `vite`, `@vitejs/plugin-react`), pinned `three@0.170.0`.
3. `npm run build` + `npm test` → baseline.
4. `npm install three@0.185.1`, re-ran both.

**Result**:

| | build | tests | bundle (`hud-*.js`) |
|---|---|---|---|
`0.170.0` | exit **0** | exit **0** | 753.22 kB |
`0.185.1` | exit **0** | exit 0, **85 pass / 0 fail** | 798.95 kB |

**No source change was required.** Bundle grows **+45.73 kB (+6.1%)**.

### ⚠️ What this does NOT prove

**The 85 tests do not import three.js at all.** Feature 072 deliberately split
`src/orgchart/` (pure logic, forbidden from importing three) from `src/orgchart-render/`
(three.js). Every test file lives on the pure side, so a green suite says nothing about
rendering. Verified: `grep -rl "from 'three" src/**/*.test.js` → no matches.

The seven modules that *do* import three — `main.js`, `orgchart-render/{bands,camera,
expansion,index,links,nodes}.js` — have **no test coverage at all**.

So the real evidence is narrower and worth stating precisely: **module resolution and
bundling of all 10 addon import paths succeed at 0.185.1**. That rules out the most
likely upgrade failure (a moved or deleted addon). It does not rule out a runtime or
visual regression, which needs browser verification (R6).

---

## R3 — Not one breaking change in r171–r185 touches this HUD

**Decision**: no remediation work is needed for the bump.

Cross-referenced the official migration guide for r171→r185 against every API the HUD
actually uses. The HUD's complete three.js surface is 10 addon imports plus core:

```
three                                    (×7 modules)
three/addons/controls/OrbitControls.js   (×2)
three/addons/renderers/CSS2DRenderer.js
three/addons/postprocessing/{EffectComposer,RenderPass,UnrealBloomPass,ShaderPass,
                             OutputPass,SMAAPass,AfterimagePass,FilmPass,GlitchPass}.js
three/addons/shaders/{VignetteShader,RGBShiftShader}.js
```

Grepped for every API deprecated or removed in that window — `Matrix3.translate/scale/
rotate`, `TiledLighting`, `LWOLoader`, `SVGLoader.createShapes`, `toTrianglesDrawMode`,
`SimplifyModifier`, `copyTextureToTexture`, `DRACOLoader.setDecoderConfig`, `FontLoader`,
`TextGeometry`, `useLegacyLights`, `outputEncoding`, `Texture.encoding`, `updateRange`,
`LightProbeGrid`, `BatchedMesh`, `AnamorphicNode`, `GTAO*`, `positionLocal`,
`directionToColor`, `inverseTransformDirection`, `PCFSoftShadowMap`+WebGPU:

**Zero hits.**

**Why the delta is so quiet for us**: the overwhelming majority of r171–r185 breaking
changes are in **TSL and the WebGPU node system** — `TextureNode.uv()`→`sample()`,
`varying()`→`toVarying()`, `blendBurn()` renames, `storageObject()` deprecation,
`PostProcessingUtils`→`RendererUtils`, `SSRNode`/`SSGINode`/`GTAONode` changes. The HUD
uses none of it. The genuinely cross-cutting breakages (WebGL 1 removal r163, color
management r152, `uv2`→`uv1` r152) all predate 0.170 and were already absorbed.

This **corrects an earlier assessment made in conversation** that "r185's deprecation
purge is a real breaking surface" for this HUD and should be treated as a deliberate
sweep rather than a bump. The evidence says the opposite: for this dependency surface it
is a bump. The one caveat is r186 (unreleased): `Object3D.dispose()` becomes a method
custom subclasses must chain via `super.dispose()`.

---

## R4 — WebGPURenderer is an either/or, not an upgrade — and this is the spec's central decision

**Decision**: treat the renderer choice as an explicit, staged fork. Do **not** couple it
to the version bump.

From the official WebGPURenderer manual, three constraints decide everything:

| Capability | Under `WebGPURenderer` |
|---|---|
Automatic WebGL 2 fallback | **Yes** — also forceable with `{ forceWebGL: true }` |
`ShaderMaterial` / `RawShaderMaterial` with raw GLSL | **NOT SUPPORTED** — must be ported to node materials + TSL |
`onBeforeCompile()` modifications | **NOT SUPPORTED** |
`EffectComposer` + its passes | **NOT SUPPORTED** — replaced by a node-based post-processing stack |

Direct quotes: *"Custom materials based on `ShaderMaterial`, `RawShaderMaterial` and
modifications of built-in materials via `onBeforeCompile()` are not supported in
`WebGPURenderer`."* and *"`EffectComposer` with its effect passes are not supported
because `WebGPURenderer` comes with a new, more modern post-processing stack."*

### The measured migration cost is small but non-zero

| Surface | Count | Migration |
|---|---|---|
`new THREE.ShaderMaterial` | **4** | port each to `NodeMaterial` + TSL |
`vertexShader:` / `fragmentShader:` blocks | 4 / 4 | same 4 materials |
`onBeforeCompile` hooks | **0** | nothing to port — a real saving |
`EffectComposer` passes in the chain | **7** (`RenderPass`, `UnrealBloomPass`, `ShaderPass`×2, `SMAAPass`, `AfterimagePass`, `FilmPass`, `GlitchPass`, `OutputPass`) | rebuild on the node stack |

Four shaders and one post-processing chain. Bounded, and the common effects (bloom
especially) are already ported to node classes upstream, so this is re-wiring rather than
re-inventing. `onBeforeCompile` being zero is the single biggest piece of luck here — that
is usually the worst part of a WebGPU migration.

**The fallback trap, stated plainly**: `forceWebGL: true` and the automatic fallback keep
the *scene* rendering, but they do not resurrect WebGPU-only capabilities. A viewer on a
WebGL-only browser gets no compute particles and no clustered lighting. Anything built on
those is therefore a **progressive enhancement**, never a baseline feature, and the HUD
must still look correct without them.

---

## R5 — Which "showboat" capabilities are genuinely new, and what each costs

Sorted by honest value **for a ~40-node operations HUD**, not by demo impressiveness.

| Capability | New since 0.170? | Needs WebGPU? | Verdict at this scale |
|---|---|---|---|
**Node-based post-processing** (`RenderPipeline`, r183) | Yes | **Yes** | Genuine win — replaces the 7-pass chain with a cleaner graph and makes *selective* per-object bloom straightforward, which the current `UnrealBloomPass` makes awkward |
**ClusteredLighting** (Forward+, r185, `three/addons/lighting/ClusteredLighting.js`) | **Yes — r185** | **Yes** (overrides the WebGPU lighting system) | Real and showy: a light per live claw. At r170 dozens of dynamic lights blew the budget; clustered shading partitions the frustum so only lights reaching a fragment are evaluated |
**Compute-shader particles** (>1M units vs ~50k WebGL ceiling) | Yes | **Yes** | **Overkill.** The headline number solves a problem 40 nodes do not have. Worth it *only* as packet-flow along links, where it is informative rather than decorative |
**TSL** (write once → WGSL + GLSL) | Yes | Authoring layer for WebGPU | A maintenance bet, not a feature. Upstream moved shader authoring here, so the 4 GLSL shaders are now the non-idiomatic path |
**WebXR + WebGPU** (r185) | **Yes — r185** | Yes | Deferred. A VR walkthrough of the mesh is a distinct feature, not part of this work |
**Selection outline / selective bloom** | No — possible at 0.170 | **No** | **Highest payoff per unit effort.** The HUD has *no* `OutlinePass`; selection is `emissiveIntensity = 1.8` + a scale bump, easy to miss against a bloom-heavy scene |
**Animated link flow** | No — possible at 0.170 | **No** | Where the "incredible" factor lives *and* it is informative: a live peer's link pulses, a 12-day-stale one goes static |
**Liveness/staleness encoding** | No | **No** | Biggest legibility win overall. `/api/n2n` already carries `channel_state`, `stale`, `inventory_received_at`; the render ignores them |

**Conclusion**: the two best improvements need no upgrade at all, and the two most
impressive need a renderer migration. That asymmetry is why the spec stages them.

---

## R6 — Runtime verification must be visual, and the tooling already exists

**Decision**: verify with the already-integrated `chrome-devtools-mcp` (feature 048), not
by adding a headless-GL test rig.

R2 established that the build proves module resolution only, and that the 7 three-importing
modules have zero test coverage. A rendering regression here is *visual* — a black canvas, a
missing bloom, mis-scaled labels — and no unit test in this repo's style would catch it.

Feature 048 already vendored `chrome-devtools-mcp` with a persistent profile, giving
navigation, console-error capture, and screenshots against `localhost:3000`. That is
exactly the missing verification layer, it needs no new dependency, and it makes
"the HUD still renders" a checkable claim instead of an assertion.

Minimum gate: load the HUD, assert zero console errors, screenshot, and confirm the
org-chart bands, labels, links and post-processing are visibly intact.

---

## R7 — The peer-detail defect is a genuine bug, already root-caused

Not a three.js issue at all, but in scope because it is the concrete complaint that
started this work: eN2N peers (e.g. "Nate") cannot be inspected in the HUD.

**Root cause** (verified in source): `setDetail()` in `main.js:1172` branches on exactly
six kinds — `local-core`, `member-core`, `integration`, `device`, `skill`, `peer-core`.
The org-chart click path passes a **seventh name that does not exist**:

```js
// main.js:2180 (mouse) and main.js:2765 (keyboard/a11y)
} else if (node.kind === 'peer') {
  setDetail('federation-peer', node.payload);   // ← no such branch
```

It falls through all six into the `// Default: overview` block at `main.js:1312` and
renders the generic "This NetClaw" + BGP summary. So the click *registers* and the panel
*repaints* — with the wrong content, which reads as "not clickable." Peer meshes are in
`pickableObjects()` and hover-scale correctly, which is what makes the dead click
confusing. `border`→`local-core` and `member`→`member-core` both hit real branches, so
members work and only peers break.

**Not fixable by renaming to `peer-core`.** That branch expects a BGP-session payload
(`peer.as`, `peer.routerId`, `peer.peerIp`, `peer.routesReceived`, `peer.adjRibIn`) from
`/api/graph`, but `layout.js:90` sets `payload: entity` — the raw `/api/n2n` peer object
(`identity`, `channel_state`, `inventory_version`, `stale`, `inventory`,
`in_flight_tasks`). Pointing it at `peer-core` would render a panel of `undefined`s. It
needs a renderer written against the federation shape — which is the *richer* one, and
carries exactly the fields R5 identifies as the biggest legibility win.

Both entry points are affected: pointer and keyboard.

---

## R8 — Constitution applicability

| Artifact | Applies? | Why |
|---|---|---|
`ui/netclaw-visual/package.json` | **Yes** | The dependency bump itself |
Principle X (HUD first-class) | **Yes** | This *is* HUD work |
Principle XI (full-stack coherence) | **Partial** | No new MCP server, no new skill, no installable component. No new capability counts to reconcile |
`scripts/reconcile-mcp.py` | **Yes — must run** | CLAUDE.md mandates it before push; CI fails on non-zero. Expected to be unaffected, but "expected" is not "verified" |
Principle XII (docs-as-code) | **Yes** | `ui/netclaw-visual/README.md` documents the renderer/post-processing stack |
`THIRD_PARTY_NOTICES.md` | **Check** | Already exists in `ui/netclaw-visual/`; a three.js version reference may need updating |
Principle XVII (milestone post) | Deferred | Drafted at completion, **offered never published** (Principle XIV) |
`.env.example` | No | No new environment variable |

**Not applicable**: no device interaction, no vendor logic, no new MCP server, no credential
surface.
