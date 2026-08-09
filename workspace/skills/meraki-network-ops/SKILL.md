---
name: meraki-network-ops
description: "Cisco Meraki organization and network operations (read-only) — org discovery, network inventory, device inventory, clients, group policies, admins, licensing, alert settings via Cisco's official Meraki MCP. Use as the entry point for any Meraki question, to discover org and network IDs, or to inventory Meraki networks and devices"
version: 2.0.0
license: Apache-2.0
tags: [cisco, meraki, organization, network, inventory, clients, discovery, read-only]
---

# Meraki Network Operations (read-only)

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

## This is the entry point

Every other Meraki skill needs an org ID and a network ID. Those come from the only two
capability IDs Cisco documents as directly callable:

```
execute_api  capability_id=getOrganizations
execute_api  capability_id=getOrganizationNetworks  organizationId=<from step 1>
```

## Verified capabilities

Live-verified against a real org:

| Capability ID | Verified result |
|---|---|
| `getOrganizations` | 1 org — id, name, licensing model, cloud region |
| `getOrganizationNetworks` | 1 network — `branch_office` (appliance, camera, switch, wireless) |
| `getOrganizationAdmins` | 2 admins |
| `getOrganizationLicensesOverview` | co-term licensing |
| `getOrganizationSaml` | SAML config |
| `getNetworkSettings` | 5 network settings |
| `getNetworkAlertsSettings` | 3 alert settings |
| `getOrganizationDevices` | **0** |
| `getOrganizationInventoryDevices` | **0** |
| `getNetworkClients` | **0** |
| `getNetworkGroupPolicies` | **0** |

Read the bottom four rows carefully. **This org has zero devices, zero inventory, zero
clients and zero group policies — while holding a fully configured four-product network
with 15 SSIDs and live firewall rules.** That is the single most important fact in this
skill: a configured network can report nothing at all.

## Workflow: Discovery

1. `getOrganizations` — record every org ID and name
2. `getOrganizationNetworks` per org — record network IDs and `productTypes`
3. `getOrganizationDevices` — the device inventory
4. **Report the counts you actually got**, including zeros, before answering anything else.
   Downstream skills need to know whether they are working from data or from an empty org.

## Workflow: Network inventory report

1. Discovery, as above
2. `getNetworkSettings` and `getNetworkAlertsSettings` per network
3. `getNetworkGroupPolicies` — policy objects, if any
4. `getOrganizationAdmins` — who can change this org
5. `getOrganizationLicensesOverview` — licence model, expiry, device entitlement
6. `productTypes` per network tells you which sibling skill applies: `wireless` →
   `meraki-wireless-ops`, `switch` → `meraki-switch-ops`, `appliance` →
   `meraki-security-appliance`

## Important Rules

- **No writes exist.** Network and org changes go through the dashboard.
- **Report zeros explicitly.** "0 devices" is a finding and must be stated, never smoothed
  over or filled in from the network's configuration.
- **`productTypes` drives which skill to hand off to** — do not run wireless workflows
  against a network without `wireless`.
- **One page only** on `getOrganizationNetworks` and `getNetworkClients` for large orgs.
- **Record in GAIT** — log every discovery run.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-wireless-ops` | Hand off networks with productType `wireless` |
| `meraki-switch-ops` | Hand off networks with productType `switch` |
| `meraki-security-appliance` | Hand off networks with productType `appliance` |
| `meraki-monitoring` | Health and change history once IDs are known |
| `gait-session-tracking` | Record all discovery runs |

## Environment Variables

- `MERAKI_DASHBOARD_API_KEY` — Meraki Dashboard API key (**read-only** recommended)
