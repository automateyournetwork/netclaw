# Spec 089 — Cisco Meraki, official MCP (adopt remote, retire dead community server)

**Status**: implemented
**Branch**: `089-meraki-official`
**Date**: 2026-08-04
**Roadmap**: second of the two Cisco items requested alongside [087](../087-catalyst-center-official/spec.md)

## Summary

Adopt Cisco's **official** Meraki MCP server at the remote endpoint `https://mcp.meraki.com/mcp`,
and retire the registered-but-dead community server `meraki-magic-mcp`.

This is the cleanest adoption in the roadmap so far: **no server code, no dependency, no install.**
Two tools reach 494 Meraki Dashboard API read operations, and the whole thing costs
**~1,561 of the 5,000-token manifest ceiling.**

Everything below was measured against the live endpoint with the operator's own sandbox key, not
read from documentation.

## What was measured

`initialize` returns `network-platform-cloud-mcp` **0.11.0**.

| Measurement | Value |
|---|---|
| Tools | **2** — `semantic_search`, `execute_api` |
| Tool manifest | ~1,357 tokens |
| `instructions` payload | ~204 tokens (818 chars) |
| **Total against the 5,000 ceiling** | **~1,561** |
| Reachable capabilities | **494** non-deprecated GET operations |
| Mutating operations reachable | **0** |
| Install footprint | none — remote HTTP |
| Self-host fallback | `CiscoDevNet/cisco-meraki-mcp-official`, **Apache-2.0**, active (pushed 2026-07-28) |

The `instructions` payload is counted deliberately. R10 (ntopng) was deferred partly because its
community server's 5,338-token `instructions` blew the ceiling once counted — a manifest measurement
that ignores `instructions` is wrong.

### Read-only is structural, not advisory

The server's `instructions` say "Only perform read operations. Deny requests for create, update,
delete, reboot…". **That alone would be worthless** — it is a prompt-level request to the model, and
NetClaw does not treat model compliance as a control.

It is genuinely enforced. Ten mutating verbs across every shape were attempted live:

```
updateNetwork  createNetwork  deleteNetwork  rebootDevice  updateOrganization
createOrganization  blinkDeviceLeds  claimIntoOrganization
updateNetworkApplianceFirewallL3FirewallRules  removeNetworkDevices
```

All ten returned `Capability not found`. `semantic_search` asked directly for
*"update or change firewall rules and reboot a device"* returned five capabilities, **all `get*`**.

The source confirms the mechanism — `providers/openapi.py`:

```python
def collect_get_operations(...):
    """Collect non-deprecated GET operations from an OpenAPI paths mapping."""
    if path_item.get is None or path_item.get.deprecated:
        continue
```

Only non-deprecated GETs are ever built into the catalogue. Of the bundled Meraki Dashboard API
**1.70.0** spec's 933 operations, **431 mutating ones (174 POST, 186 PUT, 71 DELETE) do not exist as
capabilities at all**, and 8 deprecated GETs are filtered out — which is exactly why
`getOrganizationDevicesStatuses` returned `Capability not found` live despite being present in the
spec. Predicted from the code, then confirmed against the spec's `deprecated` flag.

This matters for Principle III (ITSM-gated writes): there is no write path to gate, because there is
no write path.

### Contrast with 087

Spec 087 faced the same problem — a huge read-only API behind a hard tool ceiling — and solved it by
building a NetClaw client with 8 group dispatchers over a vendored 514-operation catalogue. Cisco
solved it here with `semantic_search` + `execute_api`. Both land ~1,500–1,800 tokens. The difference
is that **this one required writing nothing**, so it is adopted rather than built.

## Why the community server is retired, not repaired

`meraki-magic-mcp` is registered in `config/openclaw.json` pointing at
`mcp-servers/meraki-magic-mcp-community/meraki-mcp-dynamic.py`, and **it cannot start** — missing the
`meraki` SDK (one of the seven found by spec 088). Five skills route to it.

| | community (registered, dead) | Cisco official |
|---|---|---|
| Tools | 22 | 2 |
| Reachable operations | 22 hand-written | 494 |
| Writes | **yes** — `updateDeviceSwitchPort` | structurally impossible |
| Install | needs `meraki` SDK, blocked by PEP 668 on this host | none |
| Status | cannot start | live-verified |
| License | community | Apache-2.0 |

The official server dominates on every axis. Note the write capability is **not** a real loss: the
server has been unable to start, so no operator has had that capability.

## Requirements

- **FR-001** Register the official remote server in `config/openclaw.json` with Bearer auth sourced
  from `MERAKI_DASHBOARD_API_KEY`. No key in any committed file.
- **FR-002** Unregister `meraki-magic-mcp`. Remove its catalog entry and installer step.
- **FR-003** Rewire the 5 skills routing to it: `meraki-monitoring`, `meraki-network-ops`,
  `meraki-security-appliance`, `meraki-switch-ops`, `meraki-wireless-ops`.
- **FR-004** Skills MUST use the documented discovery order from the server's own `instructions`:
  `execute_api` directly with `getOrganizations`, then `getOrganizationNetworks`, and
  `semantic_search` for everything else. Guessing capability IDs wastes a round trip on
  `Capability not found`.
- **FR-005 (pagination)** `execute_api` returns **one page only**. A skill MUST NOT present a page
  as the complete dataset. This is NetClaw's recurring distinction and Cisco states it in their own
  `instructions` — honour it rather than restating it.
- **FR-006 (empty ≠ absent)** A `0`-length result means *this org/network reported none*, never
  *none exist*. The operator's own sandbox proves the hazard: `getOrganizationDevices` and
  `getOrganizationInventoryDevices` both return **0 items** while the org holds a fully configured
  `branch_office` network with 15 SSIDs.
- **FR-007** Register `mcp.meraki.com` with DefenseClaw as an outbound provider. **Unregistered
  domains are silently 403'd**, which has already cost this project a full day twice on Slack.
- **FR-008** Reconciliation must pass, including spec 088's `startup` surface, and retiring
  `meraki-magic-mcp` must reduce that surface's findings from 7 to 6.
- **FR-009** Document the self-host fallback (Apache-2.0) without implementing it, so an operator who
  cannot send an API key to a Cisco-hosted endpoint has a stated path.
- **FR-010 (added during implementation)** The five skills cited **80** method names of
  which **54 do not exist in the Meraki API at all** and 12 are mutating. They would have
  failed against any server. Skills MUST cite only real, reachable capability IDs, and a
  permanent check MUST validate that against Cisco's own spec rather than against prose.
  This was not in the original draft — it was found by validating the skills' own text.

## Scope limits, stated honestly

**Devices and live telemetry cannot be verified on this sandbox.** `DevNet-gTgBlI2IfIRS` holds
**0 devices and 0 inventory**. Any device-status, uptime, loss/latency, or client-traffic capability
is therefore *implemented-by-adoption but unverified* — and this spec will say so rather than imply
coverage. What **is** live-verifiable:

| Capability | Result on the sandbox |
|---|---|
| `getOrganizations` | 1 org, co-term licensing |
| `getOrganizationNetworks` | 1 — `branch_office` (appliance, camera, switch, wireless) |
| `getNetworkWirelessSsids` | **15 SSIDs** |
| `getNetworkApplianceFirewallL3FirewallRules` | rules present |
| `getNetworkApplianceFirewallSettings`, `getNetworkSettings`, `getNetworkAlertsSettings` | present |
| `getOrganizationAdmins` | 2 |
| `getOrganizationConfigurationChanges` | 3 |
| `getOrganizationLicensesOverview`, `getOrganizationSaml` | present |
| `getOrganizationDevices`, `getOrganizationInventoryDevices`, `getNetworkClients`, `getNetworkGroupPolicies` | **0 — the FR-006 hazard, live** |

## Out of scope

- Writes (structurally impossible upstream).
- Self-hosting the Apache-2.0 server (documented, not implemented).
- The other six startup failures — the next spec, per the operator's sequencing.
- Verifying device/telemetry capabilities, which needs hardware this sandbox does not have.
