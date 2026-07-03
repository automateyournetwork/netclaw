# Tasks: IP Fabric MCP Integration

**Input**: Design documents from `/specs/032-ipfabric-mcp-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md
**Branch**: `032-ipfabric-mcp-integration`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. This is an integration feature (no new MCP server code) - deliverables are configuration, scripts, skill definition, and documentation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US8)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: MCP configuration and environment setup - foundation for all IP Fabric capabilities

- [x] T001 Add IP Fabric MCP server configuration to `~/.openclaw/openclaw.json` under `mcp.servers` using mcp-remote proxy pattern
- [x] T002 [P] Add IPFABRIC_HOST and IPFABRIC_API_TOKEN to `.env.example` with documentation comments
- [x] T003 [P] Create `workspace/skills/ipfabric/` directory structure

**Checkpoint**: MCP server registered, environment variables documented

---

## Phase 2: User Story 8 - Installation and Onboarding (Priority: P1) 🎯 MVP

**Goal**: Enable frictionless setup for both new and existing NetClaw users

**Independent Test**: Run `scripts/ipfabric-enable.sh`, configure credentials, verify MCP connection with `openclaw mcp list | grep ipfabric`

### Implementation for User Story 8

- [x] T004 [US8] Create `scripts/ipfabric-enable.sh` for existing installations (follow checkpoint-enable.sh pattern, but simpler - no clone/build needed since it's remote MCP)
- [x] T005 [US8] Update `scripts/install.sh` to add IP Fabric integration step after Check Point section (~line 200+ area)
- [x] T006 [US8] Add connectivity verification to ipfabric-enable.sh (test MCP endpoint reachability)
- [x] T007 [US8] Add placeholder variable support for users who skip credential entry

**Checkpoint**: Both new and existing users can enable IP Fabric integration in under 5 minutes

---

## Phase 3: User Story 1 - Network Health Assessment (Priority: P1)

**Goal**: SOC analysts can query network health using natural language

**Independent Test**: Query "check network health" against configured IP Fabric instance

### Implementation for User Story 1

- [x] T008 [US1] Create `workspace/skills/ipfabric/SKILL.md` with health assessment examples and tool routing documentation
- [x] T009 [US1] Add health assessment query patterns to SKILL.md (health, status, issues, BGP, OSPF, routing)
- [x] T010 [US1] Document `ipf_network_health_assess` tool parameters and response format in SKILL.md

**Checkpoint**: Health queries route correctly to ipf_network_health_assess tool

---

## Phase 4: User Story 2 - Path Analysis with Visual Diagrams (Priority: P1)

**Goal**: Network engineers can trace paths and get visual diagrams

**Independent Test**: Query "show path from 10.0.1.5 to 10.0.2.10 with diagram" - verify PNG returned

### Implementation for User Story 2

- [x] T011 [US2] Add path lookup query patterns to `workspace/skills/ipfabric/SKILL.md` (unicast, host-to-gateway, multicast)
- [x] T012 [US2] Add diagram request patterns to SKILL.md (diagram, png, visualize keywords)
- [x] T013 [US2] Document VRF-aware path lookup parameters in SKILL.md
- [x] T014 [US2] Document PNG diagram handling (base64 response, file attachment to messaging channels)

**Checkpoint**: Path queries with "diagram" return PNG visualizations

---

## Phase 5: User Story 3 - Device Inventory Queries (Priority: P2)

**Goal**: Operations team can query device inventory by various criteria

**Independent Test**: Query "show all Cisco devices in site HQ" - verify filtered results

### Implementation for User Story 3

- [x] T015 [US3] Add inventory query patterns to `workspace/skills/ipfabric/SKILL.md` (devices, vendor, site, uptime)
- [x] T016 [US3] Document `api_invoke` usage for custom inventory queries in SKILL.md

**Checkpoint**: Inventory queries route correctly to api_invoke with proper filters

---

## Phase 6: User Story 4 - Routing Protocol Troubleshooting (Priority: P2)

**Goal**: Network engineers can diagnose BGP/OSPF adjacency issues

**Independent Test**: Query "show BGP neighbors not in Established state"

### Implementation for User Story 4

- [x] T017 [US4] Add routing protocol query patterns to `workspace/skills/ipfabric/SKILL.md` (BGP, OSPF, adjacency)
- [x] T018 [US4] Document protocol-specific filtering in health assessment results

**Checkpoint**: Routing queries extract relevant protocol data from health assessment

---

## Phase 7: User Story 5 - Intent Validation and Compliance (Priority: P2)

**Goal**: Security/compliance teams can validate network against intent rules

**Independent Test**: Query "are there any intent violations"

### Implementation for User Story 5

- [x] T019 [US5] Add intent/compliance query patterns to `workspace/skills/ipfabric/SKILL.md`
- [x] T020 [US5] Document intent rule severity levels and filtering options

**Checkpoint**: Intent queries return compliance status with severity filtering

---

## Phase 8: User Story 6 - Advanced API Discovery (Priority: P3)

**Goal**: Power users can discover and invoke arbitrary IP Fabric APIs

**Independent Test**: Query "find endpoints for device inventory" then invoke discovered endpoint

### Implementation for User Story 6

- [x] T021 [US6] Add API discovery patterns to `workspace/skills/ipfabric/SKILL.md` (find endpoint, api for)
- [x] T022 [US6] Document `ipf_api_endpoint_search`, `ipf_api_endpoint_details`, and `api_invoke` workflow

**Checkpoint**: Power users can discover and invoke custom API endpoints

---

## Phase 9: User Story 7 - Cross-Platform Composition (Priority: P4)

**Goal**: Correlate IP Fabric data with other NetClaw skills

**Independent Test**: Query "compare IP Fabric topology with my CML lab" (requires both skills configured)

### Implementation for User Story 7

- [x] T023 [US7] Add cross-platform composition examples to `workspace/skills/ipfabric/SKILL.md`
- [x] T024 [US7] Document composition patterns with SuzieQ, Batfish, Check Point, CML/GNS3

**Checkpoint**: Documentation shows how to combine IP Fabric with other skills

---

## Phase 10: Documentation (Constitution XI Compliance)

**Purpose**: Full artifact coherence per NetClaw Constitution Principle XI

### README Updates

- [x] T025 [P] Add IP Fabric section to `README.md` (after Check Point section) with:
  - Partnership attribution (Daren Fulwell, John Capobianco)
  - Feature overview (10 MCP tools, network assurance, path analysis, diagrams)
  - Quick start reference
  - Link to docs/IPFABRIC.md

### SOUL File Updates (All 4 Files)

- [x] T026 [P] Update `SOUL.md` with IP Fabric expertise and partnership attribution
- [x] T027 [P] Update `SOUL-EXPERTISE.md` with IP Fabric network assurance capabilities
- [x] T028 [P] Update `SOUL-SKILLS.md` with `/ipfabric` skill entry and tool summary
- [x] T029 [P] Update `docs/SOUL-DEFENSE.md` with IP Fabric security considerations (RBAC, token safety)

### Detailed Documentation

- [x] T030 Create `docs/IPFABRIC.md` comprehensive guide with:
  - Prerequisites (IP Fabric appliance, MCP enabled, API token)
  - Installation (new and existing users)
  - Configuration (environment variables)
  - Tool reference (all 10 tools with parameters)
  - Query examples by use case
  - Diagram handling
  - Snapshot management
  - Troubleshooting
  - Cross-platform composition
  - Partnership attribution

**Checkpoint**: All documentation artifacts updated per Constitution XI

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and blog post

- [x] T031 Run `specs/032-ipfabric-mcp-integration/quickstart.md` validation against test instance
- [x] T032 Verify all 4 SOUL files have consistent IP Fabric references
- [x] T033 Verify MCP tools count in README.md is updated
- [x] T034 Test ipfabric-enable.sh end-to-end on clean environment
- [x] T035 Draft WordPress blog post for milestone documentation (Constitution XVII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 8 (Phase 2)**: Depends on Phase 1 - CRITICAL for other stories
- **User Stories 1-7 (Phases 3-9)**: All depend on Phase 2 completion (installation working)
- **Documentation (Phase 10)**: Can run in parallel with Phases 3-9
- **Polish (Phase 11)**: Depends on all previous phases

### User Story Dependencies

| Story | Depends On | Can Run In Parallel With |
|-------|------------|-------------------------|
| US8 (Installation) | Phase 1 | None - must complete first |
| US1 (Health) | US8 | US2, US3, US4, US5 |
| US2 (Path/Diagram) | US8 | US1, US3, US4, US5 |
| US3 (Inventory) | US8 | US1, US2, US4, US5 |
| US4 (Routing) | US8 | US1, US2, US3, US5 |
| US5 (Intent) | US8 | US1, US2, US3, US4 |
| US6 (API Discovery) | US1-US5 complete | None |
| US7 (Composition) | US6 | None |

### Parallel Opportunities

**Phase 1 (all parallel)**:
```
T001 (openclaw.json)
T002 (.env.example)
T003 (skill directory)
```

**Phase 10 Documentation (all parallel)**:
```
T025 (README.md)
T026 (SOUL.md)
T027 (SOUL-EXPERTISE.md)
T028 (SOUL-SKILLS.md)
T029 (docs/SOUL-DEFENSE.md)
```

---

## Implementation Strategy

### MVP First (User Stories 8 + 1)

1. Complete Phase 1: Setup (MCP config, env vars)
2. Complete Phase 2: User Story 8 (Installation)
3. Complete Phase 3: User Story 1 (Health Assessment)
4. **STOP and VALIDATE**: Test health queries work
5. Deploy/demo basic IP Fabric health queries

### Full Integration

1. Setup + US8 + US1 → MVP ready
2. Add US2 → Path analysis with diagrams
3. Add US3, US4, US5 → Full P2 capabilities
4. Add US6 → API discovery for power users
5. Add US7 → Cross-platform composition
6. Documentation sweep (Phase 10)
7. Polish and blog post (Phase 11)

---

## Artifact Coherence Checklist (Constitution XI)

```
[ ] README.md updated (IP Fabric section, tool count, partnership)
[ ] scripts/install.sh updated (IP Fabric integration step)
[ ] scripts/ipfabric-enable.sh created (existing user enablement)
[ ] SOUL.md updated (IP Fabric expertise, partnership)
[ ] SOUL-EXPERTISE.md updated (network assurance capabilities)
[ ] SOUL-SKILLS.md updated (/ipfabric skill entry)
[ ] docs/SOUL-DEFENSE.md updated (security considerations)
[ ] workspace/skills/ipfabric/SKILL.md created (full documentation)
[ ] .env.example updated (IPFABRIC_* variables)
[ ] ~/.openclaw/openclaw.json updated (MCP server registration)
[ ] docs/IPFABRIC.md created (detailed guide)
[ ] WordPress blog post drafted (at completion)
```

---

## Notes

- IP Fabric MCP is a **remote server** (built into IP Fabric appliances) - no clone/build steps
- Uses **mcp-remote proxy** via npx - simpler than Check Point integration
- Only **2 environment variables** needed: IPFABRIC_HOST, IPFABRIC_API_TOKEN
- All **4 SOUL files** must be updated per user's explicit request
- Partnership attribution (Daren Fulwell + John Capobianco) in SKILL.md and docs/IPFABRIC.md
- Existing users can enable via `ipfabric-enable.sh` script

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 35 |
| User Stories | 8 |
| P1 (MVP) Tasks | 14 (US8 + US1 + US2) |
| P2 Tasks | 6 (US3 + US4 + US5) |
| P3 Tasks | 2 (US6) |
| P4 Tasks | 2 (US7) |
| Documentation Tasks | 6 |
| Polish Tasks | 5 |
| Parallel Opportunities | 8 tasks in Phase 1+10 |
