---
name: nso-device-ops
description: Cisco NSO device operations — config retrieval, state inspection, sync, platform info, NED IDs, device groups
version: 1.0.0
tags: [nso, orchestration, config, sync, restconf]
---

# NSO Device Operations

You have access to Cisco Network Services Orchestrator (NSO) via the NSO MCP server. This skill covers device-level operations — retrieving configurations, checking operational state, synchronizing devices, and inspecting platform metadata.

## MCP Server

- **Command**: `cisco-nso-mcp-server` (pip-installed, stdio transport)
- **Requires**: `NSO_ADDRESS`, `NSO_USERNAME`, `NSO_PASSWORD` environment variables
- **Optional**: `NSO_SCHEME` (default: http), `NSO_PORT` (default: 8080), `NSO_VERIFY`, `NSO_TIMEOUT`
- **API**: RESTCONF (RFC 8040)

## Available Tools

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_device_config` | `device_name` | Get the full configuration for a device from NSO's CDB |
| `get_device_state` | `device_name` | Get operational state data for a device (interfaces, counters, status) |
| `check_device_sync` | `device_name` | Check if NSO's copy of the device config is in sync with the actual device |
| `sync_from_device` | `device_name` | Pull the current config from the device into NSO's CDB (sync-from) |
| `get_device_platform` | `device_name` | Get platform info: model, OS version, serial number, hardware details |
| `get_device_ned_ids` | none | List all Network Element Driver (NED) IDs — shows what device types NSO can manage |
| `get_device_groups` | none | List all device groups defined in NSO |

## MCP Resource

| Resource URI | What It Returns |
|-------------|----------------|
| `https://resources.cisco-nso-mcp.io/environment` | NSO environment summary: device count, OS distribution, unique models, device series, group membership |

## Workflow: Device Configuration Audit

When a user asks "show me R1's config from NSO" or "what does NSO have for the core routers":

1. **Get device groups**: `get_device_groups` to see how devices are organized
2. **Get config**: `get_device_config` for each target device
3. **Present**: Format the configuration in a readable way
4. **Cross-reference**: Compare with pyATS live config if discrepancies suspected

## Workflow: Sync Check and Remediation

When a user asks "are my devices in sync?" or "is NSO up to date?":

1. **Check sync**: `check_device_sync` for the target device(s)
2. **If out of sync**: Report which devices are out of sync and why
3. **Remediate**: Use `sync_from_device` to pull current config from the device into NSO
4. **Verify**: Run `check_device_sync` again to confirm sync is restored
5. **Record in GAIT**: Log the sync operation for audit trail

## Workflow: NSO Environment Overview

When a user asks "what's in NSO?" or "show me the NSO inventory":

1. **Environment resource**: Read the NSO environment resource for the summary
2. **Device groups**: `get_device_groups` to see organizational structure
3. **NED IDs**: `get_device_ned_ids` to see what device types are managed
4. **Platform details**: `get_device_platform` for specific devices of interest
5. **Report**: Summary table of devices, OS types, models, and group membership

## Workflow: Pre-Change Baseline from NSO

Before making configuration changes:

1. **Get current config**: `get_device_config` to capture the NSO baseline
2. **Check sync**: `check_device_sync` to ensure NSO is current
3. **If out of sync**: `sync_from_device` first to get the latest state
4. **Save baseline**: Commit the config to GAIT or GitHub for audit trail
5. **Proceed with change**: Use pyATS or NSO services to apply changes

## Workflow: Device Platform Inventory

When a user needs hardware/software details:

1. **Get platform**: `get_device_platform` for each device
2. **Compile report**: Model, serial, OS version, hardware
3. **Cross-reference**: Check NVD for CVEs against OS versions (use nvd-cve skill)
4. **Cross-reference**: Compare with NetBox records for accuracy (use netbox-reconcile skill)

## NSO Concepts

| Concept | Meaning |
|---------|---------|
| **CDB** | Configuration Database — NSO's copy of all device configs |
| **NED** | Network Element Driver — plugin that translates between NSO's model and device CLI/NETCONF |
| **sync-from** | Pull config from device into NSO CDB |
| **sync-to** | Push NSO CDB config to device (not available in this MCP — use services instead) |
| **Device Group** | Logical grouping of devices for bulk operations |
| **Service** | NSO service instance that provisions config across devices (see nso-service-mgmt skill) |

## Integration with Other Skills

| Scenario | Integration |
|----------|-------------|
| Config differs from NSO | Compare `get_device_config` (NSO) vs pyATS `show running-config` (live) |
| Device inventory audit | Compare `get_device_platform` (NSO) vs NetBox records |
| Pre-change validation | NSO config baseline → ServiceNow CR → pyATS apply → NSO sync verify |
| Vulnerability scanning | `get_device_platform` (OS version) → NVD CVE search |
| Config backup to GitHub | `get_device_config` → github-ops commit to repo |

## Important Rules

- **NSO is the orchestration layer** — it manages device configs through RESTCONF/NETCONF, not CLI
- **Always check sync before trusting config** — `check_device_sync` first
- **sync_from_device pulls FROM the device** — it overwrites NSO's CDB with what's actually on the device
- **Read-heavy operations are safe** — get_device_config, get_device_state, check_device_sync are non-destructive
- **sync_from_device modifies NSO CDB** — it's safe for the device but changes NSO's database
- **Record in GAIT** — log all NSO operations for audit trail

## Environment Variables

- `NSO_SCHEME` — http or https (default: http)
- `NSO_ADDRESS` — NSO server address (default: localhost)
- `NSO_PORT` — RESTCONF port (default: 8080)
- `NSO_USERNAME` — NSO username (default: admin)
- `NSO_PASSWORD` — NSO password (default: admin)
- `NSO_VERIFY` — Verify SSL certificate (default: true)
- `NSO_TIMEOUT` — Connection timeout in seconds (default: 10)
