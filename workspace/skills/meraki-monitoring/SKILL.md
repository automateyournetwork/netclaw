---
name: meraki-monitoring
description: "Cisco Meraki monitoring and diagnostics (read-only) — device availability, loss and latency history, uplink status, live tool results, configuration change log, API request analytics via Cisco's official Meraki MCP. Use when checking Meraki device health, investigating uplink loss, or reviewing recent configuration changes"
version: 2.0.0
license: Apache-2.0
tags: [cisco, meraki, monitoring, diagnostics, uplink, latency, availability, read-only]
---

# Meraki Monitoring & Diagnostics (read-only)

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

Live-verified against a real org:

| Capability ID | Verified result |
|---|---|
| `getOrganizationConfigurationChanges` | 3 change records |
| `getOrganizationApiRequestsOverview` | API request analytics present |
| `getOrganizationLicensesOverview` | licensing (co-term) present |
| `getOrganizationDevices` | **0 devices** |
| `getOrganizationInventoryDevices` | **0 inventory** |
| `getOrganizationDevicesStatuses` | **`Capability not found` — deprecated upstream** |

That last row matters: **8 deprecated GETs are filtered out of the catalogue.** A
`Capability not found` on a name you remember working means it was deprecated, not that the
data is gone — `semantic_search` for the current equivalent.

There are **56** real monitoring capabilities, including `getDeviceLossAndLatencyHistory`,
`getOrganizationDevicesAvailabilities`, `getOrganizationDevicesUplinksLossAndLatency`,
`getDeviceLiveToolsPing`, `getDeviceLiveToolsCableTest`, `getDeviceLiveToolsArpTable`,
`getDeviceLiveToolsMacTable`, `getDeviceLiveToolsThroughputTest`.

**Live tools are GET-only here — you can read results, not start runs.** Starting a live
tool is a POST, which does not exist in this catalogue. Read existing results, or start the
run from the dashboard.

## Workflow: Org health check

1. `getOrganizations` → `getOrganizationNetworks`
2. `getOrganizationDevices` — **if 0, report "no devices reported by this org" and stop.**
   Do not present an empty inventory as a healthy one.
3. `semantic_search` "device availability across the organization" → invoke it
4. `semantic_search` "uplink loss and latency across the organization" → invoke it
5. `getOrganizationLicensesOverview` — licence state and expiry
6. Report health with the observation window stated. A latency number without a window is
   not a measurement.

## Workflow: Change correlation

When something broke and nobody knows why:

1. `getOrganizationConfigurationChanges` — who changed what, when (**one page only**)
2. Correlate timestamps against the reported onset of the problem
3. `getOrganizationApiRequestsOverview` — was the change made by an integration, not a human?
4. Report the correlation as **correlation**. A config change near an outage is a lead, not
   a cause, and saying otherwise has sent operators down the wrong path before.

## Important Rules

- **No writes and no run-starting.** Live tools are readable, not startable.
- **0 devices ≠ healthy.** Say the org reported none.
- **`Capability not found` on a familiar name means deprecated** — search for the successor.
- **Always state the observation window** for any loss, latency, or availability figure.
- **Record in GAIT** — log every health check.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Network and device context for health checks |
| `meraki-switch-ops` | Port-level errors behind an uplink problem |
| `servicenow-change-workflow` | Correlate Meraki config changes against CRs |
| `slack-network-alerts` | Report degradation to the operator channel |
| `gait-session-tracking` | Record all health checks |

## Environment Variables

- `MERAKI_DASHBOARD_API_KEY` — Meraki Dashboard API key (**read-only** recommended)
