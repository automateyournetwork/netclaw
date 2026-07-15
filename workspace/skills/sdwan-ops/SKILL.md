---
name: sdwan-ops
description: "Cisco SD-WAN vManage read-only operations — fabric devices, WAN Edge inventory, templates, policies, alarms, events, interface stats, BFD sessions, OMP routes, control connections, running config. Use when checking SD-WAN fabric health, viewing vManage alarms, auditing SD-WAN policies and templates, or troubleshooting BFD tunnels."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["VMANAGE_IP", "VMANAGE_USERNAME", "VMANAGE_PASSWORD"] } } }
---

# Cisco SD-WAN Operations

## MCP Server

- **Source**: [siddhartha2303/cisco-sdwan-mcp](https://github.com/siddhartha2303/cisco-sdwan-mcp)
- **Command**: `python3 -u $SDWAN_MCP_SCRIPT --transport stdio` (stdio transport)
- **Requires**: `VMANAGE_IP`, `VMANAGE_USERNAME`, `VMANAGE_PASSWORD` environment variables
- **Python**: 3.10+
- **Dependencies**: `fastmcp`, `requests`, `python-dotenv`

## How to Call Tools

```bash
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" <tool_name> '<args_json>'
```

## Available Tools (12)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_devices` | none | List all fabric devices — vManage, vSmart, vBond, vEdge with status |
| `get_wan_edge_inventory` | none | WAN Edge details: serial number, chassis ID, model, version |
| `get_device_templates` | none | All device templates with attached device count |
| `get_feature_templates` | none | All feature templates (VPN, interface, routing, security) |
| `get_centralized_policies` | none | Centralized policy definitions (traffic engineering, QoS, security) |
| `get_alarms` | none | Active alarms across the fabric with severity |
| `get_events` | none | Recent audit events and operational logs |
| `get_interface_stats` | `device_ip` | Interface statistics for a specific device (throughput, errors, drops) |
| `get_bfd_sessions` | `device_ip` | BFD session status for device-to-device connectivity health |
| `get_omp_routes` | `device_ip` | OMP routes — received and advertised routes per device |
| `get_control_connections` | `device_ip` | DTLS/TLS control connections between fabric nodes |
| `get_running_config` | `device_ip` | Full running configuration for a device |

## Workflow: SD-WAN Fabric Health Check

When a user asks about SD-WAN health or status:

1. **Fabric overview**: `get_devices` — verify all controllers and edges are reachable
2. **WAN Edge inventory**: `get_wan_edge_inventory` — check serial numbers, versions
3. **Alarms**: `get_alarms` — identify active issues (CRITICAL, MAJOR, MINOR)
4. **Control plane**: `get_control_connections` for key devices — verify DTLS/TLS tunnels
5. **BFD health**: `get_bfd_sessions` for key devices — check tunnel health
6. **Report**: Fabric status summary with severity-sorted findings
7. **GAIT**: Record all queries in audit trail

### Example: Fabric Health

```bash
# List all fabric devices
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_devices '{}'

# Check active alarms
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_alarms '{}'

# Check BFD sessions on a WAN edge
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_bfd_sessions '{"device_ip":"10.10.10.100"}'

# Check OMP routes on a WAN edge
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_omp_routes '{"device_ip":"10.10.10.100"}'
```

## Workflow: SD-WAN Policy Audit

When auditing SD-WAN templates and policies:

1. **Device templates**: `get_device_templates` — list all templates with device counts
2. **Feature templates**: `get_feature_templates` — inspect VPN, interface, routing, security templates
3. **Centralized policies**: `get_centralized_policies` — review traffic engineering and security policies
4. **Config verification**: `get_running_config` for target device — confirm template-applied config
5. **Report**: Template and policy audit with recommendations

### Example: Policy Audit

```bash
# List device templates
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_device_templates '{}'

# List centralized policies
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_centralized_policies '{}'

# Get running config for a specific device
python3 $MCP_CALL "python3 -u $SDWAN_MCP_SCRIPT --transport stdio" get_running_config '{"device_ip":"10.10.10.100"}'
```

## Workflow: SD-WAN Troubleshooting

When investigating SD-WAN connectivity or performance:

1. **Device status**: `get_devices` — is the device reachable via vManage?
2. **Control connections**: `get_control_connections` — DTLS/TLS tunnel state
3. **BFD sessions**: `get_bfd_sessions` — tunnel health between sites
4. **OMP routes**: `get_omp_routes` — are routes being exchanged?
5. **Interface stats**: `get_interface_stats` — throughput, errors, drops
6. **Events**: `get_events` — recent operational events for timeline correlation
7. **Running config**: `get_running_config` — verify configuration matches intent

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | CLI-level verification of SD-WAN edge devices via SSH |
| **gait-session-tracking** | Record all vManage queries in GAIT audit trail |
| **markmap-viz** | Visualize SD-WAN fabric topology as mind map |
| **uml-diagram** | Generate SD-WAN architecture diagrams (nwdiag, sequence) |
| **servicenow-change-workflow** | Reference SD-WAN audit findings in CRs |

## Important Rules

- **All operations are read-only** — no configuration changes can be made through this MCP server
- **GAIT audit mandatory** — record all vManage queries in the session audit trail
- **Cross-reference with pyATS** — use CLI-level verification alongside vManage API data for complete visibility
- **SSL verification** — vManage API uses HTTPS; SSL certificate warnings are suppressed by the MCP server for lab/self-signed certs
- **API rate limits** — vManage may rate-limit API requests; avoid rapid polling

## Error Handling

- **Auth fails (401/403)**: Check `VMANAGE_IP`, `VMANAGE_USERNAME`, `VMANAGE_PASSWORD` in `~/.openclaw/.env`
- **Connection timeout**: Verify vManage is reachable from the NetClaw host (`ping $VMANAGE_IP`)
- **Device IP not found**: Use `get_devices` to list all devices and find correct system IP
- **Empty results**: Device may not be onboarded or may be unreachable from vManage

## Environment Variables

- `VMANAGE_IP` — vManage IP address or hostname
- `VMANAGE_USERNAME` — vManage API username
- `VMANAGE_PASSWORD` — vManage API password
- `SDWAN_MCP_SCRIPT` — Path to the Python MCP server script (set by install.sh)
- `MCP_CALL` — Path to mcp-call.py wrapper (set by install.sh)
