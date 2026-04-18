# Tasks: Golden Config Bootstrap Workflow

**Input**: Design documents from `/specs/028-golden-config-bootstrap/`
**Prerequisites**: 027-nautobot-mcp-v2 (complete), spec.md

**Organization**: Tasks grouped by user story. Status reflects work already completed.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Prerequisites & Tooling

**Purpose**: MCP tools, skill definition, design reference, template scaffolding

- [x] T001 [US1] Add `cisco_design_reference` tool to nautobot-mcp-v2 — 13 features with best practices, config examples, rationale, RFCs, match_config patterns
- [x] T002 [US3] Add `golden_config_get_template` tool to nautobot-mcp-v2 — read template scaffolding files from references/templates/
- [x] T003 [US1] Add golden config read tools to nautobot-mcp-v2: `nautobot_get_golden_configs`, `nautobot_get_config_compliance`, `nautobot_get_compliance_rules`, `nautobot_get_golden_config_settings`, `nautobot_get_git_repositories`, `nautobot_get_graphql_queries`
- [x] T004 [US4] Add golden config write tools to nautobot-mcp-v2: `nautobot_create_compliance_feature`, `nautobot_create_compliance_rule`, `nautobot_create_git_repository`, `nautobot_create_graphql_query`, `nautobot_update_golden_config_setting`
- [x] T005 Create skill file `workspace/skills/golden-config-bootstrap/SKILL.md` — 8-phase conversational workflow, tool inventory, key design decisions
- [x] T006 [US3] Create 22 Jinja template scaffolding files in `mcp-servers/nautobot-mcp-v2/references/templates/cisco_xe/` — hierarchical structure with entry point, platform template, section templates, interface sub-templates

**Checkpoint**: All MCP tools exist. Skill is defined. Template scaffolding is readable.

---

## Phase 2: Nautobot Server-Side Setup

**Purpose**: Prepare the Nautobot instance for golden config template rendering

- [x] T007 Document Nautobot server-side prerequisites in `golden-config-work/NAUTOBOT_SETUP.md` — netaddr install + ipaddr Jinja filter registration
- [ ] T008 Install `netaddr` in Nautobot Python environment on 192.168.3.253
- [ ] T009 Add `ipaddr` filter to `nautobot_config.py` via `CUSTOM_JINJA_FILTERS` and restart Nautobot services

**Checkpoint**: Nautobot can render templates that use `{{ addr | ipaddr('address') }}`.

---

## Phase 3: User Story 1 — Analyze Live Configs (P1)

**Purpose**: Collect running configs, propose compliance features

**Already done manually** (from prior session):
- [x] T010 Collected running configs from HomeSwitch01 and HomeSwitch02 via pyATS (saved in golden-config-work/)
- [x] T011 Analyzed configs against design reference, identified 12 compliance features
- [x] T012 Created 12 compliance features in Nautobot (aaa, ntp, logging, snmp, ssh, vty_lines, spanning_tree, vtp, interfaces_l2_access, interfaces_l2_trunk, management_plane, dhcp_snooping)
- [x] T013 Created 12 compliance rules linking features to cisco_ios platform with match_config patterns

**Remaining — validate via agent:**
- [ ] T014 Test US1 end-to-end through NetClaw: ask agent to analyze a running config and propose features. Verify it uses `cisco_design_reference` tool and proposes features with rationale.

**Checkpoint**: SC-001 (configs collected), SC-002 (12 features > 5 minimum), SC-003 (rules exist).

---

## Phase 4: User Story 2 — Git Repository (P2)

**Purpose**: Create GitHub repo, register in Nautobot, wire Golden Config Setting

- [ ] T015 [US2] Create private GitHub repo via GitHub MCP with directory structure: `templates/cisco_xe/`, `intended/`, `backups/`
- [ ] T016 [US2] Register git repo in Nautobot via `nautobot_create_git_repository` with provided_contents: `nautobot_golden_config.jinjatemplate`, `nautobot_golden_config.intendedconfigs`, `nautobot_golden_config.backupconfigs`
- [ ] T017 [US2] Update Golden Config Setting via `nautobot_update_golden_config_setting` — link repos, set path templates (`{{obj.platform.network_driver}}/cisco_xe.j2`, `{{obj.location.name}}/{{obj.name}}.cfg`)

**Checkpoint**: SC-005 (GC Setting fully wired).

---

## Phase 5: User Story 3 — Commit Templates (P3)

**Purpose**: Commit Jinja templates to the GitHub repo

- [x] T018 [US3] Design template hierarchy — entry point dispatches by role, platform template includes section templates, section templates read from config_context
- [x] T019 [US3] Build all 22 templates with config_context-driven parameters and SoT data for device-specific values
- [x] T020 [US3] Fix template issues: ntp.j2 blank lines, logging.j2 blank lines, home_switch.j2 service password-encryption, users.j2 secret vs password
- [ ] T021 [US3] Commit all templates to GitHub repo via GitHub MCP (`push_files` or `create_or_update_file`)

**Checkpoint**: SC-004 (templates in correct directory structure in GitHub).

---

## Phase 6: User Story 4 — SoT Query and Config Context (P4)

**Purpose**: Create SoT aggregation query, config context, wire to Golden Config Setting

- [x] T022 [US4] Design SoT aggregation GraphQL query — returns device name, role, platform, location (with VLANs), config_context, interfaces (with VLANs, IPs, LAG, connected_interface)
- [x] T023 [US4] Design config context schema — 12 keys: system, mgmt_vrf, aaa, ntp, logging, snmp, ssh, http, spanning_tree, vtp, users, vty

**Already pushed to Nautobot (from prior session):**
- [x] T024 Created config context in Nautobot scoped to home_switch role
- [x] T025 Created saved GraphQL query in Nautobot
- [x] T026 Wired SoT query to Golden Config Setting

**Remaining:**
- [ ] T027 [US4] Verify SoT query returns correct data for HomeSwitch01 via `nautobot_graphql` tool — confirm config_context, interfaces, VLANs all present

**Checkpoint**: SC-005 (SoT query assigned).

---

## Phase 7: User Story 5 — First Compliance Run (P5)

**Purpose**: Trigger backup/intended/compliance jobs, review results, iterate

- [ ] T028 [US5] Sync git repository in Nautobot (trigger repo sync job) — verify templates are visible
- [ ] T029 [US5] Trigger golden config backup job for HomeSwitch01 and HomeSwitch02
- [ ] T030 [US5] Trigger golden config intended job — verify rendered output matches expected config
- [ ] T031 [US5] Trigger golden config compliance job — review per-feature pass/fail results
- [ ] T032 [US5] Iterate on templates based on compliance diffs — fix any mismatches between intended and backup configs

**Checkpoint**: SC-006 (compliance job runs), SC-007 (agent explains results).

---

## Phase 8: End-to-End Agent Validation

**Purpose**: Run the full bootstrap conversation through NetClaw to validate the skill works

- [ ] T033 Test full 8-phase workflow through NetClaw TUI or Slack — verify the agent follows the skill's conversational flow
- [ ] T034 Verify agent uses `cisco_design_reference` to explain recommendations
- [ ] T035 Verify agent uses `golden_config_get_template` to present templates for review
- [ ] T036 Verify agent handles pfSense-FW01 gracefully (skips — no network_driver)

---

## Dependencies & Execution Order

### Critical Path

1. **Phase 2** (T008-T009): Nautobot server-side setup — BLOCKS template rendering
2. **Phase 4** (T015-T017): GitHub repo + Nautobot registration — BLOCKS template commits
3. **Phase 5** (T021): Commit templates — BLOCKS intended config generation
4. **Phase 7** (T028-T032): First compliance run — BLOCKS validation

### What Can Run Now

- T008-T009: Nautobot server-side setup (manual on Nautobot host)
- T014: Test US1 through agent (MCP server is ready)
- T027: Verify SoT query via agent (data already in Nautobot)

### What Needs GitHub MCP

- T015-T017: Repo creation and Nautobot registration
- T021: Template commits

---

## Notes

- 028 is a SKILL, not an MCP server. The implementation is the SKILL.md file + the tools in nautobot-mcp-v2.
- The "implementation" is running the conversation through NetClaw and verifying the agent follows the workflow.
- Most Nautobot objects (features, rules, config context, SoT query, GC setting) were created manually during the prior session. The agent validation (Phase 8) confirms the agent can do this autonomously.
- Template iteration (T032) is expected — the first compliance run will reveal mismatches that need template adjustments.
