# Tasks: Documentation & HUD Refresh

**Input**: Design documents from `/specs/038-docs-hud-refresh/`
**Prerequisites**: plan.md (required), spec.md (required), research.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Primary files**: `README.md`, `ui/netclaw-visual/README.md`, `workspace/SOUL.md`, `CLAUDE.md`
- **Source of truth**: `config/openclaw.json`, `workspace/skills/`

---

## Phase 1: User Story 1 - Accurate Skill Count Display (Priority: P1) 🎯 MVP

**Goal**: Update all skill and MCP server counts in README.md to reflect verified values (179 skills, 43 MCP servers)

**Independent Test**: Run `find workspace/skills -maxdepth 1 -type d | tail -n +2 | wc -l` and compare against counts in README. Run `jq '.mcpServers | keys | length' config/openclaw.json` and compare against README.

### Implementation for User Story 1

- [x] T001 [US1] Update header paragraph skill count (113→179) and MCP count (67→43) in README.md line 7
- [x] T002 [US1] Update installer description skill count (113→179) and MCP count (67→43) in README.md line 19
- [x] T003 [US1] Search README.md for any remaining "113 skills" references and update to "179 skills"
- [x] T004 [US1] Search README.md for any remaining "67 MCP" references and update to "43 MCP servers"
- [x] T005 [US1] Verify no outdated counts remain in README.md by searching for "113", "67 MCP", "48 integrations", "103 skills"

**Checkpoint**: README.md now displays accurate skill and MCP server counts

---

## Phase 2: User Story 2 - Complete MCP Integration List (Priority: P1)

**Goal**: Add all missing MCP integrations from PRs #031-#075 to the README "What It Does" section

**Independent Test**: Compare README integration descriptions against `jq '.mcpServers | keys' config/openclaw.json` output - all 43 servers should be represented

### Implementation for User Story 2

- [x] T006 [US2] Add Forward Networks integration description to "What It Does" section in README.md (NQE queries, path verification, digital twin)
- [x] T007 [P] [US2] Add Claroty xDome integration description to "What It Does" section in README.md (21 tools, OT/IoT asset inventory, Purdue Model)
- [x] T008 [P] [US2] Add IP Fabric integration description to "What It Does" section in README.md (network assurance, intent verification)
- [x] T009 [P] [US2] Add EVE-NG integration description to "What It Does" section in README.md (lab management, node operations, topology)
- [x] T010 [P] [US2] Add HumanRail integration description to "What It Does" section in README.md (human-in-the-loop escalation)
- [x] T011 [P] [US2] Add Nautobot integration description to "What It Does" section in README.md (3 MCP servers: core, golden-config, routing)
- [x] T012 [P] [US2] Add Ollama MCP integration description to "What It Does" section in README.md (local LLM inference)
- [x] T013 [US2] Verify Checkpoint Security (15 chkp-* servers) is fully documented in README.md - update if incomplete
- [x] T014 [US2] Verify Memory MCP and Layered Memory descriptions are complete in README.md - update if incomplete
- [x] T015 [US2] Review entire "What It Does" section to ensure all 43 MCP servers are represented

**Checkpoint**: All MCP integrations from PRs #031-#075 are documented in README.md

---

## Phase 3: User Story 3 - Updated Feature Descriptions (Priority: P2)

**Goal**: Ensure all feature descriptions accurately reflect current capabilities

**Independent Test**: Read each feature description and verify it matches the actual implementation in the corresponding MCP server or skill

### Implementation for User Story 3

- [x] T016 [US3] Review and update Layered Memory description in README.md to match PR #069/#070 implementation
- [x] T017 [P] [US3] Review and update DefenseClaw/OpenShell description in README.md to match PR #059 implementation
- [x] T018 [P] [US3] Review and update GNS3 description in README.md to match current implementation
- [x] T019 [P] [US3] Review and update Prisma SD-WAN description in README.md to match current implementation
- [x] T020 [US3] Review "Enterprise Security" section in README.md for accuracy and completeness

**Checkpoint**: All feature descriptions in README.md accurately reflect current capabilities

---

## Phase 4: User Story 4 - Consistent Visual HUD References (Priority: P2)

**Goal**: Update Visual HUD documentation to reflect accurate counts and capabilities

**Independent Test**: Compare ui/netclaw-visual/README.md counts against verified values (179 skills, 43 MCP servers)

### Implementation for User Story 4

- [x] T021 [US4] Read ui/netclaw-visual/README.md to identify outdated counts
- [x] T022 [US4] Update Visual HUD skill count (103→179) in ui/netclaw-visual/README.md
- [x] T023 [US4] Update Visual HUD integration count (48→43 MCP servers) in ui/netclaw-visual/README.md
- [x] T024 [US4] Update README.md HUD section (line 96 area) to reflect "43 MCP servers, 179 skills"
- [x] T025 [US4] Verify HUD feature descriptions match current UI capabilities in ui/netclaw-visual/README.md

**Checkpoint**: Visual HUD documentation reflects accurate counts and capabilities

---

## Phase 5: User Story 5 - Updated SOUL Files (Priority: P3)

**Goal**: Ensure SOUL.md reflects current architecture patterns and technologies

**Independent Test**: Review workspace/SOUL.md against current codebase structure and patterns

### Implementation for User Story 5

- [x] T026 [US5] Read workspace/SOUL.md to assess current state
- [x] T027 [US5] Update workspace/SOUL.md skill count and capability summary
- [x] T028 [US5] Verify workspace/SOUL.md architecture patterns match current implementation
- [x] T029 [US5] Add any missing capability summaries for new integrations in workspace/SOUL.md

**Checkpoint**: SOUL.md accurately reflects current architecture and capabilities

---

## Phase 6: Polish & Verification

**Purpose**: Final verification and cross-cutting concerns

- [x] T030 Run verification: `find workspace/skills -maxdepth 1 -type d | tail -n +2 | wc -l` confirms 179 skills
- [x] T031 Run verification: `jq '.mcpServers | keys | length' config/openclaw.json` confirms 43 MCP servers
- [x] T032 Search all updated files for outdated counts (113, 67, 103, 48) to ensure none remain
- [x] T033 Verify CLAUDE.md includes recent feature additions (auto-generated - review only)
- [x] T034 Git add all changed files and prepare for PR

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (US1)**: No dependencies - can start immediately (P1 MVP)
- **Phase 2 (US2)**: No dependencies - can start in parallel with Phase 1 (P1)
- **Phase 3 (US3)**: Best after Phase 2 completion (references integration descriptions)
- **Phase 4 (US4)**: Can start in parallel with Phase 1/2 (different files)
- **Phase 5 (US5)**: Can start in parallel (different file)
- **Phase 6 (Polish)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies - README count updates
- **User Story 2 (P1)**: No dependencies - README integration descriptions
- **User Story 3 (P2)**: Best after US2 (reviews same sections)
- **User Story 4 (P2)**: No dependencies - Visual HUD updates (different file)
- **User Story 5 (P3)**: No dependencies - SOUL.md updates (different file)

### Parallel Opportunities

Tasks can be parallelized when working on different files:

**Parallel Group A** (README.md focus - serialize within group):
- T001-T005 (US1: counts)
- T006-T015 (US2: integrations)
- T016-T020 (US3: descriptions)

**Parallel Group B** (ui/netclaw-visual/README.md):
- T021-T025 (US4: HUD docs)

**Parallel Group C** (workspace/SOUL.md):
- T026-T029 (US5: SOUL files)

---

## Parallel Example: Initial Phase

```bash
# These can run in parallel (different files):
Task T001-T005: Update README.md counts (US1)
Task T021-T025: Update ui/netclaw-visual/README.md (US4)
Task T026-T029: Update workspace/SOUL.md (US5)
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: US1 - Fix skill/MCP counts in README.md
2. Complete Phase 2: US2 - Add missing integration descriptions
3. **STOP and VALIDATE**: Verify counts match codebase
4. This delivers the most critical fixes

### Incremental Delivery

1. Complete US1 + US2 → Core README accuracy restored
2. Complete US3 → Feature descriptions updated
3. Complete US4 → Visual HUD aligned
4. Complete US5 → SOUL files current
5. Complete Polish → All verification passed, ready for PR

### Parallel Strategy

With parallel execution:
1. Start US1 (README counts), US4 (HUD), US5 (SOUL) simultaneously
2. Continue US2 (README integrations) after US1 count updates
3. Continue US3 (README descriptions) after US2 integration additions
4. Final verification when all complete

---

## Notes

- All tasks are documentation-only (no code changes)
- Verify counts against codebase before finalizing
- Use `find` and `jq` commands to validate accuracy
- Commit after each logical group of changes
- Stop at any checkpoint to validate independently
