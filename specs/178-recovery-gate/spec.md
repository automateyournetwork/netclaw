# Feature Specification: R07 Single-region recovery gate

**Feature Branch**: `178-recovery-gate`  
**Created**: 2026-11-06  
**Status**: Specified; implementation and actual acceptance pending  
**Input**: “Start Spec 178 / R07 using the saved handoff.” / “drive to 100%”

Complete the recovery gate before R08 authority or R09 regional failure work.
Credit applicable R03–R06 evidence with its exact limits; qualify uncovered cases
and repair demonstrated gaps. The saved handoff delegates a coordinator and three
parallel agents in separate worktrees. It does not extend retained deployments.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Recover the same enrolled system (Priority: P1)

An operator can restart a Border or member and explicitly replace its transport
endpoint while preserving identity, approvals, pending work and completed results.

**Why this priority**: Recovery is a prerequisite for safely adding redundancy.

**Independent Test**: Capture identity and execution evidence, interrupt an owned
runtime/channel, restore it, then retrieve the original result without submitting
the workload again. Exercise explicit same-identity endpoint replacement.

**Acceptance Scenarios**:

1. **Given** an enrolled member, **When** either runtime restarts, **Then** it
   reconnects with the same identity without enrollment or repeated work.
2. **Given** an operator-selected replacement endpoint, **When** the address is
   changed, **Then** existing trust must authenticate the same Border; a different
   identity is refused and original operations remain recoverable.
3. **Given** network/address/provider loss, **When** a caller requests work,
   **Then** the system reports the observed cause, fails closed and performs no
   automatic transport downgrade or uncertain retry.

### User Story 2 — Revocation stops authority (Priority: P1)

An operator can revoke a member key/certificate or an existing authorization and
know that neither an open channel nor a reconnect retains revoked authority.

**Why this priority**: A valid connection must not outlive its authorization.

**Independent Test**: Revoke an isolated enrolled principal while its channel is
open, attempt a fresh authorized action and reconnect, and inspect native effect
counters. Preserve any action already admitted as a distinct historical outcome.

**Acceptance Scenarios**:

1. **Given** an authenticated channel, **When** revocation commits, **Then** no
   subsequent action is admitted under that authority, including on that channel.
2. **Given** a revoked key/certificate, **When** reconnect is attempted, **Then**
   authentication fails with no replacement enrollment or fallback.
3. **Given** an in-flight operation, **When** revocation or provider loss occurs,
   **Then** already observed effects remain recorded and uncertain outcomes are
   retained without a new execution.

### User Story 3 — Reconcile one effect or none (Priority: P1)

The operator can retrieve original work after a lost reply/acknowledgement and
understand duplicate and cancellation outcomes without initiating extra effects.

**Why this priority**: Retry-driven duplicate effects are unsafe even for reads.

**Independent Test**: Inject lost delivery, submit the same operation concurrently,
cancel before and after dispatch, and compare request, attempt, native tool,
provider, result, acknowledgement and audit evidence.

**Acceptance Scenarios**:

1. **Given** completed work with a lost reply or acknowledgement, **When** the
   caller recovers, **Then** the original identity/result is returned and effect
   counts do not increase.
2. **Given** duplicate submissions, **When** they race or span a restart, **Then**
   they produce at most the original effect and retain their original reference.
3. **Given** cancellation, **When** work was not admitted, **Then** there is no
   effect; after dispatch the state records actual completion or uncertainty,
   never an invented rollback or safe-to-retry assertion.

### User Story 4 — Recover from every affected client (Priority: P1)

HUD, VS Code and Mobile users keep their enrolled identity, original operations
and results across connection loss, restart and an explicit endpoint change.

**Why this priority**: Backend recovery alone does not complete client recovery.

**Independent Test**: Exercise actual browser, isolated Mac editor and native iOS
simulator flows, including Mobile foreground/background and cold recovery.

**Acceptance Scenarios**:

1. **Given** pending or completed work, **When** a client loses connection,
   **Then** reconnect retrieves the original record without renewed approval,
   submission or provider execution.
2. **Given** an explicit endpoint update, **When** identity matches, **Then**
   client authority and operation references survive; mismatched identity is
   refused without deleting the prior binding or results.
3. **Given** revoked authority, **When** any client reconnects or requests work,
   **Then** it displays the refusal and does not weaken transport or trust.

### Edge Cases

- A response is lost after native execution but before durable acknowledgement.
- Revocation races admission, response delivery or channel replacement.
- Cancellation races a late signed completion; cancellation is not rollback.
- An endpoint is reachable but presents a different identity or invalid trust.
- A stale registry revision attempts to overwrite a newer explicit endpoint.
- An outage spans client suspension, process restart or retained-resource expiry.
- A cloud cleanup job is pending or has an unknown outcome; no replay or extension.
- Prior evidence used different source/platform/runtime; credit is bounded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Map every R07 acceptance row to retained evidence or a new drill,
  recording source, platform, identities, effect counts and qualification limits.
- **FR-002**: Recover Border service and member restarts without re-enrollment,
  preserving original pending/completed operations and recorded authority.
- **FR-003**: Allow explicit endpoint replacement for the same enrolled identity
  with revision checks; reject changed identity and preserve the prior binding.
- **FR-004**: Fail closed on network/address loss with an observable cause and
  no automatic weaker-transport fallback.
- **FR-005**: Refuse revoked members, keys and certificates on reconnect and
  prohibit new admission immediately after revocation on existing channels.
- **FR-006**: Refuse provider outage at the existing guard; retain uncertain
  provider outcomes and prevent new references from bypassing that uncertainty.
- **FR-007**: Reconcile lost replies/acknowledgements by original reference with
  no duplicate native effect or provider execution.
- **FR-008**: Deduplicate concurrent/restarted task and protected-operation
  submissions by original request identity; cancellation must
  distinguish no-dispatch, dispatched/uncertain and completed outcomes.
  Synchronous read calls are separate executions and must never be automatically
  repeated after an unknown result.
- **FR-009**: Preserve HUD operation/result authority during affected recovery.
- **FR-010**: Separately implement and verify VS Code G12 recovery, including
  connection loss and explicit same-identity endpoint change.
- **FR-011**: Separately implement and verify Mobile G13 recovery, including
  foreground/background, cold recovery and endpoint/identity preservation.
- **FR-012**: Provide an operator procedure for every acceptance row, including
  diagnosis, baseline, exact restoration, no-replay rule and verification.
- **FR-013**: Measure failure-to-detection and restoration-to-recovery durations;
  propose recovery objectives from observations for human agreement.
- **FR-014**: Keep raw evidence private with immutable original failures and
  auditable scenario correlation; expose only sanitized maintainer evidence.
- **FR-015**: Inspect actual resources and original R05/R06 retirement receipts
  before resource work; preserve expiry, identities, state and scheduled cleanup.
- **FR-016**: Use bounded, isolated read-only workloads and reviewed runtime
  changes; cleanup only owned disposable resources after verified export.
- **FR-017**: Explicitly mark optional ngrok scenarios unselected/unqualified
  unless the owner selects that transport; do not substitute fixture evidence.
- **FR-018**: Retain source1.18.6, extension1.6.1 and Mobile1.0.4+7; no publication,
  general rollout, HA/multi-region work or next-stage execution in this feature.

### Key Entities

- **Recovery scenario**: fault, selected runtime/identity, baseline, injected event,
  observed outcome, restoration, measured durations and evidence classification.
- **Operation reference**: original authority/request/attempt/result/acknowledgement
  identity and immutable effect counters used to prove no replay.
- **Endpoint binding**: stable authenticated identity, explicit transport address,
  revision and durable client references; address changes do not create authority.
- **Evidence credit**: prior artifact, exact source/platform/runtime and bounded
  assertion, with uncovered cases explicitly retained.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every mandatory acceptance row has reviewed actual evidence with
  zero unresolved safety failures; optional cases are explicitly classified.
- **SC-002**: Each recovery retains the enrolled identity and original request;
  no duplicate execution, weakened trust or automatic transport fallback occurs.
- **SC-003**: Every post-revocation admission attempt is refused; cancellation
  and lost-delivery cases prove at most one original effect or none.
- **SC-004**: Actual browser, Mac VS Code and native iOS simulator recovery passes
  with preserved authority/results; physical hardware remains separately scoped.
- **SC-005**: Every scenario has a runbook and observed timing or an explicit
  inherited-evidence limitation; proposed timing objectives receive human review.
- **SC-006**: Existing deployment deadlines and cleanup authority are preserved;
  owned disposable changes have exported evidence and verified cleanup.

## Assumptions

- Existing direct transport is selected; optional ngrok is not selected.
- Accepted R03–R06 evidence is credited only for assertions it actually proves.
- Source, isolated local verification and gap fixes are authorized by this request.
  Concrete cloud/resource changes retain applicable exact-plan review boundaries.
- Recovery timing is measured first; a proposed objective is not human acceptance.
- Human acceptance remains the final roadmap gate before R08. “Drive to 100%”
  directs complete execution; it does not fabricate future acceptance evidence.

## Clarifications

### Session 2026-11-06

The saved handoff resolves scope, parallel delegation, direct transport default,
evidence reuse, read-only workloads and stage/release boundaries. No additional
architecture question is necessary. Timing objectives are deliberately reviewed
after measurement; concrete live changes are prepared before any required review.
