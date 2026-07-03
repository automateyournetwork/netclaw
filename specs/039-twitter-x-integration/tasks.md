# Tasks: Twitter/X Integration (Free Tier)

**Input**: Design documents from `/specs/039-twitter-x-integration/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **MCP Server**: `mcp-servers/twitter-mcp/`
- **Skills**: `workspace/skills/twitter-heartbeat/`, `workspace/skills/twitter-share/`
- **HUD Component**: `ui/netclaw-visual/src/components/`
- **Config**: `config/openclaw.json`, `.env.example`

---

## Phase 1: Setup

**Purpose**: Project initialization and MCP server structure

- [x] T001 Create MCP server directory structure at mcp-servers/twitter-mcp/
- [x] T002 Create mcp-servers/twitter-mcp/requirements.txt with tweepy>=4.14.0, fastmcp, python-dotenv
- [x] T003 [P] Create mcp-servers/twitter-mcp/__init__.py (empty init file)

**Checkpoint**: MCP server skeleton ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement content guardrails module in mcp-servers/twitter-mcp/guardrails.py with IPv4, IPv6, MAC, credential, hostname patterns
- [x] T005 [P] Implement thread splitting module in mcp-servers/twitter-mcp/threading.py with sentence-boundary logic
- [x] T006 Implement base MCP server in mcp-servers/twitter-mcp/server.py with tweepy Client initialization and OAuth 1.0a setup
- [x] T007 Add twitter_post_tweet tool to mcp-servers/twitter-mcp/server.py with guardrail validation
- [x] T008 Add twitter_get_rate_limits tool to mcp-servers/twitter-mcp/server.py

**Checkpoint**: Foundation ready - MCP server can post single tweets with guardrails

---

## Phase 3: User Story 1 - Autonomous Heartbeat Tweets (Priority: P1) 🎯 MVP

**Goal**: NetClaw automatically tweets every 4 hours with CCIE-level network insights

**Independent Test**: Configure heartbeat interval, wait for scheduled tweet trigger, verify tweet appears with #netclaw hashtag

### Implementation for User Story 1

- [x] T009 [US1] Add heartbeat configuration loading from environment variables in mcp-servers/twitter-mcp/server.py
- [x] T010 [US1] Implement content category rotation logic (tip, hot_take, til, achievement, musing, community) in mcp-servers/twitter-mcp/server.py
- [x] T011 [US1] Add twitter_generate_heartbeat_content tool that selects category and generates CCIE-persona content in mcp-servers/twitter-mcp/server.py
- [x] T012 [US1] Create workspace/skills/twitter-heartbeat/SKILL.md with heartbeat workflow documentation
- [x] T013 [P] [US1] Create workspace/skills/twitter-heartbeat/prompts/ directory with category-specific generation prompts

**Checkpoint**: Heartbeat tweets can be generated and posted autonomously when enabled

---

## Phase 4: User Story 2 - Manual Tweet Posting (Priority: P1)

**Goal**: Users can ask NetClaw to tweet specific content with guardrails

**Independent Test**: Tell NetClaw "tweet about BGP path selection", verify tweet is posted with CCIE voice and #netclaw

### Implementation for User Story 2

- [x] T014 [US2] Add twitter_post_thread tool to mcp-servers/twitter-mcp/server.py using threading.py for content >280 chars
- [x] T015 [P] [US2] Add twitter_post_tweet_with_media tool to mcp-servers/twitter-mcp/server.py with image upload via tweepy v1.1 API
- [x] T016 [P] [US2] Add twitter_delete_tweet tool to mcp-servers/twitter-mcp/server.py
- [x] T017 [US2] Create workspace/skills/twitter-share/SKILL.md with manual tweet workflow documentation
- [x] T018 [US2] Add human approval prompt flow to twitter-share skill (Principle XIV compliance)

**Checkpoint**: Users can request manual tweets with full content validation and approval flow

---

## Phase 5: User Story 3 - Memory-Driven Content (Priority: P2)

**Goal**: NetClaw uses persistent memory to generate authentic, personalized tweets from actual experiences

**Independent Test**: Complete several network tasks, verify heartbeat tweets reference sanitized achievements from memory

### Implementation for User Story 3

- [x] T019 [US3] Add Memory MCP integration for tweet history storage (twitter_history namespace) in mcp-servers/twitter-mcp/server.py
- [x] T020 [US3] Implement tweet deduplication logic using semantic similarity search (threshold 0.85) in mcp-servers/twitter-mcp/server.py
- [x] T021 [US3] Add achievement content generation that queries Memory MCP for recent activities in mcp-servers/twitter-mcp/server.py
- [x] T022 [US3] Implement 30-day tweet history retention and cleanup in mcp-servers/twitter-mcp/server.py
- [x] T023 [US3] Update workspace/skills/twitter-heartbeat/SKILL.md with memory-driven content generation steps

**Checkpoint**: Tweets draw from real experiences stored in Memory MCP with no duplicates

---

## Phase 6: User Story 4 - Visual HUD Twitter Panel (Priority: P3)

**Goal**: Visual HUD displays recent outbound tweets in real-time

**Independent Test**: Open Visual HUD, post a tweet, verify it appears in Twitter panel within 5 seconds

### Implementation for User Story 4

- [x] T024 [US4] Create ui/netclaw-visual/src/panels/TwitterPanel.js with tweet list display
- [x] T025 [US4] Add WebSocket event handler for new tweet notifications in TwitterPanel.js
- [x] T026 [US4] Add rate limit status indicator (X/50 remaining) to TwitterPanel.js
- [x] T027 [US4] Create TwitterPanel.css with HUD-matching cyberpunk styling
- [x] T028 [US4] Update ui/netclaw-visual/README.md with Twitter panel documentation

**Checkpoint**: Visual HUD shows live tweet feed with real-time updates

---

## Phase 7: Polish & Artifact Coherence

**Purpose**: Full-Stack Artifact Coherence (Constitution Principle XI)

### Documentation Updates

- [x] T029 [P] Add Twitter integration section to README.md with capabilities, setup, and example usage
- [x] T030 [P] Add Twitter presence skills to SOUL.md (twitter-heartbeat, twitter-share under new "Twitter Integration Skills" section)
- [x] T031 [P] Update TOOLS.md with twitter-mcp server reference
- [x] T032 [P] Create mcp-servers/twitter-mcp/README.md with tool inventory, env vars, and setup instructions

### Configuration Updates

- [x] T033 Add Twitter environment variables to .env.example (TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, TWITTER_HEARTBEAT_ENABLED, TWITTER_HEARTBEAT_INTERVAL)
- [x] T034 Add twitter-mcp server configuration to config/openclaw.json

### Installation

- [x] T035 Create scripts/twitter_install.sh with pip install and configuration prompts
- [x] T036 Update scripts/install.sh with optional Twitter setup prompt

### Final Validation

- [x] T037 Run quickstart.md validation - verify all setup steps work
- [x] T038 Verify skill count in README.md (should be 181 after adding 2 new skills)
- [x] T039 Git add all changed files and prepare for PR

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Setup - BLOCKS all user stories
- **Phase 3 (US1 Heartbeat)**: Depends on Foundational (Phase 2) - P1 MVP
- **Phase 4 (US2 Manual)**: Depends on Foundational (Phase 2) - P1, can parallel with US1
- **Phase 5 (US3 Memory)**: Depends on US1 completion (needs heartbeat content generation)
- **Phase 6 (US4 HUD)**: Depends on Foundational (Phase 2) - Can parallel with US1/US2
- **Phase 7 (Polish)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core heartbeat functionality
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Independent of US1, both are P1
- **User Story 3 (P2)**: Depends on US1 (extends heartbeat content generation with memory)
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independent UI component

### Parallel Opportunities

Tasks can be parallelized when working on different files:

**Parallel Group A** (Phase 2 - different modules):
- T004 guardrails.py and T005 threading.py can run in parallel

**Parallel Group B** (US1 + US2 + US4 - different components):
- US1 tasks (T009-T013) - MCP server heartbeat
- US2 tasks (T014-T018) - MCP server manual + skill
- US4 tasks (T024-T028) - HUD component (separate codebase)

**Parallel Group C** (Phase 7 - different files):
- T029, T030, T031, T032 can all run in parallel (different documentation files)

---

## Parallel Example: Initial Phase

```bash
# After Phase 2 completes, these can run in parallel (different components):
Task T009-T013: US1 Heartbeat (mcp-servers/twitter-mcp/ + workspace/skills/twitter-heartbeat/)
Task T024-T028: US4 HUD Panel (ui/netclaw-visual/)
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US1 Heartbeat
4. Complete Phase 4: US2 Manual Tweet
5. **STOP and VALIDATE**: Test posting via both heartbeat and manual methods
6. This delivers core Twitter capability

### Incremental Delivery

1. Complete Setup + Foundational → MCP server skeleton ready
2. Complete US1 + US2 → Core posting capability (MVP!)
3. Complete US3 → Memory-driven content intelligence
4. Complete US4 → Visual monitoring in HUD
5. Complete Polish → All artifacts updated, ready for merge

### Parallel Strategy

With parallel execution:
1. Start Setup (Phase 1)
2. Complete Foundational (Phase 2) - blocking
3. Start US1, US2, US4 simultaneously (different codebases)
4. US3 after US1 completes (extends heartbeat)
5. Polish when all complete

---

## Notes

- All tasks are specific to file paths for clear implementation
- No tests requested in spec - test tasks omitted
- Principle XIV (Human-in-the-Loop) enforced via approval flow in twitter-share skill
- Heartbeat disabled by default (TWITTER_HEARTBEAT_ENABLED=false)
- Verify each checkpoint independently before proceeding
- Commit after each logical group of changes
