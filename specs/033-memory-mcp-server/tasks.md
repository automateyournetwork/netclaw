# Tasks: Hybrid Memory MCP Server

**Input**: Design documents from `/specs/033-memory-mcp-server/`
**Prerequisites**: plan.md, spec.md, data-model.md

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Create directory structure: mcp-servers/memory-mcp/ with __init__.py
- [X] T002 Create requirements.txt (fastmcp, chromadb, sentence-transformers)
- [X] T003 [P] Create skill directory: workspace/skills/memory-management/
- [ ] T004 [P] Create memory/ directory with .gitkeep (runtime storage, gitignored)
- [X] T005 Create Dockerfile for containerized deployment (isolates torch/chromadb from host)
- [X] T006 Create docker-compose.yml for dev usage

---

## Phase 2: Structured Store (SQLite)

- [X] T007 Implement models.py with dataclasses: Fact, Decision, SessionSummary
- [X] T008 Implement structured_store.py: schema init (CREATE TABLE + indexes), connection management, auto-create DB file
- [X] T009 Implement structured_store.py: record_fact() with auto-supersession of existing entity+key facts
- [X] T010 Implement structured_store.py: get_facts(entity, key=None) returning current (valid_to IS NULL) facts
- [X] T011 Implement structured_store.py: timeline(entity, start, end) returning all facts (including invalidated) in range
- [X] T012 Implement structured_store.py: invalidate(fact_id, reason) setting valid_to
- [X] T013 Implement structured_store.py: record_decision() and get_decisions(entity=None, after=None, before=None, search=None)

**Checkpoint**: SQLite layer complete. Facts and decisions can be stored and queried. ✓ Validated.

---

## Phase 3: Semantic Store (ChromaDB)

- [X] T014 Implement semantic_store.py: lazy initialization of ChromaDB client + sentence-transformers model with graceful fallback
- [X] T015 Implement semantic_store.py: store_session(summary, entities, topics, session_id) — embed and persist
- [X] T016 Implement semantic_store.py: recall(query, top_k=5, threshold=0.3, after=None) — similarity search with metadata filtering

**Checkpoint**: Semantic layer complete. Needs Docker build to validate (deps not on host). Graceful degradation verified.

---

## Phase 4: MCP Server

- [X] T017 Implement server.py: FastMCP skeleton with stdio transport, startup validation, GAIT helper
- [X] T018 Implement server.py: memory_record_fact tool (delegates to structured_store, logs GAIT)
- [X] T019 Implement server.py: memory_get_facts tool
- [X] T020 Implement server.py: memory_timeline tool
- [X] T021 Implement server.py: memory_invalidate tool (logs GAIT)
- [X] T022 Implement server.py: memory_record_decision tool (logs GAIT)
- [X] T023 Implement server.py: memory_get_decisions tool
- [X] T024 Implement server.py: memory_store_session tool (logs GAIT, graceful degradation)
- [X] T025 Implement server.py: memory_recall tool (graceful degradation)

**Checkpoint**: All 8 tools exposed via MCP. Server imports validated. ✓

---

## Phase 5: Integration & Polish

- [X] T026 Docker build + validate full stack (semantic + structured) inside container
- [X] T027 [P] Register in config/openclaw.json with Docker stdio command
- [X] T028 [P] Create SKILL.md documenting when/how the agent should use memory tools
- [X] T029 [P] Create mcp-servers/memory-mcp/README.md with tool inventory and examples
- [X] T030 [P] Update .env.example with memory env vars
- [X] T031 [P] Update workspace/user/TOOLS.md with memory MCP reference
- [X] T032 [P] Add memory/ to .gitignore (runtime data, not committed)
- [X] T033 Verify existing MCP servers unaffected (backwards compatibility)

---

## Dependencies & Execution Order

- Phase 1: No dependencies ✓ DONE
- Phase 2: Depends on Phase 1 ✓ DONE (validated on host — SQLite is stdlib)
- Phase 3: Depends on Phase 1 ✓ DONE (validated inside Docker — embeddings work)
- Phase 4: Depends on Phase 2 + Phase 3 ✓ DONE (server imports validated)
- Phase 5: Depends on Phase 4 ✓ DONE (Docker built, e2e tested, registered in openclaw.json)

## Implementation Strategy

1. ~~Phase 1 + Phase 2 → validate SQLite layer standalone~~ ✓
2. ~~Phase 3 → validated embeddings + recall inside Docker~~ ✓
3. ~~Phase 4 → wire into MCP, server imports clean~~ ✓
4. ~~Phase 5 → Docker build, end-to-end test, registered in openclaw.json~~ ✓

## Validation Results

- Structured store: record → get → supersede → timeline → invalidate → decisions ✓
- Semantic store: embed session → recall by similar query (0.624 similarity) → threshold filters unrelated (0 results) ✓
- Graceful degradation: when deps missing, SQLite tools work, semantic tools return SEMANTIC_UNAVAILABLE ✓
- Docker image: builds from cache, ~2GB, all deps isolated ✓
- openclaw.json: 18 servers registered, existing 17 unaffected ✓
