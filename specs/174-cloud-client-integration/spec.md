# Feature Specification: R04a cloud Border clients

**Feature Branch**: `174-cloud-client-integration`  
**Created**: 2026-11-03  
**Status**: Complete and owner accepted; source integration and scoped production VS Code publication authorized November4

**Input**: Drive R04a efficiently; authoritative scope is `docs/roadmap/issue-310/briefs/R04a-cloud-border-client-integration.md`.

## November4 acceptance correction

The owner explicitly rejected the diagnostic `Cloud-Border.json` landing and the
operations-only client as failure to deliver R04a. Connecting by Name + URL must
open the existing NetClaw operating interface backed by the selected cloud Border:
normal Overview, Chat, Canvas, RAG, member/federation and other implemented panels.
A connection badge, JSON document or narrowly tested read is not completion.
Both client restrictions and the stripped cloud API must be corrected together.
Reuse the existing normal UI/routes/runtime; do not build another operations-only
substitute or expose menus whose backend is absent. Local extension-host filesystem,
installation and service actions remain local; cloud panels use explicit remote
capabilities and the selected cloud identity. No user authentication is added.
Preserve current authority/history and original failure evidence during integration.

## User Scenarios & Testing

### User Story 1 — VS Code cloud work (Priority: P1)

The operator adds a cloud Border using only its name and HTTPS URL, reviews and approves one supported read, sees its attributable result, and recovers the same work after reconnect. The current pilot requires no user authentication.

**Independent Test**: Run the actual Mac extension against a fresh protected Border; complete one R04 read and restart without repeating it.

1. **Given** a trusted HTTPS URL, **when** the operator connects, **then** the client discovers and pins its installation, verifies role/capabilities and opens the connected view without an identity or sign-in prompt.
2. **Given** a prepared request, **when** the owner approves its complete immutable review, **then** the exact revision/digest is submitted once and the result and acknowledgement are shown.
3. **Given** an interrupted response, **when** the owner reconnects, **then** the retained reference is inspected without resubmission.

### User Story 2 — Mobile cloud work (Priority: P1)

The native app offers an explicit cloud-owner profile separate from enrolled edge Chat. The owner can perform and recover the same protected workflow.

**Independent Test**: Exercise the affected native flow on the available selected platform, recording simulator versus physical-device scope separately.

1. **Given** an existing separate cloud profile, **when** the operator selects a read, **then** the app honors the server's explicit access mode and exact protected review. The current pilot has no user sign-in; legacy Ask and edge approval IDs do not authorize protected operations.
2. **Given** backgrounding, profile closure or restart, **when** recovery occurs, **then** the same operation is inspected and no effect repeats.

### User Story 3 — Preserve local and authority boundaries (Priority: P1)

**Independent Test**: Existing local profile and lifecycle regressions pass while negative cloud requests fail closed.

1. **Given** a local profile, **when** existing controls are used, **then** existing installation bindings remain authoritative.
2. **Given** a remote profile, **when** local host lifecycle, raw daemon/admin or unadvertised write controls are attempted, **then** handlers prevent them; normal advertised cloud Chat/Canvas/RAG and operating panels remain usable.

### Edge Cases

Wrong origin/installation/role, invalid TLS, redirects, changed access mode, stale review, dropped prepare/decision replies, unknown results, duplicate taps, and profile switching must fail closed without replay or credential disclosure. A retained native NetBox HTTP401/403 response may be settled as a signed failed read only after exact historical approval/attempt, source, call, HTTP and stopped-runtime evidence are validated. Recovery must reuse the original authority, perform no provider/MCP/HTTP effect, and preserve the failure evidence. Missing, conflicting or genuinely uncertain evidence remains blocked; no reference deletion or replacement approval may bypass that pause.

## Requirements

- **FR-001**: Reproduce the reported VS Code failure in the actual editor before claiming a fix.
- **FR-002**: Both clients MUST explicitly distinguish local/edge profiles from cloud-owner profiles and pin HTTPS origin plus expected installation identity.
- **FR-003**: Both clients MUST verify role/capabilities, TLS and endpoint identity using existing protected contracts; no redirects or insecure override. The current explicitly selected development pilot has no user authentication. Authentication is deferred to later roadmap work.
- **FR-004**: The current development connection MUST require no login, ticket, session or access-mode setup, including hidden auto-login. Persist only the non-secret origin and installation binding in profile state; member credentials and private results must not enter ordinary client settings/logs.
- **FR-005**: Both clients MUST provide supported catalog selection, preparation, complete exact review, one explicit decision, attributable result/ACK, and scoped audit references.
- **FR-006**: Clients MUST persist a bounded installation/origin-scoped nonce before prepare and retain operation references across ambiguous responses; recovery MUST inspect/reconcile without automatic prepare/decision replay.
- **FR-007**: Local profiles/lifecycle and enrolled Mobile flows MUST retain their original authority; unsupported cloud controls MUST fail in both UI and handlers.
- **FR-008**: Existing server confinement MUST remain unchanged; inaccurate protected edge capabilities MUST be corrected without opening legacy routes.
- **FR-009**: Verification MUST include meaningful security/regression tests, actual editor execution, affected native Mobile execution, fresh finite cloud evidence and owned cleanup; record physical-device limitations honestly.
- **FR-010**: Preserve R01 and retired R03/R04 evidence. Never replay spent plans/enrollment/approvals. The owner's November4 acceptance authorizes source integration and the production VS Code extension update. Preserve upstream source1.18.5; no source release/tag, blog, general cloud rollout or later-stage execution is authorized. See release-verification.md for this narrow exception to the roadmap publication hold.
- **FR-012**: Name + URL connection MUST open the normal operating workspace, with working cloud-backed Chat/Canvas/RAG and advertised estate/operations/integration panels. Raw JSON is optional evidence only. Reuse existing views and handlers through an explicit verified HTTPS remote HUD contract; both client and server must satisfy this before completion.
- **FR-011**: Deliver a usable persistent GCP Border and connection in the owner's installed VS Code, with a verified HTTPS URL and automatically discovered installation identity. The exact flow is Add Connection → Local / Cloud → Cloud → Name → URL → Connected; no ID/auth/access-mode prompt. Disposable editor/cloud qualification alone does not complete this requirement. Keep the owner deployment available within the scoped pilot lifetime; cleanup applies to disposable test resources. The November4 owner instruction authorizes necessary GCP image rebuild and scoped development-runtime/client updates with baseline and rollback.

### Key Entities

- Connection profile: explicit mode, origin, expected installation, non-secret label.
- Current lab principal: server-advertised installation-bound unauthenticated operator identity; truthful audit attribution, not a user session or future RBAC identity. Historical approvals retain their original principal.
- Operation reference: installation/origin, client nonce, optional operation ID; no request secrets or result bodies.
- Immutable review: operation ID, revision, digest and full server review; only explicit owner decision authorizes execution.

## Success Criteria

- **SC-001**: One actual VS Code protected read completes with correct identity, exact approval, signed result and durable ACK.
- **SC-002**: One affected native Mobile protected read completes and recovers on the selected qualified platform; physical/simulator evidence is distinguished.
- **SC-003**: Lost responses and restart produce zero repeated effects; wrong identities, invalid TLS and stale approvals are refused.
- **SC-004**: Existing local/client/server regressions pass, fresh owned qualification resources are removed, and the human receives evidence and remaining platform limits before R05.
- **SC-006**: The actual owner editor renders the normal cloud workspace and completes representative Chat, Canvas/RAG and estate operations through the selected cloud endpoint with no login or accidental local actions; installation alone or menu presence is not proof.
- **SC-005**: The owner's installed VS Code connects to the retained GCP endpoint, performs a supported protected read and recovers the same result after restart. The profile, supported extension and service remain usable at handoff; rollback and trial expiry are documented. Do not count an isolated test editor or retired hostname as this delivery.

## Assumptions

User authentication/SSO/RBAC remain deferred to R15–R17. This explicitly selected open lab uses the existing bounded HTTPS operations API without user sessions. Historical owner-session compatibility remains fail-closed outside this mode. The existing Mobile QR path requires separate HUD/WSS/protected-operation work proposed as R04b; its source assessment and the bounded Mobile compatibility tests do not claim new QR or physical-device qualification. Mac is the selected editor host; native Mobile target follows actual available device inventory. Four optional roadmap passes were used; this focused implementation uses remaining pass five, with no automatic extra improvement loops. Required fixes/qualification remain part of this pass. The prior R04 merge authorization does not release the roadmap.
