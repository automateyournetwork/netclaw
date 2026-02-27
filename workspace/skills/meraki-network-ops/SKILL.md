---
name: meraki-network-ops
description: Cisco Meraki Dashboard — organization inventory, network management, device lifecycle, client discovery, action batches
version: 1.0.0
tags: [cisco, meraki, dashboard, network, devices, clients, inventory, organization]
---

# Meraki Network & Device Operations

Manage Cisco Meraki organizations, networks, and devices via the Meraki Magic MCP server — discover inventory, manage networks, claim/unclaim devices, query clients, inspect uplinks, and run action batches for bulk operations.

## MCP Server

- **Repository**: [CiscoDevNet/meraki-magic-mcp-community](https://github.com/CiscoDevNet/meraki-magic-mcp-community)
- **Transport**: stdio (Python via FastMCP) or HTTP (`http://<host>:8008/mcp`)
- **Install**: `git clone` + `pip install -r requirements.txt`
- **Script**: `meraki-mcp-dynamic.py` (recommended — ~804 API endpoints) or `meraki-mcp.py` (40 curated)
- **Requires**: `MERAKI_API_KEY`, `MERAKI_ORG_ID`
- **Python**: 3.13+

## Key Capabilities

### Organization Management

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| List orgs | `getOrganizations` | All Meraki organizations your API key can access |
| Org details | `getOrganizationDetails` | Name, licensing model, management URL |
| Org status | `getOrganizationStatus` | Network/device health summary |
| Org inventory | `getOrganizationInventory` | All claimed devices with model, serial, MAC, network assignment |
| Org license | `getOrganizationLicense` | License status, expiration, device counts |
| Org admins | `getOrganizationAdmins` | Admin accounts and access levels |
| Config changes | `getOrganizationConfigurationChanges` | Who changed what, when (audit trail) |
| API requests | `getOrganizationApiRequests` | API usage log (rate limit monitoring) |
| Webhook logs | `getOrganizationWebhookLogs` | Webhook delivery history |
| Create admin | `createOrganizationAdmin` | **[WRITE]** Add a new admin user |

### Network Management

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| List networks | `getNetworks` | All networks in the org with type, tags, timezone |
| Network details | `getNetworkDetails` | Configuration, product types, enrollment string |
| Create network | `createNetwork` | **[WRITE]** New network (combined, wireless, switch, appliance, camera) |
| Update network | `updateNetwork` | **[WRITE]** Modify name, tags, timezone, notes |
| Delete network | `deleteNetwork` | **[WRITE]** Remove an entire network |
| Network events | `getNetworkEvents` | Event log (up/down, DHCP, auth, config changes) |
| Event types | `getNetworkEventTypes` | Available event categories for filtering |
| Network alerts | `getNetworkAlerts` | Alert history (device down, rogue AP, etc.) |
| Alert settings | `updateNetworkAlertsSettings` | **[WRITE]** Configure alert destinations and thresholds |
| Network traffic | `getNetworkTraffic` | Traffic analytics and application breakdown |

### Device Management

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| List devices (org) | `getDevices` | All devices across the org |
| List devices (network) | `getNetworkDevices` | Devices in a specific network |
| Device details | `getDeviceDetails` | Model, serial, firmware, IP, MAC, tags, notes |
| Device status | `getDeviceStatus` | Online/offline, last seen, gateway IP |
| Device uplinks | `getDeviceUplink` | WAN/cellular uplink status, IP, gateway, DNS |
| Device clients | `getDeviceClients` | Connected clients with usage stats |
| Update device | `updateDevice` | **[WRITE]** Name, tags, notes, lat/lng, address |
| Claim devices | `claimDevices` | **[WRITE]** Add devices to a network by serial |
| Remove device | `removeDevice` | **[WRITE]** Unclaim device from network |
| Reboot device | `rebootDevice` | **[WRITE]** Power cycle a device |

### Client Operations

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| List clients | `getNetworkClients` | Active clients with IP, MAC, VLAN, usage |
| Client details | `getClientDetails` | Full client info: SSID, VLAN, OS, manufacturer |
| Client usage | `getClientUsage` | Bandwidth usage over time |
| Client policy | `getClientPolicy` | Applied group or device policy |
| Update client policy | `updateClientPolicy` | **[WRITE]** Assign a different policy to a client |

### Action Batches (Bulk Operations)

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| Create batch | `createOrganizationActionBatch` | **[WRITE]** Submit bulk API operations |
| Batch status | `getOrganizationActionBatchStatus` | Check progress and results |
| List batches | `getOrganizationActionBatches` | All batches with status |

### Generic API Access

The dynamic MCP exposes a universal `call_meraki_api` tool that can call **any** of the ~804 Meraki Dashboard API methods:

```
call_meraki_api(
    section="networks",
    method="getNetworkFirmwareUpgrades",
    parameters={"networkId": "L_123456789"}
)
```

## Workflow: Organization Inventory Audit

When a user asks "show me all our Meraki devices":

1. **List orgs**: `getOrganizations` — identify accessible orgs
2. **Inventory**: `getOrganizationInventory` — all claimed devices
3. **Device status**: iterate key devices with `getDeviceStatus` — online/offline
4. **Uplinks**: `getDeviceUplink` for MX appliances — WAN connectivity
5. **License**: `getOrganizationLicense` — check expiration
6. **Report**: formatted inventory table with status, firmware, and license health

## Workflow: Network Health Dashboard

When checking overall network health:

1. **List networks**: `getNetworks` — all networks in org
2. **For each network**: `getNetworkEvents` filtered by severity
3. **Alerts**: `getNetworkAlerts` — open alert conditions
4. **Devices**: `getNetworkDevices` — count online vs offline
5. **Report**: network-by-network health summary

## Workflow: Client Investigation

When investigating a specific client:

1. **Find client**: `getNetworkClients` filtered by MAC or IP
2. **Client details**: `getClientDetails` — SSID, VLAN, OS, manufacturer
3. **Usage**: `getClientUsage` — bandwidth consumption
4. **Policy**: `getClientPolicy` — what policy is applied
5. **Device clients**: `getDeviceClients` on the AP/switch serving this client
6. **Report**: client connection details with network path

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-wireless-ops` | Network ops provides network/device context, wireless ops manages SSIDs and RF |
| `meraki-switch-ops` | Network ops provides device discovery, switch ops manages ports and VLANs |
| `meraki-security-appliance` | Network ops provides network context, security manages firewall rules and VPN |
| `meraki-monitoring` | Network ops provides baseline inventory, monitoring tracks health and diagnostics |
| `gait-session-tracking` | Record all Meraki operations in GAIT audit trail |
| `servicenow-change-workflow` | Gate all write operations behind ServiceNow CRs |
| `github-ops` | Commit Meraki config snapshots to Git for change tracking |

## Important Rules

- **READ_ONLY_MODE** — Meraki Magic MCP supports `READ_ONLY_MODE=true` to block all [WRITE] operations
- **API rate limits** — Meraki Dashboard API: 10 requests/second per org; MCP has built-in caching and retry
- **Caching** — Responses cached for 5 minutes by default (`CACHE_TTL_SECONDS=300`), reduces API calls by 50-90%
- **ServiceNow gating** — Never create/delete networks or claim/remove devices without an approved CR (unless lab mode)
- **Record in GAIT** — Log all Meraki inventory audits and device operations

## Environment Variables

- `MERAKI_API_KEY` — Meraki Dashboard API key
- `MERAKI_ORG_ID` — Meraki organization ID
- `ENABLE_CACHING` — Response caching (default: true)
- `CACHE_TTL_SECONDS` — Cache duration in seconds (default: 300)
- `READ_ONLY_MODE` — Block write operations (default: false)
