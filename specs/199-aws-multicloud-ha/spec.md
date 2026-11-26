# Feature Specification: Staged AWS Qualification

**Feature Branch**: `199-aws-multicloud-ha`
**Created**: 2026-11-25
**Status**: Owner-authorized SDD scope; implementation/live acceptance pending
**Input**: Single AWS Border, AWS member, quick Ollama test/teardown, three AWS Borders/members in three Ohio Availability Zones, nine-Border AWS/Azure/GCP mesh VERY LAST. Owner supplied a $100 AWS budget and authorized proceeding through SDD plus a short small final multi-cloud proof.

**Owner amendment — 2026-11-26**: The owner approved replacing AWS three-region acceptance with actual three-AZ acceptance in us-east-2 and then instructed “good now drive to 100%”. Original cross-region isolation, regional outage recovery and cross-region timing remain deferred/unverified; no simulation satisfies them. Azure/GCP retain three regions each in the final mesh. See [scope-amendment-20261126.md](scope-amendment-20261126.md).

## User Scenarios & Testing

### User Story 1 — One AWS Border (Priority: P1)
John reaches a fresh AWS Border, approves a protected local-member read and recovers its original result in native HUD/Code.
**Why this priority**: Establish the smallest useful AWS deployment before adding members or HA.
**Independent Test**: One Border and one fresh scoped local member produce actual native evidence, signed result/ACK and unchanged counters after client reopening. One voter is explicitly not HA.
**Acceptance Scenarios**:
1. Given verified account, baseline, eligibility, budget and safeguards, when this stage activates, then only the reviewed single-region resources exist.
2. Given a fresh permitted read, when reviewed/approved, then the member produces attributable native evidence, signed result and durable acknowledgement.
3. Given a completed operation, when HUD and Code reopen, then they recover the original result without another inference or effect.
4. Given missing confinement/guard controls, when protected work is requested, then it fails closed.

### User Story 2 — Physical AWS member (Priority: P2)
John delegates a bounded native read to a separate AWS-hosted member.
**Why this priority**: Physical placement is separate evidence from a local-member success.
**Independent Test**: Native tool artifacts and original result/ACK identify the recorded AWS instance/member.
**Acceptance Scenarios**:
1. Given US1 accepted, when a fresh cloud member enrolls, then its home, dependencies, identity and authority group are isolated.
2. Given verified Linux dependencies and relay, when a read completes, then physical placement, provider/tool counts and signatures are independently verified.
3. Given missing lazy imports or an incompatible relay, when preflight runs, then it refuses before provider dispatch; unknown operations are never replayed after repair.

### User Story 3 — Quick Ollama proof and retirement (Priority: P3)
John obtains a guarded CPU Ollama subnet-calculator result and promptly retires its temporary resources.
**Why this priority**: Prove the requested option without carrying it into later HA stages.
**Independent Test**: One bounded task has measured model activity, native tool evidence, result/ACK, verified export and owned-resource absence.
**Acceptance Scenarios**:
1. Given US2 accepted, when the bounded task is approved, then only the frozen model/tool run within their limits, with no hosted fallback.
2. Given completion or uncertainty, when cleanup begins, then evidence is exported and unknown fences remain before exact owned removal.
3. Given the next stage, when activation is considered, then no Ollama compute remains. HA/Ollama is not required by this scope.

### User Story 4 — Three-AZ AWS in Ohio (Priority: P4)
John operates three Borders and three physical AWS members, one of each per distinct observed Availability Zone in us-east-2.
**Why this priority**: Host and AZ separation follow single-host execution and cleanup proof. Regional resilience is deferred.
**Independent Test**: All nine ingress/member pairs pass; a new operation completes after actual leader change.
**Acceptance Scenarios**:
1. Given US1–US3 accepted and three eligible Ohio AZs, when HA activates, then three distinct physical instances and AZ IDs are observed. The run is labeled multi-AZ; no regional-resilience or complete AZ-outage claim follows from a host fault.
2. Given every ingress/member pair, when its operation completes, then original native result/ACK witnesses exist for all nine pairs.
3. Given actual leader loss, when a successor assumes authority, then a distinct new operation completes and old-result reads do not replay effects.
4. Given excessive latency, lost quorum, stale authority or uncertainty, when admission is attempted, then it fails closed under fresh frozen signed limits.

### User Story 5 — Nine-Border mesh VERY LAST (Priority: P5)
After AWS multi-AZ acceptance, John briefly operates three AWS, three Azure and three GCP Borders with separate cloud authorities.
**Why this priority**: Final interoperability proof is the last deployment stage.
**Independent Test**: Named ingress/destination cells pass, then all owned cloud resources/DNS are exported and retired.
**Acceptance Scenarios**:
1. Given US4 accepted and a priced short final packet, when fresh Azure/GCP resources activate, then AWS retains its three Ohio AZs, Azure/GCP each retain three regions, and each cloud retains its own authority; spent identities are never reused.
2. Given nine ingresses and three receiving groups, when representative reads complete, then all 27 ingress/group cells have receiving-group authorization and original result/ACK evidence.
3. Given three physical AWS members, when selecting final targets, then every AWS member is represented. US4 supplies complete AWS placement coverage; 27 representative cells do not claim every member permutation.
4. Given mesh acceptance, when closure finishes, then no owned billable resource/DNS remains; delayed bills and unknown reserves remain explicit.

### Edge Cases
- Expired credentials, denied regions, permission-only dry-run success, exhausted quota or unavailable capacity.
- Unknown create after send: never change token, region, zone or request to obtain a replacement before reconciliation.
- Operator/local-watchdog failure: independent deadline quiescence preserves state and leaves stopped storage costs open.
- Failed export at deadline: stop owned compute and retain evidence/storage rather than delete unexported state.
- Foreign/default infrastructure, repeated cleanup and eventually consistent inventories.
- Model/guard uncertainty, stale/quorum authority and generic remote results wrongly attributed to a named destination.
- Old-leader full artifacts may remain references; retain independently exported originals and explicit recovery limits.

## Requirements

### Functional Requirements
- **FR-001**: Enforce US1 → US2 → US3/cleanup → US4 → US5/cleanup; no stage skipping.
- **FR-002**: Verify actual account, applicable region/inventory/image/permissions/quota/prices/credits before activation; distinguish unknown from zero and permission checks from runtime proof.
- **FR-003**: Keep gross AWS cost plus open reservations within USD100 cumulatively; pause new admissions at USD80 and retain at least USD5 cleanup/uncertainty reserve. Credits never reduce the conservative ledger.
- **FR-004**: Use a conservative USD10 operational ceiling for all non-AWS spend, including hosted calls and final Azure/GCP, under the owner's small-spend direction. Price every component; this self-imposed number is not an owner quotation. Stop if the reviewed scope cannot fit.
- **FR-005**: Reserve exact resources and full lifetime before creation: maximum six-hour early-stage lease, one-hour Ollama lease and two-hour final mesh. Extensions need a fresh budget check; expired watchdogs never restart.
- **FR-006**: Persist immutable ownership, request digests and sent markers before create; reconcile unknown outcomes under the original request identity without speculative replacement.
- **FR-007**: Verify independent compute-stop safeguards before paid qualification; keep stopped disks/addresses charged until direct absence. Budget alerts are not hard caps.
- **FR-008**: Quiesce/export/hash-verify consistent authority/member/audit state before destructive owned cleanup, then verify all resource and DNS residue directly while preserving foreign/default assets.
- **FR-009**: Use fresh isolated homes, frozen source/dependencies, keys/manifests and identities; preserve Spec198 unknowns and Spec200/owner services.
- **FR-010**: Qualify full native HUD/Code review, approval and original-result recovery for the single AWS Border, explicitly without claiming HA.
- **FR-011**: Prove physical AWS member placement, native attribution, lazy imports, host-compatible relay and original result/ACK.
- **FR-012**: Prove one bounded CPU Ollama tool task and prompt evidence-first retirement; preserve runner-wide unknown fences and forbid hosted fallback.
- **FR-013**: Qualify three distinct observed AWS Availability Zones within us-east-2 with three Borders and three physical members, one Border/member pair per distinct instance and AZ. Bind actual AZ IDs and explicitly defer AWS cross-region acceptance.
- **FR-014**: Measure quorum/admission timing and freeze signed limits; retain nearest authenticated selection, expiry and receiving-group authority checks.
- **FR-015**: Prove all nine AWS ingress/member cells and a distinct completed operation after actual leader change.
- **FR-016**: Preserve three separate three-voter cloud authorities in the final mesh, pinned grants and one-group member identities.
- **FR-017**: Key final witnesses by ingress, destination group and member, covering all 27 representative cells; generic local/remote counters cannot close them.
- **FR-018**: Verify native cold GET-only recovery with original operation/result/counters; disclose manual member recovery and full-artifact replication limits where applicable.
- **FR-019**: Run guard/authority faults that may produce unknowns after each applicable stage's success cases; retain original unknowns and reservations.
- **FR-020**: Keep secrets/topology/raw state private and record GAIT, dated verification and exact evidence classes.
- **FR-021**: Review HUD, Code and Mobile impact; qualify HUD/Code and document Mobile changes or a reasoned no-new-authority decision. No broader platform/user-control claim.
- **FR-022**: Preserve existing runtime/cloud compatibility, test meaningful lifecycle/ownership/budget negatives, and retain source/client publication holds. No new MCP tool integration or general cloud installer.

### Key Entities
- **Campaign**: owner scope, cost domains/ceilings, stage frontier and owner baseline.
- **Stage packet**: exact account/resources, immutable source/profile, predecessor receipts, reservation and deadline.
- **Resource record**: immutable service identity, run/stage binding, original request and observed/exported/absent state.
- **Reservation**: gross committed usage, held uncertainty and cleanup allowance by cost domain.
- **Operation witness**: ingress, receiving group/member, original operation, native effect, signed result/ACK and recovery counters.
- **Cleanup receipt**: immutable export manifest, direct absence checks, retained residue and invoice limits.

## Success Criteria

### Measurable Outcomes
- **SC-001**: Every activation has its predecessor receipts and exact frozen resource/budget/deadline packet.
- **SC-002**: One AWS Border completes a protected local read with original result/ACK and HUD/Code recovery.
- **SC-003**: One physical AWS member completes a native read attributable to its recorded instance.
- **SC-004**: The Ollama task stays within its one-hour lease; acceptance requires real native result/ACK plus verified temporary-resource absence.
- **SC-005**: AWS HA has three distinct observed Ohio AZs and instances, three Borders/members, nine passing ingress/member cells and one new completed successor operation.
- **SC-006**: Final mesh has nine Borders, three separate authorities and 27 passing named ingress/group cells.
- **SC-007**: All required native recoveries preserve operation IDs, result digests and inference/effect counts.
- **SC-008**: Tested stale/quorum/guard/ownership/budget violations refuse unauthorized effects and retain uncertainty.
- **SC-009**: Gross-plus-held spend remains within USD100 AWS/USD10 non-AWS without cancelling reserves to admit work.
- **SC-010**: Closure has verified exports and zero open owned billable resources/DNS, with delayed invoices explicit.
- **SC-011**: Spec200 detached97fc1f1a, recordings and owner services remain preserved; no publication occurs.
- **SC-012**: Applicable automated lifecycle uncertainty, foreign ownership, budget concurrency, stage skipping and destination-attribution checks pass.

## Assumptions
- Owner's November25 SDD direction ratifies this staged scope. Exact deployment packets are execution prerequisites, not repeated general permission requests.
- Start with existing qualified OpenClaw/Sonnet read-only subnet/NetBox contracts and fresh identities/credentials. No network configuration is required.
- Ohio inventory/quota/image/RunInstances permission dry-run passed; actual capacity, host confinement and runtime are unqualified.
- The owner-approved amendment replaces the AWS region gate for US4/US5 with three observed Ohio AZs. Retain the denied-region evidence and strict original three-region source path; do not claim it passed or change AWS policy/accounts.
- AWS verified ACTIVE/FREE with USD100 credits on November25, expiration2027-05-16. The owner personally upgraded on November26; Settings confirmed advanced-feature activation. The Free Tier plan endpoint now returns ResourceNotFoundException. Credit balance/consumption are unknown; gross reservations remain authoritative. A frozen owner-upgrade attestation plus successful exact-product permission dry-run is required if plan status is unavailable; this does not prove capacity or credits.
- Azure/GCP representative receiving members may be fresh local members. Their physical cloud placement is not a new requirement; every AWS member's physical placement is required.
- Transparent member auto-recovery, full artifact replication and HA/Ollama are not new requirements; actual limits remain explicit.
- Existing publication holds supersede public rollout/blog requirements; maintainers receive private/source evidence only.
