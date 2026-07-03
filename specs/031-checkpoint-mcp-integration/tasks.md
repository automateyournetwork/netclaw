# Tasks: Check Point MCP Integration

**Input**: Design documents from `/specs/031-checkpoint-mcp-integration/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete), contracts/mcp-tools.md (complete)

**Tests**: No explicit test requirements in spec. Manual validation via quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is an integration-only feature. Deliverables are:
- `mcp-servers/checkpoint-mcp-servers/` - Cloned Check Point MCP monorepo
- `config/openclaw.json` - MCP server registrations (pointing to local builds)
- `workspace/skills/checkpoint/SKILL.md` - Skill definition
- `scripts/install.sh` - Updated installer
- `scripts/checkpoint-enable.sh` - Existing user enablement
- `.env.example` - Environment variable documentation
- `docs/CHECKPOINT.md` - Detailed guide
- `README.md`, `SOUL.md` - Documentation updates

**⚠️ IMPORTANT**: NetClaw pattern is to git clone MCP repos into `mcp-servers/` folder (46+ existing cloned repos). We must clone https://github.com/CheckPointSW/mcp-servers, NOT use npx.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Clone Check Point MCP monorepo and initialize project structure

- [x] T001 Git clone https://github.com/CheckPointSW/mcp-servers into mcp-servers/checkpoint-mcp-servers/
- [x] T002 Run npm install in mcp-servers/checkpoint-mcp-servers/ to build all 15 MCPs
- [x] T003 Create Check Point environment variable schema in .env.example with all CHKP_* variables
- [x] T004 [P] Create workspace/skills/checkpoint/ directory structure
- [x] T005 [P] Create docs/ entry point for CHECKPOINT.md

**Checkpoint**: Check Point MCP repo cloned, built, and directory structure ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: MCP server configurations that MUST be complete before ANY user story can be tested

**⚠️ CRITICAL**: No user story work can begin until all 15 MCPs are configured in openclaw.json

### MCP Server Configurations (all [P] - different JSON entries, point to local builds)

- [x] T006 [P] Add chkp-management MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/quantum-management-mcp)
- [x] T007 [P] Add chkp-management-logs MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/management-logs-mcp)
- [x] T008 [P] Add chkp-threat-prevention MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/threat-prevention-mcp)
- [x] T009 [P] Add chkp-https-inspection MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/https-inspection-mcp)
- [x] T010 [P] Add chkp-harmony-sase MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/harmony-sase-mcp)
- [x] T011 [P] Add chkp-reputation-service MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/reputation-service-mcp)
- [x] T012 [P] Add chkp-quantum-gw-cli MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/quantum-gw-cli-mcp)
- [x] T013 [P] Add chkp-gw-connection-analysis MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/quantum-gw-connection-analysis-mcp)
- [x] T014 [P] Add chkp-threat-emulation MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/threat-emulation-mcp)
- [x] T015 [P] Add chkp-quantum-gaia MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/quantum-gaia-mcp)
- [x] T016 [P] Add chkp-documentation MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/documentation-mcp)
- [x] T017 [P] Add chkp-spark-management MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/spark-management-mcp)
- [x] T018 [P] Add chkp-cpinfo-analysis MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/cpinfo-analysis-mcp)
- [x] T019 [P] Add chkp-argos-erm MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/argos-erm-mcp)
- [x] T020 [P] Add chkp-policy-insights MCP config to config/openclaw.json (mcp-servers/checkpoint-mcp-servers/packages/policy-insights-mcp)

**Checkpoint**: All 15 MCP servers configured with local paths - skill and story implementation can now begin

---

## Phase 3: User Story 8 - Installation & Onboarding (Priority: P1) 🎯 MVP

**Goal**: Enable frictionless onboarding for both new and existing NetClaw users

**Independent Test**: Run install.sh and select Check Point integration OR run checkpoint-enable.sh for existing install

### Implementation for User Story 8

- [x] T021 [US8] Add Check Point integration step to scripts/install.sh (step 48-50)
- [x] T022 [P] [US8] Create scripts/checkpoint-enable.sh for existing installations
- [x] T023 [US8] Add credential prompts and .env population logic to install.sh
- [x] T024 [US8] Add MCP config injection and git clone logic to install.sh and checkpoint-enable.sh
- [x] T025 [US8] Add skip-credentials option for deferred configuration

**Checkpoint**: New users can enable Check Point during install, existing users can run checkpoint-enable.sh

---

## Phase 4: User Story 1 - Security Policy Audit (Priority: P1)

**Goal**: Security engineers can audit firewall policies using natural language queries

**Independent Test**: Query "show me overly permissive rules" with configured Management Server

### Implementation for User Story 1

- [x] T026 [US1] Create /checkpoint skill definition in workspace/skills/checkpoint/SKILL.md
- [x] T027 [US1] Define query routing patterns for policy keywords in SKILL.md
- [x] T028 [US1] Add policy audit examples and workflows to SKILL.md
- [x] T029 [US1] Document management + policy-insights MCP composition in SKILL.md

**Checkpoint**: Policy audit queries route to correct MCPs and return structured results

---

## Phase 5: User Story 2 - Threat Intelligence & Reputation Lookup (Priority: P1)

**Goal**: SOC analysts can quickly check reputation of suspicious IPs, URLs, or files

**Independent Test**: Query "check reputation of IP 8.8.8.8" with configured Reputation API key

### Implementation for User Story 2

- [x] T030 [US2] Add reputation query routing patterns to workspace/skills/checkpoint/SKILL.md
- [x] T031 [US2] Add IP/URL/file reputation examples to SKILL.md
- [x] T032 [US2] Document reputation-service MCP usage in SKILL.md

**Checkpoint**: Reputation queries route to reputation-service MCP correctly

---

## Phase 6: User Story 3 - Gateway Diagnostics (Priority: P2)

**Goal**: Network engineers can diagnose gateway connectivity, performance, and hardware issues

**Independent Test**: Query "show gateway health status" with configured gateway credentials

### Implementation for User Story 3

- [x] T033 [US3] Add gateway diagnostics routing patterns to workspace/skills/checkpoint/SKILL.md
- [x] T034 [US3] Add gateway health and performance examples to SKILL.md
- [x] T035 [US3] Document quantum-gw-cli MCP usage in SKILL.md
- [x] T036 [US3] Document default gateway selection behavior (first configured) in SKILL.md

**Checkpoint**: Gateway diagnostic queries route to gw-cli MCP correctly

---

## Phase 7: User Story 4 - Threat Prevention Analysis (Priority: P2)

**Goal**: Security architects can review threat prevention coverage and IPS signatures

**Independent Test**: Query "show threat prevention profiles" with configured Management Server

### Implementation for User Story 4

- [x] T037 [US4] Add threat prevention routing patterns to workspace/skills/checkpoint/SKILL.md
- [x] T038 [US4] Add IPS and IOC feed examples to SKILL.md
- [x] T039 [US4] Document threat-prevention MCP usage in SKILL.md

**Checkpoint**: Threat prevention queries route correctly

---

## Phase 8: User Story 5 - SASE Management (Priority: P2)

**Goal**: Administrators can query and manage SASE regions, networks, and applications

**Independent Test**: Query "show SASE regions" with configured SASE credentials

### Implementation for User Story 5

- [x] T040 [US5] Add SASE routing patterns to workspace/skills/checkpoint/SKILL.md
- [x] T041 [US5] Add SASE region and application examples to SKILL.md
- [x] T042 [US5] Document harmony-sase MCP usage in SKILL.md

**Checkpoint**: SASE queries route to harmony-sase MCP correctly

---

## Phase 9: User Story 6 - File/Malware Analysis (Priority: P2)

**Goal**: Security analysts can analyze suspicious files for malware

**Independent Test**: Query "analyze file with hash abc123" with configured TE API key

### Implementation for User Story 6

- [x] T043 [US6] Add malware analysis routing patterns to workspace/skills/checkpoint/SKILL.md
- [x] T044 [US6] Add file submission and verdict examples to SKILL.md
- [x] T045 [US6] Document threat-emulation MCP usage in SKILL.md

**Checkpoint**: Malware analysis queries route to threat-emulation MCP correctly

---

## Phase 10: User Story 7 - Cross-Platform Composition (Priority: P3)

**Goal**: Engineers can correlate Check Point policies with other NetClaw data sources

**Independent Test**: Query "cross-reference firewall rules with CML lab topology" with both configured

### Implementation for User Story 7

- [x] T046 [US7] Add cross-platform composition patterns to workspace/skills/checkpoint/SKILL.md
- [x] T047 [US7] Document integration with CML, SuzieQ, Batfish skills in SKILL.md
- [x] T048 [US7] Add multi-source query examples to SKILL.md

**Checkpoint**: Cross-platform queries invoke multiple skill contexts correctly

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates per Constitution XI (Full-Stack Artifact Coherence)

### Documentation Updates (all [P] - different files)

- [x] T049 [P] Add Check Point section to README.md with architecture diagram placeholder
- [x] T050 [P] Add Check Point expertise and security patterns to SOUL.md
- [x] T051 [P] Create comprehensive docs/CHECKPOINT.md guide
- [x] T052 [P] Update tool count and capability summary in README.md
- [x] T053 [P] Update mcp-servers/README.md with Check Point MCP servers entry

### Remaining Documentation

- [x] T054 Add HTTPS inspection routing patterns to SKILL.md
- [x] T055 Add GAIA OS routing patterns to SKILL.md
- [x] T056 Add documentation MCP routing patterns to SKILL.md
- [x] T057 Add Spark management routing patterns to SKILL.md
- [x] T058 Add CPInfo analysis routing patterns to SKILL.md
- [x] T059 Add Argos ERM routing patterns to SKILL.md
- [x] T060 Add connection analysis (debug) routing patterns to SKILL.md
- [x] T061 Add configurable logging level (CHKP_LOG_LEVEL) documentation to all relevant files

### Final Validation

- [x] T062 Run quickstart.md validation with test credentials
- [x] T063 Verify Constitution XI artifact coherence checklist complete
- [ ] T064 Draft WordPress blog post for milestone (per Constitution XVII)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 8 (Phase 3)**: Depends on Phase 2 - MVP install experience
- **User Stories 1-7 (Phases 4-10)**: All depend on Phase 2, can proceed in parallel
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 8 (Installation)**: First - enables all other testing
- **User Story 1 (Policy Audit)**: Independent after Phase 2
- **User Story 2 (Reputation)**: Independent after Phase 2
- **User Story 3 (Gateway Diagnostics)**: Independent after Phase 2
- **User Story 4 (Threat Prevention)**: Independent after Phase 2
- **User Story 5 (SASE)**: Independent after Phase 2
- **User Story 6 (Malware Analysis)**: Independent after Phase 2
- **User Story 7 (Cross-Platform)**: Depends on other skills being available

### Within Each User Story

- Routing patterns before examples
- Examples before documentation
- Core functionality before edge cases

### Parallel Opportunities

- All 15 MCP configurations (T006-T020) can run in parallel (after git clone/build completes)
- All documentation updates (T049-T053) can run in parallel
- Install.sh and checkpoint-enable.sh (T021, T022) can run in parallel
- User Stories 1-6 can run in parallel after Phase 2

---

## Parallel Example: Phase 2 (MCP Configurations)

```bash
# Launch all 15 MCP configurations in parallel:
Task: "Add chkp-management MCP config to config/openclaw.json"
Task: "Add chkp-management-logs MCP config to config/openclaw.json"
Task: "Add chkp-threat-prevention MCP config to config/openclaw.json"
# ... all 15 can run simultaneously
```

---

## Parallel Example: Documentation Updates

```bash
# Launch all documentation updates in parallel:
Task: "Add Check Point section to README.md"
Task: "Add Check Point expertise to SOUL.md"
Task: "Create docs/CHECKPOINT.md guide"
Task: "Update tool count in README.md"
```

---

## Implementation Strategy

### MVP First (User Story 8 + 1 + 2)

1. Complete Phase 1: Setup - Clone & Build (T001-T005)
2. Complete Phase 2: All 15 MCP Configurations (T006-T020)
3. Complete Phase 3: Installation (T021-T025)
4. Complete Phase 4: Policy Audit skill (T026-T029)
5. Complete Phase 5: Reputation Lookup (T030-T032)
6. **STOP and VALIDATE**: Test with real Check Point credentials
7. Deploy/demo if ready - core security operations working

### Incremental Delivery

1. Setup + MCP Configs → Foundation ready
2. Add Installation (US8) → Test install flow → Users can enable Check Point
3. Add Policy Audit (US1) → Test queries → Core value delivered
4. Add Reputation (US2) → Test lookups → SOC value delivered
5. Add Gateway Diagnostics (US3) → Test → Network ops value
6. Add remaining stories → Full platform coverage
7. Polish → Production ready

### Parallel Team Strategy

With multiple developers after Phase 2:
- Developer A: User Story 8 (Installation) + User Story 1 (Policy)
- Developer B: User Story 2 (Reputation) + User Story 3 (Gateway)
- Developer C: User Story 4 (Threat Prevention) + User Story 5 (SASE)
- Developer D: User Story 6 (Malware) + User Story 7 (Cross-Platform)
- Developer E: Documentation (T047-T058)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All MCP configs use same JSON structure, only env vars differ
- **Git clone into mcp-servers/checkpoint-mcp-servers/** - follows NetClaw pattern (46+ existing cloned repos)
- MCP configs point to local builds: `mcp-servers/checkpoint-mcp-servers/packages/<name>`
- No new code - this is configuration + documentation only
- Verify with quickstart.md after each phase
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
