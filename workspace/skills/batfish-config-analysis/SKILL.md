---
name: batfish-config-analysis
description: "Batfish network configuration analysis -- pre-deployment validation, reachability testing, ACL/firewall tracing, differential analysis, compliance checking. Use when validating configs before deployment, testing traffic paths, tracing ACL rules, comparing config versions, or auditing compliance policies. Strictly read-only."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "docker"], "env": ["BATFISH_HOST"] } } }
---

# Batfish Configuration Analysis

## MCP Server

- **Source**: Built-in (mcp-servers/batfish-mcp/)
- **Command**: `python3 -u mcp-servers/batfish-mcp/batfish_mcp_server.py` (stdio transport)
- **Requires**: Batfish Docker container running, `BATFISH_HOST` and `BATFISH_PORT` environment variables
- **Python**: 3.10+
- **Dependencies**: `pybatfish`, `mcp[cli]`, `python-dotenv`

## Available Tools (8)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `batfish_upload_snapshot` | `snapshot_name`, `configs`/`config_path`, `network` | Upload device configs to Batfish and create a named snapshot |
| `batfish_validate_config` | `snapshot_name`, `network` | Validate configs with per-device pass/fail status, vendor detection, warnings |
| `batfish_test_reachability` | `snapshot_name`, `src_ip`, `dst_ip`, `protocol`, `dst_port` | Test if traffic can flow between two endpoints with full path trace |
| `batfish_trace_acl` | `snapshot_name`, `device`, `filter_name`, `src_ip`, `dst_ip`, `protocol`, `dst_port` | Trace a packet through ACL rules to find matching permit/deny rule |
| `batfish_diff_configs` | `reference_snapshot`, `candidate_snapshot`, `include_routes`, `include_reachability` | Compare two snapshots for route and reachability differences |
| `batfish_check_compliance` | `snapshot_name`, `policy_type` | Check configs against compliance policies (6 built-in policy types) |
| `batfish_list_snapshots` | `network` | List all available snapshots |
| `batfish_delete_snapshot` | `snapshot_name`, `network` | Delete a snapshot |

## Workflow: Pre-Change Validation

When a user wants to validate configurations before deployment:

1. **Upload configs**: `batfish_upload_snapshot` with inline configs dict or path to config directory
2. **Validate**: `batfish_validate_config` to check parse status, vendor detection, warnings/errors
3. **Test reachability**: `batfish_test_reachability` for critical traffic paths
4. **Check compliance**: `batfish_check_compliance` against organizational policies
5. **Report**: Structured pass/fail results with specific findings
6. **GAIT**: All operations automatically logged

### Example: Validate Before Deploy

```bash
# Upload proposed configs
batfish_upload_snapshot snapshot_name="pre-change-site-a" config_path="/path/to/configs/"

# Validate parse status
batfish_validate_config snapshot_name="pre-change-site-a"

# Test critical path
batfish_test_reachability snapshot_name="pre-change-site-a" src_ip="10.1.1.1" dst_ip="10.2.2.1" protocol="TCP" dst_port=443

# Check compliance
batfish_check_compliance snapshot_name="pre-change-site-a" policy_type="interface_descriptions"
```

## Workflow: Change Impact Analysis

When comparing before/after configurations:

1. **Upload "before" snapshot**: `batfish_upload_snapshot` with current configs
2. **Upload "after" snapshot**: `batfish_upload_snapshot` with proposed configs
3. **Diff**: `batfish_diff_configs` to find route and reachability differences
4. **Investigate**: Use `batfish_trace_acl` on any newly denied traffic
5. **Report**: Structured diff showing added/removed/changed routes and flows

## Workflow: ACL Troubleshooting

When investigating access control issues:

1. **Upload configs**: `batfish_upload_snapshot` with device configs
2. **Trace packet**: `batfish_trace_acl` with device, ACL name, and packet headers
3. **Review**: Identify matching rule, line number, permit/deny action
4. **Test alternatives**: Modify config, re-upload, trace again

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-config-mgmt** | Validate configs with Batfish before pushing via pyATS |
| **gait-session-tracking** | All Batfish operations automatically logged |
| **servicenow-change-workflow** | Reference Batfish validation in change request evidence |
| **fwrule-analyzer** | Complement ACL trace with cross-vendor overlap analysis |
| **cml-lab-lifecycle** | Validate CML lab configs with Batfish analysis |

## Important Rules

- **All operations are strictly read-only** -- Batfish analyzes uploaded configs, never modifies network devices
- **GAIT audit mandatory** -- All operations logged automatically
- **Snapshots are ephemeral** -- Batfish manages snapshot lifecycle; use GAIT for persistent records
- **Multi-vendor** -- Supports Cisco IOS/IOS-XE/NX-OS, JunOS, Arista EOS, Palo Alto, F5

## Error Handling

- **BATFISH_UNREACHABLE**: Verify Docker container is running (`docker ps | grep batfish`)
- **SNAPSHOT_NOT_FOUND**: Use `batfish_list_snapshots` to see available snapshots
- **INVALID_INPUT**: Check configs dict is non-empty or config_path exists
- **DEVICE_NOT_FOUND**: Use `batfish_validate_config` to list devices in snapshot
- **FILTER_NOT_FOUND**: Verify ACL/filter name exists on the specified device

## Environment Variables

- `BATFISH_HOST` -- Batfish hostname (default: localhost)
- `BATFISH_PORT` -- Batfish port (default: 9997)
- `BATFISH_NETWORK` -- Default network name (default: netclaw)
