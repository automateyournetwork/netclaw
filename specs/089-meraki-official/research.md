# Phase 0 Research — Cisco Meraki official MCP (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md`, `VERIFICATION.md` and `contracts/`.
> Everything was measured live against the endpoint with the operator's own sandbox key — nothing
> here is quoted from Cisco documentation.

---

## R1 — Adopt remote, self-host, or keep the community server?

**Decision**: Adopt the remote endpoint.

| Option | Verdict |
|---|---|
| **`https://mcp.meraki.com/mcp` (official, remote)** | **chosen** — zero install, zero dependency, 2 tools / ~1,561 tokens |
| `CiscoDevNet/cisco-meraki-mcp-official` (self-host) | **recorded as fallback** — Apache-2.0, active (pushed 2026-07-28). Not needed while the remote endpoint exists |
| `meraki-magic-mcp` (community, installed) | **retired** — could not start at all (missing `meraki` SDK), one of spec 088's seven |

---

## R2 — Manifest cost

**Decision**: Passes comfortably.

| Component | Tokens |
|---|---|
| `semantic_search` | ~739 |
| `execute_api` | ~617 |
| Tool manifest | ~1,357 |
| `instructions` (818 chars) | ~204 |
| **Total vs 5,000** | **~1,561** |

`instructions` is counted deliberately. R10 (ntopng) was deferred partly because a 5,338-token
`instructions` payload blew the ceiling once counted — **a manifest measurement that ignores
`instructions` is wrong.**

---

## R3 — Is read-only real, or just asked for?

**Decision**: Real, and structural.

The `instructions` say *"Only perform read operations. Deny requests for create, update, delete,
reboot…"*. That is a prompt-level request to the model and would be worthless on its own.

Ten mutating verbs were attempted live — `updateNetwork`, `createNetwork`, `deleteNetwork`,
`rebootDevice`, `updateOrganization`, `createOrganization`, `blinkDeviceLeds`,
`claimIntoOrganization`, `updateNetworkApplianceFirewallL3FirewallRules`, `removeNetworkDevices`.
**All ten returned `Capability not found`.**

`semantic_search` asked directly for *"update or change firewall rules and reboot a device"*
returned five capabilities, **all `get*`**.

Mechanism confirmed in source — `providers/openapi.py`:
`collect_get_operations(...)` — *"Collect non-deprecated GET operations from an OpenAPI paths
mapping."* 431 mutating operations are simply absent from the catalogue.

**Reachable: 494 non-deprecated GET operations. Mutating: 0.**

---

## R4 — The finding that outgrew the feature

**Decision**: Add a sixth reconcile surface.

Auditing the existing Meraki skills against the live capability catalogue found that **54 of the 80
method names those skills documented did not exist** in the Meraki API. The documentation had
drifted into fiction, and nothing in the repository could detect it.

Same meta-pattern spec 088 recorded: **a check that validates declarations against each other cannot
detect a declaration that is uniformly wrong.**

Remedy: `verify-meraki-ids.py`, a sixth reconcile surface that checks every Meraki capability ID
cited in a skill actually exists.

---

## R5 — Credential handling

**Decision**: Read-only sandbox key, held only in `~/.openclaw/.env`.

Verified with a direct (unpiped) grep that the key appears in **no file in the repository**.

---

## R6 — Effect on spec 088's findings

Retiring `meraki-magic-mcp` takes 088's startup findings from **7 → 6**. The remaining six are
addressed by [spec 090](../090-fix-dead-servers/spec.md), which promotes the `startup` surface to a
hard gate.
