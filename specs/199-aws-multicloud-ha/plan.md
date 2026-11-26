# Implementation Plan: Staged AWS Qualification

**Branch**: `199-aws-multicloud-ha` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Summary
Build an AWS-specific private qualification lifecycle around existing NCFED protected roles. Deliver single Border, physical member, quick Ollama/retirement, AWS three-AZ HA, and nine-Border mesh LAST. Keep later regional policy restrictions distinct from early-stage source/preflight readiness. No general deployment recipe or release.

## Technical Context
**Language/Version**: Python3.10+ stdlib host tooling; isolated Python3.12 federation; existing Node24.19/React/TypeScript clients.
**Primary Dependencies**: Existing AWS CLI2.35.24, NCFED/FastMCP/MCP, SQLite, OpenShell/DefenseClaw, Docker, pinned OpenClaw/Sonnet and Ollama reference closures; external etcd3.6.16. No new Python dependency/MCP server/UI framework.
**Storage**: Private0700 campaign directory;0600 packets, ledgers, consistent SQLite exports and credentials; secret-free source examples.
**Testing**: Python unittest/pytest for lifecycle/ledger/ownership; existing protocol/HUD/Code regressions and actual native/cloud evidence.
**Target Platform**: Ohio Ubuntu24.04 x86_64 first; later approved three-AZ Ohio AWS; existing qualified Azure/GCP profiles freshly instantiated last.
**Project Type**: Maintainer-only lifecycle/preflight CLI and qualification harness.
**Performance Goals**: Explicit stage leases and signed operation deadlines; measured regional admission. Never infer an end-to-end timeout from raw RTT.
**Constraints**: USD100 gross AWS, pause80/reserve5; USD10 all non-AWS; early stages max6h, Ollama1h, final mesh2h; preserve unknowns and owner homes.
**Scale/Scope**: One Border initially; regional3Borders/3AWSmembers; final9Borders/3clouds/27representative cells. No Ollama HA requirement.

## Constitution Check
Pre-research and post-design: PASS for bounded owner-lab source work.
- I–IV/VIII: read baseline before writes, GAIT, no device configuration, owned evidence-first cleanup. Cloud teardown is explicitly requested and exact-resource scoped.
- V–VII/XI: reuse existing MCP/NCFED execution. These lifecycle scripts do not add agent-facing tools; no new MCP/catalog/skill count or installer advertisement. Record a coherence matrix rather than inventing registrations.
- IX/XIII/XV: strict TLS, least privilege, secrets outside Git, isolated dependency closure, no AWS SDK dependency or owner installation upgrade.
- XIV/XVI: staged scope ratified by owner; specification→plan→tasks→analysis→implementation. No external communication/source publication implied.
- XII/XVII: maintainer evidence kept current; existing owner publication hold takes precedence over public WordPress/blog rollout. Record deferred milestone privately.
- Native HUD/Code are required; Mobile receives an explicit impact/authority decision. No unqualified device-key cross-cloud grants.

## Research and Design Decisions
See [research.md](research.md), [data-model.md](data-model.md), [contracts/lifecycle.md](contracts/lifecycle.md) and [contracts/acceptance.md](contracts/acceptance.md).
- Start Ohio with explicitly selected m7i-flex.large2vCPU/8GiB after the account rejected m7i.large as FREE-plan ineligible. Flex has40%baseline/vCPU and bursts; do not claim continuous full CPU. Use Canonical-owned Ubuntu24.04 AMI pinned from public SSM;40GiB encrypted gp3 root. Other types require a revised packet, never an implicit fallback.
- New owned VPC/subnet/IGW/security groups; no default-VPC mutation, NAT Gateway, load balancer or GPU. Narrow operator SSH plus exact peer/member TLS ports, host metadata restricted to bootstrap/root; containers receive no AWS credential role.
- Reuse `labs/ha/r09_prepare.py` one-voter path and schema3 protected-role payload. Do not deploy old R03 control-only host templates as a full HUD.
- Add private AWS lifecycle/preflight/ownership modules in `labs/cloud/aws/spec199/`; reuse qualified remote payload functions with provider-neutral inputs, not hardcoded Spec198 run scripts.
- Fresh stage-aware ledger; R10's USD25 hard clamp/global approval bit cannot carry USD100 scope. Persist sent markers and reserve before creating anything.
- Independent deadline stop: prefer exact-ID EventBridge Scheduler stop with a dedicated least-privilege role/schedule group, plus host/local guard. Validate IAM/Scheduler support before activation. If unavailable, first-stage activation is blocked until an equally independent reviewed safeguard exists. Preserve EBS for export; stop is not zero burn. Never rely on export-at-shutdown alone.
- AWS regional networking: unique CIDRs and pairwise inter-region VPC peering/routes, strict voter TLS with explicit hosts maps. Capability checks and pricing precede stage4; current SCP denial is an external gate.
- Core peer federation already supports multiple pinned groups. Build target-specific matrix validation; old generic local/remote acceptance is insufficient.

## Project Structure
```text
specs/199-aws-multicloud-ha/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md verification.md
  checklists/requirements.md
  contracts/lifecycle.md contracts/acceptance.md
labs/cloud/aws/spec199/
  preflight.py campaign.py lifecycle.py watchdog.py qualify.py regional.py
  run.py aws_api.py cleanup.py regional_run.py matrix.py
  test_preflight.py test_campaign.py test_lifecycle.py test_watchdog.py test_qualify.py
  test_regional.py test_regional_run.py test_matrix.py
```
Shared changes only where needed: `labs/ha/r09_prepare.py`, `r09_member.py`, `r09a_policy.py`, `r10_payload.py`, `r10_node_run.py`, `r10_group.py`, `labs/ollama/qualify.py`, and affected native client contracts. Preserve old behavior with regression tests; never rewrite historical evidence/ledgers.

## Implementation Stages
1. Setup/SDD and read-only Ohio preflight; independent research, traceability analysis, positive/negative unit checks.
2. Frozen campaign packets, reservations, immutable ownership, unknown-create reconciliation, export verification and safeguards. No paid run until these pass.
3. US1: exact single-Border packet and permitted lifecycle, fresh one-voter runtime, local scoped native read, HUD/Code recovery, late faults and export.
4. US2: separate AWS-hosted member; Unix relay/lazy imports; native placement/result/ACK proof.
5. US3: narrow Spec199 Ollama ownership extension, one bounded CPU proof, sealed exports and exact removal/absence. Stop here on any unresolved outcome.
6. US4: only after fresh three-AZ access/quota/price checks and prior acceptance, qualify three Borders/members, nine pairs and successor completion.
7. US5: final two-hour cloud mesh, named27cells, native recovery, faults last, exact all-cloud cleanup and delayed billing record.

## Execution Gates
US1–US3 actual bounded acceptance and cleanup are recorded in verification.md. Renewed authentication and all17enabled-region reads onNovember26 at16:06UTC still yield Ohio only and16OrganizationsSCPdenials. Stage4 access remains blocked. Regional once-only apply, custody, route verification, export-gated cleanup and repeated absence are implemented and fixture-tested separately from the single-Ohio runner. No actual Stage4 packet/reservation exists. A fresh complete priced packet and actual runtime safeguards remain required after access changes. Gate failures never authorize a policy workaround.

## Complexity Tracking
No new framework, agent-facing server, public installer or authority design. No constitutional exemption requested. Later external environment gates are explicit, not unresolved product decisions.

## Owner-approved Ohio amendment — 2026-11-26

Keep the existing strict three-region path and add explicit `ohio-three-az` qualification. Carry scope through the frozen campaign packet, graph, placement evidence and named matrix. Verify three distinct actual AZ IDs and instances in Ohio; aggregate six vCPUs and all three hosts in the budget. Preserve three owned VPCs, exact pairwise peering and /32 routes. In same-region peering, derive requester/accepter orientation from node/VPC identity, never region equality. Pin an account-bound owner-paid-upgrade attestation and fresh permission observations if the plan API has no data; unknown credits are never treated as available funds.

Requalify T027/T028/T032/T033/T038 before cloud activation. All original tests remain; new negatives reject one-AZ placement, wrong AZ ID/region, insufficient aggregate quota, absent upgrade evidence, understated three-host pricing and implicit scope substitution. Stage4 requires nine real cells, actual successor completion, measured admission, recovery and late faults. Stage5 remains last with Ohio three-AZ AWS plus three-region Azure and GCP, 27 real cells and original-result recovery. No simulation closes live acceptance. Supersedes the historical region-only gate above; no prior evidence is rewritten.

### Final-stage implementation refinement — 2026-11-26

Stage4 is accepted and fully retired before final activation. The final packet
uses the same owned Ohio three-VPC/AZ graph with stage5 tags and a7200-second
lease. `external.py` adds exact Azure/GCP request graphs, current subscription/
project/region/size/image/quota/price checks, durable once-only HTTP intents,
original asynchronous operation observations and resource custody. GCP uses a
custom owned network, three regional subnets and absolute terminationTime/STOP;
Azure uses three owned VNets with pairwise peering and explicit owned Network
Watchers before VNet creation. No prior Spec198 resources or budget are reused.

The frozen recipe in `mesh.py` admits one immutable child action set after all
nine actual host creations, complete network observations and three independently
signed fresh manifests. Each Border gets exactly six foreign peers on7445.
AWS children use the original reservation journal; external children use the same
final packet and external journal. Changed addresses, incarnations, manifests,
action sets or source closure refuse further writes. The exact five receiving
members are three physical AWS identities plus two fresh local identities for
Azure/GCP, as already allowed by the acceptance contract.

A new finite guard must have a fresh heartbeat and matching live process before
any external VM creation. It visits every original frozen VM slot, including
unknown writes, and never clears uncertainty to resume work. Stop/deallocation
acceptance is followed by bounded original-operation and actual billing-state
reads; an Azure202 is not deallocation, and unknown-create404 is not retirement.
Quiescent export gates deletion, including every cascaded boot disk. Parent
network removal requires original compute and reverse dependencies absent.

One newly created immutable27-operation shared ledger covers runner/HUD/Code;
two inferences and one effect per claim, concurrency1, unknown-slot retention and
legacy10-operation defaults are preserved. Native originals occupy named matrix
cells; recovery and late faults do not authorize extra originals. All final cloud
and runtime controls are preparation until the exact packet is frozen and live
receipts pass. No source publication/release follows this refinement.

### Actual final-run observation reconciliation
The consumed packet and request bodies remain immutable. A once-sealed observation-only receipt records the two-function-file Azure named-group metadata repair, with source-before hashes/AST constraints. Azure disks use their distinct2025-01-02 GET/DELETE API. After all create actions have been observed, cleanup-only adapter corrections may fail future-create source checks while preserving exact custody/export/absence conditions. They never change a live manifest, operation, budget or source-frozen member. See verification.md and the private original receipts.
