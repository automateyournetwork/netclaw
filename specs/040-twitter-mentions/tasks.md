# Tasks: Twitter Bidirectional Interaction

**Input**: Design documents from `/specs/040-twitter-mentions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.json

**Tests**: Not explicitly requested - manual testing via Twitter mentions per quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- **MCP Server**: `mcp-servers/twitter-mcp/`
- **Skills**: `workspace/skills/twitter-respond/`
- **HUD**: `ui/netclaw-visual/src/panels/`
- **Docs**: `specs/040-twitter-mentions/`

---

## Phase 1: Setup

**Purpose**: Project structure for bidirectional Twitter features

- [x] T001 Create mentions module file mcp-servers/twitter-mcp/mentions.py
- [x] T002 Create replies module file mcp-servers/twitter-mcp/replies.py
- [x] T003 Create twitter-respond skill directory workspace/skills/twitter-respond/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement get_authenticated_user_id() function in mcp-servers/twitter-mcp/mentions.py to resolve @John_Capobianco to user ID
- [x] T005 [P] Implement ProcessedMentionTracker class in mcp-servers/twitter-mcp/mentions.py with Memory MCP integration
- [x] T006 [P] Implement mention classification logic (netclaw_request, technical_network, friendly, off_topic, spam) in mcp-servers/twitter-mcp/mentions.py
- [x] T007 [P] Implement spam detection heuristics in mcp-servers/twitter-mcp/mentions.py per research.md
- [x] T008 Add TWITTER_MENTION_POLL_INTERVAL environment variable support in mcp-servers/twitter-mcp/server.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Mention Detection (Priority: P1) 🎯 MVP

**Goal**: Detect @mentions of @John_Capobianco and display them for review

**Independent Test**: Tweet "@John_Capobianco test question" from another account, verify NetClaw retrieves and displays it

### Implementation for User Story 1

- [x] T009 [US1] Implement fetch_mentions() function using tweepy client.get_users_mentions() in mcp-servers/twitter-mcp/mentions.py
- [x] T010 [US1] Implement twitter_get_mentions MCP tool in mcp-servers/twitter-mcp/server.py per contracts/mcp-tools.json
- [x] T011 [US1] Implement twitter_classify_mention MCP tool in mcp-servers/twitter-mcp/server.py
- [x] T012 [US1] Implement twitter_mark_processed MCP tool in mcp-servers/twitter-mcp/server.py
- [x] T013 [US1] Add rate limit handling with exponential backoff in mcp-servers/twitter-mcp/mentions.py

**Checkpoint**: Mention detection fully functional - can retrieve and classify @mentions

---

## Phase 4: User Story 2 - Intelligent Reply Generation (Priority: P2)

**Goal**: Generate CCIE-level replies for technical questions

**Independent Test**: Provide a sample mention text and verify appropriate technical response is generated

### Implementation for User Story 2

- [x] T014 [US2] Create reply generation prompt template in workspace/skills/twitter-respond/prompts/reply_generation.md
- [x] T015 [US2] Implement generate_reply() function in mcp-servers/twitter-mcp/replies.py
- [x] T016 [US2] Implement twitter_generate_reply MCP tool in mcp-servers/twitter-mcp/server.py per contracts/mcp-tools.json
- [x] T017 [US2] Integrate content guardrails from existing guardrails.py for reply content validation
- [x] T018 [US2] Handle long replies (>280 chars) using existing tweet_threading.py

**Checkpoint**: Reply generation functional - produces relevant CCIE-level responses

---

## Phase 5: User Story 3 - Reply Posting with Approval (Priority: P2)

**Goal**: Post replies with mandatory human approval (Constitution Principle XIV)

**Independent Test**: Generate a reply and verify approval prompt appears before posting

### Implementation for User Story 3

- [x] T019 [US3] Implement post_reply() function with in_reply_to_tweet_id in mcp-servers/twitter-mcp/replies.py
- [x] T020 [US3] Implement twitter_reply_to_tweet MCP tool with approval requirement in mcp-servers/twitter-mcp/server.py
- [x] T021 [US3] Add reply audit logging to Memory MCP in mcp-servers/twitter-mcp/replies.py
- [x] T022 [US3] Verify reply threads correctly (appears in conversation) in mcp-servers/twitter-mcp/replies.py

**Checkpoint**: Reply posting functional with human approval gate

---

## Phase 6: User Story 4 - Conversation Context (Priority: P3)

**Goal**: Retrieve thread context for better reply quality

**Independent Test**: Reply to a tweet in a thread, verify parent tweets are retrieved

### Implementation for User Story 4

- [x] T023 [US4] Implement get_conversation_context() function in mcp-servers/twitter-mcp/mentions.py
- [x] T024 [US4] Implement twitter_get_conversation MCP tool in mcp-servers/twitter-mcp/server.py per contracts/mcp-tools.json
- [x] T025 [US4] Update twitter_generate_reply to accept and use conversation_context parameter

**Checkpoint**: Conversation context retrieval functional

---

## Phase 7: User Story 5 - Memory Integration (Priority: P3)

**Goal**: Remember past interactions with users for continuity

**Independent Test**: Have same user mention twice, verify prior interaction is referenced

### Implementation for User Story 5

- [x] T026 [US5] Implement InteractionHistory storage in Memory MCP via mcp-servers/twitter-mcp/mentions.py
- [x] T027 [US5] Implement twitter_get_user_history MCP tool in mcp-servers/twitter-mcp/server.py
- [x] T028 [US5] Update twitter_generate_reply to incorporate user history context

**Checkpoint**: Memory integration functional - past interactions inform replies

---

## Phase 8: Polish & Artifact Coherence

**Purpose**: Documentation, HUD updates, and cross-cutting concerns per Constitution Principle XI

### Documentation Updates

- [x] T029 [P] Create workspace/skills/twitter-respond/SKILL.md with workflow and tools documentation
- [x] T030 [P] Update mcp-servers/twitter-mcp/README.md with new tools (7 additional)
- [x] T031 [P] Update README.md with Twitter bidirectional capabilities
- [x] T032 [P] Update SOUL.md with twitter-respond skill (total skills: 182)
- [x] T033 [P] Update TOOLS.md with new twitter-mcp tools

### HUD Updates

- [x] T034 Update ui/netclaw-visual/src/panels/TwitterPanel.js to display mentions and replies

### Configuration Updates

- [x] T035 Add TWITTER_MENTION_POLL_INTERVAL to .env.example

### Final Validation

- [x] T036 Run quickstart.md validation - verify all setup steps work
- [x] T037 Verify skill count in README.md (182 after adding twitter-respond)
- [ ] T038 Git add all changed files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Independent of US1
- **User Story 3 (P2)**: Can start after US2 (needs reply generation)
- **User Story 4 (P3)**: Can start after Foundational - Enhances US2
- **User Story 5 (P3)**: Can start after Foundational - Enhances US2

### Within Each User Story

- Core implementation before integration
- MCP tool registration after underlying function
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 2: T005, T006, T007 can run in parallel (different functions)
- Phase 8: T029-T033 can run in parallel (different files)
- US4 and US5 can run in parallel after US2

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch in parallel:
Task: "Implement ProcessedMentionTracker class in mentions.py"
Task: "Implement mention classification logic in mentions.py"
Task: "Implement spam detection heuristics in mentions.py"
```

## Parallel Example: Phase 8 Documentation

```bash
# Launch all documentation updates together:
Task: "Create twitter-respond SKILL.md"
Task: "Update twitter-mcp README.md"
Task: "Update README.md"
Task: "Update SOUL.md"
Task: "Update TOOLS.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (3 tasks)
2. Complete Phase 2: Foundational (5 tasks)
3. Complete Phase 3: User Story 1 (5 tasks)
4. **STOP and VALIDATE**: Can retrieve and classify mentions
5. Deploy/demo mention detection capability

### Incremental Delivery

1. Setup + Foundational → Foundation ready (8 tasks)
2. Add US1 (Mention Detection) → Demo: "Show me my Twitter mentions"
3. Add US2 (Reply Generation) → Demo: "Generate a reply for that question"
4. Add US3 (Reply Posting) → Demo: Full reply workflow with approval
5. Add US4 (Conversation Context) → Enhanced reply quality
6. Add US5 (Memory) → Relationship continuity
7. Polish → Full artifact coherence

### Recommended Execution Order

1. **Phase 1-3**: MVP mention detection (13 tasks)
2. **Phase 4-5**: Reply capability (9 tasks)
3. **Phase 6-7**: Enhanced context (6 tasks)
4. **Phase 8**: Documentation and polish (10 tasks)

**Total**: 38 tasks

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story is independently testable
- Commit after each task or logical group
- Constitution Principle XIV: All replies require human approval (US3)
- Extends existing twitter-mcp server - do not break existing tools
