# Implementation Plan: R03 GCP hybrid Border

**Branch**: `172-gcp-hybrid-border` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

## Summary

Build a separate authenticated control-only GCP Border using R02's owner and
signed-operation contracts. On-prem members select immutable one-device pyATS
profiles; the browser separately approves R1/R2/SW1/SW2 reads. Serve a production
protected HUD behind named HTTPS, use isolated reviewed IaC, and prove actual
apply/workload/recovery/teardown while preserving R01 and release holds.

## Technical Context

**Language/Version**: Python3.12 federation/native tools; Python3.10+ role/IaC helpers; existing JavaScript ESM/React18 and qualified Node24.19.  
**Primary Dependencies**: Existing strict TLS/federation, FastMCP/MCP, SQLite, Express/React/Vite build; OpenTofu1.13.2 Google8.9.0, Caddy2.11.7. No new MCP server or UI framework.  
**Storage**: Selected private homes/SQLite authority and ledger; one-device frozen profiles; external0700 private cloud state/evidence; bounded installation-scoped browser reference storage.  
**Testing**: Existing unittest/Node/browser suites; native transcript verification; independent receipt validation; actual GCP/IAP/DNS/TLS/firewall/workload/teardown.  
**Target Platform**: Ubuntu24.04 GCP AMD64 control-only Border; qualified Mac on-prem native pyATS25.2 and isolated OpenClaw/Hermes containers. Cloud Hermes remains unqualified.  
**Project Type**: Existing federation service/HUD plus maintainer-only IaC and activation tooling.  
**Performance Goals**: Existing one-effect/two-inference bounds and finite operation deadlines; <=32 retained browser references; <=16 immutable device profiles; no unattended loop/retry.  
**Constraints**: CAD100/month total hard ceiling including R01; exact cloud/DNS/runtime/teardown review; <=48h proposed qualification; R01 untouched; no cloud provider/device keys or model; five implementation passes overall, two already used.  
**Scale/Scope**: One configured owner, one GCP region, one fresh Border, one on-prem pyATS member with four device profiles; optional retained Hermes evidence, no cloud member/batch/write/SSO.

## Constitution Check

Pre-design and post-design gates: specification and user-authorized R03 scope
precede implementation; existing MCP/GAIT and model/tool boundaries reused;
real observations precede device claims; read-only device scope; no production
configuration CR needed because no device configuration occurs. Failed/unknown
operations remain recorded/spent. Secrets and private topology artifacts stay
private; only sanitized technical evidence enters source. Existing framework and
runtime policies preserved. Independent review and full acceptance required.

Owner's explicit issue310 release hold overrides release/version/public README,
blog/announcement/package steps in generic constitution workflow; no waiver of
execution safety is inferred. Technical spec/evidence stays under this directory,
IaC is maintainer-only and cannot be advertised as general deployment support.
Exact cloud mutations and R03 human acceptance remain separate gates. Budget
uncertainty blocks live apply, not source implementation. No unresolved design
clarification; cost/delegation are explicit execution dependencies.

## Project Structure

- `specs/172-gcp-hybrid-border/`: specification, plan, research, data model,
  contracts, tasks, private-packet references, verification and resume.
- `mcp-servers/protocol-mcp/bgp/federation/protected_docker.py`: immutable profile
  selector/factory; `protected_service.py`: catalog and role validation.
- `scripts/lib/protected_role.py`, `scripts/protected-role.py`: provider-neutral
  explicit activation contract validation/rendering and controlled launch.
- `mcp-servers/protocol-mcp/bgp/federation/posture.py`: role-aware posture if
  current production controls require a Border-local guard.
- `ui/netclaw-visual/protected-server.mjs`, `src/hud-server/`: dedicated protected
  production server using existing authority bridge; exact asset closure.
- `ui/netclaw-visual/src/dashboard/ApprovedOperationsView.jsx` and shared reference
  helpers: bounded operation references, four independent review/result rows.
- `labs/cloud/gcp/r03/`: isolated OpenTofu, reviewed unit/Caddy templates and
  source/activation/teardown helpers, no secret values or existing state.
- Existing adjacent `tests/` and HUD tests: focused source and integration cases.

## Design and work lanes

1. Freeze spec/contracts/tasks and independent consistency review.
2. **Pass3** parallel worktrees: HUD lane production ingress/four-reference UX;
   protocol lane immutable device selector/catalog tests; coordinator role/IaC
   and activation; independent lane adversarial review and qualification design.
3. Merge source only after focused tests, then integrated protected/legacy/build
   suites. Additional bounded repair passes4–5 only for actual findings; no
   automatic loop hook or repeated provider/device effects.
4. Prepare exact saved resource plan, finite cost/egress/expiry assumptions and
   teardown scope; request delegation only after it is concrete/reviewable.
5. After separate cloud/runtime delegation: fresh apply, locally generated cloud
   secrets only, fixed source transfer, least-privilege services/DNS/TLS; fresh
   on-prem enrolled member and individually qualified device profiles.
6. Browser approvals and four actual reads, negative/recovery/credential/network
   evidence; independent audit. Export private evidence before reviewed teardown.
7. Final cost/residue/R01 preservation evidence and human acceptance; stop beforeR04.

## Complexity Tracking

No new framework, MCP server, identity system or signed batch contract. A separate
production HUD entrypoint is necessary because the legacy server initializes
broader integrations and enforces a different local authority policy. Immutable
profile selection avoids four service homes while retaining one-device children.
