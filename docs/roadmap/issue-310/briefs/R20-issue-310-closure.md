# R20 — Issue #310 closure: isolation suite and UX

- **Roadmap item:** 11 — rest of issue
- **Depends on:** R19
- **Gate:** human posts the closing comment

## Specify input

Verify every requirement in issue #310 and byrn-baker's comment against real
evidence, finish the user experience, and close the issue. The experience shows
the signed-in user, separates personal and shared information clearly, shows only
the operations a role allows, and keeps identity and session handling consistent
across Chat, Canvas and terminal workflows. A cross-user isolation test suite runs
in CI covering the issue's security considerations: endpoint authorization,
WebSocket authorization, cross-user memory retrieval, temporary files and
terminals, credentials and tokens, unauthorized MCP execution, indirect access
through agent tools, retention and deletion, and concurrent use.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Which isolation tests run on every PR versus nightly against the cloud mesh.
2. Data retention and deletion policy defaults for conversations, memory, audit
   and knowledge. [HUMAN]

## Acceptance evidence

| Group | Evidence |
|---|---|
| Traceability | Every row of the README traceability table links to verification evidence |
| Isolation suite | Green in CI; nightly mesh run recorded |
| UX | Sign-in, current user, personal versus shared labels, role-aware visibility across Chat, Canvas and terminals |
| Documentation | Admin guide for providers, roles, retention and break-glass |
| Closure | Draft closing comment answering the five maintainer questions, for a human to post |
| VS Code integration | Explicit G12 impact/disposition and evidence: Consolidated actual extension evidence across the roadmap; affected UX/security/recovery gaps closed |
| Mobile integration | Explicit G13 impact/disposition and evidence: Consolidated app impact and actual affected-flow evidence; platform/device limits explicit; reasoned no-impact outcome if unaffected |
