# Feature Specification: GCP Borders and HA Mesh inside OpenShell and DefenseClaw (R09A)

**Feature Branch**: `183-openshell-defenseclaw-gcp` (stacked on `182-multi-region-ha-borders`, PR #340)
**Created**: 2026-11-09
**Status**: Draft
**Input**: Roadmap substep R09A, owner instruction 2026-11-09: "make absolutely sure the GCP Borders and HA mesh (two Borders in the same region is fine) run inside OpenShell and DefenseClaw". R09B (a survey of other GCP capabilities that make the deployment more complete) follows; Azure (R10) starts only after both.

## Context carried from R09 (inputs, not requirements)

R09 proved three GCP Borders as one HA cluster with real operations from three member kinds, and it recorded security gaps that this stage exists to close:

- The Borders, the HUD ingress and the workspace backend ran as plain systemd services on the VMs. There was no OpenShell sandbox on any Border or member host.
- The workspace chat gateway held the provider (Anthropic) key in its process environment with no model-traffic inspection on the Border; DefenseClaw guarded only the member model call.
- The hosted guard had no egress filter and no spend meter. The workspace HUD was open-lab (no sign-in).
- The repository currently documents systemd host confinement, not an OpenShell container, as the production sandbox control for iN2N Risks, and says OpenShell is optional. This feature decides, with evidence, whether OpenShell can host the HA Border and mesh processes without weakening any HA, identity or admission guarantee.

## Owner decisions already made (not open)

- Scope is the GCP deployment: the HA Borders and the HA mesh (cluster plane, iN2N attachments, members, workspace, model guard).
- A smaller validation topology is acceptable: two Borders in the same region may be used instead of the three-region mesh. The three-region result of R09 is not re-proven here unless cheap to do so.
- Azure (R10) starts only after R09A and R09B.
- Nothing is published, pushed live or announced without explicit owner approval; no billed resource is created before the owner confirms a line-item estimate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every Border and mesh component runs inside an OpenShell sandbox (Priority: P1)

The owner deploys the Borders and the mesh and can see that each NetClaw-owned runtime process (Border role, public HUD ingress, workspace backend and gateway, model guard, and each GCP-hosted member) runs inside its own OpenShell sandbox with an explicit policy for files, network peers and processes, and that the HA cluster still forms, elects a leader and completes a real operation.

**Why this priority**: It is the substance of R09A. Without it the other guarantees have nothing to protect.

**Independent Test**: Deploy two Borders in one region inside OpenShell; verify each component reports "sandboxed" with its policy; verify a leader is elected and a real operation completes through each Border.

**Acceptance Scenarios**:
1. **Given** a deployed node, **When** the owner inspects its status, **Then** every in-scope process shows the sandbox it runs in, the policy version and hash, and a healthy state.
2. **Given** two sandboxed Borders in one region, **When** the cluster starts, **Then** it forms, elects a leader, and a real protected operation completes through either Border with a durable acknowledgement.
3. **Given** a component that cannot run inside a sandbox without breaking an HA guarantee, **When** the owner reviews the deployment, **Then** a documented, evidence-backed disposition exists for it; none is silently excluded.

### User Story 2 - DefenseClaw inspects and can block model and tool activity on the Borders (Priority: P1)

All model traffic and tool calls that originate on a Border (workspace chat and agent) and on GCP-hosted members are inspected by DefenseClaw. A prompt or tool call that violates policy is blocked and recorded; if the guard is unavailable, the activity stops rather than proceeding unguarded.

**Why this priority**: R09 left the Border-side chat path uninspected and the provider credential exposed to an unguarded process.

**Independent Test**: Send a prompt and a tool call that violate policy; confirm both are blocked and audited. Stop the guard; confirm model activity stops.

**Acceptance Scenarios**:
1. **Given** guardrails in blocking mode, **When** a violating prompt or tool call is issued, **Then** it is refused, the owner sees a clear reason, and an audit record exists.
2. **Given** the guard is stopped or unreachable, **When** a model request is made, **Then** it fails closed with no unguarded provider call.
3. **Given** a skill, MCP or plugin is added, **When** it is enabled, **Then** it is scanned first and a failing component is refused.

### User Story 3 - Isolation holds under attack (Priority: P1)

An operator deliberately attempts the escapes that matter and each is refused and recorded: reading or writing outside the sandbox policy, altering the frozen source, reaching the cloud metadata server, connecting to a non-approved external host, reading the provider credential from inside the agent, and member-to-member connections.

**Why this priority**: Isolation that is not tested adversarially is not evidence.

**Independent Test**: Run the negative suite against a deployed node; every attempt fails and leaves a record.

**Acceptance Scenarios**:
1. **Given** a sandboxed workspace agent, **When** it tries to read a path or credential outside its policy, **Then** access is denied and recorded.
2. **Given** a sandboxed process, **When** it tries to contact the metadata server or an unapproved host, **Then** the connection is blocked and recorded.
3. **Given** two members, **When** one tries to connect to the other, **Then** the connection is refused as in R09.

### User Story 4 - HA behavior survives confinement (Priority: P2)

With the sandboxes and guards in place, the R09 behaviors still hold within their measured limits: leader failover, a stopped Border, a cut between Borders, an isolated Border reporting no quorum, and operations completing inside the signed admission window. The added latency of the sandbox and guard is measured and reported against that window.

**Why this priority**: Confinement is worthless if it breaks admission timing or failover; R09 showed the admission window is tight.

**Independent Test**: Re-run the R09 failure matrix on the sandboxed nodes and record timings.

**Acceptance Scenarios**:
1. **Given** sandboxed Borders, **When** the leader is stopped, **Then** a new leader is elected and operations resume through the survivor.
2. **Given** sandbox and guard overhead, **When** an operation is admitted, **Then** it completes inside the signed window, or the measured overshoot is reported with the setting that restores it.
3. **Given** a cut or isolation, **When** it is applied and healed, **Then** behavior matches the unsandboxed R09 results.

### User Story 5 - The owner can operate and prove it (Priority: P2)

The owner can see per-node sandbox and guard health in status and in VS Code, export the audit trail, start, stop and upgrade a node without breaking identity or authority, and tear everything down by exact resource list.

**Why this priority**: A secured deployment that cannot be observed or removed cleanly is not usable.

**Independent Test**: Read status for every node, export audit, restart one node, then tear down against the listed resources.

**Acceptance Scenarios**:
1. **Given** a running deployment, **When** the owner opens status, **Then** each node shows sandbox, policy and guard state.
2. **Given** a restarted node, **When** it returns, **Then** it rejoins with its original identity and does not reclaim authority it lost.
3. **Given** teardown, **When** it completes, **Then** no resource from this stage remains.

### Edge Cases

- A sandbox policy that is too strict stops a component from starting: the node reports which rule blocked it and does not fall back to an unconfined run.
- A sandbox policy that is too loose: the negative suite fails the release rather than the policy being accepted.
- The guard sidecar restarts during an operation: the in-flight operation resolves as a signed refusal or an explicit unknown, never as a silent proceed.
- Sandbox start time delays a Border past its lease: the cluster tolerates it without split authority.
- Memory or disk pressure from sandbox runtime on a small VM: reported and resolved by sizing, not by disabling confinement.
- Two Borders in one region: the cluster cannot lose a Border and keep a majority; this limit is recorded, not hidden.
- Provider or guard upstream outage: model activity fails closed and recovers without replay.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every NetClaw-owned runtime process of a GCP Border (Border role, public HUD ingress, workspace backend, chat gateway, model guard) MUST run inside an OpenShell sandbox with an explicit, versioned policy.
- **FR-002**: Every GCP-hosted member in the mesh MUST run inside an OpenShell sandbox with an explicit, versioned policy.
- **FR-003**: Each sandbox policy MUST name the files it may read and write, the network peers it may reach, and the processes it may run; everything else is denied.
- **FR-004**: The HA mesh MUST continue to function inside the sandboxes: cluster formation, leader election, authority renewal, member attachment, and forwarding from followers to the leader.
- **FR-005**: No HA, identity or admission guarantee from Specs 179 and 182 may be weakened to make confinement work; where one would be, the conflict MUST be reported with evidence and a disposition.
- **FR-006**: DefenseClaw MUST inspect all model prompts and completions that originate on a Border or a GCP-hosted member.
- **FR-007**: DefenseClaw MUST inspect tool calls on those paths and enforce its rule categories in blocking mode for the validation.
- **FR-008**: A policy violation MUST be refused, shown to the owner with a reason, and written to the audit trail.
- **FR-009**: If the guard is unavailable, model and tool activity MUST fail closed with no unguarded provider call.
- **FR-010**: Skills, MCP servers and plugins MUST be scanned before they are enabled on a sandboxed node, and a failing component MUST be refused.
- **FR-011**: The provider credential MUST NOT be readable by the agent process inside its sandbox; the path that uses it MUST be mediated.
- **FR-012**: Outbound network from each sandbox MUST be limited to the approved destinations for that component, including blocking the cloud metadata server.
- **FR-013**: A negative isolation suite MUST exist and pass: out-of-policy file read and write, frozen-source modification, metadata-server access, unapproved egress, credential read, and member-to-member connection.
- **FR-014**: Each node MUST report per-component sandbox state, policy version and hash, and guard state in status, visible in the HUD and VS Code.
- **FR-015**: The audit trail MUST be retained per node and exportable, and MUST record blocked activity, policy changes and guard availability changes.
- **FR-016**: The sandbox and guard overhead on operation admission MUST be measured and reported against the signed admission window.
- **FR-017**: The R09 failure matrix (stopped Border, leader change, cut between Borders, isolated Border) MUST be re-run on the sandboxed nodes and compared with the R09 results.
- **FR-018**: A restarted node MUST rejoin with its original identity and MUST NOT reclaim authority it lost.
- **FR-019**: A component that cannot be sandboxed MUST have a documented, evidence-backed disposition; silent exclusions are not allowed.
- **FR-020**: The validation topology MAY be two Borders in one region; if so, the loss-of-majority limit of that topology MUST be recorded.
- **FR-021**: The VS Code and Mobile client impact MUST be assessed under the roadmap's G12 and G13 rules, with a reasoned no-change disposition if unaffected, including how a guard-blocked request is presented.
- **FR-022**: No billed resource is created before the owner confirms a line-item cost estimate, and teardown is performed only on the owner's request against an exact resource list.
- **FR-023**: Nothing from this stage is published, pushed live or announced without explicit owner approval.
- **FR-024**: Findings that need changes to qualified code MUST be listed for owner review before being relied on, as in R09.

### Key Entities

- **Sandbox**: an OpenShell confinement for one component on one node, with a policy, state and health.
- **Sandbox Policy**: versioned, hashed rules for files, network peers and processes.
- **Guardrail Policy**: DefenseClaw rule configuration and mode (observe or block) for model and tool activity.
- **Audit Record**: a retained entry for blocked activity, policy change or guard state change.
- **Node Posture**: the per-node view of sandbox, policy and guard state shown in status.
- **Negative Test**: a deliberate escape or violation attempt with its expected refusal and record.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of in-scope Border and member processes on the validation nodes run inside a sandbox with a recorded policy, or carry a documented disposition.
- **SC-002**: The cluster forms and a real operation completes through every Border while sandboxed.
- **SC-003**: Every case in the negative isolation suite is refused and recorded, with zero successful escapes.
- **SC-004**: A policy-violating prompt and tool call are each blocked and audited in blocking mode.
- **SC-005**: With the guard stopped, 0 model requests reach the provider.
- **SC-006**: The provider credential is not readable from inside the agent sandbox.
- **SC-007**: Admission overhead from confinement is reported, and operations complete inside the signed window or the setting that restores it is identified.
- **SC-008**: The stopped-Border, cut and isolation tests reproduce the R09 results (leader change, clean refusal, no-quorum report) on sandboxed nodes.
- **SC-009**: Per-node sandbox and guard health is visible in the HUD and VS Code.
- **SC-010**: Teardown leaves 0 resources from this stage.

## Assumptions

- "Two is fine, same region" means a validation topology of two Borders in one region is acceptable for R09A; the three-region mesh of R09 remains the product target and is not required to be re-proven here.
- All NetClaw-owned application processes are in scope; the etcd voters are infrastructure and are confined by container policy, included in the sandbox boundary where feasible.
- DefenseClaw runs in blocking mode for the validation; an initial observe-mode run is allowed to tune policy.
- OpenShell needs a container runtime on each host, so VM sizing may increase; the cost estimate is confirmed by the owner before billed resources are created.
- Existing qualified artifacts (the R04A Anthropic guard configuration, the R09 deployment tooling) are reused; findings that require changes to qualified code follow FR-024.
- The R09 findings listed above are inputs; the open HUD and provider-key exposure are in scope to reduce, while sign-in and SSO belong to R15 to R17.
