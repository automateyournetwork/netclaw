# Tasks: Hybrid Memory MCP Server

**Input**: Design documents from `/specs/033-memory-mcp/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included based on pytest requirements from plan.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md project structure:

```text
mcp-servers/memory-mcp/
├── memory_mcp_server.py    # Main FastMCP server
├── storage/
│   ├── __init__.py
│   ├── sqlite_store.py     # Structured storage (facts, decisions, links)
│   ├── chroma_store.py     # Semantic storage (sessions)
│   └── schema.sql          # SQLite schema
├── embeddings/
│   ├── __init__.py
│   └── embedder.py         # Sentence-transformers wrapper
├── pyproject.toml          # Python package config (uvx)
└── README.md               # MCP server documentation

scripts/
└── memory-enable.sh        # Enable script for existing users

workspace/skills/memory/
└── SKILL.md                # Skill documentation

tests/
├── unit/
│   ├── test_sqlite_store.py
│   ├── test_chroma_store.py
│   └── test_embedder.py
├── integration/
│   └── test_memory_mcp.py
└── contract/
    └── test_mcp_tools.py
```

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and configure dependencies

- [x] T001 Create project directory structure: mcp-servers/memory-mcp/ with storage/, embeddings/ subdirectories
- [x] T002 Create mcp-servers/memory-mcp/pyproject.toml with dependencies: fastmcp, chromadb, sentence-transformers, torch (CPU), and uvx entry point
- [x] T003 [P] Create mcp-servers/memory-mcp/storage/__init__.py with module exports
- [x] T004 [P] Create mcp-servers/memory-mcp/embeddings/__init__.py with module exports
- [x] T005 [P] Create mcp-servers/memory-mcp/storage/schema.sql with SQLite schema from data-model.md
- [x] T006 Create tests/ directory structure: tests/unit/, tests/integration/, tests/contract/
- [x] T007 [P] Create scripts/memory-enable.sh installation script for existing users (uvx-based)
- [x] T008 Create workspace/skills/memory/SKILL.md with skill documentation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T009 Implement SQLite connection manager with WAL mode in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T010 Add database initialization and schema migration logic in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T011 [P] Implement embedder wrapper with lazy model loading in mcp-servers/memory-mcp/embeddings/embedder.py
- [x] T012 [P] Implement ChromaDB PersistentClient setup in mcp-servers/memory-mcp/storage/chroma_store.py
- [x] T013 Create FastMCP server skeleton with response format helpers in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T014 [P] Implement entity name normalization utility (lowercase) in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T015 [P] Implement validation utilities (entity length, JSON metadata, timestamps) in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T016 Add GAIT logging integration for write operations in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T017 Configure uvx entry point and test local installation in mcp-servers/memory-mcp/pyproject.toml
- [x] T018 [P] Create tests/unit/test_sqlite_store.py with connection and schema tests
- [x] T019 [P] Create tests/unit/test_chroma_store.py with ChromaDB initialization tests
- [x] T020 [P] Create tests/unit/test_embedder.py with embedding generation tests

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Record and Recall Network Facts (Priority: P1)

**Goal**: Enable storing and retrieving factual information about network entities with temporal validity

**Independent Test**: Store a fact about PE2, query it by entity, verify fact returned with correct timestamp and metadata

### Tests for User Story 1

- [x] T021 [P] [US1] Contract test for memory_record_fact in tests/contract/test_mcp_tools.py
- [x] T022 [P] [US1] Contract test for memory_get_facts in tests/contract/test_mcp_tools.py
- [x] T023 [P] [US1] Integration test for fact recording flow in tests/integration/test_memory_mcp.py

### Implementation for User Story 1

- [x] T024 [US1] Implement insert_fact method with supersession logic in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T025 [US1] Implement get_current_facts method with entity filtering in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T026 [US1] Implement memory_record_fact MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T027 [US1] Implement memory_get_facts MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T028 [US1] Add fact validation (entity, key, value length checks) in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T029 [US1] Add GAIT logging for memory_record_fact in mcp-servers/memory-mcp/memory_mcp_server.py

**Checkpoint**: User Story 1 complete - facts can be recorded and queried

---

## Phase 4: User Story 2 - Semantic Recall Across Sessions (Priority: P2)

**Goal**: Enable fuzzy recall of past sessions through semantic search

**Independent Test**: Store a session summary about BGP troubleshooting, query "BGP flapping problem", verify relevant session returned with high similarity score

### Tests for User Story 2

- [x] T030 [P] [US2] Contract test for memory_store_session in tests/contract/test_mcp_tools.py
- [x] T031 [P] [US2] Contract test for memory_recall in tests/contract/test_mcp_tools.py
- [x] T032 [P] [US2] Integration test for semantic search flow in tests/integration/test_memory_mcp.py

### Implementation for User Story 2

- [x] T033 [US2] Implement store_session method with embedding in mcp-servers/memory-mcp/storage/chroma_store.py
- [x] T034 [US2] Implement semantic_search method with similarity threshold in mcp-servers/memory-mcp/storage/chroma_store.py
- [x] T035 [US2] Implement memory_store_session MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T036 [US2] Implement memory_recall MCP tool with filtering in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T037 [US2] Add graceful degradation when ChromaDB unavailable in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T038 [US2] Add GAIT logging for memory_store_session in mcp-servers/memory-mcp/memory_mcp_server.py

**Checkpoint**: User Story 2 complete - sessions can be stored and recalled semantically

---

## Phase 5: User Story 3 - Decision Log with Rationale (Priority: P3)

**Goal**: Enable recording and retrieving operational decisions with full context

**Independent Test**: Record a decision with context, rationale, and CR number; retrieve by entity and verify all fields preserved

### Tests for User Story 3

- [x] T039 [P] [US3] Contract test for memory_record_decision in tests/contract/test_mcp_tools.py
- [x] T040 [P] [US3] Contract test for memory_get_decisions in tests/contract/test_mcp_tools.py
- [x] T041 [P] [US3] Integration test for decision recording flow in tests/integration/test_memory_mcp.py

### Implementation for User Story 3

- [x] T042 [US3] Implement insert_decision method in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T043 [US3] Implement query_decisions method with entity/time filtering in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T044 [US3] Implement memory_record_decision MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T045 [US3] Implement memory_get_decisions MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T046 [US3] Add CR number validation (CHG pattern) in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T047 [US3] Add GAIT logging for memory_record_decision in mcp-servers/memory-mcp/memory_mcp_server.py

**Checkpoint**: User Story 3 complete - decisions can be recorded and queried

---

## Phase 6: User Story 4 - Entity Relationship Tracking (Priority: P4)

**Goal**: Enable tracking and querying relationships between network entities

**Independent Test**: Create a link between PE2 and RR1 with "peers_with" predicate; query graph for PE2 and verify relationship returned

### Tests for User Story 4

- [x] T048 [P] [US4] Contract test for memory_link_entities in tests/contract/test_mcp_tools.py
- [x] T049 [P] [US4] Contract test for memory_query_graph in tests/contract/test_mcp_tools.py
- [x] T050 [P] [US4] Integration test for graph traversal in tests/integration/test_memory_mcp.py

### Implementation for User Story 4

- [x] T051 [US4] Implement insert_link method with duplicate handling in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T052 [US4] Implement query_graph method with direction filtering in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T053 [US4] Implement recursive graph traversal (depth > 1) in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T054 [US4] Implement memory_link_entities MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T055 [US4] Implement memory_query_graph MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T056 [US4] Add predicate validation and standard predicate documentation in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T057 [US4] Add GAIT logging for memory_link_entities in mcp-servers/memory-mcp/memory_mcp_server.py

**Checkpoint**: User Story 4 complete - entity relationships can be tracked and queried

---

## Phase 7: User Story 5 - Fact Lifecycle Management (Priority: P5)

**Goal**: Enable fact invalidation and historical timeline queries

**Independent Test**: Record a fact, invalidate it with reason, verify it no longer appears in current queries but still appears in timeline queries

### Tests for User Story 5

- [x] T058 [P] [US5] Contract test for memory_invalidate in tests/contract/test_mcp_tools.py
- [x] T059 [P] [US5] Contract test for memory_timeline in tests/contract/test_mcp_tools.py
- [x] T060 [P] [US5] Integration test for fact lifecycle in tests/integration/test_memory_mcp.py

### Implementation for User Story 5

- [x] T061 [US5] Implement invalidate_fact method with reason storage in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T062 [US5] Implement get_timeline method with time range filtering in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T063 [US5] Implement memory_invalidate MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T064 [US5] Implement memory_timeline MCP tool in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T065 [US5] Add timestamp validation (ISO format) in mcp-servers/memory-mcp/memory_mcp_server.py
- [x] T066 [US5] Add GAIT logging for memory_invalidate in mcp-servers/memory-mcp/memory_mcp_server.py

**Checkpoint**: User Story 5 complete - full fact lifecycle management available

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Data retention, documentation, and production readiness

- [x] T067 Implement auto-prune logic for data older than 1 year in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T068 [P] Add write queue serialization for concurrent access in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T069 [P] Create mcp-servers/memory-mcp/README.md with setup and usage documentation
- [x] T070 [P] Add error handling for database corruption recovery in mcp-servers/memory-mcp/storage/sqlite_store.py
- [x] T071 [P] Add error handling for ChromaDB failures (graceful degradation) in mcp-servers/memory-mcp/storage/chroma_store.py
- [x] T072 Add lazy model loading with cache warming option in mcp-servers/memory-mcp/embeddings/embedder.py
- [x] T073 [P] Run quickstart.md validation - test all example commands
- [x] T074 [P] Update project TOOLS.md with memory MCP server entry
- [x] T075 [P] Update workspace/SOUL-SKILLS.md with memory skill documentation
- [x] T076 Create WordPress blog post draft for feature announcement

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Independent of US1/US2/US3
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Builds on US1 fact storage

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Storage methods before MCP tools
- Core implementation before validation/error handling
- GAIT logging as final step per story

### Parallel Opportunities

- T003, T004, T005 can run in parallel (different files)
- T007, T008 can run in parallel with T005, T006
- T011, T012 can run in parallel (different storage backends)
- T014, T015 can run in parallel (different utility functions)
- T018, T019, T020 can run in parallel (unit tests)
- All contract tests within a user story can run in parallel
- Once Foundational phase completes, all user stories can start in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for memory_record_fact in tests/contract/test_mcp_tools.py"
Task: "Contract test for memory_get_facts in tests/contract/test_mcp_tools.py"
Task: "Integration test for fact recording flow in tests/integration/test_memory_mcp.py"

# After tests written, launch storage methods in parallel:
Task: "Implement insert_fact method in storage/sqlite_store.py"
Task: "Implement get_current_facts method in storage/sqlite_store.py"
```

---

## Parallel Example: All User Stories After Foundation

```bash
# With multiple developers, after Phase 2 complete:
Developer A: Phase 3 (User Story 1 - Facts)
Developer B: Phase 4 (User Story 2 - Semantic)
Developer C: Phase 5 (User Story 3 - Decisions)
Developer D: Phase 6 (User Story 4 - Graph)
Developer E: Phase 7 (User Story 5 - Lifecycle)

# Each story completes and integrates independently
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Facts)
4. **STOP and VALIDATE**: Test fact recording/retrieval independently
5. Deploy/demo if ready - agent can now remember facts!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP - basic memory!)
3. Add User Story 2 → Test independently → Deploy (semantic search!)
4. Add User Story 3 → Test independently → Deploy (decision audit!)
5. Add User Story 4 → Test independently → Deploy (graph queries!)
6. Add User Story 5 → Test independently → Deploy (full lifecycle!)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Facts - highest priority)
   - Developer B: User Story 2 (Semantic - independent)
   - Developer C: User Story 3 (Decisions - independent)
3. Stories 4 and 5 can start once capacity frees up
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Deployment: uvx package (OpenShell provides container isolation)
- Cold start target: <30 seconds (after model cached)
- Fact retrieval target: <1 second for 100K facts
