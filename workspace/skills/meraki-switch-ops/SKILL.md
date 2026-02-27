---
name: meraki-switch-ops
description: Cisco Meraki Switching — port configuration, VLANs, port status, ACLs, QoS rules, port cycling
version: 1.0.0
tags: [cisco, meraki, switch, port, vlan, acl, qos, ms]
---

# Meraki Switch Operations

Manage Cisco Meraki switches via the Meraki Magic MCP server — configure switch ports, manage VLANs, inspect port statuses, set ACLs, create QoS rules, and cycle ports for troubleshooting.

## MCP Server

- **Repository**: [CiscoDevNet/meraki-magic-mcp-community](https://github.com/CiscoDevNet/meraki-magic-mcp-community)
- **Transport**: stdio (Python via FastMCP) or HTTP
- **Requires**: `MERAKI_API_KEY`, `MERAKI_ORG_ID`

## Key Capabilities

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| List ports | `getDeviceSwitchPorts` | All ports with VLAN, type (access/trunk), PoE, STP, tagging |
| Update port | `updateDeviceSwitchPort` | **[WRITE]** VLAN, name, type, enabled, PoE, RSTP, tags, BPDU guard |
| Port statuses | `getDeviceSwitchPortStatuses` | Live status: speed, duplex, CRC errors, traffic counters, PoE draw |
| Cycle ports | `cycleDeviceSwitchPorts` | **[WRITE]** Bounce ports for PoE reset or client reconnection |
| List VLANs | `getSwitchVlans` | Network VLANs with ID, name, subnet, appliance IP |
| Create VLAN | `createSwitchVlan` | **[WRITE]** New VLAN with ID, name, subnet, appliance IP |
| Get ACLs | `getDeviceSwitchAccessControlLists` | Access control list rules on the switch |
| Update ACLs | `updateDeviceSwitchAccessControlLists` | **[WRITE]** Modify ACL rules |
| Get QoS rules | `getDeviceSwitchQosRules` | QoS rules: VLAN, protocol, port, DSCP |
| Create QoS rule | `createDeviceSwitchQosRule` | **[WRITE]** New QoS rule for traffic prioritization |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **Access Port** | Carries a single VLAN — endpoints (PCs, phones, printers) |
| **Trunk Port** | Carries multiple VLANs (802.1Q tagged) — uplinks, AP connections |
| **BPDU Guard** | Protects against rogue switches; shuts port on BPDU receipt |
| **PoE** | Power over Ethernet — Meraki switches provide 802.3af/at/bt |
| **RSTP** | Rapid Spanning Tree Protocol — loop prevention |
| **Port Cycling** | Bounce a port to reset PoE device or force client re-auth |
| **QoS** | Quality of Service — prioritize voice/video traffic via DSCP marking |

## Workflow: Switch Port Audit

When a user asks "show me the switch ports on MS-Floor1":

1. **Find switch**: `getNetworkDevices` (meraki-network-ops) to find the switch serial
2. **List ports**: `getDeviceSwitchPorts` — all port configurations
3. **Port statuses**: `getDeviceSwitchPortStatuses` — live speed, duplex, PoE, errors
4. **Flag issues**: ports with CRC errors, PoE overload, speed mismatch, disabled
5. **VLANs**: `getSwitchVlans` — verify VLAN assignments are correct
6. **Report**: port table with status, VLAN, PoE, errors, and recommendations

## Workflow: VLAN Provisioning

When adding a new VLAN:

1. **Check existing**: `getSwitchVlans` — verify VLAN ID isn't already in use
2. **ServiceNow CR**: create change request for VLAN addition
3. **Create VLAN**: `createSwitchVlan` with ID, name, subnet, gateway
4. **Assign ports**: `updateDeviceSwitchPort` on target ports to set new VLAN
5. **Verify**: `getDeviceSwitchPortStatuses` — ports up with correct VLAN
6. **Record**: GAIT audit trail

## Workflow: Port Troubleshooting

When a user reports "device on port 24 isn't working":

1. **Port config**: `getDeviceSwitchPorts` for port 24 — VLAN, type, PoE, enabled
2. **Port status**: `getDeviceSwitchPortStatuses` — link state, speed, errors, PoE draw
3. **Client**: `getDeviceClients` — what's connected to this port?
4. **If PoE issue**: check wattage draw vs budget
5. **If link down**: `cycleDeviceSwitchPorts` to bounce the port (requires CR or emergency)
6. **ACLs**: `getDeviceSwitchAccessControlLists` — is traffic being blocked?
7. **Report**: diagnosis with fix (VLAN mismatch, PoE overload, cable issue, ACL block)

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Provides device/network context for switch operations |
| `meraki-monitoring` | Live diagnostics: cable test, ping, LED blink for switch identification |
| `pyats-topology` | Compare Meraki switch port data with pyATS CDP/LLDP for hybrid environments |
| `servicenow-change-workflow` | Gate all port changes, VLAN creation, and ACL modifications |
| `gait-session-tracking` | Record all switch operations in audit trail |

## Important Rules

- **Port changes affect connected devices** — changing VLAN or disabling a port disconnects the endpoint
- **BPDU guard** should be enabled on all access ports — flag any access port without it
- **Port cycling** is a controlled action — requires ServiceNow CR unless emergency
- **ACL changes are network-wide** — affect all ports on the switch
- **Record in GAIT** — log all switch port audits and configuration changes

## Environment Variables

- `MERAKI_API_KEY` — Meraki Dashboard API key
- `MERAKI_ORG_ID` — Meraki organization ID
