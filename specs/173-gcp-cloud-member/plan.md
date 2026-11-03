# Implementation Plan: R04 GCP NetClaw cloud member

**Branch**: `173-gcp-cloud-member` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

## Summary

Extend the existing protected member to invoke installed NetBox and subnet MCPs
with reviewed skill context. Reuse R03 control-only Border/owner HUD in a fresh
GCP deployment. A separate member VM/subnet uses guarded Sonnet4.6. Qualify three
exact workloads, isolation and recovery; export evidence and retire all resources.
The supplied demo source replaces a seeded NetBox server.

## Technical Context

**Language/Version**: Python3.12 federation/MCP; Python3.10+ host helpers; existing Node24.19/React18 HUD.
**Primary Dependencies**: Existing FastMCP/MCP, requests, P256, SQLite, Docker, OpenClaw2026.7.1-2, strict iN2N, OpenTofu1.13.2/Google8.9.0, Caddy2.11.7. Existing NetBox/subnet MCPs; no new server/framework.
**Storage**: Private SQLite/GAIT and immutable profiles; external0700 state/evidence and0600 secrets; bounded browser identifiers only.
**Testing**: Python/Node suites, actual installed MCP/native Linux isolation, trusted-HTTPS browser approval, cloud inspection and independent evidence verification.
**Target Platform**: GCP Ubuntu24.04 AMD64 Border/OpenClaw member; preserve Mac/OpenClaw/Hermes behavior.
**Project Type**: Existing protected federation/HUD and maintainer cloud tooling.
**Performance Goals**: One MCP effect and at most two guarded provider calls per operation; existing finite deadlines and max32 retained references; no hidden retries.
**Constraints**: Broker-only NetBox token; guard-only provider key; no public member listener; <=48h activation with finite traffic/resources and prompt cleanup; preserve R01; release hold.
**Scale/Scope**: One fresh Border/member, one owner, device/prefix/subnet workloads.

## Constitution Check

Pre/post-design pass: user-delegated spec precedes implementation; existing skill/MCP,
GAIT and exact approval boundaries retained. Read-only demo workloads require no
device configuration or production CR. No ticket or external communication. Private
secrets never enter source/Border/model. Uncertainty stays spent. Actual observations
precede qualification; Mac/Thermidor history cannot qualify native Linux. Additive
contracts and regressions preserve existing integrations.

Owner release hold overrides generic version/public README/blog/publication steps;
maintainer technical evidence and deferred documentation only. Current R04 delegation
covers finite resource/runtime changes; exact plans, receipts and cleanup remain.
Human acceptance remains required before R05. No constitutional waiver.

## Project Structure

- `mcp-servers/protocol-mcp/bgp/federation/protected_{contract,runtime,docker,selection}.py`: explicit tools, immutable MCP/skill profiles and execution.
- `scripts/protected-{inference,tool-broker,guard}.py`: existing adapters, additive native Linux local transport.
- `scripts/lib/`, `scripts/lib/install-steps.sh`: reproducible existing NetBox compatibility; never only patch an ignored checkout.
- `workspace/skills/netbox-reconcile/SKILL.md`: observed singular object types and scoped read guidance.
- `scripts/lib/protected_role.py`: additive member role, preserve Border contract.
- `labs/cloud/gcp/r04/`: fresh IaC/host/secret/network/teardown tooling.
- `ui/netclaw-visual/src/dashboard/RetainedOperationsView.jsx`, shared protected-reference helper/tests: full selection identity and typed verified evidence.
- `specs/173-gcp-cloud-member/`: technical artifacts; raw evidence outside Git.

## Design and lanes

Pass4 of five authorized bounded passes. Broker lane owns protocol/adapters/MCP
compatibility/skill; cloud lane owns member role/R04 IaC/host; HUD lane owns
selection/results/tests. Separate worktrees. Coordinator integrates and drives
actual qualification/cleanup. No automatic Ralph loop.

Permit only actual `netbox_get_object_by_id` for observed `dcim.device` or
`ipam.prefix` IDs, and existing `subnet_calculator` for established IPv4 /24–/30.
A separately bounded MCP readiness read discovers records/schema; actual operation
approval binds observed IDs/hashes. Local profile/code/schema/endpoint drift refuses before effects. Remote changed/missing
records consume the one authorized read and retain its changed/failure result;
never retry, replay or substitute.
Load and hash existing reviewed skill context with explicit R04 read-only constraints.
Pin MCP source/schema/dependencies, credential-free origin and exact selections.

Broker-owned MCP child alone gets NetBox credential. Agent gets operation-local
facade capability; guard alone gets provider key. Native Linux uses an owned
operation-scoped Unix socket for relay-to-broker, retaining explicit Mac TCP.
No extra public broker. Existing Sonnet4.6 avoids inventing Haiku qualification.

Explicit member role has outbound direct iN2N, no HUD origin/public workload listener,
separate service identity/secret access, immutable closures and private owned state.
Host guard must account for Docker FORWARD as well as OUTPUT, reject unknown links,
recognize only reviewed bridges and deny metadata from untrusted containers.

## Resource and cost bounds

Planning sizes: e2-small Border20GiB/address and e2-standard-2 member40GiB/address.
Agent4GiB+guard768MiB+relay128MiB requires an8GiB member host. Dedicated VPC/separate
/28 subnets, identities, firewalls, exact-version secrets, verified budget alert and HTTPS DNS. IAP admin;
Border iN2N only from reviewed member source; no member inbound service rule.

Historical authenticated November2 CAD rates imply CAD7.14 base for48h or
CAD110.62 for744h continuous operation, excluding R01/traffic/tax/secrets/model.
This is not a current quote/invoice or continuous CAD100/month compliance. Refresh
pricing for exact packet; include R01 exposure, finite duration/traffic/provider
bounds, actual billing visibility and prompt teardown. Alerts are not hard caps;
credit is not a verified balance or spending target.

## Qualification sequence

1. Coherent spec/plan/tasks; implement lanes, integrate and run regressions.
2. Actual existing MCP schemas/source readiness; bind exact objects/calculator.
3. Fresh saved IaC/runtime/DNS plans, finite bounds and preservation manifests.
4. Apply once; exact source/secrets, role activation and outbound enrollment.
5. Three trusted-HTTPS owner approvals; actual skill/MCP/model evidence, signed
   results/ACKs and independent source/arithmetic comparisons.
6. Negative scope/credential/network cases; member stop/restart with unchanged
   effect counts; independent evidence review.
7. Export private state/evidence, exact teardown and zero-residue/R01 checks;
   report limitations and obtain owner acceptance before R05.

## Complexity Tracking

No new framework/server/authority model. A distinct member role and native Linux
local transport are necessary because R03 only qualified cloud coordination with
Mac execution. Direct REST replacement or same-VM deployment fails requested scope.
