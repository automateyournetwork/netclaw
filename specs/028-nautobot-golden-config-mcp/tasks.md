# Tasks: nautobot-golden-config-mcp

**Input**: `specs/028-nautobot-golden-config-mcp/spec.md`
**Output**: `mcp-servers/nautobot-golden-config-mcp/`
**Prerequisites**: Nautobot running with golden config plugin, git repos registered

---

## Phase 1: Server Scaffold

- [ ] T001 Create `mcp-servers/nautobot-golden-config-mcp/` directory structure
- [ ] T002 Create `server.py` with FastMCP scaffold, env var loading, logging
- [ ] T003 Create `nautobot_client.py` — shared async HTTP client (REST + GraphQL) with auth
- [ ] T004 Create `job_runner.py` — trigger job + poll-until-complete pattern
- [ ] T005 Create `requirements.txt` (httpx, fastmcp, mcp)
- [ ] T006 Register in `config/openclaw.json` with `.venv/bin/python3` path

**Checkpoint**: Server starts, connects to Nautobot, no tools yet.

---

## Phase 2: Config Lifecycle Tools (Core)

- [ ] T007 Implement `golden_config_generate_intended(device=)` — triggers IntendedJob, waits, returns status
- [ ] T008 Implement `golden_config_backup(device=)` — triggers BackupJob, waits, returns status
- [ ] T009 Implement `golden_config_compliance(device=)` — triggers ComplianceJob, waits, returns summary
- [ ] T010 Implement `golden_config_full_pipeline(device=)` — runs intended → backup → compliance in sequence
- [ ] T011 Implement `golden_config_remediate(device=)` — pushes intended config to fix drift

**Checkpoint**: LLM can run the full pipeline in 1-3 tool calls. SC-001 met.

---

## Phase 3: Config Inspection Tools

- [ ] T012 Implement `golden_config_get_intended(device=)` — returns rendered intended config text
- [ ] T013 Implement `golden_config_get_backup(device=)` — returns latest backup config text
- [ ] T014 Implement `golden_config_get_compliance_diff(device=)` — returns per-feature diffs (missing/extra lines)
- [ ] T015 Implement `golden_config_get_compliance_summary(device=, feature=)` — returns compliance table

**Checkpoint**: LLM can inspect compliance state in 1 call. SC-002, SC-003 met.

---

## Phase 4: Template & Context Tools

- [ ] T016 Implement `golden_config_get_templates(device=)` — lists templates for a device's platform/role
- [ ] T017 Implement `golden_config_render_preview(device=)` — renders template with device context (no save)
- [ ] T018 Implement `golden_config_get_device_context(device=)` — returns merged config context
- [ ] T019 Implement `golden_config_update_device_context(device=, key=, value=)` — updates a config context key
- [ ] T020 Implement `golden_config_update_template(path=, content=)` — commits template change to git

**Checkpoint**: LLM can preview and modify templates/contexts. SC-005, SC-006 met.

---

## Phase 5: Setup Tools

- [ ] T021 Implement `golden_config_get_settings()` — returns current GC settings (repos, paths, query)
- [ ] T022 Implement `golden_config_create_compliance_feature(name=, description=)` — creates feature
- [ ] T023 Implement `golden_config_create_compliance_rule(feature=, platform=, match_config=)` — creates rule

**Checkpoint**: LLM can set up golden config from scratch.

---

## Phase 6: Integration & Deprecation

- [ ] T024 Add deprecation warnings to golden config tools in nautobot-mcp-v2 (point to new server)
- [ ] T025 Update `workspace/skills/golden-config-bootstrap/SKILL.md` to reference new MCP server tools
- [ ] T026 Update `workspace/user/TOOLS.md` with golden config MCP server documentation
- [ ] T027 Test full pipeline: update config context → generate intended → compliance → remediate

**Checkpoint**: End-to-end workflow works. SC-007 met (context burn < 200 tokens per operation).

---

## Phase 7: Observability Template Integration

- [ ] T028 Test: update observability config context (add mgmt_vrf) → regenerate intended → compliance shows drift → remediate pushes to all devices
- [ ] T029 Test: add new template section (ip_sla.j2) → regenerate → compliance detects missing IP SLA config → remediate deploys

**Checkpoint**: The syslog/SNMP/IP SLA deployment that currently requires manual Ansible runs can be done entirely through NetClaw + golden config MCP.

---

## Execution Order

```
Phase 1 (scaffold) → Phase 2 (core lifecycle) → Phase 3 (inspection) → Phase 4 (templates) → Phase 5 (setup) → Phase 6 (integration)
                                                                                                                         ↓
                                                                                                                   Phase 7 (test with observability)
```

Phase 2 is the highest value — once the LLM can run intended/backup/compliance/remediate in single calls, the config management workflow is unblocked.
