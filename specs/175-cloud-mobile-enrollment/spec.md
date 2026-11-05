# Feature Specification: R04b Mobile QR enrollment from HUD and VS Code

**Feature Branch**: `175-cloud-mobile-enrollment`

**Created**: 2026-11-04

**Status**: Ratified by owner kickoff and explicit client/verification steering

**Input**: “04b time”; “make sure its easy right from the HUD to get the QR code; scan; enroll with local or GCP / cloud HUD; make sure the mobile section in VS Code allows for QR code / enrollment generation too use a simulated device or virtual iPhone xCode or whatever to really ensure this all works”.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enroll a phone from either HUD (Priority: P1)

The operator opens Mobile in their local or cloud Border HUD, chooses Enroll mobile device, displays a short-lived QR code, and scans it using the existing Mobile registration flow. The app saves its device identity and reconnects to the selected Border. The operator does not enter a host, installation identifier or user sign-in ticket.

**Why this priority**: This is the requested everyday connection path.

**Independent Test**: Generate and decode an actual QR from each supported HUD placement into a native iPhone simulator, observe one registered device, then reconnect using its retained key.

**Acceptance Scenarios**:

1. **Given** a ready local or cloud Border, **when** the operator opens Mobile and chooses Enroll mobile device, **then** one QR and its expiry appear without a terminal command or manual connection wizard.
2. **Given** that QR, **when** the existing scanner accepts it, **then** the app validates the Border and proves possession of its device key before registration completes.
3. **Given** an expired or spent QR, **when** another enrollment is attempted, **then** it fails clearly without regenerating authority or changing a prior enrollment.
4. **Given** an uncertain enrollment response, **when** the app reconnects, **then** it checks the original device identity without silently reenrolling.

### User Story 2 - Generate the same enrollment from VS Code (Priority: P1)

The operator opens Mobile under the selected local or cloud connection in VS Code and generates a QR in that view. Both clients use the selected Border's actual enrollment capability.

**Why this priority**: The owner explicitly requires VS Code parity, with an easy product entry point.

**Independent Test**: In a supported native editor, generate enrollment from both local and cloud Mobile views and use the generated QR with the native simulator.

**Acceptance Scenarios**:

1. **Given** a selected local or cloud Border, **when** Mobile is opened, **then** Enroll mobile device is visible whenever the Border supports it; unavailable setup is explained accurately.
2. **Given** an issued code, **when** the view closes, expires, or switches installation, **then** its secret is cleared from the view and is absent from persistent editor state and logs.
3. **Given** a cloud selection, **when** the code is generated, **then** it enrolls against that cloud installation and never invokes a local shell or unrelated runtime.

### User Story 3 - Use supported protected operations and recover (Priority: P1)

After enrollment, the phone presents the Border's actual supported operations, full immutable review and an explicit decision. It displays the signed result and delivery acknowledgment. Restart or background recovery retains the original enrollment, decision and operation.

**Why this priority**: A registered device alone does not deliver usable protected cloud operation.

**Independent Test**: Approve one bounded read on an enrolled simulator, verify its signed result and durable acknowledgment, and restart/reconnect while proving no duplicate execution.

**Acceptance Scenarios**:

1. **Given** a protected Border, **when** enrollment completes, **then** the app shows its supported protected operations and does not offer unsupported legacy Ask, capture, voice, watch or background execution.
2. **Given** a prepared operation, **when** its exact review is displayed and approved once, **then** only that reviewed operation can execute with attribution to the enrolled device.
3. **Given** a lost prepare or decision reply, **when** the app resumes, **then** it retains the uncertainty and recovers the original reference rather than preparing, deciding or executing again.
4. **Given** a completed operation, **when** the app backgrounds, reconnects or restarts, **then** the same signed result and acknowledgment remain with unchanged effect counts.
5. **Given** an existing local legacy Border, **when** the app enrolls or reconnects, **then** its existing supported local behavior and identities remain compatible.

### Edge Cases

Wrong domain, installation or device key; expired/reused token; concurrent claim of one QR; unsupported capability version; absent trusted listener; altered review; cross-device operation reference; malformed/oversized message; disconnect after token consumption; lost decision; revoked registration; app background or process death; changing selected VS Code connection while a QR is visible; scanner decode versus camera hardware limits.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: HUD Mobile MUST expose a visible Enroll mobile device action for supported local and cloud Borders without terminal steps.
- **FR-002**: VS Code Mobile MUST offer the equivalent selected-connection action and QR presentation for local and cloud.
- **FR-003**: Enrollment MUST preserve the existing scanner, device-key possession proof, single-use tokens and retained-key reconnect semantics.
- **FR-004**: Enrollment MUST bind the trusted destination, installation and device identity; wrong binding or unsupported capability MUST fail closed.
- **FR-005**: QR issuance MUST be deliberate, finite-lived and device-enrollment scoped. Expired/spent codes require a new explicit action. An unknown issuance/enrollment outcome MUST never trigger automatic replacement.
- **FR-006**: Tokens MUST stay out of logs, telemetry, clipboard automation, source, persistent UI state and shared evidence. Issued QR data exists only as long as needed for the visible enrollment flow.
- **FR-007**: Cloud transport MUST retain trusted TLS and confinement; the app MUST NOT use raw federation TCP or a public daemon/admin API.
- **FR-008**: Capabilities MUST truthfully distinguish protected operations from legacy local functionality and hide/refuse unsupported paths.
- **FR-009**: Enrolled devices MUST use the existing immutable protected catalog/review/decision/result/acknowledgment authority, with installation/device-scoped attribution and retained nonces.
- **FR-010**: Recovery MUST retain operation/enrollment identity and never repeat preparation, approval or effects. Unknown outcomes MUST remain blocked pending evidence.
- **FR-011**: Existing owner approvals, results, member keys and unrelated client/runtime profiles MUST remain unchanged; new device attribution MUST NOT rewrite historical principals.
- **FR-012**: Native iOS simulator acceptance MUST decode an actual generated QR and exercise the production enrollment/reconnect path, with precise distinction between camera hardware and image-decoding coverage.
- **FR-013**: Actual HUD and VS Code local/cloud generation, trusted enrollment, refusal cases, one protected read and no-repeat recovery MUST have separate evidence; unit tests alone do not establish native acceptance.
- **FR-014**: Deployment MUST retain the owner's usable GCP pilot and its existing lifetime; disposable test resources MUST be cleaned after evidence export. Use bounded changes and preserve rollback/unknown outcomes.
- **FR-015**: Device registration MUST NOT introduce user login, SSO, tickets, or a new user authentication system. Later identities/SSO/RBAC work remains separate.
- **FR-016**: Source, extension and Mobile version/publication holds remain in force for R04b; R05 requires a later owner instruction. Maintainer evidence MUST state exact platform and unsupported-feature limits.

### Key Entities

- **Enrollment offer**: Selected Border, destination, expiry and one-use authority displayed as a QR.
- **Registered device**: Retained device key identity, installation binding, revocation status and advertised capabilities.
- **Protected operation reference**: Installation/device identity, unique request nonce, immutable review revision/digest, decision outcome, signed result and durable acknowledgment.
- **Verification receipt**: Source and deployment identity, actual client/target, observed outcomes, effect counts and explicit coverage limitations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In each HUD placement and each selected VS Code connection type, opening Mobile exposes QR generation within one explicit action; no manual host/ticket entry is required.
- **SC-002**: Actual generated QR data completes native simulator enrollment for local and cloud, with exactly one registration per successful offer and the same retained identity after reconnect.
- **SC-003**: Wrong destination/key/installation, expired/spent offer and unauthorized-method scenarios are rejected without execution.
- **SC-004**: One separately reviewed bounded read returns its exact signed result and acknowledgment; process/background recovery leaves approval, operation and effect counts unchanged.
- **SC-005**: Existing supported local enrollment and VS Code cloud workspace checks pass, while historical pilot authority and unrelated profiles remain preserved.
- **SC-006**: Final evidence distinguishes real native behavior, fixtures and unqualified physical-device features, and inventories show no unreviewed disposable residue.

## Assumptions

- The owner's kickoff and follow-up authorize this bounded implementation and actual native verification, including necessary reviewed updates to the existing development pilot. They do not authorize broad rollout or later roadmap stages.
- Simulator coverage is explicitly requested and sufficient for this stage; physical camera/device testing is reported separately and never inferred.
- Existing cloud pilot, protected member and bounded read catalog are reused after fresh observation. No new cloud resource is needed by default.
- Local testing uses an isolated owned Border or explicitly scoped fixture, preserving existing installations. Local legacy compatibility and protected cloud behavior have separate assertions.
- The current open-lab access policy remains explicit; enrollment is device registration, not a user-identity boundary.


## November 5 scoped publication amendment

After requesting completion and supplying the replacement private credential,
the owner explicitly requested packaging, commit/PR/merge, a source patch release,
VS Code publication, changed Mobile app release, release notes, a safe screenshot,
a maintainer note and a draft in modern_website. This supersedes earlier
publication exclusions for this Mobile enrollment update only. Acceptance and
release outcomes are recorded in verification.md and release-verification.md.
The general cloud rollout hold and explicit full stop before R05 remain.
