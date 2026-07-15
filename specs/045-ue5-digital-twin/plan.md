# Implementation Plan: UE5 Network Digital Twin & Looking-Glass

**Branch**: `045-ue5-digital-twin` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/045-ue5-digital-twin/spec.md`

## Summary

Extend the merged `044-ue5-mcp-network-viz` skill from a static topology snapshot into an interactive digital twin. Devices spawn interface-level child actors for their up/up ports; every device, interface, and link carries a visible label; a persistent legend decodes the color scheme. On top of that structural change, the skill gains conversational, MCP-orchestrated capabilities that already have real backing data sources in this repo: live health via gNMI/pyATS polling and a bounded "live mode," sticky SNMP trap alerts sourced from the existing `snmptrap-mcp` server, real ping/traceroute animation, on-demand config panels, PagerDuty incident correlation by hostname match, an in-memory session history buffer with compressed/adjustable-speed playback, and hierarchical zoom using NetBox/Infrahub rack-site placement with manual grouping as a fallback. No new MCP servers and no UE5-side plugin/Blueprint code are introduced — this is an orchestration layer over MCP servers and skill modules that already exist.

## Technical Context

**Language/Version**: Python 3.10+ (matches the existing `ue5-network-viz` skill and the rest of NetClaw)
**Primary Dependencies**: httpx (existing UE5 MCP HTTP/JSON-RPC client, `ue5_mcp_client.py`), no new third-party packages required
**Storage**: N/A — all new state (sticky alert flags, live-mode status, session history buffer, manual zoom groupings) is in-memory for the lifetime of the running skill process; nothing persists across a NetClaw restart
**Testing**: pytest, following the existing `tests/integration/test_ue5_mcp.py` pattern — live integration tests against a running UE5.8 MCP server and, where practical, the real supporting MCP servers (`snmptrap-mcp`, `gnmi-mcp`, PagerDuty), with explicit skips where a live dependency (e.g. a real trap sender) isn't available
**Target Platform**: WSL2/Linux (NetClaw) + Windows (UE5 Editor GUI) — unchanged from 044
**Project Type**: Skill extension (single project) — no new MCP server code, no new top-level directories
**Performance Goals**: Interface-actor spawn adds at most one actor per up/up interface (bounded by the up/up-only rule in FR-001/FR-002); trap-driven visual alerts appear within 10s of receipt (SC-005); ping/traceroute animations complete within 30s (SC-003); config/HUD panels render within 15s (SC-004)
**Constraints**: Same fragile, GPU-heavy single UE5 host documented in 044 — this feature MUST NOT reintroduce an unbounded per-port actor count, and MUST reuse 044's SSE-stream-read-until-first-JSON-RPC-object fix and always-pass-full-transform convention for any new UE5 MCP calls rather than re-discovering those bugs
**Scale/Scope**: Same topology scale as 044 (up to ~200 devices, ~500 links), now with a bounded number of additional interface actors per device (only up/up interfaces) plus at most one legend actor, one config panel, and one metrics HUD panel per device at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | Read-only against devices for health/config/ping/traceroute; no configuration changes are made to any device |
| II. Read-Before-Write | N/A | No device writes occur anywhere in this feature |
| III. ITSM-Gated Changes | N/A | No production device changes; visualization and diagnostics only |
| IV. Immutable Audit Trail | PASS | Reuses existing GAIT logging for skill invocations; no new audit mechanism needed |
| V. MCP-Native Integration | PASS | Orchestrates exclusively through existing MCP servers (UE5, snmptrap-mcp, gnmi-mcp, netbox-mcp-server, infrahub-mcp, PagerDuty) — no bespoke integration paths |
| VI. Multi-Vendor Neutrality | PASS | Interface/health/config data sourced through vendor-neutral gNMI/pyATS abstractions already used by 044 |
| VII. Skill Modularity | PASS | Extends the single `ue5-network-viz` skill with clearly separated submodules (diagnostics, panels, incidents, playback, hierarchy) rather than a new skill per capability |
| VIII. Verify After Every Change | N/A | No device changes to verify; visualization state is verified via acceptance scenarios in spec.md |
| IX. Security by Default | PASS | No elevated privileges; reuses existing credential/auth handling of gNMI/pyATS/PagerDuty/NetBox/Infrahub/UE5 MCP integrations |
| X. Observability | PASS | Reported failures (unreachable device, no correlated incident, empty playback window) are explicit per FR-040, not silent |
| XI. Full-Stack Artifact Coherence | **REQUIRED** | Must update `SKILL.md`, README, SOUL.md, TOOLS.md where new capabilities are documented |
| XII. Documentation-as-Code | **REQUIRED** | `SKILL.md` must document all 12 new conversational capabilities |
| XIII. Credential Safety | PASS | No new credentials introduced; reuses existing env vars for gNMI/pyATS/PagerDuty/NetBox/Infrahub |
| XIV. Human-in-the-Loop | N/A | No external communications sent by this feature |
| XV. Backwards Compatibility | PASS | Existing 044 device/link-only topologies continue to render; interface actors and links-to-interfaces are additive when interface data is present, with device-level fallback (FR-003) when it is not |
| XVI. Spec-Driven Development | PASS | Following the same spec → clarify → plan → tasks → implement workflow as 044 |
| XVII. Milestone Documentation | **REQUIRED** | Blog post after completion, per constitution and prior practice |

**Gate Status**: PASS — no violations. Artifact-coherence and documentation requirements noted for the Polish phase, same as 044.

## Project Structure

### Documentation (this feature)

```text
specs/045-ue5-digital-twin/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── integration-contracts.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created here)
```

### Source Code (repository root)

```text
# Skill extension (existing package, modified + new submodules)
workspace/skills/ue5-network-viz/
├── SKILL.md              # MODIFY - document 12 new conversational capabilities
├── actors.py              # MODIFY - interface-actor spawning, interface-attached links, legend actor
├── materials.py            # MODIFY - endpoint color -> orange, legend swatch helper
├── telemetry.py             # MODIFY - sticky trap state, live-mode control, history buffer, real snmptrap-mcp/gnmi/pyATS wiring
├── renderer.py               # MODIFY - reused for panel/animation rendering primitives where applicable
├── camera.py                  # MODIFY - zoom-level camera transitions (site/rack/device)
├── diagnostics.py               # NEW - real ping/traceroute execution + path animation
├── panels.py                      # NEW - on-demand config panel + metrics HUD panel (shared text/plane-panel primitive)
├── incidents.py                     # NEW - PagerDuty hostname-match correlation, alarm visual state
├── playback.py                        # NEW - compressed/adjustable-speed replay of telemetry.py's history buffer
└── hierarchy.py                        # NEW - NetBox/Infrahub rack-site resolution + manual grouping fallback + zoom-level actor visibility

# Tests (existing file extended, no new test file needed unless a submodule warrants isolation)
tests/integration/
└── test_ue5_mcp.py       # MODIFY - add coverage for interface actors, labels, legend, trap persistence, live mode, ping/traceroute, config panel, incident correlation, playback, zoom, metrics HUD

# Documentation (modified, per Artifact Coherence Checklist below)
SOUL.md, README.md, TOOLS.md, scripts/install.sh   # MODIFY where the new capabilities need to be discoverable
```

**Structure Decision**: Single project, no new top-level directories, no new MCP servers. All new logic lives inside the existing `workspace/skills/ue5-network-viz/` package as five new focused submodules plus targeted extensions to the four existing modules that already carry the relevant responsibility (actors, materials, telemetry, camera). This mirrors 044's own structure decision and Constitution Principle VII (Skill Modularity) — one skill, cleanly separated internal modules, not one skill per user story.

## Artifact Coherence Checklist

Per Constitution Principle XI, these artifacts MUST be updated when implementation completes:

| Artifact | Action | Description |
|----------|--------|-------------|
| `workspace/skills/ue5-network-viz/SKILL.md` | MODIFY | Document all 12 new conversational capabilities, the sticky-alert/live-mode semantics, and the NetBox/Infrahub-first zoom-grouping behavior |
| `README.md` | MODIFY | Update the UE5 visualization capability description to mention interactivity/digital-twin behavior |
| `SOUL.md` | MODIFY | Update the ue5-network-viz skill entry to reflect its expanded scope |
| `TOOLS.md` | MODIFY | Note the additional integrations this skill now orchestrates (snmptrap-mcp, gnmi-mcp, PagerDuty, NetBox, Infrahub) in the UE5 entry, without duplicating their own dedicated entries |
| `tests/integration/test_ue5_mcp.py` | MODIFY | Add live-verification coverage per story, matching 044's live-integration-test convention |

## Implementation Phases

Phases below map directly to the spec's P1–P12 priority ordering so each phase remains an independently demonstrable checkpoint, per the spec's Assumptions.

### Phase 1: Structural Foundation (P1–P3)

**Goal**: Interface-level actors, universal labeling, and the color legend — the structural prerequisites every later story depends on.

**Tasks**:
1. Extend `actors.py` to spawn interface actors (child of device actor) only for up/up interfaces, using existing `source_interface`/`target_interface` link metadata.
2. Extend `actors.py` link-spawning to attach to interface actors when both ends resolve, falling back to device-level attachment (FR-003).
3. Extend the existing `generate_label_actor_name` pattern in `actors.py` to interfaces and links.
4. Add a down-interface summary (list, not actors) attached to the parent device's label/info panel.
5. Add a legend-actor spawn function in `actors.py`, driven by a new swatch-generation helper in `materials.py` that reads `DEVICE_TYPE_COLORS` directly.
6. Change `DEVICE_TYPE_COLORS[DeviceType.ENDPOINT]` from gray to orange in `materials.py`.
7. Integration tests for interface-actor counts, label presence, and legend content/accuracy.

**Deliverable**: A rebuilt topology shows interface-level actors on up/up ports only, every device/interface/link is labeled, and a legend actor is present and accurate.

### Phase 2: Live Signal (P4–P6)

**Goal**: Traffic visibility, live health polling with bounded live mode, and sticky SNMP trap alerts.

**Tasks**:
1. Extend `telemetry.py`'s polling path to retrieve real interface utilization via gNMI/pyATS and drive a traffic visual state on link/interface actors (FR-010–FR-012).
2. Add `start_live_mode()` / `stop_live_mode()` / `get_live_mode_status()` on top of the existing `TelemetryPoller` loop (FR-014–FR-015).
3. Wire real device/interface health polling into `update_device_status`/`update_link_status` (already present in `telemetry.py`) via gNMI/pyATS (FR-013).
4. Ensure a per-device/interface polling failure does not halt the rest of the poll cycle (FR-016) — this pattern already exists in `_poll_once`; extend it to the new real data calls.
5. Wire `process_snmp_trap` (already present, currently a stub) to the real `snmptrap-mcp` server.
6. Add an in-memory sticky-state registry keyed by device/interface, cleared only by a corresponding linkUp trap or a health-poll-confirmed recovery (FR-018).
7. Integration tests for traffic visualization, live-mode start/stop/status, per-device poll isolation, and trap-driven sticky alerts (with a documented skip for environments with no live trap sender).

**Deliverable**: "Refresh traffic," "start/stop live mode," and a real linkDown/linkUp trap all produce the state changes described in Stories 4–6.

### Phase 3: Active Diagnostics (P7–P8)

**Goal**: Ping/traceroute animation and on-demand config panels.

**Tasks**:
1. New `diagnostics.py`: resolve source/destination device actors, invoke a real ping via gNMI/pyATS, animate the result along the path using `renderer.py`/`actors.py` primitives (FR-020, FR-023).
2. New `diagnostics.py`: same pattern for traceroute, animating sequential hop illumination (FR-021).
3. Both diagnostics entry points MUST report (not attempt) when a named device isn't in the current topology (FR-022, FR-040).
4. New `panels.py`: a shared text/plane-panel primitive positioned relative to a device actor, with a "replace existing panel for this device" rule (FR-025).
5. `panels.py`: config-panel variant that retrieves real running-config via gNMI/pyATS and renders it (FR-024).
6. Integration tests for ping/traceroute animation (success and failure paths) and config-panel display/replacement.

**Deliverable**: "Ping R1 to R2," "traceroute R1 to R5," and "show me R1's config" all produce real, animated/rendered results in the scene.

### Phase 4: Operational Context (P9–P10)

**Goal**: Incident correlation and historical playback.

**Tasks**:
1. New `incidents.py`: query PagerDuty for open incidents, correlate by hostname substring match against title/description/service name (FR-026), apply/clear an alarm visual state via `materials.py`.
2. `incidents.py`: explicit "no correlated incident found" report path (FR-027).
3. Extend `telemetry.py` with a session-scoped, timestamped history buffer recording every health/traffic/trap-driven state change (FR-028) — this is the same event stream already flowing through `TelemetryEventProcessor`, tapped into a ring buffer rather than a new capture path.
4. New `playback.py`: replay a requested time window from the history buffer against the live scene at a compressed default speed, with an explicit speed-adjustment parameter (FR-029, FR-030), reporting when a window has no recorded changes (FR-031).
5. Integration tests for incident correlation (found/not-found) and playback (default speed, adjusted speed, empty window).

**Deliverable**: "Does R1 have an open incident?" and "replay the last 10 minutes at double speed" both work end to end.

### Phase 5: Spatial Navigation (P11–P12)

**Goal**: Hierarchical zoom and the floating metrics HUD.

**Tasks**:
1. New `hierarchy.py`: resolve rack/site placement per device from `netbox-mcp-server` or `infrahub-mcp`; accept an explicit manual-grouping call as fallback when neither has data (FR-033); report devices left ungrouped (edge case in spec.md).
2. `hierarchy.py` + `camera.py`: implement site/rack/device zoom-level transitions that toggle actor visibility/camera framing rather than rebuilding the topology (FR-032, FR-034, FR-035).
3. `panels.py`: metrics-HUD variant — floating panel above a device actor showing live CPU/memory/uptime via gNMI/pyATS, always reflecting the freshest retrieval (FR-036, FR-037).
4. Integration tests for zoom transitions (NetBox/Infrahub-sourced and manual-grouping-sourced) and metrics HUD display/refresh.

**Deliverable**: "Zoom into rack 3" and "show me R1's metrics" both work end to end, completing the full P1–P12 scope.

### Phase 6: Polish & Documentation

**Goal**: Full artifact coherence and milestone documentation, matching 044's own closing phase.

**Tasks**:
1. Update `SKILL.md` with all 12 new capabilities and their conversational trigger phrasing.
2. Update `README.md`, `SOUL.md`, `TOOLS.md` per the Artifact Coherence Checklist above.
3. Run the full extended `tests/integration/test_ue5_mcp.py` suite against a live UE5.8 instance.
4. Draft the WordPress milestone post (Constitution XVII).

## Testing Strategy

Live UE5.8 integration tests are the primary verification method, matching 044's own approach — this feature has no meaningful unit-testable surface independent of a running UE5 MCP server, and mocking that server was explicitly what caused 044's early "silently failing while reporting green" bug. Each phase's tests are additive to `tests/integration/test_ue5_mcp.py` and gated on the same live-dependency prerequisites 044 already documents (UE5.8 running, MCP plugin enabled, "All Tools" read/write access on). Tests that also require a live upstream event (an actual SNMP trap, a real open PagerDuty incident) are clearly marked skip-if-unavailable rather than mocked, so a false green is never possible for the trap/incident paths specifically — consistent with the false-positive verification bug already found and fixed in 044.

## Complexity Tracking

*No entries — Constitution Check gate passed with no violations requiring justification.*
