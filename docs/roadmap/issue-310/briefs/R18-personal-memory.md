# R18 — Personal conversations and memory

- **Roadmap item:** 11 — rest of issue (personal memory)
- **Depends on:** R17
- **Gate:** human review before R19

## Specify input

Each user has a persistent, private memory: past incidents, troubleshooting
notes, preferred diagnostic workflows, saved findings and ongoing investigations.
The agent retrieves relevant personal context automatically so users do not
repeat themselves. Personal memory never becomes visible to other users. Users can
see what is stored, correct it, delete it and export it, and retention policies
apply. Deletion propagates to every replica and index across the nine Borders.

User stories:
- P1: A user returns to an investigation and the agent recalls the earlier
  findings without being told.
- P1: A user deletes a memory and it can no longer be retrieved anywhere.
- P1: Another user cannot surface it by any prompt or tool.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Storage: reuse NetClaw's RAG and Chroma bridge (`chroma_store_bridge.py`) with
   per-user collections enforced server-side, not a shared collection filtered by
   metadata.
2. Capture: automatic, with a visible log of what was saved and one-click removal.
3. Retention default. [HUMAN]
4. Administrator access to personal memory: none, except an audited legal-hold
   process. [HUMAN]

## Acceptance evidence

| Group | Evidence |
|---|---|
| Retrieval | Relevant personal context recalled in a new conversation |
| Control | Inspect, correct, delete and export all work |
| Erasure | Deleted items absent from vector stores and replicas on every Border |
| Leakage | Canary memories cannot be retrieved by another user through prompts, tools or search |
| Retention | Expiry enforced |
| VS Code integration | Explicit G12 impact/disposition and evidence: Personal history/memory access, correction and deletion remain scoped to the signed-in user |
| Mobile integration | Explicit G13 impact/disposition and evidence: Affected personal history/memory and account-switch flows preserve the same ownership boundaries; reasoned no-impact outcome if unaffected |
