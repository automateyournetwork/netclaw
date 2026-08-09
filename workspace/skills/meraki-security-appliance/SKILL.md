---
name: meraki-security-appliance
description: "Cisco Meraki MX security appliance (read-only) — L3/L7 firewall rules, content filtering, IDS/IPS and AMP settings, site-to-site VPN, traffic shaping via Cisco's official Meraki MCP. Use when auditing Meraki firewall rules, reviewing content filtering, or inspecting MX VPN configuration"
version: 2.0.0
license: Apache-2.0
tags: [cisco, meraki, mx, firewall, security, vpn, content-filtering, read-only]
---

# Meraki Security Appliance Operations (read-only)

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

Live-verified against a real `branch_office` network with an appliance:

| Capability ID | Verified result |
|---|---|
| `getNetworkApplianceFirewallL3FirewallRules` | L3 rules present |
| `getNetworkApplianceFirewallSettings` | firewall settings present |
| `getNetworkApplianceContentFiltering` | 3 content-filtering fields |
| `getNetworkApplianceTrafficShaping` | traffic-shaping config present |
| `getNetworkApplianceVlans` | **`Invalid parameters`** — needs appliance VLANs enabled first |

There are **74** real appliance capabilities. Also useful:
`getNetworkApplianceFirewallL7FirewallRules`,
`getNetworkApplianceFirewallCellularFirewallRules`,
`getNetworkApplianceFirewallInboundFirewallRules`, `getNetworkApplianceSecurityMalware`,
`getNetworkApplianceClientSecurityEvents`, `getNetworkApplianceVpnSiteToSiteVpn`,
`getNetworkApplianceContentFilteringCategories`. Confirm with `semantic_search`.

## Workflow: Firewall rule audit

1. `getOrganizations` → `getOrganizationNetworks` → pick the appliance network
2. `getNetworkApplianceFirewallL3FirewallRules` — the L3 rule set, in order
3. `getNetworkApplianceFirewallL7FirewallRules` — application-layer rules
4. `getNetworkApplianceFirewallSettings` — spoofing protection and defaults
5. `getNetworkApplianceContentFiltering` — blocked categories and URL patterns
6. Report the rule set **in evaluation order**. A rule list presented out of order is worse
   than no list, because first-match wins and the reader will draw the wrong conclusion.

**Rule order matters and there is a default rule you did not fetch.** Meraki applies a
final implicit rule; say so rather than implying the fetched list is exhaustive.

## Workflow: Security posture review

1. `getNetworkApplianceSecurityIntrusion` — IDS/IPS mode and ruleset
2. `getNetworkApplianceSecurityMalware` — AMP enablement
3. `getNetworkApplianceClientSecurityEvents` — observed events (**one page only**)
4. `getNetworkApplianceVpnSiteToSiteVpn` — VPN mode, hubs, exported subnets
5. Report enablement state separately from observed events. **No events is not "secure"** —
   it may mean nothing was seen, the window was short, or logging is off.

## Important Rules

- **No writes exist.** Firewall, content-filtering, IDS and VPN changes go through the
  dashboard. There is no CR to raise here because there is no write path to gate.
- **Present rules in order**, and name the implicit default.
- **Absence of security events is not evidence of security.**
- **Record in GAIT** — log every firewall and posture audit.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Network context and VLAN topology for rule interpretation |
| `meraki-switch-ops` | Trace a VLAN from firewall rule back to switch port |
| `fortinet-firewall-ops` | Compare Meraki MX policy against FortiGate policy |
| `gait-session-tracking` | Record all firewall audits |

## Environment Variables

- `MERAKI_DASHBOARD_API_KEY` — Meraki Dashboard API key (**read-only** recommended)
