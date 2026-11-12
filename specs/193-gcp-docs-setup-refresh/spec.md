# Feature Specification: GCP Deployment Setup, Guides and Documentation Refresh (R09C)

**Feature Branch**: `193-gcp-docs-setup-refresh`
**Created**: 2026-11-12
**Status**: Draft
**Input**: User description: "R09C / Spec 193 - GCP deployment documentation, setup and guides refresh. Closes out GCP before Azure (R10). Make deploying NetClaw Borders and Members in GCP possible directly from the real installer paths (setup.sh / install.sh, the VS Code setup-from-scratch flow, the installer TUI), refresh README / getting-started / assistant-install / Claw Plan docs, add a separate 'NetClaw in GCP' guide, repeat a prominent no-authentication warning, and update the roadmap."

## Context

The GCP work so far (R03-R09, R09A) proved that Borders and Members run in GCP, on-prem, or mixed, and that a Risk can be made highly available and distributed across regions. That capability lives in operator-run lab tooling bound to one operator's project, names and regions. The R09B survey (`specs/192-gcp-completeness-survey/survey.md`) is **complete** and is kept as a reference if GCP is ever revisited; it is not reopened here.

R09C is the last GCP step before Azure (R10). It turns the proven GCP deployment into something any user can reach from the normal install paths, and documents it honestly, including the fact that **there is no authentication yet**. Users, SSO and RBAC arrive much later (R15-R17).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy a Border or Member in GCP from the normal installer (Priority: P1)

A NetClaw user who already has a GCP project runs the standard installer (the command-line setup, or the VS Code from-scratch flow) and chooses to place a Border, a Member, or both in GCP. They are shown exactly what will be created, where, and the estimated running cost, confirm it, and end up with a working GCP-hosted node attached to their Risk.

**Why this priority**: This is the core deliverable. Without it GCP deployment remains an operator-only lab procedure and nothing else in the spec has anything to document.

**Independent Test**: On a clean machine with a GCP project the user owns, run the installer, choose "Border in GCP", confirm the reviewed plan, and verify the Border is reachable, reports healthy, and appears in the user's Risk. Then tear it down and verify nothing the installer created remains.

**Acceptance Scenarios**:

1. **Given** a user with a GCP project and valid GCP credentials, **When** they choose a GCP Border in the installer and confirm the reviewed plan, **Then** a Border is created in their project using their own project, region and naming, and it joins their Risk.
2. **Given** the same user, **When** they choose a GCP Member, **Then** a Member is created and attached to a Border they select (GCP-hosted or on-prem).
3. **Given** a user without GCP credentials or without the needed project permissions, **When** they pick a GCP option, **Then** the installer stops before creating anything and says exactly what is missing.
4. **Given** the user declines the reviewed plan, **When** the installer exits, **Then** no GCP resource has been created or billed.
5. **Given** the user later chooses teardown, **When** they confirm, **Then** every resource the installer created is removed and a verification shows the project holds none of them.

---

### User Story 2 - Choose the topology: GCP, on-prem, or a mix (Priority: P1)

The user decides what shape of Risk they want: all in GCP, Borders in GCP with on-prem Members, on-prem Borders with GCP Members, a highly available Risk (multiple Borders), or a distributed Risk spanning regions. The installer and VS Code flow present these as named choices and only the pieces needed for the chosen shape are created.

**Why this priority**: The value the owner wants users to experiment with is the topology itself. A GCP-only path would miss the on-prem and mixed cases that were proven in R03-R09.

**Independent Test**: Pick each topology in turn in a throwaway project and verify the resulting node count, placement and Risk membership match what the choice promised.

**Acceptance Scenarios**:

1. **Given** the topology menu, **When** the user selects "GCP Border with on-prem Members", **Then** only the GCP Border is provisioned and the installer gives the steps and values needed to attach on-prem Members.
2. **Given** the topology menu, **When** the user selects an HA Risk, **Then** the installer provisions the number of Borders and supporting parts that HA requires and explains the minimum node count before asking for confirmation.
3. **Given** the topology menu, **When** the user selects a distributed (multi-region) Risk, **Then** the installer asks for the regions, shows the per-region cost, and notes any client-update requirement that applies to multi-region exposure.
4. **Given** an existing on-prem Risk, **When** the user adds a GCP Border or Member, **Then** the existing Risk is extended rather than replaced.

---

### User Story 3 - See a clear, repeated no-authentication warning (Priority: P1)

Everywhere a user can start a GCP deployment (README, installer prompts, VS Code flow, the GCP guide, and the post-deploy summary) the user is told plainly that the deployment is **not behind any authentication**, that endpoint URLs must be kept private, and that users, SSO and RBAC are planned for a much later phase.

**Why this priority**: Publicly reachable, unauthenticated infrastructure is a real exposure. The experimentation the owner is encouraging is only responsible if this is impossible to miss.

**Independent Test**: Walk every GCP entry point and the final deployment summary; each shows the warning in its own words-for-words standard text, and the installer will not proceed past the first GCP prompt without the user acknowledging it.

**Acceptance Scenarios**:

1. **Given** a user choosing any GCP option, **When** the choice is made, **Then** the warning is shown and an explicit acknowledgement is required before any resource is planned.
2. **Given** a completed deployment, **When** the summary is printed, **Then** it repeats the warning and lists each public endpoint as "keep private".
3. **Given** the README and GCP guide, **When** a reader looks at the top of each, **Then** the warning and the roadmap pointer to the later users/SSO/RBAC phase are visible without scrolling past other sections.

---

### User Story 4 - Read an accurate GCP guide and refreshed docs (Priority: P2)

A user reads a separate "NetClaw in GCP" guide that explains Borders and Members, the supported topologies (GCP, on-prem, mixed, HA Risk, distributed Risk), prerequisites, expected cost, how to tear down, and what is not yet provided. The README, VS Code getting-started guide, assistant-install guide and Claw Plan guide are updated so they agree with the installer and link to the GCP guide.

**Why this priority**: Docs make the feature usable and safe, but the installer paths (P1) must exist first for the docs to be verifiable.

**Independent Test**: A person who has never deployed NetClaw follows only the GCP guide from a blank machine to a working GCP node and to teardown, without needing any information found elsewhere.

**Acceptance Scenarios**:

1. **Given** the refreshed docs, **When** a reader compares any documented GCP step or option with the installer, **Then** they match (names, order, outcomes).
2. **Given** the GCP guide, **When** a reader looks for cost, **Then** they find per-topology running-cost estimates and the teardown steps that stop the charges.
3. **Given** the README and getting-started guide, **When** a reader looks for GCP, **Then** each links to the GCP guide and none contains instructions that contradict it.

---

### User Story 5 - Roadmap reflects the close of GCP (Priority: P3)

The Issue #310 roadmap marks R09B as complete (kept as a reference), adds R09C as the final GCP step, and shows R10 (Azure) following it, with users, SSO and RBAC (R15-R17) unchanged as a later phase.

**Why this priority**: Housekeeping that keeps planning documents truthful; low risk, small effort.

**Independent Test**: Read the roadmap index and the R09B/R09C briefs; ordering, dependencies and statuses are consistent with this spec.

**Acceptance Scenarios**:

1. **Given** the roadmap, **When** a reader looks up R09B, **Then** it is marked complete and points to the survey as a reference.
2. **Given** the roadmap, **When** a reader looks up R09C and R10, **Then** R09C follows R09B and R10 depends on R09C.

---

### Edge Cases

- The user's GCP project lacks a required service enabled, or has insufficient quota in the chosen region.
- The user's organization policy forbids something the deployment needs (for example public IP addresses or service-account keys).
- A deployment is interrupted halfway: the user must be able to re-run safely, resume, or tear down what was partially created.
- The user selects a region where a required machine type is unavailable.
- The user runs the installer on native Windows (installation targets macOS and supported WSL2 Ubuntu; Windows remains a read-only gate).
- Two users deploy into the same project: names must not collide, and teardown must only remove what that run created.
- The user already has resources whose names resemble the installer's naming scheme; teardown must not touch them.
- The user skips or fails the DNS/certificate prerequisite for public endpoints.
- A user tries to continue after declining the no-authentication acknowledgement.
- The deployment is left running unattended; the user should have been told the running cost and how to stop it.

## Requirements *(mandatory)*

### Functional Requirements

**Deployment from the installer paths**

- **FR-001**: The command-line installer MUST offer deploying a Border in GCP, a Member in GCP, or both, as named choices.
- **FR-002**: The VS Code from-scratch setup flow MUST offer the same GCP choices with the same names, order and outcomes as the command-line installer.
- **FR-003**: The installer's interactive menu (TUI) MUST present the GCP choices alongside the existing on-prem choices, including mixed topologies.
- **FR-004**: The assistant-driven install flow and the Claw Plan flow MUST be able to express the same GCP choices, so a GCP deployment is not limited to one entry point.
- **FR-005**: The installer MUST support these topologies: GCP-only, GCP Border with on-prem Members, on-prem Border with GCP Members, a highly available Risk (multiple Borders), and a distributed Risk across more than one region.
- **FR-006**: Every GCP deployment MUST use the user's own project, region(s) and resource naming supplied at setup; no value specific to a previous operator may remain in the paths a user runs.
- **FR-007**: Before creating anything, the installer MUST present a reviewable plan listing each resource to be created, its location, and estimated running cost, and MUST create nothing until the user confirms.
- **FR-008**: The installer MUST verify prerequisites (credentials, project access, required permissions, required services, quota where checkable) before the plan is shown and MUST stop with a specific message for each unmet prerequisite.
- **FR-009**: The installer MUST be safe to re-run: an interrupted or repeated run MUST NOT create duplicate nodes or silently replace an existing node's identity.
- **FR-010**: The installer MUST provide teardown that removes only resources it created, identifiable by a per-deployment marker, and MUST verify afterward that none remain.
- **FR-011**: A new GCP Border or Member MUST join the user's existing Risk, or start a new Risk if none exists, and the installer MUST report the result (node identity, role, health) at the end.
- **FR-012**: Secrets needed for deployment (model provider keys, DNS credentials) MUST NOT be written into logs, plans, summaries or the repository.
- **FR-013**: Setup choices already adopted from the R09B survey that affect initial setup (least-privilege identity for the nodes, per-person administrative access, secret storage, firewall structure, budget alert) MUST be applied by default or offered as explicit options, and each MUST be stated in the plan.
- **FR-014**: Where a topology requires newer published client builds (multi-region exposure), the installer MUST state this before confirmation.

**No-authentication warning**

- **FR-015**: Every GCP entry point (README section, installer prompts, VS Code flow, GCP guide, post-deploy summary) MUST show the same standard warning: the deployment is NOT behind any authentication; keep endpoint URLs private; users, SSO and RBAC are a much later roadmap phase (R15-R17).
- **FR-016**: The installer MUST require explicit acknowledgement of the warning before any GCP resource is planned, and MUST exit without side effects if it is declined.
- **FR-017**: The post-deploy summary MUST list each public endpoint and mark it "keep private".
- **FR-018**: Documentation MUST NOT describe or imply that sign-in, access control or user separation exists today.

**Documentation**

- **FR-019**: A separate "NetClaw in GCP" guide MUST exist covering: what Borders and Members are, supported topologies, prerequisites, step-by-step deployment from each installer path, cost per topology, HA and distributed Risk, teardown, troubleshooting, and known limits.
- **FR-020**: The README, VS Code getting-started guide, assistant-install guide and Claw Plan guide MUST be reviewed and updated where they touch GCP, installer options or topology, and MUST link to the GCP guide.
- **FR-021**: The documentation MUST encourage experimentation (GCP, on-prem, mixed, HA Risk, distributed Risk) and pair every such encouragement with the warning's scope.
- **FR-022**: Documented counts, option names and commands MUST be consistent with the installer and with the repository's existing inventory and reconciliation checks.
- **FR-023**: The roadmap MUST be updated: R09B marked complete and kept as a reference, R09C added as the final GCP step, R10 shown as following R09C, R15-R17 unchanged.

### Key Entities

- **Risk**: The user's NetClaw deployment as a whole; may span on-prem and GCP and may be HA or distributed.
- **Border**: A node that fronts a Risk and takes part in HA; each has its own identity and must not be silently replaced.
- **Member**: A node attached to a Border that provides capabilities (for example a device-access or model-hosting role).
- **Topology**: The named shape the user chooses (GCP-only, mixed, HA, distributed).
- **Deployment Plan**: The reviewed, confirmable list of resources, locations and estimated cost produced before anything is created.
- **Deployment Marker**: The per-deployment identifier that lets teardown find exactly what a run created.
- **Standard Warning**: The single agreed no-authentication text reused at every entry point.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user with a prepared GCP project can go from the installer start to a healthy GCP Border in their Risk in under 45 minutes of elapsed time, following only the GCP guide.
- **SC-002**: 100% of the documented topologies (GCP-only, GCP Border + on-prem Members, on-prem Border + GCP Members, HA Risk, distributed Risk) are selectable from the command-line installer and the VS Code flow with identical names and outcomes.
- **SC-003**: After teardown, 0 resources created by the run remain in the project, and 0 resources not created by the run are removed.
- **SC-004**: 100% of GCP entry points and the post-deploy summary display the standard warning; 0 documents imply that authentication exists.
- **SC-005**: 100% of unmet prerequisites are reported before any resource is created; declining the plan or the warning leaves 0 resources and 0 charges.
- **SC-006**: A reader comparing the docs to the installer finds 0 contradictions in option names, order, or commands in a documented review of all updated documents.
- **SC-007**: A re-run after an interruption produces 0 duplicate nodes and 0 changed node identities.
- **SC-008**: No deployment-specific value from a previous operator appears in any path a user executes (verified by an automated scan).
- **SC-009**: The roadmap shows R09B complete, R09C added, and R10 depending on R09C, with no other item's order changed.

## Assumptions

- The user owns or administers a GCP project and can create billable resources; the installer never creates a project or billing account.
- The R09B survey stays as a reference and is not reopened; only its adopted setup-relevant items are applied here.
- Native Windows remains a read-only gate; real installation targets macOS and supported WSL2 Ubuntu, as for the existing installer.
- Public endpoints remain unauthenticated until R15-R17; this spec adds no sign-in or access control.
- The existing reviewed-plan ("exact-review") installer engine is the model for presenting and confirming the plan.
- Multi-region exposure still needs the owner-approved published client builds (R09 gate); the installer informs the user but does not perform releases.
- Azure and AWS parity is out of scope; this spec only finishes the GCP pattern that R10 and R12 will mirror.
- Fixture or dry-run success is not claimed as proof of a real deployment; real-deployment evidence is recorded separately and honestly.
- Cost figures are estimates and are labeled as such.

## Out of Scope

- Authentication, users, SSO, RBAC, delegated authority (R15-R17).
- Load balancers in front of Borders, edge protection and other items the survey deferred or rejected.
- Azure and AWS deployment (R10-R14).
- Publishing client builds.
