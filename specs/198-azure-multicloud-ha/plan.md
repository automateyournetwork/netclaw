# Implementation Plan: R10 Azure Multi-Cloud

**Branch**: `198-azure-multicloud-ha` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

## Summary

Prove the R09/R09A Border, 3-region HA and member model on Microsoft Azure, then federate an Azure Border with a GCP Border. The
Border/HA/member code is already cloud-neutral; only the VM lifecycle (create, ssh/scp, firewall, tear-down, cost) is
GCP-specific. R10 therefore adds a thin **cloud driver layer** (`gcp` existing behavior preserved, `azure` new) under the R09
scripts, an **Azure preflight and spend guard**, and an **Azure phase runner** with one resource group per phase. No Border,
HA-authority or federation code is changed unless a live finding forces it, and any such change is listed for owner review.

## Technical Context

**Language/Version**: Bash (driver + deploy glue, matches `scripts/ha-r09-*.sh`), Python 3.10+ (preflight, spend ledger, evidence; stdlib only, matches `labs/ha/r09_*.py`); Border source unchanged (Python 3.12 contract env on the VM)
**Primary Dependencies**: Azure CLI (`az`, already installed) with no new Python packages; existing lego (ACME DNS-01), etcd 3.6.16 container image, GoDaddy DNS API, existing `r09_prepare.py` / `r09_member.py` / `r09_vm_*.py`
**Storage**: Local evidence under `specs/198-azure-multicloud-ha/` and `~/.local/share/netclaw/r10-*` (git-ignored); per-VM disks only; spend ledger is a small JSON file; no new datastore
**Testing**: Python unit tests for preflight/ledger parsing (fixtures of `az` JSON), shell dry-run mode for every driver command (prints, never executes), then the live phases as the integration test
**Target Platform**: Azure Linux VMs (Debian 12, x86_64) in canadacentral, westeurope, southeastasia; the operator's Mac as the on-prem member; GCP Debian VMs for the mesh phase only
**Project Type**: Infrastructure tooling and live validation (no application UI)
**Performance Goals**: Same HA behavior as R09 (signed admission_ms 4500, Montreal-class leader); preflight < 10 min
**Constraints**: $25 total, pause at $15; nothing created before an explicit go per phase; GCP side only on a separate go; one deletable resource group per phase; no managed services; key on VMs only for the run
**Scale/Scope**: 3 Border VMs + 1 optional small witness-free layout (etcd runs on the 3 Borders as in R09); members run on the Mac and as a hosted member process

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

**Structure Decision**: extend `scripts/` and `labs/ha/` in place; do not fork R09. R09 scripts get their hardcoded `gcloud`
calls routed through the driver with `CLOUD=gcp` as default, so existing R09/R09A behavior is unchanged.
