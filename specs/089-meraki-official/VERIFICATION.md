# Spec 089 — Verification

**Date**: 2026-08-04
**Endpoint**: `https://mcp.meraki.com/mcp` — `network-platform-cloud-mcp` 0.11.0
**Credential**: operator's own read-only Meraki Dashboard key, DevNet sandbox org
`DevNet-gTgBlI2IfIRS`. **The key appears in no file in this repository** — verified with a
direct (unpiped) grep across the tree.

Everything here was measured live. Nothing is quoted from Cisco's documentation.

## Manifest cost — the ceiling check

| Component | Tokens |
|---|---|
| `semantic_search` schema | ~739 |
| `execute_api` schema | ~617 |
| Tool manifest subtotal | ~1,357 |
| `instructions` payload | ~204 (818 chars) |
| **Total against the 5,000 ceiling** | **~1,561** |

`instructions` is counted deliberately. R10 (ntopng) was deferred partly because a
5,338-token `instructions` payload blew the ceiling once counted; a manifest measurement
that ignores it is wrong.

## Read-only is structural, not advisory — 10/10 confirmed

The server's `instructions` ask the model to refuse writes. That alone is not a control.
Ten mutating verbs, spanning every shape, were attempted live:

| Attempted | Result |
|---|---|
| `updateNetwork` | `Capability not found` |
| `createNetwork` | `Capability not found` |
| `deleteNetwork` | `Capability not found` |
| `rebootDevice` | `Capability not found` |
| `updateOrganization` | `Capability not found` |
| `createOrganization` | `Capability not found` |
| `blinkDeviceLeds` | `Capability not found` |
| `claimIntoOrganization` | `Capability not found` |
| `updateNetworkApplianceFirewallL3FirewallRules` | `Capability not found` |
| `removeNetworkDevices` | `Capability not found` |

`semantic_search` asked for *"update or change firewall rules and reboot a device"* returned
5 capabilities, **all `get*`**.

The `updateNetwork` attempt used a nonexistent network ID (`N_000000000000000000`) so that
nothing could have been mutated even if the call had been accepted.

**Mechanism, from `providers/openapi.py`:** `collect_get_operations()` skips
`path_item.get is None or path_item.get.deprecated`. Only non-deprecated GETs are built into
the catalogue.

## Catalogue arithmetic, from the bundled spec

Meraki Dashboard API **1.70.0**, bundled at `cisco_meraki_mcp/specs/meraki.json.gz`:

| | Count |
|---|---|
| Total operations | 933 |
| GET | 502 |
| — non-deprecated (**the live catalogue**) | **494** |
| — deprecated, filtered out | 8 |
| POST / PUT / DELETE (**structurally absent**) | 431 (174 / 186 / 71) |

**Prediction then confirmation:** `getOrganizationDevicesStatuses` returned
`Capability not found` live despite being present in the spec. Predicted cause: the
deprecated filter. Confirmed by checking the spec's `deprecated` flag — it is one of the 8.

## Live data on the sandbox

Org `669910444571369279`, network `branch_office` (appliance, camera, switch, wireless).

| Capability | Result |
|---|---|
| `getOrganizations` | 1 org, co-term licensing |
| `getOrganizationNetworks` | 1 network |
| `getNetworkWirelessSsids` | **15** |
| `getNetworkWirelessSettings` | 9 |
| `getNetworkWirelessRfProfiles` | 2 |
| `getNetworkSwitchAccessControlLists` | 1 |
| `getNetworkApplianceFirewallL3FirewallRules` | present |
| `getNetworkApplianceFirewallSettings` | present |
| `getNetworkApplianceContentFiltering` | 3 |
| `getNetworkApplianceTrafficShaping` | present |
| `getNetworkSettings` | 5 |
| `getNetworkAlertsSettings` | 3 |
| `getOrganizationAdmins` | 2 |
| `getOrganizationConfigurationChanges` | 3 |
| `getOrganizationLicensesOverview`, `getOrganizationSaml` | present |
| `getNetworkWirelessAirMarshal` | **0** |
| `getOrganizationDevices` | **0** |
| `getOrganizationInventoryDevices` | **0** |
| `getNetworkClients` | **0** |
| `getNetworkGroupPolicies` | **0** |

**The FR-006 hazard, reproduced live**: this org reports **0 devices, 0 inventory, 0 clients,
0 group policies** while holding a fully configured four-product network with 15 SSIDs and
live firewall rules. A configured network can report nothing at all. Every skill states this.

### Three distinguishable error classes

Found by hitting all three, and each needs a different fix — so the skills document all three
rather than collapsing them into "no data":

| Error | Trigger observed | Meaning |
|---|---|---|
| `Capability not found` | `updateNetwork`, `getOrganizationDevicesStatuses` | mutating, deprecated, or invented ID |
| `Resource not found` | a network ID I guessed wrong | valid ID, wrong resource |
| `Invalid parameters` | `getNetworkApplianceVlans`, `getNetworkEvents`, `getNetworkApplianceSecurityIntrusion` | valid ID, missing required parameter |

The `Resource not found` row is from my own mistake: I hardcoded a guessed network ID and got
10 consecutive failures before re-deriving it from `getOrganizationNetworks`. That is exactly
the failure the skills' "discover, do not guess" rule prevents.

## The largest finding: 54 documented calls did not exist

The five pre-existing Meraki skills cited **80** method names. Measured against the spec:

| | Count |
|---|---|
| Real, reachable GET capabilities | 14 |
| Real but mutating (unreachable) | 12 |
| **Did not exist in the Meraki API at all** | **54** |

**85% of the documented calls were fiction** — `getWirelessSSIDs`, `getDeviceStatus`,
`getNetworks`, `getNetworkSecurityFirewallRules` and 50 more. They would have failed against
the community server too. Nothing in the repository detected this for as long as those skills
have existed, because `verify-inventory-counts.py` checks that counts agree; it never asks
whether a documented call is real.

### The permanent guard

`scripts/check-meraki-capability-ids.py`, wired in as reconcile's **sixth** surface,
validates skill text against 494/8/431 vendored operation IDs extracted from Cisco's own
bundled spec (`contracts/meraki-capability-ids.json`, 39 KB, offline).

Proof it is not vacuous — run against the **old** skills from git:

```
Meraki capability-ID check: FAIL (129)
  103 findings of the form "DOES NOT EXIST in Meraki Dashboard API 1.70.0"
```

Against the rewritten skills: **PASS**.

It deliberately allows a mutating or deprecated ID when the line marks it unreachable —
the shared skill section teaches that `updateNetwork` returns `Capability not found`, and
flagging that would push authors toward vaguer documentation than the problem being solved.

## Reconciliation

Six surfaces. `startup` findings dropped **7 → 6** when `meraki-magic-mcp` was unregistered,
which is FR-008 satisfied and spec 088's surface working as a regression detector.

```
Reconciliation: PASS (with warnings)
  catalog      pass   installer coverage and vendored state
  dependencies pass   dependency pins and install paths
  docs         pass   documented counts
  meraki-ids   pass   Meraki capability IDs cited in skills
  portability  pass   registration portability
  startup      WARN   registered servers can actually start   (6, was 7)
```

## Tests

`tests/reconcile/run-tests.sh` — **42 assertions, 0 failures** (32 before this spec, 10 new).
New coverage: a real ID passes; an invented ID fails and is named; an unmarked mutating ID
fails; the same ID marked unreachable passes; an unmarked deprecated ID fails and is
distinguished from nonexistent; `--warn-only`; and the shipped skills are clean.

## Not verified, and why

**Devices, telemetry, and live tools are unverifiable on this sandbox** — it has 0 devices.
Capabilities for device status, uplink loss/latency, availability, throughput, camera
analytics and live-tool results are reachable by adoption but were **not exercised against
real hardware**. The skills cite them as `semantic_search` targets rather than as verified
results, and this spec does not claim they work.

## Documentation corrected

Nine claims were wrong and are fixed: `catalog.sh` and four README locations claimed
"~804 endpoints" (a community-README figure with no basis in the 933-operation spec);
README described the integration with the write verb "**Manage**" and advertised "network
CRUD" and "device lifecycle (claim, unclaim, reboot)"; `SOUL-SKILLS.md` documented
`READ_ONLY_MODE=true` as the way to block writes, which is now structurally moot;
`.env.example` and `setup.sh` prompted for `MERAKI_API_KEY`/`MERAKI_ORG_ID` plus a read-only
toggle, replaced by a single `MERAKI_DASHBOARD_API_KEY` (org IDs are discovered at runtime).
