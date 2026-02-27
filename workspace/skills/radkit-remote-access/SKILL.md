---
name: radkit-remote-access
description: Cisco RADKit — cloud-relayed remote device access, CLI execution, SNMP polling, device inventory discovery, attribute inspection
version: 1.0.0
tags: [cisco, radkit, remote-access, cli, snmp, inventory, cloud-relay]
---

# RADKit Remote Device Access

Securely access remote network devices via the Cisco RADKit cloud relay — discover device inventory, inspect device attributes and capabilities, execute CLI commands with timeout and truncation controls, and perform SNMP GET operations. RADKit bridges the gap between cloud-hosted AI agents and on-premises network devices without requiring direct SSH/SNMP connectivity from the agent host.

## MCP Server

- **Repository**: [CiscoDevNet/radkit-mcp-server-community](https://github.com/CiscoDevNet/radkit-mcp-server-community)
- **Transport**: stdio (Python via FastMCP), SSE, or HTTPS
- **Requires**: `RADKIT_IDENTITY`, `RADKIT_DEFAULT_SERVICE_SERIAL`, active RADKit service instance
- **Python**: 3.10+

## How RADKit Works

RADKit provides a **cloud-relayed** path to on-premises devices:

```
NetClaw Agent  -->  RADKit Cloud  -->  RADKit Service (on-prem)  -->  Device (CLI/SNMP)
```

- The **RADKit Service** runs inside the network perimeter, onboarded with access to devices
- The **RADKit Client** (this MCP server) authenticates via certificate-based identity
- All communication is encrypted, relayed through Cisco's RADKit cloud infrastructure
- No direct SSH/SNMP from the agent host to the devices is needed

This is ideal for:
- **Air-gapped networks** where the AI agent cannot directly SSH to devices
- **Cloud-hosted agents** that need to reach on-premises devices
- **Multi-site operations** where a single RADKit service provides access to many devices
- **Secure environments** where certificate-based auth is required (no passwords in transit)

## MCP Tools

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_device_inventory_names` | none | List all onboarded device names from the RADKit service |
| `get_device_attributes` | `target_device` | Retrieve device details in JSON: host, type, configs, SNMP/NETCONF status, capabilities |
| `exec_cli_commands_in_device` | `target_device, commands, timeout?, max_lines?` | Execute CLI commands on a device with timeout and line-limit controls |
| `snmp_get` | `target_device, oid(s), timeout?` | Perform SNMP GET operations without CLI execution |
| `exec_command` | `target_device, commands` | Structured command execution — returns dict/list with status and truncation info |

### Tool Details

#### get_device_inventory_names

Discovers all devices onboarded to the RADKit service. Call this first to know what devices are available.

Returns a set of device names, e.g.: `{"edge-rtr-01", "core-sw-01", "dc-fw-01"}`

#### get_device_attributes

Retrieves detailed JSON attributes for a specific device:
- **Name** and **host** address
- **Device type** (router, switch, firewall, etc.)
- **Configuration capabilities** (SSH, NETCONF, RESTCONF)
- **SNMP status** (enabled, community/v3 config)
- **Platform details** (model, OS, version)

Safe for parallel execution across multiple devices.

#### exec_cli_commands_in_device

Executes CLI commands on a device through the RADKit relay:
- **timeout** — maximum wait time per command (prevents hung sessions)
- **max_lines** — truncate output to N lines (prevents massive output from flooding context)
- Returns raw CLI output as text

Use this for standard show commands, debug captures, and configuration inspection.

#### snmp_get

Performs SNMP GET without executing CLI:
- Query one or more OIDs in a single call
- Useful for metric polling (uptime, interface counters, CPU utilization)
- Lower overhead than CLI for structured data retrieval

Common OIDs:
| OID | Metric |
|-----|--------|
| `1.3.6.1.2.1.1.1.0` | System Description |
| `1.3.6.1.2.1.1.3.0` | System Uptime |
| `1.3.6.1.2.1.1.5.0` | System Name |
| `1.3.6.1.2.1.2.2.1.2` | Interface Description |
| `1.3.6.1.2.1.2.2.1.8` | Interface Operational Status |

#### exec_command

Structured command execution that returns a dictionary or list:
- Includes **status** (success/failure) per command
- Includes **truncation info** if output exceeded limits
- Better for programmatic processing than raw CLI output

## Workflow: Remote Device Discovery

When first connecting via RADKit:

1. **Inventory**: `get_device_inventory_names` — what devices are available?
2. **Attributes**: `get_device_attributes` for each device — type, platform, capabilities
3. **Quick health**: `snmp_get` with sysUpTime (1.3.6.1.2.1.1.3.0) for each device
4. **Report**: device inventory table with type, platform, and uptime

## Workflow: Remote CLI Troubleshooting

When investigating an issue on a remote device:

1. **Identify device**: `get_device_inventory_names` — find the target device name
2. **Check capabilities**: `get_device_attributes` — confirm CLI access is available
3. **Execute commands**: `exec_cli_commands_in_device` with timeout and max_lines
   - `show ip interface brief` — interface status
   - `show ip route summary` — routing table health
   - `show processes cpu sorted` — CPU utilization
   - `show logging last 50` — recent syslog messages
4. **Structured output**: `exec_command` for commands needing programmatic parsing
5. **Report**: troubleshooting findings with device state

## Workflow: Remote SNMP Polling

When collecting metrics from remote devices:

1. **Inventory**: `get_device_inventory_names` — target devices
2. **System info**: `snmp_get` with sysDescr, sysName, sysUpTime
3. **Interface status**: `snmp_get` with ifOperStatus for key interfaces
4. **Counters**: `snmp_get` with ifInOctets, ifOutOctets for bandwidth tracking
5. **Report**: SNMP metric summary with uptime and interface health

## Workflow: Multi-Site Health Check via RADKit

When checking health across sites served by the RADKit service:

1. **Inventory**: `get_device_inventory_names` — all devices across sites
2. **Attributes**: `get_device_attributes` for each — group by type and site
3. **Health commands**: `exec_cli_commands_in_device` per device:
   - `show version` — uptime, software version
   - `show processes cpu | include CPU utilization`
   - `show memory statistics`
4. **SNMP baseline**: `snmp_get` for sysUpTime, interface counters
5. **Report**: multi-site health dashboard with per-device status

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `pyats-network` | RADKit for cloud-relayed access, pyATS for direct SSH — complementary paths to devices |
| `pyats-health-check` | RADKit provides remote device data; pyATS health-check procedures analyze it |
| `pyats-troubleshoot` | RADKit CLI exec for remote devices that pyATS can't reach directly |
| `pyats-routing` | Use RADKit to collect routing state from remote sites, analyze with routing skill |
| `pyats-security` | RADKit CLI for remote security audit commands (ACLs, AAA, CoPP) |
| `meraki-monitoring` | Meraki for cloud-managed devices, RADKit for on-prem devices behind Meraki MX |
| `te-path-analysis` | ThousandEyes external path + RADKit internal CLI for end-to-end troubleshooting |
| `nso-device-ops` | NSO for orchestrated config, RADKit for raw CLI access to same devices |
| `gait-session-tracking` | Record all RADKit remote access sessions in GAIT |
| `servicenow-change-workflow` | Gate any config changes through RADKit with ServiceNow CRs |

## Important Rules

- **RADKit is read-write capable** — if the onboarded user has write access, CLI commands can push configuration. Always gate config changes with ServiceNow CRs.
- **Certificate security is critical** — the RADKit private key must never be shared. Use strong passphrases.
- **Timeout controls prevent hung sessions** — always set reasonable timeouts on CLI commands (default: 30 seconds).
- **max_lines prevents context overflow** — use line limits for commands with potentially large output (show tech, show run on large configs).
- **SNMP is lighter than CLI** — prefer `snmp_get` over CLI for structured metrics (uptime, counters, status).
- **One RADKit service can serve many devices** — the service runs on-prem and proxies to all onboarded devices.
- **Record in GAIT** — log all remote access sessions, commands executed, and findings.
- **This is a community project** — not an official Cisco product. Use for experimentation, learning, and authorized operations.

## Environment Variables

- `RADKIT_IDENTITY` — User email address for RADKit authentication
- `RADKIT_DEFAULT_SERVICE_SERIAL` — RADKit service instance identifier

### Container/CI Deployment (base64-encoded credentials)

- `RADKIT_CERT_B64` — Base64-encoded client certificate
- `RADKIT_KEY_B64` — Base64-encoded private key
- `RADKIT_CA_B64` — Base64-encoded CA chain
- `RADKIT_KEY_PASSWORD_B64` — Base64-encoded key password

### Local Development

For local use, RADKit auto-detects certificates in `~/.radkit/identities/` generated during the setup onboarding wizard (`bash setup.sh` in the cloned repo).
