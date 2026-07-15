# Tasks: Unreal Engine 5.8 MCP Network Visualization

**Input**: Design documents from `/specs/044-ue5-mcp-network-viz/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md

**Status (2026-07-03)**: 63/67 tasks complete. Implementation was validated far more heavily than the original task list anticipated — a real multi-day incident (host instability, then live CML+pyATS→UE5 rebuilds against two different UE5 8.0 builds) forced extensive live debugging that the plan's integration-test scope didn't originally call for. See `workspace/skills/ue5-network-viz/SKILL.md`'s "Critical Conventions" / "Build-Specific Gotchas" sections for the full incident log — several real bugs (wrong tool-name calling convention, SSE keep-alive hangs, `set_actor_transform` not preserving omitted fields, topology centering, a `_StrictDict` gotcha, a `find_actors` string-response case) were found and fixed this way, not via the originally-planned automated suite. The 4 remaining open items are honest gaps, not oversights:
- **T062** (automated pytest run against live UE5): `pytest-asyncio` isn't installed in this environment, so the async tests in `test_ue5_mcp.py` are currently skipped rather than run. Manual live validation substituted for this extensively (full 10-device/12-link CML+pyATS topology built, verified, and screenshotted against real UE5 sessions) but the automated suite itself has not been executed end-to-end.
- **T064** (fly-through smoothness): camera reframing/focus was validated live; a full fly-through animation was not specifically exercised this session.
- **T065** (live health-state color change on an existing actor): color-by-device-type was validated at build time; changing an already-spawned actor's color in response to a health-state transition was not specifically exercised live.
- **T066** (WordPress blog draft): not started — per Constitution Principle XVII this requires presenting a draft to the user for review before publishing, and hasn't been requested yet.

**Tests**: Integration tests against live UE5 MCP server are included per the implementation plan.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This feature creates skill definitions and configuration (no custom MCP server code):
- `workspace/skills/ue5-network-viz/` - Skill documentation
- `config/openclaw.json` - MCP server registration
- `tests/integration/` - Integration tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, MCP server registration, and skill scaffolding

- [x] T001 Add unreal-mcp server registration to config/openclaw.json (URL-based entry for http://127.0.0.1:8000/mcp)
- [x] T002 [P] Add UE5_MCP_URL environment variable to .env.example with documentation comment
- [x] T003 [P] Create skill directory structure at workspace/skills/ue5-network-viz/
- [x] T004 [P] Create integration test directory at tests/integration/ (if not exists)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement MCP client wrapper for UE5 HTTP transport in workspace/skills/ue5-network-viz/ue5_mcp_client.py
- [x] T006 [P] Implement tool search mode helpers (list_toolsets, describe_toolset, call_tool) in workspace/skills/ue5-network-viz/ue5_mcp_client.py
- [x] T007 Implement connectivity health check function (ping UE5 MCP server) in workspace/skills/ue5-network-viz/ue5_mcp_client.py
- [x] T008 [P] Implement force-directed layout algorithm for device positioning in workspace/skills/ue5-network-viz/layout.py
- [x] T009 [P] Define device type color mappings (router=blue, switch=green, firewall=red, endpoint=gray) in workspace/skills/ue5-network-viz/materials.py
- [x] T010 Write connectivity integration test in tests/integration/test_ue5_mcp.py::test_mcp_connectivity
- [x] T011 [P] Write tool discovery integration test in tests/integration/test_ue5_mcp.py::test_tool_discovery

**Checkpoint**: Foundation ready - MCP client working, can communicate with UE5

---

## Phase 3: User Story 1 - Render Network Topology in 3D (Priority: P1) MVP

**Goal**: Static topology rendering - spawn actors for devices and links with visual differentiation

**Independent Test**: Connect to a network data source with 5+ devices, issue "render my network in UE5", verify all devices and links appear correctly positioned in UE5 scene

### Tests for User Story 1

- [x] T012 [P] [US1] Write test for single device actor spawning in tests/integration/test_ue5_mcp.py::test_spawn_single_device
- [x] T013 [P] [US1] Write test for multiple device spawning in tests/integration/test_ue5_mcp.py::test_spawn_multiple_devices
- [x] T014 [P] [US1] Write test for device removal in tests/integration/test_ue5_mcp.py::test_remove_device
- [x] T015 [P] [US1] Write test for link creation in tests/integration/test_ue5_mcp.py::test_spawn_link
- [x] T016 [P] [US1] Write test for device type colors in tests/integration/test_ue5_mcp.py::test_device_colors

### Implementation for User Story 1

- [x] T017 [US1] Implement device actor spawning (spawn_actor with cubes/spheres) in workspace/skills/ue5-network-viz/actors.py
- [x] T018 [US1] Implement material creation for device types in workspace/skills/ue5-network-viz/materials.py
- [x] T019 [US1] Implement material application to actors in workspace/skills/ue5-network-viz/actors.py
- [x] T020 [US1] Implement link actor spawning (splines/cylinders between devices) in workspace/skills/ue5-network-viz/actors.py
- [x] T021 [US1] Implement scene lighting setup in workspace/skills/ue5-network-viz/scene.py
- [x] T022 [US1] Implement topology-to-actors translation (NetworkDevice/NetworkLink → UE5Actor) in workspace/skills/ue5-network-viz/renderer.py
- [x] T023 [US1] Implement render_topology main function that orchestrates full scene creation in workspace/skills/ue5-network-viz/renderer.py
- [x] T024 [US1] Add error handling for UE5 connection failures in workspace/skills/ue5-network-viz/renderer.py
- [x] T025 [P] [US1] Write performance test for 100 devices in tests/integration/test_ue5_mcp.py::test_render_100_devices

**Checkpoint**: "Render my network in UE5" produces a complete static 3D scene with colored devices and links

---

## Phase 4: User Story 2 - Real-Time Network Health Visualization (Priority: P2)

**Goal**: Dynamic health state visualization via telemetry updates

**Independent Test**: Render a network, simulate a link failure, verify visualization updates within 30 seconds

### Tests for User Story 2

- [x] T026 [P] [US2] Write test for device health color change in tests/integration/test_ue5_mcp.py::test_device_health_color
- [x] T027 [P] [US2] Write test for link status color change in tests/integration/test_ue5_mcp.py::test_link_status_color
- [x] T028 [P] [US2] Write test for update latency (<30s) in tests/integration/test_ue5_mcp.py::test_update_latency

### Implementation for User Story 2

- [x] T029 [US2] Implement device status color mapping (healthy/warning/critical/unknown) in workspace/skills/ue5-network-viz/materials.py
- [x] T030 [US2] Implement link status color mapping (healthy/degraded/down/unknown) in workspace/skills/ue5-network-viz/materials.py
- [x] T031 [US2] Implement material parameter update function (set_material_parameter) in workspace/skills/ue5-network-viz/materials.py
- [x] T032 [US2] Implement emissive materials for critical alerts (glowing red) in workspace/skills/ue5-network-viz/materials.py
- [x] T033 [US2] Implement event-driven update handler for telemetry alerts in workspace/skills/ue5-network-viz/telemetry.py
- [x] T034 [US2] Implement polling loop for utilization metrics in workspace/skills/ue5-network-viz/telemetry.py
- [x] T035 [US2] Integrate with Telemetry Receivers MCP (Feature 010) for event-driven alerts in workspace/skills/ue5-network-viz/telemetry.py

**Checkpoint**: Device/link colors update in real-time based on telemetry data

---

## Phase 5: User Story 3 - Navigate and Explore the Network (Priority: P3)

**Goal**: Camera controls for scene exploration and fly-through sequences

**Independent Test**: Render any network scene, request camera fly-through, verify smooth movement

### Tests for User Story 3

- [x] T036 [P] [US3] Write test for focus_on_device in tests/integration/test_ue5_mcp.py::test_focus_on_device
- [x] T037 [P] [US3] Write test for camera fly-through in tests/integration/test_ue5_mcp.py::test_flythrough

### Implementation for User Story 3

- [x] T038 [US3] Implement camera state preservation (get_camera_state) in workspace/skills/ue5-network-viz/camera.py
- [x] T039 [US3] Implement focus_on_actor for device inspection in workspace/skills/ue5-network-viz/camera.py
- [x] T040 [US3] Implement set_camera_location for manual positioning in workspace/skills/ue5-network-viz/camera.py
- [x] T041 [US3] Implement fly-through camera animation (keyframe sequence through device clusters) in workspace/skills/ue5-network-viz/camera.py
- [x] T042 [US3] Add natural language hooks for camera commands in workspace/skills/ue5-network-viz/SKILL.md

**Checkpoint**: "Focus on router-1" and "Fly through the network" work smoothly

---

## Phase 6: User Story 4 - Device Detail Inspection (Priority: P4)

**Goal**: Query device metadata and display details

**Independent Test**: Render network, query specific device, verify correct metadata returned

### Implementation for User Story 4

- [x] T043 [US4] Implement actor metadata storage (hostname, device_type, IPs stored with actor tags) in workspace/skills/ue5-network-viz/actors.py
- [x] T044 [US4] Implement get_device_details function (query actor and return metadata) in workspace/skills/ue5-network-viz/renderer.py
- [x] T045 [US4] Implement scene query for all rendered devices (list hostnames) in workspace/skills/ue5-network-viz/renderer.py
- [x] T046 [US4] Add natural language hooks for device queries in workspace/skills/ue5-network-viz/SKILL.md

**Checkpoint**: "What is device router-1?" returns complete device metadata

---

## Phase 7: Incremental Updates

**Goal**: Efficient scene updates without full re-render, preserving camera position

**Independent Test**: Render topology, add/remove device from source, verify only changed actors update

### Tests for Incremental Updates

- [x] T047 [P] Write test for incremental device add in tests/integration/test_ue5_mcp.py::test_incremental_add
- [x] T048 [P] Write test for incremental device remove in tests/integration/test_ue5_mcp.py::test_incremental_remove
- [x] T049 [P] Write test for camera preserved during update in tests/integration/test_ue5_mcp.py::test_camera_preserved

### Implementation for Incremental Updates

- [x] T050 Implement actor tracking map (hostname → actor_name) in workspace/skills/ue5-network-viz/scene.py
- [x] T051 Implement get_all_actors_with_tag("netclaw") query in workspace/skills/ue5-network-viz/scene.py
- [x] T052 Implement topology diff (compare new topology against scene actors) in workspace/skills/ue5-network-viz/renderer.py
- [x] T053 Implement incremental spawn/destroy operations based on diff in workspace/skills/ue5-network-viz/renderer.py
- [x] T054 Implement camera position restoration after incremental update in workspace/skills/ue5-network-viz/camera.py

**Checkpoint**: Re-render only changes, camera position preserved

---

## Phase 8: Polish & Documentation (Artifact Coherence)

**Purpose**: Complete all artifact updates per Constitution Principle XI

### Documentation Updates (REQUIRED)

- [x] T055 [P] Create full SKILL.md documentation in workspace/skills/ue5-network-viz/SKILL.md with workflow examples
- [x] T056 [P] Copy quickstart.md from specs to workspace/skills/ue5-network-viz/quickstart.md
- [x] T057 [P] Update SOUL.md to add ue5-network-viz skill definition
- [x] T058 [P] Update README.md to add UE5 to visualization capabilities and update MCP server count
- [x] T059 [P] Update scripts/install.sh to add UE5 installation instructions and MCP plugin setup
- [x] T060 [P] Update TOOLS.md to add UE5 MCP to infrastructure reference
- [x] T061 [P] Update ui/netclaw-visual/ to add UE5 node to Three.js HUD (if applicable)

### Validation

- [ ] T062 Run full integration test suite against live UE5 MCP (pytest tests/integration/test_ue5_mcp.py -v)
- [x] T063 Manual verification: render 5-device topology and verify visual appearance
- [ ] T064 Manual verification: test camera fly-through for smoothness
- [ ] T065 Manual verification: test health state color changes

### Completion

- [ ] T066 Draft WordPress blog post per Constitution XVII (present to user for review before publishing)
- [x] T067 Final review of artifact coherence checklist (README, SOUL, install.sh, TOOLS, SKILL.md all updated)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 (P1) is MVP - complete first
  - US2-US4 can proceed after US1 or in parallel
- **Incremental Updates (Phase 7)**: Depends on US1 completion (need basic rendering first)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories - THIS IS MVP
- **User Story 2 (P2)**: Can start after Foundational - Depends on US1 actors being renderable for updates
- **User Story 3 (P3)**: Can start after Foundational - Depends on US1 scene existing for camera control
- **User Story 4 (P4)**: Can start after Foundational - Depends on US1 actors having metadata

### Parallel Opportunities

**Within Phase 1 (Setup)**:
- T002, T003, T004 can run in parallel

**Within Phase 2 (Foundational)**:
- T006, T008, T009 can run in parallel
- T010, T011 can run in parallel

**Within User Story 1**:
- T012, T013, T014, T015, T016 (all tests) can run in parallel
- T017-T024 must be sequential (actors → materials → links → orchestration)
- T025 (performance test) can run after T023

**Within User Story 2**:
- T026, T027, T028 (all tests) can run in parallel
- T029, T030 can run in parallel (device/link color mappings)

**Within User Story 3**:
- T036, T037 (tests) can run in parallel
- T038, T039, T040 can run partially in parallel

**Within Incremental Updates**:
- T047, T048, T049 (all tests) can run in parallel

**Within Polish**:
- T055-T061 (all documentation) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (requires UE5 running):
Task: "Write test for single device actor spawning in tests/integration/test_ue5_mcp.py::test_spawn_single_device"
Task: "Write test for multiple device spawning in tests/integration/test_ue5_mcp.py::test_spawn_multiple_devices"
Task: "Write test for device removal in tests/integration/test_ue5_mcp.py::test_remove_device"
Task: "Write test for link creation in tests/integration/test_ue5_mcp.py::test_spawn_link"
Task: "Write test for device type colors in tests/integration/test_ue5_mcp.py::test_device_colors"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T011)
3. Complete Phase 3: User Story 1 (T012-T025)
4. **STOP and VALIDATE**: Test "render my network in UE5" with real topology
5. Deploy/demo if ready - this is a functional MVP!

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 → Static topology visualization
2. **+US2**: Add real-time health updates → Live dashboard
3. **+US3**: Add camera navigation → Interactive exploration
4. **+US4**: Add device inspection → Full detail access
5. **+Incremental**: Add efficient updates → Production-ready
6. **+Polish**: Documentation complete → Feature complete

### Total Task Count: 67

| Phase | Task Count | Description |
|-------|------------|-------------|
| Setup | 4 | Project initialization |
| Foundational | 7 | MCP client, layout, colors |
| US1 (P1) | 14 | Core rendering (MVP) |
| US2 (P2) | 10 | Real-time health |
| US3 (P3) | 7 | Camera navigation |
| US4 (P4) | 4 | Device inspection |
| Incremental | 8 | Efficient updates |
| Polish | 13 | Documentation & validation |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- All integration tests require UE5 running with MCP enabled
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MVP (User Story 1) delivers immediate value - prioritize this
