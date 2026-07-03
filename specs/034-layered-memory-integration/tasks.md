# Tasks: Layered Memory Integration

**Input**: Design documents from `/specs/034-layered-memory-integration/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Manual verification via 10 representative scenarios (no automated tests required for this documentation update)

**Organization**: Tasks grouped by user story - primary deliverable is SOUL.md update

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

## Path Conventions

- **SOUL.md**: `~/.openclaw/workspace/SOUL.md` (production) or project copy
- **MEMORY.md**: `~/.openclaw/workspace/MEMORY.md`
- **Config**: `~/.openclaw/config/openclaw.json`

---

## Phase 1: Setup

**Purpose**: Verify prerequisites and prepare for SOUL.md update

- [ ] T001 Verify Memory MCP server exists at mcp-servers/memory-mcp/memory_mcp_server.py
- [ ] T002 Verify Memory MCP is registered in ~/.openclaw/config/openclaw.json
- [ ] T003 [P] Verify MEMORY.md exists at ~/.openclaw/workspace/MEMORY.md (create if missing)
- [ ] T004 [P] Backup current SOUL.md to ~/.openclaw/workspace/SOUL.md.backup

---

## Phase 2: Foundational (SOUL.md Core Section)

**Purpose**: Add the layered memory section to SOUL.md - BLOCKS all user story validation

**⚠️ CRITICAL**: This section must be added before any memory behavior can be tested

- [ ] T005 Read contracts/soul-memory-section.md to get exact content to insert
- [ ] T006 Locate insertion point in SOUL.md (after "### GAIT: Always-On Audit Trail")
- [ ] T007 Insert "### Layered Memory: Your Two-Tier Brain" section from contract
- [ ] T008 Verify SOUL.md markdown structure is valid (no broken headings)
- [ ] T009 Restart OpenClaw gateway to pick up SOUL.md changes

**Checkpoint**: SOUL.md now contains layered memory instructions

---

## Phase 3: User Story 1 - Record Facts During Operation (Priority: P1) 🎯 MVP

**Goal**: Agent automatically records facts about network entities during troubleshooting

**Independent Test**: Ask NetClaw to check a device, then query `memory_get_facts` for that device

### Implementation for User Story 1

- [ ] T010 [US1] Verify SOUL.md section includes `memory_record_fact` tool reference
- [ ] T011 [US1] Verify SOUL.md includes instruction: "When you discover device state → memory_record_fact"
- [ ] T012 [US1] Verify SOUL.md includes GAIT logging instruction for fact recording
- [ ] T013 [US1] Manual test: Ask "Check BGP status on PE2" - verify fact is recorded
- [ ] T014 [US1] Manual test: Query `memory_get_facts entity="pe2"` - verify fact returned

**Checkpoint**: Facts are automatically recorded during troubleshooting

---

## Phase 4: User Story 2 - Query Recent Facts First (Priority: P1)

**Goal**: Agent queries Memory MCP before MEMORY.md when asked about entities

**Independent Test**: Record a fact, then ask about that device - should return Memory MCP fact first

### Implementation for User Story 2

- [ ] T015 [US2] Verify SOUL.md section includes query order instructions (Memory MCP → MEMORY.md)
- [ ] T016 [US2] Verify SOUL.md includes presentation labels ("Current State" vs "Historical Context")
- [ ] T017 [US2] Manual test: Add fact via `memory_record_fact`, then ask "What do you know about X?"
- [ ] T018 [US2] Manual test: Verify Memory MCP facts shown as "Current State"
- [ ] T019 [US2] Manual test: Verify MEMORY.md content shown as "Historical Context" when applicable

**Checkpoint**: Query order is Memory MCP first, MEMORY.md fallback

---

## Phase 5: User Story 3 - Semantic Session Recall (Priority: P2)

**Goal**: Users can search past sessions with natural language

**Independent Test**: Store sessions, then query with semantic search

### Implementation for User Story 3

- [ ] T020 [US3] Verify SOUL.md section includes `memory_store_session` tool reference
- [ ] T021 [US3] Verify SOUL.md section includes `memory_recall` tool reference
- [ ] T022 [US3] Verify SOUL.md includes semantic search instructions
- [ ] T023 [US3] Manual test: Store session via `memory_store_session summary="..." entities=[...] topics=[...]`
- [ ] T024 [US3] Manual test: Query via `memory_recall query="..."` - verify semantic results

**Checkpoint**: Semantic session search working

---

## Phase 6: User Story 4 - Record Decisions with Rationale (Priority: P2)

**Goal**: Operational decisions recorded with full context for audit

**Independent Test**: Make a decision, then query decisions for that entity

### Implementation for User Story 4

- [ ] T025 [US4] Verify SOUL.md section includes `memory_record_decision` tool reference
- [ ] T026 [US4] Verify SOUL.md includes instruction: "When you make/recommend a change → memory_record_decision"
- [ ] T027 [US4] Verify SOUL.md includes CR number field mention
- [ ] T028 [US4] Manual test: Record decision with context, rationale, entities
- [ ] T029 [US4] Manual test: Query `memory_get_decisions entity="..."` - verify decision returned

**Checkpoint**: Decisions recorded with full audit trail

---

## Phase 7: User Story 5 - Consolidate Patterns to Long-Term Memory (Priority: P3)

**Goal**: Patterns consolidated from Memory MCP to MEMORY.md at session end

**Independent Test**: Create 3+ similar facts, end session, check MEMORY.md for pattern

### Implementation for User Story 5

- [ ] T030 [US5] Verify SOUL.md section includes consolidation instructions (at session end)
- [ ] T031 [US5] Verify SOUL.md includes pattern threshold (3+ occurrences)
- [ ] T032 [US5] Verify SOUL.md includes MEMORY.md section structure for patterns
- [ ] T033 [US5] Manual test: Verify consolidation happens at session end (not during)

**Checkpoint**: Patterns consolidated to MEMORY.md

---

## Phase 8: User Story 6 - Track Entity Relationships (Priority: P3)

**Goal**: Entity relationships tracked for impact analysis

**Independent Test**: Create links, then query graph for dependencies

### Implementation for User Story 6

- [ ] T034 [US6] Verify SOUL.md section includes `memory_link_entities` tool reference
- [ ] T035 [US6] Verify SOUL.md section includes `memory_query_graph` tool reference
- [ ] T036 [US6] Verify SOUL.md includes standard predicates list
- [ ] T037 [US6] Manual test: Create link via `memory_link_entities subject="..." predicate="..." object="..."`
- [ ] T038 [US6] Manual test: Query via `memory_query_graph entity="..." direction="both"`

**Checkpoint**: Entity relationships tracked and queryable

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, and edge case testing

- [ ] T039 [P] Verify credential exclusion: Test that passwords/keys are NOT stored
- [ ] T040 [P] Verify GAIT logging: Check audit trail for all memory operations
- [ ] T041 [P] Test fallback behavior: Disable Memory MCP, verify MEMORY.md-only mode works
- [ ] T042 Update TOOLS.md with Memory MCP integration notes in TOOLS.md
- [ ] T043 Run 10 representative scenarios from spec SC-007 for validation
- [ ] T044 Update README.md with layered memory capability mention
- [ ] T045 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify prerequisites
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase
  - US1 and US2 are both P1 - complete both for MVP
  - US3 and US4 are both P2 - complete after P1 stories
  - US5 and US6 are both P3 - complete after P2 stories
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Record Facts)**: Can start after Foundational - No dependencies
- **US2 (Query Facts)**: Can start after Foundational - Tests build on US1 data
- **US3 (Semantic Recall)**: Can start after Foundational - Independent
- **US4 (Record Decisions)**: Can start after Foundational - Independent
- **US5 (Consolidate Patterns)**: Can start after Foundational - Tests need US1 data
- **US6 (Track Relationships)**: Can start after Foundational - Independent

### Parallel Opportunities

- T003 and T004 (Setup) can run in parallel
- US1 and US2 validation can run sequentially (US2 builds on US1 data)
- US3, US4, US6 can run in parallel (independent)
- T039, T040, T041 (Polish) can run in parallel

---

## Parallel Example: Setup Phase

```bash
# Launch backup and MEMORY.md check together:
Task T003: "Verify MEMORY.md exists at ~/.openclaw/workspace/MEMORY.md"
Task T004: "Backup current SOUL.md to ~/.openclaw/workspace/SOUL.md.backup"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational - Add SOUL.md section (T005-T009)
3. Complete Phase 3: User Story 1 - Record Facts (T010-T014)
4. Complete Phase 4: User Story 2 - Query Facts (T015-T019)
5. **STOP and VALIDATE**: Test fact recording and retrieval
6. Deploy if ready - basic memory working

### Incremental Delivery

1. MVP (US1 + US2) → Facts can be recorded and queried
2. Add US3 + US4 → Semantic search and decisions
3. Add US5 + US6 → Consolidation and relationships
4. Polish → Full validation suite

### Single Developer Strategy

Execute phases sequentially in priority order:
1. Setup + Foundational → SOUL.md ready
2. US1 → US2 → MVP complete
3. US3 → US4 → Full feature set
4. US5 → US6 → Advanced features
5. Polish → Production ready

---

## Notes

- Primary deliverable is SOUL.md update - all tasks verify content or test behavior
- Manual tests validate that the agent follows SOUL.md instructions
- Memory MCP server already exists (Feature 033) - this feature integrates it
- GAIT logging must be verified for audit compliance
- Credential exclusion is security-critical (FR-012)
- 10 representative scenarios (SC-007) are the acceptance test
