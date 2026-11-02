# R17 — RBAC, delegated authority, approvals and audit

- **Roadmap item:** 10 — RBAC and fine-grained permissions
- **Depends on:** R16
- **Gate:** human review; multi-user may ship enabled after this passes

## Specify input

Permissions come from identity-provider groups or roles through a
provider-neutral mapping, and are enforced server-side at the Border and again at
the executing member for every MCP tool, SSH session, API integration and
automation workflow. UI hiding is never the control. The user's authority travels
with every delegation, over iN2N and eN2N, as a signed, scoped, short-lived
assertion; each member enforces the user's grants intersected with its own peer
grants and local ceiling. Border access never implies administrator access.

High-impact operations need approval by a different authorized user, and
production changes still need their ServiceNow CR. Audit records show who
initiated a request, which devices were accessed, which tools ran, which commands
or changes executed, whether and by whom they were approved, and the outcome.
Secrets are redacted, records are tamper-evident in GAIT, and only authorized
roles can read them.

User stories:
- P1: A Network Viewer can diagnose and search knowledge but cannot prepare or
  execute changes, even by asking the agent.
- P1: A Network Engineer prepares a change; a Network Administrator who is not the
  author approves it; it executes under a CR with full audit.
- P1: A member refuses a delegation that exceeds the user's grants.
- P2: An auditor queries who touched a device in a time window.

## Clarify: decisions (recommended default first)

1. Permission model: subject (principal or group) × action (read, diagnose,
   prepare change, execute change, approve, administer) × scope (device, device
   group, site or tag, member, Border, tool or MCP, integration) × conditions (CR
   required, time window).
2. Default roles: Viewer, Engineer, Administrator (from the issue) plus Approver and
   Auditor.
3. Policy engine: one declarative policy evaluated identically on Border and
   member. Compare an in-house evaluator with Cedar or OPA in research. [HUMAN]
4. Device scope source: NetBox sites, roles and tags.
5. eN2N: the external organization receives a pseudonymous principal plus an
   organization assertion and applies its own grants.
6. Self-approval: prohibited for anything requiring approval.
7. Group staleness: a bounded maximum age before re-evaluation.

## Plan notes

- Write operations become possible for the first time here; Constitution I–III
  and VIII apply in full (observe first, baseline, CR, verify, rollback).
- Prompt injection must not be able to widen authority: the broker checks the
  delegation assertion, not the model's request.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Matrix | Automated role × action × scope tests |
| Bypass | Operations hidden in the UI but called through the API, WebSocket or agent are refused |
| Injection | Agent asked to use an unpermitted tool is refused at the broker |
| Delegation | Member refuses assertions exceeding user grants, expired assertions and assertions from a non-authority Border |
| Approvals | Four-eyes enforced; self-approval refused; CR required for production changes |
| Audit | Each required field present; secrets redacted; non-auditors refused; tampering detected |
