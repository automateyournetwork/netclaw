# Feature Specification: R05 guarded Ollama members

**Feature Branch**: `176-ollama-members`  
**Created**: 2026-11-05  
**Status**: Implementation authorized and in progress  
**Input**: Owner: R5 / next Spec176 using SDD, heavily referring to Thermidor's working solution, tests, outcomes, approach and lessons; then “proceed” and “make the branch and specs etc”.

**Owner clarification during implementation**: This is NetClaw and a NetClaw
member using Ollama, with no Tailscale. Thermidor is reference evidence/patterns
only; no Thermidor product/runtime dependency or transport is introduced.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One request, two approved local-model calculations (Priority: P1)

The operator asks for an IPv4 subnet summary from the on-premises member and an
IPv6 summary from the cloud member in one request. The review shows the exact
input, member, hosting location, inference location, model and limits for each
child. Each child needs its own approval. Both verified results remain together.

**Why this priority**: This is the R05 outcome already demonstrated by Thermidor.

**Independent Test**: Submit a combined request for `192.0.2.0/26` and
`2001:db8:1234::/48`, approve each child separately and independently verify both
results and their execution receipts.

**Acceptance Scenarios**:

1. **Given** two ready members, **When** a combined request is prepared, **Then**
   two immutable child reviews appear and no inference or calculation occurs.
2. **Given** those reviews, **When** only IPv4 is approved, **Then** only that
   child may execute; IPv6 remains unapproved until its separate decision.
3. **Given** both approved children, **When** both succeed, **Then** each result
   identifies the actual member/model, exact arithmetic, measured usage, signed
   result and durable acknowledgement; model narration is not arithmetic proof.
4. **Given** a changed input, member, model or limit, **When** an earlier approval
   is submitted, **Then** it is refused without substituting another executor.

### User Story 2 - Enforced private inference and finite resources (Priority: P1)

Each member runs its own local model behind the existing execution guard. The
operator can verify which callers can reach it and the resources it consumed.

**Why this priority**: Zero provider charges must not weaken execution controls.

**Independent Test**: Prove an admitted guard call succeeds while direct calls
from the agent, broker, sibling member, Border and external probe fail; inspect
observed limits and per-child usage.

**Acceptance Scenarios**:

1. **Given** a healthy model, **When** an unapproved process attempts direct
   inference or an altered target/model, **Then** access is refused before work.
2. **Given** an approved child, **When** it reaches its turn, time, memory or
   output bound, **Then** it stops with a truthful outcome and no paid fallback.
3. **Given** completion, **When** the operator inspects accounting, **Then**
   elapsed time, tokens, CPU/memory observations and zero provider API charges
   are recorded; host/transfer costs are described separately.

### User Story 3 - Recover one child without repeating either (Priority: P1)

An unavailable member, lost reply, model timeout or client restart must preserve
the other child's evidence and allow status recovery without repeating work.

**Why this priority**: Thermidor's unknown-outcome fence is essential even for
read-only arithmetic and free inference.

**Independent Test**: Complete IPv4, interrupt IPv6 after dispatch, restart the
client and owned worker, and compare original IDs, results and effect counts.

**Acceptance Scenarios**:

1. **Given** one completed child, **When** its sibling fails or remains unknown,
   **Then** the successful result remains visible and is never replayed.
2. **Given** a lost prepare/approval response, **When** the client reconnects,
   **Then** it recovers the same parent/children by read-only status lookup.
3. **Given** an uncertain provider request, **When** the process restarts,
   **Then** the persisted fence prevents retransmission; new work requires a new
   explicit approval after owned-process recovery has been verified.

### User Story 4 - Complete the workflow in VS Code and Mobile (Priority: P2)

The operator can prepare, separately review and approve, inspect and recover the
combined request in the installed VS Code workflow and enrolled Mobile client.

**Why this priority**: Roadmap G12/G13 require client delivery in this stage.

**Independent Test**: Actual Mac VS Code and native iPhone simulator each exercise
two child reviews/results and one-child failure/reconnect against the cloud Border.

**Acceptance Scenarios**:

1. **Given** the existing VS Code Name + URL connection, **When** the operator
   opens the combined request, **Then** both reviews and result states are usable
   without a new login scheme or manual installation-ID entry.
2. **Given** an enrolled Mobile device, **When** it runs the same workflow and
   backgrounds/reconnects, **Then** retained device identity and request references
   recover the same outcomes without replay or exposing model credentials.

### Edge Cases

- Invalid/noncanonical CIDR, duplicate family, a third child, mismatched member
  family, unsupported free text, host-bit input or changed model digest.
- IPv4 `/31` and `/32`; IPv6 `/0`, `/127`, `/128`; integer counts larger than
  browser precision; previous/next network overflow; excessive result size.
- Missing model, incompatible guard, stale readiness, OOM, provider timeout,
  expired review, denied second child, cancellation and stale profile generation.
- Lost acknowledgement, duplicate decisions, restart during inference, foreign
  installation/device references and old clients that lack combined capability.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Support one on-prem IPv4 member and one GCP IPv6 member using their
  own CPU-based Ollama instance; preserve placement versus inference distinctions.
- **FR-002**: Prepare one durable combined request containing exactly two stable
  child references, with distinct exact approvals and no work on preparation.
- **FR-003**: Bind each approval to principal, Border/member identity and current
  generations, exact canonical input, model/profile revision and finite limits.
- **FR-004**: Require a real model-proposed native subnet tool call and independently
  verified arithmetic. Keep authoritative result separate from model explanation.
- **FR-005**: Permit Ollama inference only through the child's qualified guard;
  prohibit direct agent/broker/Border/sibling/internet access and caller-selected
  upstreams, model downloads/mutations or paid-provider fallback.
- **FR-006**: Apply verified model/runner integrity, turn/token/output, CPU/memory,
  process, call and task limits; report unsupported profiles as unavailable.
- **FR-007**: Persist dispatch claims and truthful completed/failed/unknown outcomes.
  Reconnect, retry, duplicate submission and lost acknowledgements cannot repeat work.
- **FR-008**: Isolate child failure/cancellation; preserve successful sibling
  results and never silently redirect, renew approval or restart either child.
- **FR-009**: Record per-child elapsed time, actual token and CPU/memory observations,
  zero provider API charges, signed results, durable acknowledgements and GAIT links.
- **FR-010**: Present combined preparation, separate approval, results and recovery
  in HUD and VS Code with explicit G12 acceptance evidence.
- **FR-011**: Implement and verify the affected Mobile contracts and flow under
  G13; retain QR/device identity and distinguish simulator from physical evidence.
- **FR-012**: Preserve prior protected pyATS/NetBox/subnet behavior, paid-model
  profiles, historical authorities, usable owner deployment, Chat and Canvas.
- **FR-013**: Use finite owned qualification resources; capture baseline, rollback,
  preservation and cleanup evidence. Keep intended owner delivery usable within
  its existing lifetime; retire disposable resources after verified export.
- **FR-014**: Trace adopted choices/tests to exact Thermidor source and historical
  outcomes; qualify current NetClaw independently and retain unsuccessful attempts.
- **FR-015**: Keep workloads read-only, existing principal/transport controls and
  release holds; no new user-auth scheme, HA, eN2N, GPU or later roadmap stage.

### Key Entities

- **Calculator profile**: member family, placement, model/integrity, guard and limits.
- **Combined request**: immutable pair of child intents, owner context and expiry.
- **Child operation**: exact approved workload and existing execution lifecycle.
- **Verified result**: bounded arithmetic, explanation, usage and signed evidence.
- **Qualification record**: source/profile identities, actual probes, failures,
  client evidence, preservation and resource retirement or retained ownership.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One actual combined browser request yields two independently correct
  results from the intended hosts under two approvals; each child records two
  inference turns and exactly one native tool invocation within 180 seconds.
- **SC-002**: All named bypass probes fail while the matching admitted positive
  control succeeds on both hosts; observed resource limits match approved limits.
- **SC-003**: Each successful child has positive measured token usage, elapsed time,
  CPU/memory observations, zero provider API charges and verifiable result/ACK links.
- **SC-004**: Failure, lost reply and restart drills preserve both original child
  references and successful results with unchanged invocation counts.
- **SC-005**: Browser, actual Mac VS Code and native iPhone simulator each complete
  their specified combined-request and recovery scenarios, with platform limits stated.
- **SC-006**: Existing protected workload regressions pass; baseline comparisons show
  preserved owner state; every disposable resource is accounted for at closeout.

## Assumptions

- The owner has started R05 after accepted R04a/R04b. This deliverable is the branch
  and SDD package; implementation, actual execution and human acceptance are recorded
  separately. Spec176 preparation alone is not live qualification.
- Use Thermidor's final proven runner/model/guard/prompt and resource profiles as
  the starting point. Exact digests and adaptation are specified in research/contracts.
- Keep the R05 workload to subnet summaries using NetClaw's existing IPv4/IPv6 MCP
  tools. Thermidor subdivisions inform bounded arithmetic tests but are not a required
  new addressing-plan feature. Arbitrary natural-language planning is out of scope.
- Historical 28-second local and 150-second cloud completion are comparison evidence,
  not a promised latency target. Model locality does not eliminate result transfer.
- Retained pilot and client identities are preserved; no previous spent deployment,
  enrollment or operation artifact can be replayed. Exact cloud resource changes
  remain subject to the existing scoped execution review, not an inferred new grant.
- Source1.18.6, extension1.6.1 and Mobile1.0.4+7 are the baseline. No version bump,
  publication or R06/R07 advancement is part of this spec preparation.
