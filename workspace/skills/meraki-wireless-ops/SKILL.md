---
name: meraki-wireless-ops
description: "Cisco Meraki wireless (read-only) — SSID configuration, RF profiles, Air Marshal, channel utilization, signal quality, client connectivity events via Cisco's official Meraki MCP. Use when inspecting Meraki SSIDs, auditing RF configuration, or investigating WiFi connectivity"
version: 2.0.0
license: Apache-2.0
tags: [cisco, meraki, wireless, ssid, rf, wifi, access-point, read-only]
---

# Meraki Wireless Operations (read-only)

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

Live-verified against a real Meraki org (`branch_office`, wireless + switch + appliance + camera):

| Capability ID | Verified result |
|---|---|
| `getNetworkWirelessSsids` | **15 SSIDs** — auth, VLAN, band, visibility per slot |
| `getNetworkWirelessSettings` | 9 network-level wireless settings |
| `getNetworkWirelessRfProfiles` | 2 RF profiles — band selection, power, channel width |
| `getNetworkWirelessAirMarshal` | **0 — and 0 here means "none seen in the window", not "no rogues exist"** |

Meraki always exposes **15 SSID slots** whether configured or not, so a count of 15 is the
shape of the API, not evidence of 15 live networks. Check `enabled` per SSID.

Everything else — connection stats, latency stats, channel utilization, client
connectivity events, per-device radio settings — via `semantic_search`. There are **98**
real wireless capabilities; search rather than guess.

## Workflow: Wireless configuration audit

1. `getOrganizations` → `getOrganizationNetworks` → pick the wireless network
2. `getNetworkWirelessSsids` — which slots are `enabled`, auth type, VLAN, band
3. `getNetworkWirelessRfProfiles` — power, channel width, band steering
4. `getNetworkWirelessSettings` — network-wide wireless posture
5. `getNetworkWirelessAirMarshal` — rogue/interference observations, if any
6. Report the configuration as read. Recommend changes; do not attempt them.

## Workflow: WiFi complaint triage

1. `semantic_search` "wireless client connectivity events for a client" → capability ID
2. `semantic_search` "wireless connection statistics success failure rates" → capability ID
3. Compare the client-specific view against the network-wide one — **is it this client or
   everyone?** Reporting a systemic failure as a client problem sends the operator to the
   wrong place.
4. `semantic_search` "channel utilization history" for the serving AP — congestion
5. `getNetworkWirelessSsids` — auth/VLAN/band restrictions that would exclude the client
6. Report findings, explicitly separating what was measured from what is inferred.

## Important Rules

- **No writes exist.** SSID, RF profile and radio changes must be made in the dashboard.
- **Channel utilization** over 50% is a warning, over 70% is critical — but say which AP and
  which window the number came from, or it is not actionable.
- **15 SSIDs is the API's shape**, not a finding.
- **Record in GAIT** — log every wireless assessment.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Network and device context for wireless work |
| `meraki-monitoring` | Live diagnostics and loss/latency history for APs |
| `catc-wireless-ops` | Compare Meraki wireless against Catalyst Center wireless |
| `gait-session-tracking` | Record all wireless investigations |

## Environment Variables

- `MERAKI_DASHBOARD_API_KEY` — Meraki Dashboard API key (**read-only** recommended)
