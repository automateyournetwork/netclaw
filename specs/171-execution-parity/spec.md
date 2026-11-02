# Feature Specification: Principal-bound execution parity

**Feature Branch**: `171-execution-parity`
**Created**: 2026-11-02
**Status**: Implementation pass 1; independent design gate passed
**Roadmap**: R02 — execution parity on NetClaw production mode
**Input**: Owner directs R02–R05 to complete with independent parallel agents and at most five implementation-loop iterations, retaining the roadmap release hold and human acceptance/cloud-resource gates.

## User Scenarios & Testing

### User Story 1 — Approve one exact read (Priority: P1)

The authenticated owner reviews the operation, enrolled member, model profile,
selected device, tool and exact arguments before authorizing one bounded read.
The member accepts only that operation and reports its attributable result.

**Why this priority**: Reachability and enrollment do not authorize a tool effect.
**Independent Test**: Approve a local-lab `show version` operation through the HUD;
the named member executes the approved read once and the owner sees its result.

**Acceptance Scenarios**:
1. Given an eligible enrolled member and selected lab device, when the owner
   approves the reviewed read, the member executes the exact operation once.
2. Given the same request, when the device, tool, arguments, member, model,
   principal, expiration or signature is changed, the member refuses execution.
3. Given an expired, denied, revoked, missing or consumed approval, when it is
   submitted or replayed concurrently, no further tool execution occurs.

### User Story 2 — Enforce the execution boundary (Priority: P1)

The member's model may propose a tool call. A trusted broker checks that proposal
against the approved operation and owns access to the integration credentials.
The model cannot grant authority or reach the tool/provider around the guard.

**Why this priority**: An approval is ineffective if another path can execute.
**Independent Test**: A permitted proposal reaches the existing pyATS read tool;
changed arguments, a direct tool call and a direct model call are refused.

**Acceptance Scenarios**:
1. Given an approved read, when the model proposes the exact allowed call through
   the guarded path, the broker executes it using member-held credentials.
2. Given the same runtime, when a caller bypasses the guard or broker, execution
   is refused and evidenced without substituting a weaker path.
3. Given the Border and model transcript, when their contents are inspected,
   neither contains device credentials or provider API keys.

### User Story 3 — Reconcile an uncertain outcome (Priority: P1)

The owner can distinguish a refusal, a completed result and an execution whose
outcome is unknown. Losing a reply or restarting a participant never silently
repeats an approved operation.

**Why this priority**: A timeout does not prove that the operation did not run.
**Independent Test**: Drop the submit or result acknowledgement after actual
admission/execution; recover by the original operation identity, with one effect.

**Acceptance Scenarios**:
1. Given a consumed approval, when the submit acknowledgement is lost, the Border
   reconciles the original request instead of creating another execution.
2. Given a finished member operation, when the result acknowledgement is lost,
   the member retains its signed result and the Border reconciles that result.
3. Given a process restart, when a prior effect cannot be established, the owner
   sees an unknown/reconciliation state and no automatic re-execution.
4. Given an altered, unsigned, foreign-member or mismatched result, when received,
   the Border refuses to present it as verified completion.

### User Story 4 — Attribute every decision (Priority: P1)

The owner can trace who approved an operation, which member accepted it, the
execution attempt and the verified outcome in the existing audit trail.

**Independent Test**: Follow one approved read and one refusal through GAIT;
principal, operation and approval identities agree across the relevant records.

**Acceptance Scenarios**:
1. Given an owner request, when it is approved, dispatched, refused or completed,
   records retain the trusted principal and correlation identities.
2. Given client-supplied identity claims or model text, when they conflict with
   the authenticated owner, they do not change the principal or authorization.
3. Given unavailable required durable storage or audit, when new protected work
   is requested, the request fails closed before the affected boundary.

### User Story 5 — Preserve existing installations and explain parity (Priority: P2)

Maintainers can inspect an evidence-based mapping of the reference guarantees to
NetClaw's reused, partial and newly implemented controls. Existing qualified
harnesses and installation paths retain their documented behavior.

**Independent Test**: Review the matrix and verification report, run the existing
relevant regression suites and show the new protected path in fresh local homes.

**Acceptance Scenarios**:
1. Given a claimed control, when a maintainer inspects the matrix, it links to
   code and actual evidence or explicitly states an unqualified boundary.
2. Given existing OpenClaw/Hermes installations, when the new profile is not
   selected, unrelated homes, credentials, runtime bindings and services remain
   unchanged; unsupported protected profiles refuse rather than downgrade.

### Edge Cases

- Duplicate submissions or concurrent approval consumption on one member.
- Lost submit acknowledgement before the Border learns the member task ID.
- Expiration/revocation during inference but before the proposed tool effect.
- Membership removal, identity replacement or model-profile change after review.
- Guard/broker stop, runtime restart, partial durable writes or full storage.
- Tool effect followed by process termination before result persistence.
- Result persisted on the member but not acknowledged durably by the Border.
- Correctly signed result attached to the wrong operation, principal or member.
- Unknown device, changed device identity, disallowed command or stale inventory.
- Client/model attempt to supply an approval, principal or stronger scope.
- Missing local runtime, unavailable lab device or hosted-provider failure.

## Requirements

### Functional Requirements

- **FR-001**: Every protected request MUST carry a trusted principal with issuer,
  subject, display name and roles; R02 supports the owner principal only. Client
  claims and model output MUST NOT establish identity or grant authority.
- **FR-002**: The owner MUST review the exact operation, enrolled member, model
  profile, tool, arguments and device scope before approval. Reviewed material
  MUST be immutable; any changed material requires a new approval.
- **FR-003**: Approval MUST bind the principal, operation identity, member
  identity, tool, exact argument digest, model profile, expiry and unique nonce.
  It MUST be signed by trusted issuing authority and validated by the member.
- **FR-004**: Approval admission/consumption MUST be durable, atomic and one-use.
  Concurrent, expired, reused, missing, foreign and tampered approvals MUST fail
  closed. A resubmission may report existing state but MUST NOT execute again.
- **FR-005**: The member MUST enforce the approved tool/device/argument scope at
  the effect boundary, after the model proposes a call. A model suggestion MUST
  NOT widen scope, select an alternate device or substitute another tool.
- **FR-006**: Integration credentials MUST remain with the executing member's
  broker/guard and MUST be absent from the Border and model context. The new
  Border workflow MUST operate without local inference or provider credentials.
- **FR-007**: Protected model and tool operations MUST use the qualified guard
  and broker paths. Direct calls, unavailable enforcement and unsupported model
  profiles MUST refuse, without automatically falling back to unguarded paths.
- **FR-008**: An execution attempt marker MUST be durable before the guarded
  executor starts. Interruption after possible dispatch/effect MUST preserve an
  uncertain outcome until evidence resolves it, independently of harness.
- **FR-009**: The member MUST sign and durably retain result evidence bound to
  the operation, approval, principal, member, model and exact tool call. The
  Border MUST verify those bindings and durably acknowledge the result before
  presenting the operation as verified completion.
- **FR-010**: Recovery MUST use the original operation/request identity across
  submit-ACK loss, result-ACK loss and restarts. Reconciliation MUST NOT start
  inference or invoke a tool again. Unknown outcomes MUST remain visible.
- **FR-011**: Approval, dispatch, refusal and result audit MUST extend GAIT with
  principal attribution and correlation identities, preserving existing audit
  records and explicit unavailable/failure states.
- **FR-012**: Local acceptance MUST execute an approved pyATS `show version`
  through a member in production mode and independently validate the returned
  parsed evidence. It MUST also prove refusal of unknown devices, disallowed
  commands, altered arguments, expired/reused/missing approvals and guard bypass.
- **FR-013**: Owner-facing review, approval and result endpoints MUST enforce the
  authenticated owner boundary, origin/CSRF protection and private evidence
  ownership. This MUST NOT introduce general multi-user administration or SSO.
- **FR-014**: A parity matrix MUST map every reference control to existing,
  partial or missing NetClaw behavior and then record its implemented evidence
  and qualification limits. Reference/fixture results MUST NOT count as live
  NetClaw qualification.
- **FR-015**: Source changes MUST preserve existing qualified OpenClaw/Hermes
  behavior and installation separation. New profile activation and live tests
  MUST use fresh owned homes unless a separately reviewed change names another
  runtime. Unqualified protected runtime/platform profiles MUST be explicit.
- **FR-016**: This feature MUST perform no cloud deployment, device configuration,
  general release/version bump or public rollout documentation. R03 starts only
  after human review of the completed parity matrix and verification evidence.

### Key Entities

- **Principal**: authenticated owner identity, with future-compatible issuer,
  subject, display name and role attributes.
- **Reviewed operation**: immutable selected member/model/tool/device scope and
  arguments, correlated by one stable operation identity.
- **Approval**: signed, expiring, one-use authorization for that operation.
- **Execution attempt**: durable admission, dispatch/effect and uncertainty state.
- **Member result**: signed, durable, operation-bound evidence or explicit failure.
- **Result acknowledgement**: durable Border acceptance of a verified result.
- **Reconciliation item**: unresolved original operation, recovered without replay.
- **Parity entry**: reference guarantee, actual NetClaw implementation/evidence,
  remaining limits and acceptance status.

## Success Criteria

### Measurable Outcomes

- **SC-001**: One actual browser-approved local pyATS read completes through the
  production member path with matching operation, approval, task and tool evidence.
- **SC-002**: Every listed refusal case prevents unauthorized tool execution;
  concurrent reuse of one approval produces at most one admitted execution.
- **SC-003**: Lost submit-ACK, lost result-ACK and interrupted-execution drills
  each recover or remain explicitly unknown with zero automatic duplicate effects.
- **SC-004**: Every accepted result verifies its signature and approved bindings;
  all signature/binding tampering cases are refused.
- **SC-005**: Inspection of the fresh Border and model context finds no provider
  or integration credentials; actual bypass tests confirm guard/broker confinement.
- **SC-006**: All protected approval/dispatch/result events carry the same trusted
  principal and correlated identities in the existing GAIT trail.
- **SC-007**: Every parity row has an implementation decision and acceptance
  evidence or an explicit qualification limit; relevant regressions pass before
  the human R02 acceptance gate is presented.

## Assumptions

- The accepted R02 brief supplies the scope and recommended decisions: signed
  principal-bound approvals, member-signed results and durable acknowledgement;
  read-only operations require no ServiceNow CR. Writes remain outside R02.
- OpenClaw production mode is the first live acceptance profile. Hermes support
  retains existing behavior; new parity claims require their own actual evidence.
- The owner authorized use of existing Anthropic credentials for scoped lab work;
  model/runtime selection must be pinned and qualified, not inferred from names.
- The prior R01 open Sonnet cloud lab is preserved. It is not the R02 local
  acceptance environment or evidence for R03's authenticated control-only Border.
- The owner selected a coordinator plus three parallel agents. Shared contracts
  are agreed before implementation; each worker receives a separate worktree and
  file ownership. Independent review remains separate from implementation claims.
- Ralph-style implementation loops are optional and limited to five iterations
  total across R02–R05. Their counters and actual validation are recorded; reaching
  the cap never implies completion or waives approvals.
- The owner imposed a total $100/month GCP ceiling, conservatively interpreted
  as CAD100 including R01 pending correction. R02 needs no cloud resources; later
  exact cloud plans must account for existing usage, enforceable resource limits,
  monitoring/stop rules and the provider's billing limitations before approval.
- The full-roadmap release/rollout hold remains. This instruction authorizes
  progression through R02–R05, subject to the existing human acceptance gates and
  exact cloud resource/spend review; it does not start later roadmap features.

## Owner clarification — harness coverage

On 2026-11-02 the owner explicitly added Hermes to R02 testing. Qualify both
OpenClaw and Hermes through the same signed operation, exact tool gate, isolated
credential boundary and no-replay recovery contract. Each has a separately pinned
image/runtime profile and actual acceptance row. A passing OpenClaw result does
not qualify Hermes, and synthetic fixture results do not qualify a live provider
or device. Broader model/provider/platform support remains evidence-specific.
