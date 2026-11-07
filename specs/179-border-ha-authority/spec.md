# Feature Specification: R08 Border HA authority

**Feature Branch**: `179-border-ha-authority`  
**Created**: 2026-11-07  
**Status**: Authorized scope; SDD design validated; implementation in progress  
**Roadmap**: R08; depends on accepted R07/Spec178  
**Input**: “alright drive R08 to 100% do you have questions remember to use SDD”

Deliver the shared HA architecture discussed with the owner through the R08
safety gate. R09 separately deploys and measures it across three GCP regions.
Several Borders in one organization provide one current protected-execution
authority. Members enforce that authority. Loss of majority blocks new protected
admission; uncertainty never permits an automatic second execution.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Continue through a surviving Border (Priority: P1)

The operator can use any enrolled Border and continue new read-only work after
one Border fails, with the same cluster identity and original operation history.

**Why this priority**: Redundant ingress must preserve exclusive execution authority.

**Independent Test**: Three isolated Borders and a member, one exact approved
native workload, then loss of the active authority and a distinct new operation
through a survivor. Inspect all admissions, model/tool calls and signed receipts.

**Acceptance Scenarios**:
1. **Given** a healthy majority, **When** an operator uses a follower, **Then** it
   forwards protected requests to the current authority without creating a new approval.
2. **Given** authority loss, **When** the surviving majority establishes a new
   authority, **Then** members accept fresh work under it and refuse stale dispatches.
3. **Given** an original uncertain or completed operation, **When** authority
   changes, **Then** recovery retrieves its original evidence or truthful uncertainty.

### User Story 2 — Refuse split authority and stale work (Priority: P1)

The operator can trust that isolation, delayed traffic or a returning old process
cannot create another execution authority or spend an approval again.

**Why this priority**: Availability must not create duplicated effects or grants.

**Independent Test**: Minority, asymmetric and three-way partitions; pause/resume
old processes; delay admission replies; lose majority; compare durable admissions
and native effect counts across all participants.

**Acceptance Scenarios**:
1. **Given** a partition, **When** a minority or stale Border requests admission,
   **Then** it cannot obtain fresh authority-dependent execution claims.
2. **Given** no majority, **When** any path attempts a new protected model/tool
   admission, **Then** it refuses and reports quorum unavailable.
3. **Given** an admission that committed before failure, **When** its response or
   effect becomes uncertain, **Then** the original claim stays spent and no replacement
   attempt is automatically created. Previously admitted in-flight work is recorded.
4. **Given** a member isolated with an old Border, **When** it has never observed
   the newer leader epoch, **Then** cached authority alone cannot admit fresh work.

### User Story 3 — Recover and administer authority safely (Priority: P1)

The operator can restart, retire or restore owned cluster components without
resurrecting expired authority, removed identities or consumed approvals.

**Why this priority**: Recovery and lifecycle controls are part of HA correctness.

**Independent Test**: Full restart, expired/revoked membership, retired-node return,
unknown commit recovery and an isolated restore drill with old-authority fencing.

**Acceptance Scenarios**:
1. **Given** a full process restart, **When** original durable state is recovered,
   **Then** pending, spent and unknown claims survive and nothing replays.
2. **Given** a retired node or obsolete enrollment, **When** it reconnects,
   **Then** it is refused until explicitly enrolled again with new authority.
3. **Given** a proposed restore, **When** old voters/executors cannot be shown
   isolated, **Then** activation refuses. A changed cluster identifier alone is insufficient.
4. **Given** member or external federation credentials, **When** they access
   cluster administration or consensus, **Then** access is denied.

### User Story 4 — Use HA from HUD, VS Code and Mobile (Priority: P1)

The operator sees authority/quorum health and preserves enrollment, exact pending
reviews and original results while connecting to another trusted cluster Border.

**Why this priority**: All three operating interfaces are affected by logical identity.

**Independent Test**: Actual browser, isolated supported Mac VS Code and native iOS
simulator sessions against the owned cluster; change authority, lose quorum, cold
restart/reconnect and recover the same operation with unchanged effects.

**Acceptance Scenarios**:
1. **Given** cluster enrollment, **When** the selected Border fails, **Then** a
   trusted alternative authenticates the same cluster and a separately enrolled node.
2. **Given** stale or already sent approval, **When** a client reconnects,
   **Then** it cannot renew, widen or repeat that decision automatically.
3. **Given** quorum loss, **When** the interface opens, **Then** it distinguishes
   retained status from current authority and explains why new work is unavailable.
4. **Given** an unrelated cluster/node or invalid TLS identity, **When** it is
   offered as a replacement endpoint, **Then** it is refused without erasing prior state.

### Edge Cases

- A quorum transaction commits but its reply is lost; same-ID reconciliation is read-only.
- A process pauses between receiving permission and crossing an effect boundary.
- A clock jumps, the host suspends or an execution process incarnation changes.
- A new operation ID attempts to bypass an unknown runner or workload reservation.
- A revoked membership/approval races leader transfer or an asynchronous response.
- Capacity, state quota, disk latency or audit storage exhaustion prevents safe admission.
- An endpoint remains reachable after authority loss, or a proxy redirects to a stranger.
- A stale snapshot contains old approvals; a surviving old quorum remains reachable.
- An external peer or member claims a cluster role; shared addressing confers no trust.
- The owner retains a standalone installation and its current identities and schedules.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Support explicitly selected HA clusters with a stable organization/
  cluster identity, separate Border/node identities and explicit membership generations.
- **FR-002**: Establish at most one current authority through a majority of three
  voters; distinguish voter membership, Border membership and transport health.
- **FR-003**: Permit protected requests through each eligible Border, forwarding
  to the authority with unchanged request identity, principal, approval and scope.
- **FR-004**: Attach members outbound to all enrolled eligible Borders; refuse
  member-to-member and unenrolled Border access. Preserve standalone behaviour.
- **FR-005**: Members and native guards MUST require fresh, exact, single-use
  authority for each protected model/tool admission; old epochs, process instances,
  approvals, nonces and reused claims are refused even on still-open channels.
- **FR-006**: Each authority-dependent admission has one durable total-order
  decision point. No majority means no new decision can commit. Already committed
  work may begin only within its admission validity window, then finish under the
  existing bounded operation/tool deadline. Every later model/tool boundary needs
  a fresh admission; completed effects cannot be
  undone by later loss. Never claim instantaneous cancellation or universal exactly-once effects.
- **FR-007**: Lease/freshness enforcement MUST handle configured clock uncertainty,
  process pause/restart and delayed replies conservatively, failing closed outside
  the measured timing envelope. A local clock or cached leader observation is insufficient.
- **FR-008**: Preserve approvals, revocations, claim consumption, outstanding
  resource/runner fences and original operation identities across leader changes.
- **FR-009**: Unknown admission/provider/tool outcomes remain fenced and reconcile
  by original identity without automatic effect retry or new-ID escape.
- **FR-010**: Persist signed native results, acknowledgement and audit references;
  a surviving Border can recover original available evidence. Unavailable evidence
  is reported honestly and does not authorize re-execution.
- **FR-026**: Ground HA in existing NCFED framing, authenticated federation identity,
  iN2N execution and eN2N boundaries. Consensus is private coordination only; it
  does not replace NCFED, create member consensus access or bypass grants/guards.
- **FR-011**: Cluster enrollment and links are a distinct authenticated relationship
  from iN2N members and independent-organization eN2N grants. Neither grants votes,
  cluster administration or consensus access.
- **FR-012**: Protect cluster peer and control access with authenticated encryption,
  explicit caller/address constraints and least privilege. No public consensus,
  member credentials, model, MCP or broker endpoints.
- **FR-013**: Shared authority contains only bounded control metadata and evidence
  references; never chat/RAG payloads, integration secrets or whole installation databases.
  Capacity exhaustion refuses new work without discarding spent/unknown evidence.
- **FR-014**: Retire nodes durably before disconnect; returning obsolete identities
  cannot regain authority. Adding/removing voters requires the current majority.
- **FR-015**: Full restart and restore retain consumed authority. A restore activates
  only after demonstrable isolation of old voters/executors and explicit new fenced
  generation. If an old snapshot omits later admissions, reconcile that evidence
  gap or freeze every affected resource/runner; missing evidence refuses activation.
- **FR-016**: HUD exposes leader, quorum, node/attachment health, stale observations
  and refusal reasons without confusing reachability with execution authority.
- **FR-017**: VS Code separately supports trusted cluster identity/endpoint selection,
  failover and exact pending/result recovery with actual native G12 evidence.
- **FR-018**: Mobile separately supports cluster enrollment/trusted endpoint reconnect,
  approvals/results, background/cold recovery with actual native G13 evidence.
- **FR-019**: All clients preserve the existing sent-decision markers and reject
  stale reviews or identity substitutions; status recovery performs no submission.
- **FR-020**: Qualify the full fault matrix with actual authenticated quorum transport
  and controlled effects first, then the actual NetClaw supported guarded runtime,
  real model, native read-only MCP, signed results, durable ACK and attributable audit.
- **FR-021**: Label every evidence row FIXTURE or REAL with exact source/runtime,
  faults, counters and limits; companion/standalone evidence cannot qualify HA binding.
- **FR-022**: Use fresh isolated owned resources and finite workload/resource bounds;
  baseline/export/verify cleanup and preserve retained owner runtimes and retirement jobs.
- **FR-023**: Maintain existing standalone OpenClaw/Hermes, direct transport, ordinary
  eN2N and client behaviour. Unqualified HA adapters fail closed with a documented reason.
- **FR-024**: Complete operator setup, diagnosis, retirement, fenced restore and
  evidence procedures; reconcile installer/configuration/client artifacts and maintain
  a complete requirement-to-evidence ledger.
- **FR-025**: Preserve source1.18.7, extension1.6.1, Mobile1.0.4+7 and roadmap publication
  hold. R09 resources, geographic availability, multi-user/SSO/RBAC, external federation
  endpoint failover and workload replicas are separate scopes, not implied achievements.

### Key Entities

- **Cluster identity/membership**: stable service audience, fenced generation,
  enrolled node keys, roles, endpoint identities and revocation revisions.
- **Authority**: current leader incarnation, epoch, majority decision and lease.
- **Approval/admission**: exact principal, operation/member/workload, approved content,
  expiry, fresh challenge, one-use claim and resource/runner reservation.
- **Operation evidence**: original attempts, model/tool claims, signed result, ACK,
  audit links and unknown state, independent of the currently selected Border.
- **Client binding**: trusted cluster audience plus node identity and routing endpoint,
  original operation references and monotone decision markers.
- **Qualification record**: fault/evidence class, immutable source/runtime identities,
  actual counters, timing envelope, negative cases and owned-resource lifecycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All mandated leader-loss, minority/asymmetric/three-way partition,
  stale-leader, quorum-loss, clock uncertainty, full restart, retired-node and
  fenced-restore rows have passing fixture evidence followed by the explicit required real
  guarded-runtime/control-plane evidence in the qualification matrix, with no unresolved safety failure.
- **SC-002**: Across every drill there is at most one current admitting authority;
  zero stale/invalid admissions, replayed effects or unknown-claim escapes occur.
- **SC-003**: Every healthy Border can serve a selected actual protected workload;
  leader failure permits a distinct new operation through a surviving majority,
  while original result/unknown recovery never increases original effect counters.
- **SC-004**: Actual browser, Mac VS Code and native iOS simulator demonstrate
  authority change, quorum loss and original approval/result preservation; physical
  iPhone and other platforms receive explicit qualification limits.
- **SC-005**: Every fault records detection, new-authority and service-recovery
  durations separately, alongside network/storage/clock bounds; recovery objectives
  are based on measurements rather than a claim of zero interruption.
- **SC-006**: All required tasks, regressions and artifact coherence checks pass;
  private evidence export and owned cleanup are verified, retained resources preserved,
  and the owner receives the complete acceptance packet before R09.

## Assumptions

- The owner's “alright drive R08 to100%” follows the joint strategy and authorizes
  full SDD/source implementation and isolated local qualification with its stated
  private direct transport and three-voter starting design. Earlier discussion-only
  holds are superseded for R08; no repeated permission request is needed for that scope.
- Existing local model/native subnet tooling is the default first real workload.
  Exact runtime images, resource bounds and protocol/timing choices belong in the plan.
- The initial fault model is authenticated crash/omission/partition failure among
  trusted enrolled processes, not Byzantine quorum or compromised-host tolerance.
- Geographic deployment, surviving every cloud member's region and eN2N ingress
  failover remain R09 design decisions. No existing deployment is silently upgraded.
- Human roadmap acceptance follows the completed evidence packet; the agent does
  not fabricate that future acceptance. All technical closure work remains required.

## Clarifications

### Session 2026-11-07

Zero additional blocking questions. Scope and recommended transport/consensus
starting point were presented before the owner directed completion. The defaults
above are explicit implementation assumptions, not invented question answers.
Formal coverage: functional scope, identities/data, interactions, nonfunctional
bounds, dependencies, failures, constraints and terminology are specified;
concrete dependency/timing/resource choices are resolved during planning.

Owner steering during SDD: “and its all grounded in NCFED rifght”. FR-026 makes
that foundation explicit; no alternative application federation stack is introduced.
