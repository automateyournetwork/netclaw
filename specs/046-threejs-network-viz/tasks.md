# Tasks: Three.js Browser Network Topology Visualization

**Input**: Design documents from `/specs/046-threejs-network-viz/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan.md's Testing Strategy explicitly calls for unit tests on the core Python logic and live integration tests on topology-source composition.

**Organization**: Tasks are grouped by user story (spec.md's P1–P5) so each story is independently implementable, testable, and demonstrable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependency)
- **[Story]**: US1–US5, mapping to spec.md's five prioritized user stories
- All file paths are exact and relative to the repo root

---

## Phase 1: Setup

**Purpose**: Skill skeleton and vendored assets needed before any story-specific code exists

- [X] T001 Create the skill package skeleton at `workspace/skills/threejs-network-viz/__init__.py` (empty package marker; the top-level orchestration entry point is added in Phase 3, T014)
- [X] T002 [P] Fetch and commit Three.js **r147** (`three@0.147.0`) `build/three.js` into `workspace/skills/threejs-network-viz/vendor/three/build/three.js` (research.md §1 — the last release with a working classic global/UMD build)
- [X] T003 [P] Fetch and commit the same r147 release's `examples/js/controls/OrbitControls.js` and `examples/js/loaders/GLTFLoader.js` into `workspace/skills/threejs-network-viz/vendor/three/examples/js/` (research.md §2 — must be the same release as T002 to avoid API drift)
- [X] T004 [P] Create the persistent workspace output directory `workspace/output/threejs-network-viz/` (with a `.gitkeep`) that `output.py` will write timestamped scene files into (FR-023, Clarification session 2026-07-05)

**Checkpoint**: Package skeleton exists; Three.js r147 core + addons are vendored and available for the runtime JS template.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Canonical data model, layout, coloring, and output-writing logic that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Implement `Vector3`, `Device`, `Interface`, `Link`, `LinkEndpoint`, `TopologySnapshot`, `DeviceAsset`, `FallbackNote` dataclasses in `workspace/skills/threejs-network-viz/topology_model.py`, matching data-model.md's fields and validation rules exactly
- [X] T006 [P] Port `ForceDirectedLayout` and its centroid-centering fix from `workspace/skills/ue5-network-viz/layout.py` into `workspace/skills/threejs-network-viz/layout.py`, adapted to operate on `topology_model.py`'s `Device`/`Link`/`Vector3` types (research.md §4, FR-008) — depends on T005
- [X] T007 [P] Port `infer_device_type` and the role-based `DEVICE_TYPE_COLORS` table from `workspace/skills/ue5-network-viz/materials.py` into `workspace/skills/threejs-network-viz/materials.py` (FR-002) — depends on T005 (state-based coloring is added later in US4, not here)
- [X] T008 Implement `write_scene(html: str, snapshot_id: str) -> Path` and `open_in_browser(path: Path) -> None` in `workspace/skills/threejs-network-viz/output.py` per contracts/topology-scene-contract.md (FR-001, FR-023) — depends on T004

**Checkpoint**: Canonical model, layout, base coloring, and file-delivery primitives all exist and are independently unit-testable. User story implementation can now begin.

---

## Phase 3: User Story 1 - View a Live Topology as an Interactive 3D Scene (Priority: P1) 🎯 MVP

**Goal**: Ask NetClaw to visualize one already-integrated live topology (using the spec's own worked example, a CML lab) and get a single, self-contained, correctly labeled/colored/centered, navigable 3D scene, opened directly in the browser.

**Independent Test**: Request a visualization of a real CML lab topology; confirm a `.html` file opens automatically with every device/interface/link visible, labeled, colored by role, explained by a legend, centered/scaled correctly, and navigable via mouse (rotate/pan/zoom), with interfaces remaining attached when a device is repositioned.

### Tests for User Story 1

- [X] T009 [P] [US1] Unit test centering/scale correctness across varied and far-from-origin coordinate ranges in `tests/unit/test_threejs_layout.py`
- [X] T010 [P] [US1] Unit test the embedded topology JSON payload structure — full per-object transforms, interface-as-child nesting, link endpoint references — in `tests/unit/test_threejs_scene_builder.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement a minimal `from_cml(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py`, sufficient to demonstrate Story 1 end-to-end (FR-010 partial; the remaining seven source adapters and source-selection logic are completed in User Story 2)
- [X] T012 [US1] Implement `scene_builder.py`: build the embedded topology JSON payload — device entries with nested interface children and complete (never partial) transform data, link entries referencing both endpoints, and a legend generated from `materials.py`'s color table (contracts/topology-scene-contract.md; FR-003, FR-005, FR-006, FR-009) — depends on T005, T006, T007
- [X] T013 [US1] Implement `html_template.py`: the single self-contained HTML template inlining the vendored Three.js r147 core, `OrbitControls`, and `GLTFLoader` (T002, T003), plus a runtime JS engine that reads the embedded JSON payload and constructs `THREE.Group` device→interface hierarchies, `TubeGeometry`/`CatmullRomCurve3` link cables anchored via `getWorldPosition()` on interface objects, procedural `BoxGeometry`/`CylinderGeometry`/`ExtrudeGeometry` shapes by role, canvas-texture/Sprite labels, `OrbitControls` navigation, and the legend (FR-002, FR-004, FR-005, FR-006, FR-007) — depends on T012
- [X] T014 [US1] Implement the top-level orchestration entry point `visualize_topology(request) -> Path` in `workspace/skills/threejs-network-viz/__init__.py`, wiring `sources.py` → `layout.py` → `materials.py` → `scene_builder.py` → `html_template.py` → `output.py` (real-stencil resolution via `assets.py` is wired in later, in User Story 5) — depends on T011, T013, T008
- [X] T015 [US1] Write the initial `workspace/skills/threejs-network-viz/SKILL.md` covering Story 1's invocation and workflow (finalized with all stories in the Polish phase)
- [X] T016 [US1] Live integration test: generate a scene from a real CML lab and assert structural correctness (device/interface/link counts, legend presence, centered coordinate bounds) in `tests/integration/test_threejs_network_viz.py` — depends on T014

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Compose Topology Data From Any Supported Source (Priority: P2)

**Goal**: The same renderer produces equivalent-quality scenes regardless of which supported topology-source integration supplied the data.

**Independent Test**: Request visualizations sourced from at least two different integrations (e.g., CML and Nautobot) and confirm both produce correctly rendered scenes using identical shape/color/label/legend conventions.

### Implementation for User Story 2

- [X] T017 [US2] Implement `from_gns3(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T018 [US2] Implement `from_containerlab(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T019 [US2] Implement `from_eve_ng(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T020 [US2] Implement `from_nautobot(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T021 [US2] Implement `from_netbox_infrahub(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T022 [US2] Implement `from_ip_fabric(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T023 [US2] Implement `from_forward_networks(raw_topology: dict) -> TopologySnapshot` adapter in `workspace/skills/threejs-network-viz/sources.py` (FR-010) — depends on T005
- [X] T024 [US2] Implement `resolve_source(request_text: str, available_sources: list[str]) -> str | AmbiguousSourceError` disambiguation logic in `workspace/skills/threejs-network-viz/sources.py` and wire it into `visualize_topology()` in `__init__.py` (FR-012) — depends on T017–T023, T014
- [X] T025 [US2] Implement `SourceUnreachableError` and consistent unreachable/error reporting across all `sources.py` adapters, surfaced verbatim by `visualize_topology()` rather than producing a partial scene (FR-013) — depends on T017–T023
- [X] T026 [P] [US2] Live integration test: generate scenes from two different real topology sources and assert they use identical rendering conventions, in `tests/integration/test_threejs_network_viz.py` — depends on T024

**Checkpoint**: User Stories 1 and 2 both work independently — visualization now works from any of the 8 supported live sources.

---

## Phase 5: User Story 3 - Sketch a Freeform Topology Without a Live Source (Priority: P3)

**Goal**: A plain-language topology description (no live source) produces the same quality of rendered scene as a live-sourced one.

**Independent Test**: Describe a small topology in plain language and confirm a correctly rendered, labeled scene results, with reasonable defaults clearly indicated for any omitted details.

### Implementation for User Story 3

- [X] T027 [US3] Implement `from_freeform(description: str) -> TopologySnapshot` in `workspace/skills/threejs-network-viz/sources.py`, producing `source_kind="freeform"` snapshots (FR-014) — depends on T005
- [X] T028 [US3] Implement clearly-indicated default substitution (generic role, generated interface name) for details omitted from a freeform description, recorded in the affected `Device`/`Interface`'s `metadata` (FR-015) — depends on T027
- [X] T029 [P] [US3] Integration test: a freeform description produces a scene using identical shape/color/label/legend conventions to a live-sourced one, in `tests/integration/test_threejs_network_viz.py` — depends on T028

**Checkpoint**: User Stories 1–3 all work independently — the skill now works with or without a live source.

---

## Phase 6: User Story 4 - See Device and Link Health Through Color (Priority: P4)

**Goal**: Known operational state (healthy/degraded/down) is visually distinguishable through color and explained by the legend, on top of base role coloring.

**Independent Test**: Visualize a topology with at least one down/degraded device or link and confirm it's visually distinguishable from healthy elements, with the legend explaining the distinction; confirm elements with no state data show the neutral default.

### Implementation for User Story 4

- [X] T030 [US4] Add a state-color table (`healthy`, `degraded`, `down`, neutral default for `unknown`/`None`) to `workspace/skills/threejs-network-viz/materials.py` (FR-016, FR-017) — depends on T007
- [X] T031 [US4] Apply the state-color overlay to device and link entries in `scene_builder.py`'s JSON payload, defaulting to the neutral appearance when state is absent (FR-016, FR-017) — depends on T030, T012
- [X] T032 [US4] Extend the legend generation in `scene_builder.py`/`html_template.py` to explain state colors alongside role colors (FR-016) — depends on T031, T013
- [X] T033 [P] [US4] Unit test state-color mapping and neutral-default fallback behavior in `tests/unit/test_threejs_materials.py` — depends on T030

**Checkpoint**: User Stories 1–4 all work independently — health state is now visually triageable.

---

## Phase 7: User Story 5 - Use Real 3D Device Models Instead of Shapes (Priority: P5)

**Goal**: An opt-in real-stencil mode renders CC0-verified Sketchfab models where available, with automatic, reported fallback to procedural shapes elsewhere — all still inside a single self-contained file.

**Independent Test**: Enable real-stencil mode on a topology with mixed model availability; confirm resolvable roles render real geometry, everything else falls back cleanly with a reported reason, and gated marketplaces are never auto-fetched from.

### Implementation for User Story 5

- [X] T034 [US5] Implement `check_cached_asset(role: str) -> DeviceAsset | None` in `workspace/skills/threejs-network-viz/assets.py`
- [X] T035 [US5] Implement `search_sketchfab_cc0(role: str) -> SketchfabModelRef | None` calling the `sketchfab-mcp` server's `sketchfab-search` tool (`downloadable: true`) in `workspace/skills/threejs-network-viz/assets.py` (contracts/topology-scene-contract.md)
- [X] T036 [US5] Implement `verify_cc0_license(model_uid: str) -> bool` calling `sketchfab-mcp`'s `sketchfab-model-details` tool, accepting only an exact `license.slug == "cc0"` match (research.md §3, FR-019a) — depends on T035
- [X] T037 [US5] Implement `download_and_embed(model_uid: str, fmt="glb") -> str` calling `sketchfab-mcp`'s `sketchfab-download` tool and base64-encoding the result in `workspace/skills/threejs-network-viz/assets.py` (FR-001, FR-019) — depends on T036
- [X] T038 [US5] Implement `resolve_device_asset(role: str, real_stencil_mode: bool) -> DeviceAsset` orchestrating check-cache → search → verify → download-and-embed → procedural fallback, appending a `FallbackNote` on any non-success path (FR-021) — depends on T034, T036, T037
- [X] T039 [US5] Implement the gated-marketplace verify-only path (Fab, TurboSquid, CGTrader, GrabCAD): check only for a user-supplied local asset, never issue an automated fetch, in `workspace/skills/threejs-network-viz/assets.py` (FR-020) — depends on T038
- [X] T040 [US5] Extend `html_template.py`'s runtime JS to base64-decode an embedded glTF/GLB payload and call `GLTFLoader.parse(arrayBuffer, '', onLoad, onError)` for any `real_model` `DeviceAsset` entry, with no `fetch`/XHR call (research.md §2) — depends on T013, T038
- [X] T041 [US5] Wire `resolve_device_asset()` into `visualize_topology()` in `__init__.py`, gated by a real-stencil-mode request flag — depends on T038, T014
- [X] T042 [P] [US5] Unit test CC0 acceptance/rejection, fallback reasons, and gated-marketplace non-fetch behavior with `sketchfab-mcp` calls mocked, in `tests/unit/test_threejs_assets.py` — depends on T038, T039

**Checkpoint**: All five user stories work independently — the feature is functionally complete per spec.md.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Full Constitution Principle XI artifact coherence and milestone documentation

- [X] T043 [P] Finalize `workspace/skills/threejs-network-viz/SKILL.md` documenting all five stories, every composed topology source, the real-stencil CC0 policy, and the `SKETCHFAB_API_KEY`/`SKETCHFAB_USERNAME` environment variables
- [X] T044 [P] Update `README.md` with the new skill's capability description, positioned as the recommended browser-based alternative to the UE5/Blender skills
- [X] T045 [P] Update `SOUL.md` with the `threejs-network-viz` skill entry
- [X] T046 [P] Update `TOOLS.md` with the `sketchfab-mcp` integration entry (tools, env vars, transport)
- [X] T047 Add a `mcp-servers/sketchfab-mcp-server` clone + `npm install` + `npm run build` step to `scripts/install.sh`, matching the pattern used for other vendored community MCP servers
- [X] T048 Add a `sketchfab-mcp` status node to `ui/netclaw-visual/` (Constitution Principle X)
- [X] T049 Run the full unit (`tests/unit/test_threejs_*.py`) and live integration (`tests/integration/test_threejs_network_viz.py`) suite and resolve any failures
- [X] T050 Execute quickstart.md's full Development Loop (steps 1–5) end-to-end as final validation, including the "open with no network access" real-stencil embedding check
- [X] T051 Draft the WordPress milestone blog post per Constitution Principle XVII and present it for review before publishing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T004 specifically for T008) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational; extends `sources.py` alongside US1's `from_cml` but is independently testable once its own tasks land
- **User Story 3 (Phase 5)**: Depends on Foundational; independent of US2's live-source adapters
- **User Story 4 (Phase 6)**: Depends on Foundational and on US1's `scene_builder.py`/`html_template.py` existing (T012, T013) to extend
- **User Story 5 (Phase 7)**: Depends on Foundational and on US1's `html_template.py` (T013) and orchestration entry point (T014) to extend
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests are written alongside/before their story's implementation tasks per the checklist above
- Data model → layout/materials → scene assembly → HTML template → orchestration wiring, in that order
- Each story's Checkpoint marks a fully independently-testable increment

### Parallel Opportunities

- T002, T003, T004 (Setup) can run in parallel
- T005, T006, T007 (Foundational) can run in parallel once T005 lands (T006/T007 both depend only on T005, not each other)
- T009, T010 (US1 tests) can run in parallel
- T017–T023 (US2's seven remaining source adapters) touch the same file (`sources.py`) and are NOT marked `[P]` for that reason, but are otherwise logically independent and can be split across contributors sequentially without cross-task coupling
- Once Foundational (Phase 2) is complete, US2 and US3 can be staffed in parallel with each other (both extend `sources.py` but add distinct, non-overlapping functions); US4 and US5 must wait on US1's `scene_builder.py`/`html_template.py` (T012, T013) specifically, not on US2/US3

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "Unit test centering/scale correctness in tests/unit/test_threejs_layout.py"
Task: "Unit test topology JSON payload structure in tests/unit/test_threejs_scene_builder.py"
```

## Parallel Example: Foundational Phase

```bash
# After T005 (topology_model.py) lands, launch these together:
Task: "Port ForceDirectedLayout into workspace/skills/threejs-network-viz/layout.py"
Task: "Port infer_device_type + DEVICE_TYPE_COLORS into workspace/skills/threejs-network-viz/materials.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: ask NetClaw to visualize a real CML lab; confirm the single-file scene opens, is fully labeled/colored/centered, and is navigable
5. This is the demonstrable MVP — replaces the core UE5/Blender friction with zero new source-adapter or asset work

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate → MVP demo (a browser-based CML topology, no server/build/desktop app)
3. User Story 2 → validate → now works from any of the 8 supported sources
4. User Story 3 → validate → now works with no live source at all
5. User Story 4 → validate → health state is now visually triageable
6. User Story 5 → validate → optional real-stencil visual richness, still zero-server/single-file
7. Polish → full Constitution artifact coherence + milestone blog post

### Suggested MVP Scope

**User Story 1 alone** is the MVP: it independently delivers the entire "ask NetClaw, get a browser-based 3D topology, no install/build/server" value proposition using the spec's own worked example (a CML lab). Stories 2–5 are additive quality/breadth improvements, not required for the core promise to be true.

---

## Notes

- [P] tasks touch different files with no unmet dependency
- [Story] labels map every user-story-phase task back to spec.md's US1–US5 for traceability
- `sources.py`, `materials.py`, and `assets.py` are each touched by more than one story — this is expected (multiple distinct functions in one file) and is called out explicitly wherever it affects parallelization
- Commit after each task or logical group; stop at any Checkpoint to validate a story independently before continuing
- Avoid: vague tasks, same-function edits from two stories, or a later story silently changing an earlier story's already-validated behavior
