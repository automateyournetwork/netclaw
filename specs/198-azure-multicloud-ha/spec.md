# Feature Specification: R10 Azure Multi-Cloud (Border, 3-Region HA, GCP↔Azure Mesh)

**Feature Branch**: `198-azure-multicloud-ha`
**Created**: 2026-11-14
**Status**: Verified live acceptance and owned cleanup complete, 2026-11-24; source integration authorized. See [closure](closure-20261124.md) for original signed receipts, final cleanup, USD19.589 conservative ledger, retained limits and integration record.
**Input**: User description: "R10 Azure: NetClaw multi-cloud on Microsoft Azure, mirroring the proven GCP R09/R09A roadmap. A Border claw hosted in Azure with an on-prem member and a cloud-hosted member; 3-region HA Borders in Azure; then a cross-cloud mesh proving GCP-hosted Borders federate with Azure-hosted Borders; then update all docs and release-gate notes. Hard constraints: $25 total spend ceiling (stop and ask at $15), tear down right after validation, nothing created until the owner says go."

Latest instruction: resume implementation and bounded live qualification from
`ca64f507`; investigate the stable-network admission failure before paying for
another run. Close Azure-to-GCP, execution through every follower and actual GCP
leader-change success; qualify clients/members, reconcile billing, export and
verify owned cleanup. See [resume-20261124.md](resume-20261124.md). Three distinct
regions per cloud, current authority/security guarantees, USD25 cap and
Spec200 preservation remain. The owner approved one crossing of USD15 for the exact
USD23.0075943167 envelope and merging after verified acceptance; client publication is held. No checkbox/offline-only
completion claim is permitted.

## Execution amendment — 2026-11-14

See [activation-delegation.md](activation-delegation.md): owner authorizes alternate
Azure regions and the sequence one Azure Border → three Azure HA Borders plus
cloud NetBox member → federation with three GCP HA Borders (six total). This
supersedes the fixed region list, one-GCP-Border limit, repeated phase-go pauses
and the requirement to retire Azure before the bounded final mesh proof. The
USD15 pause, USD25 total ceiling, evidence/cleanup and publication holds remain.

## Context

NetClaw's Border claw, 3-region HA authority, and federated members were proven on one cloud (GCP) in R09/R09A (specs 179, 182, 185). R10 repeats that proof on a second major cloud provider, Microsoft Azure, and then proves the two clouds interoperate. The value is evidence that NetClaw is not tied to a single provider, produced within a small, hard-capped budget and with every resource removed immediately after validation.

## Clarifications

### Session 2026-11-14 (owner answers)

- Q: Azure regions? → A: Canada Central, West Europe, Southeast Asia (mirrors R09).
- Q: DNS? → A: Reuse the owner's domain with fresh per-run names (`<code>-<id6>.automateyournetwork.com`) via the existing DNS provider.
- Q: Provider key on VMs? → A: Yes, placed only for the hosted model profile and deleted at teardown.
- Q: On-prem member content? → A: Subnet-calculator members only; no CML in R10.
- Q: GCP side of the mesh? → A: Yes, but stood up only when the owner explicitly says it is time.
- Q: Spend ceiling? → A: $25 total; stop and ask at $15.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preflight and budget guard (Priority: P1)

Before anything is created, the owner can see that the Azure subscription is usable, that each target region offers a suitably small virtual machine size with enough quota, and that a spend alert and a spend tracker are in place. No billable resource exists after this story.

**Why this priority**: The owner has little budget and a newly upgraded subscription; discovering a quota or size restriction halfway through a deployment would waste money. This is the gate for everything else.

**Independent Test**: Run the preflight; it reports subscription state, per-region size availability and quota, and the budget alert status, and it creates nothing billable.

**Acceptance Scenarios**:

1. **Given** a subscription in a non-active state, **When** preflight runs, **Then** it reports the blocker and stops without creating anything.
2. **Given** an active subscription, **When** preflight runs, **Then** each of the three regions is reported as OK or blocked, with the reason (size unavailable or quota too low).
3. **Given** the cumulative estimated spend reaches $15, **When** the next billable step is about to start, **Then** the work pauses and asks the owner before continuing.

---

### User Story 2 - Border claw in Azure with on-prem and cloud members (Priority: P2)

The owner can reach a Border claw hosted in Azure over a trusted web address, attach a member running on the owner's own machine (on-prem) and a member hosted in the cloud, and complete a real operation through the Border from each member.

**Why this priority**: This is the smallest end-to-end proof that Azure can host a Border with both member placements. It is the MVP of R10.

**Independent Test**: With one Azure Border live, the on-prem subnet-calculator member and the cloud-hosted member each complete a real operation and the results are visible in the Border's workspace and audit record.

**Acceptance Scenarios**:

1. **Given** a running Azure Border with a valid certificate, **When** the owner opens its address, **Then** the workspace loads over a trusted secure connection.
2. **Given** the on-prem subnet-calculator member is enrolled, **When** an operation is requested through the Border, **Then** it completes and the result is returned.
3. **Given** the cloud-hosted NetBox member is enrolled against the public demo NetBox instance, **When** a NetBox query is requested, **Then** it completes with real data.

---

### User Story 3 - 3-region HA Borders in Azure (Priority: P3)

Three Azure Borders in three regions form one highly available group. Operations succeed when entered through any of the three Borders, and the group behaves according to the HA rules already proven on the other cloud (including the known finding that a degraded two-of-three far-region quorum cannot admit new operations).

**Why this priority**: This is the HA claim, which builds on the single-Border proof and costs the most to run.

**Independent Test**: Entering the same real operation through each of the three Borders completes with members attached, and a leader loss triggers takeover within the documented limits.

**Acceptance Scenarios**:

1. **Given** three healthy Borders, **When** an operation is entered through each in turn, **Then** each completes and is recorded.
2. **Given** the leader Border is stopped, **When** a new operation is entered through a surviving Border, **Then** the group elects a new leader and the operation completes or is refused with a clear, documented reason.
3. **Given** the validation is complete, **When** teardown runs, **Then** no billable Azure resource from this spec remains.

---

### User Story 4 - GCP↔Azure federation proof (Priority: P4)

A GCP-hosted Border and an Azure-hosted Border can federate, so an operation entered on one cloud is carried out by a member or Border on the other, with both clouds visible in the audit record.

**Why this priority**: This is the headline multi-cloud claim, but it depends on the earlier stories and on re-creating a GCP side, so it runs last and only on the owner's explicit go.

**Independent Test**: With one Border on each cloud federated, an operation entered on one is completed through the other and both audit records show it.

**Acceptance Scenarios**:

1. **Given** the owner has said the GCP side may start, **When** a minimal GCP Border is stood up, **Then** it federates with the Azure Border using the same trust model as between any two peers.
2. **Given** both clouds are federated, **When** an operation is entered on the Azure side that needs a member on the GCP side, **Then** it completes and appears in both audit records.
3. **Given** the proof is complete, **When** teardown runs, **Then** no billable resource remains on either cloud and the DNS records are removed.

---

### User Story 5 - Documentation and release-gate update (Priority: P5)

The documentation presents Azure as a supported second cloud next to GCP, and the release gate notes state exactly what remains unpublished.

**Why this priority**: Needed to close the roadmap, but it carries no cloud cost and can be done after the evidence exists.

**Independent Test**: A reader following the setup docs can find the Azure path, the budget guard, the teardown steps, and the explicit statement that no client build was published.

**Acceptance Scenarios**:

1. **Given** the GCP completeness and setup docs from specs 192 and 193, **When** this story is complete, **Then** each has an Azure counterpart or a clearly marked Azure section.
2. **Given** the release gate, **When** the docs are updated, **Then** they state that VS Code, mobile and HUD builds are not published without owner approval.

---

### Edge Cases

- The subscription is still in a warned state, or a card is declined partway through: the work stops before any billable step.
- A chosen region has no suitable small size or too little quota: preflight reports it and offers a documented substitute region for the owner to approve rather than switching silently.
- A run is interrupted midway: a single teardown action per phase removes everything labelled for this spec.
- Spend estimate crosses $15: the work pauses and asks; crossing $25 is not allowed.
- Certificate issuance is rate-limited or DNS propagation is slow: the run waits or retries without leaving billable resources idle for long.
- The provider key must never be left on a machine after teardown.
- A stranded operation holds the single admission slot (R09 finding): operations known to produce uncertain results run last.
- Billing country or card problems on the owner's account are an external dependency, not something this spec can fix.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Preflight MUST verify the subscription is active, and per region the availability and quota of the intended small virtual machine size, using read-only queries, before any billable resource is created.
- **FR-002**: The system MUST NOT create any Azure or GCP resource until the owner explicitly says go for that phase.
- **FR-003**: The GCP side of the cross-cloud proof MUST NOT be created until the owner explicitly says the time has come, separately from the Azure go.
- **FR-004**: Every cloud resource created MUST carry a label identifying spec 198 and its phase, and each phase MUST live in its own grouping so one deletion removes the phase.
- **FR-005**: Teardown MUST remove all labelled resources, the DNS records for the run, and any provider key placed on machines, and MUST then verify that none remain.
- **FR-006**: The system MUST track estimated cumulative spend, MUST pause and ask the owner at $15, and MUST NOT exceed $25 total.
- **FR-007**: A spend alert MUST be configured on the subscription before the first billable phase, with notification at 50% and 80% of $25.
- **FR-008**: Only small, low-cost virtual machine sizes and no managed cloud services MAY be used.
- **FR-009**: Each Azure Border MUST be reachable at a fresh per-run web address under the owner's domain with a trusted certificate.
- **FR-010**: The system MUST support enrolling an on-prem subnet-calculator member and a cloud-hosted member into the Azure Border and completing real operations through them.
- **FR-011**: The cloud-hosted member MUST be able to query the public demo NetBox instance using the owner's current token, which MUST be stored only in the owner's private local credential file and never printed.
- **FR-012**: The three Azure Borders MUST form one HA group across three distinct, owner-delegated, live-validated Azure regions, reusing the existing HA authority behavior without weakening it.
- **FR-013**: Operations MUST be demonstrated entering through each of the three Borders, with results and audit records captured as evidence.
- **FR-014**: A leader-loss takeover MUST be exercised and its outcome recorded, including any known limitations observed.
- **FR-015**: The hosted model profile MUST receive the provider key only for the duration of the run, and the key MUST be deleted from every machine at teardown.
- **FR-016**: A three-Border GCP HA group and the three-Border Azure HA group MUST federate using the existing peer trust model, and an operation crossing clouds MUST complete and appear in both audit records.
- **FR-017**: Any change to code that is already qualified MUST be listed for owner review and MUST NOT be merged or pushed without the owner's approval.
- **FR-018**: Nothing MUST be published, pushed live, version-bumped or announced (VS Code extension, mobile app, HUD) without the owner's explicit approval; the existing release gate remains in force.
- **FR-019**: Documentation MUST be updated to present Azure alongside GCP, including the budget guard, the preflight, the teardown procedure and the specs 192/193 surfaces.
- **FR-020**: Every phase MUST end with a recorded evidence entry (what ran, what passed, what failed, measured cost) in the spec's verification record.

### Key Entities

- **Phase**: One bounded stage (preflight, single Border with members, 3-region HA, cross-cloud mesh), with its own resource grouping, go decision, spend estimate and teardown.
- **Border**: A hosted claw serving the workspace and member traffic at a per-run address.
- **Member**: An on-prem or cloud-hosted worker (subnet calculator or NetBox) enrolled into a Border.
- **HA Group**: Three Borders in three regions sharing authority and an operation slot.
- **Spend Ledger**: Running estimate of cost per phase with the $15 pause point and $25 ceiling.
- **Evidence Record**: The verification entries for each phase, including cost and teardown confirmation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Total spend across all of R10, as shown by the cloud billing view, stays at or below $25, and no billable step starts after the $15 pause point without the owner's approval.
- **SC-002**: Preflight produces a per-region go/no-go for all three regions with no billable resource created, in under 10 minutes.
- **SC-003**: The owner can open an Azure Border's workspace over a trusted secure connection and complete one real operation through each of the two member types.
- **SC-004**: Real operations complete when entered through each of the three Azure Borders (3 of 3).
- **SC-005**: After a leader loss, the HA group reaches a new leader and the outcome of the next operation is recorded as completed or as a documented refusal, with no unexplained hang.
- **SC-006**: One operation entered on one cloud completes through the other cloud, and both audit records show it.
- **SC-007**: After each phase's teardown, a verification query finds zero remaining resources for that phase on every cloud, zero DNS records for the run, and no provider key on any machine.
- **SC-008**: No client build is published and no qualified code is merged without a recorded owner approval.
- **SC-009**: A reader can find the Azure setup, budget guard and teardown in the docs, and every doc that listed GCP-only coverage now covers Azure or marks it explicitly.

## Assumptions

- The owner's Azure subscription becomes active (the current state is "warned" until the upgrade completes); this is an external dependency.
- The existing R09/R09A tooling and the specs 179/182/185 behavior are reused and extended rather than rewritten; GCP-specific steps get Azure equivalents.
- The owner's domain and DNS provider credentials already on the owner's machine remain valid.
- GCP project billing is available for the final mesh phase and is counted toward the same $25 ceiling.
- The on-prem member is the owner's own machine, and subnet-calculator members need no external equipment.
- Public demo NetBox is available and its data is not sensitive.
- Cost estimates use published small-VM hourly rates, plus small allowances for addresses and storage; the billing view is the final measure.
- Native client releases remain out of scope; only release-gate notes are updated.
- This spec depends on, and does not duplicate, the HA authority (179), the multi-region GCP deployment (182) and the sandboxed deployment (185).
