# Implementation Plan: Three.js Browser Network Topology Visualization

**Branch**: `046-threejs-network-viz` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/046-threejs-network-viz/spec.md`

## Summary

A new NetClaw skill (`workspace/skills/threejs-network-viz/`) that composes topology data from any of NetClaw's existing topology-source integrations (or a freeform description), assembles it into a canonical topology model, lays it out in 3D space, and renders it into a single self-contained HTML file embedding Three.js — devices as `THREE.Group` hierarchies with interfaces as true child objects, links as `TubeGeometry` cables anchored to interface world positions, procedural shapes by default with an optional CC0-verified real-3D-model "stencil" mode sourced primarily from Sketchfab (via the newly vendored `sketchfab-mcp-server`), labels/legend, and state-based coloring. The file is written to a persistent, timestamped location in NetClaw's workspace output directory and opened directly in the engineer's browser — no build step, no server process, no desktop application, replacing that exact friction in the UE5 (`044-ue5-mcp-network-viz`, `045-ue5-digital-twin`) and Blender (`024-blender-3d-viz`) skills.

## Technical Context

**Language/Version**: Python 3.10+ (skill logic, consistent with the rest of NetClaw)
**Primary Dependencies**: Three.js **r147 pinned** (`three@0.147.0` — the last release shipping both a classic global/UMD `build/three.js` core and non-module `examples/js/controls/OrbitControls.js` / `examples/js/loaders/GLTFLoader.js` addons; see research.md §1–2) vendored as static JS, not npm-installed into the skill itself, so it can be inlined into a `file://`-safe single HTML output, the newly vendored community `sketchfab-mcp-server` (Node.js, `mcp-servers/sketchfab-mcp-server/`, registered as `sketchfab-mcp` in `config/openclaw.json`) for real-stencil model search/download, and NetClaw's existing topology-source skills/MCP servers (CML lab tooling, `gns3-mcp-server`, `clab-mcp-server`, `eve-ng-mcp-server`, `nautobot-mcp-v2`, `netbox-mcp-server`, `infrahub-mcp`, `ipfabric` integration, `forward-mcp`) consumed as-is, not modified
**Storage**: N/A for rendering itself; generated visualizations are written as timestamped, uniquely-named `.html` files to a persistent NetClaw workspace output directory (per Clarification session 2026-07-05) — never overwritten, never ephemeral
**Testing**: pytest — unit tests for topology-model assembly, layout/centering, role/state color mapping, and the CC0 license-verification/fallback logic (sketchfab-mcp calls mocked); a small number of live integration tests against at least one real topology-source MCP (e.g., GNS3 or CML) that assert on the structure of the generated HTML/embedded topology JSON, following the live-test-over-mock convention already established in `tests/integration/test_ue5_mcp.py`
**Target Platform**: Any modern desktop browser (Chrome/Firefox/Edge) on the engineer's own machine; skill logic runs wherever NetClaw itself runs (WSL2/Linux)
**Project Type**: Single new skill (no new NetClaw-authored MCP server); one new vendored third-party community MCP server (`sketchfab-mcp-server`) for the optional real-stencil enhancement only
**Performance Goals**: End-to-end "ask → open in browser" under 30 seconds for a typical lab-sized topology (SC-001); rendered scene interactive at standard 60fps browser rendering rates once open
**Constraints**: The delivered file MUST remain a single self-contained artifact with zero external file references in both procedural and real-stencil modes (FR-001, FR-019) — Three.js, its addons, and any fetched glTF/GLB model data are all inlined into the one HTML file; real-stencil mode MUST reject any Sketchfab candidate model whose verified license isn't CC0 (FR-019a) rather than trusting catalog-level "downloadable" filtering alone
**Scale/Scope**: Comfortably renders a typical lab/campus topology (tens of devices, hundreds of interfaces — same order of magnitude as the ~200 device / ~500 link ceiling already assumed by 044/045); extreme-scale topologies are explicitly out of scope per spec.md Assumptions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | Purely read-only visualization; no device configuration is ever changed |
| II. Read-Before-Write | N/A | No device writes occur anywhere in this feature |
| III. ITSM-Gated Changes | N/A | No production device changes; visualization only |
| IV. Immutable Audit Trail | PASS | Reuses existing GAIT logging for skill invocations; no new audit mechanism needed |
| V. MCP-Native Integration | PASS | Composes exclusively through existing topology-source MCP servers plus the newly-registered `sketchfab-mcp` server (proper MCP registration in `config/openclaw.json`, not a bespoke HTTP call) |
| VI. Multi-Vendor Neutrality | PASS | Rendering/layout logic is vendor-neutral; all vendor-specific topology retrieval stays inside each source's own existing MCP server |
| VII. Skill Modularity | PASS | One new skill (`threejs-network-viz`) with focused internal modules; composes existing source-skills rather than duplicating their retrieval logic |
| VIII. Verify After Every Change | N/A | No device changes to verify; acceptance is via spec.md's scenarios |
| IX. Security by Default | PASS (flagged) | `SKETCHFAB_API_KEY` is scoped to Sketchfab only, least-privilege, never exposed to device-facing code; note: the vendored `sketchfab-mcp-server`'s own `npm audit` reports vulnerabilities in its dev/build dependencies (tracked for Polish-phase review, not blocking since it's an isolated, sandboxed, read/download-only third-party process) |
| X. Observability | **REQUIRED** | Failure/fallback conditions (unreachable source, ambiguous source, no permitted real-stencil model) are always explicitly reported (FR-013, FR-021) rather than silent; additionally, per this principle, `ui/netclaw-visual/` (NetClaw's existing MCP-status HUD) MUST gain a status node for the new `sketchfab-mcp` integration |
| XI. Full-Stack Artifact Coherence | **REQUIRED** | `README.md`, `SOUL.md`, `TOOLS.md`, `scripts/install.sh` (clone+build step for `sketchfab-mcp-server`), `ui/netclaw-visual/` HUD node, and `workspace/skills/threejs-network-viz/SKILL.md` all need updates — see checklist below |
| XII. Documentation-as-Code | **REQUIRED** | New `SKILL.md` must document purpose, composed sources, real-stencil mode, and the `SKETCHFAB_API_KEY`/`SKETCHFAB_USERNAME` environment variables |
| XIII. Credential Safety | PASS | `SKETCHFAB_API_KEY`/`SKETCHFAB_USERNAME` already added to local `.env` (gitignored) only; `.env.example` documents variable names with no values; nothing hardcoded in source |
| XIV. Human-in-the-Loop | N/A | No external communications (Slack/ServiceNow/GitHub/etc.) triggered by this feature |
| XV. Backwards Compatibility | PASS | New, additive skill; existing `ue5-network-viz` and `blender-3d-viz` skills are untouched and remain available |
| XVI. Spec-Driven Development | PASS | Following the full specify → clarify → plan → tasks → implement workflow |
| XVII. Milestone Documentation | **REQUIRED** | WordPress blog post after implementation, per constitution and prior practice (044/045) |

**Gate Status**: PASS — no violations requiring justification. Observability (X), Artifact Coherence (XI), Documentation (XII), and Milestone Documentation (XVII) requirements are tracked for the Polish phase, matching how 044/045 handled the same conditional-pass pattern.

## Project Structure

### Documentation (this feature)

```text
specs/046-threejs-network-viz/
├── plan.md               # This file (/speckit.plan command output)
├── research.md           # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md         # Phase 1 output (/speckit.plan command)
├── contracts/            # Phase 1 output (/speckit.plan command)
│   └── topology-scene-contract.md
├── checklists/
│   └── requirements.md   # Spec quality checklist
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created here)
```

### Source Code (repository root)

```text
# New skill (single project, no new NetClaw-authored MCP server)
workspace/skills/threejs-network-viz/
├── SKILL.md              # NEW - purpose, composed sources, real-stencil mode, env vars
├── topology_model.py     # NEW - Device/Interface/Link/TopologySnapshot canonical dataclasses
├── layout.py             # NEW - force-directed layout + centroid-centering, ported/adapted from
│                          #       ue5-network-viz/layout.py's proven ForceDirectedLayout (already
│                          #       engine-agnostic Vector3 math) rather than re-derived from scratch
├── materials.py           # NEW - role-based and state-based color tables + hostname-based device-type
│                           #       inference, ported/adapted from ue5-network-viz/materials.py
├── sources.py               # NEW - adapters: each topology-source skill/MCP's native output (and
│                             #       freeform conversational input) -> topology_model.TopologySnapshot
├── assets.py                 # NEW - real-stencil resolution chain: existing-asset check -> sketchfab-mcp
│                              #       search + per-model CC0 license verification (FR-019a) -> glTF/GLB
│                              #       download -> base64 embed -> procedural fallback + reporting (FR-021)
├── scene_builder.py           # NEW - builds the embedded topology JSON payload (device/interface/link/
│                               #       legend/state data) consumed by the HTML template's runtime JS
├── html_template.py            # NEW - renders the single self-contained HTML file: inlined Three.js
│                                #       UMD build + OrbitControls + GLTFLoader + runtime scene-construction
│                                #       JS + the embedded topology JSON payload
├── output.py                    # NEW - writes the timestamped HTML file to the persistent workspace
│                                 #       output directory (FR-023) and opens it in the default browser
└── vendor/
    └── three/                    # NEW - vendored static Three.js r160+ UMD build, OrbitControls.js,
                                   #       GLTFLoader.js (no npm/CDN dependency at render time)

# Vendored third-party community MCP server (not NetClaw-authored; gitignored per existing
# mcp-servers/* convention, same as other community MCPs already in this repo)
mcp-servers/sketchfab-mcp-server/   # ALREADY CLONED + BUILT this session (npm install && npm run build)

# Tests
tests/unit/
├── test_threejs_layout.py         # NEW - centering/scale correctness across varied coordinate ranges
├── test_threejs_materials.py      # NEW - role/state color mapping, hostname device-type inference
├── test_threejs_assets.py         # NEW - CC0 verification + fallback logic (sketchfab-mcp calls mocked)
└── test_threejs_scene_builder.py  # NEW - topology JSON payload structure, parent-child attachment

tests/integration/
└── test_threejs_network_viz.py    # NEW - live end-to-end generation against at least one real
                                    #        topology-source MCP; structural assertions on output HTML

# Documentation/config touched (per Artifact Coherence Checklist below)
README.md, SOUL.md, TOOLS.md, scripts/install.sh, ui/netclaw-visual/, .env.example, config/openclaw.json
```

**Structure Decision**: Single new skill, no new NetClaw-authored MCP server. All rendering/layout/asset-resolution logic lives inside `workspace/skills/threejs-network-viz/` as focused modules mirroring the pattern already established by `ue5-network-viz/` (separate `layout.py`, `materials.py`, module-per-responsibility), per Constitution Principle VII. The one new external dependency is the vendored, third-party `sketchfab-mcp-server`, already cloned, built, and registered this session — it is used strictly as an MCP tool call from `assets.py`, never modified.

## Artifact Coherence Checklist

Per Constitution Principle XI, these artifacts MUST be updated when implementation completes:

| Artifact | Action | Description |
|----------|--------|-------------|
| `workspace/skills/threejs-network-viz/SKILL.md` | CREATE | Document purpose, all composed topology sources, freeform input, real-stencil mode and its CC0 policy, and required env vars |
| `README.md` | MODIFY | Add the new skill's capability description; note it as the recommended browser-based alternative to the UE5/Blender skills |
| `SOUL.md` | MODIFY | Add the `threejs-network-viz` skill entry |
| `TOOLS.md` | MODIFY | Note the new `sketchfab-mcp` integration entry (tools, env vars, transport) |
| `scripts/install.sh` | MODIFY | Add a clone+`npm install`+`npm run build` step for `mcp-servers/sketchfab-mcp-server/`, matching the pattern used for other vendored community MCP servers |
| `ui/netclaw-visual/` | MODIFY | Add a HUD status node for the new `sketchfab-mcp` integration (Constitution Principle X) |
| `.env.example` | DONE | `SKETCHFAB_API_KEY`/`SKETCHFAB_USERNAME` placeholders already added this session |
| `config/openclaw.json` | DONE | `sketchfab-mcp` server registration already added this session |
| `mcp-servers/sketchfab-mcp-server/` | DONE | Already cloned and built this session |

## Implementation Phases

Phases map to the spec's P1–P5 priority ordering so each phase is an independently demonstrable checkpoint, per spec.md's story structure.

### Phase 1: Core Rendering Foundation (P1)

**Goal**: A live-sourced topology renders as a correctly-structured, labeled, navigable, centered single-file 3D scene — the entire MVP value proposition.

**Tasks**:
1. `topology_model.py`: define `Device`, `Interface`, `Link`, `TopologySnapshot` dataclasses (FR-002–FR-005 attributes, plus the metadata fields agreed in Clarifications: arbitrary source-exposed metadata, excluding credentials/config).
2. `layout.py`: port/adapt `ue5-network-viz/layout.py`'s `ForceDirectedLayout` and centroid-centering fix into an engine-agnostic 3D layout producing positions for `topology_model` objects (FR-008).
3. `materials.py`: port/adapt `ue5-network-viz/materials.py`'s `infer_device_type` and device-type color table; add a state-color table (FR-016, FR-017).
4. `scene_builder.py`: build the embedded topology JSON payload — device groups with child interface entries and full (not partial) transform data per object (FR-003, FR-009), link entries carrying both endpoint interface references.
5. `html_template.py` + `vendor/three/`: single self-contained HTML template with inlined Three.js UMD build, `OrbitControls` (FR-007), a runtime JS engine that reads the embedded JSON and constructs `THREE.Group` device→interface hierarchies, `TubeGeometry`/`CatmullRomCurve3` link cables anchored via `getWorldPosition` on interface objects, procedural shape-by-role meshes, and Sprite/canvas-texture (or bundled troika-three-text) labels plus a legend built from the same color table `materials.py` uses (FR-002, FR-005, FR-006).
6. `output.py`: write the generated HTML to a timestamped, uniquely-named file under the persistent workspace output directory and open it in the default browser (FR-001, FR-023).
7. Unit tests: `test_threejs_layout.py` (centering/scale across varied/far-from-origin/inconsistent coordinate inputs), `test_threejs_scene_builder.py` (parent-child structure, full-transform data present).

**Deliverable**: Asking NetClaw to visualize one already-integrated live topology (e.g., a GNS3 or CML lab) produces a single HTML file that opens directly in a browser showing a correctly labeled, colored, centered, navigable scene with true interface-child attachment and interface-to-interface link wiring.

### Phase 2: Composable Sourcing (P2, P3)

**Goal**: The same renderer works identically regardless of topology origin — any supported live source, or a freeform description.

**Tasks**:
1. `sources.py`: one adapter per supported topology-source skill/MCP (CML, GNS3, containerlab, EVE-NG, Nautobot, NetBox/Infrahub, IP Fabric, Forward Networks), each mapping that source's native topology representation into `topology_model.TopologySnapshot` (FR-010, FR-011).
2. `sources.py`: ambiguous-source disambiguation logic — ask rather than guess when a request doesn't clearly name a source and more than one applies (FR-012); explicit unreachable/error reporting per source (FR-013).
3. `sources.py`: freeform-description parser producing the same `TopologySnapshot` shape, with clearly-indicated defaults for omitted role/interface-name details (FR-014, FR-015).
4. Integration test: `test_threejs_network_viz.py` generates a scene from at least one live source and, separately, from a freeform description, asserting both use identical rendering conventions.

**Deliverable**: "Replicate the CML lab topology" and "sketch me a topology with two routers and a switch" both produce equivalent-quality scenes.

### Phase 3: Real 3D Model Stencils (P5)

**Goal**: Optional real-stencil mode using CC0-verified Sketchfab models, embedded into the single-file output, with automatic graceful fallback.

**Tasks**:
1. `assets.py`: check-existing-asset step (project-local cache keyed by device role).
2. `assets.py`: Sketchfab search via `sketchfab-mcp` (`sketchfab-search` tool, `downloadable=true`), then `sketchfab-model-details` per candidate to read its actual license, accepting only verified-CC0 candidates (FR-019, FR-019a) — never trusting "downloadable" alone.
3. `assets.py`: download accepted model via `sketchfab-download` (glTF/GLB format), base64-encode it, and hand it to `html_template.py` for direct embedding via `GLTFLoader`'s data-URI loading path — never a separate linked file (FR-001, FR-019).
4. `assets.py`: automatic fallback to the procedural shape for any device role with no verified-CC0 candidate, plus a structured fallback report surfaced to the engineer (FR-021).
5. `assets.py`: explicit non-scraping guarantee for gated marketplaces (Fab, TurboSquid, CGTrader, GrabCAD) — check-user-supplied-asset-only path, never an automated fetch attempt (FR-020).
6. Unit tests: `test_threejs_assets.py` with `sketchfab-mcp` calls mocked — verified-CC0 acceptance, non-CC0 rejection, unreachable-source fallback, gated-marketplace non-fetch behavior.

**Deliverable**: Enabling real-stencil mode on a topology with mixed model availability renders confirmed-CC0 Sketchfab models where resolved and clean procedural fallbacks everywhere else, with a clear fallback report — all still inside one self-contained file.

### Phase 4: State Coloring Polish (P4)

**Goal**: Device/link operational state is visually distinguishable and legend-explained.

**Tasks**:
1. `materials.py` / `scene_builder.py`: apply state-color overlay (healthy/degraded/down) on top of role coloring when state data is present; neutral default otherwise (FR-016, FR-017).
2. `html_template.py`: extend the legend to explain state colors alongside role colors.
3. Unit test coverage folded into `test_threejs_materials.py`.

**Deliverable**: A topology with a mix of healthy/degraded/down elements is visually triageable by color alone, matching SC-006.

### Phase 5: Polish & Documentation

**Goal**: Full Constitution artifact coherence and milestone documentation.

**Tasks**:
1. Write `workspace/skills/threejs-network-viz/SKILL.md`.
2. Update `README.md`, `SOUL.md`, `TOOLS.md` per the Artifact Coherence Checklist above.
3. Add the `sketchfab-mcp-server` clone+build step to `scripts/install.sh`.
4. Add a `sketchfab-mcp` status node to `ui/netclaw-visual/` (Constitution Principle X).
5. Run the full unit + live integration test suite.
6. Draft the WordPress milestone post (Constitution XVII).

## Testing Strategy

Unlike the UE5/Blender skills — which have no meaningful unit-testable surface independent of a running desktop engine — this feature's core logic (topology modeling, layout/centering, color mapping, asset-resolution fallback) is pure Python and fully unit-testable without any live dependency, so unit tests are the primary verification layer here. A smaller set of live integration tests cover the parts that genuinely require a real external system: at least one real topology-source MCP (structural assertions on the generated file, not visual/pixel verification) and, separately, mocked-not-live tests against `sketchfab-mcp` (a live Sketchfab-catalog dependency would make CC0-availability tests flaky and rate-limit-prone) — this mirrors 044/045's rule of never mocking the one thing that would make a bug silently pass, while still avoiding brittle tests against an external catalog's ever-changing contents.

## Complexity Tracking

*No entries — Constitution Check gate passed with no violations requiring justification.*
