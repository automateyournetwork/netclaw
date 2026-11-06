# Implementation Plan: R05 guarded Ollama members

**Branch**: `176-ollama-members` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

## Summary

Adapt Thermidor Spec004's proven profile, keyless guard routing, calculator-v4
prompt, compact result handling, durable provider fence and two-child workflow.
Keep NetClaw's current protected execution, existing subnet MCP component, identities,
transport, result/ACK and installed-client architecture. Qualify bounded subnet
summaries first; no new calculator product, provider framework or transport.

The owner accepted the prepared SDD package and instructed implementation on
2026-11-05, explicitly emphasizing reuse of proven Thermidor work. Execute the
tasks through source and actual qualification; preserve exact runtime/resource
review and human R05 acceptance before the next roadmap stage.

## Technical Context

**Language/Version**: Python3.12 federation/runtime; Python3.10+ host helpers;
existing Node24.19/React18 HUD, TypeScript5.9 extension and Dart3.12.2/Flutter3.44.8.

**Primary Dependencies**: existing MCP/FastMCP, SQLite, P256, Docker, OpenClaw,
DefenseClaw and native subnet MCP; pinned Ollama0.40.11/Qwen3:0.6b Q4_K_M.
No new framework or MCP server. Recheck installed artifact identity before qualification.

**Storage**: additive private combined-request/profile records and existing operation
ledger; operation-owned provider fence and evidence; bounded client references.
Private directories0700/files0600. No keys or prompt bodies in client persistence.

**Testing**: targeted Python contracts/guard/recovery tests, real-container confinement,
Node/HUD tests, TypeScript extension tests, Dart tests and actual Mac/browser/iOS
simulator evidence. Reuse named Thermidor tests in research.md as behavioral cases.

**Target Platform**: Linux ARM64 Docker on Mac for IPv4; Linux AMD64 Docker on GCP
for IPv6; current cloud Border, Mac VS Code and native iPhone simulator.

**Project Type**: additive protected execution profile and client orchestration.

**Performance Goals**: two inference turns and one native MCP invocation per success;
180s per child; local/cloud60s/120s call limits. Historical28s/150s are comparators.

**Constraints**: CPU only;2GiB model RAM;1536MiB agent RAM/no swap; local2/cloud1
model CPUs;16,384 context/1,024 output; local30s/cloud120s retention; no paid fallback.

**Scale/Scope**: one Border, two members, exactly two separately approved children,
summary calculations and one active protected operation per member. Bound parent
review to15min and each child to180s/current deployment expiry. Human review before R06/R07.

## Constitution Check

Pre-design and post-design: PASS for planning. Implementation acceptance remains open.

- I–IV/VIII: read-only calculations, real baselines before runtime changes, existing
  approval authority, GAIT and post-change verification; no device writes/ITSM changes.
- V–VII: use the existing subnet skill/native MCP and protected facade. Thermidor
  arithmetic is an independent verifier, not a bypass or second executable tool path.
- IX/X/XIII: enforce guard-only access, private artifacts, finite resources, usage
  and truthful observability; no provider secrets required by Ollama.
- XI/XII/XV: update affected protected configuration/skill/tool notes and all clients;
  retain hosted profiles and native tools. No new server means no new server count
  or catalog registration. Record any installer/catalog/environment change explicitly.
  Public README/setup/blog changes are deferred under the owner's roadmap release
  hold; a coherence disposition must name unchanged/deferred artifacts before merge.
- XIV/XVI/XVII: owner direction authorizes this SDD preparation. No external messages,
  PRs/publication, version bump or later stage. The specific roadmap publication hold
  supersedes generic milestone-blog guidance. No automatic optional loop.

## Project Structure

Documentation in `specs/176-ollama-members/`: spec, plan, research, data model,
contracts, quickstart, tasks, verification, requirements checklist and exact
`thermidor-reference.json` source hashes.

Existing integration points:

- `mcp-servers/protocol-mcp/bgp/federation/protected_contract.py`, `protected_store.py`,
  `protected_service.py`, `protected_owner.py`, `protected_device.py`: reuse child
  authority/state/ACK and expose additive combined-request capability.
- New `protected_calculator.py`: deterministic request normalization, bounded
  independent result verification and parent coordination; no direct tool execution.
- New `protected_ollama.py`: immutable model profile and current-profile validation.
- `protected_docker.py`, `protected_runtime.py`, `protected_mcp.py`: profile-specific
  container/agent limits, native IPv6 selection and compact MCP result delivery.
- `scripts/protected-guard.py`, `scripts/lib/protected_provider.py`: retain Anthropic
  route; add a narrowly selected local profile through new `scripts/lib/protected_ollama.py`
  with immutable upstream, trusted controls, per-request claims and a member/runner-wide busy/uncertain latch.
- `scripts/patches/subnet-calculator-bounded.patch` (new if corrected upstream is unavailable)
  and `scripts/lib/install-steps.sh`: reproducibly pin/fix the existing native subnet
  component before broad summary/IPv6 admission; never rely on ignored local edits.
- `scripts/protected-mcp-profile.py`, `scripts/lib/protected_role.py`: profile/source
  manifest generation and host readiness. `labs/ollama/` (new) holds adaptation-specific
  model lock, qualification/runbook and exact owned deployment/preservation receipts.
- `ui/netclaw-visual/src/hud-server/protected-operations.js`,
  `src/shared/protected-operations-client.js`, `src/dashboard/ApprovedOperationsView.jsx`:
  combined workflow and bounded references through existing protected routes.
- `extensions/netclaw-vscode/src/client/owner.ts`, `src/views/owner.ts`: G12 support.
- `mobile/netclaw-mobile/lib/cloud/owner_client.dart`,
  `lib/ncfed/protected_device_client.dart`, `lib/screens/protected_device_screen.dart`:
  G13 support through existing enrolled-device channel, retaining QR/key lifecycle.
- `tests/n2n/`, existing HUD/extension/Mobile test directories: mapped verification.

## Phase 0: Evidence and gap decisions

Research is in [research.md](research.md). Adopt the final qualified Thermidor
profile, not early failed values. Pin inspected bytes because its checkout includes
unrelated uncommitted HA changes. Preserve notices for any copied code/tests.
NetClaw's current native execution is pinned to Sonnet and canonical IPv4 `/24–/30`;
Ollama/IPv6 must be new explicit profiles, never a silent widening of historical ones.

## Phase 1: Design

[Profile/guard contract](contracts/ollama-profile.md) and
[combined-request contract](contracts/combined-request.md) freeze the trust boundaries.
Parent coordination references existing child operations, without minting a parent
execution capability. Typed two-child input is sufficient; a bounded deterministic
summary-text adapter may feed the same input, with no model-based routing.

The inspected native clone lacks IPv6 and uses unbounded IPv4 iteration. T006 first
qualifies/pins corrected native source, or applies the tracked narrow component patch,
then a new profile discovers the actual `subnet_calculator` / `subnet_calculator_v6` schema. Validate exact inputs/results,
return one compact JSON text result, and use decimal strings for exact large counts.
Retain the old tools/profiles and their original historical schemas.

Guard admission derives target, prompt, schema and reasoning settings from the
immutable signed profile. Preserve the real model/tool conversation and require
its actual generated tool call. Inspect current DefenseClaw capability before use;
Thermidor is evidence for the design, not proof the installed NetClaw build passed.
An incompatible guard marks the profile unavailable; do not widen general routing.

The existing pilot has no user login by owner direction; retain truthful open-lab
browser attribution and enrolled Mobile device principal. Do not import Thermidor's
Tailscale or owner-session model. Existing HTTPS/iN2N identity and child approvals remain.

## Phase 2: Implementation and qualification order

1. Freeze profile/contract and implement refusal tests from Thermidor.
2. Add native IPv6 selection, bounded result verifier, compact output and Ollama guard.
3. Add durable parent coordination and both client integrations against fixed contracts.
4. Qualify one local child, one cloud child, then combined browser and client flows.
5. Prove model isolation, resource bounds, child failure and no-repeat recovery.
6. Export evidence; retire disposable resources; preserve usable intended owner delivery;
   reconcile all findings and submit the human R05 gate before R06/R07.

Deploy only after a concrete owned runtime/resource packet identifies changes,
rollback, retention and existing authorization. Planning does not create that packet
or authorize changes to the retained pilot. Reuse capacity only after measured headroom;
no GPU/new VM purchase or cloud sizing assumption is required for this design.

## Cost and retention estimate

This preparation creates no cloud resources and incurs no new cloud charges. The
implementation default reuses measured spare capacity on the retained GCP host;
if sufficient, incremental VM charges are zero, while existing host/disk/IP and
transfer charges continue. Capacity must include the Thermidor4,416MiB per-project
requirement/reserve and current NetClaw overhead, measured before placement. No
claim of free compute or verified credit balance is made. T015 must document the
exact current price/retained costs, alert/expiry, owned IaC changes and cleanup;
insufficient capacity requires a separately reviewed concrete resource plan.
Preserve the existing December1 lifetime and shared budgets.

## Complexity Tracking

No new framework/server or general provider abstraction. A separate immutable Ollama
profile avoids weakening the proven Anthropic contract. The parent record is needed
because three clients must recover the same two children after a lost response.
Thermidor subdivisions, HA, Tailscale, external delegation and arbitrary models are
excluded. Actual hardware/client differences remain explicit qualification limits.
