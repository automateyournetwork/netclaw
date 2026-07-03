# Tasks: Twilio Voice MCP Integration

**Input**: Design documents from `/specs/042-twilio-voice-mcp/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested - implementation tasks only.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- MCP server: `mcp-servers/twilio-voice-mcp/`
- Skills: `workspace/skills/`
- Config: `config/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and configuration

- [ ] T001 Create MCP server directory structure at mcp-servers/twilio-voice-mcp/
- [ ] T002 [P] Create requirements.txt with FastMCP, twilio, httpx dependencies in mcp-servers/twilio-voice-mcp/requirements.txt
- [ ] T003 [P] Add Twilio credentials to ~/.openclaw/.env (TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, TWILIO_API_SECRET)
- [ ] T004 [P] Create config/twilio-voice.json with whitelist, quiet_hours, emergency_categories, rate_limits
- [ ] T005 Add @twilio-alpha/mcp to ~/.openclaw/openclaw.json MCP servers configuration
- [ ] T006 [P] Create mcp-servers/twilio-voice-mcp/README.md documenting the server

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Implement guardrails.py with sanitize_for_voice() function (IP, MAC, credential filtering) in mcp-servers/twilio-voice-mcp/guardrails.py
- [ ] T008 Implement rate limiting functions (check_rate_limit, record_call) using Memory MCP in mcp-servers/twilio-voice-mcp/guardrails.py
- [ ] T009 Implement quiet hours checking function (is_quiet_hours, can_call_now) in mcp-servers/twilio-voice-mcp/guardrails.py
- [ ] T010 Implement whitelist validation functions (is_whitelisted, validate_phone_number) in mcp-servers/twilio-voice-mcp/guardrails.py
- [ ] T011 Create base server.py with FastMCP setup and tool registration in mcp-servers/twilio-voice-mcp/server.py
- [ ] T012 Implement call_logging functions to store CallRecord in Memory MCP in mcp-servers/twilio-voice-mcp/server.py
- [ ] T013 Add twilio-voice-mcp to ~/.openclaw/openclaw.json MCP servers (webhook server)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Emergency Alert Calls (Priority: P1) 🎯 MVP

**Goal**: NetClaw auto-calls John when P1 incidents or critical device failures occur

**Independent Test**: Simulate a P1 PagerDuty incident and verify call is placed within 60 seconds

### Implementation for User Story 1

- [ ] T014 [US1] Implement twilio_voice_call tool in mcp-servers/twilio-voice-mcp/server.py (uses @twilio-alpha/mcp)
- [ ] T015 [US1] Implement emergency category detection function in mcp-servers/twilio-voice-mcp/server.py
- [ ] T016 [US1] Implement auto-approval logic for emergency calls (bypass approval_status) in mcp-servers/twilio-voice-mcp/server.py
- [ ] T017 [US1] Implement call retry logic with exponential backoff in mcp-servers/twilio-voice-mcp/server.py
- [ ] T018 [US1] Implement SMS/Slack fallback on call failure in mcp-servers/twilio-voice-mcp/server.py
- [ ] T019 [US1] Create workspace/skills/twilio-emergency-call/SKILL.md documenting the emergency call workflow
- [ ] T020 [US1] Add emergency call skill to SOUL.md under Twilio/X Integration Skills section

**Checkpoint**: Emergency calls work - P1 incidents trigger auto-calls to John

---

## Phase 4: User Story 2 - On-Demand Status Calls (Priority: P2)

**Goal**: John can request "call me with network status" and receive a voice briefing

**Independent Test**: Send "call me with network status" via Slack and verify call is placed with status summary

### Implementation for User Story 2

- [ ] T021 [US2] Implement twilio_voice_request tool for on-demand calls with approval flow in mcp-servers/twilio-voice-mcp/server.py
- [ ] T022 [US2] Implement content generation function to build call message from network status in mcp-servers/twilio-voice-mcp/server.py
- [ ] T023 [US2] Implement call queue for handling concurrent requests in mcp-servers/twilio-voice-mcp/server.py
- [ ] T024 [US2] Create workspace/skills/twilio-outbound-call/SKILL.md documenting on-demand call workflow
- [ ] T025 [US2] Add outbound call skill to SOUL.md

**Checkpoint**: On-demand calls work - John can request status calls via Slack/CLI

---

## Phase 5: User Story 3 - Situation Update Calls (Priority: P2)

**Goal**: John can request periodic update calls during ongoing incidents

**Independent Test**: Request "call me every 30 minutes with updates" and verify scheduled calls occur

### Implementation for User Story 3

- [ ] T026 [US3] Implement scheduled call registration (store in Memory MCP) in mcp-servers/twilio-voice-mcp/server.py
- [ ] T027 [US3] Implement status change detection to skip calls when no updates in mcp-servers/twilio-voice-mcp/server.py
- [ ] T028 [US3] Implement immediate call trigger for critical changes (resolved, escalated) in mcp-servers/twilio-voice-mcp/server.py
- [ ] T029 [US3] Implement call schedule cancellation when incident resolves in mcp-servers/twilio-voice-mcp/server.py
- [ ] T030 [US3] Update workspace/skills/twilio-outbound-call/SKILL.md with periodic update workflow

**Checkpoint**: Situation updates work - John receives scheduled calls during incidents

---

## Phase 6: User Story 4 - Daily Check-in Calls (Priority: P3)

**Goal**: Optional daily phone briefings at scheduled time

**Independent Test**: Enable daily briefing at 8 AM, verify call occurs with overnight summary

### Implementation for User Story 4

- [ ] T031 [US4] Implement daily briefing configuration (time, enabled/disabled) in config/twilio-voice.json
- [ ] T032 [US4] Implement heartbeat integration for daily call trigger in mcp-servers/twilio-voice-mcp/server.py
- [ ] T033 [US4] Implement overnight event summary generation in mcp-servers/twilio-voice-mcp/server.py
- [ ] T034 [US4] Implement "all clear" short message for quiet nights in mcp-servers/twilio-voice-mcp/server.py
- [ ] T035 [US4] Create workspace/skills/twilio-daily-briefing/SKILL.md documenting daily briefing workflow
- [ ] T036 [US4] Add daily briefing skill to SOUL.md

**Checkpoint**: Daily briefings work - John receives morning status calls if enabled

---

## Phase 7: User Story 5 - Inbound Voice Conversations (Priority: P2)

**Goal**: John can call a Twilio number and have a voice conversation with NetClaw

**Independent Test**: Call the NetClaw number, ask "What's my network status?", verify voice response

### Implementation for User Story 5

- [ ] T037 [US5] Implement webhook endpoint POST /webhooks/twilio/voice in mcp-servers/twilio-voice-mcp/server.py
- [ ] T038 [US5] Implement caller ID authentication against whitelist in mcp-servers/twilio-voice-mcp/server.py
- [ ] T039 [US5] Implement TwiML response generation for greeting and rejection in mcp-servers/twilio-voice-mcp/server.py
- [ ] T040 [US5] Create voice_handler.py for Media Streams WebSocket handling in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T041 [US5] Implement STT integration using Whisper API in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T042 [US5] Implement TTS response via Twilio <Say> TwiML in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T043 [US5] Implement conversation context tracking in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T044 [US5] Implement VoiceConversation logging to Memory MCP in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T045 [US5] Implement webhook status callback POST /webhooks/twilio/voice/status in mcp-servers/twilio-voice-mcp/server.py
- [ ] T046 [US5] Create workspace/skills/twilio-inbound-voice/SKILL.md documenting inbound conversation workflow
- [ ] T047 [US5] Add inbound voice skill to SOUL.md

**Checkpoint**: Inbound calls work - John can call NetClaw and have a voice conversation

---

## Phase 8: User Story 6 - Voice-Initiated Network Commands (Priority: P3)

**Goal**: John can issue network commands via voice during a call

**Independent Test**: Call NetClaw, say "Show me BGP neighbors on router-1", verify spoken response

### Implementation for User Story 6

- [ ] T048 [US6] Implement voice command parsing and intent detection in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T049 [US6] Implement verbal confirmation flow for impactful actions in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T050 [US6] Implement network tool invocation from voice commands in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T051 [US6] Implement response sanitization for sensitive command output in mcp-servers/twilio-voice-mcp/voice_handler.py
- [ ] T052 [US6] Update workspace/skills/twilio-inbound-voice/SKILL.md with voice command workflow

**Checkpoint**: Voice commands work - John can query and control the network via voice

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, artifact coherence, and final validation

- [ ] T053 [P] Update README.md with Twilio Voice capability description and tool count
- [ ] T054 [P] Update .env.example with all TWILIO_* environment variables
- [ ] T055 [P] Update TOOLS.md with twilio-voice-mcp infrastructure reference
- [ ] T056 Add Twilio Voice Skills section to SOUL.md (consolidate all skill references)
- [ ] T057 [P] Create SOUL-SKILLS.md entry for Twilio voice procedures
- [ ] T058 Run quickstart.md validation - test all documented examples
- [ ] T059 Verify all Constitution Artifact Coherence checklist items complete
- [ ] T060 Draft WordPress blog post for feature milestone (per Principle XVII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (Emergency) → US2 (On-Demand) → US3 (Situation Updates) → US4 (Daily) can proceed sequentially
  - US5 (Inbound) can start after Foundational (independent of outbound stories)
  - US6 (Voice Commands) depends on US5 completion
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
       │
       ├── US1: Emergency Alert Calls (P1) - MVP, no dependencies
       │    │
       │    ├── US2: On-Demand Status Calls (P2) - builds on US1 call infrastructure
       │    │    │
       │    │    └── US3: Situation Update Calls (P2) - extends US2 with scheduling
       │    │         │
       │    │         └── US4: Daily Check-in Calls (P3) - extends US3 with heartbeat
       │    │
       │    └── US5: Inbound Voice Conversations (P2) - independent inbound path
       │              │
       │              └── US6: Voice-Initiated Commands (P3) - extends US5
       │
       └── Polish (Phase 9)
```

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks T007-T010 (guardrails functions) can run in parallel
- US1-US4 (outbound) and US5-US6 (inbound) can be developed by different team members in parallel
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all guardrail functions in parallel:
Task: "Implement guardrails.py with sanitize_for_voice() function"
Task: "Implement rate limiting functions using Memory MCP"
Task: "Implement quiet hours checking function"
Task: "Implement whitelist validation functions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 - Emergency Alert Calls
4. **STOP and VALIDATE**: Test emergency call with simulated P1 incident
5. Deploy if ready - emergency alerts are the core value

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test emergency calls → Deploy (MVP!)
3. Add User Story 2 → Test on-demand calls → Deploy
4. Add User Story 3 → Test scheduled updates → Deploy
5. Add User Story 4 → Test daily briefings → Deploy
6. Add User Story 5 → Test inbound calls → Deploy
7. Add User Story 6 → Test voice commands → Deploy
8. Complete Polish → Full feature ready

### Parallel Team Strategy

With two developers:
- Developer A: US1 → US2 → US3 → US4 (outbound calling path)
- Developer B: US5 → US6 (inbound calling path)

Both paths can proceed independently after Foundational phase.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MVP = User Story 1 (Emergency Alert Calls) - provides immediate value
- Twilio credentials already provided - use them in T003
