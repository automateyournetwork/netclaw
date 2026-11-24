# Implementation Plan: R10 Azure Multi-Cloud

> Implemented and live-qualified November24. See [closure-20261124.md](closure-20261124.md) for actual acceptance, source changes, cost and teardown evidence. Each member binds to ONE authority group; signed peer relay supplies cross-cloud execution.

**Branch**: `198-azure-multicloud-ha` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

## Summary

Prove the R09/R09A Border, 3-region HA and member model on Microsoft Azure, then federate two three-Border Azure and GCP HA groups. The
Border/HA/member code is already cloud-neutral; only the VM lifecycle (create, ssh/scp, firewall, tear-down, cost) is
GCP-specific. R10 therefore adds a thin **cloud driver layer** (`gcp` existing behavior preserved, `azure` new) under the R09
scripts, an **Azure preflight and spend guard**, and an **Azure phase runner** with one resource group per phase. No Border,
HA-authority or federation code is changed unless a live finding forces it, and any such change is listed for owner review.

## Technical Context

**Language/Version**: Bash (driver + deploy glue, matches `scripts/ha-r09-*.sh`), Python 3.10+ (preflight, spend ledger, evidence; stdlib only, matches `labs/ha/r09_*.py`); isolated Python 3.12 Border contract environment, with measured admission and signed relay changes listed in closure
**Primary Dependencies**: Azure CLI (`az`, already installed) with no new Python packages; existing lego (ACME DNS-01), etcd 3.6.16 container image, GoDaddy DNS API, existing `r09_prepare.py` / `r09_member.py` / `r09_vm_*.py`
**Storage**: Local evidence under `specs/198-azure-multicloud-ha/` and `~/.local/share/netclaw/r10-*` (git-ignored); per-VM disks only; spend ledger is a small JSON file; no new datastore
**Testing**: Python unit tests for preflight/ledger parsing (fixtures of `az` JSON), shell dry-run mode for every driver command (prints, never executes), then the live phases as the integration test
**Target Platform**: Ubuntu24.04 x86_64; Azure canadacentral/eastus2/swedencentral and GCP Montreal/Belgium/Singapore; Mac subnet members and a physical GCP NetBox member
**Project Type**: Infrastructure tooling and live validation (no application UI)
**Performance Goals**: Preserved HA guarantees with topology-measured, freshly signed admission_ms 9000 and manifest-derived RPC wait; preflight < 10 min
**Constraints**: USD25 cumulative hard ceiling; owner approved the USD23.0075943167 envelope and one crossing of the USD15 pause; seven bounded VMs with unchanged finite watchdogs; exported state before verified teardown
**Scale/Scope**: Six Border VMs, three per cloud with colocated etcd voters, plus one physical GCP member VM; fresh isolated Mac members

## Constitution Check

| Principle | Status |
|-----------|--------|
| I Safety-first / VIII Verify after change | PASS: dry-run mode, per-phase verification, teardown verified by query |
| IV Immutable audit trail | PASS: evidence record per phase (FR-020), federation audit on both clouds |
| IX Security by default | PASS: SSH limited to the owner's IP, no open management ports except 443/federation, key shredded at teardown; owner already accepted open-lab workspace for R09, restating it is required here (see research R6) |
| XI Full-stack artifact coherence | PASS (no new MCP/skill): docs surfaces enumerated in tasks; README, docs, `.env.example` updated for new variables |
| XIII Credential safety | PASS: Azure/GoDaddy/Anthropic/NetBox values only in private env files, never printed or committed |
| XVI Spec-driven | PASS: spec, plan, tasks, evidence |
| XVII Milestone doc | Deferred: blog post drafted for owner review only, never published without approval |
| XV Backwards compatibility | PASS: GCP behavior preserved via driver default `gcp`, GCP scripts keep working |

No violations; Complexity Tracking not needed.

## Project Structure

```text
specs/198-azure-multicloud-ha/   spec.md plan.md research.md data-model.md quickstart.md contracts/ tasks.md verification.md
scripts/
├── ha-cloud.sh                  # driver dispatcher: ha_cloud <provider> <verb> ...  (verbs in contracts/cloud-driver.md)
├── ha-cloud-gcp.sh              # existing gcloud behavior extracted verbatim (no behavior change)
├── ha-cloud-azure.sh            # az implementation
├── ha-r10-preflight.sh          # read-only: subscription, size, quota, budget, DNS/key presence
└── ha-r10-phase.sh              # up|status|down for one phase (resource group)
labs/ha/
├── r10_ledger.py                # spend ledger + $15/$25 gates
├── r10_preflight.py             # parse az JSON -> go/no-go report
└── test_r10_*.py
docs/                            # Azure counterparts (see tasks)
```

**Structure Decision**: extend `scripts/` and `labs/ha/` in place. R10 deployment copies route through the cloud driver; existing R09 deployment scripts remain intact. The shared member builder gained dependency closure validation required by the actual fresh Linux host finding.
