# Feature Specification: Multi-Region HA Borders (R09)

**Feature Branch**: none created (owner instruction: reuse `specs/182-multi-region-ha-borders`; no new numbered branch)
**Created**: 2026-11-08
**Status**: Draft
**Input**: Three HA Borders (Spec 179 authority model) across three cloud regions, DNS-named TLS endpoints, a NetBox cloud member, on-prem pyATS and CML members attaching outbound, client support for region-aware endpoints and failover under the R09 release gate. Draft inputs: `plan.md` in this folder; `specs/179-border-ha-authority/{acceptance,resume,runbook,real-closure-plan}.md`.

## Owner decisions already made (not open)

- Regions: northamerica-northeast1, europe-west1, asia-southeast1 (owner chose "global spread").
- Monthly cost ceiling: $300.
- Project `netclaw-506315`, account `ptcapo@gmail.com`.
- The old environment (VM `netclaw-r01-20261101`, its 2 reserved IPs, its firewall rules) stays until the owner asks to tear it down. The owner asks only after adding the three new Borders by DNS name in VS Code and capturing a screenshot. Teardown then needs its own confirmation of an exact resource list.
- No billed resource is created until the owner confirms the line-item cost estimate.
- Nothing is published, pushed live or announced (VS Code, Mobile, HUD) without explicit owner approval.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner proves three global Borders by name (Priority: P1)

The owner opens VS Code, adds three Borders by their DNS names (one per region) and sees each connect over verified TLS, showing its region and role (current authority or follower). The owner captures a screenshot as proof.

**Why this priority**: It is the stated success condition and the gate for tearing down the old environment.

**Independent Test**: With only three running Borders and a client build that accepts DNS-named endpoints, add all three in VS Code and confirm each shows connected, with the cluster identity matching.

**Acceptance Scenarios**:

1. **Given** three Borders running with valid certificates for their DNS names, **When** the owner adds each name in VS Code, **Then** each shows connected with the same cluster identity, a distinct region and an indication of which Border currently holds authority.
2. **Given** an endpoint whose name or certificate does not match the cluster's signed membership, **When** the owner adds it, **Then** the client refuses it and says why.
3. **Given** the screenshot is captured, **Then** the old environment is still untouched.

---

### User Story 2 - Authority survives loss of a region (Priority: P1)

Any one region can become unreachable. The remaining two keep admitting protected work; the lost region's Border refuses new protected work and never acts on stale authority.

**Why this priority**: This is the point of multi-region HA, and R08 only proved it on one host.

**Independent Test**: Isolate one region at the network level (real WAN, not only the consensus path). Verify the majority continues, the isolated Border refuses, and no effect occurs twice.

**Acceptance Scenarios**:

1. **Given** a healthy three-region cluster, **When** the authority's region is cut off, **Then** a new authority is elected among the other two and protected work resumes within the measured admission bounds.
2. **Given** an isolated Border, **When** a user approves work through it, **Then** it is refused and nothing is executed.
3. **Given** all three regions are cut from each other, **Then** every Border refuses protected work and no tool is called.
4. **Given** the lost region returns, **Then** it rejoins without replaying or re-running earlier work.

---

### User Story 3 - Members attach from cloud and on-prem (Priority: P2)

A NetBox member runs in the cloud, and pyATS and CML members run on-prem. All attach outbound only to the Borders. No on-prem inbound port is opened. The members stay usable when one Border is lost.

**Why this priority**: It proves the real topology (outbound-only on-prem), but depends on Borders existing.

**Independent Test**: Start each member, confirm it is enrolled and visible through all three Borders, then drop a Border and confirm work still reaches the member through a survivor.

**Acceptance Scenarios**:

1. **Given** on-prem pyATS and CML with outbound internet only, **When** they enroll, **Then** they attach to all three Borders without any inbound firewall change.
2. **Given** a member attached to three Borders, **When** one Border is lost, **Then** a request still reaches the member through a survivor.
3. **Given** a member, **Then** it holds no consensus credentials and no listening role.

---

### User Story 4 - Client builds support multi-region and are gated (Priority: P2)

VS Code, Mobile and HUD builds handle region-aware endpoint lists, failover between regions and clear no-quorum/stale-review states. Each build is bumped and built, then held for owner approval.

**Why this priority**: It is a hard R09 gate. Multi-region HA cannot be called released without it. The owner's screenshot (US1) needs only the VS Code part first.

**Independent Test**: Build each client, run its journey against the multi-region topology, and confirm the published-build re-run is blocked until owner approval is recorded.

**Acceptance Scenarios**:

1. **Given** a cluster with three regional endpoints, **When** the active endpoint fails, **Then** the client moves to another signed endpoint and shows the failover.
2. **Given** a pending review whose authority changed, **Then** the client shows it as stale and does not auto-renew, resend or invoke.
3. **Given** a finished build, **Then** nothing is published, pushed live or announced without a recorded owner approval.
4. **Given** published builds, **Then** the journeys are re-run against them (not repo checkouts) before R09 is called released.

---

### User Story 5 - Cost-bounded, owned, reversible environment (Priority: P1)

The owner sees a line-item monthly estimate under $300 before anything is created. Every resource is labelled so only exactly-owned resources are touched, and teardown is a separate, confirmed step.

**Why this priority**: It controls spend and protects other resources.

**Independent Test**: Review the estimate and resource inventory without any billed resource existing, then check that every resource created later carries the ownership label.

**Acceptance Scenarios**:

1. **Given** the design, **Then** the estimate lists each resource with its monthly cost and a total at or below $300 including egress.
2. **Given** deployment, **Then** every resource carries the spec's ownership label and the firewall has no world-open ssh or rdp rules.
3. **Given** teardown, **Then** it only removes labelled or named resources the owner confirmed.

---

### User Story 6 - Honest evidence against R08 limits (Priority: P3)

The multi-region qualification closes or explicitly restates each R08 limit. It claims nothing it did not observe.

**Why this priority**: Credibility. It does not block the screenshot.

**Independent Test**: Walk the R08 limit list and confirm each has either new evidence or an explicit "still not claimed".

**Acceptance Scenarios**:

1. **Given** the R08 limits (etcd-path-only partitions, forward-only clock step, Border-to-Border channel cut not exercised, fenced restore Phase 2 not run, native effect counts not independently observed), **Then** each is closed with evidence or restated as unclaimed.
2. **Given** any run that leaves a budget slot `unknown`, **Then** the slot is never reset.

### Edge Cases

- Inter-region latency is too high for the admission window: the system refuses safely, no availability claim is made, and the owner gets options.
- The authority sits in the slowest region (Asia): leader placement is decided from measurements.
- One region is fully down while an on-prem member is mid-operation: work is not fabricated, and an uncertain effect stays unknown.
- Clock skew or a backward clock step in one region.
- Certificate expiry or DNS failure for one Border.
- Cloud quota or billing limit blocks creating a region.
- Linux behaves differently from macOS in CI (process identity, time handling).
- The old environment's open firewall rules remain while the new environment is being built.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run three Borders, one in each of the three owner-chosen regions, forming a three-voter quorum under the Spec 179 authority model.
- **FR-002**: Each Border MUST be reachable at a stable DNS name with a valid TLS certificate matching its signed membership identity.
- **FR-003**: Protected work MUST be admitted only by the current majority. A reachable but isolated Border MUST refuse it.
- **FR-004**: Loss of any one region MUST NOT stop protected work on the remaining two, within measured bounds.
- **FR-005**: Isolating all three Borders from each other MUST cause refusal everywhere with zero added tool calls.
- **FR-006**: A Border that returns after a partition MUST rejoin without replaying or re-running prior effects.
- **FR-007**: A cloud NetBox member MUST attach outbound to all three Borders.
- **FR-008**: On-prem pyATS and CML members MUST attach outbound only, with no inbound port opened, and MUST NOT hold consensus credentials.
- **FR-009**: Members MUST remain reachable through surviving Borders when any one Border is lost.
- **FR-010**: Inter-region latency between the three regions MUST be measured before deployment, and leader placement and the admission window MUST be decided from those measurements. If the measurements do not fit the admission window, the system MUST be reported as refusing safely and no availability claim made.
- **FR-011**: Real inter-region network partitions MUST be tested, including the Border-to-Border channel. The production change this needs MUST be specified as a task, not assumed.
- **FR-012**: Clock handling MUST be tested for forward step, backward step and suspend or monotonic discontinuity, in addition to R08's forward wall step.
- **FR-013**: Fenced restore Phase 2 MUST be run on a new generation, or restated as not claimed.
- **FR-014**: Effect counts MUST be observed independently of the process under test, or restated as not claimed.
- **FR-015**: The VS Code extension MUST accept three DNS-named Borders, show per-Border region and role, and fail over between signed endpoints.
- **FR-016**: The Mobile app MUST support enrollment against a multi-region cluster descriptor, node selection across regions, and background/cold recovery.
- **FR-017**: The HUD/Border build MUST serve the fixed mobile enrollment route on every Border.
- **FR-018**: Clients MUST show no-quorum and stale-review states, and MUST NOT auto-renew a stale review, resend approval or invoke a tool.
- **FR-019**: Client versions MUST be bumped and built, and each outward step (publish, push live, announce) MUST require a recorded owner approval. The agent MUST NOT take it unprompted.
- **FR-020**: After publication, the HUD, VS Code and iOS journeys MUST be re-run against the published builds on the multi-region topology before R09 is called released.
- **FR-021**: A line-item monthly cost estimate at or below $300 (including egress) MUST be presented and confirmed by the owner before any billed resource is created.
- **FR-022**: Every created resource MUST carry an ownership label. The firewall MUST NOT allow world-open ssh or rdp, and administration MUST use an identity-aware path.
- **FR-023**: The old VM, reserved IPs and firewall rules MUST NOT be deleted or modified until the owner asks. Teardown MUST list the exact resources and get a separate confirmation.
- **FR-024**: Only exactly-owned resources MAY be removed, and unrelated containers and services (equinix-*, pyats-mcp, gateway5, drawio-mcp) MUST NOT be touched.
- **FR-025**: An `unknown` budget slot MUST NEVER be reset. Unknown-producing scenarios MUST run last, one per run.
- **FR-026**: Exit codes MUST NOT be read through pipes in any script or verification step.
- **FR-027**: Tests MUST run on both macOS and Linux CI, with local pytest on Python 3.10.
- **FR-028**: Maintainers MUST be told about the spec-number collision with `specs/179-convergence-setup` and the un-bumped versions (main 1.20.0). A draft note is prepared, and nothing is sent without the owner.
- **FR-029**: Documentation MUST NOT describe multi-region HA as available to end users until the release gate (FR-019, FR-020) is satisfied.

### Key Entities

- **Border**: a regional node with its own identity, key, certificate and DNS name; one of three voters; at most one holds execution authority at a time.
- **Cluster descriptor**: the signed membership listing every Border endpoint, region and identity; the only source clients trust for endpoints.
- **Member**: an outbound-only attached service (NetBox, pyATS, CML) with no consensus credential or listening role.
- **Region placement**: the mapping of Border to region, with measured latency and leader preference.
- **Cost estimate**: the line-item monthly projection and the owner's confirmation record.
- **Ownership label**: the marker that identifies resources this spec created.
- **Release approval record**: the owner's explicit approval for each outward step.
- **Evidence matrix**: the per-row record of what was observed versus not claimed, including the R08 limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner adds all three Borders by DNS name in VS Code and captures a screenshot showing three connected Borders, each with a distinct region.
- **SC-002**: With any single region isolated, protected work continues on the other two and the isolated Border admits zero protected work, in 100% of tested cases.
- **SC-003**: With all three regions isolated, zero protected tool calls occur.
- **SC-004**: Measured inter-region latency is recorded for every region pair before deployment, and the admission window and leader placement are justified by it.
- **SC-005**: The monthly estimate is at or below $300 and every resource is listed with its cost before anything is created.
- **SC-006**: 100% of created resources carry the ownership label, and no world-open ssh or rdp rule exists in the new environment.
- **SC-007**: On-prem members run with zero inbound firewall changes.
- **SC-008**: Each of the five R08 limits is closed with new evidence or restated as unclaimed.
- **SC-009**: Zero client builds are published, pushed live or announced without a recorded owner approval.
- **SC-010**: Before R09 is called released, the HUD, VS Code and iOS journeys pass against published builds.
- **SC-011**: The old environment is unchanged until the owner asks for its teardown.

## Assumptions

- The Spec 179 authority, admission and recovery implementation on main is the base. This spec adds the deployment and the client support, not a new consensus design.
- Quota and billing in `netclaw-506315` allow three regions. This is verified before the estimate is confirmed.
- DNS names come from a domain the owner controls. Which domain is chosen at planning time.
- The owner provides on-prem hosts for pyATS and CML with outbound internet access.
- Latency across the global-spread regions may not fit the 3 s admission window in the worst leader placement. FR-010 governs that case.
- Public, versioned releases of the clients are done only by the owner through an owner-approved channel. App Store review time is outside our control.
- Out of scope: tearing down the old environment (separate owner-triggered step), changing the consensus design, and announcing or documenting multi-region HA as available before the release gate.
