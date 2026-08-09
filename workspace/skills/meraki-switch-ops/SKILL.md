---
name: meraki-switch-ops
description: "Cisco Meraki switching (read-only) — port configuration and status, VLANs, ACLs, QoS, STP, link aggregation, routing interfaces via Cisco's official Meraki MCP. Use when inspecting Meraki switch ports, auditing switch ACLs, or investigating port errors"
version: 2.0.0
license: Apache-2.0
tags: [cisco, meraki, switch, port, vlan, acl, qos, stp, read-only]
---

# Meraki Switch Operations (read-only)

## MCP Server

- **Server**: Cisco's **official** Meraki MCP — [developer.cisco.com](https://developer.cisco.com/meraki/api-v1/mcp-server/)
- **Endpoint**: `https://mcp.meraki.com/mcp` (remote HTTP, no local install)
- **Self-host fallback**: [CiscoDevNet/cisco-meraki-mcp-official](https://github.com/CiscoDevNet/cisco-meraki-mcp-official) (Apache-2.0)
- **Requires**: `MERAKI_DASHBOARD_API_KEY` — use a **read-only** dashboard key
- **Tools**: exactly two — `semantic_search` (discover) and `execute_api` (invoke)

## Read-only, structurally

All 431 mutating Meraki operations (174 POST, 186 PUT, 71 DELETE) are **absent from the
capability catalogue**. Only non-deprecated GETs are built in, so `updateNetwork`,
`rebootDevice`, `blinkDeviceLeds` and friends return `Capability not found`.

Do not attempt writes and do not offer them. There is no ServiceNow CR path here because
there is nothing to gate — a change must be made in the Meraki dashboard directly.

## How to call it

Two capability IDs may be called directly; everything else must be discovered:

1. `execute_api` → `getOrganizations` — find accessible org IDs
2. `execute_api` → `getOrganizationNetworks` — find network IDs in the chosen org
3. `semantic_search` → describe the intent in words → returns ranked `capability_id`s
4. `execute_api` → the chosen `capability_id` + its required parameters

**Discover, do not guess.** An earlier version of this skill hardcoded 80 method names and
**54 of them did not exist in the Meraki API at all** — they failed regardless of server.
`semantic_search` is the guard against that: it can only return IDs that exist.

## Reading results honestly

- **One page only.** `execute_api` returns a single page. Request a bounded page size when
  supported, and never present a page as the complete dataset.
- **Empty is not absent.** `n=0` means *this network reported none*, never *none exist*.
  Live proof from a real sandbox org: `getOrganizationDevices` returns **0 devices** while
  the same org has a fully configured network with **15 SSIDs**.
- **Three distinct errors, three different fixes:**

  | Error | Meaning | Fix |
  |---|---|---|
  | `Capability not found` | ID is mutating, deprecated, or invented | `semantic_search` for a real one |
  | `Resource not found` | valid ID, wrong org/network/serial | re-derive the ID from step 1–2 |
  | `Invalid parameters` | valid ID, missing a required parameter | read the capability's parameters |

  Never report any of the three as "no data" — none of them mean that.

## Verified capabilities

| Capability ID | Verified result |
|---|---|
| `getNetworkSwitchAccessControlLists` | 1 ACL set on a real network |

There are **50** real switch capabilities. The ones you will reach for most:
`getDeviceSwitchPorts`, `getDeviceSwitchPortsStatuses`, `getDeviceSwitchPortsStatusesPackets`,
`getNetworkSwitchAccessPolicies`, `getNetworkSwitchRoutingMulticast`,
`getDeviceSwitchRoutingInterfaces`, `getDeviceSwitchRoutingStaticRoutes`,
`getDeviceSwitchWarmSpare`. Confirm each with `semantic_search` before calling.

**Port capabilities are per-device and need a `serial`**, not a network ID. Get serials from
`getOrganizationDevices` (org-wide) — and note that an org with **0 devices returns 0
serials**, which is not the same as "the switches have no ports".

## Workflow: Port configuration audit

1. `getOrganizations` → `getOrganizationNetworks` → `getOrganizationDevices`
2. If 0 devices: **stop and say so.** Do not proceed to invent port data.
3. Per switch serial: `getDeviceSwitchPorts` — VLAN, type, PoE, STP guard, isolation
4. `getDeviceSwitchPortsStatuses` — link state, speed, duplex, errors, discards
5. `getNetworkSwitchAccessControlLists` and `getNetworkSwitchAccessPolicies` — ACL/802.1X
6. Report per-port configuration drift against intent

## Workflow: Port error investigation

1. `getDeviceSwitchPortsStatuses` — identify ports with errors or discards
2. `getDeviceSwitchPortsStatusesPackets` — packet-level breakdown per port
3. `semantic_search` "switch port cable test results" — physical-layer evidence
4. Correlate with `getDeviceLossAndLatencyHistory` via `meraki-monitoring`
5. Distinguish **errors** (physical/duplex) from **discards** (congestion/QoS) — they have
   different fixes, and conflating them is the usual wrong answer here.

## Important Rules

- **No writes exist.** Port, VLAN, ACL and QoS changes must be made in the dashboard.
- **Port capabilities need a device serial**, not a network ID.
- **Errors ≠ discards.** Say which, with counts and the window.
- **Record in GAIT** — log every switch audit.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Network and device inventory for switch discovery |
| `meraki-monitoring` | Loss/latency history and live tools for switch uplinks |
| `meraki-security-appliance` | Trace a VLAN from switch port to firewall rule |
| `gait-session-tracking` | Record all switch audits |

## Environment Variables

- `MERAKI_DASHBOARD_API_KEY` — Meraki Dashboard API key (**read-only** recommended)
