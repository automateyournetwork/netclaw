# R10 — Azure single region

- **Roadmap item:** 5 — Azure, repeat the GCP sequence (single)
- **Depends on:** R09
- **Gate:** human review before R11

## Specify input

Repeat the R03–R05 pattern on Azure using the provider-neutral role contract: an
Azure Border, an Azure NetBox member with a hosted model and an Azure Ollama
member, with the on-prem members attached. The same workloads, refusals and
evidence apply. Azure is qualified as its own environment so the GCP cluster is
unaffected.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Region. [HUMAN]
2. Member identities during provider qualification: on-prem members get separate
   enrolled instances for the Azure environment; R14 consolidates them to one
   identity per member attached to all Borders. [HUMAN]
3. Admin path: Azure Bastion or equivalent identity-aware access.

## Plan notes (Azure deltas)

- Managed identity for the VMs; Key Vault rendered into private `.env` at start.
- Network security groups with no inbound rules for NetClaw services.
- IaC module under `labs/cloud/azure/` implementing the same role contract.

## Acceptance evidence

All R03, R04, R04a and R05 acceptance rows, re-run on Azure, plus cost and teardown.

| Group | Evidence |
|---|---|
| VS Code integration | Explicit G12 impact/disposition and evidence: Azure Border connection, verified identity/authentication and supported workflows |
| Mobile integration | Explicit G13 impact/disposition and evidence: Affected Azure endpoint/enrollment/Ask Border paths use the supported verified transport; reasoned no-impact outcome if unaffected |
