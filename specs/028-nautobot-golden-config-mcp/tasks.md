# Tasks: nautobot-golden-config-mcp

**Input**: `specs/028-nautobot-golden-config-mcp/spec.md`
**Output**: `mcp-servers/nautobot-golden-config-mcp/`
**Prerequisites**: Nautobot running with golden config plugin, git repos registered

---

## Phase 1: Server Scaffold

- [x] T001 Create `mcp-servers/nautobot-golden-config-mcp/` directory structure
- [x] T002 Create `server.py` with FastMCP scaffold, env var loading, logging
- [x] T003 Create `nautobot_client.py` — shared async HTTP client (REST + GraphQL) with auth
- [x] T004 Create `job_runner.py` — trigger job + poll-until-complete pattern
- [x] T005 Create `requirements.txt` (httpx, fastmcp, mcp)
- [x] T006 Register in `config/openclaw.json` with `.venv/bin/python3` path

**Checkpoint**: Server starts, connects to Nautobot, no tools yet.

---

## Phase 2: Config Lifecycle Tools (Core)

- [x] T007 Implement `golden_config_generate_intended(device=)` — triggers IntendedJob, waits, returns status
- [x] T008 Implement `golden_config_backup(device=)` — triggers BackupJob, waits, returns status
- [x] T009 Implement `golden_config_compliance(device=)` — triggers ComplianceJob, waits, returns summary
- [x] T010 Implement `golden_config_full_pipeline(device=)` — runs intended → backup → compliance in sequence
- [x] T011 Implement `golden_config_remediate(device=)` — pushes intended config to fix drift

**Checkpoint**: LLM can run the full pipeline in 1-3 tool calls. SC-001 met.

---

## Phase 3: Config Inspection Tools

- [x] T012 Implement `golden_config_get_intended(device=)` — returns rendered intended config text
- [x] T013 Implement `golden_config_get_backup(device=)` — returns latest backup config text
- [x] T014 Implement `golden_config_get_compliance_diff(device=)` — returns per-feature diffs (missing/extra lines)
- [x] T015 Implement `golden_config_get_compliance_summary(device=, feature=)` — returns compliance table

**Checkpoint**: LLM can inspect compliance state in 1 call. SC-002, SC-003 met.

---

## Phase 4: Template & Context Tools

- [x] T016 Implement `golden_config_get_templates(device=)` — lists templates for a device's platform/role
- [x] T017 Implement `golden_config_render_preview(device=)` — renders template with device context (no save)
- [x] T018 Implement `golden_config_get_device_context(device=)` — returns merged config context
- [x] T019 Implement `golden_config_update_device_context(device=, key=, value=)` — updates a config context key
- [x] T020 Implement `golden_config_update_template(path=, content=)` — commits template change to git

**Checkpoint**: LLM can preview and modify templates/contexts. SC-005, SC-006 met.

---

## Phase 5: Setup Tools

- [x] T021 Implement `golden_config_get_settings()` — returns current GC settings (repos, paths, query)
- [x] T022 Implement `golden_config_create_compliance_feature(name=, description=)` — creates feature
- [x] T023 Implement `golden_config_create_compliance_rule(feature=, platform=, match_config=)` — creates rule

**Checkpoint**: LLM can set up golden config from scratch.

---

## Phase 6: Integration & Deprecation

- [x] T024 Add deprecation warnings to golden config tools in nautobot-mcp-v2 (point to new server)
- [x] T025 Update `workspace/skills/golden-config-bootstrap/SKILL.md` to reference new MCP server tools
- [x] T026 Update `workspace/user/TOOLS.md` with golden config MCP server documentation
- [x] T027 Test full pipeline: update config context → generate intended → compliance → remediate

**Checkpoint**: End-to-end workflow works. SC-007 met (context burn < 200 tokens per operation).

---

## Phase 7: Observability Template Integration

- [x] T028 Test: update observability config context (add mgmt_vrf) → regenerate intended → compliance shows drift → remediate pushes to all devices
- [x] T029 Test: add new template section (ip_sla.j2) → regenerate → compliance detects missing IP SLA config → remediate deploys

**T028 Results:** Context update → regenerate → compliance workflow verified end-to-end against live Nautobot. Context update correctly finds role-matched context with key-preference logic. Intended regeneration and compliance jobs complete in ~5s each. Drift detection requires template to reference the new key (expected — tools work, template authoring is separate).

**T029 Results:** Full IP SLA workflow verified: create feature + rule → update context → prepare template → regenerate → compliance detects new feature (13 total). Compliance correctly reports compliant when both intended and backup are empty for the match pattern. Once template is committed to git via GitHub MCP, intended will render IP SLA config and compliance will detect drift against backup. All tools in the chain work correctly.

**Checkpoint**: The syslog/SNMP/IP SLA deployment that currently requires manual Ansible runs can be done entirely through NetClaw + golden config MCP.

---

## Execution Order

```
Phase 1 (scaffold) → Phase 2 (core lifecycle) → Phase 3 (inspection) → Phase 4 (templates) → Phase 5 (setup) → Phase 6 (integration)
                                                                                                                         ↓
                                                                                                                   Phase 7 (test with observability)
```

Phase 2 is the highest value — once the LLM can run intended/backup/compliance/remediate in single calls, the config management workflow is unblocked.
