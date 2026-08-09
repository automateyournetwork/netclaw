# Implementation Plan: Cisco Meraki — official remote MCP

**Branch**: `089-meraki-official` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, `VERIFICATION.md`, `contracts/` and the git
> history. No `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096
> drift.

## Summary

Adopt Cisco's **official** remote Meraki MCP at `https://mcp.meraki.com/mcp` and retire the
registered-but-dead community server `meraki-magic-mcp`.

**The cleanest adoption in the roadmap: no server code, no dependency, no install.** Two tools reach
**494** Meraki Dashboard read operations for **~1,561 of the 5,000-token ceiling**.

## Technical Context

**Language/Version**: None authored — remote HTTP endpoint
**Primary Dependencies**: `https://mcp.meraki.com/mcp` (`network-platform-cloud-mcp` 0.11.0).
Self-host fallback exists: `CiscoDevNet/cisco-meraki-mcp-official`, Apache-2.0, active
**Storage**: None — stateless proxy
**Testing**: Live, against the operator's own Meraki sandbox key (org `DevNet-gTgBlI2IfIRS`)
**Target Platform**: Any — remote
**Project Type**: MCP integration — adopt remote, zero install
**Performance Goals**: Manifest ≤ 5,000 (achieved ~1,561)
**Constraints**: Read-only, and it must be **structurally** read-only, not advisory
**Scale/Scope**: 494 reachable capabilities behind 2 tools

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **II. Read-Before-Write** | No mutation reachable | **PASS** — verified by attempting 10 mutating verbs, all refused |
| **V. MCP-Native** | Capability as MCP server | **PASS** |
| **IX. Security by Default** | Least privilege | **PASS** — read-only sandbox key; the key appears in no repository file |
| **XI. Artifact Coherence** | All touchpoints | **PASS** — plus a **sixth reconcile surface** added (see below) |
| **XV. Backwards Compatibility** | Retiring a server must not orphan callers | **PASS** — skills migrated in the same change |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## Project Structure

```text
specs/089-meraki-official/
├── spec.md · VERIFICATION.md · contracts/
├── plan.md · research.md · tasks.md      # reconstructions

config/openclaw.json          # remote registration (url + headers); meraki-magic-mcp removed
scripts/verify-meraki-ids.py  # the sixth surface
```

**Structure Decision**: Remote registration — no vendored tree, no install step beyond credentials.
The self-host fallback is recorded but not used: adopting the remote endpoint costs nothing and the
fallback is Apache-2.0 if Cisco ever withdraws it.

## Read-only is structural, and that had to be proven

The server's `instructions` ask the model to refuse writes. **That alone is worthless** — it is a
prompt-level request, and NetClaw does not treat model compliance as a control.

It is genuinely enforced: 10 mutating verbs spanning every shape (`updateNetwork`, `createNetwork`,
`deleteNetwork`, `rebootDevice`, `blinkDeviceLeds`, `claimIntoOrganization`, …) all returned
`Capability not found`. `semantic_search` asked directly for *"update or change firewall rules and
reboot a device"* returned five capabilities, **all `get*`**. The mechanism is confirmed in the
source: `providers/openapi.py` collects **non-deprecated GET operations only**.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a recurrence gate |
| **A sixth reconcile surface added mid-feature** | The audit found **54 of 80 method names** the old Meraki skills documented **did not exist** in the Meraki API — documentation drifted into fiction with nothing checking it | Fixing the 54 without a gate would leave the next drift undetected. The surface is cheap and mechanical |
