# Tasks: UE5 Network Digital Twin & Looking-Glass

**Input**: Design documents from `/specs/045-ue5-digital-twin/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/integration-contracts.md, quickstart.md

**Tests**: Live-integration tests against a real running UE5.8 MCP server are included, matching 044's own testing strategy (mocking the UE5 MCP server previously produced a false-positive "passing" test in 044). Tests that also depend on a live upstream *event* (a real SNMP trap, a real open PagerDuty incident) are documented as skip-if-unavailable rather than mocked.

**Organization**: Tasks are grouped by user story (P1-P12 from spec.md) to enable independent implementation, testing, and delivery of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1-US12)
- Exact file paths are included in every task description

## Path Conventions

This feature extends the existing `044-ue5-mcp-network-viz` skill — no new MCP servers, no new top-level directories:
- `workspace/skills/ue5-network-viz/` — existing skill package (modified files + 5 new submodules)
- `tests/integration/test_ue5_mcp.py` — existing integration test file (extended)

---

## Phase 1: Setup

**Purpose**: Confirm the six upstream integrations this feature orchestrates are reachable before any story-specific work begins

- [x] T001 [P] Verify `gnmi-mcp`, `snmptrap-mcp`, PagerDuty MCP, `netbox-mcp-server`, and `infrahub-mcp` are registered and reachable per the prerequisites in `specs/045-ue5-digital-twin/quickstart.md`; note any gaps directly in that file
- [x] T002 [P] Confirm `tests/integration/test_ue5_mcp.py` and its existing live-UE5 fixtures from 044 are reusable as-is for the new test additions in this feature
- [x] T003 Add a scope-expansion note at the top of `workspace/skills/ue5-network-viz/SKILL.md` marking the start of 045 work (full documentation content is completed in Polish phase)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two genuinely cross-cutting primitives nearly every later story depends on — resolving a name against the current topology (FR-040), and recording a state-change history (FR-028)

**⚠️ CRITICAL**: Complete this phase before starting US5 and later stories; US1-US4 do not require it

- [x] T004 Implement a shared topology name-resolution helper (device/interface/link lookup by name against current build state, returning an explicit not-found result) in `workspace/skills/ue5-network-viz/actors.py`, supporting the FR-040 "report rather than attempt" requirement used by US5, US7, US8, US9, US10, US11, US12
- [x] T005 Implement the in-memory, timestamped `HistoryRecord` buffer with `record_history()`/`get_history_window()` primitives in `workspace/skills/ue5-network-viz/telemetry.py`, per data-model.md — populated by US4/US5/US6, consumed by US10

**Checkpoint**: Foundation ready — US1-US4 can already proceed in parallel with this phase; US5 onward should wait for it

---

## Phase 3: User Story 1 - Interface-Level Actors (Priority: P1) 🎯 MVP

**Goal**: Routers/switches spawn child actors for their up/up interfaces; links attach interface-to-interface with device-level fallback; down interfaces are summarized, not spawned as actors

**Independent Test**: Build a topology with a device carrying a mix of up/down interfaces; confirm only up/up interfaces get actors, links attach to interface actors, and repositioning the parent moves its interface actors with it

- [ ] T006 [P] [US1] Implement `spawn_interface_actor()` in `workspace/skills/ue5-network-viz/actors.py`, spawning a child actor only for interfaces reported operationally up/up (FR-001, FR-002)
- [ ] T007 [US1] Extend link-spawning logic in `workspace/skills/ue5-network-viz/actors.py` to attach to source/target interface actors when both resolve, falling back to device-level attachment otherwise (FR-003) — depends on T006
- [ ] T008 [US1] Implement the `DownInterfaceSummary` list generation, attached to the parent device's label/info panel, for interfaces reported down (FR-002)
- [ ] T009 [US1] Ensure interface actors are parented to their device actor's transform so they move together on reposition (FR-004)
- [ ] T010 [P] [US1] Integration test: a device with a mix of up/down interfaces spawns actors only for the up/up ones in `tests/integration/test_ue5_mcp.py`
- [ ] T011 [P] [US1] Integration test: a link with known source/target interfaces attaches to the two interface actors, not the device actors, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Interface-level actors are fully functional and independently testable — this is the structural prerequisite for every later story

---

## Phase 4: User Story 2 - Universal Visible Labeling (Priority: P2)

**Goal**: Every device, up/up interface, and link carries a visible 3D text label

**Independent Test**: Build a topology and visually confirm every device, up/up interface, and link is labeled, without querying NetClaw

- [ ] T012 [P] [US2] Implement `generate_interface_label_actor_name()` in `workspace/skills/ue5-network-viz/actors.py`, extending the existing `generate_label_actor_name` device pattern (FR-006)
- [ ] T013 [P] [US2] Implement `generate_link_label_actor_name()` in `workspace/skills/ue5-network-viz/actors.py`, following the same pattern (FR-007)
- [ ] T014 [US2] Wire label spawning into the device/interface/link actor creation flow in `workspace/skills/ue5-network-viz/actors.py` (FR-005-FR-007) — depends on T012, T013, and US1's interface actors
- [ ] T015 [P] [US2] Integration test: every device, up/up interface, and link in a built topology carries a readable label in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: US1 + US2 together produce a fully labeled, interface-level topology

---

## Phase 5: User Story 3 - Color Legend (Priority: P3)

**Goal**: A single, persistent, always-accurate legend actor decodes the device-type color scheme

**Independent Test**: Build any topology and confirm a legend is present with the correct color for each device type in use, without any additional request

- [ ] T016 [P] [US3] Change `DEVICE_TYPE_COLORS[DeviceType.ENDPOINT]` from gray to orange in `workspace/skills/ue5-network-viz/materials.py` (FR-009)
- [ ] T017 [P] [US3] Implement `generate_legend_swatches()` in `workspace/skills/ue5-network-viz/materials.py`, reading `DEVICE_TYPE_COLORS` directly so the legend cannot drift from the real mapping (FR-009)
- [ ] T018 [US3] Implement `spawn_legend_actor()` in `workspace/skills/ue5-network-viz/actors.py`, called once per topology build (FR-008) — depends on T017
- [ ] T019 [P] [US3] Integration test: legend actor is present after a build and its entries match the live `DEVICE_TYPE_COLORS` mapping, including orange for endpoints, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: US1-US3 complete the full structural-foundation phase from plan.md

---

## Phase 6: User Story 4 - Traffic Visibility on Links and Ports (Priority: P4)

**Goal**: Links/interfaces visually respond to real traffic utilization on request

**Independent Test**: Request a traffic refresh on a topology with known and unknown utilization links; confirm distinct visual states for known-utilization links and default appearance for unknown ones

- [ ] T020 [P] [US4] Implement traffic-utilization retrieval via gNMI/pyATS in `workspace/skills/ue5-network-viz/telemetry.py` (FR-010) — depends on Foundational T004
- [ ] T021 [US4] Implement traffic visual-state application (intensity/pulse) on link/interface actors in `workspace/skills/ue5-network-viz/actors.py` and `materials.py` (FR-010, FR-012) — depends on T020 and US1's interface actors
- [ ] T022 [US4] Implement an on-demand traffic-refresh entry point in `workspace/skills/ue5-network-viz/telemetry.py` that calls `record_history()` for each change (FR-011) — depends on T005, T021
- [ ] T023 [P] [US4] Integration test: a link with utilization data shows a distinct visual state, a link without data shows its default appearance, and a repeated refresh updates values, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Traffic visibility works end to end, independent of live mode or trap alerts

---

## Phase 7: User Story 5 - Live Health via Polling (Priority: P5)

**Goal**: On-demand and continuous ("live mode") real device/interface health reflected as actor color state

**Independent Test**: Trigger an on-demand health refresh and confirm colors update; separately start live mode, observe an automatic update, then stop it and confirm status

- [ ] T024 [P] [US5] Wire real device/interface health retrieval via gNMI/pyATS into the existing `update_device_status`/`update_link_status` functions in `workspace/skills/ue5-network-viz/telemetry.py` (FR-013)
- [ ] T025 [US5] Implement `start_live_mode()` / `stop_live_mode()` / `get_live_mode_status()` on top of the existing `TelemetryPoller` loop in `workspace/skills/ue5-network-viz/telemetry.py` (FR-014, FR-015)
- [ ] T026 [US5] Extend `_poll_once` in `workspace/skills/ue5-network-viz/telemetry.py` so a single device/interface polling failure does not halt the rest of the poll cycle (FR-016)
- [ ] T027 [US5] Call `record_history()` for each health-state change produced by polling in `workspace/skills/ue5-network-viz/telemetry.py` — depends on T005
- [ ] T028 [P] [US5] Integration test: on-demand health refresh updates actor colors; live mode start/stop/status; one unreachable device does not block polling of the rest, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Live health polling and bounded live mode work end to end

---

## Phase 8: User Story 6 - SNMP Trap Alerts (Priority: P6)

**Goal**: Real SNMP traps produce sticky visual alerts that persist until an explicit recovery signal

**Independent Test**: Send a linkDown trap for a device/interface in the topology and confirm the alert appears and persists across an unrelated refresh; send a matching linkUp trap and confirm it clears; send a trap for an unknown device and confirm it is ignored without error

- [ ] T029 [P] [US6] Implement the `StickyAlertState` registry (`latch_sticky_alert()` / `clear_sticky_alert()` / `is_sticky_alert_active()`) in `workspace/skills/ue5-network-viz/telemetry.py` per data-model.md (FR-018)
- [ ] T030 [US6] Wire `process_snmp_trap` (currently a stub in `telemetry.py`) to the real `snmptrap-mcp` server (FR-017) — depends on T029
- [ ] T031 [US6] Apply the sticky visual alert state to the corresponding interface/link actor on a down-type trap, via `actors.py`/`materials.py` (FR-018) — depends on T029 and US1's interface actors
- [ ] T032 [US6] Clear the sticky alert only on a matching linkUp trap or a health-poll-confirmed recovery in `telemetry.py` (FR-018) — depends on T029 and US5's health polling (T024)
- [ ] T033 [US6] Ignore trap events referencing a device/interface not present in the current scene, without raising an error, in `telemetry.py` (FR-019) — depends on Foundational T004
- [ ] T034 [US6] Call `record_history()` for trap-driven state changes in `telemetry.py` — depends on T005
- [ ] T035 [P] [US6] Integration test: a linkDown trap latches a sticky alert that survives an unrelated refresh; a matching linkUp trap or confirmed health-poll recovery clears it; a trap for an unknown device is ignored without error, in `tests/integration/test_ue5_mcp.py` (document as skip-if-unavailable where no live trap sender exists)

**Checkpoint**: US4-US6 complete the full live-signal phase from plan.md

---

## Phase 9: User Story 7 - Ping and Traceroute Visualization (Priority: P7)

**Goal**: Real ping/traceroute between two topology devices animates in the 3D scene

**Independent Test**: Request a ping between two reachable devices and confirm the animated path completes; request a traceroute with an intermediate hop and confirm sequential illumination; request either against a device not in the topology and confirm it is reported, not attempted

- [ ] T036 [P] [US7] Create `workspace/skills/ue5-network-viz/diagnostics.py` with `animate_ping()`, invoking a real ping via gNMI/pyATS and animating the result along the path using existing `renderer.py`/`actors.py` primitives (FR-020, FR-023)
- [ ] T037 [US7] Implement `animate_traceroute()` in `diagnostics.py`, animating sequential hop-by-hop illumination (FR-021) — depends on T036
- [ ] T038 [US7] Resolve source/destination devices via the Foundational lookup helper (T004) and report — rather than attempt — when either is not present in the current topology (FR-022, FR-040)
- [ ] T039 [P] [US7] Integration test: ping and traceroute between reachable devices animate and complete; an unreachable target shows a visually distinguishable failure; an unknown device is reported, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Ping/traceroute visualization works end to end, independent of config panels

---

## Phase 10: User Story 8 - Show Config On Demand (Priority: P8)

**Goal**: A device's real running configuration appears as an in-scene panel on request

**Independent Test**: Request a device's config and confirm a readable panel with real content appears near its actor; request it again and confirm the panel is replaced, not duplicated

- [ ] T040 [P] [US8] Create `workspace/skills/ue5-network-viz/panels.py` with a shared `_render_panel()` primitive that replaces any existing panel of the same kind for a device (FR-025)
- [ ] T041 [US8] Implement `show_config_panel()` in `panels.py`, retrieving real running-config via gNMI/pyATS (FR-024) — depends on T040
- [ ] T042 [P] [US8] Integration test: a config panel with real content appears near the device actor; a repeated request replaces rather than duplicates the panel, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Config panels work end to end — the shared panel primitive is also the foundation for US12's metrics HUD

---

## Phase 11: User Story 9 - Incident Correlation (Priority: P9)

**Goal**: A device/link's open PagerDuty incident (matched by hostname) drives a distinct alarm visual state

**Independent Test**: With a known open incident referencing a device's hostname, request correlation and confirm the alarm state appears; with no matching incident for a different device, confirm NetClaw reports none was found

- [ ] T043 [P] [US9] Implement `get_alarm_color()` in `workspace/skills/ue5-network-viz/materials.py` for the incident alarm visual state, distinct from existing status colors (FR-026)
- [ ] T044 [US9] Create `workspace/skills/ue5-network-viz/incidents.py` with `correlate_incident()`, querying PagerDuty's existing MCP integration and matching by hostname substring against title/description/service name (FR-026) — depends on T043 and Foundational T004
- [ ] T045 [US9] Implement the explicit "no correlated incident found" report path in `incidents.py` (FR-027) — depends on T044
- [ ] T046 [P] [US9] Integration test: a device with a matching open incident gets the alarm visual state; a device with no match gets a clear "not found" report, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Incident correlation works end to end, independent of playback

---

## Phase 12: User Story 10 - Historical Playback (Priority: P10)

**Goal**: A recorded time window of state changes replays in the scene at a compressed, adjustable speed

**Independent Test**: Generate several state changes, request playback of that window, and confirm they replay in original order at compressed speed; request an adjusted speed and confirm proportional duration change; request an empty window and confirm it is reported

- [ ] T047 [P] [US10] Create `workspace/skills/ue5-network-viz/playback.py` with `replay_window()` reading `telemetry.get_history_window()` (FR-029) — depends on Foundational T005 and history being populated by US4/US5/US6 (T022, T027, T034)
- [ ] T048 [US10] Implement compressed default-speed replay against the live scene, in original order, in `playback.py` (FR-029) — depends on T047
- [ ] T049 [US10] Implement an explicit speed-adjustment parameter that proportionally changes replay duration in `playback.py` (FR-030) — depends on T048
- [ ] T050 [US10] Implement the explicit "no changes found for this window" report path in `playback.py` (FR-031) — depends on T047
- [ ] T051 [P] [US10] Integration test: a window with recorded changes replays in order at compressed default speed; an adjusted speed changes duration proportionally; an empty window is reported, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: US9-US10 complete the full operational-context phase from plan.md

---

## Phase 13: User Story 11 - Hierarchical Zoom (Priority: P11)

**Goal**: Site/rack/device zoom levels, grouped from NetBox/Infrahub with manual fallback

**Independent Test**: With devices carrying NetBox/Infrahub rack placement, zoom into that rack and confirm correct grouping; with devices carrying no placement, manually assign a grouping and confirm the same zoom behavior; zoom back out and confirm no duplicated/missing actors

- [ ] T052 [P] [US11] Create `workspace/skills/ue5-network-viz/hierarchy.py` with `resolve_zoom_groups()`, querying `netbox-mcp-server` and `infrahub-mcp` for rack/site placement by hostname (FR-033)
- [ ] T053 [US11] Implement `assign_manual_group()` as the fallback path for devices with no source-of-truth placement in `hierarchy.py` (FR-033) — depends on T052
- [ ] T054 [US11] Implement `zoom_to()` / `zoom_out_to_site()` in `hierarchy.py`, extending `workspace/skills/ue5-network-viz/camera.py` to toggle actor visibility/camera framing without rebuilding the topology (FR-032, FR-034, FR-035) — depends on T052, T053
- [ ] T055 [US11] Report devices with no NetBox/Infrahub placement and no manual assignment as ungrouped, rather than silently defaulting them, in `hierarchy.py` (edge case in spec.md) — depends on T052
- [ ] T056 [P] [US11] Integration test: zoom into a NetBox/Infrahub-sourced rack view and into a manually-grouped view both work correctly; zooming back out restores the full topology with no duplicated/missing actors, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: Hierarchical zoom works end to end

---

## Phase 14: User Story 12 - Floating Metrics HUD (Priority: P12)

**Goal**: A device's live CPU/memory/uptime appear as a floating panel on request

**Independent Test**: Request metrics for a device and confirm a floating panel with current values appears above its actor; request again and confirm freshly retrieved values, not a cached display

- [ ] T057 [P] [US12] Implement `show_metrics_hud()` in `workspace/skills/ue5-network-viz/panels.py`, retrieving live CPU/memory/uptime via gNMI/pyATS (FR-036) — depends on US8's shared `_render_panel` primitive (T040)
- [ ] T058 [US12] Ensure a repeated metrics request reflects freshly retrieved values rather than a previously cached display, in `panels.py` (FR-037) — depends on T057
- [ ] T059 [P] [US12] Integration test: a metrics HUD panel appears above the device actor with current CPU/memory/uptime; a repeated request shows freshly retrieved values, in `tests/integration/test_ue5_mcp.py`

**Checkpoint**: All 12 user stories are independently functional — full P1-P12 scope complete

---

## Phase 15: Polish & Cross-Cutting Concerns

**Purpose**: Full artifact coherence and milestone documentation, per Constitution Principles XI, XII, and XVII

- [ ] T060 Update `workspace/skills/ue5-network-viz/SKILL.md` documenting all 12 new conversational capabilities, their trigger phrasing, the sticky-alert/live-mode semantics, and the NetBox/Infrahub-first zoom-grouping behavior
- [ ] T061 [P] Update `README.md` to describe the skill's expanded interactive/digital-twin capabilities
- [ ] T062 [P] Update `SOUL.md`'s ue5-network-viz skill entry to reflect the expanded scope
- [ ] T063 [P] Update `TOOLS.md` noting the additional integrations this skill now orchestrates (snmptrap-mcp, gnmi-mcp, PagerDuty, NetBox, Infrahub)
- [ ] T064 Run the full extended `tests/integration/test_ue5_mcp.py` suite against a live UE5.8 instance and record results
- [ ] T065 Draft the WordPress milestone blog post per Constitution Principle XVII and present it for review before publishing
- [ ] T066 Run `specs/045-ue5-digital-twin/quickstart.md` end to end and correct any drift found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependencies on Setup completing, but T004/T005 should land before US5 onward
- **US1 (Phase 3)**: No dependencies beyond Setup — this is the MVP and the structural prerequisite for every later story
- **US2 (Phase 4)**: Depends on US1 (labels interface actors that must already exist)
- **US3 (Phase 5)**: Independent of US1/US2 at the code level, but conventionally built after them to complete the "structural foundation" milestone
- **US4 (Phase 6)**: Depends on US1 (interface actors) and Foundational T004
- **US5 (Phase 7)**: Depends on US1 (interface actors) and Foundational T004/T005
- **US6 (Phase 8)**: Depends on US1, Foundational T004/T005, and US5 (health-poll-confirmed recovery, T024)
- **US7 (Phase 9)**: Depends on Foundational T004
- **US8 (Phase 10)**: Depends on Foundational T004
- **US9 (Phase 11)**: Depends on Foundational T004
- **US10 (Phase 12)**: Depends on Foundational T005 and history actually being populated by US4/US5/US6
- **US11 (Phase 13)**: Independent of other stories at the code level
- **US12 (Phase 14)**: Depends on US8's shared panel primitive (T040)
- **Polish (Phase 15)**: Depends on all desired user stories being complete

### Parallel Opportunities

- All Setup tasks (T001-T002) marked [P] can run in parallel; T003 is independent text-file work
- T004 and T005 (Foundational) touch different files and can run in parallel
- Within each user story phase, tasks marked [P] touch different files/functions and can run in parallel; unmarked tasks depend on a preceding task in the same phase
- US3 can be implemented in parallel with US1/US2 by a second contributor, since it has no code-level dependency on either
- US7, US8, and US9 have no code-level dependency on each other (beyond the shared Foundational lookup helper) and can be implemented in parallel
- US11 has no code-level dependency on any other story and can be implemented at any point after Setup

---

## Parallel Example: User Story 1

```bash
# Launch US1's parallelizable tasks together:
Task: "Implement spawn_interface_actor() in workspace/skills/ue5-network-viz/actors.py, spawning a child actor only for up/up interfaces (FR-001, FR-002)"
Task: "Integration test: interface-actor count matches up/up interfaces only in tests/integration/test_ue5_mcp.py"
Task: "Integration test: link attaches to interface actors with device-level fallback in tests/integration/test_ue5_mcp.py"
```

## Parallel Example: User Stories 7, 8, and 9

```bash
# These three stories share no files and only depend on the Foundational lookup helper (T004):
Task: "Create workspace/skills/ue5-network-viz/diagnostics.py with animate_ping()"
Task: "Create workspace/skills/ue5-network-viz/panels.py with a shared _render_panel() primitive"
Task: "Implement get_alarm_color() in workspace/skills/ue5-network-viz/materials.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (Foundational T004/T005 are not required for US1 itself)
3. **STOP and VALIDATE**: Build a topology and confirm interface-level actors spawn correctly per the Independent Test
4. Demo: "render my network in UE5" now shows real interface-level actors on up/up ports

### Incremental Delivery (matches plan.md's 6-phase grouping)

1. Setup → US1 → US2 → US3 → **Structural Foundation checkpoint** (interface actors, labels, legend all working)
2. Foundational (T004-T005) → US4 → US5 → US6 → **Live Signal checkpoint** (traffic, live health, sticky trap alerts)
3. US7 → US8 → **Active Diagnostics checkpoint** (ping/traceroute animation, config panels)
4. US9 → US10 → **Operational Context checkpoint** (incident correlation, historical playback)
5. US11 → US12 → **Spatial Navigation checkpoint** — full P1-P12 scope complete
6. Polish → milestone documentation

### Parallel Team Strategy

With multiple developers, after Setup + Foundational:

- Developer A: US1 → US2 → US4 → US5 → US6 (the actor/telemetry-heavy chain)
- Developer B: US3 (independent) → US7 → US9 (independent of A's chain once T004 exists)
- Developer C: US8 → US12 (the panel-primitive chain) → US11 (independent)
- Regroup for US10 once US4/US5/US6 are populating history, then complete Polish together
