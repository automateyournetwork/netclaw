# Tasks: DefenseClaw Security Integration

**Input**: Design documents from `/specs/027-netshell-security/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested - skipped per template guidelines.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Scope

This feature:
1. Removes original NetShell implementation
2. Integrates Cisco DefenseClaw as the enterprise security layer
3. Creates comprehensive documentation and onboarding guides
4. Updates all relevant files (SOUL, README, skills, MCPs)

---

## Phase 1: Setup (Cleanup Old Artifacts)

**Purpose**: Remove original NetShell artifacts that are replaced by DefenseClaw

- [x] T001 Archive netshell/ directory to netshell.bak/ (preserve for reference)
- [x] T002 [P] Remove NetShell Security Layer section from CLAUDE.md
- [x] T003 [P] Remove old NetShell section from scripts/install.sh (lines ~2847-2939)

---

## Phase 2: Foundational (DefenseClaw Infrastructure)

**Purpose**: Create core scripts and configuration for DefenseClaw integration

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create scripts/defenseclaw-enable.sh for post-install enablement
- [x] T005 [P] Create scripts/defenseclaw-disable.sh for disabling DefenseClaw
- [x] T006 [P] Update config/openclaw.json with security section schema

**Checkpoint**: Foundation ready - DefenseClaw enable/disable scripts exist

---

## Phase 3: User Story 1 - Production Security with DefenseClaw (Priority: P1) MVP

**Goal**: Enable DefenseClaw as the comprehensive security solution during installation

**Independent Test**: Run install.sh, enable DefenseClaw, verify CLI/gateway/extension installed

### Implementation for User Story 1

- [x] T007 [US1] Add DefenseClaw section to scripts/install.sh with opt-in prompt
- [x] T008 [US1] Add prerequisite checks (Docker, Python 3.10+, Go 1.25+, Node.js 20+)
- [x] T009 [US1] Add DefenseClaw installer: curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash
- [x] T010 [US1] Add defenseclaw init --enable-guardrail command
- [x] T011 [US1] Update openclaw.json with security.mode on enable/decline
- [x] T012 [US1] Add success/skip messages with next steps

**Checkpoint**: DefenseClaw can be enabled during fresh installation

---

## Phase 4: User Story 2 - Existing User Onboarding (Priority: P1)

**Goal**: Provide clear upgrade path for existing NetClaw users to enable DefenseClaw

**Independent Test**: Existing user runs defenseclaw-enable.sh, DefenseClaw activates

### Implementation for User Story 2

- [x] T013 [US2] Enhance scripts/defenseclaw-enable.sh with full onboarding flow
- [x] T014 [US2] Add prerequisite validation with helpful error messages
- [x] T015 [US2] Add backup of current config before enabling
- [x] T016 [P] [US2] Create docs/UPGRADE-TO-DEFENSECLAW.md migration guide
- [x] T017 [US2] Add "defenseclaw-enable.sh" mention to main README.md

**Checkpoint**: Existing users have clear upgrade path

---

## Phase 5: User Story 3 - Hobby Mode Preservation (Priority: P2)

**Goal**: Preserve easy onboarding for users who decline security features

**Independent Test**: Decline DefenseClaw during install, NetClaw runs normally

### Implementation for User Story 3

- [x] T018 [US3] Add hobby mode path in install.sh when DefenseClaw declined
- [x] T019 [US3] Add clear messaging about hobby mode limitations
- [x] T020 [P] [US3] Add upgrade reminder: "Enable later: ./scripts/defenseclaw-enable.sh"

**Checkpoint**: Users can decline security and still use NetClaw

---

## Phase 6: User Story 4 - Comprehensive Documentation (Priority: P1)

**Goal**: Create comprehensive DefenseClaw documentation suite

**Independent Test**: New user can follow docs to fully configure DefenseClaw

### DefenseClaw Enterprise Guide (New File)

- [x] T021 [US4] Create docs/DEFENSECLAW.md - comprehensive enterprise security guide
- [x] T022 [P] [US4] Add "What is DefenseClaw?" section with architecture diagram
- [x] T023 [P] [US4] Add "Installation" section (fresh install + upgrade paths)
- [x] T024 [US4] Add "Component Scanning" section (skills, MCPs, plugins)
- [x] T025 [US4] Add "Runtime Guardrails" section (observe vs action modes)
- [x] T026 [US4] Add "Tool Management" section (block/allow commands)
- [x] T027 [US4] Add "Audit & Compliance" section (SQLite, SIEM, exports)
- [x] T028 [US4] Add "SIEM Integration" section (Splunk HEC, OTLP, webhooks)
- [x] T029 [US4] Add "Troubleshooting" section
- [x] T030 [US4] Add "Quick Reference" command cheat sheet

### Main README Updates

- [x] T031 [US4] Update README.md feature list with DefenseClaw (replace NetShell mention)
- [x] T032 [P] [US4] Add "Enterprise Security" section to README.md linking to docs/DEFENSECLAW.md
- [x] T033 [US4] Update architecture diagram in README.md to show DefenseClaw layer

**Checkpoint**: Complete documentation suite exists

---

## Phase 7: SOUL and Constitution Updates (Priority: P1)

**Goal**: Update SOUL.md and create SOUL-DEFENSE.md for security principles

### SOUL Updates

- [x] T034 [US5] Update SOUL.md P18-P25 to reference DefenseClaw instead of NetShell
- [x] T035 [P] [US5] Create docs/SOUL-DEFENSE.md with detailed security principles
- [x] T036 [US5] Add security posture guidance to SOUL-DEFENSE.md (when to use observe vs action)
- [x] T037 [US5] Add compliance mapping in SOUL-DEFENSE.md (SOC2, PCI-DSS, HIPAA)
- [x] T038 [P] [US5] Link SOUL-DEFENSE.md from main SOUL.md

**Checkpoint**: Security principles documented and linked

---

## Phase 8: Skill and MCP Awareness (Priority: P2)

**Goal**: Update skills and MCPs to be DefenseClaw-aware

### Skill Updates

- [x] T039 [US6] Update workspace/skills/SKILL-SCHEMA.md to remove netshell: section (DefenseClaw handles this)
- [x] T040 [P] [US6] Add "Security" section to SKILL-SCHEMA.md explaining DefenseClaw scanning
- [x] T041 [US6] Create workspace/skills/defenseclaw-ops/SKILL.md for DefenseClaw management skill
- [x] T042 [US6] Update 5 example skills with security notes (pyats, meraki, catc, suzieq, aws)

### MCP Updates

- [x] T043 [US6] Update mcp-servers/README.md with DefenseClaw scanning note
- [x] T044 [P] [US6] Add security section to MCP template explaining CodeGuard analysis

**Checkpoint**: Skills and MCPs reference DefenseClaw

---

## Phase 9: CLAUDE.md Agent Context (Priority: P2)

**Goal**: Update agent context for DefenseClaw awareness

- [x] T045 [US7] Add DefenseClaw section to CLAUDE.md (replace NetShell section)
- [x] T046 [US7] Document key DefenseClaw commands in CLAUDE.md
- [x] T047 [P] [US7] Add security mode detection guidance

**Checkpoint**: Agent is DefenseClaw-aware

---

## Phase 10: Polish & Validation

**Purpose**: Final validation and blog post

- [x] T048 Validate install.sh flow end-to-end (fresh install with DefenseClaw)
- [x] T049 [P] Validate defenseclaw-enable.sh flow (existing user upgrade)
- [x] T050 [P] Validate defenseclaw-disable.sh flow (disable and re-enable)
- [x] T051 Run quickstart.md validation scenarios 1-8
- [x] T052 Create WordPress blog post announcing DefenseClaw integration
- [x] T053 Final review: all links work, no broken references

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Cleanup) ──► Phase 2 (Foundation) ──► Phase 3 (US1 Install)
                                            │
                                            ├──► Phase 4 (US2 Onboarding)
                                            │
                                            ├──► Phase 5 (US3 Hobby)
                                            │
                                            └──► Phase 6 (US4 Docs)
                                                      │
                                                      ├──► Phase 7 (SOUL)
                                                      │
                                                      ├──► Phase 8 (Skills/MCPs)
                                                      │
                                                      └──► Phase 9 (CLAUDE.md)
                                                                │
                                                                └──► Phase 10 (Polish)
```

### Parallel Opportunities

- Phase 1: T002-T003 in parallel
- Phase 2: T005-T006 in parallel with T004
- Phase 4: T016 in parallel with T013-T015
- Phase 5: T020 in parallel with T018-T019
- Phase 6: T022-T023, T032 in parallel
- Phase 7: T035, T038 in parallel
- Phase 8: T040, T044 in parallel
- Phase 9: T047 in parallel with T045-T046
- Phase 10: T049-T050 in parallel

---

## Key Files Created/Modified

### New Files
| File | Description |
|------|-------------|
| `scripts/defenseclaw-enable.sh` | Enable DefenseClaw post-install |
| `scripts/defenseclaw-disable.sh` | Disable DefenseClaw |
| `docs/DEFENSECLAW.md` | Comprehensive enterprise security guide |
| `docs/SOUL-DEFENSE.md` | Security principles and compliance |
| `docs/UPGRADE-TO-DEFENSECLAW.md` | Migration guide for existing users |
| `workspace/skills/defenseclaw-ops/SKILL.md` | DefenseClaw management skill |

### Modified Files
| File | Changes |
|------|---------|
| `scripts/install.sh` | Add DefenseClaw section, remove NetShell |
| `README.md` | Add Enterprise Security section |
| `SOUL.md` | Update P18-P25 for DefenseClaw |
| `CLAUDE.md` | Replace NetShell with DefenseClaw context |
| `config/openclaw.json` | Add security.mode field |
| `workspace/skills/SKILL-SCHEMA.md` | Update for DefenseClaw |
| `mcp-servers/README.md` | Add DefenseClaw note |

### Archived Files
| File | Action |
|------|--------|
| `netshell/` | Move to `netshell.bak/` |

---

## Task Count Summary

| Phase | Tasks | Parallelizable |
|-------|-------|----------------|
| 1. Setup | 3 | 2 |
| 2. Foundation | 3 | 2 |
| 3. US1 Install | 6 | 0 |
| 4. US2 Onboarding | 5 | 1 |
| 5. US3 Hobby | 3 | 1 |
| 6. US4 Docs | 13 | 2 |
| 7. SOUL | 5 | 2 |
| 8. Skills/MCPs | 6 | 2 |
| 9. CLAUDE.md | 3 | 1 |
| 10. Polish | 6 | 2 |
| **Total** | **53** | **15** |

---

## MVP Scope

**Phases 1-3 only** (12 tasks):
- Cleanup NetShell
- Create enable/disable scripts
- Integrate DefenseClaw into install.sh

**Full scope**: All 53 tasks for complete documentation and integration.

---

## Notes

- DefenseClaw replaces ALL NetShell functionality
- DefenseClaw handles OpenShell sandbox automatically
- No custom Python scripts needed - DefenseClaw provides CLI
- docs/DEFENSECLAW.md is the comprehensive enterprise guide
- docs/SOUL-DEFENSE.md contains security principles
- Existing users upgrade via defenseclaw-enable.sh
- Blog post per Constitution XVII
