# Feature Specification: R04a cloud Border clients

**Feature Branch**: `174-cloud-client-integration`  
**Created**: 2026-11-03  
**Status**: Technical qualification and owned retirement complete; human acceptance pending

**Input**: Drive R04a efficiently; authoritative scope is `docs/roadmap/issue-310/briefs/R04a-cloud-border-client-integration.md`.

## User Scenarios & Testing

### User Story 1 — VS Code cloud work (Priority: P1)

An owner explicitly selects a cloud Border, authenticates, reviews and approves one supported read, sees its attributable result, and recovers the same work after reconnect.

**Independent Test**: Run the actual Mac extension against a fresh protected Border; complete one R04 read and restart without repeating it.

1. **Given** a trusted HTTPS origin and expected installation, **when** the owner connects, **then** the client verifies identity, role and supported capabilities before accepting the owner session.
2. **Given** a prepared request, **when** the owner approves its complete immutable review, **then** the exact revision/digest is submitted once and the result and acknowledgement are shown.
3. **Given** an interrupted response, **when** the owner reconnects, **then** the retained reference is inspected without resubmission.

### User Story 2 — Mobile cloud work (Priority: P1)

The native app offers an explicit cloud-owner profile separate from enrolled edge Chat. The owner can perform and recover the same protected workflow.

**Independent Test**: Exercise the affected native flow on the available selected platform, recording simulator versus physical-device scope separately.

1. **Given** a cloud profile, **when** the owner authenticates and selects a read, **then** the app uses protected owner authority and exact review rather than legacy Ask or edge approval IDs.
2. **Given** backgrounding, sign-out or restart, **when** recovery occurs, **then** the same operation is inspected and no effect repeats.

### User Story 3 — Preserve local and authority boundaries (Priority: P1)

**Independent Test**: Existing local profile and lifecycle regressions pass while negative cloud requests fail closed.

1. **Given** a local profile, **when** existing controls are used, **then** existing installation bindings remain authoritative.
2. **Given** a remote profile, **when** local lifecycle, legacy Chat, model, MCP or admin controls are attempted, **then** unsupported actions are unavailable and handler enforcement prevents them.

### Edge Cases

Wrong origin/installation/role, invalid TLS, redirects, expired/revoked sessions, stale review, dropped prepare/decision replies, unknown results, duplicate taps, and profile switching must fail closed without replay or credential disclosure.

## Requirements

- **FR-001**: Reproduce the reported VS Code failure in the actual editor before claiming a fix.
- **FR-002**: Both clients MUST explicitly distinguish local/edge profiles from cloud-owner profiles and pin HTTPS origin plus expected installation identity.
- **FR-003**: Both clients MUST verify role/capabilities, TLS and owner authority using existing protected contracts; no redirects, insecure override or authority inferred from a URL.
- **FR-004**: Bootstrap tickets MUST remain transient; sessions belong in native secure storage, CSRF in memory, and neither secrets nor private results in ordinary profile state/logs.
- **FR-005**: Both clients MUST provide supported catalog selection, preparation, complete exact review, one explicit decision, attributable result/ACK, and scoped audit references.
- **FR-006**: Clients MUST persist a bounded installation/origin-scoped nonce before prepare and retain operation references across ambiguous responses; recovery MUST inspect/reconcile without automatic prepare/decision replay.
- **FR-007**: Local profiles/lifecycle and enrolled Mobile flows MUST retain their original authority; unsupported cloud controls MUST fail in both UI and handlers.
- **FR-008**: Existing server confinement MUST remain unchanged; inaccurate protected edge capabilities MUST be corrected without opening legacy routes.
- **FR-009**: Verification MUST include meaningful security/regression tests, actual editor execution, affected native Mobile execution, fresh finite cloud evidence and owned cleanup; record physical-device limitations honestly.
- **FR-010**: Preserve R01 and retired R03/R04 evidence. Never replay spent plans/enrollment/approvals. No version, release, Marketplace, blog or public rollout; human evidence review precedes R05.

### Key Entities

- Connection profile: explicit mode, origin, expected installation, non-secret label.
- Owner session: native secure credential, in-memory CSRF and expiry, bound to profile identity.
- Operation reference: installation/origin, client nonce, optional operation ID; no request secrets or result bodies.
- Immutable review: operation ID, revision, digest and full server review; only explicit owner decision authorizes execution.

## Success Criteria

- **SC-001**: One actual VS Code protected read completes with correct identity, exact approval, signed result and durable ACK.
- **SC-002**: One affected native Mobile protected read completes and recovers on the selected qualified platform; physical/simulator evidence is distinguished.
- **SC-003**: Lost responses and restart produce zero repeated effects; wrong identities, invalid TLS and stale approvals are refused.
- **SC-004**: Existing local/client/server regressions pass, fresh owned qualification resources are removed, and the human receives evidence and remaining platform limits before R05.

## Assumptions

Existing single-owner authority applies until R15–R17. Current HTTPS owner/operations API is sufficient. Mac is the selected editor host; native Mobile target follows actual available device inventory. Four optional roadmap passes were used; this focused implementation uses remaining pass five, with no automatic extra improvement loops. Required fixes/qualification remain part of this pass. The prior R04 merge authorization does not release the roadmap.
