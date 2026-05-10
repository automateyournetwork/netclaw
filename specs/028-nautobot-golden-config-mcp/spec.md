# Feature Specification: nautobot-golden-config-mcp

**Spec**: `028-nautobot-golden-config-mcp`
**Created**: 2026-04-09 (originally golden-config-bootstrap skill)
**Updated**: 2026-05-10 (rewritten as standalone MCP server)
**Status**: In Progress
**Server Location**: `mcp-servers/nautobot-golden-config-mcp/server.py`

## Context

The Nautobot Golden Config plugin is the config management engine for the lab. It generates intended configs from Jinja templates + config contexts, pulls backups from devices, diffs them for compliance, and can remediate drift.

Currently, the golden config tools are scattered across `nautobot-mcp-v2` (read tools) and the `golden-config-bootstrap` skill (orchestration logic). The LLM burns excessive context navigating raw Nautobot APIs to accomplish config lifecycle tasks.

**This spec defines a standalone MCP server** (`nautobot-golden-config-mcp`) that provides high-level, purpose-built tools for the config lifecycle pipeline. The LLM calls one tool instead of 10+ API calls.

## Design Principles

1. **One tool = one workflow step** — no multi-call sequences for common operations
2. **Nautobot is the engine** — this MCP server orchestrates Nautobot's golden config jobs, it doesn't bypass them
3. **PyATS is for verification only** — config pushes go through Nautobot's Nornir/NAPALM backend, not direct pyATS
4. **Idempotent** — calling a tool twice with the same params produces the same result
5. **SoT-first** — tools that modify config contexts or templates update Nautobot first, then trigger regeneration

## Tools

### Config Lifecycle (Core Pipeline)

| Tool | Purpose | Nautobot Action |
|------|---------|-----------------|
| `golden_config_generate_intended` | Render intended config for device(s) from templates + SoT data | Triggers IntendedJob |
| `golden_config_backup` | Pull running config from device(s) into Nautobot | Triggers BackupJob |
| `golden_config_compliance` | Compare intended vs backup, produce compliance results | Triggers ComplianceJob |
| `golden_config_remediate` | Push intended config to non-compliant device(s) to fix drift | Triggers ConfigPlanDeploy or direct push |
| `golden_config_full_pipeline` | Run all three (intended → backup → compliance) in sequence for device(s) | Triggers all three jobs sequentially |

### Config Inspection

| Tool | Purpose | Returns |
|------|---------|---------|
| `golden_config_get_intended` | Get the rendered intended config for a device | The full intended config text |
| `golden_config_get_backup` | Get the latest backup config for a device | The full backup config text |
| `golden_config_get_compliance_diff` | Get the compliance diff for a device (what's different) | Per-feature diffs: missing lines, extra lines, ordered/unordered |
| `golden_config_get_compliance_summary` | Get compliance status across all devices or filtered | Table: device, feature, compliant (yes/no), last run |

### Template Management

| Tool | Purpose | Returns |
|------|---------|---------|
| `golden_config_get_templates` | List templates that apply to a device (based on platform/role) | Template file paths and content |
| `golden_config_render_preview` | Render a template with a device's config context (dry run, no save) | The rendered config text |
| `golden_config_update_template` | Update a template file in the git repo | Commits the change via GitHub MCP or direct git |

### Config Context Management

| Tool | Purpose | Returns |
|------|---------|---------|
| `golden_config_get_device_context` | Get the merged config context as templates see it | Full merged dict |
| `golden_config_update_device_context` | Update a device-specific config context | Updates the config context in Nautobot |
| `golden_config_add_context_key` | Add a key to a config context (e.g., add `ip_sla` block to observability context) | Updated context |

### Setup & Wiring

| Tool | Purpose | Returns |
|------|---------|---------|
| `golden_config_get_settings` | Get the current golden config settings (repos, paths, SoT query) | Settings object |
| `golden_config_create_compliance_feature` | Create a compliance feature (e.g., 'observability', 'bgp', 'ospf') | Feature ID |
| `golden_config_create_compliance_rule` | Create a compliance rule linking feature to platform with match_config | Rule ID |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NAUTOBOT_URL` | Yes | `http://localhost:8080` | Nautobot instance URL |
| `NAUTOBOT_TOKEN` | Yes | — | Nautobot API token |
| `NAUTOBOT_TIMEOUT` | No | `60` | API request timeout (seconds) |
| `GOLDEN_CONFIG_POLL_INTERVAL` | No | `5` | Seconds between job status polls |
| `GOLDEN_CONFIG_JOB_TIMEOUT` | No | `300` | Max seconds to wait for a job to complete |

## Server Structure

```
mcp-servers/nautobot-golden-config-mcp/
├── server.py              # FastMCP server with all tools
├── nautobot_client.py     # Shared Nautobot REST/GraphQL client
├── job_runner.py          # Job trigger + poll-until-complete logic
├── requirements.txt       # httpx, fastmcp, mcp
└── __init__.py
```

## Key Implementation Details

### Job Runner Pattern

Golden config operations are async jobs in Nautobot. The pattern:
1. POST to `/api/extras/jobs/<job-id>/run/` with device filter
2. Poll `/api/extras/job-results/<result-id>/` until status is "completed" or "failed"
3. Return the result

```python
async def run_job_and_wait(job_class_path: str, data: dict, timeout: int = 300) -> dict:
    """Trigger a Nautobot job and wait for completion."""
    # Find job by class_path
    # POST to run endpoint
    # Poll until complete or timeout
    # Return result
```

### Device Filtering

Most tools accept an optional `device` parameter. When provided:
- Filter by device name for single-device operations
- When omitted, operate on all devices in the golden config scope

### Compliance Diff Format

The compliance diff should be human-readable:
```
Device: RR1
Feature: observability
Status: NON-COMPLIANT

Missing (should be on device but isn't):
+ logging trap informational

Extra (on device but not in intended):
- logging host 192.168.220.200 transport udp port 1514
```

## Relationship to Other MCP Servers

| Server | Responsibility |
|--------|---------------|
| `nautobot-mcp-v2` | SoT CRUD: devices, interfaces, IPs, BGP, VLANs, config contexts (create/read/update) |
| `nautobot-golden-config-mcp` | Config lifecycle: generate intended, backup, compliance, remediate, template management |
| `pyATS MCP` | Ad-hoc show commands, troubleshooting, verification (NOT config pushes) |

## Migration from nautobot-mcp-v2

These tools currently in nautobot-mcp-v2 should be **deprecated** (kept for backward compat) and replaced by this server:

- `nautobot_get_golden_configs` → `golden_config_get_intended` / `golden_config_get_backup`
- `nautobot_get_config_compliance` → `golden_config_get_compliance_summary`
- `nautobot_get_compliance_rules` → `golden_config_get_settings`
- `nautobot_get_golden_config_settings` → `golden_config_get_settings`
- `nautobot_create_compliance_feature` → `golden_config_create_compliance_feature`
- `nautobot_create_compliance_rule` → `golden_config_create_compliance_rule`
- `nautobot_update_golden_config_setting` → `golden_config_get_settings` (read) + direct update
- `nautobot_render_device_config` → `golden_config_render_preview`
- `nautobot_get_device_config_context` → `golden_config_get_device_context`

## Success Criteria

- **SC-001**: LLM can run the full config pipeline (intended → backup → compliance) in 3 tool calls or fewer
- **SC-002**: LLM can check compliance status for a device in 1 tool call
- **SC-003**: LLM can view the compliance diff (what's wrong) in 1 tool call
- **SC-004**: LLM can remediate a non-compliant device in 1 tool call
- **SC-005**: LLM can preview what a template renders for a device in 1 tool call
- **SC-006**: LLM can update a config context and regenerate intended config in 2 tool calls
- **SC-007**: No more than 200 tokens of context burned per golden config operation (vs 2000+ currently)

## Workflow Example: Fix Syslog Drift

Before (current — LLM spirals through 15+ calls):
```
nautobot_graphql → find device → nautobot_get_golden_configs → parse response →
nautobot_get_config_compliance → parse → figure out what's wrong → nautobot_run_job →
poll job → poll again → get result → parse compliance → ...
```

After (with this MCP server):
```
golden_config_get_compliance_diff(device="RR1")
→ "RR1 missing: logging trap informational"

golden_config_remediate(device="RR1")
→ "Pushed intended config. RR1 now compliant."
```

Two calls. Done.
