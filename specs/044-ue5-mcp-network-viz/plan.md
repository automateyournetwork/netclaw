# Implementation Plan: Unreal Engine 5.8 MCP Network Visualization

**Branch**: `044-ue5-mcp-network-viz` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/044-ue5-mcp-network-viz/spec.md`

## Summary

Integrate the built-in Unreal Engine 5.8 MCP server to enable 3D network topology visualization. Network engineers can request topology renderings via natural language (e.g., "render my network in UE5"), and NetClaw collects data from existing MCP servers (pyATS, SuzieQ, GNS3, CML), translates devices and links into UE5 actor commands, and spawns a complete 3D scene. The integration supports real-time updates via hybrid telemetry (event-driven alerts, polling for metrics) and incremental scene updates that preserve camera position.

## Technical Context

**Language/Version**: Python 3.10+ (skill logic), No custom MCP server code (uses built-in UE5 MCP)
**Primary Dependencies**: httpx (HTTP client for MCP), Unreal Engine 5.8+ (user-installed with MCP plugin)
**Storage**: N/A (stateless - visualization is ephemeral in UE5)
**Testing**: pytest (integration tests against live UE5 MCP server)
**Target Platform**: WSL2/Linux (NetClaw) + Windows (UE5 Editor GUI)
**Project Type**: MCP integration + skill definition (no custom server code required)
**Performance Goals**: Render 100 devices in <60 seconds; update latency <30 seconds
**Constraints**: Local-machine only (loopback); requires UE5 running with MCP plugin; GPU recommended
**Scale/Scope**: Up to 200 devices, 500 links per topology visualization

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | Read-only visualization; no device modifications |
| II. Read-Before-Write | PASS | Reads topology data before rendering; no device writes |
| III. ITSM-Gated Changes | N/A | No production changes; visualization only |
| IV. Immutable Audit Trail | PASS | GAIT logging for sessions |
| V. MCP-Native Integration | PASS | Uses built-in UE5 MCP server via HTTP transport |
| VI. Multi-Vendor Neutrality | PASS | Visualization is vendor-agnostic; works with any topology source |
| VII. Skill Modularity | PASS | Single-purpose skill (ue5-network-viz) |
| VIII. Verify After Every Change | N/A | No device changes to verify |
| IX. Security by Default | PASS | No elevated privileges; local-only MCP (loopback) |
| X. Observability | PASS | Error messages for connection failures; scene state queryable |
| XI. Full-Stack Artifact Coherence | **REQUIRED** | Must update README, SOUL.md, install.sh, openclaw.json, SKILL.md |
| XII. Documentation-as-Code | **REQUIRED** | Must create SKILL.md |
| XIII. Credential Safety | PASS | No credentials required (local HTTP server) |
| XIV. Human-in-the-Loop | N/A | No external communications |
| XV. Backwards Compatibility | PASS | New capability; no breaking changes |
| XVI. Spec-Driven Development | PASS | Following SDD workflow |
| XVII. Milestone Documentation | **REQUIRED** | Blog post after completion |

**Gate Status**: PASS - No violations. Requirements noted for artifact coherence.

## Project Structure

### Documentation (this feature)

```text
specs/044-ue5-mcp-network-viz/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (UE5 MCP research)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (developer setup)
├── contracts/           # Phase 1 output (MCP tool schemas)
│   └── mcp-tools.md     # UE5 MCP tool contracts
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
# Configuration files (modified)
config/openclaw.json         # Add unreal-mcp server registration
.env.example                 # Add UE5_MCP_URL

# Skill definition (new)
workspace/skills/ue5-network-viz/
├── SKILL.md                 # Skill documentation
└── quickstart.md            # Copy from specs for workspace access

# Documentation (modified)
SOUL.md                      # Add ue5-network-viz skill
README.md                    # Add to MCP integration table, update architecture
scripts/install.sh           # Add UE5 setup instructions
TOOLS.md                     # Add UE5 MCP to infrastructure reference

# Tests (new)
tests/integration/
└── test_ue5_mcp.py          # Live integration tests against UE5 MCP
```

**Structure Decision**: No custom MCP server code required. This integration uses the built-in UE5.8 MCP server. Implementation consists of:
1. MCP server registration in `openclaw.json` (URL-based, like Jenkins/Datadog)
2. Skill definition in `workspace/skills/ue5-network-viz/SKILL.md`
3. Integration tests against live UE5 MCP server
4. Documentation updates across all standard touchpoints

## Artifact Coherence Checklist

Per Constitution Principle XI, all these artifacts MUST be updated:

| Artifact | Action | Description |
|----------|--------|-------------|
| `README.md` | MODIFY | Add UE5 to visualization capabilities, update MCP server count, add to architecture diagram |
| `SOUL.md` | MODIFY | Add ue5-network-viz skill definition |
| `scripts/install.sh` | MODIFY | Add UE5 installation instructions and MCP plugin setup |
| `config/openclaw.json` | MODIFY | Add unreal-mcp server registration |
| `.env.example` | MODIFY | Add UE5_MCP_URL variable |
| `TOOLS.md` | MODIFY | Add UE5 MCP to infrastructure reference |
| `workspace/skills/ue5-network-viz/SKILL.md` | CREATE | Full skill documentation |
| `tests/integration/test_ue5_mcp.py` | CREATE | Integration tests |
| `ui/netclaw-visual/` | MODIFY | Add UE5 node to Three.js HUD (if applicable) |

## Implementation Phases

### Phase 1: Foundation (P1 - Core Rendering)

**Goal**: Basic topology rendering - spawn actors for devices and links.

**Tasks**:
1. Register UE5 MCP server in `openclaw.json`
2. Create skill scaffolding (`workspace/skills/ue5-network-viz/`)
3. Implement MCP connectivity check (ping/health)
4. Implement device actor spawning (cubes/spheres)
5. Implement force-directed layout algorithm
6. Implement link actor spawning (splines/cylinders)
7. Implement material creation and application (device type colors)
8. Write integration tests for actor spawning (against live UE5)
9. Update `.env.example` with UE5_MCP_URL

**Deliverable**: "Render my network in UE5" produces a static 3D scene.

### Phase 2: Real-Time Updates (P2 - Health Visualization)

**Goal**: Dynamic health state visualization via telemetry.

**Tasks**:
1. Implement device status color mapping (healthy/warning/critical)
2. Implement link status color mapping
3. Integrate with Telemetry Receivers MCP (event-driven alerts)
4. Implement polling loop for utilization metrics
5. Implement material parameter updates for color changes
6. Add emissive materials for critical alerts (glowing effect)
7. Write integration tests for status updates

**Deliverable**: Device/link colors update based on telemetry data.

### Phase 3: Navigation & Inspection (P3-P4)

**Goal**: Camera controls and device inspection.

**Tasks**:
1. Implement camera state preservation
2. Implement `focus_on_actor` for device inspection
3. Implement fly-through camera animation
4. Implement scene query for device details
5. Write integration tests for camera operations

**Deliverable**: "Focus on router-1" and "Fly through the network" work.

### Phase 4: Incremental Updates

**Goal**: Efficient scene updates without full re-render.

**Tasks**:
1. Implement actor tracking (hostname → actor mapping)
2. Implement topology diff (adds/removes/updates)
3. Implement incremental actor operations
4. Ensure camera position preserved during updates
5. Write integration tests for incremental updates

**Deliverable**: Re-render only changes, not the entire scene.

### Phase 5: Polish & Documentation

**Goal**: Complete artifact coherence and documentation.

**Tasks**:
1. Update README.md (capabilities, MCP count, architecture)
2. Update SOUL.md (skill definition)
3. Update scripts/install.sh (UE5 setup instructions)
4. Update TOOLS.md (infrastructure reference)
5. Create full SKILL.md documentation
6. Update Three.js HUD (if applicable)
7. Run full integration test suite
8. Draft WordPress blog post (per Constitution XVII)

**Deliverable**: Feature complete with all artifacts updated.

## Testing Strategy

### Live UE5 Integration Tests

All tests run against a live UE5.8 instance with MCP enabled.

**Prerequisites**:
- UE5.8 installed and running
- MCP plugin enabled (Edit > Plugins > Unreal MCP)
- MCP server started (auto-start or `ModelContextProtocol.StartServer`)

**Test Categories**:

| Category | Test Count | Description |
|----------|------------|-------------|
| Connectivity | 2 | Verify MCP server reachable, tool discovery |
| Actor Spawning | 5 | Single device, multiple devices, remove device, scale test |
| Materials | 3 | Device colors, health state changes, link colors |
| Links | 3 | Create links, update status, remove links |
| Incremental | 4 | Add device, remove device, update device, camera preserved |
| Performance | 2 | Render 100 devices (<60s), update latency (<30s) |
| Camera | 2 | Focus on device, fly-through |

**Test Execution**:
```bash
# Ensure UE5 is running with MCP enabled, then:
pytest tests/integration/test_ue5_mcp.py -v --tb=short

# Performance tests (longer timeout)
pytest tests/integration/test_ue5_mcp.py -k "performance" -v --timeout=120
```

### Manual Verification

After automated tests pass:

- [ ] Devices visually distinguishable by color
- [ ] Links connect device centers properly
- [ ] Scene lighting is adequate
- [ ] Camera fly-through is smooth
- [ ] Health color changes are visible
- [ ] Scene looks presentation-ready

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| UE5 MCP is experimental | Test early; document API quirks; plan for potential changes |
| WSL-to-Windows connectivity issues | Document Windows host IP method; provide troubleshooting guide |
| Large topology performance | Implement device limit (200); use efficient actor operations |
| First command timeout | Document as expected behavior; implement retry logic |
| Tool search mode complexity | Abstract behind helper functions; cache toolset schemas |

## Complexity Tracking

No violations requiring justification. This is a straightforward MCP integration following established NetClaw patterns (similar to Feature 024 Blender integration, but simpler since UE5 MCP is built-in).

## Success Criteria Mapping

| Spec Criteria | Implementation | Verification |
|---------------|----------------|--------------|
| SC-001: 100 devices in <60s | Batch actor spawning, efficient layout | Performance test |
| SC-002: Health update <30s | Event-driven updates for alerts | Integration test |
| SC-003: 4 device types distinguishable | Color-coded materials | Manual + automated |
| SC-004: 200 devices, 500 links responsive | Level-of-detail, efficient materials | Performance test |
| SC-005: 90% first-attempt success | Clear error messages, health check | User testing |
| SC-006: Smooth fly-through | UE5 camera tools, keyframe animation | Manual verification |

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Unreal Engine 5.8+ | External | User must install; free for internal use |
| UE5 MCP Plugin | External | Built into UE5.8; must be enabled |
| Topology data source | Internal | pyATS, SuzieQ, GNS3, or CML MCP server |
| Telemetry Receivers MCP (Feature 010) | Internal | For event-driven updates |
| httpx | Python package | HTTP client for MCP communication |

## Next Steps

After this plan is approved:
1. Run `/speckit.tasks` to generate task breakdown
2. Begin Phase 1 implementation
3. Test against live UE5 MCP server continuously
4. Complete artifact coherence checklist before merge
