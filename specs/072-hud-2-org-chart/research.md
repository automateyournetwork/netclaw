# Phase 0 Research: HUD 2.0 — Top-Down Trust Org Chart

Feature: `072-hud-2-org-chart` · Date: 2026-07-27

Resolves every NEEDS CLARIFICATION in the plan's Technical Context.

---

## R1. How is a *visual* specification tested when no JS test framework exists?

**Finding.** `ui/netclaw-visual/package.json` has four scripts (`dev`, `server`,
`build`, `preview`) and **no test framework** — no vitest, jest, playwright,
cypress or puppeteer. Every test in the repo is Python/pytest. The 13 success
criteria in this spec are largely perceptual ("identifiable within 2 seconds",
"distinguishable in greyscale", "located in under 5 seconds").

**Decision.** Split the feature into two testable halves, and make the split an
architectural requirement rather than a testing afterthought:

1. **Pure logic — unit tested, no browser, no GPU.** Category derivation, health
   classification, dedup, label fallback, ordering, and band/row position math
   are all pure functions of the `/api/n2n` payload. Extracted into modules that
   **import nothing from three.js**, they are testable as plain data-in/data-out.
   This covers the majority of the spec's falsifiable content: FR-006, 006a,
   006b, 008, 008a, 014, 015, 029a, 034, 034b.
2. **Perceptual / runtime — verified in a real browser.** Everything that only
   exists once pixels are drawn: FR-009a/b, 012, 013, 029b/c, 032, 033 and
   SC-001..013.

**Rationale.** Without this split, a WebGL scene is effectively untestable and
the 64 requirements degrade into "looks right to me". With it, the numeric and
structural requirements get real regression tests, and human judgement is
reserved for genuinely perceptual claims.

**Alternatives considered.**
- *Test through the rendered scene only* — rejected: slow, flaky, needs a GPU in
  CI, and cannot isolate a layout maths bug from a material bug.
- *Skip automated testing* — rejected: the spec makes falsifiable numeric claims
  (100 members, 60 fps, 900 s threshold, four states) that would silently rot.

---

## R2. Which test runner, given Constitution XV (dependency isolation)?

**Decision.** **Node's built-in `node:test`** (`node --test`), zero new
dependencies. Test files as `src/**/*.test.js`, run via a new
`"test": "node --test src/"` script.

**Rationale.** The pure-logic modules from R1 import nothing but plain JS, so
none of vitest's value (vite resolution, ESM/CJS interop, `three/addons`
aliasing, browser mode) is actually needed. Node 25 is installed and ships
`node:test` with ESM support. Constitution XV requires new dependencies to be
isolated and non-conflicting; the cheapest way to satisfy that is not to add
one. This also matches the repo's established stdlib-only tooling convention
(`scripts/*.py` are Python-stdlib only by policy).

**Alternatives considered.**
- *vitest* — the ecosystem default and better DX, and it would integrate with
  the existing vite 5 config. Rejected only because the code under test is
  deliberately dependency-free; adding a runner to test functions that import
  nothing is unjustified weight. **Revisit if** rendering-layer tests are ever
  wanted, where vite resolution would genuinely pay for itself.
- *pytest via a JS bridge* — rejected as absurd for this purpose.

---

## R3. How are the perceptual and performance criteria verified?

**Finding.** `chrome-devtools-mcp` is registered in the repo template
(`config/openclaw.json`, both headless and visible variants, from feature 048)
but is **not** in the live `~/.openclaw/openclaw.json`. It runs on demand via
`npx -y chrome-devtools-mcp@latest` with no install step.

**Decision.** Use it as the verification harness for the perceptual half:

| Criterion | Method |
|---|---|
| SC-007 greyscale | Screenshot, apply a greyscale filter, confirm four states remain separable |
| SC-007a fault-find < 5 s | Seeded fixture (1 FAULT among 25 COLD), human timing |
| SC-009 keyboard | Drive Tab/arrows/Enter, assert focus lands on every node |
| SC-010 reduced motion | Emulate `prefers-reduced-motion`, re-run SC-007 |
| SC-011 position stability | Capture node coordinates first frame vs last, diff |
| SC-013 60 fps / regression | DevTools performance trace at the FR-029 ceiling |

**Rationale.** It is already vendored, needs no new dependency, and gives
screenshots, CDP emulation (including `prefers-reduced-motion`) and performance
traces from one tool. Registering it live is a one-line config change and is
**not** required for the feature to ship — it is a developer-workflow step.

**Alternatives considered.** Playwright (a new dependency covering the same
ground); manual verification only (rejected — SC-011 and SC-013 are numeric and
would never actually be checked).

---

## R4. Synthetic fixtures — how are 100 members and first-run tested?

**Finding.** The live Border has 29 members, 4 peers and 2 edges. The spec
requires correctness at ~100 members / ~25 categories (FR-029) and on an empty
first-run install (FR-033). Neither state can be produced from live data, and
`SC-006` explicitly demands validation against Borders the code has never seen.

**Decision.** Commit synthetic `/api/n2n` fixtures under
`specs/072-hud-2-org-chart/fixtures/`: `empty.json` (no risk/members/peers),
`single.json` (1 member), `live-29.json` (a captured snapshot of today's real
Border), `scale-100.json` (100 members / ~25 categories), and
`uncategorised.json` (members matching no integration prefix). Pure-logic tests
run against all five; the dev server gains a documented way to serve a fixture
instead of live data.

**Rationale.** SC-006 is a product-generality claim and cannot be honoured by
testing one deployment. Fixtures make the claim falsifiable and let the 100-node
performance target be exercised before anyone has that many claws.

**Alternatives considered.** Generating members procedurally at runtime
(rejected — FR-033c forbids synthetic topologies reaching the real UI, and a
fixture file is easier to reason about than a generator).

---

## R5. Does removing the scene populations break the panel? (FR-030d)

**Finding — confirmed by reading the source, not assumed.** `renderSidebar(graph)`
and `renderMetrics(graph)` both consume the `/api/graph` payload, and
`fetchGraph()` supplies it. FR-030 removes the *scene objects* built from that
payload (`buildIntegrations`, `buildDevices`, `createSkillSprites`,
`computeDendritePositions`, `createDendriteMaterial`, `lightIntegration`,
`lightDevice`) but the payload itself still has consumers.

**Decision.** Keep `fetchGraph()` and the `/api/graph` request. Delete only the
scene-construction functions and the integration/device branches of
`applyFilters()`. `state.integrations` and `state.devices` must be re-examined
individually: any field still read by a retained panel renderer stays.

**Rationale.** This is the highest-risk part of a hard replace — deleting a
fetch whose data a panel still needs would breach FR-017/FR-018 and only surface
at runtime. Making it an explicit, verified step rather than an assumption.

---

## R6. Layout algorithm

**Decision.** Deterministic banded row-packing. Three fixed bands on the XY
plane (external / border / internal); the internal band packs category columns
left→right, wrapping to a new row when width is exceeded; members stack
vertically within their column. Order is computed **once** per session (FR-034).
No force simulation, no tidy-tree.

**Rationale.** The graph is depth-2 by construction (Border → category →
member) — every member is depth-1 from the Border, as measured in the spec.
Reingold–Tilford and force-directed layouts both solve problems this graph does
not have, and force simulation would actively violate FR-034's position
stability.

**Alternatives considered.** `d3-hierarchy` (a new dependency for a tree that is
two levels deep); force-directed (non-deterministic, contradicts FR-034).

---

## R7. Camera model (FR-012 / FR-013)

**Decision.** `THREE.OrthographicCamera` with `OrbitControls` configured as
`enableRotate = false`, pan and zoom retained, and zoom clamped. The existing
`CSS2DRenderer` label layer is kept and doubles as the accessibility DOM overlay
required by FR-032.

**Rationale.** Orthographic makes equal-tier siblings render at equal size,
which is the property that makes a chart read as a chart (FR-013), and it
removes the perspective foreshortening that currently makes the far side of the
orbit unreadable. `OrbitControls` is already imported and supports rotation
lockout, so no control library is added or replaced.

**Alternatives considered.** Perspective with compensating per-tier scale
(FR-013's fallback — more maths, worse result); `MapControls` (a second control
addon for behaviour `OrbitControls` already provides).

---

## R8. `prefers-reduced-motion` vs the four-state encoding (FR-032c)

**Decision.** Motion is a **redundant** channel, never a load-bearing one. Each
of HOT/WARM/COLD/FAULT is separable by form and colour temperature alone; motion
is added on top for HOT and FAULT only. Under reduced motion, animation is
suppressed and the encoding is unaffected.

**Rationale.** FR-009a asks for multi-channel encoding and FR-032c requires the
encoding to survive motion suppression. The only way to satisfy both is for
motion to be additive. Designing it as redundant from the start also means
SC-007 (greyscale) and SC-010 (reduced motion) test the same underlying
property rather than two separate mechanisms.

---

## Resolved unknowns

| Unknown | Resolution |
|---|---|
| Testing approach for a visual feature | R1 — pure/perceptual split, made architectural |
| Test runner | R2 — `node:test`, zero new dependencies |
| Perceptual + perf verification | R3 — `chrome-devtools-mcp`, already vendored |
| Fixtures for scale and first-run | R4 — five committed `/api/n2n` fixtures |
| Panel breakage risk from FR-030 | R5 — keep `fetchGraph()`, delete scene builders only |
| Layout algorithm | R6 — deterministic banded row-packing |
| Camera | R7 — orthographic, rotation disabled |
| Reduced motion vs health encoding | R8 — motion is redundant, never load-bearing |

**No NEEDS CLARIFICATION remain.**
