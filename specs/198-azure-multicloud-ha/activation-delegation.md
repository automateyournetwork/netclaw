# R10 execution authorization — 2026-11-14

The owner authorized choosing three available Azure regions and proceeding with
Spec198 within the existing USD25 budget. This supersedes the fixed West Europe
requirement and earlier per-Azure-phase permission pauses. Preserve the USD15
pause, USD25 total ceiling, bounded run, evidence export and owned cleanup.

The owner then clarified the delivery sequence explicitly:

1. One Azure Border.
2. Three Azure Borders in an HA mesh, plus a cloud-hosted NetBox member.
3. Mesh with a **three-Border GCP HA group**, producing six NCFED Borders total.

The third step supplies the previously reserved GCP go, conditional on completing
the Azure checks first. It supersedes the original one-GCP/one-Azure mesh scope.
No additional permission is needed for those scoped deployments or their teardown.

Implementation interpretation: two three-Border HA authorities, connected through
NCFED federation, with each group's quorum, identity, protected admission and
unknown-result guarantees intact. Six listeners or an ordinary peer connection
alone are not acceptance. Capture actual cross-cloud operations and correlated
evidence from both HA groups; prove operations through all six ingresses and record
leader-loss/recovery outcomes without replay. Keep the on-prem subnet member from
the original scope. This does not authorize a six-voter quorum redesign.

Use fresh isolated resources and per-run state. Existing owner R01/R09 resources,
homes, keys and unrelated workloads remain preserved. Retain the qualified Azure
HA group only for the bounded final mesh proof, then remove owned resources on both
clouds; avoid destroying/recreating it merely to cross a phase boundary. Record
that phase handoff and its continuing ledger entry explicitly.

The cost plan must include six Border VMs, the cloud NetBox member, disks, public
IPs, transfer, bounded hosted-model calls, prior Spec198 spend and cleanup margin.
Subscription budget alerts and a local ledger are not provider hard spending caps;
use short deadlines and automated owned cleanup in addition to admission checks.

Publication, source push/merge, version changes and client releases remain held.
The optional Spec Kit git-commit hook is not executed by this instruction.

## Full Border requirement (owner clarification, same session)

The owner explicitly requires full Azure Borders replicating the GCP functionality:
working HUD, working VS Code, working OpenShell and DefenseClaw, and real calls.
An infrastructure-only VM or successful posture probe does not satisfy this scope.
Use Ubuntu 24.04 amd64 with observed Landlock ABI >=3, Docker >=28, pinned
OpenShell 0.1.7, DefenseClaw 1.0.4 and OpenClaw 2026.7.1-2. Start with 8 GiB
Border hosts and measure memory. The earlier Debian12/4GiB bootstrap is retired;
its successful VM creation is diagnostic evidence only.

Acceptance requires trusted HTTPS HUD rendering, a running workspace and chat
gateway, actual VS Code owner-client discovery/review/approval/reconciliation,
guarded successful calls, guard refusal and fail-closed evidence, cloud NetBox
and on-prem subnet member execution with durable ACKs, then the staged HA and
cross-cloud proofs above. Record each surface's actual evidence separately.
R09A's previous embedded-agent calls do not prove a long-running workspace or
gateway; those must be exercised in this run.

## Owner stop and teardown — 2026-11-14

The owner subsequently requested confirmation that builds are possible, a handoff
for another agent, and to stop and tear everything down for now. This supersedes
the ongoing execution delegation: no further deployment or implementation in this
session. Complete owned cleanup and record the paused, incomplete application
qualification in `handoff.md`. A later explicit resume is required to create again.
